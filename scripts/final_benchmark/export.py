"""Assemble 31 configurations/case, standalone code and reproducibility metadata."""
import argparse
import ast
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import re
import shutil

from .api import digest, now, read, save
from .pipeline import ROOT, DEFAULT_OUT, LANGUAGES, FONT, bind, placeholder_keys

REPLY = {'en': 'Please answer in English.', 'zh': '请用中文回答。',
         'ja': '日本語で回答してください。', 'ko': '한국어로 답해주세요.',
         'fr': 'Veuillez répondre en français.', 'de': 'Bitte antworten Sie auf Deutsch.',
         'es': 'Responde en español.', 'pt': 'Responda em português.',
         'ru': 'Пожалуйста, ответьте на русском языке.', 'ar': 'يرجى الإجابة باللغة العربية.',
         'hi': 'कृपया हिन्दी में उत्तर दें।'}


def numeric_tokens(text):
    return re.findall(r'(?<![0-9A-Za-z])[-+−]?\d+(?:[.,]\d+)*(?:[eE][-+]?\d+)?|\d+(?:[.,]\d+)*(?:[eE][-+]?\d+)?', text)


def same_localized_numbers(original, translated):
    source = numeric_tokens(original)
    target = numeric_tokens(translated)
    if sorted(source) == sorted(target):
        return True
    # East Asian dates conventionally turn English month names into month numbers.
    # Admit only the exact corresponding month; never ignore other changed values.
    months = 'january february march april may june july august september october november december'.split()
    for number, name in enumerate(months, 1):
        if re.search(r'\b' + name + r'\b', original, re.I) and re.search(r'(?<!\d)' + str(number) + r'\s*[月월]', translated):
            return sorted(source + [str(number)]) == sorted(target)
    return False


def localization_issues(original, locale):
    issues = []
    for key, text in original['labels'].items():
        translated = locale['labels'].get(key, '')
        if not same_localized_numbers(text, translated):
            issues.append({'check': 'label_numeric_tokens_changed', 'key': key,
                           'original': text, 'translated': translated})
    buckets = {}
    for key, text in locale['labels'].items():
        buckets.setdefault(text.strip().casefold(), []).append(key)
    for keys in buckets.values():
        if len({original['labels'][key].strip().casefold() for key in keys}) > 1:
            issues.append({'check': 'distinct_labels_collapsed', 'keys': keys})
    if not same_localized_numbers(original['question'], locale['question']):
        issues.append({'check': 'question_numeric_tokens_changed'})
    return issues


def code_prelude():
    helper = (ROOT/'skills/multilingual-visual-benchmark/scripts/multilingual_drawing.py').read_text()
    runtime = (Path(__file__).with_name('render_runtime.py')).read_text()
    tree = ast.parse(runtime)
    runtime = '\n\n'.join(ast.get_source_segment(runtime, n) for n in tree.body
                           if not (isinstance(n, ast.FunctionDef) and n.name == 'validate_code'))
    return '''# Reconstructed Python snapshot, not upstream author's original plotting code.
# No API calls; frozen numeric data and language literals embedded below.
import argparse, json, os
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--output',required=True)
parser.add_argument('--font',default='/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
args=parser.parse_args()
os.environ['MVISQA_FONT']=args.font
os.environ.setdefault('MPLCONFIGDIR',str(Path(args.output).resolve().parent/'.matplotlib_cache'))
''' + helper + '\n' + runtime + '\n'


def emit_code(folder, spec, language, locale, prelude):
    category = 'original' if language == 'en' else 'translated'
    code = prelude + '\n' + spec['python_code'] + '\n'
    code += '\nBASE_ID = ' + repr(spec['base_id']) + '\nLANGUAGE = ' + repr(language)
    code += '\nDATA = ' + repr(spec['data']) + '\nLABELS = ' + repr(locale['labels'])
    code += '''
image, boxes = render(DATA, LABELS)
output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)
image.save(output, optimize=True)
output.with_suffix('.layout.json').write_text(json.dumps({'boxes':boxes,'missing_glyphs':sorted(set(MISSING_GLYPHS))},ensure_ascii=False,indent=2))
'''
    compile(code, '<standalone_snapshot>', 'exec')
    path = folder/'code'/category/language/'render.py'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() != code:
        historic = path.with_name('render.' + hashlib.sha256(path.read_bytes()).hexdigest()[:12] + '.py')
        if not historic.exists():
            shutil.copy2(path, historic)
    path.write_text(code)
    return path


