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
const state = { data: null, opts, candleSeries: null };
const primitives = [];
// 往左拖那套状态：span＝现在手上是第几档，spanMax＝后台给的封顶，earliest＝币安真没有了。
// viewSet＝**我们自己摆的那个视口**（用来认事件回声，见 setView）；reqId＝在飞的那一份的号（换品种就作废）。
const paging = { span: 1, spanMax: null, earliest: false, nogain: false, stop: null, loading: false, failedAt: 0, reqId: 0, applying: false };
let viewSet = null;
let settleTimer = 0;
const SETTLE_MS = 40;      // 「自己摆视口」的认回声窗口，见 holdView()

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

// span = 数据档（后端白名单 1、2、4、8……）：1 档 210 天，每翻一档往前多要同样长的一段。
// ★ 这个 **`span` 是发给后台的参数**，跟地址栏里 `?at=N&span=M` 那个「看多少根」**不是一回事**
//   —— 同一个词两个意思，所以地址栏里那个数据档我另叫 `?load=`（见 go()），别混。
async function load(symbol, tf, span) {
  try {
    const r = await fetch(`/api/chart?symbol=${encodeURIComponent(symbol)}&tf=${encodeURIComponent(tf)}&span=${span}`);
    if (r.ok) return vetted({ ...(await r.json()), source: 'api' });
  } catch (e) { /* 静态打开（file:// 或本地 http.server）时没有后台，走样本 */ }
  for (const n of fixtureNames(symbol, tf)) {
    const r = await fetch(`fixtures/${n}`);
    // 样本只有一段：说自己「到最早」是实话（手上就这些），也就不会去要下一档。
    if (r.ok) return vetted({ ...(await r.json()), source: `样本 ${n}`, span: 1, span_max: 1, earliest: true });
  }
  throw new Error(`取不到 ${symbol} ${tf}（后台没起、仓里也没有这一份样本）`);
}

