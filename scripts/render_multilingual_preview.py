"""Render the 5 x 11 translation run, preserving originals and language metadata."""
import base64
import hashlib
import json
import mimetypes
import re
from collections import Counter

from render_translation_preview import CSS
from translate_multilingual_pilot import OUT, ROOT, SOURCE


def numbers(text):
    return Counter(re.findall(r'[-+−]?\d[\d,]*(?:\.\d+)?', text))


def audit(case, result):
    if result['status'] != 'completed':
        return {'passed':False, 'checks':{}, 'review_notes':['API 调用或输出解析失败。']}
    t = result['translation']
    checks = {
        'question_numeric_tokens_preserved':numbers(case['question_en'])==numbers(t['question']),
        'answer_numeric_tokens_preserved':numbers(case['answer_en'])==numbers(t['answer']),
        'table_text_ids_preserved':set(t['table_texts'])==set(case['table']['texts']),
        'table_text_numeric_tokens_preserved':all(numbers(v)==numbers(t['table_texts'].get(k,'')) for k,v in case['table']['texts'].items()),
        'base_id_preserved':case['base_id']==result['base_id'],
    }
    if result['language']=='en':
        checks['english_exact_identity'] = (t['question']==case['question_en'] and t['answer']==case['answer_en'] and t['table_texts']==case['table']['texts'])
    notes = []
    if not all(checks.values()):
        notes.append('自动检查发现差异；请展开检查详情。数值变化不一定意味着语义错误，也可能是表示方式变化。')
    if result['language']=='ko' and case['id']=='2807106cc9f8feac0ee1' and '10년대' in t['question']:
        notes.append('具体差异：韩语将 decades 写作 10년대（十年期），增加了一个数字 10；人口阈值仍为 10백만。此处属于表述方式差异，保留模型输出待语言复核。')
    if result['language']=='zh' and '10百万' in t['question']:
        notes.append('表达提示：为保持原始数字标记，模型写作“10百万”；中文通常写“一千万”。数值量级不变，但后续宜统一数量单位的本地化规则。')
    if re.search(r'\b([A-Za-z][A-Za-z -]*)\s*[（(]\1[）)]',t['question']):
        notes.append('可能存在重复的英文标签括注，需复核语言表达。')
    return {'passed':all(checks.values()), 'checks':checks,'review_notes':notes,
            'semantic_review':'not_independently_verified',
            'table_geometry':'source structure reused; no model-generated row/col changes'}


EXTRA_CSS = '''
.langbar{position:sticky;top:0;z-index:5;background:#f4f3eef5;backdrop-filter:blur(12px);padding:14px 0;border-bottom:1px solid var(--line);display:flex;gap:15px;align-items:center;flex-wrap:wrap}.langbar label{font-weight:650;font-size:13px}.langbar select{font:inherit;background:white;color:var(--green);padding:10px 38px 10px 12px;border:1px solid #b6cbbb;border-radius:9px;min-width:190px}.langhint{font-size:12px;color:var(--muted)}.qa-box[dir=rtl]{text-align:right}.term{unicode-bidi:plaintext}.warn{background:#fff2d7;color:#886111}.stats{flex-wrap:wrap}.question{overflow-wrap:anywhere}.language{letter-spacing:1px}.card-controls{display:flex;align-items:center;gap:12px}.note-label{font-size:11px;color:var(--muted)}.table-scroll{direction:ltr}td[dir=rtl],th[dir=rtl]{text-align:right}bdi{unicode-bidi:isolate}article{scroll-margin-top:95px}.run-notice{font-size:12px;color:var(--muted)}@media(max-width:720px){.langbar{gap:8px}.langhint{width:100%}.stats{gap:20px}.card-head{flex-wrap:wrap}}
'''


def main():
    cases = json.loads((OUT/'source_cases.json').read_text())
    results = json.loads((OUT/'translations.json').read_text())
    languages = json.loads((OUT/'languages.json').read_text())
    summary = json.loads((OUT/'run_summary.json').read_text())
    assert len(results)==55 and len({r['variant_id'] for r in results})==55
    assert len(list((OUT/'results').glob('*/*.attempt.json')))==55
    index = {c['id']:c for c in cases}
    audits = []
    for result in results:
        result['audit'] = audit(index[result['id']], result)
        audits.append({'id':result['id'],'language':result['language'],'variant_id':result['variant_id'],**result['audit']})
    passed = sum(a['passed'] for a in audits)
    (OUT/'validation.json').write_text(json.dumps({'expected':55,'automatic_checks_passed':passed,
        'automatic_checks_flagged':55-passed,'semantic_review':'not independently verified for all eleven languages',
        'cases':audits},ensure_ascii=False,indent=2))
    images = {}
    for case in cases:
        if case['original_image']:
            path=ROOT/case['original_image']
            images[case['id']]='data:'+(mimetypes.guess_type(path)[0] or 'image/png')+';base64,'+base64.b64encode(path.read_bytes()).decode()
    display_results = [{k:r[k] for k in ['id','variant_id','language','direction','status','audit','translation'] if k in r} for r in results]
    data = json.dumps({'cases':cases,'results':display_results,'languages':languages,'images':images},ensure_ascii=False).replace('</','<\\/')
    layout = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MVisQA · 11 语言翻译对照</title><style>__CSS__</style></head><body>
