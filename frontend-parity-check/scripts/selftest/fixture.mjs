// Two deliberately-diverging versions of the same page, used to prove the toolchain works.
// The "new" version drops a filter field and an export button, renames a table column,
// changes theme color / radius / base font-size, and throws on opening a detail row.
import http from 'node:http';
import { pathToFileURL } from 'node:url';

const page = ({ title, primaryBg, radius, extraBtn, missingField, colName, fontSize, brokenJs }) => `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>${title}</title>
<style>
 body{font-family:"Helvetica Neue",Arial,sans-serif;margin:0;background:#f5f6f8;color:#222;font-size:${fontSize}}
 .wrap{max-width:1000px;margin:24px auto;background:#fff;padding:20px;border-radius:${radius}}
 h1{font-size:22px;margin:0 0 16px}
 .search-form{display:flex;gap:12px;align-items:center;margin-bottom:16px}
 input,select{padding:6px 10px;border:1px solid #dcdfe6;border-radius:4px}
 button{padding:7px 16px;border:0;border-radius:${radius};cursor:pointer}
 .el-button--primary{background:${primaryBg};color:#fff}
 table{width:100%;border-collapse:collapse}
 th{background:#fafafa;text-align:left;padding:10px;border-bottom:1px solid #ebeef5;font-weight:600}
 td{padding:10px;border-bottom:1px solid #ebeef5}
 .detail-panel{margin-top:16px;padding:16px;background:#f0f7ff;border-radius:6px}
 .hidden{display:none}
</style></head><body>
<div class="wrap">
 <h1>订单列表</h1>
 <div class="search-form">
  <label for="kw">关键词</label>
  <input id="kw" name="keyword" placeholder="请输入订单号">
  ${missingField ? '' : '<label for="st">状态</label><select id="st" name="status"><option>全部</option><option>已完成</option></select>'}
  <button class="el-button--primary" onclick="doSearch()">查询</button>
  <button onclick="reset()">重置</button>
  ${extraBtn ? '<button class="export">导出</button>' : ''}
 </div>
 <table class="el-table"><thead><tr><th>订单号</th><th>${colName}</th><th>金额</th><th>操作</th></tr></thead>
 <tbody id="tb"></tbody></table>
 <div class="detail-panel hidden"><h2>订单详情</h2><p id="dtl"></p></div>
</div>
<script>
 const rows=[{no:'A001',c:'张三',amt:'￥120.00'},{no:'A002',c:'李四',amt:'￥98.50'},{no:'B003',c:'王五',amt:'￥310.00'}];
 function render(list){document.getElementById('tb').innerHTML=list.map(r=>
  '<tr class="el-table__row"><td>'+r.no+'</td><td>'+r.c+'</td><td>'+r.amt+
  '</td><td><a href="#detail" class="detail-link" onclick="openDetail(\\''+r.no+'\\')">查看</a></td></tr>').join('');}
 function doSearch(){const k=document.getElementById('kw').value.trim();
  render(k?rows.filter(r=>r.no.includes(k)):rows);}
 function reset(){document.getElementById('kw').value='';render(rows);}
 function openDetail(no){${brokenJs ? 'window.__missing.fn();' : ''}
  document.getElementById('dtl').textContent='订单 '+no+' 的详情';
  document.querySelector('.detail-panel').classList.remove('hidden');
  history.replaceState({},'','?order='+no);}
 render(rows);
</script></body></html>`;

const VARIANTS = {
  9401: { title: '订单列表 - 旧版', primaryBg: '#409eff', radius: '4px', extraBtn: true, missingField: false, colName: '客户名称', fontSize: '14px', brokenJs: false },
  9402: { title: '订单列表 - 新版', primaryBg: '#1668dc', radius: '10px', extraBtn: false, missingField: true, colName: '客户', fontSize: '13px', brokenJs: true },
};

export function startFixture() {
  const servers = Object.entries(VARIANTS).map(([port, v]) =>
    http.createServer((_req, res) => {
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
      res.end(page(v));
    }).listen(Number(port)));
  return () => servers.forEach((s) => s.close());
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  startFixture();
  console.log('fixture on http://127.0.0.1:9401 (old) and http://127.0.0.1:9402 (new)');
}