// >>> EARLIER_PAGING （tools/web_more_check.py 抠出来在 node 里真跑；纯函数，不碰 DOM、不碰图）
// 往左拖自动加载更早的 K 线，做四件事，每件都是**纯函数**，好让尺子量的是真身而不是我拼的替身：
//   ① 什么时候该去要下一档   nextSpan()
//   ② 要哪一档               nextSpan()
//   ③ 换数据之后画面放回哪儿  anchorOf() / restoreRange()   ← 这一条是「不许跳」的全部
//   ④ 那两句话什么时候印      moreText()
//   ⑤ 换数据之前的体检        badIndex() / vetted()
const PAGE_FROM = 20;            // 可视区左沿离**已加载的最左一根**不到这么多根 ⇒ 该往前要了
const SPAN_WL_MAX = 16;          // 契约里 span 只认 1、2、4、8、16（Nova 2026-10-04）：发出去的值必须落在这五个里
// ⑤ 凡是**用下标指位置**的地方（笔的 i0/i1、线段的 i0/i1）都得落在这份 bars 里；落不进去就当这份数据没取到。
//    ★ **一根线都不许先画上去**：paint() 是一样一样画的，画到一半才抛，屏幕上就是
//      「K 线已经换成新的、笔还是上一份的」，两套东西互相打架。这不是假想 —— 2026-10-04 的联调工装里
//      真撞出来了（我那份假后台切了 bars 却没重算结构：图换了一半，提示还写着「没取到」）。
//      后台哪天真回一份这样的，页面上该**什么都没变**才对。样本也走同一道体检。
function badIndex(d) {
  const n = (d.bars || []).length, over = (i) => !(i >= 0 && i < n);
  for (const p of d.pens || []) if (over(p.i0) || over(p.i1)) return `笔 [${p.i0}, ${p.i1}]`;
  for (const s of d.segs || []) if (over(s.i0) || over(s.i1)) return `线段 [${s.i0}, ${s.i1}]`;
  return null;
}
function vetted(d) {
  const bad = badIndex(d);
  if (bad) throw new Error(`后台这份数据对不上：${bad} 超出了 ${(d.bars || []).length} 根 —— 图没换`);
  return d;
}
// ① 下一档：白名单是 1、2、4、8……（翻倍），越过封顶就返回 null（null＝别发请求）
function nextSpan(span, spanMax) {
  const s = span * 2;
  return spanMax != null && s > spanMax ? null : s;
}
// ② 为什么不再要了（null＝还能要）。三种「到头」是**三件事**，别塌成一句：
//    earliest＝币安真没有更早的数据了 ／ cap＝我们自己封的顶（币安还有） ／ nogain＝要了但一根没多
function stopReason(s) {
  if (s.earliest) return 'earliest';
  if (s.spanMax != null && s.span >= s.spanMax) return 'cap';
  if (s.nogain) return 'nogain';
  return null;
}
// ① 拖到左边该干什么：'load'＝去要下一档 ／ 'stop'＝到头了，说一句话 ／ null＝不关我的事（离左沿还远）
//    ★ 边界就写在**这一块里**（`>= PAGE_FROM` 就是不触发）：尺子要能改到这里，才能证明它真会红。
function onLeft(s) {
  if (s.from >= PAGE_FROM) return null;
  return stopReason(s) ? 'stop' : 'load';
}
// 地址栏 ?load=N 进来的档位：**只认契约里那五个值 1、2、4、8、16**（Nova 2026-10-04 定的），
// 别的（3、0、-1、"abc"、64…）一律退回它下面的那一档；小于 1 的退回 1。
// ★ 上限**必须封在 16**：发出去的值不在那五个里，后台按契约回 400 ⇒ 首屏整张挂掉（Atlas 两头各打一次挑出来的）。
//   周期自己的封顶（15m 4 / 30m 8 / 1h 以上 16）前端**不猜** —— 后台会在 span_max 里说，见 adopt()。
function ladderSpan(v) {
  const n = Number(v);
  if (!Number.isFinite(n) || n < 1) return 1;               // 非数字/小于 1 ⇒ 1
  return Math.max(1, Math.min(SPAN_WL_MAX, Math.pow(2, Math.floor(Math.log2(n)))));   // 大于 16 ⇒ 16
}
// ⑤ 后台回显说了算（Nova 2026-10-04 定的口径）：我们发出去的那个数只是「请求」，手上到底是第几档、
//    是不是到头了，一律以**响应里的回显**为准（后台会钳档、会标 earliest）。
// ★ 首屏（go）和往左加载（loadEarlier）**共用这一个口** —— 两处各写一遍，迟早只有一处认回显：
//   首屏不认 ⇒ 一开始就 earliest 的品种（AAPL 那种）会白发一次请求；?load=16 在 15m 上被钳到 4 之后，
//   页面还以为自己是 16 档，停法就印错（Atlas 2026-10-04 读代码挑出来的）。
// 纯函数：给「现在手上那份的状态 cur」和「后台回的一份 d」，算出手上该变成什么；调用方 Object.assign 回去。
function adopt(cur, d, prevLen) {
  const s = { span: Number.isFinite(d.span) ? d.span : cur.span,          // 回显的档位就是真档位
              spanMax: Number.isFinite(d.span_max) ? d.span_max : cur.spanMax,
              // 三个字段同一条规矩：**回了就听回显的，没回就维持现状**。
              // 离线的仓里样本就没有这三个字段（老后台也没有）⇒ 那时候等于什么都不改，照旧能翻页。
              earliest: d.earliest == null ? cur.earliest : !!d.earliest, nogain: false };
  // 「要了却一根没多」只有在补数据时才有基准（首屏没有「上一份」可比，就不判这条）
  s.nogain = prevLen != null && (d.bars || []).length <= prevLen && !s.earliest;
  return s;
}
// ④ 三句话。★ 刻意**不合并**成一句「已到最早」：`earliest` 是币安真没有更早的了，
//    而 `span===span_max` 是**我们自己封的顶**——那时候币安明明还有更早的数据，
//    印「已到最早」就是一句假话（跟图脚「数据源」那次是同一类账）。所以分开两句话。
function moreText(s) {
  if (s.loading) return '加载更早数据…';
  if (s.failed) return '更早的数据没取到';
  if (s.stop === 'earliest') return '已到最早';
  if (s.stop === 'cap') return '已到本周期可加载的最早';
  if (s.stop === 'nogain') return '取不到更早数据';   // 要了但一根没多（后台没认这一档）——别打转
  return '';
}
// ③ 「按时间放回原位」：**锚点存时间，不存下标**。往前补数据是往**数组头上插**，
//    同一个下标指向的是**另一根** K 线（插了多少根就错多少根），所以下标一存就跳。
//    存的是「可视区左沿那一根的时间 + 它在左沿外多少根（小数）」——左边多出多少根都不影响它。
function anchorOf(bars, range) {
  if (!bars || !bars.length || !range) return null;
  const k = Math.max(0, Math.min(bars.length - 1, Math.ceil(range.from)));
  return { t: bars[k].t, frac: range.from - k, width: range.to - range.from, oldLen: bars.length, oldFrom: range.from };
}
// 二分找回同一根：时间戳是升序的（后台按时间排），找不到（换了品种/样本对不上）返回 null
function timeIndex(bars, t) {
  let lo = 0, hi = bars.length - 1;
  while (lo < hi) { const m = (lo + hi) >> 1; if (bars[m].t < t) lo = m + 1; else hi = m; }
  return bars.length && bars[lo].t === t ? lo : null;
}
function restoreRange(bars, anchor) {
  const i = timeIndex(bars, anchor.t);
  // 找不回那一根才退回「按右端对」：新数据是往左补的，**离右端的距离**跟下标无关，
  // 拿它兜底至少不跳得离谱。（这不是常态——时间戳对得上就走上面那条。）
  const from = i === null ? bars.length - anchor.oldLen + anchor.oldFrom : i + anchor.frac;
  return { from, to: from + anchor.width };
}
const NOTICE_TEXT = '已接上更早的K线，左侧的笔、线段、中枢和买卖点按新的起点重算';
const NOTICE_MS = 3000;
let noticeTimer = 0;
// 记一句「这一屏里现在有哪些东西、长什么样」：按**时间戳和价格**记，不按下标 ——
// 往左补数据是往数组头上插，同一个下标当场就指向另一根 K 线（跟 anchorOf 是同一条理由）。
// ★ 只记**跟可视窗口有时间重叠**的那些：窗口外也跟着重算了（一画就是全局的），
//   但用户没看那儿 —— 没变就别说，变了才说（Nova 2026-10-04 定的口径，Atlas 补的「可视窗口」）。
// ★ 记哪几层 ＝ **屏幕上看得见的那几层**（Nova 2026-10-04 拍 (a)）：笔、线段、类中枢、线段中枢、买卖点。
//   原先只记笔和线段 —— 可是换档后先变的往往正是中枢：BTC 4h 那对 1↔2 就是**只有线段中枢的 ZD 变了**
//   （65569.2 ↔ 67300），笔和段一动没动，屏幕上的框变了却不出声。看得见的东西变了就得说。
function structKey(d, t0, t1) {
  const ts = (i) => (d.bars[i] || {}).t;
  const ov = (a, b) => a != null && b != null && b >= t0 && a <= t1;   // 区间跟窗口有重叠（含边界）
  const at = (t) => t != null && t >= t0 && t <= t1;                   // 单个时间点落在窗口里
  const inWin = (o) => ov(ts(o.i0), ts(o.i1));
  const row = (o) => `${ts(o.i0)}>${ts(o.i1)}@${o.p0},${o.p1}`;
  const part = (a) => (a || []).filter(inWin).map(row).join('|');
  // 中枢：取**画出来的那个框**的横跨区 ⇒ 跟 layers.js 的 boxes() 同一个取法
  //   （host[PI0].i0 ／ host[PI1].i1。类中枢 host=笔；线段中枢 host=**已完成**线段，别拿 segs 直接取。
  //    样本上 X0/X1 跟这个取法逐条相同，但「画的是哪个」以 boxes() 为准，不押在另一个字段上。）
  const boxes = (zs, host) => (zs || []).map((z) => {
    const a = host[z.PI0], b = host[z.PI1];
    if (!a || !b) return null;
    const up = (z.up || []).map((u) => `${u.ZD},${u.ZG}`).join(';');   // 升级标签也是画在框上的
    return { i0: a.i0, i1: b.i1, s: `${z.ZD},${z.ZG}${z.live ? ',live' : ''}${up ? ',' + up : ''}` };
  }).filter((o) => o && ov(ts(o.i0), ts(o.i1))).map((o) => `${ts(o.i0)}>${ts(o.i1)}@${o.s}`).join('|');
  // 买卖点：一个点 —— 三角和它的字都画在这个 x 上
  const sigs = (a) => (a || []).filter((s) => at(ts(s.bar)))
    .map((s) => `${ts(s.bar)}@${s.price},${s.kind}${s.confirmed === false ? ',未确认' : ''}`).join('|');
  const done = (d.segs || []).filter((s) => !s.live);   // 线段中枢的 host（跟 layers.js doneSegs 同一条）
  return [part(d.pens), part(d.segs), boxes(d.centers, d.pens || []), boxes(d.seg_centers, done),
          sigs((d.signals || {}).seg), sigs((d.signals || {}).pen)].join('#');
}
// 可视窗口 → 时间区间。★ 换档前取一次、换档后用**同一段时间**再取一次：
// 拿换完之后的新窗口去比，比的是「另一段时间」，那就不是「这一屏变没变」了。
function windowOf(bars, range) {
  if (!bars || !bars.length || !range) return null;
  const a = Math.max(0, Math.ceil(range.from)), b = Math.min(bars.length - 1, Math.floor(range.to));
  if (b < a) return null;
  return { t0: bars[a].t, t1: bars[b].t };
}
// <<< EARLIER_PAGING

