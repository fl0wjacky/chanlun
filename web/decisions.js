// 决策树页（卡 card-fe3aebd3-819）。数据照 Atlas 的 docs/spec/decisions.json 原样读（`{schema, decisions:[…]}`），前端不改名、不补内容。
// 一条的字段（Atlas 11:14 样例）：id, also[], layer（层名）, layer_order（0～9，跟总纲十层对齐）, title,
//   status{kind: 小栋定|我们定|待定, verified, date, quote, via, by, note, choice?}, what{plain, analogy},
//   sources[{source: 原博|镜像|编者, layer: 正文|答疑|推论|原文没写, lesson, lines, text, url?, sha256?, date?, speaker?, garbled?, reading?}],
//   options[{key, label, effect, numbers{}, figures[]}], tried[{label, result}], recommendation{choice, by, basis, reason},
//   affects[], depends_on[], docs[], open[], skeleton?
// ★ 缺的块写「（还没填）」，**不编**。★ `status.verified` 不是 true 的，一律画「状态待核」，不显示成小栋定／我们定（Nova 11:15）。
const $ = (id) => document.getElementById(id);
const MOCK = new URLSearchParams(location.search).has('mock');     // 样例：读 decisions/mock.json，不保存
const KIND = { '小栋定': 'xiaodong', '我们定': 'ours', '待定': 'open' };
const st = { items: [], byId: {}, layers: [], choices: {}, pending: {}, cur: null };

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const todo = '<span class="mu">（还没填）</span>';
const dotCls = (s) => (!s || !s.verified ? 'unver' : (KIND[s.kind] || 'open'));
const kindTxt = (s) => (!s || !s.verified ? '状态待核' : s.kind || '待定');
const day = (t) => String(t || '').replace(/^\d{4}-/, '');            // 2026-10-09 11:07 → 10-09 11:07

async function getJSON(url, opt) {
  const r = await fetch(url, Object.assign({ cache: 'no-store' }, opt));
  if (!r.ok) throw new Error(`${url} → ${r.status}`);
  return r.json();
}

async function load() {
  if (MOCK) { $('mode').hidden = false; $('mode').textContent = '样例数据 · 不保存'; }
  const data = await getJSON(MOCK ? 'decisions/mock.json' : '/api/decisions');
  st.items = Array.isArray(data) ? data : (data.decisions || data.items || []);
  st.byId = {};
  for (const d of st.items) { st.byId[d.id] = d; for (const a of d.also || []) if (!st.byId[a]) st.byId[a] = d; }
  // 层名照数据里的 layer（字符串）＋ layer_order 排序，前端不另起编号（Nova 11:17 ⑤）
  const L = new Map();
  for (const d of st.items) if (!L.has(d.layer_order)) L.set(d.layer_order, d.layer);
  st.layers = [...L.entries()].sort((a, b) => a[0] - b[0]);
  if (!MOCK) { try { st.choices = await getJSON('/api/decisions/choices'); } catch (e) { st.choices = {}; } }
  renderTree();
  const want = decodeURIComponent(location.hash.slice(1));
  show(st.byId[want] ? st.byId[want].id : (st.items.find((d) => !d.skeleton) || st.items[0] || {}).id);
}

