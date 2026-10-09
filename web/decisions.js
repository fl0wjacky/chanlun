// 决策树页（卡 card-fe3aebd3-819）。数据字段照 Atlas 的结构化数据原样读，前端不改名、不补内容：
//   {id, layer, title, status: 'xiaodong'|'ours'|'open', decided?: {at, quote},
//    what: {plain, analogy?}, sources: [{kind: 正文|答疑|镜像|推论, ref, text, sha?}],
//    options: [{key, label, effect, numbers?: [{label, value}], figs?: [{src, caption}]}],
//    recommend?: {key, why, basis: 原文|产品}, depends?: [id], affects?: [id]}
// ★ 缺的块就写「（还没填）」，**不编**：这页是给小栋拍板用的，空着比编的好。
const $ = (id) => document.getElementById(id);
const MOCK = new URLSearchParams(location.search).has('mock');   // 样例模式：只读 decisions/mock.json，不保存
const LAYERS = ['读法', '笔', '线段', '中枢', '走势', '买卖点'];
const STATUS = { xiaodong: '小栋定', ours: '我们定', open: '待定' };
const st = { items: [], byId: {}, choices: {}, pending: {}, cur: null };

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const todo = '<span class="mu">（还没填）</span>';

async function getJSON(url) {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(`${url} → ${r.status}`);
  return r.json();
}

async function load() {
  if (MOCK) { $('mode').hidden = false; $('mode').textContent = '样例数据 · 不保存'; }
  const data = await getJSON(MOCK ? 'decisions/mock.json' : '/api/decisions');
  st.items = Array.isArray(data) ? data : (data.items || []);
  st.byId = Object.fromEntries(st.items.map((d) => [d.id, d]));
  if (!MOCK) {
    try { st.choices = await getJSON('/api/decisions/choices'); } catch (e) { st.choices = {}; }
  }
  renderTree();
  const want = decodeURIComponent(location.hash.slice(1));
  show(st.byId[want] ? want : (st.items[0] || {}).id);
}

// 状态：后台存下来的选择优先显示成「小栋选了」，但条目本身的 status 只认数据（定没定由人改数据，页面不自作主张）
function renderTree() {
  const only = $('onlyOpen').checked;
  const nav = $('tree'), sel = $('treeSel');
  nav.innerHTML = ''; sel.innerHTML = '';
  LAYERS.forEach((name, L) => {
    const its = st.items.filter((d) => (d.layer ?? 0) === L && (!only || d.status === 'open'));
    if (!its.length) return;
    const h = document.createElement('div'); h.className = 'layer'; h.textContent = `第 ${L} 层 · ${name}`; nav.appendChild(h);
    const og = document.createElement('optgroup'); og.label = `第 ${L} 层 · ${name}`;
    for (const d of its) {
      const b = document.createElement('button');
      b.className = 'node'; b.type = 'button'; b.dataset.id = d.id;
      b.innerHTML = `<span class="dot ${esc(d.status)}" title="${esc(STATUS[d.status] || d.status)}"></span><span class="id">${esc(d.id)}</span><span>${esc(d.title)}</span>`;
      b.onclick = () => show(d.id);
      nav.appendChild(b);
      const o = document.createElement('option'); o.value = d.id; o.textContent = `${d.id} ${d.title}（${STATUS[d.status] || d.status}）`;   // 原生下拉上不了色，状态写成字 og.appendChild(o);
    }
    sel.appendChild(og);
  });
  sel.onchange = () => show(sel.value);
  if (st.cur) markCurrent();
}
function markCurrent() {
  for (const b of $('tree').querySelectorAll('.node')) b.setAttribute('aria-current', b.dataset.id === st.cur ? 'true' : 'false');
  $('treeSel').value = st.cur;
}

