"""Generate a self-contained interactive HTML report from exported JSONL."""

import html
import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {number}: {exc.msg}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"line {number} must contain a JSON object")
            records.append(value)
    return records


def generate_report(input_path: Path, output_path: Path) -> int:
    records = load_jsonl(input_path)
    payload = json.dumps(records, ensure_ascii=False).replace("</", "<\\/")
    title = html.escape(input_path.name)
    document = _TEMPLATE.replace("__TITLE__", title).replace("__DATA__", payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return len(records)


_TEMPLATE = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paper extraction report — __TITLE__</title>
<style>
:root{color-scheme:light dark;--bg:#f6f7f9;--panel:#fff;--text:#17202a;--muted:#667085;--line:#d9dee7;--accent:#2563eb;--good:#16803c;--bad:#c2413a} @media(prefers-color-scheme:dark){:root{--bg:#111827;--panel:#1f2937;--text:#f3f4f6;--muted:#aab2c0;--line:#445064;--accent:#7aa2ff;--good:#65d68a;--bad:#ff8580}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 system-ui,sans-serif}main{max-width:1400px;margin:auto;padding:24px}.top{display:flex;gap:16px;align-items:end;justify-content:space-between;flex-wrap:wrap}.controls{display:flex;gap:10px;flex-wrap:wrap}input,select{font:inherit;color:inherit;background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:8px 10px}input{min-width:260px}.stats{display:grid;grid-template-columns:repeat(4,minmax(130px,1fr));gap:10px;margin:18px 0}.stat,.paper,.viewer{background:var(--panel);border:1px solid var(--line);border-radius:10px}.stat{padding:12px}.stat b{display:block;font-size:22px}.muted{color:var(--muted)}.layout{display:grid;grid-template-columns:minmax(280px,36%) 1fr;gap:14px}.list{display:grid;gap:8px}.paper{padding:12px;text-align:left;color:inherit;cursor:pointer}.paper.active{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}.paper h3{font-size:14px;margin:0 0 5px}.bad{color:var(--bad)}.good{color:var(--good)}.viewer{padding:16px;min-width:0}.viewer h2{font-size:19px;margin:0 0 5px}.section{border-top:1px solid var(--line);padding-top:12px;margin-top:12px}.section h3{font-size:15px;margin:0 0 8px}.grid{display:grid;grid-template-columns:minmax(150px,28%) 1fr;gap:5px 12px}.key{color:var(--muted);overflow-wrap:anywhere}.value{overflow-wrap:anywhere}.array{display:grid;gap:8px}.item{border-left:3px solid var(--line);padding-left:10px}pre{white-space:pre-wrap;overflow-wrap:anywhere;margin:0;font:12px/1.45 ui-monospace,monospace}@media(max-width:760px){main{padding:14px}.stats{grid-template-columns:repeat(2,1fr)}.layout{grid-template-columns:1fr}input{min-width:0;width:100%}}
</style></head><body><main>
<div class="top"><div><h1 style="margin:0">论文提取结果</h1><div class="muted">__TITLE__</div></div><div class="controls"><input id="search" type="search" placeholder="搜索标题、DOI、作者…"><select id="status"><option value="">全部状态</option><option value="success">success</option><option value="failed">failed</option><option value="pending">pending</option></select></div></div>
<div class="stats" id="stats"></div><div class="layout"><div class="list" id="list"></div><article class="viewer" id="viewer"><span class="muted">选择一篇论文查看详情</span></article></div>
</main><script id="report-data" type="application/json">__DATA__</script><script>
const data=JSON.parse(document.getElementById('report-data').textContent),list=document.getElementById('list'),viewer=document.getElementById('viewer'),search=document.getElementById('search'),status=document.getElementById('status');let selected=null;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function renderValue(v){if(v===null||v===undefined||v==='')return '<span class="muted">—</span>';if(Array.isArray(v))return '<div class="array">'+v.map((x,i)=>'<div class="item">'+(typeof x==='object'?renderObject(x):esc(x))+'</div>').join('')+'</div>';if(typeof v==='object')return renderObject(v);return '<span class="value">'+esc(v)+'</span>'}
function renderObject(o){return '<div class="grid">'+Object.entries(o||{}).map(([k,v])=>'<div class="key">'+esc(k)+'</div><div>'+renderValue(v)+'</div>').join('')+'</div>'}
function show(r){selected=r.id;const x=r.extraction_json||{};viewer.innerHTML='<h2>'+esc(r.title||'Untitled')+'</h2><div class="muted">'+esc([r.year,r.doi,r.source].filter(Boolean).join(' · '))+'</div>'+(['research_scope','catalyst_formulations','reaction_conditions','performance_metrics','characterization_methods','mechanistic_interpretation','deactivation_and_stability','key_findings','limitations','data_quality_notes'].filter(k=>k in x).map(k=>'<section class="section"><h3>'+esc(k)+'</h3>'+renderValue(x[k])+'</section>').join(''))+(r.extraction_error?'<section class="section"><h3 class="bad">extraction_error</h3><pre>'+esc(r.extraction_error)+'</pre></section>':'');renderList()}
function filtered(){const q=search.value.toLowerCase(),s=status.value;return data.filter(r=>(!s||r.extraction_status===s)&&(!q||JSON.stringify([r.title,r.doi,r.authors,r.source]).toLowerCase().includes(q)))}
function renderList(){const rows=filtered();list.innerHTML=rows.map(r=>'<button class="paper '+(r.id===selected?'active':'')+'" data-id="'+esc(r.id)+'"><h3>'+esc(r.title||'Untitled')+'</h3><span class="'+(r.extraction_status==='success'?'good':r.extraction_status==='failed'?'bad':'muted')+'">'+esc(r.extraction_status||'unknown')+'</span><span class="muted"> · '+esc(r.year||'')+' · '+esc(r.doi||r.source||'')+'</span></button>').join('')||'<span class="muted">没有匹配记录</span>';list.querySelectorAll('button').forEach(b=>b.onclick=()=>show(data.find(r=>String(r.id)===b.dataset.id)))}
function renderStats(){const success=data.filter(r=>r.extraction_status==='success').length,failed=data.filter(r=>r.extraction_status==='failed').length,downloaded=data.filter(r=>r.download_status==='downloaded').length;document.getElementById('stats').innerHTML=[['记录',data.length],['已下载',downloaded],['提取成功',success],['提取失败',failed]].map(x=>'<div class="stat"><span class="muted">'+x[0]+'</span><b>'+x[1]+'</b></div>').join('')}
search.oninput=status.onchange=renderList;renderStats();renderList();if(data.length)show(data[0]);
</script></body></html>"""
