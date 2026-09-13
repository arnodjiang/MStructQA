"""Build a self-contained, offline HTML translation review with basic QA checks."""
import base64
import hashlib
import html
import json
import mimetypes
import re
from collections import Counter

from translate_pilot import OUT, ROOT, SOURCE


def esc(value):
    return html.escape(str(value), quote=True)


def rows(text):
    return [line.strip().strip('|').split('|') for line in text.splitlines()
            if line.strip().startswith('|')]


def table(text):
    result = []
    for index, row in enumerate(rows(text)):
        if all(re.fullmatch(r'[\s:\-]+', cell) for cell in row):
            continue
        tag = 'th' if index == 0 else 'td'
        result.append('<tr>' + ''.join(f'<{tag}>{esc(cell.strip())}</{tag}>' for cell in row) + '</tr>')
    return '<div class="table-scroll"><table>' + ''.join(result) + '</table></div>'


def numbers(text):
    return Counter(re.findall(r'[-+−]?\d[\d,]*(?:\.\d+)?', text))


def validate(record):
    translated = record['translation']
    checks = {'question_numeric_tokens_preserved': numbers(record['question_en']) == numbers(translated['question_zh']),
              'answer_numeric_tokens_preserved': numbers(record['answer_en']) == numbers(translated['answer_zh'])}
    if record['table_en']:
        before, after = rows(record['table_en']), rows(translated['table_zh'])
        checks['table_row_column_counts_preserved'] = [len(r) for r in before] == [len(r) for r in after]
        checks['table_numeric_tokens_preserved'] = numbers(record['table_en']) == numbers(translated['table_zh'])
        checks['table_numbers_in_original_cells'] = (len(before) == len(after) and
            all(len(a)==len(b) and all(numbers(x)==numbers(y) for x,y in zip(a,b)) for a,b in zip(before,after)))
    return checks


CSS = '''
.qa-grid > *{min-width:0}
:root{--bg:#f4f3ee;--ink:#182b28;--muted:#6a7771;--line:#dce3dc;--green:#185e4c;--pale:#eaf3ed}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif}
a{color:inherit}aside{position:fixed;inset:0 auto 0 0;width:235px;background:#133e34;color:#eaf3ed;padding:35px 25px;display:flex;flex-direction:column;gap:30px}.brand{font-size:25px;font-weight:750;letter-spacing:-1px}.brand small{display:block;font-size:10px;letter-spacing:3px;opacity:.65;font-weight:500;margin-top:5px}nav{display:grid;gap:8px}nav a{text-decoration:none;padding:12px;border-radius:8px;font-size:13px}nav a:hover{background:#ffffff12}nav b{display:block;font-size:15px}nav span{opacity:.6}.sidefoot{margin-top:auto;font-size:12px;color:#a9c4b9}main{max-width:1600px;margin-left:235px;padding:48px 44px 80px}.eyebrow{font-size:11px;letter-spacing:2px;color:var(--green);font-weight:700}h1{font-size:38px;letter-spacing:-1.4px;margin:8px 0 12px;line-height:1.2}header p{color:var(--muted);max-width:850px}.stats{display:flex;gap:40px;padding:23px 0;margin:25px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.stat strong{font-size:25px;display:block}.stat span{font-size:12px;color:var(--muted)}.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:25px 0}button{font:inherit;cursor:pointer}.filter{border:1px solid var(--line);border-radius:22px;padding:7px 16px;background:white;font-size:13px}.filter.active{background:var(--green);color:white;border-color:var(--green)}article{background:#fff;border:1px solid var(--line);border-radius:16px;margin:0 0 28px;padding:26px;scroll-margin-top:20px;box-shadow:0 5px 20px #193c2903}article[hidden]{display:none}.card-head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:20px}.card-title{display:flex;gap:14px;align-items:center}.num{font-size:28px;color:#a6b7ab;font-weight:400}h2{font-size:20px;margin:0}.subtitle{font-size:12px;color:var(--muted)}.badge{font-size:11px;border-radius:20px;background:var(--pale);padding:6px 12px;color:var(--green)}.qa-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.language{font-size:10px;letter-spacing:2px;color:var(--muted);font-weight:700}.qa-box{padding:20px;background:#f7f8f5;border-radius:10px;min-width:0}.qa-box.zh{background:#edf5ef}.question{font-size:17px;font-weight:550;min-height:62px;margin:12px 0 18px}.answer{border-top:1px solid #dbe5dc;padding-top:12px;font-size:18px}.answer small{font-size:11px;color:var(--muted);display:block;margin-bottom:4px}.visual{margin:22px 0;background:#fafbf9;border:1px solid var(--line);border-radius:10px;padding:16px;text-align:center}.visual img{max-width:100%;max-height:470px;object-fit:contain;cursor:zoom-in}.visual figcaption{color:var(--muted);font-size:11px;margin-top:8px}.table-scroll{overflow:auto;width:100%;max-height:470px;border:1px solid var(--line);border-radius:8px;margin-top:10px}table{border-collapse:collapse;font-size:12px;width:100%;min-width:430px}th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);border-right:1px solid var(--line);white-space:normal;min-width:75px}th{background:#e9eeea;position:sticky;top:0}tr:nth-child(even) td{background:#fafbf9}details{margin-top:15px;border-top:1px solid var(--line);padding-top:14px}summary{cursor:pointer;color:var(--green);font-size:13px}.meta{font-size:11px;color:var(--muted);word-break:break-all}.terms{margin:15px 0 0;display:flex;gap:8px;flex-wrap:wrap}.term{font-size:11px;background:#f4f5f1;border:1px solid var(--line);border-radius:5px;padding:4px 8px}.notes{font-size:12px;color:var(--muted);margin-top:15px}.notice{background:#e9eee5;border-left:3px solid #5c826a;padding:14px 18px;font-size:13px;margin-bottom:25px}footer{font-size:12px;color:var(--muted)}dialog{width:95vw;max-width:1500px;border:none;border-radius:12px;padding:20px}dialog::backdrop{background:#102c25bb}dialog img{max-width:100%;display:block;margin:auto}.close{position:sticky;top:0;float:right;border:0;border-radius:50%;background:#173e32;color:white;width:36px;height:36px}pre{white-space:pre-wrap;word-break:break-word;font-size:11px}
@media(max-width:1000px){aside{width:180px;padding:25px 16px}main{margin-left:180px;padding:30px 22px}.qa-grid{gap:12px}article{padding:20px}h1{font-size:30px}.stats{gap:25px}}
@media(max-width:720px){aside{position:static;width:auto;padding:18px 22px;display:block}aside nav,.sidefoot{display:none}.brand{font-size:22px}.brand small{display:none}main{margin-left:0;padding:25px 16px}.qa-grid{grid-template-columns:1fr}.question{min-height:0}.stats{gap:25px}.stat strong{font-size:20px}.card-head{align-items:flex-start}.badge{white-space:nowrap;font-size:10px}}
'''

