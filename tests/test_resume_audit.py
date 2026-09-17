import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.evaluation.audit_resume import audit
from scripts.final_benchmark.api import digest, save


class ResumeAuditTests(unittest.TestCase):
    def test_explicit_retry_can_recover_rate_limited_plain_request_only(self):
        from scripts.evaluation.run_token_router import resume_answer_mode
        attempt = {'attempt_number': 2, 'answer_mode': 'plain', 'status': 'failed', 'http_status': 429}
        self.assertIsNone(resume_answer_mode([attempt]))
        self.assertEqual(resume_answer_mode([attempt], True), 'plain')
        self.assertIsNone(resume_answer_mode([dict(attempt, http_status=200)], True))
        self.assertIsNone(resume_answer_mode([dict(attempt, raw_output='answer')], True))

    def test_stale_request_is_rejected_even_with_current_reference_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / 'run'; dataset = Path(tmp) / 'dataset'
            (dataset / 'validation_release').mkdir(parents=True)
            run.mkdir()
            row = {'id': 'one', 'query': 'Current question?', 'image_sha256': 'image'}
            raw = (json.dumps(row) + '\n').encode()
            (dataset / 'validation_release/val.candidates.jsonl').write_bytes(raw)
            (run / 'references.jsonl').write_bytes(raw)
            (run / 'prompt.txt').write_text('Prompt')
            save(run / 'manifest.json', {'dataset': str(dataset), 'run_key': 'key',
                 'references_sha256': hashlib.sha256(raw).hexdigest(),
                 'prompt_sha256': digest('Prompt'), 'model': 'model'})
            save(run / 'migration.json', {'changed_input_ids': ['one']})
            save(run / 'predictions/one.json', {'id': 'one', 'run_key': 'key', 'status': 'failed'})
            request = {'id': 'one', 'run_key': 'key', 'model': 'model',
                       'question': 'Old question?', 'image_sha256': 'image',
                       'prompt_sha256': digest('Prompt')}
            save(run / 'requests/one.json', request)
            with patch('scripts.evaluation.audit_resume.verify_clean'), patch('scripts.evaluation.audit_resume.verify_images'):
                with self.assertRaisesRegex(ValueError, 'Stale request'):
                    audit(run)
                request['question'] = row['query']
                save(run / 'requests/one.json', request)
                self.assertEqual(audit(run)['stale_predictions'], 0)
                request['input_text'] = 'Old extra context'
                save(run / 'requests/one.json', request)
                with self.assertRaisesRegex(ValueError, 'Stale request'):
                    audit(run)
