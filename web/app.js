// chanlun.surfers.cc 前端 —— 接线：取数 → 建图 → 开关 → 角上的「最后更新时间」。
//
// 数据只认一个形状（`tools/make_web_fixture.py` 就是它的可执行定义，后台卡 card-29a45ab6-0ac 照着吐）：
//   {symbol, tf, name, updated, closed, bars[], pens[], segs[], centers[], seg_centers[], signals{seg,pen}, meta{tick,pen_rule}}
// 取不到后台就退回 `fixtures/`（离线也能看、也能截图对账）；两边都没有就老实说取不到，不画半张图。
import { CHART, PAGE, CANDLE, WIDTH, SUB } from './theme.js';
import { makeBoxPrimitive, makeAnnotPrimitive, shownOf } from './layers.js';

const LWC = window.LightweightCharts;

// 配色灌进 CSS 变量（style.css 不写死任何色值 —— 色只有一个出处：theme.js → render/style.py）
for (const [k, v] of Object.entries(PAGE)) document.documentElement.style.setProperty(`--${k}`, v);
// ★ 徽标的两个强调色也在这里出。原先 style.css 里写死了 `#ffbc3c`，而 style.py 的 AM 是 `#ffbe3c`
//   —— 差 2，肉眼看不出来，`tools/web_theme_sync.py` 也看不出来（它只读 theme.js，读不到 CSS）。
//   现在 CSS 里只剩 var()，值的来源还是这一处；边框是把同色压到页面底色上算出来的（不另发明一个色）。
const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const mix = (a, b, k) => '#' + rgb(a).map((c, i) => Math.round(c * k + rgb(b)[i] * (1 - k))
  .toString(16).padStart(2, '0')).join('');                     // mix(a,b,k) = k·a + (1−k)·b
// 给 theme.js 的色**加一个透明度**（不新造色）：成交量的柱子压在结构底下，实心太重。
// 写法跟图上中枢框一致（layers.js 里是 `rgba(col, fill)`，fill 是 0-255）—— 色仍只有 theme.js 一个出处。
const hexA = (h, a) => `rgba(${rgb(h).join(',')},${a})`;
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

// 副图那两个开关（成交量／MACD，卡 card-68704ee6-a5a）的初值：**桌面开、手机关**。
// ★ 它们**不进 DEFAULTS**：那个对象记的是「TradingView 的默认值」（那一组是卡面点名的，不许顺手改），
//   而这两颗跟 pine 的默认值无关，跟**屏宽**有关 —— 两套理由别挤在一个对象里。
//   手机上关的理由跟 card-b9792318-91d 是同一条（小栋 2026-10-04 05:00Z：手机上让图占满）：
//   MACD 那一格要吃掉主图三成高度，手机上没那么多地方可给。
//   ★ 760 这个数**不是这里发明的** —— style.css 那一档窄屏断点就是它（同一件事的另一半，改一起改）。
// ★ 地址栏 `?vol=0|1` / `?macd=0|1` 可以指名（可分享、可截图复现，工装也拿它把两种状态都摆出来）；
//   不写就是这一屏的默认。默认值与"写不写进地址栏"比的是**同一个数**（SUB_DEF，加载时定死的那一份）。
const NARROW = () => matchMedia('(max-width:760px)').matches;
const SUB_Q = new URLSearchParams(location.search);
const SUB_DEF = !NARROW();
const subParam = (k) => (SUB_Q.get(k) === '1' ? true : SUB_Q.get(k) === '0' ? false : SUB_DEF);

const el = (id) => document.getElementById(id);
const opts = { ...DEFAULTS, sigKinds: { ...DEFAULTS.sigKinds } };
opts.vol = subParam('vol');
opts.macd = subParam('macd');
const state = { data: null, opts, candleSeries: null };
const primitives = [];
// 往左拖那套状态：span＝现在手上是第几档，spanMax＝后台给的封顶，earliest＝币安真没有了。
// viewSet＝**我们自己摆的那个视口**（用来认事件回声，见 setView）；reqId＝在飞的那一份的号（换品种就作废）。
const DEFAULT_MEASURE = 'macd';       // 后台的缺省也是它（core/signals.py 的 MEASURES）；地址栏里不写它
// ★ measure 的初值是**地址栏说的那个**（可分享、可截图复现），不是写死的缺省 —— 但地址栏点名的那个
//   后台认不认只有 /api/meta 知道，所以首屏是「先等名单、再发图表那一趟」，见文件末尾的启动那几行。
const paging = { span: 1, spanMax: null, earliest: false, nogain: false, stop: null, loading: false, failedAt: 0, reqId: 0, applying: false,
                 measure: new URLSearchParams(location.search).get('measure') || DEFAULT_MEASURE };

// ---- 背驰看法（卡 card-84091d2d-c97：四选一、默认不动、图脚标明当前用的是哪种）----
// 口径在 docs/spec/背驰.md 第六节，四个名字的出处是 core/signals.py 的 MEASURES 上面那一行。
// ★ 四个名字**不写死在前端**（跟图层那份 SHOWN_LAYERS 一个道理：两份名单迟早错开，那时候用户点的
//   那颗和后台算的那份就不是一回事了）：**能切哪几种以 /api/meta 的 measures 为准**，前端只负责把
//   代号翻成人话。翻不出来（后台加了第五种、我这儿还没起名）⇒ 原样印代号 + title 里说明白，
//   **不吞** —— 宁可难看，也不能让后台真有的东西在页面上凭空消失。
// （代号 → 人话那张表在图脚那一块里，见 RENDER_META —— 图和脚用的是同一份，别在这儿再抄一遍。）
// list 空 ⇒ 这一组不画（离线样本、旧后台：不知道的事不编，页面上一个字都不多）。
// ★ orig：**哪些看法不是 108 课原文**由 /api/meta 说（card-6381042d-03f），前端不写死名字。
//   `orig[id] === false` ⇒ 那颗芯片挂「非原文」那枚小标；**读不到就一个标都不挂**（不知道的事不编）。
const measures = { list: [], orig: {} };
let viewSet = null;
let settleTimer = 0;
const SETTLE_MS = 40;      // 「自己摆视口」的认回声窗口，见 holdView()

// 图上那一刻怎么念 —— **只此一份**：时间轴上的刻度、光标读数里的时刻，念的是同一句。
// （抄两份的话，同一根 K 线在两个地方会有两种写法，那时候"读数"就是在跟时间轴打架。）
const timeLabel = (t) => new Date(t * 1000).toISOString().slice(0, 16).replace('T', ' ') + ' UTC';

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
  localization: { locale: 'zh-CN', timeFormatter: timeLabel },
});

const candle = chart.addSeries(LWC.CandlestickSeries, {
  upColor: CANDLE.up, downColor: CANDLE.dn, borderVisible: false,
  wickUpColor: CANDLE.up, wickDownColor: CANDLE.dn,
  priceLineVisible: false,
});
// 成交量（卡 card-68704ee6-a5a）：**叠在主图窗格的下沿**（自己一根价格轴 'vol'），不另占一格高度 ——
// 手机上这一条很重要：主图的高度就是用户的全部视野（card-b9792318-91d 刚把图拉满）。
// ★ 建在 K 线之后、笔/线段**之前**：这个库里**建系列的次序就是画的次序**（下面 overlay 那条注释讲的是同一件事）
//   ⇒ 成交量画在笔/线段/中枢的底下，不去挡结构（DIF/DEA 那两条线单独一格，跟这个无关）。
const VOL_ALPHA = 0.5;
const volSeries = chart.addSeries(LWC.HistogramSeries, {
  priceScaleId: 'vol', priceFormat: { type: 'volume' },
  lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false,
});
// 压在下面 18%：top=0.82 是那一格里的**位置**（0 是顶、1 是底），跟主图的对数价轴互不干涉（它自己一根轴）。
volSeries.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