REVIEW_NOTES = {
    'e9862f967583ff461a6b': '人工初看：Aggregate（Aggregate）重复，且与术语表“汇总”不一致。建议后续统一为“汇总（Aggregate）”；这里保留模型原始译文。',
    '2807106cc9f8feac0ee1': '人工初看：“有多少个十年人口超过了 10 百万”表达生硬。后续可将数量单位规范为“人口超过 1,000 万的十年期有多少个”，同时记录数值等价转换；这里保留原始试译。',
    '3cb6452a2a243405fae2': '人工初看：“$3.0 十亿美元”的货币标记重复。该样本仅有 HTML 源表，当前 API 请求只翻译问答，未翻译表格；源 HTML 仍保存在原始资产目录。',
}


def main():
    data = json.loads((OUT/'translations.json').read_text())
    audits, cards, nav = [], [], []
    labels = ['子图定位 · 近似读数', '相关关系 · 极值比较', '条件筛选 · 计数', '财务表格 · 定位查找', '历史表格 · 数值计算']
    for i, record in enumerate(data, 1):
        translated = record['translation']
        checks = validate(record)
        audits.append({'id':record['id'], 'base_id':record['base_id'], 'checks':checks,
                       'semantic_review':'not_independently_verified'})
        source = esc(record['source'])
        nav.append(f'<a href="#case-{i}"><span>CASE 0{i}</span><b>{source}</b></a>')
        visual = ''
        if record['original_image']:
            path = ROOT / record['original_image']
            uri = 'data:' + (mimetypes.guess_type(path)[0] or 'image/png') + ';base64,' + base64.b64encode(path.read_bytes()).decode()
            visual = f'<figure class="visual"><img src="{uri}" alt="Case {i} 原始英文图像" tabindex="0"><figcaption>原始英文图像 · 点击放大 · 图中文字尚未翻译</figcaption></figure>'
        tables = ''
        if record['table_en']:
            tables = '<details open><summary>原始表格与中文文字预览</summary><div class="qa-grid"><div><p class="language">ORIGINAL TABLE</p>' + table(record['table_en']) + '</div><div><p class="language">中文表格</p>' + table(translated['table_zh']) + '</div></div></details>'
            if not visual:
                tables = '<p class="notes">此样本原始输入为文本表格，以下采用 HTML 展示；尚未生成评测用图像。</p>' + tables
        terms = ''.join('<span class="term">'+esc(p['en'])+' → '+esc(p['zh'])+'</span>' for p in translated['term_pairs'])
        notes = ''.join('<li>'+esc(n)+'</li>' for n in translated['notes_zh'])
        review_note = '<p class="notice">'+esc(REVIEW_NOTES[record['id']])+'</p>' if record['id'] in REVIEW_NOTES else ''
        badge = '数值 / 结构检查通过' if all(checks.values()) else '有检查项待复核'
        cards.append(f'''<article id="case-{i}" data-source="{source}">
<div class="card-head"><div class="card-title"><span class="num">0{i}</span><div><h2>{source}</h2><div class="subtitle">{labels[i-1]}</div></div></div><span class="badge">{badge}</span></div>
<div class="qa-grid"><section class="qa-box"><div class="language">ENGLISH · ORIGINAL</div><p class="question">{esc(record['question_en'])}</p><div class="answer"><small>原始答案</small>{esc(record['answer_en'])}</div></section>
<section class="qa-box zh"><div class="language">简体中文 · MODEL TRANSLATION</div><p class="question">{esc(translated['question_zh'])}</p><div class="answer"><small>翻译答案</small>{esc(translated['answer_zh'])}</div></section></div>
{visual}{tables}<div class="terms">{terms}</div><ul class="notes">{notes}</ul>{review_note}
<details><summary>追溯信息与自动检查</summary><p class="meta">BASE ID · {esc(record['base_id'])}</p><p class="meta">原始记录 · {esc(record['id'])} · {esc(record['provenance']['file'])} · 行 {record['provenance']['row_index']}（从 0 起）</p><pre>{esc(json.dumps(checks,ensure_ascii=False,indent=2))}</pre></details></article>''')
    passed = sum(all(a['checks'].values()) for a in audits)
    filters = ''.join(f'<button class="filter" data-filter="{esc(s)}">{esc(s)}</button>' for s in dict.fromkeys(r['source'] for r in data))
    content = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MVisQA · 五条中文试译对照</title><style>{CSS}</style></head><body>
