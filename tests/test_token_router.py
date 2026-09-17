import unittest
from unittest.mock import patch
from scripts.evaluation.token_router import endpoint,normalize_usage,answer_text,request_body,load_config
from scripts.evaluation.run_token_router import smoke_rows


class TokenRouterTests(unittest.TestCase):
    def test_endpoint_variants(self):
        expected='https://api.tokenrouter.com/v1beta/models/google/gemini-3.8-flash:generateContent'
        for suffix in ['', '/v1', '/v1/', '/v1beta', '/v1beta/models']:
            self.assertEqual(endpoint('https://api.tokenrouter.com'+suffix),expected)
        for url in ['http://api.tokenrouter.com/v1','https://key@api.tokenrouter.com/v1','https://api.tokenrouter.com/v1?key=x']:
            with self.assertRaises(ValueError):endpoint(url)

    def test_isolated_credentials(self):
        env={'TOKEN_ROUTER_API_KEY':'router','TOKEN_ROUTER_BASE_URL':'https://example.com/v1',
             'OPENAI_API_KEY':'wrong-key','OPENAI_BASE_URL':'https://wrong.example'}
        with patch('scripts.evaluation.token_router.dotenv_values',return_value=env),patch.dict('os.environ',{},clear=True):
            c=load_config('/unused')
        self.assertEqual(set(c),{'TOKEN_ROUTER_API_KEY','TOKEN_ROUTER_BASE_URL'})
        self.assertEqual(c['TOKEN_ROUTER_API_KEY'],'router')

    def test_image_question_schema(self):
        b=request_body('system','exact query',b'image')
        self.assertEqual(b['contents'][0]['parts'][0],{'text':'exact query'})
        self.assertEqual(b['contents'][0]['parts'][1]['inlineData']['data'],'aW1hZ2U=')
        self.assertEqual(b['generationConfig']['responseMimeType'],'application/json')
        self.assertNotIn('reference',str(b))

    def test_finish_and_thought_filter(self):
        data={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'reasoning','thought':True},{'text':'{"answer":"1"}'}]}}]}
        self.assertEqual(answer_text(data),'{"answer":"1"}')
        data['candidates'][0]['finishReason']='MAX_TOKENS'
        with self.assertRaises(ValueError):answer_text(data)
        with self.assertRaises(ValueError):answer_text({'promptFeedback':{'blockReason':'SAFETY'}})

    def test_token_accounting(self):
        u=normalize_usage({'promptTokenCount':100,'candidatesTokenCount':10,'thoughtsTokenCount':50,'totalTokenCount':160})
        self.assertEqual(u['output_tokens'],60)
        self.assertEqual(u['total_tokens'],160)
        self.assertIsNone(u['input_tokens_details']['cached_tokens'])
        u=normalize_usage({'promptTokenCount':100,'candidatesTokenCount':10,'totalTokenCount':160})
        self.assertEqual(u['output_tokens'],60)
        self.assertIsNone(u['output_tokens_details']['reasoning_tokens'])
        self.assertIsNone(normalize_usage({}))

    def test_distinct_smoke_visuals(self):
        rows=[dict(id='chart-en',visual_kind='chart',image_language='en',query_language='en'),
              dict(id='chart-zh',visual_kind='chart',image_language='zh',query_language='zh'),
              dict(id='table-zh',visual_kind='table',image_language='zh',query_language='zh')]
        self.assertEqual([r['id'] for r in smoke_rows(rows)],['chart-en','table-zh'])