// pane 缺省（undefined）＝第 0 格（主图）；副图那两条线传 1（见 buildSub）。
// 副图那两条线也走这个 helper：它们的「不画价格线 / 不画末值 / 不画十字线光标」跟主图的线是同一条账。
const line = (o, pane) => chart.addSeries(LWC.LineSeries, {
  priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, ...o,
}, pane);
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
async function load(symbol, tf, span, measure) {
  try {
    const q = new URLSearchParams({ symbol, tf, span: String(span) });
    // ★ 名单还没到手（离线样本、旧后台、或者首屏那个并行的 /api/meta 还没回来）⇒ measure 一个字都不带，
    //   走后台自己的缺省。**这不是省事**：旧后台的查询白名单里没有 measure，多带一个参数就是 400，
    //   整张图会挂在这一个词上。
    if (measures.list.length && measure) q.set('measure', measure);
    const r = await fetch(`/api/chart?${q}`);
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
  const s = { measure: typeof d.measure === 'string' && d.measure ? d.measure : cur.measure,
              span: Number.isFinite(d.span) ? d.span : cur.span,          // 回显的档位就是真档位
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
// ★ 再收一格（Nova 2026-10-04 定的口径）：**关着的层不算「看得见」**。类中枢、高一级、买卖点
//   默认就是关的 —— 那些层重算了用户屏幕上什么也没动，这时候喊一句「结构重算了」就是喊狼。
//   `shown`（＝ shownOf(opts)）由调用点传进来，**跟 layers.js 画图用的是同一个函数**：判据那边
//   绝不另写一份过滤（两份迟早在某一格上错开）。不传 `shown` ＝ 五层全比（老口径，尺里量窗口取法的用例走这条）。
function structKey(d, t0, t1, shown) {
  const sh = shown || null;
  const on = (k) => !sh || !!sh[k];        // 这一层画没画（没给开关就当作画着）
  const ts = (i) => (d.bars[i] || {}).t;
  const ov = (a, b) => a != null && b != null && b >= t0 && a <= t1;   // 区间跟窗口有重叠（含边界）
  const at = (t) => t != null && t >= t0 && t <= t1;                   // 单个时间点落在窗口里
  const inWin = (o) => ov(ts(o.i0), ts(o.i1));
  const row = (o) => `${ts(o.i0)}>${ts(o.i1)}@${o.p0},${o.p1}`;
  const part = (a) => (a || []).filter(inWin).map(row).join('|');
  // 中枢：取**画出来的那个框**的横跨区 ⇒ 跟 layers.js 的 boxes() 同一个取法
  //   （host[PI0].i0 ／ host[PI1].i1。类中枢 host=笔；线段中枢 host=**已完成**线段，别拿 segs 直接取。
  //    样本上 X0/X1 跟这个取法逐条相同，但「画的是哪个」以 boxes() 为准，不押在另一个字段上。）
  //   高一级的标签跟着 `up` 开关走（layers.js 里那个 if 用的就是 sh.up）。
  const boxes = (zs, host, upOn) => (zs || []).map((z) => {
    const a = host[z.PI0], b = host[z.PI1];
    if (!a || !b) return null;
    const up = (upOn ? (z.up || []) : []).map((u) => `${u.ZD},${u.ZG}`).join(';');   // 升级标签也是画在框上的
    return { i0: a.i0, i1: b.i1, s: `${z.ZD},${z.ZG}${z.live ? ',live' : ''}${up ? ',' + up : ''}` };
  }).filter((o) => o && ov(ts(o.i0), ts(o.i1))).map((o) => `${ts(o.i0)}>${ts(o.i1)}@${o.s}`).join('|');
  // 买卖点：一个点 —— 三角和它的字都画在这个 x 上。画不画由 shownOf 说了算
  //   （大开关 ＋ 六个 kind 的 chip ＋ 待确认；带了 shown 就必须带 sigAt，缺了当场炸，不静默放过）
  const sigs = (a) => (a || []).filter((s) => at(ts(s.bar)) && (!sh || sh.sigAt(s)))
    .map((s) => `${ts(s.bar)}@${s.price},${s.kind}${s.confirmed === false ? ',未确认' : ''}`).join('|');
  const done = (d.segs || []).filter((s) => !s.live);   // 线段中枢的 host（跟 layers.js doneSegs 同一条）
  return [on('pen') ? part(d.pens) : '', on('seg') ? part(d.segs) : '',
          on('pc') ? boxes(d.centers, d.pens || [], on('up')) : '',
          on('sc') ? boxes(d.seg_centers, done, on('up')) : '',
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

// 成交量（卡 card-68704ee6-a5a）：一根一根照着 bars[].v 画，**没有 v 就不画那一根**。
// ★ 绝不拿 0 顶上去 —— 画一根 0 高的柱子等于说「这一根的成交量是 0」，那是句假话。
//   （仓里那份冻结样本就是这种：zec_1h.json 5040 根一根 v 都没有，而后台那份有。所以这颗开关
//    在没有 v 的样本页上是**按灰**的，见 applyToggles —— 跟「买卖点关着时那六个 chip」同一个写法。）
// 颜色：K 线那一对涨跌色（收 ≥ 开 为阳）—— 跟 K 线读起来是同一件事，而且色仍只有 theme.js 一个出处。
function paintVol(d) {
  const pts = [];
  for (const b of d.bars || []) {
    if (typeof b.v !== 'number' || !isFinite(b.v)) continue;
    pts.push({ time: b.t / 1000, value: b.v, color: hexA(b.c >= b.o ? SUB.up : SUB.dn, VOL_ALPHA) });
  }
  sub.hasVol = pts.length > 0;       // 有成交量的那份数据才让这颗开关能点（applyToggles 读它）
  volSeries.setData(pts);
}

// ---------------------------------------------------------------- 画一张
// ★ 画（paint）和**摆视口**（draw 里那一段）分开了：往左补数据之后重画，**不能**再走「摆视口」
//   那一段（它要么 fitContent 缩成一团、要么按 ?last/?at 跳走）—— 补数据时视口由 place() 按**时间**放回原位。
function paint(d) {
  state.data = d;
  // 手上换了**另一份**数据（换档/换品种/换看法）⇒ 读数收起：十字线没动，但它底下那一根已经不是
  // 刚才那一根了，留着就是一行**过期的数**（光标一动它自己会回来）。手机上抬着手看的时候尤其要收。
  // ★★ 2026-10-04 实测（tools/web_readout_swap_probe.js）：**光这一句在这个位置量不出来** ——
  //   LWC 在 setData 之后会自己重发一次十字线，读数当场就用**新那份**重读了（换完之后原样／摘掉这句
  //   逐条读数一模一样）。真正盖住「换的那一刻」的是 go() 里那一句：数据还在飞的整段时间里，
  //   屏幕上还是旧图、读数写的却是上一份的数 —— 那一段就在这里之前，这一句够不到。
  //   留着是给**不走 go()** 的那些入口当保险（往前补数据 / 以后新加的换法）。
  hideRead();
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
  paintVol(d);
  syncSub();                 // 副图跟着主图一起换（同一份 K 线、同一个档位）；关着就一个请求都不发
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
    // 补数据这一趟带着**当前**的看法（换品种/换档时看法不该自己变回默认）
    const d = await load(symbol, tf, span, paging.measure);
    if (id !== paging.reqId) return;             // 等数据这段时间里换了品种/周期 ⇒ 这一份丢掉，别画上去
    // ★ 锚点要在**动数据之前**抓（setData 一换，视口的下标含义就变了），但要是**数据到手的这一刻**抓，
    //   不是发请求的那一刻：这一趟可能要等一两秒，用户在这期间还会接着往左拖 —— 拿发请求时的位置去「放回原位」，
    //   就是把他刚拖出来的画面**弹回去**（工装里量到过：拖到一半来的数据，画面被拽回 200px）。
    //   此刻 state.data 还是旧那份，bar 的时间戳还是旧的下标，抓锚点正合适。
    const range0 = chart.timeScale().getVisibleLogicalRange();
    const anchor = anchorOf(own.bars, range0);
    // ★ 基准要在**动数据之前**取：换完之后再取就没得比了（比的就是换前换后）。
    const win = windowOf(own.bars, range0);
    // ★ 判据只比**用户当前打开的那几层**，开关照 layers.js 实际画图用的那份（shownOf）取；
    //   前后两次用**同一个** sh：要是两次之间开关自己变了，那跟换档没关系，别算进去。
    const sh = shownOf(state.opts);
    const keyBefore = win && structKey(own, win.t0, win.t1, sh);
    Object.assign(paging, adopt(paging, d, own.bars.length));   // 回显说了算（钳档 / earliest / 有没有多出来）
    setUrl();
    draw(d, anchor);
    // 同一段时间、换完之后再取一次：不一样 ⇒ 用户正看着的那一屏被重算了 ⇒ 说一句，3 秒自己收
    if (win && structKey(d, win.t0, win.t1, sh) !== keyBefore) showNotice();
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

// ---------------------------------------------------------------- 光标读数（card-4cdf628c-c84）
// 「十字线停在哪一根，就把那一根摊开」：时刻 ＋ 开/高/低/收 ＋ 涨跌幅（对前一根的收）。
// ★ 这里一个新算法都不许有，三件事各有**一处**出处：
//   ① 数据：OHLC 取 `param.seriesData` —— 那是这一根**画在图上的**那份（刻度念的也是它）；
//      前收取 `state.data.bars`（喂给图的是**同一个数组**），按**时间**找回下标（timeIndex）。
//   ② 精度：`fmtPrice(v, tick)` —— 跟页头「最新 …」同一个函数、同一个 tick；价格轴的刻度走
//      `priceFormat(tick)`，precision ＝ `decimals(tick)`，跟这两个是同一个数。
//   ③ 时刻：`timeLabel` —— 跟时间轴上的刻度同一个函数（见 createChart 那几行）。
// ★ 触摸**不另写一套**：lightweight-charts 5.2.1 自己接长按（2026-10-04 实测：按住 ~500ms
//   出十字线，之后横向拖是**读数在走、视口不动**，抬手十字线不消失 ⇒ 抬着手也读得到）。
//   鼠标和手指走的是**同一条回调**，不留两份会各自漂的行为。
// ★ 「不挡图、不吃拖拽」写在 CSS（pointer-events:none），但量它的**真身**是工装里那两格：
//   「读数块正中心的 elementFromPoint 是画布」＋「从读数块上按下往左拖，视口照样动」。
//   只读 computedStyle 是替身 —— `.more` 那次就是位置对、字对、`visibility` 也对，整块被画布盖住。
const PCT_DASH = '—';            // 没有前一根（最左边那根）＝ 不编一个数给它，写「不知道」
let readShown = false;
// ★★ 2026-10-04（Nova 定的口径，卡 card-4cdf628c-c84）：**换品种/周期这一段（新的一份还在飞）里，读数整个压住**。
//   不只是「换的那一刻收一下」—— 那段时间页头已经写着新品种了，屏上还是旧图，**光标一动**读数就自己亮回来，
//   亮的是**上一份**的量级。实测（`tools/web_readout_swap_probe.js` 的 D 段，真后台，那一趟扣 2.5s）：
//     ZEC→BTC 换到一半，指针往旁边扫一下 ⇒ 块里亮着 `1,655.24 2026-09-27 12:00 UTC`（ZEC 那份的价），
//     页头写着 BTCUSDT；副图那三格同理（印着 DIF -11.69，而 BTC 那份是 -121.11）。
//   ⇒ 所以要压的是**整段**，不是那一刻：`showRead()` 在这一段里谁来叫都不亮、`refreshSubVals()` 印「—」，
//     放开的那一刻是**新数据画上去**（或这一趟完了）—— 放开之后光标一动／LWC 重发十字线，读数照旧回来。
//   谁在压：只有 `go()`（换品种、换周期、首屏）。**不**压「往左补数据」和「换看法」：那两条换的不是品种，
//     屏上那份的刻度没作废（换看法后台契约里 K 线逐字节不变），压住只会让读数白闪两下。
let dataStale = false;

function readAt(param) {
  const s = param.seriesData && param.seriesData.get(candle);
  if (param.time == null || !s) return null;
  const bars = (state.data && state.data.bars) || [];
  const i = timeIndex(bars, param.time * 1000);        // ★ 按时间找（换档是往数组头上插，下标会错位）
  const prev = i != null && i > 0 ? bars[i - 1] : null;
  return { t: param.time, o: s.open, h: s.high, l: s.low, c: s.close,
           tick: state.data.meta && state.data.meta.tick,
           pct: prev && prev.c ? (s.close - prev.c) / prev.c * 100 : null };
}
// 涨跌幅那一格：符号 ＋ 两位小数。★ `-0.00%` 不许出现（-0.001 会印成它）—— 那是句假话：
// 四舍五入到 0 就直接写 `0.00%`，而且**药丸的颜色跟着印出来的字走**（不是跟着没印出来的小数走）。
function pctText(p) {
  if (p == null || !Number.isFinite(p)) return PCT_DASH;
  const r = Math.round(p * 100) / 100;
  return (r > 0 ? '+' : r < 0 ? '-' : '') + Math.abs(r).toFixed(2) + '%';
}
function showRead(b) {
  // ★ 屏上那份 K 线已经不是页头写着的那一份了（新的一份还在飞）⇒ 光标动到哪儿都不亮（见 dataStale 那段）。
  //   放在这儿而不是那个回调里：**亮读数只有这一个口**，以后谁加了一条叫它的路，也自动归这条口径管。
  if (dataStale) return;
  const dir = Math.sign(Math.round(b.pct == null ? 0 : b.pct * 100));   // 印出来的那个数的方向
  const pct = el('ro-pct');
  el('ro-time').textContent = timeLabel(b.t);
  el('ro-open').textContent = fmtPrice(b.o, b.tick);
  el('ro-high').textContent = fmtPrice(b.h, b.tick);
  el('ro-low').textContent = fmtPrice(b.l, b.tick);
  el('ro-close').textContent = fmtPrice(b.c, b.tick);
  pct.textContent = pctText(b.pct);
  // 实底 ＋ 黑字，跟图上价签**同一种写法**（不新发明一种"标色"）；涨跌色只有 theme.js 一个出处。
  pct.style.background = dir > 0 ? CANDLE.up : dir < 0 ? CANDLE.dn : 'transparent';
  pct.style.color = dir === 0 ? PAGE.mu : CHART.tag_ink;
  el('readout').classList.add('on');
  readShown = true;
}
function hideRead() {
  if (!readShown) return;
  readShown = false;
  el('readout').classList.remove('on');
}
chart.subscribeCrosshairMove((param) => {
  // 指针离开图 / 十字线收起来时，LWC 给的是 time == null —— 那就是「读不到了」，读数跟着收。
  const b = param && param.time != null ? readAt(param) : null;
  if (b) showRead(b); else hideRead();
  // 副图那一格跟主图**共用同一条十字线**，所以**不另订阅一次**：就在这条回调里记下"停在哪一根"。
  // （同一个时刻的数据本来就一起到：2026-10-04 实测，指针停在哪一格，param.seriesData 里都带着
  //   同一时刻**所有窗格**的系列 —— 这是这个库自带的行为，不是我们拼的。）
  setSubHover(param && param.time != null ? param.time : null);
});

// ---------------------------------------------------------------- 副图：MACD（卡 card-68704ee6-a5a）
// 后端那一半（`/api/macd`，卡 card-ed2bbcf6-ffd）已经在 main 上，Nova 外测过。前端在这一块里只做三件事：
//   ① 要数 —— **懒取**：开关关着一个请求都不发；换品种/周期/档位就跟着主图一起换（同一份 K 线、同一个 span）
//   ② 画 —— 主图**下面单独一个窗格**（lightweight-charts 5.2.1 的 pane），高度按 stretchFactor 分，主图拿大头
//   ③ 念 —— 窗格那一格的头（#subhead）：口径照响应念，悬停时跟上那一根的三个数
// ★★ 前端**一步算术都不做**：柱子就是响应里的 hist，标题里的口径就是响应里的 hist_def。
//   前端自己再减一遍 DIF−DEA 的话，后台哪天换了柱子的定义，屏幕跟引擎就分家了 ——
//   而且**没有一处会红**（后端那一轮被 Atlas 逮到的正是这个形状：hist 在两个地方各减了一遍）。
//   工装里那一格就是拿这个当判据：假后台故意回一份 hist ≠ dif−dea 的（乘 2），画出来必须还是它。
const MACD_DEC = 2;                 // 副图价格轴的精度。★ 轴和读数**必须同一个数**（跟主图 tick 是同一条账）
const MACD_MIN = Number((10 ** -MACD_DEC).toFixed(MACD_DEC));   // 0.01：价轴的最小步进，由精度推出来，别另写一个
const HIST_DEF = { 'dif-dea': 'DIF−DEA' };   // 认得的柱子定义翻成人话；认不得的**原样印**（不吞，跟看法那张表同一条）
const SUB_H = { desk: 3, mob: 4 };  // 主图 : 副图 的高度比。手机给主图留得更多（4:1 ⇒ 主图拿八成）
let subHover = null;                // 光标停在哪一根（**秒**，跟 param.time 同一个单位）；null ＝ 光标不在图上
const sub = { series: null, data: null, at: null, slot: null, err: '', reqId: 0, hasVol: false };

// 那一格的头：**口径照响应念**（params ／ hist_def），前端不写死「12,26,9」也不写死「DIF−DEA」。
// 写死了，后台哪天改了参数或改了柱子的定义，屏幕上还写着老话，而且没有一处会红 —— 跟图脚那一格同一条账。
function subTitle(m) {
  const p = Array.isArray(m.params) && m.params.length ? `(${m.params.join(',')})` : '';
  const d = typeof m.hist_def === 'string' && m.hist_def ? HIST_DEF[m.hist_def] || m.hist_def : '';
  return `MACD${p}${d ? ` 柱=${d}` : ''}`;
}
// 头里的三格：光标那一根（光标不在图上 ⇒ 拿**最后一根**，跟读数块的收放同一条）。
// ★ 对不上的那一格写「—」**不写 0**：0 是个数，"这一根没有副图的数"是另一回事。
const subBox = el('subhead');
const subDom = subBox ? (() => {
  const title = document.createElement('span');
  title.className = 't';
  const cells = ['DIF', 'DEA', '柱'].map((k) => {
    const cell = document.createElement('span');
    cell.className = 'cell';
    const i = document.createElement('i'); i.textContent = k;
    const b = document.createElement('b'); b.textContent = '—';
    cell.append(i, ' ', b); subBox.append(cell);
    return b;
  });
  subBox.prepend(title);            // 口径在最前，三个数跟在后面
  return { title, cells };
})() : null;

function refreshSubVals() {
  if (!subDom) return;
  // ★ 同一个病、同一段时间：页头已经写着新品种，这三格却念着**上一份**的量级（实测见 dataStale 那段）。
  //   ⇒ 跟读数块一起压住，印「—」（这一格本来就有的写法：对不上就不印数，见上面那句「— 不写 0」）。
  //   ★ 标题不跟着改：它念的是**口径**（params / hist_def），不是这一根的数 —— 屏上那张副图也还是旧那份，
  //     标题跟它一起留着是对的（这一格写「MACD 取数…」是 sub.data 没到手时的写法，不是这一段的）。
  if (dataStale) { subDom.cells.forEach((b) => { b.textContent = '—'; }); return; }
  const m = sub.data;
  const bars = (state.data && state.data.bars) || [];
  const t = subHover != null ? subHover * 1000 : (bars.length ? bars.at(-1).t : null);
  const j = m && sub.at && t != null ? sub.at.get(t) : null;
  const f = (v) => (typeof v === 'number' && isFinite(v) ? v.toFixed(MACD_DEC) : '—');
  const vals = j == null ? ['—', '—', '—'] : [f(m.dif[j]), f(m.dea[j]), f(m.hist[j])];
  subDom.cells.forEach((b, i) => { b.textContent = vals[i]; });
}
function renderSubHead() {
  if (!subDom) return;
  subDom.title.textContent = sub.err ? `MACD 取不到：${sub.err}` : sub.data ? subTitle(sub.data) : 'MACD 取数…';
  subDom.title.classList.toggle('err', !!sub.err);
  refreshSubVals();
}
function setSubHover(t) {
  if (t === subHover) return;
  subHover = t;
  if (opts.macd) refreshSubVals();     // 关着的时候一个字都不用改
}

// 建／拆窗格。**幂等**：在不在以 `sub.series` 为准，不另记一个布尔（两个状态迟早对不上）。
// ★ 5.2.1 实测（2026-10-04，`_scratch/sub_probe*.js`）：把某个窗格的系列全 removeSeries 掉，那个窗格
//   **自己收回去**（窗格数回到 1）⇒ 关副图不会在下面留一条空白带；而 addSeries(…, 1) 会自动把窗格建出来。
function buildSub() {
  if (sub.series) return;
  const fmt = { type: 'price', precision: MACD_DEC, minMove: MACD_MIN };
  // 三条都用**自己那一格的 'right' 轴**（pane 1 的右轴）：一格一根刻度，跟主图那根互不干涉，
  // ★ 而且刻度**看得见** —— 用别的名字（overlay 轴）就没刻度：副图那一格会空着右半边，
  //   读者只能从头上那三个数猜量级（刻度是"一眼看出波动多大"的那把尺）。
  //   代价是要盯住一件事：两格的作图区宽度必须还是同一个（见工装里"十字线在两格里同一个 x"那一格）。
  sub.series = {
    hist: chart.addSeries(LWC.HistogramSeries, { priceFormat: fmt, base: 0,
                                                 lastValueVisible: false, priceLineVisible: false }, 1),
    // ★ 线宽要**写出来**：不写就是这个库的缺省 3（跟主图那几条比粗一倍，而且两条一样粗——
    //   "黄白线"就只剩下一坨黄盖住白）。1 跟笔同宽：它们是同一种东西（一条细线），不是线段那一档。
    dif: line({ color: SUB.dif, lineWidth: 1, priceFormat: fmt }, 1),
    dea: line({ color: SUB.dea, lineWidth: 1, priceFormat: fmt }, 1),
  };
  const ps = chart.panes();
  if (ps.length > 1) { ps[0].setStretchFactor(NARROW() ? SUB_H.mob : SUB_H.desk); ps[1].setStretchFactor(1); }
  // ★ 副图那一格的右轴必须**掰回线性**。建图时那句 `rightPriceScale: { mode: Logarithmic }` 铺的是**每一格**的
  //   right 轴（5.2.1 实测：`panes[0].priceScale('right')` 与 `panes[1].priceScale('right')` 是两根不同对象，
  //   但 `mode` 都是 1＝对数）。主图那根对数轴是**故意的**（对齐 chart_full_smooth.py 的 Y=log）；
  //   可 MACD 的值跨 0、还有负数，对数轴对这些点没有意义 —— 量过：0→1000 走 67px、1000→2000 只走 3px，
  //   轴上的刻度就成了 0.00 / -20000.00 这种跟数据无关的数，柱子也按错的比例尺画（Nova 外测那两张截图）。
  //   这一格的量法是线性：`Normal` 之后轴自己按**可见窗口**收，±3586 罩住 dif 的 -2497～3477（工装 web_macd_axis.js）。
  ps[1].priceScale('right').applyOptions({ mode: LWC.PriceScaleMode.Normal });
  subTopMargin = null;        // ★ 新窗格是新的一根比例尺：把「记着的留白」抹掉，不然 reserveSubhead 会以为已经让过了
  // 窗格一分，主图那一栏的高度就变了 ⇒ 图例/读数/页脚都不用动，但那一格的头要重新贴一次（见 placeSubhead）
}
function teardownSub() {
  if (!sub.series) return;
  for (const s of Object.values(sub.series)) chart.removeSeries(s);   // 摘干净 ⇒ 窗格自己收回去
  sub.series = null;
  subHover = null;
  subTopMargin = null;        // 窗格没了，记的留白也作废（跟 buildSub 那头一对）
}
// 副图的点**按时间取**，不按下标：换档是往数组头上插 K 线，同一个下标当场就指向另一根
// （跟 anchorOf / timeIndex 是同一条账）。主图有哪几根，副图就画哪几根；响应里没有这一根 ⇒ **那根不画**。
// 绝不拿邻点凑一个数出来 —— 凑出来的那根长得跟真的一模一样，谁也看不出来。
// ★ 两边的 t 都是**毫秒**：/api/macd 的 t[] 就是这份 K 线的 t（server.py 里取的同一个数组）。
function subPoints(bars, col, pick) {
  const out = [];
  for (const b of bars) {
    const j = sub.at.get(b.t);
    const v = j == null ? null : col[j];
    if (typeof v === 'number' && isFinite(v)) out.push(pick(v, b.t / 1000));
  }
  return out;
}
// 把手上这一份灌上去（没数就空着）＋ 摆头。**幂等**，谁都可以随时叫一次。
function paintSubData() {
  if (!opts.macd || !sub.series) return;
  const bars = (state.data && state.data.bars) || [];
  const m = sub.data && sub.at ? sub.data : null;
  const sign = (v) => (v >= 0 ? SUB.up : SUB.dn);     // 柱子用 K 线那一对涨跌色（theme.js 的 SUB）
  sub.series.hist.setData(m ? subPoints(bars, m.hist, (v, t) => ({ time: t, value: v, color: sign(v) })) : []);
  sub.series.dif.setData(m ? subPoints(bars, m.dif, (v, t) => ({ time: t, value: v })) : []);
  sub.series.dea.setData(m ? subPoints(bars, m.dea, (v, t) => ({ time: t, value: v })) : []);
  renderSubHead();
  placeSubhead();
}
// 那一格的头**贴着副图窗格的上沿**：位置不是 CSS 摆的 —— 窗格高是 LWC 按 stretchFactor 排出来的，
// CSS 算不出那个数（算得出来也会在换档、展开开关、转屏时过期）。所以每次布局变都重算一次。
const SUBHEAD_TOP = 4;      // 页头离窗格上沿的那个偏移（placeSubhead 与 reserveSubhead 用的是同一个数）
const SUBHEAD_GAP = 4;      // 页头下沿再留一点气口：柱尖贴在它下沿上看着还是「顶着」
function placeSubhead() {
  if (!subBox) return;
  const on = !!opts.macd && !!sub.series;
  subBox.classList.toggle('on', on);
  if (!on) return;
  reserveSubhead();                              // 先给页头让出那一条（比例尺变了不影响下面那行 top 的计算）
  const pane = chart.panes()[1];
  const chartBox = el('chart').getBoundingClientRect();
  const tsH = chart.timeScale().height();          // 时间轴是**共用**的一条，压在整栏的最下面
  // top 是**相对 .overlays 那个盒子**算的（它就是 subBox 的定位祖先，自己离图顶有 10px，见 style.css）——
  // 那个 10px 不在这里再抄一遍：从**两个盒子的实测距离**里减掉（CSS 改了这里也跟着对）。
  const offset = subBox.parentElement.getBoundingClientRect().top - chartBox.top;
  const top = chartBox.height - tsH - (pane ? pane.getHeight() : 0) + SUBHEAD_TOP - offset;
  subBox.style.top = Math.max(0, Math.round(top)) + 'px';
}
// 页头那块浮层**压在副图上沿**而不是排在它上面 —— 它盖住的那一条里不许有数据。
// 量过（2026-10-04，真后台 8796，ZECUSDT 15m，可见窗口收到 120 根）：那一格的比例尺上下各留 8%
// ⇒ 窗格里最极端的那个点正好画在 y=13.4（168px 的 8%），而页头的下沿在 y=26 ⇒ **最高那根柱子的
// 柱尖上面 12.6px 是画了、被它画掉的**（把页头 display:none 再拍一张，柱尖就露出来了）。挑窗有讲究：
// 副图那格的轴是 hist/dif/dea **一起**撑的，多数窗口里 DIF 比柱子大、柱子够不到顶（首屏就是这样，
// 所以一直没人看见）；要 max|hist| ≥ max(|dif|,|dea|) 的那种窗口（柱子自己撑轴）才咬得着。
// 修法：把那一格的右轴**上边留白按页头实测的高度让出来** —— 数据一个像素都不进那条带子。
// 页头的高度是**量出来的**（手机上这句会换行，两行就更高），所以跟 placeSubhead 一起每次布局重算；
// 值没变就别再 applyOptions（那会重画一整格）。★ 建／拆窗格时要把记的值抹掉（见 buildSub/teardownSub）：
// 新窗格的比例尺是新的，记着旧值就会「只有第一次生效」。
let subTopMargin = null;
function reserveSubhead() {
  const pane = chart.panes()[1];
  if (!pane || !subBox) return;
  const h = pane.getHeight();
  if (!h) return;
  const need = SUBHEAD_TOP + subBox.offsetHeight + SUBHEAD_GAP;   // 页头在窗格顶占掉的那一条（px）
  const top = Math.min(0.4, need / h);                            // 兜个上限：窗户太小也不许把数据挤没
  if (subTopMargin != null && Math.abs(subTopMargin - top) < 1e-4) return;
  subTopMargin = top;
  // bottom 跟着 LWC 的缺省（0.08）写出来：只改 top 的话另一头也跟着漂，那就不是「让出页头」了
  pane.priceScale('right').applyOptions({ scaleMargins: { top, bottom: 0.08 } });
}
if (subBox && 'ResizeObserver' in window) new ResizeObserver(() => placeSubhead()).observe(el('chart'));

async function loadSub(symbol, tf, span) {
  const r = await fetch(`/api/macd?${new URLSearchParams({ symbol, tf, span: String(span) })}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return await r.json();
}
// 把副图**对上现在这一格**（品种|周期|档位）。三件事按这个次序：
//   ① 手上这份先画上（换档途中不留上一格的数：宁可空一格，也不给一份对不上主图的旧数）
//   ② 这一格没处理过才发请求（`sub.slot` 就是"处理过"那一个记号：成功、失败、在飞，都算处理过 ——
//      失败不重敲，等换格自然重来，跟 paging 的失败退避同一条账）
//   ③ 到手的数按时间对齐再画（见 subPoints）
function syncSub() {
  if (!opts.macd) {                                 // ★ 关着不付：窗格拆干净、一个请求都不发（卡面点名的验收之一）
    teardownSub();
    if (subBox) subBox.classList.remove('on');
    return;
  }
  buildSub();                                       // 窗格在这儿建（幂等）—— 首屏第一趟 paint 就走到这里
  paintSubData();
  if (!state.data) return;
  const symbol = el('symbol').value, tf = el('tf').value;
  const want = `${symbol}|${tf}|${paging.span}`;
  if (sub.slot === want) return;
  sub.slot = want;
  sub.data = null; sub.at = null; sub.err = '';
  paintSubData();
  const id = ++sub.reqId;                           // 换格 ⇒ 在飞的那一份作废（跟 paging.reqId 同一个写法）
  loadSub(symbol, tf, paging.span).then((m) => {
    if (id !== sub.reqId || !opts.macd) return;
    sub.data = m;
    sub.at = new Map((m.t || []).map((t, j) => [t, j]));
    paintSubData();
  }).catch((e) => {
    if (id !== sub.reqId || !opts.macd) return;
    sub.err = String((e && e.message) || e);        // 取不到就说取不到（那一格的头里写着），不静默画一条空窗格
    paintSubData();
  });
}
// 开关动过之后走这一条：建/拆窗格、该取的取 —— 都是 syncSub 自己的事（它认得 `opts.macd`），
// 这里只多补一件：地址栏跟着改（图层那几颗不进地址栏，这两颗进）。
function syncSubView() { syncSub(); setUrl(); }

// ---------------------------------------------------------------- 开关
function applyToggles() {
  penSolid.applyOptions({ visible: opts.pen });
  penDash.applyOptions({ visible: opts.pen });
  segSolid.applyOptions({ visible: opts.seg });
  segDash.applyOptions({ visible: opts.seg });
  // 成交量：开关说着开、数据里也确实有 v —— 两条都成立才画（样本没有 v ⇒ 开着也画不出来，
  // 那就把开关按灰并说出来，别让用户点了没反应还不知道为什么）。
  volSeries.applyOptions({ visible: !!opts.vol && sub.hasVol });
  repaint();
  renderLegend();
  // ★ 只扫**图层那排**（带 data-key 的）。底下「背驰看法」那一组也长着 .chip 的皮（同一个药丸尺寸），
  //   但它是**单选**（aria-checked，归 renderMeasures 管），没有 data-key ——
  //   扫进来就会对着 undefined 取 .startsWith，整张图连带图脚一起炸（2026-10-04 真撞过）。
  for (const b of document.querySelectorAll('.chip[data-key]')) {
    const k = b.dataset.key;
    const on = k === 'sigPend' ? opts.sigPend : k.startsWith('sig:') ? opts.sigKinds[k.slice(4)] : opts[k];
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    const sigChip = k.startsWith('sig:') || k === 'sigPend';
    // 成交量那颗在**没有 v 的数据上**按灰（仓里的样本就是）：能点却画不出东西的开关是骗人的。
    b.disabled = sigChip ? !opts.sig : k === 'vol' ? !sub.hasVol : false;
  }
  // 「关着的层不许有能点的开关」这条账，看法那组也算：买卖点一关，它就得跟着灰（或反过来亮回来）。
  renderMeasures();
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
      // 副图那两颗关掉再打开 ⇒ **重新要一份**：关着的那段时间数据可能已经旧了/后台换过了。
      // （不这样，`sub.slot` 还是老值 ⇒ syncSub 认为"这一格处理过了"，窗格会空着不取数。）
      if (key === 'macd' && opts.macd) { sub.slot = null; sub.err = ''; }
      applyToggles();
      if (key === 'vol' || key === 'macd') syncSubView();
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
  // 副图那两颗（卡 card-68704ee6-a5a）**排在最末尾**：上面那几颗管的是「主图上画什么」，
  // 这两颗管的是**另外两格**（主图下沿那条成交量、下面那一格 MACD）—— 中间隔着一个"买卖点"组，
  // 正好把"叠层"和"另起一格"分开，眼睛一扫就知道它们不是一类。
  // 点取 theme.js 的 SUB：成交量用 K 线那一对涨跌色（取阳色），MACD 取黄白线里的黄（原文的叫法）。
  add('成交量', 'vol', CANDLE.up);
  add('MACD', 'macd', SUB.dea);
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

// ---------------------------------------------------------------- 手机上：图例/数据/约定 收起（卡 card-b9792318-91d）
// 默认**收起**（小栋 2026-10-04 05:00Z 定 ②B：手机上让图占满）。收的是「学一次（图例）／读一次（约定）／
// 诊断（元信息）」这三块 —— 图层那一排（天天要点）**不动**，账写在 style.css 窄屏那一档里。
// ★ 开关不自己藏一个布尔：`aria-expanded` 就是那个状态，收起/展开两句话由它推出来，
//   点一下只走 setFold 一条路（各自记一个的话，迟早在某处对不上，屏幕上就会出现"箭头说收起、其实没收起"）。
// ★ 桌面这一颗在 CSS 里就是 display:none（桌面放得下，图占 84%）：这里照挂类，桌面那两条规则不认它。
function setFold(open) {
  document.body.classList.toggle('m-fold', !open);
  el('fold').setAttribute('aria-expanded', String(open));
  el('fold-tx').textContent = open ? '收起' : '图例 · 数据 · 约定';
  reserveFold();
}
// 图层条右端给开关留的那一格有多宽：**量开关自己**，写进 CSS 变量（style.css 的 `.panel` padding-right）。
// 不在那里抄一个数：抄的数跟开关的字对不上，条子滑到头就会有一两颗 chip **停在开关底下** —— 看得见、点不到。
// 开关的字会变（「图例 · 数据 · 约定」／「收起」），所以每次改完口都重量；换窗口宽也可能换字号，resize 也重量。
function reserveFold() {
  const b = el('fold');
  if (b) cssVar('--fold-w', `${Math.ceil(b.getBoundingClientRect().width) + 8}px`);
}
el('fold').addEventListener('click', () => setFold(document.body.classList.contains('m-fold')));
addEventListener('resize', reserveFold);
setFold(false);

// ---------------------------------------------------------------- 背驰看法那一组（卡 card-84091d2d-c97）
// 放在图层那一排**前面**：它决定的是「买卖点按哪种力度比较算出来」（算什么），比「画哪几层」还靠上一步。
// ★ 样式上跟图层开关**刻意分开**：图层是一排可多选的开关（`aria-pressed`，虚边），这一组是**单选**
//   （`role=radio` / `aria-checked`，选中的那颗实心）—— 眼睛一扫就知道这两排不是一回事。
// ★ 能切哪几种**以 /api/meta 的 measures 为准**（同上：名单不许写死在前端）。名单没到 ⇒ 这一组不画。
//
// ★★ measures 这个字段**两种形状都吃**（card-6381042d-03f）：
//    ① **契约**（后端 `agent/bram/meta-measure-orig` = 787c923）：`measures` 还是字符串数组，
//       「是不是原文」另挂一张 `measure_orig = {看法: 布尔}`；
//    ② **往后挪一步的容错**：哪天有人把 `measures` 改成 `[{id, orig}, …]`，这里也照吃。
//    为什么要留这半步：只认一种形状的话，后台先换、浏览器还缓存着旧 app.js（或反过来），过滤完是
//    **空数组** ⇒ `list.length < 2` 直接 return ⇒ 整组「背驰看法」**从页面上消失**，而且**一声不响**
//    （没报错、没空格子，就是没了）。那是最坏的失败方式 —— Bram 选①也是这个理由。
//    ⇒ 名单照收；`orig` 读得到就读，**读不到就一个标都不挂**（不知道的事不编，跟图脚同一条规矩）。
function readMeasures(m) {
  const raw = Array.isArray(m && m.measures) ? m.measures : [];
  const side = (m && typeof m.measure_orig === 'object' && m.measure_orig) || null;
  const list = [], orig = {};
  for (const it of raw) {
    const id = typeof it === 'string' ? it : (it && typeof it.id === 'string' ? it.id : '');
    if (!id) continue;
    list.push(id);
    if (side && typeof side[id] === 'boolean') orig[id] = side[id];   // ①：旁边那张表
    else if (it && typeof it.orig === 'boolean') orig[id] = it.orig;  // ②：项自己带着
  }
  return { list, orig };
}

async function loadMeasures() {
  try {
    const r = await fetch('/api/meta');
    if (!r.ok) return;
    const m = await r.json();
    const { list, orig } = readMeasures(m);
    if (list.length < 2) return;         // 只有一种看法＝没什么可切的；不画一个只有一个选项的开关
    measures.list = list;
    measures.orig = orig;
    // 地址栏点名的那个后台认不认：名单外的一律退回缺省（缺省不在名单里才拿第一个）
    const want = new URLSearchParams(location.search).get('measure');
    if (want && !list.includes(want)) paging.measure = list.includes(DEFAULT_MEASURE) ? DEFAULT_MEASURE : list[0];
    buildMeasures();
  } catch (e) { /* 没后台（离线样本）或没这个接口：没有看法可切，页面上不多一个字 */ }
}

// 「非原文」那枚小标（card-6381042d-03f，小栋 2026-10-04 定 ①A：**留着，标明**）。
// 短的是芯片上那两个字，长的是悬停那句 —— 措辞**只写这一处**（跟 MEASURE_NAME 一个道理：屏幕上一份、
// title 里再抄一份，迟早一份改了另一份没改）。
// ★ 这里写死的只有**说明那句话**，不是**哪几种看法非原文** —— 后者一律听 /api/meta 的（见 readMeasures）。
//   「非原文」出现在页面上，就得答得出「那原文是什么」：答案是第 24 课只写柱子面积。
// ★ 措辞口径（Atlas 核的时候提的，别写回去）：**不许写「原文没提过斜率」** —— 「斜率」这两个字原文
//   真出现过两处（`L55:29` 讲通道、`L98:17` 讲类背驰时顺口带过），只是**都没把「价差 ÷ 根数」定成
//   一种比力度的量法**。所以「非原文」说的是**那个公式**，不是那两个字 —— 写错了就是拿一句可以
//   被两句原文当场打脸的话，去标一个本来站得住的结论。
const NON_ORIG_SHORT = '非原文';
const NON_ORIG_LONG = '非原文：第 24 课讲背驰的力度只写了「柱子面积」；价差 ÷ 根数这种比法原文没有，是本引擎自己加的';

function buildMeasures() {
  const box = el('panel');
  const g = document.createElement('div');
  g.className = 'mgroup'; g.id = 'mgroup';
  g.setAttribute('role', 'radiogroup'); g.setAttribute('aria-label', '背驰看法');
  const cap = document.createElement('span');
  cap.className = 'mcap'; cap.textContent = '背驰看法';
  g.appendChild(cap);
  for (const id of measures.list) {
    // 翻不出中文名的（后台加了第五种）⇒ 原样印代号，title 里说明白：**不吞**。
    const [short, long] = MEASURE_NAME[id] || [id, `${id}（后台新加的看法，前端还没有中文名）`];
    const b = document.createElement('button');
    b.className = 'chip mchip'; b.type = 'button'; b.dataset.measure = id;
    b.textContent = short; b.title = long;
    // ★ 后台说它**不是原文**（`orig:false`）⇒ 挂上那枚小标，并把那句说明接到 title 后面。
    //   判据是**后台那个布尔**，不是前端认死「斜率」两个字 —— 认死的话，后台哪天把某一条改成原文的、
    //   或者新加一种原文没有的，标记就跟事实脱钩了，而屏幕上没人看得出来。**读不到 orig 就不挂**。
    if (measures.orig[id] === false) {
      const mark = document.createElement('span');
      mark.className = 'nonorig'; mark.textContent = NON_ORIG_SHORT;
      b.appendChild(mark);
      b.title = `${long} ｜ ${NON_ORIG_LONG}`;
    }
    b.setAttribute('role', 'radio');
    b.onclick = () => setMeasure(id);
    g.appendChild(b);
  }
  box.prepend(g);
  watchOverflow(box);                  // 手机上多了一排，右边还有没有东西要重算一遍
  renderMeasures();
}

// 亮哪一颗**看回显**（paging.measure 是 adopt() 从响应里认来的），不看用户刚点的那一颗。
// ★ 买卖点那层关着 ⇒ 这一组**置灰不可点**：这四颗只换买卖点的画法，层关着的时候换看法，
//   屏幕上**什么都不会变** —— 点了没反应会被当成坏了（判据只有 opts.sig 一处，跟别的开关同一条账）。
//   ★ 手机上没有 hover，所以「为什么是灰的」不能只写在 title 里，标题那行也得说。
function renderMeasures() {
  const g = el('mgroup'); if (!g) return;
  const on = !!opts.sig;
  for (const b of g.querySelectorAll('.mchip')) {
    b.setAttribute('aria-checked', b.dataset.measure === paging.measure ? 'true' : 'false');
    b.disabled = !on;
  }
  const cap = g.querySelector('.mcap');
  if (cap) cap.textContent = on ? '背驰看法' : '背驰看法 · 买卖点那层关着';
  if (on) g.removeAttribute('title');
  else g.title = '买卖点那一层关着 —— 这四颗只换买卖点的画法，先把它打开';
}

async function setMeasure(id) {
  if (!measures.list.includes(id) || id === paging.measure || paging.loading) return;
  const own = state.data;
  const id0 = ++paging.reqId;          // 跟首屏／往左加载共用同一个号：谁后发谁算数，先到的那份丢掉
  paging.loading = true;
  el('state').textContent = '换看法…'; el('state').className = 'badge';
  try {
    // ★ 锚点在**动数据之前**按**时间**抓（anchorOf）。后台契约是「切看法只换 signals，K线/笔/段/中枢
    //   逐字节不变」⇒ 这个锚点原样指回同一根，视口一动不动。真变了也不跳：这一手本来就是按时间放回去的，
    //   所以这里**不押**在「一定不变」上。
    const anchor = own ? anchorOf(own.bars, chart.timeScale().getVisibleLogicalRange()) : null;
    const d = await load(el('symbol').value, el('tf').value, paging.span, id);
    if (id0 !== paging.reqId) return;
    // prevLen 传 undefined：换看法**不是补数据**，「要了却一根没多」这条判据在这儿不成立 ——
    // K 线根数本来就该一样，传了它，下一次往左拖就会被判成 nogain、印一句「取不到更早数据」的假话。
    Object.assign(paging, adopt(paging, d));
    setUrl();
    if (anchor) draw(d, anchor); else draw(d);
    renderMeasures();
    el('state').textContent = d.closed ? '已收盘' : '未收盘（最后一根还在走）';
    el('state').className = 'badge ' + (d.closed ? '' : 'live');
  } catch (e) {
    if (id0 !== paging.reqId) return;
    el('state').textContent = String(e.message || e); el('state').className = 'badge bad';
    renderMeasures();                  // 没换成 ⇒ 亮回原来那一颗
  } finally {
    if (id0 === paging.reqId) paging.loading = false;
  }
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

// 背驰看法：代号 → 人话。措辞照 core/signals.py 里 MEASURES 上面那一行（不自己另起名字）。
// ★ 这张表**同时给图脚和控件**用，放在这一块里：尺 ③ 把 renderMeta 抠出来单跑，只喂 `el` 和 `d`
//   —— 模板要是回头去读块外的符号（比如「后台给了哪几种」那份名单），当场 ReferenceError ⇒ 直接红。
//   **图脚本来也不该依赖那份名单**：它认的是**回显**（d.measure），跟 span / earliest 同一条规矩。
const MEASURE_NAME = {
  macd: ['面积', 'MACD 柱子的面积（默认）'],
  slope: ['斜率', '斜率'],
  lines: ['黄白线', '黄白线不创新高低'],
  peak: ['峰值', '柱子一波的峰值'],
  // 后台的第五种（`macd_or_lines`，spec 六.3，card-bead5f56-74b）：**名字要跟着后台加** —— 后台先上线、
  //   名字没跟上的那半天里，芯片上是一串英文代号：不报错、也不算坏，但没人认得出那是什么。
  //   依据是原文那句 `L27:42`「只要其中一个符合就可以是一个背驰的信号，两个都满足就更标准了」。
  //   名字写全「面积或黄白线」而不是缩成「或」：这是**选一种量法**的地方，含糊比宽几个像素贵。
  macd_or_lines: ['面积或黄白线', '面积或黄白线：两样里有一个符合就算背驰（第 27 课「只要其中一个符合就可以是一个背驰的信号」）'],
};
// 图脚那一格：**以回显为准** —— 用户点的那颗可能会失败（后台 400/503），屏幕上画的到底是哪种，
// 只有后台回的那份说了算。旧后台和离线样本没有这个字段 ⇒ 这一格**不出现**，不知道的事不编。
function measureText(d) {
  const m = d.measure;
  if (typeof m !== 'string' || !m) return '';
  return ` ｜ 背驰看法 ${(MEASURE_NAME[m] || [m])[0]}`;
}

function renderMeta(d) {
  const done = d.segs.filter((s) => !s.live).length;
  el('meta').textContent =
    `${d.name || d.symbol} · ${d.tf} ｜ ${d.nbars} 根 ｜ 笔 ${d.pens.length} ｜ 类中枢 ${d.centers.length}`
    + ` ｜ 完成线段 ${done}（+${d.segs.length - done} 未完成）｜ 线段中枢 ${d.seg_centers.length}`
    + ` ｜ 精度 ${d.meta?.tick} ｜ ${d.meta?.pen_rule === 'new' ? '新笔' : '老笔'}`
    + ` ｜ 买卖点 线段中枢层 ${sigTierText(d.signals?.seg || [])} · 类中枢层 ${sigTierText(d.signals?.pen || [])}`
    + measureText(d)
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
  // 看法同理：写着缺省（面积）是噪音，抹掉；只有真换了才写上去（可分享、可截图复现）。
  if (measures.list.length && paging.measure !== DEFAULT_MEASURE) q.set('measure', paging.measure);
  else q.delete('measure');
  // 副图那两颗同理：跟**这一屏的默认**（桌面开、手机关，见 SUB_DEF）不一样才写上去。
  // 这样地址栏永远只写"这一屏再从零打开会不一样的东西"—— 写着默认值是噪音，换屏时还得记得抹掉。
  for (const k of ['vol', 'macd']) {
    if (opts[k] === SUB_DEF) q.delete(k); else q.set(k, opts[k] ? '1' : '0');
  }
  history.replaceState(null, '', `?${q}`);            // 可分享、可截图复现
}

async function go(span = 1) {
  const symbol = el('symbol').value, tf = el('tf').value;
  resetPaging(span);
  setUrl();
  const id = paging.reqId;                            // 连点两次品种：先发的那份回来时已经不是它了，别画
  paging.loading = true;        // 这一份还在飞（换品种时旧图还挂在屏上）⇒ 别在这中间再插一个「更早」的请求
  // ★ 读数在**换的这一刻**就收，不等新数据回来。数据没到的这整段时间里屏上还是旧图，十字线也没动，
  //   但读数要是留着，写的就是**上一份数据的数**（屏上那份图跟它已经不是一回事了）。
  //   放这儿而不是 paint() 里：paint() 跑在新数据到了之后，**那一段它够不到**（实测见 paint() 那段注释）。
  //   收掉不会让它回不来：新数据画上之后 LWC 会重发一次十字线，读数自己就用新那份回来了（工装 ⑮⑯ 量着）。
  dataStale = true;      // ★ 而且**整段压住**，不只是这一下：这段时间里光标一动读数也不许亮回来（见 dataStale 那段）
  hideRead();
  el('state').textContent = '取数…'; el('state').className = 'badge';
  try {
    const d = await load(symbol, tf, paging.span, paging.measure);
    if (id !== paging.reqId) return;
    Object.assign(paging, adopt(paging, d));     // ★ 首屏也认回显：一开始就 earliest 的品种不该白发请求
    setUrl();                                    // 后台钳过档的话（15m 要 16 钳到 4），地址栏写**真**档位
    draw(d);
    renderMeasures();                            // 亮哪一颗看回显（名单是后到的，首屏画完得补一次）
    el('state').textContent = d.closed ? '已收盘' : '未收盘（最后一根还在走）';
    el('state').className = 'badge ' + (d.closed ? '' : 'live');
  } catch (e) {
    if (id !== paging.reqId) return;
    el('state').textContent = String(e.message || e);
    el('state').className = 'badge bad';
  } finally {
    // ★ 放开读数：新的画上去了就是这一趟的结尾。放在 `finally` 而不是 `draw()` 后面，是为了**失败那一趟
    //   也放开** —— 取数失败时新图没来、屏上那张老图没被换掉，老读数跟它还是同一份，压着不放才是一句谎
    //   （工装 ⑳ 量的就是这一条：不许把读数压死）。
    //   id 对不上就别碰：那是**更新的一趟**在管这个标志，它自己有始有终。
    if (id === paging.reqId) { paging.loading = false; dataStale = false; }
  }
}

buildPickers();
buildChips();
applyToggles();
// 看法那份名单跟首屏的图表请求**并行**发（不为一个小请求把首屏推后）。只有一个例外见下面：
const metaReady = loadMeasures();
(async () => {
  const q = new URLSearchParams(location.search);
  // ★ 地址栏**点名了**看法就得先等名单：名单外的名字发出去后台回 400，整张图会白挂在这一个词上
  //   （跟 `?load=` 超白名单会被钳是同一类账，只是那边前端能自己钳、这边得先问后台认哪几个）。
  //   没点名（绝大多数）⇒ 一个字都不等，立刻发第一趟；那一趟不带 measure，走后台自己的缺省。
  if (q.has('measure')) await metaReady;
  // ?load=N：直接打开某一档（可分享 / 可截图复现；N 不在白名单上就退回它下面的那一档）
  go(ladderSpan(q.get('load')));
})();

// 给验收工装一个**只读**入口：并排截图要把网页这一格切到跟 Python 出图同一段 K 线、同一价格带，
// 那就得问图自己「第 i 根在哪个 x、这个价在哪个 y」（timeToCoordinate / priceToCoordinate）。
// 不是功能开关，页面上没有任何东西读它；去掉它，验收那两张图就没法对齐。
window.__app = { chart, state, opts, paging, measures, sub };