<aside><div class="brand">MVisQA<small>TRANSLATION LAB</small></div><nav>{''.join(nav)}</nav><div class="sidefoot">EN → 简体中文<br>5 CASES / PILOT 01<br>本地离线对照页</div></aside>
<main><header><div class="eyebrow">MULTILINGUAL BENCHMARK / TRANSLATION PILOT</div><h1>让同一道题，跨越语言。</h1><p>五条普通 QA 的首次中文试译。对照原始图表，检查提问、答案与表格文字的表达；每条译文均保留原题身份。</p></header>
<div class="stats"><div class="stat"><strong>05</strong><span>试译样本</span></div><div class="stat"><strong>04</strong><span>数据来源</span></div><div class="stat"><strong>{passed} / 5</strong><span>自动数值 / 结构检查</span></div><div class="stat"><strong>EN → ZH</strong><span>语言方向</span></div></div>
<div class="notice">模型：{esc(data[0]['requested_model'])}。原始图像保持英文，表格中文为文字预览。自动检查不等于答案正确性或翻译语义已经独立验证。</div>
<div class="toolbar" role="group" aria-label="按来源筛选"><button class="filter active" data-filter="all">全部 5 条</button>{filters}</div>
{''.join(cards)}<footer>本地生成 · 原始数据未覆盖 · 图像已内嵌，可离线打开 · 译文与调用记录另存 translations.json</footer></main>
<dialog id="zoom"><button class="close" aria-label="关闭大图">×</button><img alt="放大的原始图像"></dialog>
<script>
document.querySelectorAll('.filter').forEach(b=>b.addEventListener('click',()=>{{document.querySelectorAll('.filter').forEach(x=>x.classList.toggle('active',x===b));document.querySelectorAll('article').forEach(a=>a.hidden=b.dataset.filter!=='all'&&a.dataset.source!==b.dataset.filter);}}));
document.querySelectorAll('nav a').forEach(a=>a.addEventListener('click',()=>document.querySelector('[data-filter="all"]').click()));
const dialog=document.getElementById('zoom');document.querySelectorAll('.visual img').forEach(im=>{{const show=()=>{{dialog.querySelector('img').src=im.src;dialog.showModal()}};im.addEventListener('click',show);im.addEventListener('keydown',e=>{{if(e.key==='Enter')show()}})}});dialog.querySelector('button').addEventListener('click',()=>dialog.close());dialog.addEventListener('click',e=>{{if(e.target===dialog)dialog.close()}});
</script></body></html>'''
    (OUT/'index.html').write_text(content)
    (OUT/'validation.json').write_text(json.dumps({'cases':audits,'all_automatic_checks_passed':passed==5},ensure_ascii=False,indent=2))
    (OUT/'review_notes.json').write_text(json.dumps({'reviewer':'Codex linguistic spot review', 'notes':REVIEW_NOTES, 'model_output_modified':False},ensure_ascii=False,indent=2))
    # Keep source identity and source table archive unchanged.
    lock=json.loads((SOURCE/'selection_lock.json').read_text())
    assert all(hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()==checksum for name,checksum in lock['input_file_hashes'].items())
    print(f'HTML saved; automatic checks passed for {passed}/5 cases.')


if __name__ == '__main__':
    main()