// ---------------------------------------------------------------- 画一张
// ★ 画（paint）和**摆视口**（draw 里那一段）分开了：往左补数据之后重画，**不能**再走「摆视口」
//   那一段（它要么 fitContent 缩成一团、要么按 ?last/?at 跳走）—— 补数据时视口由 place() 按**时间**放回原位。
function paint(d) {
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
  applyToggles();
  renderMeta(d);
  const last = bars.at(-1);
  el('last').textContent = last ? `最新 ${fmtPrice(last.close, d.meta?.tick)}` : '';
  stamp(d);
}

// 装一张新数据：**先画，再摆视口**。keep 是补数据前抓的锚点（见 paging）；给了它就走「按时间放回原位」。
function draw(d, keep) {
  paint(d);
  if (keep) { place(d, keep); return; }
  chart.timeScale().fitContent();
  holdView();                                   // fitContent 也是「我们自己摆的」，给它同一个认回声的窗口
  // ?last=N：只显示最后 N 根（可分享 / 截图复现同一段）；不带就整段
  // ★ 参数**在不在**要用 has() 判，不能用 Number() 的返回值判：`Number(null)` 是 0、`isFinite(0)` 是 true
  //   ⇒ 不带 ?at= 的时候会被当成 at=0，视图被钉在「序列最开头 ±80 根」，fitContent 白调了。
  //   （截图对账时才照出来：整图那一格显示的是开头两周，不是全序列。）
  const q2 = new URLSearchParams(location.search);
  const num = (k) => (q2.has(k) ? Number(q2.get(k)) : NaN);
  const lastN = num('last'), at = num('at'), viewSpan = num('span');
  if (Number.isFinite(lastN) && lastN > 0) {
    setView({ from: Math.max(0, d.bars.length - lastN), to: d.bars.length + 3 });
  } else if (Number.isFinite(at)) {               // ?at=<某根K线下标>&span=<看多少根>：对准某一段（可分享、可截图复现）
    const n = Number.isFinite(viewSpan) && viewSpan > 0 ? viewSpan : 160;
    setView({ from: at - n / 2, to: at + n / 2 });
  } else markView();
}

