import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.final_benchmark.api import save
from scripts.final_benchmark.clean_release import clean_reference, copy_current, write_current_views, verify_clean
from scripts.evaluation.lineage import source_record, Archive


class CleanReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source, self.target, self.store = root/'old', root/'latest', root/'external_archive'
        folder = self.source/'cases/case1'
        image = folder/'images/en.png'; image.parent.mkdir(parents=True); image.write_bytes(b'current-image')
        original = folder/'original/original.png'; original.parent.mkdir(); original.write_bytes(b'original-image')
        code = folder/'code/original/en/render.py'; code.parent.mkdir(parents=True); code.write_text('def render(): pass\n')
        provenance = {'file':'data.parquet', 'row_index':1, 'slot':'qa'}
        save(folder/'source.json', {'candidate':dict(provenance, id='case1', source='test', question='OLD UPSTREAM QUESTION', answer='OLD LABEL', raw_record={}),
             'identity':{'id':'case1', 'base_id':'qa_case1', 'source':'test', 'question':'OLD UPSTREAM QUESTION',
                         'provenance':provenance, 'fingerprints':{'image_sha256':hashlib.sha256(b'original-image').hexdigest()}}})
        save(folder/'before_reference_correction/qa.json', {'question':'OLD QUESTION'})
        save(self.source/'benchmark.partial.jsonl', {'question':'OLD PARTIAL'})
        save(self.source/'source/query_polish/old.json', {'question':'OLD DRAFT'})
        self.row = {'id':'variant_1', 'base_id':'qa_case1', 'case_id':'case1', 'source':'test', 'visual_kind':'chart',
                    'query':'Current question?', 'answer':'1', 'original_query':'OLD UPSTREAM QUESTION', 'original_answer':'OLD LABEL',
                    'image_language':'en', 'query_language':'en', 'answer_language':'en', 'provenance':provenance,
                    'image_path':'../cases/case1/images/en.png', 'image_sha256':hashlib.sha256(b'current-image').hexdigest(),
                    'code_path':'../cases/case1/code/original/en/render.py',
                    'audit':{'status':'accepted', 'review_path':'old_review.json', 'critical_issues':['OLD ISSUE']}}

    def export(self):
        with patch('scripts.evaluation.lineage.DEFAULT_STORE', self.store):
            copy_current(self.source, self.target, [self.row])
        write_current_views(self.target, [clean_reference(self.row)])

    def test_only_current_qa_is_exported_and_original_is_external(self):
        self.export()
        self.assertEqual(verify_clean(self.target)['historical_question_fields'], 0)
        self.assertFalse((self.target/'cases/case1/source.json').exists())
        self.assertFalse((self.target/'cases/case1/original').exists())
        self.assertFalse((self.target/'benchmark.partial.jsonl').exists())
        self.assertFalse((self.target/'source').exists())
        for p in self.target.rglob('*'):
            if p.is_file(): self.assertNotIn(b'OLD UPSTREAM QUESTION', p.read_bytes())
        archived = source_record(self.target, clean_reference(self.row), Archive(self.store))
        self.assertEqual(archived['upstream_question'], 'OLD UPSTREAM QUESTION')
        self.assertEqual(archived['original_sample_id'], 'qa_case1')

    def test_gate_rejects_extra_history_or_changed_current_view(self):
        self.export()
        path = self.target/'benchmark.partial.jsonl'; path.write_text('{"query":"old"}\n')
        with self.assertRaisesRegex(ValueError, 'unexpected_release_file'): verify_clean(self.target)
        path.unlink()
        (self.target/'benchmark.jsonl').write_text('{}\n')
        with self.assertRaisesRegex(ValueError, 'view_mismatch'): verify_clean(self.target)

    def test_old_nested_qa_is_rejected(self):
        self.export()
        save(self.target/'context_revision.json', {'unexpected': {'original_query':'old'}})
        with self.assertRaisesRegex(ValueError, 'historical_content'): verify_clean(self.target)

    def test_stale_subset_is_rejected_even_with_valid_field_names(self):
        self.export()
        (self.target/'validation_release/val.jsonl').write_text('{"id":"old","query":"Old question?"}\n')
        with self.assertRaisesRegex(ValueError, 'stale_current_subset_view'): verify_clean(self.target)


if __name__ == '__main__': unittest.main()