function renderTree() {
  const only = $('onlyOpen').checked;
  const nav = $('tree'), sel = $('treeSel');
  nav.innerHTML = ''; sel.innerHTML = '';
  for (const [order, name] of st.layers) {
    const its = st.items.filter((d) => d.layer_order === order && (!only || !(d.status && d.status.verified) || d.status.kind === '待定'));
    if (!its.length) continue;
    const h = document.createElement('div'); h.className = 'layer'; h.textContent = `第 ${order} 层 · ${name}`; nav.appendChild(h);
    const og = document.createElement('optgroup'); og.label = `第 ${order} 层 · ${name}`;
    for (const d of its) {
      const b = document.createElement('button');
      b.className = 'node' + (d.skeleton ? ' skel' : ''); b.type = 'button'; b.dataset.id = d.id;
      b.innerHTML = `<span class="dot ${dotCls(d.status)}" title="${esc(kindTxt(d.status))}"></span><span class="id">${esc(d.id)}</span><span>${esc(d.title)}</span>`;
      b.onclick = () => show(d.id);
      nav.appendChild(b);
      const o = document.createElement('option'); o.value = d.id; o.textContent = `${d.id} ${d.title}（${kindTxt(d.status)}）`; og.appendChild(o);
    }
    sel.appendChild(og);
  }
  sel.onchange = () => show(sel.value);
  if (st.cur) markCurrent();
}
function markCurrent() {
  for (const b of $('tree').querySelectorAll('.node')) b.setAttribute('aria-current', b.dataset.id === st.cur ? 'true' : 'false');
  $('treeSel').value = st.cur;
}

// 状态那一行（Nova 11:17 ③：放标题下面，写全）
function statusLine(s) {
  if (!s || !s.verified) return '<span class="dot unver"></span>状态待核<span class="mu">（还没逐条核过，先别当真）</span>';
  if (s.kind === '小栋定') return `<span class="dot xiaodong"></span>小栋定${s.date ? ' · ' + esc(day(s.date)) : ''}${s.quote ? ` · 『${esc(s.quote)}』` : ''}${s.via ? `<span class="mu">（${esc(s.via)}）</span>` : ''}`;
  if (s.kind === '我们定') return `<span class="dot ours"></span>我们定${s.by ? ' · ' + esc(s.by) : ''}${s.date ? ' · ' + esc(day(s.date)) : ''}<span class="mu"> — 这是我们替你定的，你可以推翻</span>`;
  return '<span class="dot open"></span>待定';
}

function srcBlock(s) {
  const ref = s.lesson ? `L${esc(s.lesson)}${s.lines ? ':' + esc(s.lines) : ''}` : '';
  const who = s.source === '镜像' ? [s.date, s.speaker].filter(Boolean).map(esc).join(' · ') : '';
  const link = s.url ? `<a class="url" href="${esc(s.url)}" target="_blank" rel="noopener">原博</a>` : '';
  return `<div class="src"><span class="tag k-${esc(s.layer)}">${esc(s.layer || '')}</span><span class="from">${esc(s.source || '')}</span><span class="ref">${ref}</span>${link}
    ${who ? `<div class="who">${who}</div>` : ''}
    ${s.text ? `<blockquote>${esc(s.text)}</blockquote>` : ''}
    ${s.garbled ? `<div class="garbled">镜像这里有乱字：${esc(s.garbled)}</div>` : ''}${s.reading ? `<div class="reading">读作：${esc(s.reading)}</div>` : ''}
    ${s.sha256 ? `<div class="sha">原博页面 sha256 ${esc(s.sha256)}</div>` : ''}</div>`;
}

// 配图：数据里可以是 {src, caption}，也可以是一句「待 Iris 列：…」的字符串（还没配）
function figBlock(list) {
  const figs = (list || []).filter((f) => f && typeof f === 'object' && f.src);
  const want = (list || []).filter((f) => typeof f === 'string');
  return (figs.length ? `<div class="figs">${figs.map((f) => `<figure data-src="${esc(f.src)}" data-cap="${esc(f.caption || '')}"><img loading="lazy" src="${esc(f.src)}" alt="${esc(f.caption || '')}"><figcaption>${esc(f.caption || '')}</figcaption></figure>`).join('')}</div>` : '')
    + want.map((w) => `<p class="mu">配图：${esc(w)}</p>`).join('');
}

const linkIds = (ids) => (ids || []).map((x) => st.byId[x] ? `<a href="#${esc(st.byId[x].id)}" data-go="${esc(st.byId[x].id)}">${esc(x)}</a>` : `<span class="free">${esc(x)}</span>`).join('') || '<span class="mu">无</span>';