// 摆视口只走这一个口：**记下这次是我们自己摆的**，好把随后那一次事件回声认出来
// （不然 fitContent 自己触发的那一下会被当成「用户拖到左边了」，一打开页面就去要下一档）。
// ★ 只记「要的那个」还不够：LWC 会把视口**微调**一下再报一次（要 from=-50，它随后报 -53.373），
//   而 getVisibleLogicalRange 是**懒更新**的 —— 摆完同步读回来还是旧值，光靠读回来认不出后一下。
//   所以自己摆完先记一笔「接下来那一次视口事件是我的回声」，**由事件本身来销账**（见下面的订阅），
//   不再拿时钟当判据。
function holdView() {
  paging.applying = true;
  clearTimeout(settleTimer);
  // 兜底：万一下一次视口事件永远不来（摆成跟原来一样，LWC 就不吭声），别让 applying 一直挂着
  // 把用户下一次拖的第一下吃掉。这是**兜底**，不是判据 —— 判据是「真有没有人动过输入设备」。
  settleTimer = setTimeout(() => { paging.applying = false; markView(); }, SETTLE_MS);
}
// ★★ 怎么认出「这一下是用户弄的」：**问输入设备，不问时钟**（2026-10-04 改的）。
//   原来只靠上面那个 40ms 窗口 —— 那是个**替身**：它猜「刚才多半是我们自己摆的」，猜错就出事。
//   Atlas 2026-10-04 在三次里红过一次：**打开页面没人拖，它自己发了 span=2**。机理很清楚：
//   `?at=40&span=180` 摆出来的是 from=-50，LWC 归一化后回一个 -53.373 的**回声** ——
//   这个回声跟我们要的不一样（sameRange 认不出），而 -53.373 < 20 又正好满足「贴到左沿」，
//   于是**我们自己的回声被当成了用户在拖**。机器快，回声落在 40ms 窗口里就没事；机器慢，落在窗口外，就发请求。
//   ⇒ 判据换成真东西：**用户有没有真的动过输入设备**（pointerdown/move、wheel、touch、keydown）。
//     自己摆视口不产生这些事件；拖、滚、捏一定会。脚本摆视口（工装、?at=?last=、fitContent）从此
//     一律不算「用户要看更早的」—— 这是对的：脚本摆一下不等于有人想看。
//   ★ 时序竞争**证不了不存在**：快机器上连跑 10 次全绿说明不了慢机器上不出来。工装里有
//     `--throttle=N`（CDP 把 CPU 拖慢）可以故意把这一格跑红，规矩是**改之前红、改之后绿**。
//   ★★ `pointermove` **只在按着键的时候**才算（Atlas 2026-10-04 多跑的一格逮到的）：
//     鼠标**停在图上晃、一个键都不按**，pointermove 照样一直在刷 —— 于是「1.5 秒内动过输入设备」
//     成立，视口随便一点变化都被当成用户在拖。桌面上从链接点进来、鼠标正好落在图上，是最常见的情形
//     ⇒ 没人拖，页面自己翻了一档：跟 40ms 时钟那个 bug 同一张脸，换条路又回来了（降速 4× 下 6/6 红）。
//     `buttons` 是「此刻按着哪几个键」的位掩码：0 ＝ 没按 ⇒ 那是悬停，不是拖。
//     touchmove / wheel / keydown 照旧：触摸没有「悬停」这回事，滚轮和方向键本身就是动作。
const INPUT_MS = 1500;      // 最后一次真实输入之后这么久之内，视口变化算用户的（拖拽会一直刷 pointermove）
let lastInputAt = 0;
for (const [ev, real] of [
  ['pointerdown', () => true],
  ['pointermove', (e) => e.buttons !== 0],   // ★ 悬停不算：没按键就是在看，不是在拖
  ['wheel', () => true],
  ['touchstart', () => true],
  ['touchmove', () => true],
  ['keydown', () => true],
]) {
  el('chart').addEventListener(ev, (e) => { if (real(e)) lastInputAt = Date.now(); },
                               { passive: true, capture: true });
}
const userDrove = () => Date.now() - lastInputAt <= INPUT_MS;
function setView(r) {
  chart.timeScale().setVisibleLogicalRange(r);
  markView(r);
  holdView();
}
function markView(r) {
  viewSet = r || chart.timeScale().getVisibleLogicalRange();
}
function place(d, anchor) {
  setView(restoreRange(d.bars, anchor));
}

