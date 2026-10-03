// chanlun.surfers.cc 前端 —— 接线：取数 → 建图 → 开关 → 角上的「最后更新时间」。
//
// 数据只认一个形状（`tools/make_web_fixture.py` 就是它的可执行定义，后台卡 card-29a45ab6-0ac 照着吐）：
//   {symbol, tf, name, updated, closed, bars[], pens[], segs[], centers[], seg_centers[], signals{seg,pen}, meta{tick,pen_rule}}
// 取不到后台就退回 `fixtures/`（离线也能看、也能截图对账）；两边都没有就老实说取不到，不画半张图。
import { CHART, PAGE, CANDLE, WIDTH } from './theme.js';
import { makeBoxPrimitive, makeAnnotPrimitive } from './layers.js';

const LWC = window.LightweightCharts;

// 配色灌进 CSS 变量（style.css 不写死任何色值 —— 色只有一个出处：theme.js → render/style.py）
for (const [k, v] of Object.entries(PAGE)) document.documentElement.style.setProperty(`--${k}`, v);
// ★ 徽标的两个强调色也在这里出。原先 style.css 里写死了 `#ffbc3c`，而 style.py 的 AM 是 `#ffbe3c`
//   —— 差 2，肉眼看不出来，`tools/web_theme_sync.py` 也看不出来（它只读 theme.js，读不到 CSS）。
//   现在 CSS 里只剩 var()，值的来源还是这一处；边框是把同色压到页面底色上算出来的（不另发明一个色）。
const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const mix = (a, b, k) => '#' + rgb(a).map((c, i) => Math.round(c * k + rgb(b)[i] * (1 - k))
  .toString(16).padStart(2, '0')).join('');                     // mix(a,b,k) = k·a + (1−k)·b
const cssVar = (n, v) => document.documentElement.style.setProperty(n, v);
cssVar('--am', CANDLE.open);                                  // 未收盘 / 旧数据：琥珀（style.py AM）
cssVar('--rd', CHART.sell);                                   // 出错：红（style.py CHART.sell）
cssVar('--am-line', mix(CANDLE.open, PAGE.bg, 0.26));         // 徽标边框＝同色压到 bg 上，不新造色
cssVar('--rd-line', mix(CHART.sell, PAGE.bg, 0.26));
cssVar('--panel-hi', mix(PAGE.tx, PAGE.panel, 0.05));         // 选中的 chip：panel 抬 5% 白
document.getElementById('today').textContent = new Date().toISOString().slice(0, 10);   // 署名：冲浪者 · 日期

// 白名单跟后台卡一致（后台卡：白名单外一律 400）——前端也拦一道，省一次没意义的请求
export const SYMBOLS = [
  ['BTCUSDT', 'BTC/USDT 永续', 'btc'],
  ['ZECUSDT', 'ZEC/USDT 永续', 'zec'],
  ['AAPLUSDT', 'AAPL/USDT 永续', 'aaplusdt'],
];
const TFS = ['15m', '30m', '1h', '2h', '4h'];

// 默认开关 = TradingView 的默认值（tradingview/chanlun.pine）：笔/线段/线段中枢开，
// 类中枢、高一级、买卖点关。★ 这条是卡面点名的，别顺手改「好看一点」的默认。
const DEFAULTS = {
  pen: true, seg: true, pc: false, sc: true, up: false,
  sig: false, sigPend: false,
  sigKinds: { 一买: true, 二买: true, 三买: true, 一卖: true, 二卖: true, 三卖: true },
};

const el = (id) => document.getElementById(id);
const opts = { ...DEFAULTS, sigKinds: { ...DEFAULTS.sigKinds } };
const state = { data: null, opts, candleSeries: null, source: '' };
const primitives = [];