def assemble(out, partial=False):
    out = Path(out)
    sources = [json.loads(x) for x in (out/'source/candidates.jsonl').read_text().splitlines()]
    identities = {r['id']: r for r in map(json.loads, (out/'source/selected_reserve_identity.jsonl').read_text().splitlines())}
    records, images, cases, missing, localization = [], [], [], [], []
    prelude = code_prelude()
    diversity = Counter()
    for source in sources:
        identifier = source['id']
        folder = out/'cases'/identifier
        if not (folder/'render_complete.json').exists():
            missing.append(identifier)
            continue
        identity = identities[identifier]
        spec, qa = read(folder/'render_spec.json'), read(folder/'qa.json')
        locales = {lang: read(folder/'locales'/(lang+'.json')) for lang in LANGUAGES}
        locale_checks = {lang: localization_issues(locales['en'], locales[lang]) for lang in LANGUAGES}
        localization.extend({'id': identifier, 'language': lang, 'issues': issues}
                            for lang, issues in locale_checks.items() if issues)
        review = read(folder/'review.json') if (folder/'review.json').exists() else {'status': 'pending'}
        if review.get('status') != 'pending' and review.get('spec_sha256') != digest(read(folder/'spec.json')):
            review = dict(review, status='stale', previous_status=review.get('status'))
        case_flags = list(qa.get('review_flags', []))
        if review.get('status') != 'pass':
            case_flags.append('visual_answer_review_' + review.get('status', 'pending'))
        # Original source groups are preserved; variants must never cross data splits.
        split_group = identity.get('dedup_group_keys') or [identity['base_id']]
        original = next(iter(sorted((folder/'original').glob('original.*'))), None)
        info = {'id': identifier, 'base_id': identity['base_id'], 'source': source['source'],
                'kind': spec['kind'], 'original': str(original.relative_to(out)) if original else None,
                'task_tags': identity['features']['inferred']['task_tags'],
                'api_task_tags': qa.get('task_tags', []), 'recovery': spec.get('recovery'),
                'review': review, 'qa_flags': case_flags, 'provenance': identity['provenance']}
        cases.append(info)
        for token in identity.get('diversity_tokens', []):
            diversity[token] += 1
        for language in LANGUAGES:
            image = folder/'images'/(language+'.png')
            layout = read(image.with_suffix('.layout.json'))
            code = emit_code(folder, spec, language, locales[language], prelude)
            entry = {'id': identifier, 'base_id': identity['base_id'], 'visual_language': language,
                     'image': str(image.relative_to(out)), 'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
                     'code': str(code.relative_to(out)), 'code_sha256': hashlib.sha256(code.read_bytes()).hexdigest(),
                     'data_sha256': digest(spec['data']), 'labels_sha256': digest(locales[language]['labels']),
                     'width': layout['width'], 'height': layout['height'],
                     'text_inside_canvas': layout['all_text_inside_canvas'],
                     'text_inside_cells': layout['all_text_inside_cells'], 'missing_glyphs': layout['missing_glyphs']}
            images.append(entry)
            for qlang in sorted({language, 'zh', 'en'}):
                locale = locales[qlang]
                question = bind(locale['question'], locale['labels'])
                answer = bind(locale['answer_template'], locale['labels'])
                qflags = list(case_flags)
                for lang in sorted({language, qlang}):
                    if locale_checks[lang]:
                        qflags.append('localization_check_' + lang)
                if qa.get('answer_type') == 'numeric' and numeric_tokens(answer) != numeric_tokens(qa['answer']):
                    qflags.append('numeric_answer_translation_difference')
                record = {'variant_id': 'variant_' + digest([identity['base_id'], language, qlang, qlang]),
                          'base_id': identity['base_id'], 'id': identifier, 'source': source['source'],
                          'visual_language': language, 'query_language': qlang, 'answer_language': qlang,
                          'configuration': 'monolingual' if language == qlang else 'cross_' + qlang,
                          'image': entry['image'], 'image_sha256': entry['image_sha256'],
                          'question': question + '\n' + REPLY[qlang], 'question_without_instruction': question,
                          'answer': answer, 'answer_type': qa.get('answer_type'),
                          'source_question': source['question'], 'source_answer': source['answer'],
                          'canonical_answer_en': qa['answer'],
                          'reference_label_keys': placeholder_keys(locale['question']),
                          'task_tags': info['task_tags'], 'api_task_tags': info['api_task_tags'],
                          'stratum': source['stratum'], 'split_group_keys': split_group,
                          'provenance': identity['provenance'], 'code': entry['code'],
                          'data_sha256': entry['data_sha256'],
                          'status': 'api_reviewed_candidate' if not qflags else 'needs_review', 'review_flags': qflags}
                records.append(record)
    expected = len(cases) * (3*len(LANGUAGES)-2)
    if len(records) != expected or len({r['variant_id'] for r in records}) != expected:
        raise ValueError('configuration_count_or_id_failure')
    if missing and not partial:
        raise ValueError('Incomplete cases: ' + ','.join(missing))
    for r in records:
        assert r['answer_language'] == r['query_language']
        assert '[[' not in r['question'] and '[[' not in r['answer']
        assert r['question'].endswith(REPLY[r['answer_language']])
    save(out/'image_manifest.json', images)
    save(out/'case_manifest.json', cases)
    save(out/'localization_checks.json', localization)
    name = 'benchmark.partial.jsonl' if missing else 'benchmark.jsonl'
    (out/name).write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in records))
    candidate_pass = [r for r in records if r['status'] == 'api_reviewed_candidate']
    (out/'benchmark.api_reviewed.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in candidate_pass))
    summary = {'generated_at': now(), 'base_cases': len(cases), 'images': len(images), 'samples': len(records),
               'expected_base_cases': len(sources), 'expected_images': len(sources)*len(LANGUAGES), 'expected_samples': len(sources)*(3*len(LANGUAGES)-2), 'missing_cases': missing,
               'configuration_counts': dict(Counter(r['configuration'] for r in records)),
               'source_counts_base': dict(Counter(c['source'] for c in cases)),
               'source_counts_samples': dict(Counter(r['source'] for r in records)),
               'status_counts': dict(Counter(r['status'] for r in records)),
               'source_diversity_coverage': dict(diversity),
               'all_codes_exported': len(images) == len(list((out/'cases').glob('*/code/*/*/render.py'))),
               'all_text_inside_canvas': all(i['text_inside_canvas'] for i in images),
               'all_text_inside_cells': all(i['text_inside_cells'] for i in images),
               'all_language_data_hashes_identical': all(len({i['data_sha256'] for i in images if i['id']==c['id']}) == 1 for c in cases),
               'missing_glyphs': sorted({s for i in images for s in i['missing_glyphs']}),
               'human_semantic_review': 'not_performed', 'font_sha256': hashlib.sha256(Path(FONT).read_bytes()).hexdigest()}
    save(out/'validation.json', summary)
    save(out/'diversity_report.json', {'frozen_original': read(out/'source/diversity_coverage.json'), 'constructed_coverage': dict(diversity),
                                      'selection_changes': [], 'task_labels_are_inferred_not_human_verified': True})
    gallery(out, cases, records, summary)
    return summary


def gallery(out, cases, records, summary):
    payload = json.dumps({'cases': cases, 'records': [{k:r[k] for k in ('id','visual_language','query_language','question','answer','image','code','status')} for r in records],
                          'languages': LANGUAGES, 'summary': summary}, ensure_ascii=False).replace('</', '<\\/')
    document = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MVisQA 128 · Multilingual Benchmark</title><style>
body{margin:0;background:#f0f3ee;color:#21362c;font:16px system-ui}header{background:#173d32;color:white;padding:30px 4vw}header p{max-width:1100px;line-height:1.6}a{color:#287857}header a{color:#c7ecd7}.controls{padding:18px 4vw;background:#fff;position:sticky;top:0;display:flex;gap:20px;flex-wrap:wrap}select{font:inherit;padding:6px}main{margin:25px 4vw}article{background:white;padding:22px;border-radius:12px;margin-bottom:20px}.qa{padding:18px;background:#edf5ed;white-space:pre-wrap;line-height:1.65}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.grid img{width:100%;height:auto}code{overflow-wrap:anywhere;font-size:12px}.note{color:#916222;font-size:14px}details img{max-width:100%}@media(max-width:800px){.grid{grid-template-columns:1fr}}
</style><header><h1>MVisQA · 128 条候选的多语言变体</h1><p id="stats"></p><p>英文/中文问题跨 11 种图像语言，以及 11 种同语问答；回答语言与问题语言一致。同一个原题共有31个去重配置。API 重建和复核仍可能出错，审核状态随每条样本保留。</p><a href="benchmark.jsonl">完整 JSONL</a> · <a href="validation.json">验证报告</a> · <a href="diversity_report.json">多样性报告</a> · <a href="README.md">复现说明</a></header><div class="controls"><label>图像语言 <select id="lang"></select></label><label>问题语言 <select id="query"><option value="same">跟随图像</option><option value="zh">中文</option><option value="en">English</option></select></label><label>来源 <select id="source"><option value="all">全部</option></select></label><label>案例 <select id="case"></select></label></div><main id="content"></main><script>const D=__DATA__;const $=s=>document.querySelector(s);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
$('#stats').textContent=`已生成 ${D.summary.base_cases}/128 个原题 · ${D.summary.images}/1408 张图像 · ${D.summary.samples}/3968 条样本`;
$('#lang').innerHTML=Object.entries(D.languages).map(([k,v])=>`<option value="${k}">${v} (${k})</option>`).join('');$('#lang').value='zh';$('#source').innerHTML+=[...new Set(D.cases.map(c=>c.source))].map(s=>`<option>${s}</option>`).join('');
function choices(){const old=$('#case').value;$('#case').innerHTML=D.cases.filter(c=>$('#source').value==='all'||c.source===$('#source').value).map(c=>`<option value="${c.id}">${D.cases.indexOf(c)+1}. ${c.source} · ${c.id}</option>`).join('');if([...$('#case').options].some(x=>x.value===old))$('#case').value=old;draw()}
function draw(){const c=D.cases.find(x=>x.id===$('#case').value);if(!c){$('#content').textContent='当前筛选没有完成的案例';return}const l=$('#lang').value,q=$('#query').value==='same'?l:$('#query').value;const r=D.records.find(x=>x.id===c.id&&x.visual_language===l&&x.query_language===q);$('#content').innerHTML=`<article><h2>${esc(c.source)} · ${esc(c.kind)}</h2><code>${c.base_id}</code><p>${esc(c.task_tags.join(' / '))}</p><div class="qa" dir="${q==='ar'?'rtl':'ltr'}">Q: ${esc(r.question)}\nA: ${esc(r.answer)}</div><p class="note">状态：${esc(r.status)} · ${esc(JSON.stringify(c.review))}</p><div class="grid"><div><h3>英文重绘基线</h3><a href="cases/${c.id}/images/en.png"><img src="cases/${c.id}/images/en.png"></a></div><div><h3>${esc(D.languages[l])}</h3><a href="${r.image}"><img src="${r.image}"></a></div></div><p><a href="${r.code}">当前语言 Python 代码</a> · <a href="cases/${c.id}/code/original/en/render.py">英文 Python 代码</a> · <a href="cases/${c.id}/spec.json">恢复规格</a> · <a href="cases/${c.id}/qa.json">答案规范化记录</a></p><details><summary>原始输入与来源</summary>${c.original&&/\\.(png|jpg|jpeg)$/.test(c.original)?`<img src="${c.original}">`:''}<pre>${esc(JSON.stringify(c.provenance,null,2))}</pre></details></article>`}
$('#source').addEventListener('change',choices);['#lang','#query','#case'].forEach(x=>$(x).addEventListener('change',draw));choices();</script>'''.replace('__DATA__', payload)
    if summary['missing_cases']:
        document = document.replace('href="benchmark.jsonl">完整 JSONL', 'href="benchmark.partial.jsonl">已完成部分 JSONL')
    (out/'index.html').write_text(document)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', default=str(DEFAULT_OUT))
    p.add_argument('--partial', action='store_true')
    args = p.parse_args()
    result = assemble(args.output, args.partial)
    print(json.dumps({k:result[k] for k in ('base_cases','images','samples','status_counts')}, ensure_ascii=False))