// ---------------------------------------------------------------- 往左拖 ⇒ 要更早的 K 线
// 提示挂在图上（`#more`），不塞进顶栏那排徽标：用户是在图**左边**做这个动作，话就要说在眼睛在看的地方。
let moreTimer = 0;
function renderMore(s, hold) {
  const n = el('more');
  if (!n) return;
  const txt = moreText(s);
  clearTimeout(moreTimer);
  n.textContent = txt;
  n.classList.toggle('on', !!txt);
  n.classList.toggle('end', !!txt && !s.loading);
  // 到头那两句话是**回答用户那一下拖**的，说一次就够；常驻会变成一块贴在图上不走的膏药。
  if (txt && !s.loading && hold) moreTimer = setTimeout(() => n.classList.remove('on', 'end'), hold);
}
// ---------------------------------------------------------------- 换档之后那句话
// 往左多要一段 K 线 ＝ **整份重算**（原文算法决定的：起点一挪，后面的笔和线段全都重新划分，拼接是假的）。
// 所以换完之后左边那些线可能已经不是用户刚才看到的样子了 —— 这时候得说一句，
// 不然「图怎么自己变了」就成了一桩没有解释的事。
function showNotice() {
  const n = el('notice');
  if (!n) return;
  n.textContent = NOTICE_TEXT;
  n.classList.add('on');
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => n.classList.remove('on'), NOTICE_MS);
}
function resetPaging(span) {
  paging.span = ladderSpan(span); paging.spanMax = null; paging.earliest = false; paging.nogain = false;
  paging.loading = false; paging.failedAt = 0; paging.applying = false;
  clearTimeout(settleTimer);                     // 上一份数据的「认回声窗口」别带到这一份上
  paging.reqId++;                                // 在飞的那一份作废（换品种/周期了）
  renderMore({});
}
const sameRange = (a, b) => !!b && Math.abs(a.from - b.from) < 0.5 && Math.abs(a.to - b.to) < 0.5;

// 一次只飞一个（paging.loading 就是那道闸）；失败退避 FAIL_COOLDOWN，别在一次拖拽里把后台敲烂。
const FAIL_COOLDOWN = 10000;
chart.timeScale().subscribeVisibleLogicalRangeChange((r) => {
  if (!r || !state.data) return;
  // 自己摆的那一下（含 LWC 随后那点微调）：认下来当新基准，销掉 applying，**不触发**。
  // ★ 基准每次事件都往前挪一格（原来只在窗口末尾挪一次）—— 这样连着来两次回声也不会漏。
  if (paging.applying) { paging.applying = false; markView(r); return; }
  if (sameRange(r, viewSet)) return;                 // 视口没真动
  if (!userDrove()) return;                          // ★ 没人在动输入设备 ⇒ 这是脚本摆的/回声，不是用户要看更早的
  const act = onLeft({ from: r.from, span: paging.span, spanMax: paging.spanMax,
                       earliest: paging.earliest, nogain: paging.nogain });
  if (act === null) { if (!paging.loading) renderMore({}); return; }           // 离左沿还远：把话收掉
  if (act === 'stop') return renderMore({ stop: stopReason(paging) }, 2600);
  if (paging.loading || Date.now() - paging.failedAt < FAIL_COOLDOWN) return;  // 一次只飞一个 ＋ 失败退避
  loadEarlier(nextSpan(paging.span, paging.spanMax));
});

