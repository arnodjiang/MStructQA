import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.evaluation.migrate_token_router import migrate, reusable, verify_images
from scripts.evaluation.run import Runner
from scripts.evaluation.run_token_router import TokenRouterRunner
from scripts.final_benchmark.api import save, read


class MigrationTests(unittest.TestCase):
    def test_openai_repair_preserves_unchanged_failure_and_requeues_only_changed_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old, new, source, target = [root/n for n in ('old','new','source','target')]
            refs = []
            for dataset in (old, new):
                (dataset/'validation_release').mkdir(parents=True)
                (dataset/'original.png').write_bytes(b'original')
                (dataset/'changed.png').write_bytes(b'changed')
            for i in range(3):
                refs.append(dict(id=str(i), case_id=str(i), source='fixture', query='Q?',
                    image_path='../original.png', image_sha256=hashlib.sha256(b'original').hexdigest(),
                    query_language='en', image_language='en', answer_language='en',
                    provenance={'row_index':i}, answer='1'))
            (old/'validation_release/val.candidates.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in refs))
            revised = [dict(r) for r in refs]
            revised[0]['answer'] = 'corrected'
            revised[2].update(image_path='../changed.png', image_sha256=hashlib.sha256(b'changed').hexdigest())
            (new/'validation_release/val.candidates.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in revised))
            args = SimpleNamespace(dataset=old, output=source, max_output_tokens=8192, workers=1, smoke=False)
            with patch('scripts.evaluation.run.load', return_value={'OPENAI_API_KEY':'fixture','OPENAI_MODEL':'fixture'}):
                runner = Runner(args)
                for i in range(3):
                    rid = str(i)
                    save(source/'predictions'/(rid+'.json'), dict(id=rid, run_key=runner.run_key,
                        status='failed' if i==1 else 'completed', prediction=None if i==1 else '1', selected_attempt=1))
                    save(source/'attempts'/rid/'001.json', dict(id=rid, attempt_number=1, status='failed' if i==1 else 'completed'))
                    save(source/'requests'/(rid+'.json'), dict(id=rid, run_key=runner.run_key,
                        question='Q?', image_sha256=refs[i]['image_sha256'], model='fixture',
                        prompt_sha256=runner.identity['prompt_sha256']))
                runner.lock_file.close()
                report = migrate(source,new,target,provider='openai',preserve_failed=True,expected_changed={'2'})
            self.assertEqual(report, {'reused_count':2,'changed_input_count':1,'remaining':1})
            self.assertEqual(read(target/'predictions/1.json')['status'],'failed')
            self.assertFalse((target/'predictions/2.json').exists())
            self.assertEqual(read(source/'predictions/0.json')['run_key'],runner.run_key)
            # A paused full run can migrate without resampling completed unaffected QA.
            from scripts.final_benchmark.api import digest
            from scripts.evaluation.context_input import VERSION
            paragraphs = [{'id':'pre_000', 'text':'Source evidence: 1.'}]
            revised[2]['source_context'] = {'policy':VERSION, 'language':'en',
                'paragraphs':paragraphs, 'text_sha256':digest(paragraphs)}
            (new/'validation_release/val.candidates.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in revised))
            (source/'predictions/1.json').unlink()
            with patch('scripts.evaluation.run.load', return_value={'OPENAI_API_KEY':'fixture','OPENAI_MODEL':'fixture'}):
                report = migrate(source,new,root/'partial',provider='openai',preserve_failed=True,
                                 expected_changed={'2'},allow_partial=True)
            self.assertEqual(report, {'reused_count':1,'changed_input_count':1,'remaining':2})
            self.assertIn('context_protocol',read(root/'partial/manifest.json'))

    def test_gold_change_is_reusable_but_input_and_source_changes_are_not(self):
        row = dict(id='one', case_id='case', source='source', query='Q?',
                   image_sha256='abc', query_language='en', image_language='en',
                   answer_language='en', provenance={'row_index': 3}, answer='old')
        self.assertTrue(reusable(row, dict(row, answer='corrected')))
        for change in ({'query':'Changed?'}, {'image_sha256':'changed'},
                       {'source_context':{'paragraphs':['additional document evidence']}},
                       {'provenance':{'row_index':4}}, {'case_id':'another'}):
            self.assertFalse(reusable(row, dict(row, **change)))

    def test_hash_verification_rejects_mutated_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'validation_release').mkdir()
            (root/'image.png').write_bytes(b'original')
            row = {'id':'one', 'image_path':'../image.png',
                   'image_sha256':hashlib.sha256(b'original').hexdigest()}
            verify_images(root, [row])
            (root/'image.png').write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError, 'image_hash_mismatch'):
                verify_images(root, [row])

    def test_judge_starts_after_scoring_complete_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = TokenRouterRunner.__new__(TokenRouterRunner)
            runner.out = Path(tmp)
            runner.args = SimpleNamespace(smoke=False, retry_failed=False, workers=1,
                                          defer_scoring=False, llm_judge=True)
            runner.rows = [{'id':'one'}]
            runner.results = {'one':{'id':'one', 'status':'completed', 'prediction':'1'}}
            runner.attempts = []
            save(runner.out/'manifest.json', {'sessions':[{}]})
            events = []
            with patch('scripts.evaluation.run_token_router.score_run', side_effect=lambda p: events.append('strict')), \
                 patch('scripts.evaluation.judge.run_judge', side_effect=lambda p: events.append('judge')), \
                 patch('scripts.evaluation.lineage.snapshot_run'):
                runner.run()
            self.assertEqual(events, ['strict', 'judge'])
            self.assertEqual(read(runner.out/'progress.json')['state'], 'finished')
