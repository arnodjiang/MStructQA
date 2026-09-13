"""Offline behavioral tests: structure, localization, replay and tamper detection."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import visual_harness as harness
import table_renderer
FONT=os.environ.get('MVISQA_FONT','/System/Library/Fonts/Supplemental/Arial Unicode.ttf')


class ContractTests(unittest.TestCase):
    def test_changed_reference_rejected(self):
        source={'labels':{'a':'Name'},'qas':{'q':{'question':'Value of [[a]]?','answer':'5'}}}
        target=copy.deepcopy(source);target['qas']['q']['question']='Value of Name?'
        with self.assertRaises(ValueError):harness.validate_locale(source,target)

    def test_spans_and_ragged_grid(self):
        data=harness.read(ROOT/'examples/table.json')['data'];cells,ncols=table_renderer.geometry(data)
        self.assertEqual(ncols,3);self.assertEqual(cells[2][0:4],(1,1,1,1))
        with self.assertRaises(ValueError):table_renderer.geometry({'rows':[[{'text':'a'},{'text':'b'}],[{'text':'c'}]]})

    def test_prepare_html_preserves_raw_and_numeric_strings(self):
        with tempfile.TemporaryDirectory() as t:
            raw='<table><tr><th rowspan="2">Item</th><th>2002</th></tr><tr><td>03.00</td></tr></table>'
            path=Path(t)/'table.html';path.write_text(raw)
            from argparse import Namespace
            harness.prepare_table(Namespace(input=str(path),output=str(Path(t)/'spec.json'),source_language='en'))
            result=harness.read(Path(t)/'spec.json');self.assertEqual(result['source']['original_raw'],raw)
            self.assertEqual(result['data']['rows'][1][0]['text'],'03.00')
            self.assertNotIn('label_key',result['data']['rows'][1][0])

    def test_scientific_notation_is_not_translated(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'numbers.csv';path.write_text('Value,1e3,-2E-4\n')
            from argparse import Namespace
            harness.prepare_table(Namespace(input=str(path),output=str(Path(t)/'spec.json'),source_language='en'))
            result=harness.read(Path(t)/'spec.json')
            self.assertEqual(result['labels'],{'cell_0_0':'Value'})
            self.assertEqual(result['data']['rows'][0][1]['text'],'1e3')


@unittest.skipUnless(Path(FONT).exists(),'Set MVISQA_FONT to a covering Unicode font')
class RenderingTests(unittest.TestCase):
    def invoke(self,args,ok=True):
        proc=subprocess.run([sys.executable,str(ROOT/'scripts/visual_harness.py')]+args,capture_output=True,text=True)
        if ok:self.assertEqual(proc.returncode,0,proc.stderr)
        else:self.assertNotEqual(proc.returncode,0)
        return proc

    def test_table_localization_replay_and_tamper(self):
        with tempfile.TemporaryDirectory() as t:
            args=['run','--spec',str(ROOT/'examples/table.json'),'--output',t,'--languages','en,zh,ar','--translations',str(ROOT/'examples/table_locales.json'),'--font',FONT]
            self.invoke(args);dest=Path(harness.read(Path(t)/'latest.json')['directory'])
            source=harness.read(dest/'source_spec.json');render=harness.read(dest/'render_spec.json')
            self.assertEqual(source['data']['rows'],render['data']['rows'])
            records=[json.loads(x) for x in (dest/'benchmark.jsonl').read_text().splitlines()]
            self.assertIn('纸尿裤',next(x for x in records if x['visual_language']=='zh')['question'])
            self.assertEqual(len({x['variant_id'] for x in records}),3)
            self.assertTrue(harness.read(dest/'validation.json')['all_languages_share_data'])
            for lang in ('en','zh','ar'):
                layout=harness.read(dest/'images'/(lang+'.layout.json'))
                self.assertTrue(all(x['inside_canvas'] and x['inside_cell'] for x in layout['boxes']))
            export=dest/'code/translated/ar/render.py';standalone=Path(t)/'detached.py';standalone.write_bytes(export.read_bytes());image=Path(t)/'detached.png'
            subprocess.run([sys.executable,str(standalone),'--font',FONT,'--output',str(image)],check=True,capture_output=True)
            self.assertEqual(image.read_bytes(),(dest/'images/ar.png').read_bytes())
            self.invoke(args)
            export.write_text(export.read_text()+'\n# tampered\n');self.invoke(args,ok=False)

    def test_chart_localized_code_has_labels_and_replays(self):
        with tempfile.TemporaryDirectory() as t:
            args=['run','--spec',str(ROOT/'examples/chart.json'),'--output',t,'--languages','en,zh','--translations',str(ROOT/'examples/chart_locales.json'),'--font',FONT]
            self.invoke(args);dest=Path(harness.read(Path(t)/'latest.json')['directory']);code=dest/'code/translated/zh/render.py'
            self.assertIn('单腿机器人：站立',code.read_text());self.assertNotIn('What is the value',code.read_text())
            image=Path(t)/'replayed.png';subprocess.run([sys.executable,str(code),'--font',FONT,'--output',str(image)],check=True,capture_output=True)
            self.assertEqual(image.read_bytes(),(dest/'images/zh.png').read_bytes())
            self.assertTrue((dest/'code/original/en/render.py').exists())


if __name__=='__main__':unittest.main()
