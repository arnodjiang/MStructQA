import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.evaluation.lineage import snapshot_run, pairing_key
from scripts.final_benchmark.api import read, save


class LineageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.dataset, self.run, self.store = root / 'dataset', root / 'run', root / 'archive'
        self.folder = self.dataset / 'cases/case1'
        image = self.folder / 'images/en.png'
        image.parent.mkdir(parents=True)
        image.write_bytes(b'reconstructed-image')
        source_image = self.folder / 'original/original.png'
        source_image.parent.mkdir()
        source_image.write_bytes(b'upstream-image')
        provenance = {'file': 'source.parquet', 'row_index': 8, 'slot': 'qa'}
        source = {'candidate': dict(provenance, id='case1', source='test', question='Original?', answer='OLD', raw_record={}),
                  'identity': {'id': 'case1', 'base_id': 'qa_original', 'source': 'test', 'question': 'Original?',
                               'provenance': provenance, 'fingerprints': {'image_sha256': hashlib.sha256(b'upstream-image').hexdigest()}}}
        save(self.folder / 'source.json', source)
        self.row = {'id': 'variant_1', 'case_id': 'case1', 'base_id': 'qa_original', 'source': 'test',
                    'query': 'Polished?', 'answer': 'corrected', 'query_language': 'en', 'image_language': 'en',
                    'answer_language': 'en', 'image_path': '../cases/case1/images/en.png',
                    'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest()}
        (self.dataset / 'validation_release').mkdir()
        self.run.mkdir()
        self.refs = self.run / 'references.jsonl'
        self.refs.write_text(json.dumps(self.row) + '\n')
        (self.run / 'prompt.txt').write_text('Return an answer.')
        save(self.run / 'manifest.json', {'dataset': str(self.dataset), 'model': 'test-model', 'run_key': 'run1',
                                        'references_sha256': hashlib.sha256(self.refs.read_bytes()).hexdigest()})

    def prediction(self, output):
        save(self.run / 'requests/variant_1.json', {'id': 'variant_1', 'question': self.row['query'], 'image_sha256': self.row['image_sha256']})
        save(self.run / 'attempts/variant_1/001.json', {'id': 'variant_1', 'attempt_number': 1, 'status': 'completed', 'raw_output': output})
        save(self.run / 'responses/variant_1/001.json', {'output': output})
        save(self.run / 'predictions/variant_1.json', {'id': 'variant_1', 'run_key': 'run1', 'status': 'completed', 'prediction': output, 'selected_attempt': 1})

    def test_raw_io_is_immutable_across_later_changes(self):
        self.prediction('first response')
        before_refs = self.refs.read_bytes()
        first = snapshot_run(self.run, self.store)
        first_data = read(first['snapshot']['archive_path'])
        self.prediction('later response')
        second = snapshot_run(self.run, self.store)
        second_data = read(second['snapshot']['archive_path'])
        self.assertNotEqual(first['snapshot']['sha256'], second['snapshot']['sha256'])
        self.assertEqual(read(first['snapshot']['archive_path']), first_data)
        a, b = first_data['samples'][0], second_data['samples'][0]
        self.assertEqual(a['pair_id'], b['pair_id'])
        self.assertNotEqual(a['model_io_id'], b['model_io_id'])
        self.assertEqual(read(a['attempts'][0]['response']['archive_path'])['output'], 'first response')
        self.assertEqual(first_data['source_records'][0]['upstream_answer'], 'OLD')
        self.assertEqual(a['input']['reference_answer'], 'corrected')
        self.assertFalse(a['is_upstream_original_input'])
        self.assertEqual(before_refs, self.refs.read_bytes())

    def test_rejects_wrong_request_and_changed_image(self):
        self.prediction('answer')
        path = self.run / 'requests/variant_1.json'
        request = read(path)
        save(path, dict(request, question='Another sample?'))
        with self.assertRaisesRegex(ValueError, 'request_input_mismatch'):
            snapshot_run(self.run, self.store)
        save(path, request)
        (self.folder / 'images/en.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'evaluation_image_changed'):
            snapshot_run(self.run, self.store)

    def test_missing_source_image_is_not_a_measured_baseline(self):
        (self.folder / 'original/original.png').unlink()
        source = read(self.folder / 'source.json')
        source['identity']['fingerprints']['image_sha256'] = None
        save(self.folder / 'source.json', source)
        report = snapshot_run(self.run, self.store)
        self.assertEqual(report['original_visual_status'], {'requires_faithful_table_rendering': 1})
        self.assertEqual(report['prediction_status'], {'pending': 1})
        self.assertEqual(report['baseline_evaluation_status'], 'not_established_by_this_run')
        self.assertNotEqual(pairing_key(self.row), pairing_key(dict(self.row, query_language='zh')))

    def test_post_judge_refresh_does_not_read_images(self):
        self.prediction('answer')
        snapshot_run(self.run, self.store)
        (self.folder / 'images/en.png').unlink()
        (self.folder / 'original/original.png').unlink()
        save(self.run / 'llm_judge_text_v2/judgments/variant_1.json', {
            'id': 'variant_1', 'prediction': 'answer', 'reference_effective': 'corrected',
            'verdict': 'different'})
        report = snapshot_run(self.run, self.store, frozen_inputs_only=True)
        self.assertEqual(report['judged'], 1)
        self.assertFalse(read(report['snapshot']['archive_path'])['samples'][0]['correct'])

    def test_public_release_runs_without_private_source_archive(self):
        (self.folder / 'source.json').unlink()
        save(self.dataset / 'provenance_index.json', {'cases': {'case1': {
            'case_id': 'case1', 'original_sample_id': 'qa_original', 'source': 'test',
            'source_record_sha256': 'a' * 64}}})
        self.prediction('answer')
        report = snapshot_run(self.run, self.store)
        self.assertEqual(report['original_visual_status'], {'not_in_public_release': 1})
        record = read(report['snapshot']['archive_path'])['source_records'][0]
        self.assertIsNone(record['upstream_answer'])
        self.assertEqual(record['original_sample_id'], 'qa_original')


if __name__ == '__main__':
    unittest.main()