async function loadEarlier(span) {
  const own = state.data;
  const id = ++paging.reqId;
  const symbol = el('symbol').value, tf = el('tf').value;
  paging.loading = true;
  renderMore({ loading: true });
  try {
    const d = await load(symbol, tf, span);
    if (id !== paging.reqId) return;             // 等数据这段时间里换了品种/周期 ⇒ 这一份丢掉，别画上去
    // ★ 锚点要在**动数据之前**抓（setData 一换，视口的下标含义就变了），但要是**数据到手的这一刻**抓，
    //   不是发请求的那一刻：这一趟可能要等一两秒，用户在这期间还会接着往左拖 —— 拿发请求时的位置去「放回原位」，
    //   就是把他刚拖出来的画面**弹回去**（工装里量到过：拖到一半来的数据，画面被拽回 200px）。
    //   此刻 state.data 还是旧那份，bar 的时间戳还是旧的下标，抓锚点正合适。
    const range0 = chart.timeScale().getVisibleLogicalRange();
    const anchor = anchorOf(own.bars, range0);
    // ★ 基准要在**动数据之前**取：换完之后再取就没得比了（比的就是换前换后）。
    const win = windowOf(own.bars, range0);
    const keyBefore = win && structKey(own, win.t0, win.t1);
    Object.assign(paging, adopt(paging, d, own.bars.length));   // 回显说了算（钳档 / earliest / 有没有多出来）
    setUrl();
    draw(d, anchor);
    // 同一段时间、换完之后再取一次：不一样 ⇒ 用户正看着的那一屏被重算了 ⇒ 说一句，3 秒自己收
    if (win && structKey(d, win.t0, win.t1) !== keyBefore) showNotice();
    renderMore({ stop: stopReason(paging) }, 2600);
  } catch (e) {
    paging.failedAt = Date.now();
    renderMore({ failed: true }, 4000);
    console.warn('更早的数据没取到：', e);
  } finally {
    paging.loading = false;
  }
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
  watchOverflow(box);
}