function show(id) {
  const d = st.byId[id];
  if (!d) return;
  id = d.id; st.cur = id;
  if (location.hash.slice(1) !== id) history.replaceState(null, '', '#' + encodeURIComponent(id));
  markCurrent();
  const s = d.status || {};
  const mine = st.choices[id];                       // 页面上存过的（后台）
  const his = s.verified && s.kind === '小栋定' ? s.choice : null;   // 数据里记的小栋定的那一项（Atlas 补 status.choice 后才有）
  const pend = st.pending[id];
  const rec = d.recommendation || {};
  const opts = (d.options || []).map((o) => {
    const isHis = his === o.key || (mine && mine.option === o.key);
    const cls = ['opt', o.key === rec.choice ? 'rec' : '', isHis ? 'chosen' : '', pend === o.key ? 'pending' : ''].join(' ');
    const nums = o.numbers && Object.keys(o.numbers).length ? `<table class="nums">${Object.entries(o.numbers).map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join('')}</table>` : '';
    const hisTag = isHis ? `<span class="tagme">你选的${his === o.key ? `（${esc(day(s.date))}，原话『${esc(s.quote || '')}』）` : `（${esc(mine.at || '')}，页面上存的）`}</span>` : '';
    return `<article class="${cls}" data-key="${esc(o.key)}">
      <header><b>${esc(o.key)}　${esc(o.label)}</b>${o.key === rec.choice ? '<span class="tagrec">推荐</span>' : ''}${hisTag}</header>
      <p>${o.effect ? esc(o.effect) : todo}</p>${nums}${figBlock(o.figures)}
      <div class="pick"><button type="button" class="ghost" data-pick="${esc(o.key)}">选这个</button></div></article>`;
  }).join('') || `<p>${todo}</p>`;
  const tried = (d.tried || []).length ? `<section class="blk tried"><h3>试过、没用的路</h3><ul>${d.tried.map((t) => `<li><b>${esc(t.label)}</b>：${esc(t.result)}</li>`).join('')}</ul></section>` : '';
  $('detail').innerHTML = `
    <h2>${esc(d.id)}${(d.also || []).length ? `<span class="also">（也是 ${d.also.map(esc).join('、')}）</span>` : ''}　${esc(d.title)}</h2>
    <div class="status">${statusLine(s)}</div>
    ${s.verified && s.note ? `<p class="snote">${esc(s.note)}</p>` : ''}
    ${d.skeleton ? '<p class="mu">这一条只有标题，详情还在填。</p>' : ''}
    <section class="blk what"><h3>① 管什么</h3>${d.what && d.what.plain ? `<p>${esc(d.what.plain)}</p>` : `<p>${todo}</p>`}${d.what && d.what.analogy ? `<p class="analogy">打个比方：${esc(d.what.analogy)}</p>` : ''}</section>
    <section class="blk"><h3>② 原文</h3>${(d.sources || []).map(srcBlock).join('') || `<p>${todo}</p>`}</section>
    <section class="blk"><h3>③ 各选项后果</h3><div class="opts">${opts}</div>
      <div class="saveline" id="saveline" ${pend ? '' : 'hidden'}>已选 ${esc(pend || '')}，还没保存　<button type="button" id="saveBtn">确认</button><button type="button" class="ghost" id="undoBtn">算了</button><span id="saveErr" class="err"></span></div></section>
    ${tried}
    <section class="blk rec"><h3>④ 推荐和理由</h3>${rec.choice ? `<p><b>${esc(rec.choice)}</b>　<span class="basis">${rec.basis === '原文' ? '原文站在这边' : rec.basis === '产品要求' ? '为了产品要求' : esc(rec.basis || '')}</span>${rec.by ? `<span class="mu">　推荐人：${esc(rec.by)}</span>` : ''}</p><p>${rec.reason ? esc(rec.reason) : todo}</p>` : `<p>${todo}</p>`}</section>
    <section class="blk deps"><h3>⑤ 牵连</h3><p>依赖：${linkIds(d.depends_on)}</p><p>改了它会跟着变：${linkIds(d.affects)}</p>${(d.docs || []).length ? `<p class="mu">文档：${d.docs.map(esc).join('；')}</p>` : ''}</section>
    <section class="blk"><h3>⑥ 状态</h3><p>${statusLine(s)}</p>${(d.open || []).length ? `<p class="mu">还没量完的：</p><ul class="open">${d.open.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}</section>`;
  for (const b of $('detail').querySelectorAll('[data-pick]')) b.onclick = () => { st.pending[id] = b.dataset.pick; show(id); };
  for (const a of $('detail').querySelectorAll('[data-go]')) a.onclick = (e) => { e.preventDefault(); show(a.dataset.go); };
  for (const f of $('detail').querySelectorAll('figure[data-src]')) f.onclick = () => { $('zoomImg').src = f.dataset.src; $('zoomCap').textContent = f.dataset.cap; $('zoom').showModal(); };
  if (pend) {
    $('undoBtn').onclick = () => { delete st.pending[id]; show(id); };
    $('saveBtn').onclick = () => confirmSave(d, pend);
  }
}

const decided = (x) => x && ((x.status && x.status.verified && x.status.kind === '小栋定') || st.choices[x.id]);

// 改已定的、或牵连到已定的 ⇒ 先列出来再存（Nova 11:12）
async function confirmSave(d, key) {
  const hit = [];
  if (decided(d)) hit.push([d.id, d.title, '这一条本身已经定过']);
  for (const x of d.affects || []) { const t = st.byId[x]; if (t && t.id !== d.id && decided(t)) hit.push([t.id, t.title, '已定，会跟着变']); }
  if (hit.length) {
    $('impactWhy').textContent = `选 ${key} 以后，下面这些已经定过的条目可能要重看：`;
    $('impactList').innerHTML = hit.map(([x, t, why]) => `<li><b>${esc(x)}</b> ${esc(t)} <span class="mu">— ${esc(why)}</span></li>`).join('');
    const ok = await new Promise((res) => { $('impact').onclose = () => res($('impact').returnValue === 'ok'); $('impact').showModal(); });
    if (!ok) return;
  }
  if (MOCK) { st.choices[d.id] = { option: key, at: '样例，不保存' }; delete st.pending[d.id]; show(d.id); return; }
  // 存选择要口令（Nova 11:13 ①：网站公开）。口令只私信给小栋，第一次输一下，存在他这台浏览器里；不进页面源码
  let pass = localStorage.getItem('decisions.pass');
  if (!pass) { pass = prompt('保存需要口令（私信里给你的那个）：') || ''; if (!pass) return; }
  try {
    const r = await fetch('/api/decisions/choices', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Decisions-Pass': pass }, body: JSON.stringify({ id: d.id, option: key }) });
    if (r.status === 401 || r.status === 403) { localStorage.removeItem('decisions.pass'); throw new Error('口令不对，再点一次确认重新输'); }
    if (!r.ok) throw new Error('保存失败：' + r.status);
    localStorage.setItem('decisions.pass', pass);
    st.choices[d.id] = await r.json();
    delete st.pending[d.id];
    show(d.id);
  } catch (e) { $('saveErr').textContent = e.message; }
}

$('onlyOpen').onchange = renderTree;
addEventListener('hashchange', () => { const id = decodeURIComponent(location.hash.slice(1)); if (st.byId[id] && st.byId[id].id !== st.cur) show(id); });
load().catch((e) => { $('detail').innerHTML = `<p class="err">数据没取到：${esc(e.message)}</p><p class="mu">后台的 /api/decisions 还没上的话，可以先加 ?mock=1 看样例。</p>`; });