const chart = LWC.createChart(el('chart'), {
  autoSize: true,
  layout: { background: { type: 'solid', color: PAGE.bg }, textColor: PAGE.mu, panes: { separatorColor: PAGE.line } },
  grid: { vertLines: { visible: false }, horzLines: { color: '#1b1f28' } },
  rightPriceScale: {
    borderColor: PAGE.line,
    mode: LWC.PriceScaleMode.Logarithmic,      // ★ Python 那版是**一根对数轴**（chart_full_smooth.py 的 Y=log）
    scaleMargins: { top: 0.08, bottom: 0.08 },
  },
  timeScale: { borderColor: PAGE.line, timeVisible: true, secondsVisible: false, rightOffset: 3, barSpacing: 6 },
  crosshair: { mode: LWC.CrosshairMode.Normal },
  localization: {
    locale: 'zh-CN',
    timeFormatter: (t) => new Date(t * 1000).toISOString().slice(0, 16).replace('T', ' ') + ' UTC',
  },
});

const candle = chart.addSeries(LWC.CandlestickSeries, {
  upColor: CANDLE.up, downColor: CANDLE.dn, borderVisible: false,
  wickUpColor: CANDLE.up, wickDownColor: CANDLE.dn,
  priceLineVisible: false,
});
const line = (o) => chart.addSeries(LWC.LineSeries, {
  priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, ...o,
});
const penSolid = line({ color: CHART.pen, lineWidth: WIDTH.pen });
const penDash = line({ color: CHART.pen, lineWidth: WIDTH.pen, lineStyle: LWC.LineStyle.Dashed });
const segSolid = line({ color: CHART.seg, lineWidth: WIDTH.seg });
const segDash = line({ color: CHART.seg, lineWidth: WIDTH.seg, lineStyle: LWC.LineStyle.LargeDashed });

// 标注层要挂在一个**永远可见**的系列上：挂在「线段」系列上的话，一关线段开关，
// 系列不可见 ⇒ 它的 primitive 也不再被画，价签和买卖点会跟着一起消失（那不是开关的语义）。
// 所以另起一条透明、只放一个点的辅助系列，加在最后 ⇒ 画在最上层，跟 Python「标签最后画」同一次序。
const overlay = line({ color: 'rgba(0,0,0,0)', lineWidth: 1 });
state.overlaySeries = overlay;

state.candleSeries = candle;
for (const [c, p] of [[candle, makeBoxPrimitive(state)], [overlay, makeAnnotPrimitive(state)]]) {
  c.attachPrimitive(p);
  primitives.push(p);
}
const repaint = () => primitives.forEach((p) => p._request && p._request());

// ---------------------------------------------------------------- 取数
function fixtureNames(symbol, tf) {
  const pre = (SYMBOLS.find((s) => s[0] === symbol) || [])[2] || symbol.toLowerCase();
  const want = new Set([tf, tf.replace('m', ''), tf.replace('m', '_m')]);   // 4h / zec15 这种旧名都认
  const names = [];
  for (const t of want) {
    names.push(`${pre}_${t}.json`);
    if (!t.includes('_')) names.push(`${pre}${t}.json`);
  }
  return names;
}

async function load(symbol, tf) {
  try {
    const r = await fetch(`/api/chart?symbol=${encodeURIComponent(symbol)}&tf=${encodeURIComponent(tf)}`);
    if (r.ok) return { ...(await r.json()), source: 'api' };
  } catch (e) { /* 静态打开（file:// 或本地 http.server）时没有后台，走样本 */ }
  for (const n of fixtureNames(symbol, tf)) {
    const r = await fetch(`fixtures/${n}`);
    if (r.ok) return { ...(await r.json()), source: `样本 ${n}` };
  }
  throw new Error(`取不到 ${symbol} ${tf}（后台没起、仓里也没有这一份样本）`);
}

