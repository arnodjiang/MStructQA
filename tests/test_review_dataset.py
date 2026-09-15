import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.review_dataset import Dataset, fingerprint


class ReviewDatasetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'validation_release').mkdir()
        (self.root / 'cases/c/locales').mkdir(parents=True)
        (self.root / 'image.png').write_bytes(b'image fixture')
        (self.root / 'render.py').write_text('# fixture')
        for lang in ['en', 'zh']:
            (self.root / ('cases/c/locales/'+lang+'.json')).write_text('{}')
        (self.root / 'selection_lock.json').write_text(json.dumps({'ids':['c'],'languages':['en','zh']}))
        self.rows = [dict(id=v+q, case_id='c',source='fixture',image_language=v,query_language=q,answer_language=q,
                         image_path='../image.png',code_path='../render.py',query='Q',answer='1',
                         image_sha256=hashlib.sha256(b'image fixture').hexdigest(),visual_metadata={'data_sha256':'same'},audit={'status':'accepted'})
                     for v in ['en','zh'] for q in ['en','zh']]
        self.write_rows()

    def write_rows(self):
        (self.root / 'validation_release/val.candidates.jsonl').write_text('\n'.join(json.dumps(r) for r in self.rows))

    def test_complete_and_separate_persistent_review(self):
        d=Dataset(self.root)
        self.assertEqual(d.summary()['issues'],0)
        original=(self.root/'validation_release/val.candidates.jsonl').read_bytes()
        d.save({'id':'enen','fingerprint':fingerprint(self.rows[0]),'verdict':'pass','notes':'checked'})
        self.assertEqual(Dataset(self.root).summary()['reviewed'],1)
        self.assertEqual(original,(self.root/'validation_release/val.candidates.jsonl').read_bytes())

    def test_missing_duplicate_hash_and_escape(self):
        self.rows.pop()
        self.rows.append(dict(self.rows[0]))
        self.rows[0]['image_path']='../../outside.png'
        (self.root/'image.png').write_bytes(b'changed')
        self.write_rows()
        issues='\n'.join(Dataset(self.root).issues['c'])
        for label in ['Missing configuration','Duplicate variant ID','Image hash mismatch','Missing or unsafe image_path']:
            self.assertIn(label,issues)

    def test_stale_annotation_and_reject_conflicting_save(self):
        d=Dataset(self.root)
        d.save({'id':'enen','fingerprint':fingerprint(self.rows[0]),'verdict':'fail'})
        self.rows[0]['query']='Changed question'
        self.write_rows()
        d=Dataset(self.root)
        self.assertTrue(d.review(self.rows[0])['stale'])
        self.assertEqual(d.summary()['reviewed'],0)
        with self.assertRaises(ValueError):
            d.save({'id':'enen','fingerprint':'old','verdict':'pass'})

if __name__=='__main__':
    unittest.main()