class DeferredScoringTests(unittest.TestCase):
    def test_completed_inference_can_defer_scoring(self):
        import json
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from scripts.evaluation.run_token_router import TokenRouterRunner
        with tempfile.TemporaryDirectory() as tmp:
            runner=TokenRouterRunner.__new__(TokenRouterRunner)
            runner.out=Path(tmp)
            runner.args=SimpleNamespace(smoke=False,retry_failed=False,workers=1,defer_scoring=True)
            runner.rows=[{'id':'fixture'}]
            runner.results={'fixture':{'id':'fixture','status':'completed','prediction':'1'}}
            runner.attempts=[]
            (runner.out/'manifest.json').write_text(json.dumps({'sessions':[{}]}))
            with patch('scripts.evaluation.run_token_router.score_run') as scorer, patch('scripts.evaluation.lineage.snapshot_run'):
                runner.run()
                scorer.assert_not_called()
            self.assertTrue((runner.out/'predictions.jsonl').exists())
            progress=json.loads((runner.out/'progress.json').read_text())
            self.assertEqual(progress['state'],'inference_finished_scoring_deferred')


class QuotaStopTests(unittest.TestCase):
    def test_quota_vs_transient_rate_limit(self):
        from scripts.evaluation.token_router import quota_exhausted
        for payload in [{'error':{'code':'insufficient_user_quota'}},
                        {'error':{'code':'insufficient_quota'}},
                        {'error':{'message':"User's credit limit is insufficient"}},
                        {'message':'Your account quota is running low ($0.00)'}]:
            self.assertTrue(quota_exhausted(payload))
        self.assertFalse(quota_exhausted({'error':{'code':'rate_limit_exceeded','message':'Too many requests'}}))
        self.assertFalse(quota_exhausted({'candidates':[{'content':{'parts':[{'text':'insufficient credit'}]}}]}))

    def test_quota_stops_without_retry(self):
        import hashlib
        import json
        import tempfile
        import threading
        from pathlib import Path
        from types import SimpleNamespace
        import httpx
        from scripts.evaluation.run_token_router import TokenRouterRunner
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'validation_release').mkdir();(root/'image.png').write_bytes(b'fixture')
            runner=TokenRouterRunner.__new__(TokenRouterRunner)
            runner.out=root/'run';runner.out.mkdir()
            runner.source=root/'validation_release/val.candidates.jsonl'
            runner.args=SimpleNamespace(dataset=root,model='google/gemini-3.8-flash',temperature=.7,max_output_tokens=8192,request_interval=0,timeout=1)
            runner.prompt='test';runner.identity={'prompt_sha256':'p'};runner.run_key='r'
            runner.config={'TOKEN_ROUTER_API_KEY':'fixture'};runner.url='https://example.com/model'
            runner.rows=[{'id':'one'}];runner.results={};runner.attempts=[]
            runner.abort=threading.Event();runner.abort_reason=None
            runner.mutex=threading.Lock();runner.rate=threading.Lock();runner.last_start=0
            (runner.out/'manifest.json').write_text(json.dumps({'sessions':[{}]}))
            row={'id':'one','query':'Q','image_path':'../image.png','image_sha256':hashlib.sha256(b'fixture').hexdigest()}
            response=httpx.Response(429,json={'error':{'code':'insufficient_quota'}},request=httpx.Request('POST',runner.url))
            with patch('scripts.evaluation.run_token_router.httpx.Client') as client:
                client.return_value.__enter__.return_value.post.return_value=response
                runner.evaluate(row)
                runner.evaluate(dict(row,id='two'))
                self.assertEqual(client.return_value.__enter__.return_value.post.call_count,1)
            self.assertTrue(runner.abort.is_set())
            self.assertEqual(runner.abort_reason,'quota_exhausted')
            self.assertFalse(runner.attempts[0]['retryable'])
            self.assertEqual(json.loads((runner.out/'progress.json').read_text())['state'],'quota_exhausted')
            runner.args.smoke=False;runner.args.retry_failed=False;runner.args.workers=1;runner.args.defer_scoring=True
            with patch('scripts.evaluation.run_token_router.score_run') as scorer, patch('scripts.evaluation.lineage.snapshot_run'):
                with self.assertRaises(SystemExit) as error:runner.run()
                self.assertEqual(error.exception.code,3)
                scorer.assert_not_called()
