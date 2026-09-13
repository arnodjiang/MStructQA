"""Portable offline checks: no credentials, network or system fonts required."""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
from openai import APIConnectionError
from scripts.final_benchmark.api import API
from scripts.final_benchmark.languages24 import NEW_LANGUAGES,REPLY
from scripts.final_benchmark.pipeline import LANGUAGES

ROOT=Path(__file__).resolve().parents[1]


class PublicContracts(unittest.TestCase):
    def test_24_language_configuration(self):
        languages=dict(LANGUAGES,**NEW_LANGUAGES)
        self.assertEqual(len(languages),24)
        self.assertEqual(set(REPLY),set(NEW_LANGUAGES))
        configs={(v,q,q) for v in languages for q in {v,'en','zh'}}
        self.assertEqual(len(configs),70)
        self.assertEqual(sum(v==q for v,q,a in configs),24)

    def test_prompt_manifest(self):
        manifest=json.loads((ROOT/'prompts/manifest.json').read_text())
        for name,entry in manifest.items():
            self.assertEqual(hashlib.sha256((ROOT/'prompts'/name).read_bytes()).hexdigest(),entry['sha256'])
        self.assertEqual(len(list((ROOT/'prompts/query').glob('*.txt'))),24)

    def test_transport_retries_and_next_item(self):
        config={'OPENAI_API_KEY':'synthetic-test-key','OPENAI_MODEL':'synthetic-model'}
        ok=SimpleNamespace(id='ok',model='synthetic',status='completed',usage=None,output_text='{"ok":true}')
        error=APIConnectionError(request=httpx.Request('POST','https://example.invalid'))
        with tempfile.TemporaryDirectory() as tmp:
            api=API(tmp,config,True)
            with patch('scripts.final_benchmark.api.create',side_effect=[error]*11+[ok]) as create,patch('scripts.final_benchmark.api.time.sleep') as sleep:
                with self.assertRaisesRegex(RuntimeError,'transport_retries_exhausted'):api.call('test','failed','test',{})
                self.assertEqual(create.call_count,11)
                self.assertEqual(sum(c.args==(5,) for c in sleep.call_args_list),10)
                self.assertTrue(api.call('test','next','test',{})[0]['ok'])
            self.assertEqual(len(list(Path(tmp).glob('api/test/failed/*/attempt_*.json'))),11)

    def test_malformed_response_not_retried(self):
        bad=SimpleNamespace(id='bad',model='synthetic',status='completed',usage=None,output_text='not json')
        with tempfile.TemporaryDirectory() as tmp,patch('scripts.final_benchmark.api.create',return_value=bad) as create:
            with self.assertRaises(RuntimeError):API(tmp,{'OPENAI_API_KEY':'synthetic-test-key','OPENAI_MODEL':'synthetic'},True).call('test','bad','test',{})
            self.assertEqual(create.call_count,1)


if __name__=='__main__':unittest.main()