function show(id) {
  const d = st.byId[id];
  if (!d) return;
  st.cur = id;
  if (location.hash.slice(1) !== id) history.replaceState(null, '', '#' + encodeURIComponent(id));
  markCurrent();
  const mine = st.choices[id];
  const pend = st.pending[id];
  const rec = d.recommend || {};
  const src = (d.sources || []).map((s) => `<div class="src"><span class="tag k-${esc(s.kind)}">${esc(s.kind)}</span><span class="ref">${esc(s.ref || '')}</span>
      ${s.text ? `<blockquote>${esc(s.text)}</blockquote>` : ''}${s.sha ? `<div class="sha">sha256 ${esc(s.sha)}</div>` : ''}</div>`).join('')
    || '<p class="mu">原文没写（或者还没填）。</p>';
  const opts = (d.options || []).map((o) => {
    const cls = ['opt', o.key === rec.key ? 'rec' : '', mine && mine.option === o.key ? 'chosen' : '', pend === o.key ? 'pending' : ''].join(' ');
    const nums = (o.numbers || []).length ? `<table class="nums">${o.numbers.map((n) => `<tr><td>${esc(n.label)}</td><td>${esc(n.value)}</td></tr>`).join('')}</table>` : '';
    const figs = (o.figs || []).length ? `<div class="figs">${o.figs.map((f) => `<figure data-src="${esc(f.src)}" data-cap="${esc(f.caption || '')}"><img loading="lazy" src="${esc(f.src)}" alt="${esc(f.caption || '')}"><figcaption>${esc(f.caption || '')}</figcaption></figure>`).join('')}</div>` : '';
    return `<article class="${cls}" data-key="${esc(o.key)}">
      <header><b>${esc(o.key)}　${esc(o.label)}</b>${o.key === rec.key ? '<span class="tagrec">推荐</span>' : ''}${mine && mine.option === o.key ? '<span class="tagme">● 小栋选了这个</span>' : ''}</header>
      <p>${o.effect ? esc(o.effect) : todo}</p>${nums}${figs}
      <div class="pick"><button type="button" class="ghost" data-pick="${esc(o.key)}">选这个</button></div></article>`;
  }).join('') || `<p>${todo}</p>`;
  const link = (ids) => (ids || []).map((x) => st.byId[x] ? `<a href="#${esc(x)}" data-go="${esc(x)}">${esc(x)}</a>` : `<span class="mu">${esc(x)}</span>`).join('') || '<span class="mu">无</span>';
  $('detail').innerHTML = `
    <h2>${esc(d.id)}　${esc(d.title)}</h2>
    <span class="status"><span class="dot ${esc(d.status)}"></span>${esc(STATUS[d.status] || d.status)}</span>
    <section class="blk what"><h3>① 管什么</h3>${d.what && d.what.plain ? `<p>${esc(d.what.plain)}</p>` : `<p>${todo}</p>`}${d.what && d.what.analogy ? `<p class="analogy">打个比方：${esc(d.what.analogy)}</p>` : ''}</section>
    <section class="blk"><h3>② 原文</h3>${src}</section>
    <section class="blk"><h3>③ 各选项后果</h3><div class="opts">${opts}</div>
      <div class="saveline" id="saveline" ${pend ? '' : 'hidden'}>已选 ${esc(pend || '')}，还没保存　<button type="button" id="saveBtn">确认</button><button type="button" class="ghost" id="undoBtn">算了</button><span id="saveErr" class="err"></span></div></section>
    <section class="blk rec"><h3>④ 推荐和理由</h3>${rec.key ? `<p><b>${esc(rec.key)}</b>　<span class="basis">${rec.basis === '原文' ? '原文站在这边' : rec.basis === '产品' ? '为了产品要求' : esc(rec.basis || '')}</span></p><p>${rec.why ? esc(rec.why) : todo}</p>` : `<p>${todo}</p>`}</section>
    <section class="blk deps"><h3>⑤ 牵连</h3><p>依赖：${link(d.depends)}</p><p>改了它会跟着变：${link(d.affects)}</p></section>
    <section class="blk"><h3>⑥ 状态</h3>${d.status === 'xiaodong' && d.decided ? `<div class="decided">小栋 ${esc(d.decided.at || '')} 定：「${esc(d.decided.quote || '')}」</div>` : `<p>${esc(STATUS[d.status] || d.status)}</p>`}
      ${mine ? `<p class="mu">页面上存的选择：${esc(mine.option)}（${esc(mine.at || '')}）</p>` : ''}</section>`;
  for (const b of $('detail').querySelectorAll('[data-pick]')) b.onclick = () => { st.pending[id] = b.dataset.pick; show(id); };
  for (const a of $('detail').querySelectorAll('[data-go]')) a.onclick = (e) => { e.preventDefault(); show(a.dataset.go); };
  for (const f of $('detail').querySelectorAll('figure[data-src]')) f.onclick = () => { $('zoomImg').src = f.dataset.src; $('zoomCap').textContent = f.dataset.cap; $('zoom').showModal(); };
  if (pend) {
    $('undoBtn').onclick = () => { delete st.pending[id]; show(id); };
    $('saveBtn').onclick = () => confirmSave(d, pend);
  }
}

// 改已定的、或者牵连到已定的 ⇒ 先列出来让他看，再存（小栋 11:10 / Nova：改已定条目要先弹牵连提示）
async function confirmSave(d, key) {
  const hit = [];
  if (d.status === 'xiaodong' || st.choices[d.id]) hit.push([d.id, d.title, '这一条本身已经定过']);
  for (const x of d.affects || []) {
    const t = st.byId[x];
    if (t && (t.status === 'xiaodong' || st.choices[x])) hit.push([x, t.title, '已定，会跟着变']);
  }
  if (hit.length) {
    $('impactWhy').textContent = `选 ${key} 以后，下面这些已经定过的条目可能要重看：`;
    $('impactList').innerHTML = hit.map(([x, t, why]) => `<li><b>${esc(x)}</b> ${esc(t)} <span class="mu">— ${esc(why)}</span></li>`).join('');
    const ok = await new Promise((res) => { $('impact').onclose = () => res($('impact').returnValue === 'ok'); $('impact').showModal(); });
    if (!ok) return;
  }
  if (MOCK) { st.choices[d.id] = { option: key, at: '（样例，不保存）' }; delete st.pending[d.id]; show(d.id); return; }
  try {
    const r = await fetch('/api/decisions/choices', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: d.id, option: key }) });
    if (!r.ok) throw new Error('保存失败：' + r.status);
    st.choices[d.id] = await r.json();
    delete st.pending[d.id];
    show(d.id);
  } catch (e) { $('saveErr').textContent = e.message; }
}

$('onlyOpen').onchange = renderTree;
addEventListener('hashchange', () => { const id = decodeURIComponent(location.hash.slice(1)); if (id !== st.cur && st.byId[id]) show(id); });
load().catch((e) => { $('detail').innerHTML = `<p class="err">数据没取到：${esc(e.message)}</p><p class="mu">后台的 /api/decisions 还没上的话，可以先加 ?mock=1 看样例。</p>`; });