<aside><div class="brand">MVisQA<small>TRANSLATION LAB</small></div><nav id="navigation"></nav><div class="sidefoot">5 CASES × 11 LANGUAGES<br>55 独立 API 调用<br>多语言文字试译 · V1</div></aside>
<main><header><div class="eyebrow">MULTILINGUAL BENCHMARK / PILOT 02</div><h1>五道题，十一种语言。</h1><p>切换语言，对照同一份原始图表与问答。表格文字随语言切换，数值、行列和合并单元格沿用原始结构。</p></header>
<div class="stats"><div class="stat"><strong>05</strong><span>原始案例</span></div><div class="stat"><strong>11</strong><span>目标语言</span></div><div class="stat"><strong>__SUCCESS__ / 55</strong><span>成功调用</span></div><div class="stat"><strong>__PASSED__ / 55</strong><span>自动检查通过</span></div></div>
<div class="notice">本次为文字翻译预览，图像内文字仍为英文。两张表格提供译文；英文版本单独调用并作原文保持检查。所有原始材料和旧版中文试译均保留。</div>
<div class="langbar"><label for="language">查看语言</label><select id="language" aria-label="查看语言"></select><span class="langhint" id="language-hint"></span></div>
<div class="toolbar" id="filters" role="group" aria-label="按来源筛选"></div><div id="cards"></div>
<footer>模型：__MODEL__ · 共 __TOKENS__ 个 API 报告 token · 翻译语义尚未完成 11 种语言的独立复核。<br>图像内嵌，页面支持离线打开；原题 base_id 不变，每个语言配置有独立 variant_id。</footer></main>
<dialog id="zoom"><button class="close" aria-label="关闭大图">×</button><img alt="放大的原始图像"></dialog>
<script id="payload" type="application/json">__DATA__</script><script>
const DATA=JSON.parse(document.getElementById('payload').textContent);
const escapeHTML=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let activeLanguage='zh',activeSource='all';
const languageSelect=document.getElementById('language');
languageSelect.innerHTML=DATA.languages.map(l=>`<option value="${l.code}">${escapeHTML(l.label)} · ${l.code.toUpperCase()}</option>`).join('');
document.getElementById('navigation').innerHTML=DATA.cases.map((c,i)=>`<a href="#case-${i+1}" data-nav="${i+1}"><span>CASE 0${i+1}</span><b>${escapeHTML(c.source)}</b></a>`).join('');
const sourceList=['all',...new Set(DATA.cases.map(c=>c.source))];
document.getElementById('filters').innerHTML=sourceList.map(s=>`<button class="filter ${s==='all'?'active':''}" data-source="${escapeHTML(s)}">${s==='all'?'全部 5 条':escapeHTML(s)}</button>`).join('');
function renderTable(c,texts,dir){return '<div class="table-scroll"><table>'+c.table.rows.map((row,i)=>'<tr>'+row.map(cell=>{const tag=i===0?'th':'td';const text=cell.text_id&&texts?texts[cell.text_id]:cell.text;return `<${tag} colspan="${cell.colspan}" rowspan="${cell.rowspan}" dir="${cell.text_id?dir:'ltr'}">${cell.text_id?escapeHTML(text):'<bdi dir="ltr">'+escapeHTML(text)+'</bdi>'}</${tag}>`}).join('')+'</tr>').join('')+'</table></div>'}
function render(){
const lang=DATA.languages.find(l=>l.code===activeLanguage);
document.getElementById('language-hint').textContent=activeLanguage==='en'?'英文保持对照 · 每题独立调用':`English → ${lang.label} · 同一组 5 条案例`;
document.getElementById('cards').innerHTML=DATA.cases.map((c,i)=>{
const r=DATA.results.find(r=>r.id===c.id&&r.language===activeLanguage),t=r?.translation;
const ok=r?.status==='completed',check=r?.audit;
const visual=DATA.images[c.id]?`<figure class="visual"><img src="${DATA.images[c.id]}" alt="Case ${i+1} 原始英文图像" tabindex="0"><figcaption>原始英文图像 · 点击放大 · 图中文字尚未翻译</figcaption></figure>`:'';
const tables=c.table.rows.length?`<details open><summary>原始表格与 ${escapeHTML(lang.label)} 表格</summary><div class="qa-grid"><div><p class="language">ORIGINAL TABLE</p>${renderTable(c,null,'ltr')}</div><div><p class="language">${escapeHTML(lang.label)}</p>${ok?renderTable(c,t.table_texts,lang.direction):'<p>翻译不可用</p>'}</div></div><p class="notes">文本单元格由模型翻译；数字及合并单元格由原始数据保留。此 HTML 表格不是已重绘的 benchmark 图像。</p></details>`:'';
const terms=ok&&Array.isArray(t.terms)?t.terms.map(p=>`<span class="term">${escapeHTML(p.source)} → ${escapeHTML(p.target)}</span>`).join(''):'';
const notes=[...(check?.review_notes||[]),...(ok?t.notes:[])].map(n=>`<li>${escapeHTML(n)}</li>`).join('');
return `<article id="case-${i+1}" ${activeSource!=='all'&&activeSource!==c.source?'hidden':''}><div class="card-head"><div class="card-title"><span class="num">0${i+1}</span><div><h2>${escapeHTML(c.source)}</h2><div class="subtitle">${escapeHTML(lang.label)} · ${activeLanguage==='en'?'原文保持对照':'文字试译'}</div></div></div><span class="badge ${check?.passed?'':'warn'}">${!ok?'调用失败':check?.passed?'自动检查通过':'需复核差异'}</span></div>
<div class="qa-grid"><section class="qa-box"><div class="language">ENGLISH · ORIGINAL</div><p class="question">${escapeHTML(c.question_en)}</p><div class="answer"><small>原始答案</small>${escapeHTML(c.answer_en)}</div></section><section class="qa-box zh" lang="${activeLanguage}" dir="${lang.direction}"><div class="language">${escapeHTML(lang.label)} · MODEL OUTPUT</div><p class="question">${ok?escapeHTML(t.question):'本次调用未完成'}</p><div class="answer"><small>翻译答案</small>${ok?escapeHTML(t.answer):'—'}</div></section></div>
${visual}${tables}<div class="terms">${terms}</div><ul class="notes">${notes}</ul><details><summary>追溯信息与检查详情</summary><p class="meta">BASE ID · ${escapeHTML(c.base_id)}</p><p class="meta">VARIANT ID · ${escapeHTML(r?.variant_id)}</p><pre>${escapeHTML(JSON.stringify(check?.checks,null,2))}</pre><p class="notes">自动数值检查不代表翻译语义或原始答案已独立验证。</p></details></article>`;
}).join('');
document.querySelectorAll('.visual img').forEach(im=>{const show=()=>{document.querySelector('#zoom img').src=im.src;document.getElementById('zoom').showModal()};im.addEventListener('click',show);im.addEventListener('keydown',e=>{if(e.key==='Enter')show()})});
}
languageSelect.addEventListener('change',()=>{activeLanguage=languageSelect.value;render()});
document.querySelectorAll('#filters button').forEach(b=>b.addEventListener('click',()=>{activeSource=b.dataset.source;document.querySelectorAll('#filters button').forEach(x=>x.classList.toggle('active',x===b));render()}));
document.querySelectorAll('[data-nav]').forEach(a=>a.addEventListener('click',()=>{activeSource='all';document.querySelectorAll('#filters button').forEach(b=>b.classList.toggle('active',b.dataset.source==='all'));render()}));
document.querySelector('#zoom button').addEventListener('click',()=>document.getElementById('zoom').close());
render();
</script></body></html>'''
    content=layout.replace('__CSS__',CSS+EXTRA_CSS).replace('__SUCCESS__',str(summary['completed'])).replace('__PASSED__',str(passed)).replace('__MODEL__',results[0]['requested_model']).replace('__TOKENS__',str(summary['total_reported_tokens'])).replace('__DATA__',data)
    (OUT/'index.html').write_text(content)
    lock=json.loads((SOURCE/'selection_lock.json').read_text())
    assert all(hashlib.sha256((SOURCE/k).read_bytes()).hexdigest()==v for k,v in lock['input_file_hashes'].items())
    print(f'HTML saved; {passed}/55 automatic checks passed.')


if __name__=='__main__':
    main()