// ---------------------------------------------------------------- 画一张
function draw(d) {
  state.data = d;
  const bars = d.bars.map((b) => ({ time: b.t / 1000, open: b.o, high: b.h, low: b.l, close: b.c }));
  candle.applyOptions({ priceFormat: priceFormat(d.meta?.tick) });
  candle.setData(bars);

  // ★ K线下标 → 时间：结构里记的是**下标**（i0/i1），图上要的是**时间**。
  //   这里踩过一次：直接拿下标当秒数喂进去，笔和线段全画到 1970 年去了（屏幕上只剩左边挤成一团竖线）。
  const T = (i) => bars[i].time;

  // 笔：除最后一根外实线，最后一根虚线（它的终点还会被更极端的分型替换）
  const pens = d.pens;
  const penA = pens.length ? [{ time: T(pens[0].i0), value: pens[0].p0 }] : [];
  for (let k = 0; k < pens.length - 1; k++) penA.push({ time: T(pens[k].i1), value: pens[k].p1 });
  penSolid.setData(penA);
  penDash.setData(pens.length > 1 ? penA.slice(-1).concat([{ time: T(pens.at(-1).i1), value: pens.at(-1).p1 }]) : []);

  // 线段：已完成的实线、未完成的虚线（画到迄今的极值，跟 Python 同一条）
  const segs = d.segs, done = segs.filter((s) => !s.live), live = segs.find((s) => s.live);
  const segA = done.length ? [{ time: T(done[0].i0), value: done[0].p0 }] : [];
  for (const s of done) segA.push({ time: T(s.i1), value: s.p1 });
  segSolid.setData(segA);
  if (live) {
    const ext = live.dir === 'up' ? live.hi : live.lo;
    let k = live.PI0;
    for (let j = live.PI0; j <= live.PI1; j++) if (d.pens[j] && d.pens[j].p1 === ext) k = j;
    segDash.setData([{ time: T(live.i0), value: live.p0 }, { time: T(d.pens[k].i1), value: ext }]);
  } else segDash.setData([]);

  overlay.setData(bars.length ? [{ time: bars.at(-1).time, value: bars.at(-1).close }] : []);
  chart.timeScale().fitContent();
  // ?last=N：只显示最后 N 根（可分享 / 截图复现同一段）；不带就整段
  // ★ 参数**在不在**要用 has() 判，不能用 Number() 的返回值判：`Number(null)` 是 0、`isFinite(0)` 是 true
  //   ⇒ 不带 ?at= 的时候会被当成 at=0，视图被钉在「序列最开头 ±80 根」，fitContent 白调了。
  //   （截图对账时才照出来：整图那一格显示的是开头两周，不是全序列。）
  const q2 = new URLSearchParams(location.search);
  const num = (k) => (q2.has(k) ? Number(q2.get(k)) : NaN);
  const lastN = num('last'), at = num('at'), span = num('span');
  if (Number.isFinite(lastN) && lastN > 0) {
    chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, bars.length - lastN), to: bars.length + 3 });
  } else if (Number.isFinite(at)) {                 // ?at=<某根K线下标>&span=<看多少根>：对准某一段（可分享、可截图复现）
    const n = Number.isFinite(span) && span > 0 ? span : 160;
    chart.timeScale().setVisibleLogicalRange({ from: at - n / 2, to: at + n / 2 });
  }
  applyToggles();
  renderMeta(d);
  const last = bars.at(-1);
  el('last').textContent = last ? `最新 ${fmtPrice(last.close, d.meta?.tick)}` : '';
  stamp(d);
}

const fmtPrice = (v, tick) => {
  const dec = decimals(tick);
  return v.toLocaleString('zh-CN', { minimumFractionDigits: dec, maximumFractionDigits: dec });
};
const decimals = (tick) => {
  const t = String(tick ?? 0.01);
  return t.includes('.') ? t.split('.')[1].length : 0;
};
const priceFormat = (tick) => ({ type: 'price', precision: decimals(tick), minMove: Number(tick) || 0.01 });

// ---------------------------------------------------------------- 开关
function applyToggles() {
  penSolid.applyOptions({ visible: opts.pen });
  penDash.applyOptions({ visible: opts.pen });
  segSolid.applyOptions({ visible: opts.seg });
  segDash.applyOptions({ visible: opts.seg });
  repaint();
  renderLegend();
  for (const b of document.querySelectorAll('.chip')) {
    const k = b.dataset.key;
    const on = k === 'sigPend' ? opts.sigPend : k.startsWith('sig:') ? opts.sigKinds[k.slice(4)] : opts[k];
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    b.disabled = k.startsWith('sig:') || k === 'sigPend' ? !opts.sig : false;
  }
}