// ★ 图层那一行在手机上装不下（13 个 chip，`scrollWidth` 953 / `clientWidth` 390）——2026-10-03 真机反馈：
//   右边被切掉，看着像"还有一个按钮看不到"。它**本来就能横滑**（style.css 的 `overflow-x: auto`），
//   缺的是**提示**。这里只挂两个类，渐隐由 CSS 画：右边还有内容才 `fade-r`、左边还有才 `fade-l`，
//   滑到头就不淡 —— 不然"滑到头了还在淡"本身又是一句假话。
//   只在窄屏那档 CSS 里生效（桌面是换行排的，没有横滑这件事）。
function watchOverflow(box) {
  const hint = () => {
    const max = box.scrollWidth - box.clientWidth;
    box.classList.toggle('fade-l', max > 1 && box.scrollLeft > 1);
    box.classList.toggle('fade-r', max > 1 && box.scrollLeft < max - 1);
    box.classList.toggle('fade-lr', max > 1 && box.scrollLeft > 1 && box.scrollLeft < max - 1);
  };
  box.addEventListener('scroll', hint, { passive: true });
  addEventListener('resize', hint);
  addEventListener('orientationchange', hint);
  hint();                                 // 验收工装要重算，`dispatchEvent(new Event('resize'))` 即可
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
  // ★ 价签那一格**不能用定宽 SVG**（2026-10-03 真机反馈：`[ZD,ZG]` 缺了右括号）。
  //   原来样例是 `<svg width="30">` ＋ 里面 `<text font-size="9">`：那串字**实测 35.23px**、起点 x=3
  //   ⇒ 越界 8.23px。注意这跟「真机太窄」无关 —— SVG 定宽 30，**桌面宽度下一样缺右括号**。
  //   改成 HTML 一格：宽由浏览器按字量出来，写死的那一头就没了（同一类账：图脚那把尺的 44 字预算）。
  //   样例文字与 Python 的图例一字不差（`full_common.py:270` 画的就是 `[ZD, ZG]`，带空格）。
  el('legend').innerHTML = items.map(([kind, col, w, name]) => {
    const dash = kind === 'line-dash';
    const svg = kind === 'tag'
      ? `<span class="tagsw" style="background:${col};color:${CHART.tag_ink}">[ZD, ZG]</span>`
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

// >>> SIG_TIER_TEXT —— tools/web_footer_check.py 把这两行之间**整段抠出来单跑**（纯函数，不碰 DOM）。
//     抠不到这块，尺子直接报红；改这里就等于改那把尺子的被测量。
// 买卖点那段**按 kind 归并计数**，不逐个列。原先逐个 join：仓里的样本只有 4~17 个信号
//（btc_4h 4 个＝11 字符、zec_1h 17 个＝50 字符），看着就是一句归纳；换成 Bram 后台的实时源
//（ZEC 15m，20160 根）一次 66 个 ⇒「类中枢层」那一层列表 **197 字符＝1549.6px**（390px 视口下
// 图脚格只有 **362px**），连标签整段 256 字符＝2005.5px ⇒ **整块图脚 8 行**。
// 归并之后每层各一行（实测 170.3 / 245.6px）。
// ★ 尺子量的主语是**每个层级那一段「标签＋列表」整句**（≤ 44 字符），标签是**从下面 renderMeta
//   那个模板里读**的、不在尺子里另抄一份 —— 以后改标签名，尺子自动跟着改；标签抠不到就报错。
//   ★ 只量列表会假绿：列表卡在 44 字时，加上「线段中枢层 」就是 47 字 ≈ 381px > 362px，是要换行的。
// ★ 不是「不小心写长了」：逐个列的长度**跟着信号数涨**，样本比线上小两个数量级，尺子就量不到 ——
//   这类毛病只在实时数据上显形。归并之后长度只跟**种类数**有关（最多 6 种 × 已确认/待确认），
//   与 K 线多少根无关。
const SIG_KINDS = ['一买', '二买', '三买', '一卖', '二卖', '三卖'];   // 与上面 chip 同序，出图稳定
function sigTierText(s) {
  const n = new Map();
  for (const x of s) {
    const k = x.kind + (x.confirmed ? '' : '?');   // 「?＝待确认」，与图例同一套写法
    n.set(k, (n.get(k) || 0) + 1);
  }
  // 排序：已知 kind 按 SIG_KINDS 序（未确认的紧跟同 kind 之后），认不出的排最后 —— 引擎将来加了
  // 新类型，这里要看得见，不许静默吞掉（与「判据只许有一处」同一条账）。0 个的不出现。
  const rank = (k) => { const i = SIG_KINDS.indexOf(k.replace('?', '')); return i < 0 ? 99 : i * 2 + (k.endsWith('?') ? 1 : 0); };
  return [...n.entries()].sort((a, b) => rank(a[0]) - rank(b[0]))
    .map(([k, c]) => (c > 1 ? `${k}×${c}` : k)).join('·') || '无';
}
// <<< SIG_TIER_TEXT

// >>> RENDER_META  （tools/web_footer_check.py 抠出来配假 DOM 真跑，量图脚整句）
// ★ 2026-10-03 线上逮到的那个洞（图脚末尾「｜ 数据源」后面**常年空着**）的根因不是模板写错，
//   而是模板印的 `state.source` **从来没被赋过值** —— load() 把出处挂在**返回对象**上
//   （'api' ／ '样本 x.json'），draw() 只存了 `state.data`。当时的修法是给 draw() 补一行接线，
//   Atlas 随即指出那还留着第二个洞：**接线有顺序** —— 把 renderMeta(d) 挪到接线前面，
//   真页面会印**上一次** load 的出处，而尺子量的是它自己拼出来的顺序，照样绿。
//   ⇒ 现在的写法让那个顺序**不存在**：直接从传进来的 d 上取，不经中间的 state。
//   ★ 教训（写给下一个动这里的人）：**「模板印了什么」和「那个值从哪来」是两件事**；
//     中间多一个变量就多一处能走错的接线。这里不留中间变量。
function sourceLabel(src, stale) {
  // 'api' 是给日志看的词，用户看不懂 —— 说人话。但 stale 为真时数据是**上一轮**从币安拉的，
  // 那时写「实时」就是一句假话（角上同时挂着「★ 旧数据（本轮拉取失败）」），所以分两态。
  // ★ refreshing（后台正在后台刷、手上这份还是好的）不另起第三态：数据本身没坏，照写「实时」。
  if (src === 'api') return stale ? '币安缓存' : '币安实时';
  return src || '未知';        // 离线样本原样透出；字段缺就写「未知」—— 空着是看不出来，未知是看得出来的不知道
}

function renderMeta(d) {
  const done = d.segs.filter((s) => !s.live).length;
  el('meta').textContent =
    `${d.name || d.symbol} · ${d.tf} ｜ ${d.nbars} 根 ｜ 笔 ${d.pens.length} ｜ 类中枢 ${d.centers.length}`
    + ` ｜ 完成线段 ${done}（+${d.segs.length - done} 未完成）｜ 线段中枢 ${d.seg_centers.length}`
    + ` ｜ 精度 ${d.meta?.tick} ｜ ${d.meta?.pen_rule === 'new' ? '新笔' : '老笔'}`
    + ` ｜ 买卖点 线段中枢层 ${sigTierText(d.signals?.seg || [])} · 类中枢层 ${sigTierText(d.signals?.pen || [])}`
    + ` ｜ 数据源 ${sourceLabel(d.source, d.stale)}`;
}
// <<< RENDER_META

// ---------------------------------------------------------------- 角上的时间
// ★ 2026-10-03 真机反馈（小栋，iPhone / BTC 4h）改的口径：原来角上写
//   「数据 2026-10-03 12:00 UTC ｜ 3 小时前」—— 12:00 是**最后一根 K 线的开盘时间**，
//   **不是数据有多旧**（价格是实时的，旁边还写着「未收盘」）。用户读到的是「数据 3 小时前」。
//   现在两件事各自带名字，谁也别冒充谁：
//     本根 = 最后一根 K 线的开盘时间（"本根 12:00 开盘"）
//     数据 = 后台从币安取数的时间（payload 里的 fetched_at，"数据 14:50 刷新"）
//   fetched_at 缺（离线样本、旧后台）就**只说本根** —— 不知道的事不编。
function stamp(d) {
  const t = d.updated ? new Date(d.updated) : null;
  const f = d.fetched_at ? new Date(d.fetched_at) : null;
  const bar = t && !isNaN(t) ? `本根 ${shortUtc(d.updated)} 开盘` : '数据时间未知';
  const fresh = f && !isNaN(f) ? ` ｜ 数据 ${shortUtc(d.fetched_at)} 刷新` : '';   // 秒在角上只是噪音
  // 后台这轮没拉到币安、回的是上一次的结果时会带 stale=true：那这格的取数时间说的是**上一次**，
  // 不标出来它就是一句假话 —— 角上必须自己承认。字段没有 / 为 false 就照常。
  const st = !!d.stale;
  const base = bar + fresh;
  el('updated').textContent = st ? `${base} ｜ ★ 旧数据（本轮拉取失败）` : base;
  el('updated').className = 'badge' + (st ? ' warn' : '');
  // 相对时间（"3 小时前"）只放 title：角上那格宽度有限，而且相对时间依赖**客户端时钟**，
  // 钟不准就会说错话 —— 绝对时间不会。相对值在这里仍有用（一眼看出多旧），所以不删。
  const rel = f && !isNaN(f) ? `（${ago(f)}）` : '';
  el('updated').title = st
    ? `这是上一次的结果：本轮拉取没成功（后台 stale=true）；「数据 … 刷新」说的是那一次的取数时间（UTC）${rel}`
    : `本根＝最后一根 K 线的开盘时间（UTC）；数据＝后台从币安取数的时间（UTC）${rel}，价格随它更新`;
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
  for (const id of ['symbol', 'tf']) el(id).onchange = () => go(1);   // 换品种/周期：回到 1 档重来
}

// 地址栏只写**真话**：`load` 只在本档 >1 时挂上去（1 档是默认值，写了是噪音，换品种时还得记得抹掉）。
function setUrl() {
  const q = new URLSearchParams(location.search);     // 保留 last= / at= 之类的既有参数，别把地址栏洗掉
  q.set('symbol', el('symbol').value); q.set('tf', el('tf').value);
  if (paging.span > 1) q.set('load', paging.span); else q.delete('load');
  history.replaceState(null, '', `?${q}`);            // 可分享、可截图复现
}

async function go(span = 1) {
  const symbol = el('symbol').value, tf = el('tf').value;
  resetPaging(span);
  setUrl();
  const id = paging.reqId;                            // 连点两次品种：先发的那份回来时已经不是它了，别画
  paging.loading = true;        // 这一份还在飞（换品种时旧图还挂在屏上）⇒ 别在这中间再插一个「更早」的请求
  el('state').textContent = '取数…'; el('state').className = 'badge';
  try {
    const d = await load(symbol, tf, paging.span);
    if (id !== paging.reqId) return;
    Object.assign(paging, adopt(paging, d));     // ★ 首屏也认回显：一开始就 earliest 的品种不该白发请求
    setUrl();                                    // 后台钳过档的话（15m 要 16 钳到 4），地址栏写**真**档位
    draw(d);
    el('state').textContent = d.closed ? '已收盘' : '未收盘（最后一根还在走）';
    el('state').className = 'badge ' + (d.closed ? '' : 'live');
  } catch (e) {
    if (id !== paging.reqId) return;
    el('state').textContent = String(e.message || e);
    el('state').className = 'badge bad';
  } finally {
    if (id === paging.reqId) paging.loading = false;
  }
}

buildPickers();
buildChips();
applyToggles();
// ?load=N：直接打开某一档（可分享 / 可截图复现；N 不在白名单上就退回它下面的那一档）
go(ladderSpan(new URLSearchParams(location.search).get('load')));

// 给验收工装一个**只读**入口：并排截图要把网页这一格切到跟 Python 出图同一段 K 线、同一价格带，
// 那就得问图自己「第 i 根在哪个 x、这个价在哪个 y」（timeToCoordinate / priceToCoordinate）。
// 不是功能开关，页面上没有任何东西读它；去掉它，验收那两张图就没法对齐。
window.__app = { chart, state, opts, paging };