function buildChips() {
  const box = el('panel');
  const add = (label, key, dot) => {
    const b = document.createElement('button');
    b.className = 'chip'; b.type = 'button'; b.dataset.key = key;
    b.innerHTML = (dot ? `<i style="background:${dot}"></i>` : '') + label;
    b.onclick = () => {
      if (key.startsWith('sig:')) opts.sigKinds[key.slice(4)] = !opts.sigKinds[key.slice(4)];
      else opts[key] = !opts[key];
      applyToggles();
    };
    box.appendChild(b);
  };
  add('笔', 'pen', CHART.pen);
  add('线段', 'seg', CHART.seg);
  add('类中枢', 'pc', CHART.pen);
  add('线段中枢', 'sc', CHART.seg);
  add('高一级', 'up', CHART.up_seg);
  add('买卖点', 'sig', CHART.buy);
  for (const k of ['一买', '二买', '三买', '一卖', '二卖', '三卖']) add(k, `sig:${k}`, k.endsWith('买') ? CHART.buy : CHART.sell);
  add('待确认', 'sigPend', CHART.sell);
}

function renderLegend() {
  const items = [];
  if (opts.pen) items.push(['line', CHART.pen, 1, '笔'], ['line-dash', CHART.pen, 1, '未完成的笔']);
  if (opts.seg) items.push(['line', CHART.seg, 2, '线段'], ['line-dash', CHART.seg, 2, '未完成的线段']);
  if (opts.pc) items.push(['box', CHART.pen, 2, '类中枢（与笔同色）'], ['box-split', CHART.pen, 2, '前三实线 / 延续虚线']);
  if (opts.sc) items.push(['box', CHART.seg, 4, '线段中枢（与线段同色）']);
  if (opts.up) items.push(['box', CHART.up_pen, 2, '高一级：类中枢升的'], ['box', CHART.up_seg, 4, '高一级：线段中枢升的']);
  items.push(['tag', CHART.pen, 0, '价签：实底 ＋ 黑字']);
  if (opts.sig) items.push(['tri-fill', CHART.buy, 0, '买卖点（线段中枢层）'], ['tri-hollow', CHART.sell, 0, '空心「·笔」＝类中枢层，「?」＝待确认']);
  el('legend').innerHTML = items.map(([kind, col, w, name]) => {
    const dash = kind === 'line-dash';
    const svg = kind === 'tag'
      ? `<svg width="30" height="14"><rect x="0" y="1" width="30" height="12" rx="3" fill="${col}"/><text x="3" y="10" font-size="9" fill="${CHART.tag_ink}">[ZD,ZG]</text></svg>`
      : kind === 'tri-fill'
        ? `<svg width="30" height="14"><polygon points="15,1 6,13 24,13" fill="${col}"/></svg>`
        : kind === 'tri-hollow'
          ? `<svg width="30" height="14"><polygon points="15,1 6,13 24,13" fill="none" stroke="${col}" stroke-width="2"/></svg>`
          : kind === 'box' || kind === 'box-split'
            ? `<svg width="30" height="14"><rect x="1" y="2" width="28" height="10" fill="${col}22" stroke="${col}" stroke-width="${Math.min(3, w * 0.6)}" ${kind === 'box-split' ? 'stroke-dasharray="6 4"' : ''}/></svg>`
            : `<svg width="30" height="14"><line x1="1" y1="7" x2="29" y2="7" stroke="${col}" stroke-width="${w}" ${dash ? 'stroke-dasharray="5 4"' : ''}/></svg>`;
    return `<span class="lg">${svg}${name}</span>`;
  }).join('');
}

function renderMeta(d) {
  const done = d.segs.filter((s) => !s.live).length;
  const mk = (s) => s.map((x) => `${x.kind}${x.confirmed ? '' : '?'}`).join('·') || '无';
  el('meta').textContent =
    `${d.name || d.symbol} · ${d.tf} ｜ ${d.nbars} 根 ｜ 笔 ${d.pens.length} ｜ 类中枢 ${d.centers.length}`
    + ` ｜ 完成线段 ${done}（+${d.segs.length - done} 未完成）｜ 线段中枢 ${d.seg_centers.length}`
    + ` ｜ 精度 ${d.meta?.tick} ｜ ${d.meta?.pen_rule === 'new' ? '新笔' : '老笔'}`
    + ` ｜ 买卖点 线段中枢层 ${mk(d.signals?.seg || [])} · 类中枢层 ${mk(d.signals?.pen || [])}`
    + ` ｜ 数据源 ${state.source}`;
}

// ---------------------------------------------------------------- 角上的时间
function stamp(d) {
  const t = d.updated ? new Date(d.updated) : null;
  const base = t && !isNaN(t)
    ? `数据 ${shortUtc(d.updated)} UTC ｜ ${ago(t)}`      // 秒在角上只是噪音：K 线本来就是整点/整刻
    : '数据时间未知';
  // 后台这轮没拉到币安、回的是上一次的结果时会带 stale=true：那这格的「N 分钟前」说的是**上一次**，
  // 不标出来它就是一句假话 —— 角上必须自己承认。字段没有 / 为 false 就照常。
  const st = !!d.stale;
  el('updated').textContent = st ? `${base} ｜ ★ 旧数据（本轮拉取失败）` : base;
  el('updated').className = 'badge' + (st ? ' warn' : '');
  el('updated').title = st ? '这是上一次的结果：本轮拉取没成功（后台 stale=true）'
                           : '最后一根 K 线的开盘时间（UTC）';
}
/** "2026-09-29T00:00:00Z" → "2026-09-29 00:00"；形状不是 ISO（后台换了格式）就原样返回，不猜 */
const shortUtc = (s) => {
  const m = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/.exec(String(s));
  return m ? `${m[1]} ${m[2]}` : String(s).replace('T', ' ').replace('Z', '');
};
function ago(t) {
  const m = Math.round((Date.now() - t.getTime()) / 60000);
  if (m < 1) return '刚刚';
  if (m < 60) return `${m} 分钟前`;
  const h = Math.round(m / 60);
  return h < 24 ? `${h} 小时前` : `${Math.round(h / 24)} 天前`;
}
setInterval(() => { if (state.data) stamp(state.data); }, 30000);

// ---------------------------------------------------------------- 接线
function buildPickers() {
  el('symbol').innerHTML = SYMBOLS.map(([v, n]) => `<option value="${v}">${n}</option>`).join('');
  el('tf').innerHTML = TFS.map((t) => `<option value="${t}">${t}</option>`).join('');
  const q = new URLSearchParams(location.search);
  const sym = SYMBOLS.some((s) => s[0] === q.get('symbol')) ? q.get('symbol') : 'BTCUSDT';   // 白名单外不认
  const tf = TFS.includes(q.get('tf')) ? q.get('tf') : '4h';
  el('symbol').value = sym; el('tf').value = tf;
  for (const id of ['symbol', 'tf']) el(id).onchange = () => go();
}

async function go() {
  const symbol = el('symbol').value, tf = el('tf').value;
  const q = new URLSearchParams(location.search);     // 保留 last= 之类的既有参数，别把地址栏洗掉
  q.set('symbol', symbol); q.set('tf', tf);
  history.replaceState(null, '', `?${q}`);            // 可分享、可截图复现
  el('state').textContent = '取数…'; el('state').className = 'badge';
  try {
    const d = await load(symbol, tf);
    draw(d);
    el('state').textContent = d.closed ? '已收盘' : '未收盘（最后一根还在走）';
    el('state').className = 'badge ' + (d.closed ? '' : 'live');
  } catch (e) {
    el('state').textContent = String(e.message || e);
    el('state').className = 'badge bad';
  }
}

buildPickers();
buildChips();
applyToggles();
go();

// 给验收工装一个**只读**入口：并排截图要把网页这一格切到跟 Python 出图同一段 K 线、同一价格带，
// 那就得问图自己「第 i 根在哪个 x、这个价在哪个 y」（timeToCoordinate / priceToCoordinate）。
// 不是功能开关，页面上没有任何东西读它；去掉它，验收那两张图就没法对齐。
window.__app = { chart, state, opts };
