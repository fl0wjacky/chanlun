// chanlun.surfers.cc 前端 —— 接线：取数 → 建图 → 开关 → 角上的「最后更新时间」。
//
// 数据只认一个形状（`tools/make_web_fixture.py` 就是它的可执行定义，后台卡 card-29a45ab6-0ac 照着吐）：
//   {symbol, tf, name, updated, closed, bars[], pens[], segs[], centers[], seg_centers[], signals{seg,pen}, meta{tick,pen_rule}}
// 取不到后台就退回 `fixtures/`（离线也能看、也能截图对账）；两边都没有就老实说取不到，不画半张图。
import { CHART, PAGE, CANDLE, WIDTH, SUB, TREND } from './theme.js';
import { makeBoxPrimitive, makeAnnotPrimitive, makeTrendPrimitive, makeWolfPrimitive, shownOf, ghostHitAt,
         boundHitAt, pzHitAt, refTfName } from './layers.js';

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
// 角上署名那颗日期印的是**浏览器本地的今天**（`card-e7554dd2-44a`：这格答的是「今天几号」，
//   读的人是看图的人，跟页头「本根／数据」那两格同一类）。
// ★ 不写 `toISOString().slice(0, 10)` —— 那是 **UTC**：一个 UTC+8 的人晚上十点打开页面，
//   角上写的是"明天"。图上那些记号（时间轴刻度、光标读数）仍按 UTC，那是行情自己的坐标；
//   这一格不是坐标，是"今天"，两回事。
const localDate = (d = new Date()) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  + `-${String(d.getDate()).padStart(2, '0')}`;
cssVar('--am', CANDLE.open);                                  // 未收盘 / 旧数据：琥珀（style.py AM）
cssVar('--rd', CHART.sell);                                   // 出错：红（style.py CHART.sell）
cssVar('--am-line', mix(CANDLE.open, PAGE.bg, 0.26));         // 徽标边框＝同色压到 bg 上，不新造色
cssVar('--rd-line', mix(CHART.sell, PAGE.bg, 0.26));
cssVar('--panel-hi', mix(PAGE.tx, PAGE.panel, 0.05));         // 选中的 chip：panel 抬 5% 白
document.getElementById('today').textContent = localDate();   // 署名：冲浪者 · 日期（本地钟）

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
// 入门防守（T13，均线.md 六.7）：**默认关**（Nova 09:02 定）。关着就一个请求都不发（跟 MACD 那颗同一条账）。
// 地址栏 `?wolf=1` 开；`?wolftf=1h` 指名周期（不写 ＝ 跟着这张图的周期）。周期**由用户选**，原文没给默认。
opts.wolf = SUB_Q.get('wolf') === '1';
// 走势分段那一层（v3 §八，卡 card-c73ab37d-5a1）：**默认开**（Nova 2026-10-05 17:09Z 定）——
// 这一层就是小栋要看的那个东西，藏在 `?trend=1` 后面他打开页面根本看不见；开关留着，可以手动关掉。
// 所以地址栏这一头是**反着写**的：`?trend=0` 才关（可分享、可截图复现）。
// ★ 不进 DEFAULTS：那个对象记的是「TradingView 的默认值」那一组（卡面点名的），这一颗的理由跟它无关。
// ★ 它**只在 `cut=trend` 那份载荷上有东西可画**（`cut=extend` 那份连 `trend` 这个键都没有）——
//   所以那一档下这一颗按灰，理由写在标题里（跟「成交量」那颗在没有 v 的数据上按灰同一条账）。
opts.trend = SUB_Q.get('trend') !== '0';
// 框编号 A／B／C（v3 §八 6，卡 card-c6644f52-2fa）：**默认关**（小栋 10-05 12:3xZ 拍的；
// 这一条跟「走势分段」那颗反着来，理由也是反的：那层是小栋要看的东西、藏着等于没有；
// 编号是**加在它上面的一层细读**，默认糊在图上会把主图的字挤满）。地址栏 `?trendnum=1` 可以指名
// （可分享、可截图复现），一个字没有 ⇒ 关。
// ★ 字母挂哪一级**这一层不猜**：载荷的 `trend_reading` 说了算（A 挂合成出来的高一级中枢、
//   B 挂本级别）。⇒ D3 保持 A 还是换 P6，是**后台一个字段**的事，前端这一行一个字都不用改。
opts.trendNum = SUB_Q.get('trendnum') === '1';
// 级别对照那一层（卡 card-01961644-68f，接口规则 L-9）：**默认开** —— 它是"合成框跟**对照图**
// （后台 `ref_tf` 那一档）对不上"的那一句标，藏起来等于没做。跟「走势分段」同一条写法：地址栏 `?lv=0` 才关（可分享、可截图复现）。
// ★ 它画在**合成框**上（那层归「高一级」）⇒ `shownOf` 里跟 `up` 与过；「高一级」默认关着，所以
//   这一颗**默认开也画不出东西**，得先把「高一级」打开才有框可标。这不是 bug，是那一层的从属关系。
// ★★ 2026-10-06 19:2xZ（Nova 拍，card-6e338490-f11）：那个"从属"从前**只写在 `shownOf` 里**，
//   芯片那一头读的还是裸标志 ⇒ 首屏亮着一颗做不了事的芯片（`pressed=true` **且** `disabled=true`，
//   三种状态里只有它骗人）。现在按 **「lv 跟着 `up` 走」**：`opts.lv` 这个**意愿**留着
//   （所以「高一级」一开、对照自己就在，不用再点第二颗），但**亮不亮、画不画都只看 `shownOf(opts).lv`**
//   ⇒ 首屏两颗都关：芯片不亮、按灰。★ 地址栏 `?lv=1` 仍把意愿钉成开（首屏那颗照样不亮 ——
//   亮 ⟺ 画，钉的是意愿不是显示），`?lv=0` 钉成关。下游 `:2327` 那一头（默认开 ⇒ 关着才写）
//   跟着 `opts.lv`（意愿）走，不跟着显示走 —— 换屏时写不写地址栏不该随「高一级」的开合变。
opts.lv = SUB_Q.get('lv') !== '0';
// ★ `tf` / `span` 是「**此刻屏上这一份**是哪一档」，由 `noteView()`（在 `draw()` 里）每次摆图时记一笔。
//   级别对照那一层要用它：`levels` 是**另一次**请求的载荷，跟图表那份没有共同的身份字段，
//   只能靠"同一档"来判断那份还在不在讲这一张图（见 layers.js `lvAligned`）。
const state = { data: null, opts, candleSeries: null, levels: null, tf: '', span: null };
const primitives = [];
// 往左拖那套状态：span＝现在手上是第几档，spanMax＝后台给的封顶，earliest＝币安真没有了。
// viewSet＝**我们自己摆的那个视口**（用来认事件回声，见 setView）；reqId＝在飞的那一份的号（换品种就作废）。
const DEFAULT_MEASURE = 'macd';       // 后台的缺省也是它（core/signals.py 的 MEASURES）；地址栏里不写它
// 中枢切法（卡 card-e346ede6-996）：`cut=extend`＝原文那套（延伸/扩展），`trend`＝按 docs/spec/走势分段.md
// 的段定义切（v3，卡 card-51571a5f-dc2）。**缺省就是 trend**（取代小栋 2026-10-05 11:09Z 拍的 turn，
// card-21fbf426-889）⇒ 缺省的这一份地址栏一个字都不写（跟 measure 同一条账）。
// ★★ 这一行**不许单独上**：不带 `cut` 的那一趟由**后台的缺省**说了算，回显再把 `paging.cut` 改回后台
//   回的那个（见 load() 上面那段账）。前端先上 ⇒ 后台还回 extend ⇒ chip 亮「延伸」，白改一场。
//   ⇒ 必须跟后台默认值（server.py 的 CUT_MODES／请求缺省／缓存主变体）**同一次部署**。
// ★ 老的 `turn`（笔层出刀）后台已删，但**当 trend 收、不报 400**（分享出去的链接不能打开就挂）——
//   所以地址栏里那个 `?cut=turn` 只会活到 /api/meta 回来为止：回显写 trend，`:1239` 那条闸门把
//   认不出的词摆回缺省，两下一夹，这一页就落在 trend 上。**别在前端也留一份 turn 的名字表**。
const DEFAULT_CUT = 'trend';
// ★ 2026-10-06（小栋定 A，卡 card-3edd7fb3-412）：「延伸」**不摆给用户**了 —— 页面上只留「走势分段」。
//   后台一个字没动：`cut_modes` 照旧回两档、`?cut=extend` 照旧打得开、图脚照旧印得出「延伸」，
//   我们自己比对、查问题全靠它。⇒ 这是**藏起来**，不是删掉。
//   ★ 摆出来只剩一档的时候，`loadMeasures` 那条「只有一个切法就不画这一组」自己会把整组藏掉 ——
//     所以这里不用另写一段隐藏逻辑，也不动 CSS。★ 深链和归一都走**后台那份全名单**，不走这一行。
const CUT_HIDDEN = ['extend'];
// ★ measure 的初值是**地址栏说的那个**（可分享、可截图复现），不是写死的缺省 —— 但地址栏点名的那个
//   后台认不认只有 /api/meta 知道，所以首屏是「先等名单、再发图表那一趟」，见文件末尾的启动那几行。
//   切法同理（`?cut=extend` 可分享），所以这两个词的初值都是**地址栏说的那个**。
const paging = { span: 1, spanMax: null, earliest: false, nogain: false, stop: null, loading: false, failedAt: 0, reqId: 0, applying: false,
                 measure: new URLSearchParams(location.search).get('measure') || DEFAULT_MEASURE,
                 cut: new URLSearchParams(location.search).get('cut') || DEFAULT_CUT,
                 // ★ 笔的根数：地址栏点名的那个（`?pen=7`），没点名就是 null ＝「听后台的缺省」。
                 //   名单到了以后 loadMeasures 会把 null／名单外的数摆回 `pens.def`。
                 // ★ 新笔（B-10＝C，小栋 10-09 06:32）：`?pen=new`。名单成了混型 [6, 7, "new"]，**不许**一律 Number()：
                 //   Number('new') 是 NaN ⇒ 当场掉回缺省，分享出去的 `?pen=new` 打开就变老笔（Bram 06:34 提醒过）。
                 pen: penOf(new URLSearchParams(location.search).get('pen')) };

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
const measures = { list: [], orig: {}, note: {} };
// ---- 中枢切法（卡 card-e346ede6-996；v3 见 card-51571a5f-dc2）----
// 口径：`/api/chart?…&cut=extend|trend`（Bram 10-05 定的契约，v3 换的这一档）。trend＝走势分段、**是缺省**
//   ⇒ 缺省那份不带就不发；extend＝原文那套（可切的一档）。白名单外 400，回显顶层 `cut`，缓存键
//   (span, measure, cut)。★ 老名字 `turn` 后台**当 trend 收**（不 400）、回显写 trend。
// ★ 能切哪几种**以 /api/meta 的 `cut_modes` 为准**，前端不写死（跟 measures／图层名单同一个理由：两份名单
//   迟早错开，那时候用户点的那颗和后台算的那份就不是一回事了）。**名单没到 ⇒ 这一组不画、这个参数
//   一个字都不发** —— 这不是省事：后台的查询白名单里没有这个词的时候，多带一个参数就是 400，
//   整张图会挂在这一个词上（跟 measure 那次是同一个洞，见 load() 里那段注释）。
// ★ 名单没到就自己编一对名字发出去，是这里最坏的做法：看着能用，直到后台把那颗点成 400。
const cuts = { list: [] };
// ---- 笔最少几根 K 线（C3，小栋 10-08 12:42 定：默认 6、可切 7；卡 card-2e6bb3bd-4ae）----
// 口径：`/api/chart?…&pen_min=6|7`（Bram 2007121）。能选哪几档、缺省是哪一档**都听 /api/meta**
//   （`pen_min_options`／`pen_min_default`），前端不写死 —— 默认这会儿还是 7，第二步才翻成 6，
//   写死哪个都会在另一步里变成一句假话。名单没到 ⇒ 这一组不画、这个参数一个字都不发（跟切法同一个洞）。
const pens = { list: [], def: null };
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
// D-3 选 C（小栋 10-09 12:57）：载荷带 `segs_std`（标准化线段＝分界用的那一套）时，最后一条已完成的画**短虚线**、淡一档 ——
//   它的终点还可能往后挪（后面一段走完，标准化会把端点挪到真极值、或者把相邻的并成一条）。未完成那一截照旧是 segDash 的长虚线。
const fadeHex = (h, a) => `rgba(${parseInt(h.slice(1, 3), 16)},${parseInt(h.slice(3, 5), 16)},${parseInt(h.slice(5, 7), 16)},${a})`;   // 从主题色现算，不抄色号
const segStdLast = line({ color: fadeHex(CHART.seg, 0.75), lineWidth: WIDTH.seg, lineStyle: LWC.LineStyle.Dashed });

// 标注层要挂在一个**永远可见**的系列上：挂在「线段」系列上的话，一关线段开关，
// 系列不可见 ⇒ 它的 primitive 也不再被画，价签和买卖点会跟着一起消失（那不是开关的语义）。
// 所以另起一条透明、只放一个点的辅助系列，加在最后 ⇒ 画在最上层，跟 Python「标签最后画」同一次序。
const overlay = line({ color: 'rgba(0,0,0,0)', lineWidth: 1 });
state.overlaySeries = overlay;

state.candleSeries = candle;
// ★ 走势分段那一层排在标注层**后面**：它的底图带（`bottom`）和记号（`top`）住在同一个 primitive 的
//   两个 paneView 里，挂哪条系列不影响 zOrder（`bottom` 就在 K 线底下），所以挂在**永远可见**的
//   `overlay` 上最稳（挂线段那条的话，一关线段开关整层跟着消失 —— 跟上面那段是同一条理由）。
for (const [c, p] of [[candle, makeBoxPrimitive(state)], [overlay, makeAnnotPrimitive(state)],
                      [overlay, makeWolfPrimitive(state)],   // T13：插在走势那层**前面**，trendPrim 仍是最后一个
                      [overlay, makeTrendPrimitive(state)]]) {
  c.attachPrimitive(p);
  primitives.push(p);
}
const repaint = () => primitives.forEach((p) => p._request && p._request());
// ★ 级别对照那一趟（`/api/levels`）回来时**只重画走势那一层**（卡 card-01961644-68f）：它是异步的，
//   比图表那份小得多、通常先到 —— 到了不能走整条 `paint()`（那会 setData、重排、fitContent，
//   首屏还没画完就再来一遍）也不能不管（框已经在屏上了，标得补上去）。所以按住**那一个** primitive
//   单独 `_request()`。`primitives` 里最后那个就是 `makeTrendPrimitive`（顺序见上面那个 for）。
const trendPrim = primitives[primitives.length - 1];
const redrawTrend = () => { if (trendPrim && trendPrim._request) trendPrim._request(); };

// ---------------------------------------------------------------- 级别对照那一行话（card-01961644-68f，L-7／L-9）
// 「这一层到底说了什么」全落在一个**浮层**里（`#lvhead`），**不进图脚** —— 图脚是流内布局，
// 多一行就把 `#chart` 挤矮（`#ghostc` 那一格栽过的同一条，见 index.html 里那段账）。
// 它有两个来源，各自「有才说、没有一个字都不说」：
//   ① 起点那一句（L-7）：只认 `start.status`，`same`／`unmeasured`／没有 start ⇒ 不出现；
//   ② 覆盖率那一句（L-9）：把 `unmeasured`／`partial` 如实报出来 —— 这是"没比成"不被读成"对得上"的**唯一**出口。
// ★ 代号 → 人话：这几个周期名跟图脚那几格一样，**只有一处**（`TF_LABEL`）。认不出来 ⇒ 空串 ⇒ 那句少半截、
//   不编（跟 CUT_NAME／MEASURE_NAME 同一条规矩）。
const TF_LABEL = { '15m': '15 分钟图', '30m': '30 分钟图', '1h': '1 小时图', '2h': '2 小时图', '4h': '4 小时图' };
/** 载荷里的时刻 → `MM-DD`（本地时区，跟 shortLocal／clockLocal 同一处口径）。
 *  ★ 认不出来 ⇒ 空串（不编一个假日子）。`t` 可能给 unix **秒**、unix **毫秒** 或 ISO 串：
 *    数字 >1e12 当毫秒（2026 年的秒数才 1.7e9，差三个数量级，分得开），否则当秒乘 1000。
 *    `new Date(null)` 不是 Invalid 而是 1970 —— 所以 `null`／`''` 先挡掉，别让它安安静静印出个假日子。 */
const mmdd = (t) => {
  if (t == null || t === '') return '';
  const ms = typeof t === 'number' ? (t > 1e12 ? t : t * 1000) : Date.parse(t);
  const d = new Date(ms);
  if (isNaN(d.getTime())) return '';
  const p = (n) => String(n).padStart(2, '0');
  return `${p(d.getMonth() + 1)}-${p(d.getDate())}`;
};
/** 起点那一句（L-7）。★ 返回 '' ＝ 这一格不说 —— **这是常态，不是省略**：只有 `differs`／`window`
 *  才开口；`same`（一样）、`unmeasured`（没量成）、`start` 没有，都**什么都不写**（不知道的事不编）。
 *  ★ `start.status` 是后台 `start_link` 定的四个词（`web/levels.py`）：`same`＝**一样、不标**
 *    ／`differs`＝真分歧／`window`＝窗口不同（印下面那句，不算分歧）／`unmeasured`。
 *    ⇒ `same` **一个字都不许说**：在"一样"上贴一句话，等于**凭空捏一个分歧**出来（跟"没比成说成对得上"
 *      是同一种假账的两个方向）。Bram 的原文就是「一样，不标」。
 *  ★★ **`differs` 只报事实，不下判断**（Nova 14:09Z，card-6e338490）。这句里**没有**任何
 *    「谁对」「算不算分歧」的裁决 —— 原因：`status:'differs'` 只证明**两刀不一样**，**不证明为什么**。
 *    报文的 `differs` 有两种来源：fixture 那次是 spec §四 4 说的**真分歧**（最细 191.35 vs 对照 205.07），
 *    线上那次是**换窗口**把图头挪了 —— 两件事在报文上**逐字节一样**，任何写死的裁决
 *    必然在其中一种上说错（Bram 14:05Z）。⇒ 跟 `unmeasured` 同一条老规矩：**没量到根因就不下结论**。
 *    ★ 所以先前那半句 L-7 disclaimer（「…到 X 才有中枢，这不是级别分歧」）**整条拿掉**，别再加回来。
 *  ★ 「会变」这半句**无条件**（Bram）：`start.finest` 就是最细那张图的 `bounds[0]`，也就是它的
 *    **图头那一刀** —— 「会变」的前提**每次都成立**，拿 `first_center_t` 之类的谓词去分是分不开的。
 *    先前那个 `finest.t < first_center_t` 判据作废。
 *  ★ 第三句「本图第一个中枢 <MM-DD> 开始」—— **这才是 `first_center_t` 的用处**：不是拿它当判据，
 *    是把对照图第一个中枢的日子**印出来**（读者自己看两刀差在哪）。它**可以缺**（后台没给就整句不印），
 *    前两句和「会变」**不能缺**。 */
function levelsStartText(lv) {
  const st = lv && lv.start;
  if (!st) return '';
  // ★ 这一句**不带句号**：句号归**整行**（`renderLevelsHead` 在那行末尾补一个），不归某一段 ——
  //   段与段之间是 `｜`，一段自己带句号的话，后面再接一段就成了"句子说完了又接着说"。
  if (st.status === 'window') return '图里没有更早的数据 —— 两张图的窗口不同，起点没法比，不算分歧';
  if (st.status !== 'differs') return '';           // same／unmeasured：不写（后台 start_link 的 `same`＝一样、不标）
  const who = TF_LABEL[lv.finest_tf] || '';
  const dFine = mmdd(st.finest && st.finest.t);
  const tick = state.data && state.data.meta ? state.data.meta.tick : undefined;
  const fine = (st.finest && st.finest.price != null) ? fmtPrice(st.finest.price, tick) : '';
  if (!who || !dFine || !fine) return '';           // 前两句拼不齐（缺周期名／日子／价）⇒ 整句不说，不写半截
  const seg = [
    `起点按 ${who}算在 ${dFine}（${fine}），以细图为准`,
    // ★ 名字前后**都要那个空格**：`起点按 ${who}算在…` 那一截有，这一截原来漏了 ⇒ 同一句里
    //   同一个名字印成「起点按 15 分钟图…这是15 分钟图…」两种样子。空格是**字面量**（不在
    //   `TF_LABEL` 那几张表里），所以每一处都得自己带 —— 加/改这句的人连空格一起加。
    `这是 ${who}的图头那一刀，窗口一变会跟着挪（「会变」）`,
  ];
  const dC = mmdd(st.first_center_t);
  if (dC) seg.push(`本图第一个中枢 ${dC} 开始`);
  // ★ **不在这里收句号**（Nova 定的）：这一行话是 `｜` 串起来的读数，不是一句话 ——
  //   句号归**整行**末尾那一处（`renderLevelsHead`）。加在这儿，后面再缀一段覆盖率就变成
  //   「…开始。 ｜ 跨度最大的一档，没有对照图」：一句已经说完了，还接着往下说。
  //   1h（没有覆盖率那一句）看不出来，2h 一眼就出来了。
  return seg.join('｜');
}
/** 覆盖率那一句（L-9）——「没比成」的诚实出口。★★ **先看 `ref_tf`，再看缓存**（这两件事在报文上
 *  长得像、意思相反，Nova 五个档全探过）：
 *   · `ref_tf == null` ⇒ 这一档**根本没有对照图**（阶梯最顶那几档）⇒ 说「跨度最大的一档，没有对照图」。
 *     ★ **绝不**说「还没取到」—— 那是在承诺一张**永远不会来**的图（2h／4h 的单个框在报文上也是
 *       `unmeasured`，跟"对照图没缓存"**逐字节一样**，所以只能靠 `ref_tf` 分这条叉）。
 *   · `ref_tf != null && data_at.ref == null` ⇒ 冷缓存 ⇒ 说「对照图（X）还没取到 —— 这一层先不标」。
 *     ★ 这时候**不逐框报数**：23 个框全是 unmeasured，报出来是「23 个框：23 个没比成」——
 *       新开一页就砸这么一句在脸上，是噪音不是信息（说的是"还没到"，不是"出了事"）。
 *   · 有对照图、但个别框没比成（`unmeasured`）或只有一部分比了（`partial`）⇒ 报那一栏数：
 *       `N 个框：M 个比过、[P 个部分没比、]K 个没比成`。★「比过」＝ match ＋ mismatch（都真比了，
 *       只是一个对一个对不上）；`unmeasured` 是**没比**。混成一句就把"没量"说成了"量过"。
 *   · 全比过（match／mismatch，无 partial／unmeasured）⇒ 不占这一格（没话找话）。 */
function levelsCoverageText(lv) {
  if (!lv) return '';
  if (lv.ref_tf == null) return '跨度最大的一档，没有对照图';
  const times = lv.data_at || {};
  if (times.ref == null) {
    const rn = refTfName(lv.ref_tf).replace(/图$/, '');
    // ★ 认不出 ref_tf ⇒ 不编一个名字，也不说这句（名字都念不出来，"还没取到"也指不清是哪个）。
    return rn ? `对照图（${rn}）还没取到 —— 这一层先不标` : '';
  }
  const us = Array.isArray(lv.units) ? lv.units : [];
  const N = us.length;
  if (!N) return '';
  let k = 0, p = 0;
  for (const u of us) { const s = u && u.status; if (s === 'unmeasured') k++; else if (s === 'partial') p++; }
  if (!k && !p) return '';
  const m = N - k - p;                              // 比过 = match + mismatch
  const seg = [`${m} 个比过`];
  if (p) seg.push(`${p} 个部分没比`);
  if (k) seg.push(`${k} 个没比成`);
  return `${N} 个框：${seg.join('、')}`;
}
/** 那一行话 = 起点那一句 ＋ 覆盖率那一句，中间用 ` ｜ ` 接。开关关着 ⇒ 整行收掉。
 *  ★★ 这里的"开关"是**这一层画不画**（`shownOf(opts).lv` ＝ `opts.lv && opts.up`），
 *  不是 `opts.lv` 那一个裸标志 —— 跟 ⑥ 里给框写字用的是**同一个谓词**（`layers.js` 的 `sh.lv`）。
 *  写 `opts.lv && lv` 会出一件很难看的事：「高一级」**默认关着** ⇒ 屏上零个框、零个标，
 *  那一行话却照样印「6 个框：4 个比过、2 个没比」——**它在说屏上根本没有的那几个框**，
 *  而旁边那颗「级别对照」芯片正按灰（"用不了"）。芯片说"没有"，字说"这是结果"，同一屏自相矛盾
 *  （这是「能点却画不出东西的开关是骗人的」那一族的另一头：画不出东西却还在说话的读数）。
 *  ★ `up` 一开关两样一起出、一起收：`applyToggles()` 里就调这个函数（见那儿），所以拨一下
 *    「高一级」，框、标、这一行话三条同时到位 —— 不用另写一份"跟着谁走"的规矩。 */
function renderLevelsHead() {
  const e = el('lvhead');
  if (!e) return;
  const lv = state.levels;
  let txt = '';
  if (shownOf(opts, state.data).lv && lv) {
    const a = levelsStartText(lv), b = levelsCoverageText(lv);
    txt = [a, b].filter(Boolean).join(' ｜ ');
    // ★★ `。` 归**整行**，不归某一段（Nova 2026-10-06 定，见 `levelsStartText` 末尾那段账）：
    //   · 有起点那一句 ⇒ 在**行末**补一个（1h 那一屏跟以前一字不差）。
    //   · 只有覆盖率 ⇒ 不补：`6 个框：4 个比过、2 个部分没比` 是一栏读数，不是一句话，
    //     给它缀个句号是把读数打扮成句子。⇒ 判的是 `a` 在不在，不是"有没有 txt"。
    if (a) txt += '。';
  }
  e.textContent = txt;
  e.classList.toggle('on', !!txt);
}
/** levels 那一趟落地：存到 state 上、只重画走势那一层、更新那一行话（**不走整条 paint**）。 */
function renderLevels() {
  redrawTrend();
  renderLevelsHead();
}

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
// ★ 切法的**缺省是「当前那个」**（`paging.cut`），不是 `undefined`：切法是**看的这一屏**的一个属性
//   （跟档位、看法一样），换品种／换看法／往左补一档／收盘自动重取都得**带着它**走。漏了的话那一趟
//   不带 `cut` ⇒ 后台按缺省回「延伸」⇒ 回显把 `paging.cut` 当场改回 extend —— 用户切好的那一刀
//   在换一次看法之后就自己弹回去了，而且屏幕上没有任何东西说过这件事。（工装 ⑰f 就是这么逮到的：
//   深链 `?cut=extend` 打开，首屏那一趟没带参数，图脚和 chip 一起摆回当时那一档缺省。）
//   ★ 这条理由跟**哪一档当缺省**无关，缺省从 extend 换到 turn 再换到 trend，**机制一个字不变**。
async function load(symbol, tf, span, measure, cut = paging.cut, pen = paging.pen) {
  try {
    const q = new URLSearchParams({ symbol, tf, span: String(span) });
    // ★ 名单还没到手（离线样本、旧后台、或者首屏那个并行的 /api/meta 还没回来）⇒ measure 一个字都不带，
    //   走后台自己的缺省。**这不是省事**：旧后台的查询白名单里没有 measure，多带一个参数就是 400，
    //   整张图会挂在这一个词上。
    if (measures.list.length && measure) q.set('measure', measure);
    // 切法同一条闸门、同一个理由。★ 缺省的 trend **不带**：后台缺省就是它（同一次部署），带上只是噪音，
    //   而且地址栏那份（setUrl）也得跟着少一个词 —— 两处对「缺省」的判断得是同一个（都用 DEFAULT_CUT）。
    if (cuts.list.length && cut && cut !== DEFAULT_CUT) q.set('cut', cut);
    // 笔的根数：同一条闸门。缺省那档**不带**（后台缺省就是它），名单没到也不带。
    if (pens.list.length && pen != null && pen !== pens.def) q.set('pen_min', String(pen));
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

// ---------------------------------------------------------------- 级别对照那一趟（card-01961644-68f，L-9）
/** `GET /api/levels?symbol=&tf=&span=` —— 拿本图（最细那张）的合成框跟**对照图**（后台 `ref_tf`
 *  那一档）的中枢逐框比。
 *  ★ 它**只做一件事**：把载荷原样拿回来交给 layers.js 画、交给浮层写那一行话。前端**不判状态**
 *    （match/partial/mismatch/unmeasured 是后台按 L-9 算的）、**不重算占比** —— 重算就是第二份规矩，
 *    跟后台那份迟早在某一格上错开。
 *  ★ 跟 `/api/chart` 一个写法：`span` 照发；静态打开/旧后台没有这个口 ⇒ **返回 null**（这一层不存在），
 *    页面上一个字都不多、一个标都不画。**不抛**：它不是首屏必需品，拿不到就当没有（fail-closed）。
 *  ★ 它**不参与** `load()` 那个「取不到后台就退回 fixtures」的兜底 —— 仓里没有 levels 样本，
 *    而且这一层的语义就是"后台算了才有"，退回一份假样本等于编数据。 */
async function loadLevels(symbol, tf, span) {
  try {
    const q = new URLSearchParams({ symbol, tf, span: String(span) });
    const r = await fetch(`/api/levels?${q}`);
    if (r.ok) return await r.json();
  } catch (e) { /* 没有后台／没有这个口：这一层不存在 */ }
  return null;
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
  for (const s of d.segs || []) if (over(s.i0) || over(s.i1)) return `线段 [${s.i0}, ${s.i1}]`;   // RAW-SEGS: 体检两套都查（原始里有未完成段）
  for (const s of d.segs_std || []) if (over(s.i0) || over(s.i1)) return `线段（标准化）[${s.i0}, ${s.i1}]`;
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
// 笔的档：6／7 是数，新笔是字符串 'new'。外面进来的（地址栏、/api/meta）一律过这一道，里头就只有这两种形状。
function penOf(x) {
  if (x === 'new') return 'new';
  const n = Number(x);
  return x != null && x !== '' && Number.isInteger(n) ? n : null;
}
function adopt(cur, d, prevLen) {
  const s = { measure: typeof d.measure === 'string' && d.measure ? d.measure : cur.measure,
              // 切法也认回显（跟 measure 同一格）：点的那颗可能失败，屏幕上画的到底是哪种只有后台那份说了算
              cut: typeof d.cut === 'string' && d.cut ? d.cut : cur.cut,
              // 笔的根数也认回显：屏上画的到底是几根的笔，只有后台那份说了算
              //   新笔那档回显 `pen_min: null`（「最少几根」对新笔不成立），认 `meta.pen_rule === 'new'`（Bram 47838ce）
              pen: d.meta?.pen_rule === 'new' ? 'new' : Number.isFinite(d.pen_min) ? d.pen_min : cur.pen,
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
// ★ `levels`（card-01961644-68f，L-9，**可选第五个参数**）＝ 级别对照那一趟的载荷。它跟图表那份
//   **并行**来，换档（往左补数据）时不重取 ⇒ 这里**只在传了它、且 `lv` 开着**时才算它那一栏；
//   不传/为 null ⇒ 跟以前逐字节一样（尺里那些用例走的还是四个参数的老路）。★ 记的是**画出来的那件事**
//   （这个框多标了一个「对不上」的字），不是把载荷序列化 —— 同下面那句"不序列化 trend"的账。
function structKey(d, t0, t1, shown, levels) {
  const sh = shown || null;
  const on = (k) => !sh || !!sh[k];        // 这一层画没画（没给开关就当作画着）
  // 级别对照：`levels.units` 跟框**只有"同下标"这一条契约**（它没有身份字段，连 X0 都没有 ——
  //   见 layers.js `lvAligned` 那段账）⇒ 这里也按**下标**取，并把 layers 那三道闸的第一道
  //   （框数一样）抄过来：框数不一样就当这一层不存在，否则下标错位会把「对标」记到旁边那个框上。
  //   ★ tf／span 那两道闸这儿不比 —— 换档那条路（loadEarlier）当场把 `state.levels` 清成 null，
  //     压根轮不到拿旧档位的快照来算账（见那儿）。
  const tv = d.trend || {};
  const lvUnits = Array.isArray((levels || {}).units) ? levels.units : null;
  const lvStat = (lvUnits && Array.isArray(tv.units) && on('lv') && lvUnits.length === tv.units.length)
    ? lvUnits.map((u) => (u && u.status) || '') : [];
  const ts = (i) => (d.bars[i] || {}).t;
  const ov = (a, b) => a != null && b != null && b >= t0 && a <= t1;   // 区间跟窗口有重叠（含边界）
  const at = (t) => t != null && t >= t0 && t <= t1;                   // 单个时间点落在窗口里
  const inWin = (o) => ov(ts(o.i0), ts(o.i1));
  const row = (o) => `${ts(o.i0)}>${ts(o.i1)}@${o.p0},${o.p1}`;
  const part = (a) => (a || []).filter(inWin).map(row).join('|');
  // 中枢：取**画出来的那个框**的横跨区 ⇒ 跟 layers.js 的 boxes() 同一个取法
  //   （载荷的 X0／X1，没有才退回 host[PI0].i0 ／ host[PI1].i1 —— 跟 boxes() 逐字同一条，card-f2ce0437-ba4：
  //    线段中枢的 PI 指 segs_std，host 却是原始线段，两套端点挪过的地方取出来的范围是错的。）
  //   高一级的标签跟着 `up` 开关走（layers.js 里那个 if 用的就是 sh.up）。
  const boxes = (zs, host, upOn) => (zs || []).map((z) => {
    const a = host[z.PI0], b = host[z.PI1];
    const i0 = Number.isInteger(z.X0) ? z.X0 : a && a.i0, i1 = Number.isInteger(z.X1) ? z.X1 : b && b.i1;
    if (i0 == null || i1 == null) return null;
    const up = (upOn ? (z.up || []) : []).map((u) => `${u.ZD},${u.ZG}`).join(';');   // 升级标签也是画在框上的
    return { i0, i1, s: `${z.ZD},${z.ZG}${z.live ? ',live' : ''}${up ? ',' + up : ''}` };
  }).filter((o) => o && ov(ts(o.i0), ts(o.i1))).map((o) => `${ts(o.i0)}>${ts(o.i1)}@${o.s}`).join('|');
  // 买卖点：一个点 —— 三角和它的字都画在这个 x 上。画不画由 shownOf 说了算
  //   （大开关 ＋ 六个 kind 的 chip ＋ 待确认；带了 shown 就必须带 sigAt，缺了当场炸，不静默放过）
  const sigs = (a) => (a || []).filter((s) => at(ts(s.bar)) && (!sh || sh.sigAt(s)))
    .map((s) => `${ts(s.bar)}@${s.price},${s.kind}${s.why ? ',' + s.why : ''}${s.confirmed === false ? ',未确认' : ''}`).join('|');
  // 线段中枢的 host ＋ 线段那一层「看得见的变化」：都按**图上画的那套**算（跟 layers.js hostOf、app.js paint 同一条）——
  //   有 segs_std ⇒ 已完成段用它、未完成段接原始里的 live；没有 ⇒ 整套原始（card-83915c20-9e3）。
  const stdD = Array.isArray(d.segs_std) && d.segs_std.length ? d.segs_std : null;
  const done = stdD || (d.segs || []).filter((s) => !s.live);   // RAW-SEGS: 老后台退路
  const segsDrawn = stdD ? stdD.concat((d.segs || []).filter((s) => s.live)) : (d.segs || []);   // RAW-SEGS: 未完成段只在原始里有
  // 走势分段那一层（v3 §八，卡 card-c73ab37d-5a1）。★ 跟别的层同一条账：**层关着就不算「看得见」**
  //   —— 开着它却不算它的账，换档之后走势段整个换了一批、屏幕上明明白白变了，那句话却不出声。
  // ★ 记的是**画出来的那几件事实**（分界／中阴那头／待定／撤回／背景带／升级框），不是把整个
  //   `trend` 序列化：序列化会把"载荷里多了一个前端根本不画的键"也算成"屏幕变了"，那正是喊狼。
  const trend = () => {
    const T = d.trend || {};
    const b = (T.bounds || []).filter((x) => at(ts(x.bar)))
      .map((x) => `${ts(x.bar)}@${x.price},${x.kind}>${ts(x.pullback_end_bar)}`).join('|');
    const pd = (T.pending || []).filter((x) => at(ts(x.bar))).map((x) => `${ts(x.bar)}@${x.price},${x.kind}`).join('|');
    const rt = (T.retracted || []).filter((x) => at(ts(x.bar)))
      .map((x) => `${ts(x.bar)}@${x.price},${x.kind}>${ts(x.retracted_bar)}`).join('|');
    const sg = (T.segments || []).filter((s) => ov(ts(s.i0), ts(s.i1)))
      .map((s) => `${ts(s.i0)}>${ts(s.i1)}@${s.type}${s.upgraded ? ',升级' : ''}${s.live ? ',live' : ''}`).join('|');
    // ★★ 合成大框（`un`）现在**归 `up` 那颗芯片**，不跟 `trend` 走（小栋 10-05 23:3xZ 定，
    //   卡 card-113a3b16-026；`layers.js` 里那两个 if 用的是同一个 `shownOf`）。⇒ 可见性也得各按各的开关取：
    //   `trend` 关着的时候前四样不画，`up` 关着的时候合成框不画 —— 谁关着就不算谁"看得见"，
    //   否则"开关关着的层变了"会被算成"屏幕变了"，正是这一段开头那句喊狼。
    // ★★ 级别对照那枚短标也要进账：`match`／`partial`／`unmeasured` 都**不出字**，只有 `mismatch`
    //   会在框右沿多写一句（见 layers.js ⑥）—— 所以只有 `mismatch` 算"屏幕变了"。
    //   ★ 记的是**画出来的那件事**（这个框多标了「对不上」），不是把 levels 载荷序列化（同上面那句账）；
    //     对不上的框（`lvStat` 里没有 / 状态不是 mismatch）一个字节都不加 ⇒ 旧用例仍逐字节一样。
    //   ★ 这里顺手复用的是 `lvStat`（按下标的对位表）：先记**原下标**再按窗口筛 —— 筛完还认得出是哪一条。
    //     没标的那几条（状态不是 mismatch）一个字节都不加 ⇒ 跟画那半边走同一条判据。
    const un = (on('up') ? (T.units || []) : []).map((u, i) => [u, i])
      .filter(([u]) => ov(ts(u.X0), ts(u.X1)))
      .map(([u, i]) => `${ts(u.X0)}>${ts(u.X1)}@${u.DD},${u.GG}${lvStat[i] === 'mismatch' ? ',对标' : ''}`).join('|');
    return (on('trend') ? [b, pd, rt, sg].join('/') : '') + '/' + un;
  };
  return [on('pen') ? part(d.pens) : '', on('seg') ? part(segsDrawn) : '',
          on('pc') ? boxes(d.centers, d.pens || [], on('up')) : '',
          on('sc') ? boxes(d.seg_centers, done, on('up')) : '',
          // 小转大的二类（走势层 xzd_seconds，M29）画在段级买卖点那一路里 ⇒ 算进段级那一份；字（why）也算，二买 ↔ 二买·盘背 是看得见的变化
          sigs([...((d.signals || {}).seg || []), ...((d.trend || {}).xzd_seconds || [])]), sigs((d.signals || {}).pen),
          (on('trend') || on('up')) ? trend() : ''].join('#');
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

// ---------------------------------------------------------------- 「消失的点」（卡 card-cf3ed018-795）
// 小栋 10-05 ②A：**确认过的**买卖点，后来又没了 —— 在图上把它标出来（空心 ＋ 划一刀，悬停说一句）。
//
// ★ 这件事**只在有人看着的时候才成立**。谁也没看的那些小时里它没了几次，这张图不知道，也不该装作
//   知道（那是第二步那个离线标注文件的活）。所以底下就是一个**页面内存里的账本**：每次新数据回来，
//   跟同一个桶里上一份比一比，少掉的记下来；**重开页面就清零**。因为只在内存里，它天生就是
//   「本次打开」—— 不需要后台留历史（Bram 10-05 那个「要存每个点的首次确认时刻」的估价当场收回了）。
//
// ★ 桶 = (品种, 周期, 看法, 档位)。**少一样就会造鬼**：
//   · 换看法（面积 ↔ 黄白线）不是重画，是**换了一把尺**。拿新尺子量出来的点去比旧尺子那份，
//     旧尺子的点全都「少了」，屏幕上当场刷出一片空心三角 —— 而那件事根本没发生。
//   · 往左加载同一条：档位一变，后台是**整段重算**，靠左那一段本来就会变（span_measure 量过）。
//   ⇒ 这两个动作**换桶**，不是「喂给同一个桶比」。这跟「加字段别换形状」是同一族毛病：
//     把「状态变了」和「换了一把尺」当成了一件事。
//
// ★ 点的身份 = (层级, 种类, 极值那根的时间戳)。**不许用下标**（Bram 10-05 第 ③ 条）：
//   往左补数据是往数组头上插，同一个下标当场就指向另一根 K 线（跟 anchorOf / structKey 同一条账）。
//
// ★ 只比**已确认**的点（Bram 第 ② 条）：待确认的点本来就会变，它变了不算「消失」；
//   但「已确认 → 变回待确认」**要算** —— 那种点确实从图上被拿掉了。做法是这份账本**只把已确认的
//   收进基准**，所以它下次没出现在已确认那份名单里，就自然算成消失，不用另写一条判据。
//
// ★ 左沿守卫（Atlas 10-05 提的）：线上窗口是定长的（210 天），起点自己会往后滑。起点一动，
//   靠左沿那一段的结构本来就会被重算 —— 那里的点掉掉不是「被推翻」，是**尺子从左边收了一格**。
//   拿 tools/span_measure.py 那套量法（同一档位、只把窗口往后滑），在 ZECUSDT 15m span=1
//   （20161 根）上量了三档：
//       滑  1 根（15 分钟）⇒ 重叠区 **0 处**差异
//       滑 16 根（4 小时） ⇒ 5 处，最靠右那处在**离左沿第 2009 根**
//       滑 96 根（1 天）   ⇒ 10 处，最靠右那处在**离左沿第 5463 根**
//   比值 126 / 57 不稳（只有一份品种、三档滑动），所以倍数往上取 200 留足余量、下限 200 根。
//   这道闸**宁可少报也不误报**：它吃掉的只是窗口最左边那一段（用户基本不看那儿）；
//   误报一个「消失的点」，是拿一句假话去解释一件没发生的事 —— 那比漏报贵得多。
const GHOST_SLIDE_MUL = 200, GHOST_SLIDE_MIN = 200;
const ghostBuckets = new Map();      // 桶 → { pts: 上一份的已确认点, gone: 记下来的消失, first: 上一份的窗口起点 }

function ghostConfirmed(d) {
  const m = new Map();
  for (const tier of ['seg', 'pen']) {
    for (const s of (d.signals || {})[tier] || []) {
      if (s.confirmed !== true) continue;                    // 待确认的不进基准（见上）
      const t = (d.bars[s.bar] || {}).t;
      if (t == null) continue;                               // 点落在数据外面 ⇒ 身份都组不出来，跳过
      m.set(`${tier}|${s.kind}|${t}`, { tier, kind: s.kind, t, price: s.price });
    }
  }
  return m;
}

/** 新的一份数据到了：跟同一个桶里上一份比，少掉的点记成「已经消失」。结果挂在 `d.ghosts` 上
 *  （图脚和图都从 `d` 上读 —— 不留中间变量，跟 sourceLabel 那条同一条理由）。 */
function ghostReconcile(d) {
  // ★ `engine`（core/*.py 的版本，Bram 10-05 加在 /api/chart 顶层）**也进键**：引擎一换就是**换了一把尺**，
  //   不能拿新旧两份比出「消失」。不并的话，部署那一刻**所有开着的页面**会当场把整屏读成「全没了」——
  //   满屏假空心点，而用户什么都没做（跟我刚修掉的「取不到后台退回样本」是同一个病：把另一份数据当成
  //   「同一份数据刷新了」）。
  //   ★ 读 **chart 自己那份**，不读 /api/meta：meta 只在页面打开时取一次，部署之后开着的页面手里还是旧 meta
  //   （Bram 指出的）。旧后台/样本没有这个字段 ⇒ 取 `''`，跟今天的行为一模一样。
  //   往回滚也一样：E1→E2→E1 各算各的桶，不会拿 E2 那份去比 E1 的本子。
  // ★ 切法（`cut`）和笔的根数（`pen_min`）**也进键**，理由跟 engine 一样：换的是**规则**，不是同一份数据刷新了。
  //   漏掉的话，用户从 7 根切到 6 根，上一份（7 根）的已确认点在新的一份里对不上，当场被记成「消失的点 34」
  //   —— 用户只是换了个设置（10-08 实测逮到）。切法那一半原来就漏着，同一个洞，一起补。
  const key = [d.symbol, d.tf, d.measure || paging.measure, d.cut || paging.cut, d.pen_min ?? paging.pen ?? '',
               d.span ?? paging.span, d.engine ?? ''].join('|');
  const prev = ghostBuckets.get(key);
  const now = ghostConfirmed(d);
  if (prev) {
    const start = (d.bars[0] || {}).t;
    const stepMs = Math.max(1, ((d.bars[1] || {}).t - start) || 1);
    const slide = prev.first != null && start != null && start > prev.first
      ? Math.round((start - prev.first) / stepMs) : 0;
    const guardT = (d.bars[Math.min(Math.max(GHOST_SLIDE_MIN, slide * GHOST_SLIDE_MUL), d.bars.length - 1)] || {}).t;
    for (const [k, p] of prev.pts) {
      if (now.has(k)) continue;                              // 还在 ⇒ 什么都没发生
      if (p.t < guardT) continue;                            // 离左沿太近：尺子动过，不算（见上）
      if (prev.gone.has(k)) continue;                        // 早记过了 —— 第一次丢失的时刻才算，别被后面的刷新改写
      prev.gone.set(k, { ...p, at: Date.now() });
    }
    // ★ 又回来了 ⇒ 记号收掉：它现在就在图上，两个记号并列是自相矛盾。
    //   这一句**必须**扫 gone 自己，不能挂在上面那个循环里 —— 一个点进了 gone，就是因为它**不在**
    //   `now` 里，而 `b.pts = now` 又把它的键从 pts 里抹掉了；它回来的时候 pts 里已经没有这个键，
    //   上面那个循环根本看不见它。（2026-10-05 工装 ⑧ 那一格抓到的就是这一条：macd 第 3 趟
    //   明明把点给回来了，记号还挂在图上。）
    for (const k of [...prev.gone.keys()]) if (now.has(k)) prev.gone.delete(k);
  }
  const b = prev || { pts: new Map(), gone: new Map() };
  b.pts = now;
  b.first = (d.bars[0] || {}).t;
  ghostBuckets.set(key, b);
  // 记号要画在**当前这份**数据上：按时间戳找回下标（下标会随往左补数据整体平移，不能用旧的）。
  // 找不回（它那根已经滑出窗口了）就**不画** —— 位置画不出来的时候宁可不画，也不能挪个地方画：
  // 位置本身就是这句话的一半。
  const idx = new Map();
  for (let i = 0; i < d.bars.length; i++) idx.set(d.bars[i].t, i);
  d.ghosts = [...b.gone.values()].map((g) => {
    const i = idx.get(g.t);
    // `confirmed: true` 不是给它脸上贴金：它当初就是已确认的（本子只收已确认的），
    // 而 layers.js 那边画不画它走的是**同一个** sigAt（大开关 ＋ kind 芯片）——
    // 少这个字段，芯片一关它自己就没了，跟别的点两种待遇。
    return i == null ? null : { bar: i, price: g.price, kind: g.kind, tier: g.tier, t: g.t, at: g.at, confirmed: true };
  }).filter(Boolean);
}

// 悬停说明：画布上的记号没有 DOM，自己挂一层。命中判定在 layers.js（窗格坐标系只有那一处知道），
// 这儿只管把鼠标位置递进去、把话摆出来。`fixed` 跟着指针走；`pointer-events:none`（见 style.css）
// 它是说明、不是按钮，不许把拖拽/缩放吃掉（跟 .more / .readout 同一条账）。
const ghostTip = document.createElement('div');
ghostTip.id = 'ghosttip';
ghostTip.className = 'ghosttip';
ghostTip.setAttribute('role', 'tooltip');
document.body.appendChild(ghostTip);
let ghostOn = null;          // 现在指着哪一个（换了才重写文字，不然每动一下都重排）
// 两个时刻**都要带 UTC**：时间轴的刻度就是 UTC（localization.timeFormatter 是 timeLabel），
// 悬停里省掉这两个字母，用户就会拿本地时间去对轴上的刻度，然后怀疑图上标错了位置。
const ghostDate = (ms) => new Date(ms).toISOString().slice(5, 16).replace('T', ' ');   // 10-05 12:43
const ghostTime = (ms) => new Date(ms).toISOString().slice(11, 16);                    // 12:43

function ghostShow(e, g) {
  if (g !== ghostOn) {
    ghostOn = g;
    // ★ 措辞按 Atlas 2026-10-05 核的那条改过一版：原来写「这个点 04-02 13:30 出现过」，可那是
    //   **极值那根**的时间，点在这之后才确认 —— 那一刻它还没「出现」。别让一句话把时间说错：
    //   `g.t` 是极值那根，`g.at` 才是我们**看着它没掉**的那一刻。
    ghostTip.textContent =
      `极值在 ${ghostDate(g.t)} UTC 的这个${g.kind}，之前确认过 —— 本次打开 ${ghostTime(g.at)} UTC 那次取数时它已经不在了\n`
      + `（只在页面上记着，重开就清空）`;
  }
  placeTip(e);
}
// 摆位置：两个来源（幽灵点、分界）共用这一支 —— 这条式子抄两份，迟早在某一格上错开
// （跟"坐标换算只留一处"是同一条账）。`pointer-events:none` 见 style.css。
function placeTip(e) {
  ghostTip.classList.add('on');
  const r = ghostTip.getBoundingClientRect();
  ghostTip.style.left = `${Math.max(8, Math.min(e.clientX + 14, innerWidth - r.width - 8))}px`;
  ghostTip.style.top = `${Math.max(8, Math.min(e.clientY + 14, innerHeight - r.height - 8))}px`;
}
function ghostHide() { ghostOn = null; ghostTip.classList.remove('on'); }

// 分界那句（卡 card-22888623-1a7）：大横盘后补切的那一刀，凭什么在这儿（第 29 课）。
// ★ 认人靠 `rule`，**判据只有一处出处**：后端在 bound 上标的那个值。前端不自己重推一遍
//   「这一刀算不算 D2-8」—— 重推就是把判据写成两份，迟早在某一格上错开（app.js:130 那条账）。
// ★★ 字段名**换过一次**，记在这儿免得以后有人去找一个不存在的 `via`：Nova 10-06 拍的是
//    `via: "D2-8"`，Bram 落引擎时用的是 **`rule`**，而且给**每一刀**都带名字
//    （普通的 `"D2-2"`＝反方向三类点确立，补的那刀 `"D2-8"`）。引擎是**产的那一头**，
//    所以前端跟着改成 `rule`；`trend_check` 那边还有一条不变量「每刀都得有认得的 rule」。
//    ⚠️ 两边名字不同时**不会报错**，浮层只是**静默不出** —— 这类错最费时间，所以才写这一段。
// ★ 第六批 ② 起每一刀都有死点类型（D2-5），浮层都有话说；没有 death 的（旧后台）照旧不出 —— 浮层冒出来却什么都不说，比不出来更让人以为这儿有事。
// ★ 那句话是 Nova 10-06 定的原话，一个字没改（「按第 29 课：大横盘后接一段上涨，在这里切开」）。
const BOUND_TIP = '按第 29 课：大横盘后接一段上涨，在这里切开';
// D2-5 死点类型（第六批 ②）：每一刀都出一句「这一刀是怎么死的」，全名＋后台给的理由（`death_why`），一个字不改写。
//   D2-8 那一刀照旧先说第 29 课那句（Nova 10-06 定的原话），死点那句接在后面。
// 六类的一句话和出处：Atlas 10-09 00:37 照 spec 走势分段.md D2-5（第 118-131 行）列的，「一句话」是他按 spec 写的白话。
//   ★ 后三类是**编者口径**，原文没有这几个名字 ⇒ 出处照实写「编者口径」，不挂原文。
//   ★ 小转大引 L44 那条定理，原文说的是**必要条件**，写「L44（必要条件）」，不写成「L44 判定」。
const DEATH_INFO = {
  '趋势背驰': ['这一刀正好是引擎认出的一买／一卖：趋势里最后一段跟前一段比，力度变小了。', 'L24 背驰（趋势背驰）'],
  '盘整背驰': ['离开中枢的那一段 C，比进入那一段 A 走得更远，可力度（面积）更小。', 'L24、L27'],
  '小转大': ['前一段是本级别趋势，趋势背驰、盘整背驰都真比过，都不成立；是小级别的转折带出了这一级的转折。', 'L43；L44（必要条件）'],
  '盘整·未见背驰': ['跟「小转大」一样都比过、都不成立，但前一段是盘整，不叫小转大。', '编者口径'],
  '比不了': ['没法比力度：找不到它离开的中枢，或者找不到进入段，或者进入段方向跟 C 相反。不算小转大。', '编者口径'],
  'D2-8 补刀': ['这一刀是大一级盘整里按中枢排布切出来的，不是背驰，也不是反方向三类点确立的，不分类。', '编者口径'],
  // S5 刀（同级别正式版，S12，Atlas 定名）。原文 L38:20「那么就当成两个 30 分钟盘整类型的连接」（语料硬折行，这半句整在第 20 行）。
  //   图上不挂字（layers.js 故意不收进 DEATH_SHORT），只在这里讲。
  '盘整相连': ['两个同级别盘整首尾相接的接缝：前一个中枢的第三段走完，后一个中枢就从这里起。不是背驰，也不是三类点确立的，不分类。', 'L38:20 正文「当成两个 30 分钟盘整类型的连接」；编者口径 S12'],
};
// ①D（同级别正式版，D-1／D-3／D-5）：刀上 `state`。只读后台给的值，前端不推（S5 的也由后台按 D-4 派生）。
const STATE_TIP = {
  pending: '状态：待确认 —— 确认条件还没满足，这把刀还可能被撤回（图上空心点）。确认以后就不再撤。',
  confirmed: '状态：已确认 —— 以后不再撤。',
};
function boundText(b) {
  const st = STATE_TIP[b.state] || '';        // 没有 state（老后台／现行口径）⇒ 不写这一行，跟改之前一个字不差
  if (!b.death) return [b.rule === 'D2-8' ? BOUND_TIP : '', st].filter(Boolean).join('\n');
  const [say, src] = DEATH_INFO[b.death] || ['', ''];
  const d = [`死点：${b.death}${say ? ' —— ' + say : ''}`, b.death_why ? `这一刀：${b.death_why}` : '', src ? `出处：${src}` : '', st]
    .filter(Boolean).join('\n');
  // ★ 刀的位置不归类型管（spec D2-5：类型只影响「中阴从哪一刻开始」和图上标什么字），所以这里一句都不提刀为什么落在这儿
  return b.rule === 'D2-8' ? BOUND_TIP + '\n' + d : d;
}
function boundShow(e, b) {
  if (b !== ghostOn) { ghostOn = b; ghostTip.textContent = boundText(b); }
  placeTip(e);
}
// 盘整组那块标签（卡 card-9f7a80b6-e8a）：为什么相邻几段盘整标成一组。引原文两句，**分界不动**这件事也说出来
// （不然读者会问"既然是同一个，为什么中间还有竖线"）。原文逐字：主引 L38 原博正文、L45:60 答疑；附 L33:162（镜像答疑，不当原博正文；Nova 22:03 定）。出处见 spec 走势分段.md D1-3／§八 9。
const PZ_TIP = '相邻这几段都是盘整：照原文，它们是同一个更大的盘整（中枢延伸、扩展出来的），中间的分界照旧画着、没动。\n'
  + '第 38 课：「注意，以前说不允许“盘整+盘整”是在非同级别分解方式下的」\n'
  + '第 45 课答疑：「如果真是盘整+盘整，那就是中枢延伸或扩展出来的，除了在同级别分解中可以允许盘整+盘整，其他情况下是不允许的。」\n'
  + '第 33 课答疑（镜像）：「盘整+盘整还是盘整，但加多了就是级别大的盘整」\n'
  + '（本页用的是非同级别分解）';
function pzShow(e, g) {
  if (g !== ghostOn) { ghostOn = g; ghostTip.textContent = PZ_TIP; }
  placeTip(e);
}
el('chart').addEventListener('mousemove', (e) => {
  // 幽灵点优先：它是个小方框，分界那条带是**满高**的一列 —— 两者叠上时该说话的是那个点
  // （"这个点之前确认过"是这一眼下更具体的一件事）。
  const g = ghostHitAt(e.clientX, e.clientY);
  if (g) { ghostShow(e, g); return; }
  // 盘整组标签排在分界**之前**：理由跟幽灵点一样 —— 标签是一小块，分界那条带是满高的一列，
  // 两者叠上时指针分明是指着标签。
  const p = pzHitAt(e.clientX, e.clientY);
  if (p) { pzShow(e, p); return; }
  const b = boundHitAt(e.clientX, e.clientY);
  if (b && boundText(b)) { boundShow(e, b); return; }
  ghostHide();
});
el('chart').addEventListener('mouseleave', ghostHide);
// 图在动（滚轮/拖拽缩放）时记号会跟着挪，指针底下那个可能已经不是它了 ⇒ 收掉，等下一次 mousemove 再说。
el('chart').addEventListener('wheel', ghostHide, { passive: true });

// ---------------------------------------------------------------- 画一张
// ★ 画（paint）和**摆视口**（draw 里那一段）分开了：往左补数据之后重画，**不能**再走「摆视口」
//   那一段（它要么 fitContent 缩成一团、要么按 ?last/?at 跳走）—— 补数据时视口由 place() 按**时间**放回原位。
/** 页头「最新 …」**唯一**的一处写法。paint（新数据落地）和跳价（card-f3fffac4-83d）都从这儿走 ——
 *  两处各写一遍就会分家（图上写着 A、页头写着 B，那种账这一屏上已经栽过）。
 *  ★ 价**停住**的时候必须写出来停在哪一刻：跳价那一趟后台没拉到新的（回的 `stale=true`，
 *    `fetched_at` 冻在上次成功那一刻）⇒ 「最新」两个字不加注明就是一句假话（跟角上那句同一个道理）。 */
function renderLast() {
  const d = state.data;
  const last = d && d.bars && d.bars.length ? d.bars[d.bars.length - 1] : null;
  const badge = el('last');
  if (!last) { badge.textContent = ''; badge.className = 'badge'; badge.removeAttribute('title'); return; }
  // ★ 收价取 `bars` 那份的 `c`（短键）：`d.bars` 是**源**（跳价改的就是它），图上那份是它的映射
  //   （paint 里 `d.bars.map(...)`）。两处口径一样，但字段名不一样 —— 写成 `.close` 就是 undefined，
  //   而 fmtPrice 会当场抛（`v.toLocaleString`）⇒ paint 半路炸掉，后面的 stamp/autoPlan 全没了。
  const px = `最新 ${fmtPrice(last.c, d.meta?.tick)}`;
  if (!tickStale) { badge.textContent = px; badge.className = 'badge'; badge.removeAttribute('title'); return; }
  const at = clockLocal(tickAt);
  // ★ 这一格**自己不带时区字样**（card-e7554dd2-44a 的口径）：它是同一行里最左边那颗短徽标，
  //   而这一行的偏移量由右边那颗常驻的「本根…数据…」写在末尾 —— 一行的钟说一遍就够，
  //   两颗徽标各写一遍，360 宽上先爆的就是它们（见 style.css 手机那段的账）。
  //   说清楚的那句话在 title 里（下面那行），一个字都没省。
  badge.textContent = at ? `${px} ｜ 价格停在 ${at}` : `${px} ｜ 价格停了`;
  badge.className = 'badge warn';
  const za = at && tickAt ? `（本地时区 ${zoneTag(new Date(tickAt))}）` : '';
  badge.title = at
    ? `跳价这一趟没拉到新的（后台回的 stale=true）—— ${px} 是 ${at}${za}那一次的，之后就停在那儿了`
    : '跳价这一趟没拉到新的（后台回的 stale=true），这个价之后就停在那儿了';
}

function paint(d) {
  state.data = d;
  // ★ 新的一份数据落地 = 价的"新鲜度"重新从这一份算：跳价记着的那两笔（取数时刻、有没有卡住）
  //   是**上一份**的账，不清掉页头会拿旧戳冒充新数据（见 tickApply 那段）。反正下一趟跳价（≤5 秒）就来。
  tickAt = null; tickStale = false;
  // ★ 记账要在**画之前**：记出来的东西挂在 d 上（d.ghosts），layers.js 和图脚都是从 d 上读的
  //   —— 顺序反了屏上就是上一份的记号（跟 renderMeta 那条"不留中间变量"是同一类账）。
  ghostReconcile(d);
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
  // ★ S7「暂定」（card-d5a92ea2-3b2）：暂定段也带 live ⇒ 未完成的可能有**两条**首尾相接：暂定段（起点 → 判出来的那一刀 V）
  //   ＋ 它后面真正还在走的那一截（V → 迄今的极值）。原来只取 `find` 第一条 ⇒ 后面那一截**整条不画**。
  //   两条都是虚线、在 V 处拐弯，V 上那个虚线圈和「暂定」两个字在 layers.js 端点那一层画。
  // D-3 C：有 `segs_std` ⇒ 已完成的线段画标准化那一套（跟分界同一套），最后一条单拎出来画短虚线；没有 ⇒ 照旧画原始段。
  const std = Array.isArray(d.segs_std) && d.segs_std.length ? d.segs_std : null;
  // 哪几条画虚线：载荷里每条带 `state`（"pending"／"confirmed"）就**照它**（后台 snapshot 那一行说了算，跟撤回账本同一把尺）；
  //   没带 `state`（老载荷）⇒ 退回「只有最后一条」。待确认的一定是尾巴上连着的几条 ⇒ 一条折线就画得下。
  const nOpen = std ? (std.some((s) => s.state) ? std.length - std.findIndex((s) => s.state === 'pending') : 1) : 0;
  const open = std && nOpen > 0 && nOpen <= std.length ? std.slice(-nOpen) : [];
  // RAW-SEGS: 未完成段（live／暂定）只在原始里有；已完成段有 segs_std 就用它
  const segs = d.segs, lives = segs.filter((s) => s.live), done = std ? std.slice(0, std.length - open.length) : segs.filter((s) => !s.live);
  segStdLast.setData(open.length ? [{ time: T(open[0].i0), value: open[0].p0 }].concat(open.map((s) => ({ time: T(s.i1), value: s.p1 }))) : []);
  const segA = done.length ? [{ time: T(done[0].i0), value: done[0].p0 }] : [];
  for (const s of done) segA.push({ time: T(s.i1), value: s.p1 });
  segSolid.setData(segA);
  const dash = [];
  for (const s of lives) {
    if (!dash.length) dash.push({ time: T(s.i0), value: s.p0 });
    if (s.tentative) { dash.push({ time: T(s.i1), value: s.p1 }); continue; }
    const ext = s.dir === 'up' ? s.hi : s.lo;
    let k = s.PI0;
    for (let j = s.PI0; j <= s.PI1; j++) if (d.pens[j] && d.pens[j].p1 === ext) k = j;
    dash.push({ time: T(d.pens[k].i1), value: ext });
  }
  segDash.setData(dash);

  overlay.setData(bars.length ? [{ time: bars.at(-1).time, value: bars.at(-1).close }] : []);
  paintVol(d);
  syncSub();                 // 副图跟着主图一起换（同一份 K 线、同一个档位）；关着就一个请求都不发
  syncWolf();                // 入门防守同理（T13）：关着不请求；开着就跟着品种／档位换（周期另选）
  applyToggles();
  renderMeta(d);
  renderLast();
  stamp(d);
  // 数据一落地就按**这一份**重排自动重取（见那一节）。放这儿是因为 paint 是**所有**数据的唯一落点
  // ——首屏、换品种、换看法、往左补数据、自动重取自己，全从这儿过，不用在每个入口各排一次。
  autoPlan();
}

// 装一张新数据：**先画，再摆视口**。keep 是补数据前抓的锚点（见 paging）；给了它就走「按时间放回原位」。
/** ★ 记下「此刻屏上这一份是哪一档」（品种/周期/档位）。**放在 `draw()` 头一行**：每一条会把载荷
 *  摆上屏的路（首屏／换看法／换切法／换品种／往左补数据）都得走这个口，一处漏写就漏一处。
 *  ★ 记的是**回显过的**档位（`paging.span` 是 `adopt()` 从响应里认来的，不是我们发出去的那个数），
 *    跟"后台会钳档"那条账同一条 —— 级别对照的对齐守卫要拿它比（layers.js `lvAligned`）。 */
function noteView() { state.tf = el('tf').value; state.span = paging.span; }
function draw(d, keep) {
  noteView();
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
    const sh = shownOf(state.opts, state.data);
    // ★★ 补数据**一换档，手上那份 levels 当场作废**（card-01961644-68f）：它是对着**旧那一档**的
    //   `trend.units` 逐框数出来的（`levels.units` 跟框只有"同下标"这一条契约），档位一变，
    //   同一个下标在新图上指的就不是同一个框了 —— 标会整批错位，而屏上照样是"有字的"。
    //   它也不重取（`/api/levels` 是跟首屏 `go()` 并行发的那一趟）⇒ 只能**先全撤**，保守那一边。
    //   ★ 摆在**取基准之前**：前后两次 `structKey` 都给 `null`，那一栏两边都不加 —— 不喊狼
    //     （levels 缺席时本来就一个字节都不加，见 structKey 里 `un` 那段）。
    if (paging.span !== span) { state.levels = null; renderLevelsHead(); }
    const keyBefore = win && structKey(own, win.t0, win.t1, sh, state.levels);
    Object.assign(paging, adopt(paging, d, own.bars.length));   // 回显说了算（钳档 / earliest / 有没有多出来）
    setUrl();
    // ★ 摆图之前再看一眼：`adopt()` 可能把档钳回去（15m 要 16 钳到 4）⇒ 真换了档，仍要作废。
    if (paging.span !== state.span) { state.levels = null; }
    draw(d, anchor);
    // 同一段时间、换完之后再取一次：不一样 ⇒ 用户正看着的那一屏被重算了 ⇒ 说一句，3 秒自己收
    if (win && structKey(d, win.t0, win.t1, sh, state.levels) !== keyBefore) showNotice();
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

/** 一根 K 线摊成读数那一块的**形状**。★ 只有这一处：十字线停在哪一根、跳价改了哪一根，说的是同一个形状。
 *  `tSec` 是**秒**（跟 LWC 的 param.time 同一个单位 —— 时间轴和读数都从这儿念数）。
 *  `prevClose` 缺（最左边那根、或者还没有前一根）⇒ 涨跌幅写「不知道」，不编一个数给它。 */
const readBox = (o, h, l, c, tSec, tick, prevClose) => ({
  t: tSec, o, h, l, c, tick,
  pct: prevClose ? (c - prevClose) / prevClose * 100 : null,
});
function readAt(param) {
  const s = param.seriesData && param.seriesData.get(candle);
  if (param.time == null || !s) return null;
  const bars = (state.data && state.data.bars) || [];
  const i = timeIndex(bars, param.time * 1000);        // ★ 按时间找（换档是往数组头上插，下标会错位）
  const prev = i != null && i > 0 ? bars[i - 1] : null;
  return readBox(s.open, s.high, s.low, s.close, param.time,
                 state.data.meta && state.data.meta.tick, prev && prev.c);
}
/** 跳价改的是**画在图上**的那一根 ⇒ 十字线要是正停在这根上，读数也得跟着换（card-f3fffac4-83d）。
 *  不换的话，图上那个价在动、块里那个数冻着 —— 两个数指着同一根 K 线，就是一句谎
 *  （跟 paint() 里 hideRead() 那条是同一笔账：屏上和读数必须是同一份）。
 *  `subHover` 就是十字线停在哪一根（秒，跟 param.time 同一个单位）；读数收着、或者停在别处，就不动它。 */
function readTick(d) {
  const bars = d.bars, i = bars.length - 1;
  if (!readShown || subHover == null || i < 1) return;
  if (Math.round(subHover * 1000) !== bars[i].t) return;
  showRead(readBox(bars[i].o, bars[i].h, bars[i].l, bars[i].c, bars[i].t / 1000,
                   d.meta && d.meta.tick, bars[i - 1].c));
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
  const pane = chart.panes()[1];
  // ★ 窗格刚建、LWC 还没把它排出来时 `getHeight()` 是 **0**，这一拍**不许摆**：
  //   下面那行 top 是拿 `pane.getHeight()` 减出来的，按 0 算就**低一整格**
  //   （实测格高 172 ⇒ 该是 514px，算成 686px ＝ 514＋172），页头整块掉到副图下面去。
  //   而这一拍之后**不一定还有下一趟**：`syncSub()` 认出「还是这一格」就直接返回，不再取数、不再重画
  //   ⇒ 错的值会**一直挂着**（2026-10-05 实测：连点两次开关就进这个状态，等 2.6 秒也没人修）。
  //   所以：版面没出来就先不摆，下一帧再试一次；试满 500ms 就放手（不空转 —— 图被藏起来时高度永远是 0）。
  if (!pane || !pane.getHeight()) {              // 窗格还没回来也算：拿不到格高就不摆
    const now = performance.now();
    if (!subPlaceFrom) subPlaceFrom = now;
    if (now - subPlaceFrom < 500) requestAnimationFrame(placeSubhead);
    else subPlaceFrom = 0;                       // 额度用完就清掉：下一次「格高还是 0」重新给 500ms
    return;
  }
  subPlaceFrom = 0;
  reserveSubhead();                              // 先给页头让出那一条（比例尺变了不影响下面那行 top 的计算）
  const chartBox = el('chart').getBoundingClientRect();
  const tsH = chart.timeScale().height();          // 时间轴是**共用**的一条，压在整栏的最下面
  // top 是**相对 .overlays 那个盒子**算的（它就是 subBox 的定位祖先，自己离图顶有 10px，见 style.css）——
  // 那个 10px 不在这里再抄一遍：从**两个盒子的实测距离**里减掉（CSS 改了这里也跟着对）。
  const offset = subBox.parentElement.getBoundingClientRect().top - chartBox.top;
  const top = chartBox.height - tsH - (pane ? pane.getHeight() : 0) + SUBHEAD_TOP - offset;
  subBox.style.top = Math.max(0, Math.round(top)) + 'px';
}
// 页头那块浮层**压在副图上沿**而不是排在它上面 —— 它盖住的那一条里不许有数据。
// 量过（2026-10-04，真后台，ZECUSDT 15m，可见窗口收到 120 根）：那一格的比例尺上下各留 8%
// ⇒ 窗格里最极端的那个点正好画在 y=13.4（168px 的 8%），而页头的下沿在 y=26 ⇒ **最高那根柱子的
// 柱尖上面 12.6px 是画了、被它画掉的**（把页头 display:none 再拍一张，柱尖就露出来了）。挑窗有讲究：
// 副图那格的轴是 hist/dif/dea **一起**撑的，多数窗口里 DIF 比柱子大、柱子够不到顶（首屏就是这样，
// 所以一直没人看见）；要 max|hist| ≥ max(|dif|,|dea|) 的那种窗口（柱子自己撑轴）才咬得着。
// 修法：把那一格的右轴**上边留白按页头实测的高度让出来** —— 数据一个像素都不进那条带子。
// 页头的高度是**量出来的**（手机上这句会换行，两行就更高），所以跟 placeSubhead 一起每次布局重算；
// 值没变就别再 applyOptions（那会重画一整格）。★ 建／拆窗格时要把记的值抹掉（见 buildSub/teardownSub）：
// 新窗格的比例尺是新的，记着旧值就会「只有第一次生效」。
let subTopMargin = null;
// placeSubhead「等版面」那一小段的起点：进了「格高还是 0」这个状态就记一下，好给它 500ms 的额度（见 placeSubhead）
let subPlaceFrom = 0;
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

// ---------------------------------------------------------------- 入门防守（T13，均线.md 六.7；后台 /api/wolf）
// 作者给入门者的傻瓜化规则（第 103 课）：黄白线在 0 轴下面的不参与。**不是判据** —— 图上只铺一条格底窄带
// （画法见 layers.js makeWolfPrimitive），任何一层都不读它。
// 周期由用户选（下拉），默认「跟图」＝ 这张图的周期；后台按时间回区间，前端按时间落到这张图上。
// 跟 MACD 副图同一套取数口径：懒取、按「品种|周期|档位」认格、换格作废在飞的那一份、取不到就说取不到。
const wolf = { on: false, below: null, label: '', note: '', err: '', slot: null, reqId: 0, fromT: null,
  // 「只算到 X 之后」里那个 X 按**图上的坐标**念（UTC，跟时间轴、光标读数同一句话，见 timeLabel）
  fmt: (ms) => timeLabel(ms / 1000) };
state.wolf = wolf;
let wolfTf = SUB_Q.get('wolftf') || '';          // '' ＝ 跟图
const WOLF_NAME = '防狼术';
async function loadWolf(symbol, tf, span) {
  const r = await fetch(`/api/wolf?${new URLSearchParams({ symbol, tf, span: String(span) })}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return await r.json();
}
function wolfLabel(tf) { return `${WOLF_NAME}（入门过滤，不是判据）· 周期 ${tf}`; }
function syncWolf() {
  wolf.on = !!opts.wolf;
  // T13＋T16 合起来时手机上的让位（Iris 09:44）：防狼术开着 ⇒ 格底窄带＋左下角那一两行字占住图底；
  //   峰值那行浮条（窄屏的 #mnote）靠这个类往上挪，让开它们。宽屏 #mnote 在右栏，不受影响。
  el('chart').classList.toggle('wolf-on', wolf.on);
  const sel = el('wolftf');
  if (sel) sel.hidden = !opts.wolf;
  if (!opts.wolf) {                                 // 关着不付：清掉、不请求
    wolf.below = null; wolf.slot = null; wolf.err = ''; wolf.fromT = null; wolf.reqId++;
    repaint();
    return;
  }
  if (!state.data) return;
  const symbol = el('symbol').value, tf = wolfTf || el('tf').value;
  const want = `${symbol}|${tf}|${paging.span}`;
  if (wolf.slot === want) return;
  wolf.slot = want; wolf.below = null; wolf.err = ''; wolf.fromT = null; wolf.label = wolfLabel(tf);
  repaint();
  const id = ++wolf.reqId;
  loadWolf(symbol, tf, paging.span).then((m) => {
    if (id !== wolf.reqId || !opts.wolf) return;
    wolf.below = Array.isArray(m.below) ? m.below : [];
    // 后台算到的第一根（Bram eb89f5b）：周期比图细时 span 会被钳，更早那截是**没算**，不是「不在下面」。
    // 画法那边拿它把没算那截单独画出来，并在那句字后面补「只算到 X 之后」（随图往左补数据自动变，不在这儿算死）。
    wolf.fromT = typeof m.from_t === 'number' ? m.from_t : null;
    wolf.note = typeof m.note === 'string' ? m.note : '';
    const chip = document.querySelector('.chip[data-key="wolf"]');
    if (chip) chip.title = wolf.note ? `${wolfLabel(tf)} ｜ ${wolf.note}` : wolfLabel(tf);
    repaint();
  }).catch((e) => {
    if (id !== wolf.reqId || !opts.wolf) return;
    wolf.err = String((e && e.message) || e);
    wolf.below = []; wolf.label = `${WOLF_NAME}：取不到（${wolf.err}）`;
    const chip = document.querySelector('.chip[data-key="wolf"]');
    if (chip) chip.title = wolf.label;
    repaint();
  });
}

// ---------------------------------------------------------------- 开关
function applyToggles() {
  penSolid.applyOptions({ visible: opts.pen });
  penDash.applyOptions({ visible: opts.pen });
  segSolid.applyOptions({ visible: opts.seg });
  segDash.applyOptions({ visible: opts.seg });
  segStdLast.applyOptions({ visible: opts.seg });
  // 成交量：开关说着开、数据里也确实有 v —— 两条都成立才画（样本没有 v ⇒ 开着也画不出来，
  // 那就把开关按灰并说出来，别让用户点了没反应还不知道为什么）。
  volSeries.applyOptions({ visible: !!opts.vol && sub.hasVol });
  repaint();
  renderLegend();
  renderLevelsHead();        // 那一行话（起点／覆盖率）的可见性跟着这一层的开关走，见那一节
  // ★ 只扫**图层那排**（带 data-key 的）。底下「背驰看法」那一组也长着 .chip 的皮（同一个药丸尺寸），
  //   但它是**单选**（aria-checked，归 renderMeasures 管），没有 data-key ——
  //   扫进来就会对着 undefined 取 .startsWith，整张图连带图脚一起炸（2026-10-04 真撞过）。
  for (const b of document.querySelectorAll('.chip[data-key]')) {
    const k = b.dataset.key;
    // ★★ 「亮不亮」＝"**这一层画不画**"，不是那颗开关的裸标志 —— 这两件事在"载荷里没这一层"时会分家，
    //    分家的样子就是 `pressed=true` **且** `disabled=true`：它说"开着"，可屏上什么都没画、又点不动。
    //    ★ 用这个文件自己的话：**三种状态里只有这一种骗人**。
    //    · `lv`（Nova 2026-10-06 19:2xZ 拍，card-6e338490-f11）：亮 ⟺ `shownOf(opts).lv`（＝ `opts.lv && opts.up`），
    //      跟 ⑥ 给框写字、跟 `renderLevelsHead` **同一个谓词** —— 「一处判据」那条账的又一站。
    //    · `trend`（card-961dcef6-d1c，2026-10-07）：`CUT_HIDDEN` 里那个 `extend` 深链**照旧进得去**
    //      （实测：参数不被归一、后台照发那一档），而那一档载荷**没有 `trend` 键**；`opts.trend` 又默认开
    //      ⇒ 从前也是"亮着但按灰"。**跟 `lv` 同一个形状、同一条账，此前只修了 `lv` 那一半。**
    //      现在：亮 ⟺ `opts.trend && hasTrend`。
    //   ★ 这一族**首屏看不出来**：`trendNum` 长在「走势分段」上、默认关 ⇒ 首屏"裸标志"和"画不画"都是关，
    //     两套判据不显形；要露头得**换一档**（`lv` 靠「高一级」默认开，`trend` 靠 `?cut=extend`）。
    //     ⇒ 量这个形状的东西，**缺省那一趟是量不到的**。
    //   ★ 注意 `on` 跟下面那个 `disabled` 判的是**两个不同的问题**，别合并：
    //     亮不亮＝"这一层画没画"；能不能点＝"这颗芯片此刻有没有用"（`opts.trend` / `opts.up`）。
    //     前者管"说的是不是真的"，后者管"按了会不会白按"。
    //     ★ 这两半现在共用下面那个 `hasTrend` —— 这**不是**把两条判据合成一条：`hasTrend` 是一个**事实**
    //       （载荷里有没有这一层），两处各自拿它去回答自己的问题（"有没有用"←`opts`；"画没画"←`opts && 事实`）。
    const hasTrend = !!(state.data && state.data.trend);
    // 买卖点那 7 颗子芯片（6 类＋待确认）：亮＝「买卖点」总开关开着 **并且** 这一类勾着（card-963457e4-e31，Nova 10-09 12:08 定）。
    //   第一版只看子项自己的勾 ⇒ 总开关关着（缺省）时 6 颗亮着又按灰、图上一个点都没有 —— 跟 trend／lv 修过的是同一种骗人。
    //   子项的勾（`opts.sigKinds`／`opts.sigPend`）一个字不动：总开关一开，用户原来勾的原样回来。
    const on = k === 'sigPend' ? opts.sig && opts.sigPend : k.startsWith('sig:') ? opts.sig && opts.sigKinds[k.slice(4)]
      : k === 'lv' ? shownOf(opts, state.data).lv
        : k === 'trend' ? opts.trend && hasTrend
          : opts[k];
    // 同级别正式版：「高一级」**藏起来**（这一套口径里根本没有这一层）。「级别对照」**不藏、按灰、悬停写原因**（Nova 10-09 13:14 选 ①）：
    //   级别联动第 3 项在同级别下不适用（spec §四），藏起来等于把「不适用」也藏了；按灰＋说明为什么，跟「按灰＝此刻用不了」同一条规矩。
    //   判据跟画图同一个 `shownOf`：它那边 `up`／`lv` 已经与上了 `!sameLevel`。
    const sameLevel = !!(state.data && state.data.trend_reading === 'same_level');
    if (k === 'up') b.hidden = sameLevel;
    b.setAttribute('aria-pressed', (k === 'up' ? on && !sameLevel : on) ? 'true' : 'false');
    const sigChip = k.startsWith('sig:') || k === 'sigPend';
    // 成交量那颗在**没有 v 的数据上**按灰（仓里的样本就是）：能点却画不出东西的开关是骗人的。
    // 走势分段那颗同理：`cut=extend` 那份载荷没有 `trend` 这个键 ⇒ 开着也画不出东西 ⇒ 按灰。
    b.disabled = sigChip ? !opts.sig : k === 'vol' ? !sub.hasVol
      : k === 'trend' ? !hasTrend
        // 框编号画在走势那一层**里面**（字母说的是"这一段里的第几个中枢"）⇒ 那一层关着时它按灰：
        // 能点却画不出东西的开关是骗人的（跟上面那条同一条账，不是新规矩）。
        : k === 'trendNum' ? !hasTrend || !opts.trend
          // 级别对照标的字挂在**合成框**上（`shownOf` 里 `lv` 跟 `up` 与着）⇒「高一级」关着时它按灰。
          // ★ 按灰判的是**"这颗此刻有没有用"**（`!opts.up`），跟上面那个 `on` 判的**"这一层画没画"**
          //   （`shownOf(opts).lv`）是**两个问题、两条判据** —— 别合并。两个都从 `opts.up` 这同一个根上长出来：
          //   拿 `shownOf(opts).lv` 来判"有没有用"会绕远（那个式子里的 `opts.lv` 跟"能不能用"无关）。
          : k === 'lv' ? !opts.up || sameLevel : false;
    if (k === 'lv') {
      if (sameLevel) b.title = LV_NA;
      else b.removeAttribute('title');
    }
  }
  // 成交量那颗：亮＝开着**并且**这份数据真有成交量（`sub.hasVol`，跟 volSeries 的 visible 同一个式子）。缺了这半，
  //   首屏那一秒多（副图数据还没到）它是「亮着又按灰」—— 跟 trend、买卖点子芯片同一种骗人（card-8aa5c9de-0c2，Nova 13:34 看出来的）。
  //   ★ 写在循环外面单独一句，不塞进上面 `on` 那串三元：那几行同级别那支也在改，挨着改就冲突。
  const volChip = document.querySelector('.chip[data-key="vol"]');
  if (volChip && !sub.hasVol) volChip.setAttribute('aria-pressed', 'false');
  // 「关着的层不许有能点的开关」这条账，看法那组也算：买卖点一关，它就得跟着灰（或反过来亮回来）。
  renderMeasures();
  // 切法那组同理：中枢两层都关着时它得跟灰（判据在 renderCuts 一处，别在这儿再写一遍）。
  renderCuts();
  renderPens();
}

// 「级别对照」在同级别下按灰时的悬停说明（spec 级别联动.md §四 第 3 项；Atlas 14d231b）
const LV_NA = '同级别下不适用：本级不合成框；L38:35「该级别以上级别，根本不考虑」';

function buildChips() {
  const box = el('panel');
  const add = (label, key, dot) => {
    const b = document.createElement('button');
    b.className = 'chip'; b.type = 'button'; b.dataset.key = key;
    // 色块的颜色走 CSS 变量 `--c`（不是直接写 background）：关着画**空心框**、开着才**填实**，两种都得拿到这个色（style.css `.chip i`）
    b.innerHTML = (dot ? `<i style="--c:${dot}"></i>` : '') + label;
    b.onclick = () => {
      if (key.startsWith('sig:')) opts.sigKinds[key.slice(4)] = !opts.sigKinds[key.slice(4)];
      else opts[key] = !opts[key];
      // 副图那两颗关掉再打开 ⇒ **重新要一份**：关着的那段时间数据可能已经旧了/后台换过了。
      // （不这样，`sub.slot` 还是老值 ⇒ syncSub 认为"这一格处理过了"，窗格会空着不取数。）
      if (key === 'macd' && opts.macd) { sub.slot = null; sub.err = ''; }
      applyToggles();
      if (key === 'vol' || key === 'macd') syncSubView();
      if (key === 'wolf') { wolf.slot = null; syncWolf(); setUrl(); }
    };
    box.appendChild(b);
  };
  add('笔', 'pen', CHART.pen);
  add('线段', 'seg', CHART.seg);
  add('类中枢', 'pc', CHART.pen);
  add('线段中枢', 'sc', CHART.seg);
  add('高一级', 'up', CHART.up_seg);
  // 级别对照（卡 card-01961644-68f，接口规则 L-9）：**紧挨着「高一级」放** —— 它标的就是那一层
  // 合成出来的框（跟对照图的 `ref_tf` 中枢对不上的那些，在框右沿标一句）。跟「框编号紧挨走势分段」
  // 是同一条理由：标的是哪一层的字，就住在哪一层的芯片旁边。**默认开**，但**亮不亮跟着 `up` 走**：
  // `up` 关着时它不亮、也按灰（亮 ⟺ 画，见 `applyToggles` 里 `on` 那一段账）。
  add('级别对照', 'lv', TREND.lv);
  // 走势分段那一层（v3 §八，卡 card-c73ab37d-5a1）：背景带／分界／中阴／待定／撤回／升级框。
  // 排在「高一级」后面 —— 它俩都跟"升级"沾边，挨着放；但**不是一个东西**（那颗是第 33 课"满 9 段"
  // 升出来的框，这一层是 v3 的 D3"连续扩展合成"），标题里说清楚。
  add('走势分段', 'trend', TREND.up);
  // 框编号那一层（v3 §八 6，卡 card-c6644f52-2fa）：**紧挨着「走势分段」放** —— 它俩是同一件事的
  // 粗读和细读（那一层说"走势怎么切的"，这一颗说"每段里那几个中枢排第几"）。**默认关**。
  // 点色借 `TREND.edge`（结构墨色）：字母本身按段的方向上绿／红／灰，拿哪一个当点色都是半句谎。
  add('框编号', 'trendNum', TREND.edge);
  add('买卖点', 'sig', CHART.buy);
  for (const k of ['一买', '二买', '三买', '一卖', '二卖', '三卖']) add(k, `sig:${k}`, k.endsWith('买') ? CHART.buy : CHART.sell);
  add('待确认', 'sigPend', CHART.sell);
  // 副图那两颗（卡 card-68704ee6-a5a）**排在最末尾**：上面那几颗管的是「主图上画什么」，
  // 这两颗管的是**另外两格**（主图下沿那条成交量、下面那一格 MACD）—— 中间隔着一个"买卖点"组，
  // 正好把"叠层"和"另起一格"分开，眼睛一扫就知道它们不是一类。
  // 点取 theme.js 的 SUB：成交量用 K 线那一对涨跌色（取阳色），MACD 取黄白线里的黄（原文的叫法）。
  add('成交量', 'vol', CANDLE.up);
  add('MACD', 'macd', SUB.dea);
  // 入门防守（T13）：**排在 MACD 后面**（它就是拿 MACD 的黄白线判的），点色取 MACD 负柱那个色（跟图上那条带同色）。
  add(WOLF_NAME, 'wolf', SUB.dn);
  {
    const b = box.querySelector('.chip[data-key="wolf"]');
    b.title = `${WOLF_NAME}：黄白线两条都在 0 轴下的区间，图底铺一条窄带（第 103 课的入门过滤，不是判据）`;
    // 周期下拉：开着才露出来。「跟图」＝ 这张图的周期。
    const sel = document.createElement('select');
    sel.id = 'wolftf'; sel.className = 'wolftf'; sel.hidden = !opts.wolf;
    sel.setAttribute('aria-label', `${WOLF_NAME}看哪个周期的 MACD`);
    for (const [v, t] of [['', '跟图'], ...TFS.map((x) => [x, x])]) {
      const o = document.createElement('option'); o.value = v; o.textContent = t; sel.appendChild(o);
    }
    sel.value = TFS.includes(wolfTf) ? wolfTf : '';
    wolfTf = sel.value;
    sel.onchange = () => { wolfTf = sel.value; wolf.slot = null; syncWolf(); setUrl(); };
    b.after(sel);
  }
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

// ---------------------------------------------------------------- 全屏看图（卡 card-5014b0cb-e4d）
// 进全屏的是 **`main`**（`#chart` ＋ 右边那一栏开关），**不是** `#chart` —— 小栋要的是「图跟开关栏一起
// 撑满」，不是「把开关栏挡掉」。这一条定下之后，卡里 ② 就是白送的：`#panel` 还是 `main` 的孩子，
// 全屏里各颗开关照点。
//
// ★ 卡里 ⑤（进出全屏自动重画）**也是白送的**：建图时就是 `autoSize: true`（见上面 createChart），
//   LWC 自己挂着 ResizeObserver，`#chart` 一变尺寸它自己重排。这儿**不另写一套重画** ——
//   两套重画迟早会在某一刻各画一半。⇒ 剩下的活只有三件：按钮摆哪、进出怎么走、退路。
//
// ★★ 进出全屏**唯一要自己管的是视口**：尺寸一变，LWC 按新的宽度重排可视窗（同一段 K 线往边上挪）。
//   所以进/出各做一次「先记下这一屏 → 等它重排完 → 摆回去」，走的就是页面自己那套 setView/holdView
//   ——它认得「这是我们自己摆的」，不会把这一下当成用户在往左拖、跑去要更早的数据（那笔账见上面
//   holdView 那一大段：认的是**输入设备**，脚本摆视口不算）。
const fsMain = document.querySelector('main');
const fsBtn = el('fs');
const fsNative = () => !!(document.fullscreenElement || document.webkitFullscreenElement);
const fsFake = () => document.body.classList.contains('fs-fake');
const fsOn = () => fsNative() || fsFake();

// 按钮的 right 让开**右轴那一条**：轴宽是图自己算的（随价位位数变），所以**问图要**，不抄一个数。
// 这就是卡里 ①「别挡轴和最新价标签」那条约束在代码里的**唯一出处**；验收那一格量的也是它。
function placeFs() {
  const pane = chart.panes()[0];
  const ps = pane && pane.priceScale('right');
  const w = ps && typeof ps.width === 'function' ? ps.width() : 0;
  if (w > 0) cssVar('--ps-right', `${Math.ceil(w)}px`);
}
// 进/出全屏：把「刚才那一屏」记下来，等 LWC 按新尺寸排完，摆回去。两次 rAF 是**让 LWC 先重排**——
// 它的重排挂在 ResizeObserver 上，同一拍里读回来的还是旧尺寸。
// ★ 「刚才那一屏」＝**屏上正在显示的范围**，不是 viewSet（card-c90f0f08-3ac）。viewSet 只记**我们自己摆的**
//   那一下（拿来认回声，见 setView／sameRange），用户用手势拖过之后它不跟着更新 ⇒ 拿它当基准，拖完一进全屏
//   就跳回最初那一屏。viewSet 本身**不动**：手势也去写它，会把下一次真的拖动当成回声吞掉（Atlas 10-07）。
//   屏上读不到（图还没建好）才退回 viewSet。
function keepView(r) {
  const want = r || chart.timeScale().getVisibleLogicalRange() || viewSet;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    if (want) setView(want);
    placeFs();
    placeSubhead();
  }));
}
// ★ `#fs` 不在就当没这回事（浏览器缓存着旧 index.html、或谁把它删了）：**不许让整支 js 挂在这里** ——
//   这颗按钮没了只是少个功能，一个 null 上去抛出去，整页就只剩白板跟顶栏（比没按钮坏得多）。
function syncFs() {
  const on = fsOn();
  document.body.classList.toggle('fs-on', on);          // 只用来换那两副箭头（CSS 认这个类）
  if (!fsBtn) return;
  fsBtn.setAttribute('aria-pressed', String(on));
  fsBtn.setAttribute('aria-label', on ? '退出全屏' : '全屏看图');
  fsBtn.title = on ? '退出全屏（Esc）' : '全屏看图（Esc 退出）';
}
async function toggleFs() {
  const r = chart.timeScale().getVisibleLogicalRange() || viewSet;   // 进/出都摆回屏上这一屏（见 keepView 上面那段）
  if (fsOn()) {
    if (fsNative()) {
      try { await document.exitFullscreen(); } catch (e) { /* 已经退了：下面 syncFs 会认掉 */ }
    } else {
      document.body.classList.remove('fs-fake');
    }
    syncFs(); keepView(r);
    return;
  }
  // 原生那条路走不通就别硬走：`fullscreenEnabled` 为假（iPhone Safari 对非 video 元素就是）**或者**
  // requestFullscreen 当场被拒（没有用户手势/被策略拦），都落到自铺那一档。
  let ok = false;
  try {
    if (fsMain && fsMain.requestFullscreen && document.fullscreenEnabled) {
      await fsMain.requestFullscreen();
      ok = true;
    }
  } catch (e) { ok = false; }
  if (!ok) document.body.classList.add('fs-fake');
  syncFs(); keepView(r);
}
if (fsBtn) fsBtn.addEventListener('click', toggleFs);
// 原生那条路**退出是全浏览器包办的**（Esc、手势、系统返回都可能触发）⇒ 状态跟着 `fullscreenchange` 走，
// 不自己记一个布尔（自己记：迟早出现「按钮说在全屏、其实已经退了」）。
for (const ev of ['fullscreenchange', 'webkitfullscreenchange']) {
  document.addEventListener(ev, () => { syncFs(); keepView(); });
}
// 退路那一档：Esc 得**自己听**（原生那条路浏览器包办）。
addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && fsFake()) {
    document.body.classList.remove('fs-fake');
    syncFs();
    keepView();
  }
});
// 轴宽不是固定的：价位位数变、换档、转屏、窗格增减都会变 ⇒ 每次布局重量一次（跟 placeSubhead 同一个触发点）。
if ('ResizeObserver' in window) new ResizeObserver(() => placeFs()).observe(el('chart'));
addEventListener('resize', placeFs);
placeFs();

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
  // ★ T16（背驰.md 六.3）：`measure_note = {看法: 一句话}` —— 量是原文、单用超出原文的那几种另挂一句说明，
  //   **不是**「非原文」那枚标（那是 orig:false 的事）。读不到或不是字符串就不挂，同上一条规矩。
  const ns = (m && typeof m.measure_note === 'object' && m.measure_note) || {};
  const note = {};
  for (const id of list) if (typeof ns[id] === 'string' && ns[id]) note[id] = ns[id];
  return { list, orig, note };
}

// 一次 `/api/meta` 拿两张名单（看法、切法）—— 不是图省一次请求，是**只有一份「名单到没到」**：
// 分两次请求就有两个 ready 门，首屏那个 `?measure=`/`?cut=` 的等待、失败回退、离线样本那三条路
// 都得各写一遍，迟早一处漏掉（漏掉的那次就是带着白名单外的词发请求 ⇒ 400 ⇒ 整张图挂掉）。
// ★ 两张名单**各判各的**：看法只有一种（不画那一组）不等于切法也只有一种，两件事别互相带着 return。
async function loadMeasures() {
  try {
    const r = await fetch('/api/meta');
    if (!r.ok) return;
    const m = await r.json();
    const { list, orig, note } = readMeasures(m);
    if (list.length >= 2) {              // 只有一种看法＝没什么可切的；不画一个只有一个选项的开关
      measures.list = list;
      measures.orig = orig;
      measures.note = note;
      // 地址栏点名的那个后台认不认：名单外的一律退回缺省（缺省不在名单里才拿第一个）
      const want = new URLSearchParams(location.search).get('measure');
      if (want && !list.includes(want)) paging.measure = list.includes(DEFAULT_MEASURE) ? DEFAULT_MEASURE : list[0];
      buildMeasures();
    }
    // 名单叫 `cut_modes`（Bram 10-05）：不叫 `cuts` —— 那个名字是**图表载荷**顶层那份切点清单的，
    // 两个接口里同名不同物，混起来就是把一张表的字段名当另一张表的用。
    const cl = Array.isArray(m.cut_modes) ? m.cut_modes.filter((x) => typeof x === 'string' && x) : [];
    // ★ 两个名单，别混：`cl` 是**后台真认的那几档**（地址栏那一头、深链归一那一条要看它 ——
    //   `?cut=extend` 能不能留、该不该归一，问的是后台认不认，不是我们摆了几颗 chip）；
    //   `shown` 才是**摆给用户的那几档**（滤掉 `CUT_HIDDEN`，见 DEFAULT_CUT 上面那段）。
    const shown = cl.filter((x) => !CUT_HIDDEN.includes(x));
    if (cl.length >= 2) {
      cuts.list = shown;
      const want = new URLSearchParams(location.search).get('cut');
      if (want && !cl.includes(want)) paging.cut = cl.includes(DEFAULT_CUT) ? DEFAULT_CUT : cl[0];
      if (shown.length >= 2) buildCuts();    // 只剩一档＝没什么可切的：不画这一组、也不发这个参数
    }
    // 笔的根数（C3）：两个字段**都**得在、都得是整数，才画这一组。缺省不在名单里 ⇒ 当没这回事（不编）。
    //   ★ 名单是混型 [6, 7, "new"]：过 `penOf`，整数和 'new' 都收（原来 `filter(Number.isInteger)` 会把 new 静默滤掉）
    const po = Array.isArray(m.pen_min_options) ? m.pen_min_options.map(penOf).filter((x) => x !== null) : [];
    const pd = penOf(m.pen_min_default);
    if (po.length >= 2 && pd != null && po.includes(pd)) {
      pens.list = po; pens.def = pd;
      if (paging.pen == null || !po.includes(paging.pen)) paging.pen = pd;   // 没点名／点了名单外的 ⇒ 缺省
      buildPens();
    }
  } catch (e) { /* 没后台（离线样本）或没这个接口：没有看法/切法可切，页面上不多一个字 */ }
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
    if (measures.note[id]) {                                              // T16：悬停多一句「单用超出原文」
      b.title = `${b.title} ｜ ${measures.note[id]}`;
      b.setAttribute('aria-description', measures.note[id]);              // 读屏器不一定念 title（Iris 09:18）
    }
    b.setAttribute('role', 'radio');
    b.onclick = () => setMeasure(id);
    g.appendChild(b);
  }
  box.prepend(g);
  // T16（Nova 09:18 定）：触屏没有 hover ⇒ **选中**带说明的那种看法时，出一行小字。
  //   ★ 位置（Iris 09:36 真机量过）：放成 main 的流内子元素会在 grid 里多出一行 ⇒ 图被压矮 41～68px、手机上还盖住 #fold。
  //   ⇒ **同一个元素、两处落脚**（placeMnote）：宽屏放进看法那一组当最后一项（右栏里自己折行，不碰图）；
  //     窄屏那一组是横滑单行、放不下 ⇒ 挪进 #chart 浮在图上（.more 那套写法），不占流、不压图。
  if (!el('mnote')) {
    const n = document.createElement('div');
    n.id = 'mnote'; n.className = 'mnote'; n.hidden = true;
    n.setAttribute('aria-live', 'polite');
    g.appendChild(n);
  }
  placeMnote();
  watchOverflow(box);                  // 手机上多了一排，右边还有没有东西要重算一遍
  renderMeasures();
}

// 亮哪一颗**看回显**（paging.measure 是 adopt() 从响应里认来的），不看用户刚点的那一颗。
// ★ 买卖点那层关着 ⇒ 这一组**置灰不可点**：这四颗只换买卖点的画法，层关着的时候换看法，
//   屏幕上**什么都不会变** —— 点了没反应会被当成坏了（判据只有 opts.sig 一处，跟别的开关同一条账）。
//   ★ 手机上没有 hover，所以「为什么是灰的」不能只写在 title 里，标题那行也得说。
// T16：#mnote 宽屏在看法那一组里、窄屏浮在 #chart 上。断点跟 style.css 的 @media (max-width: 760px) 同一个。
const MNOTE_MQ = window.matchMedia('(max-width: 760px)');
function placeMnote() {
  const n = el('mnote'); if (!n) return;
  const host = MNOTE_MQ.matches ? el('chart') : el('mgroup');
  if (host && n.parentNode !== host) host.appendChild(n);
}
MNOTE_MQ.addEventListener('change', placeMnote);

function renderMeasures() {
  const g = el('mgroup'); if (!g) return;
  const on = !!opts.sig;
  for (const b of g.querySelectorAll('.mchip')) {
    b.setAttribute('aria-checked', b.dataset.measure === paging.measure ? 'true' : 'false');
    b.disabled = !on;
  }
  const cap = g.querySelector('.mcap');
  if (cap) cap.textContent = on ? '背驰看法' : '背驰看法 · 买卖点那层关着';
  const mn = el('mnote');                // T16：选中的看法有说明（现在只有峰值）就印出来，没有就收起
  if (mn) {
    const t = measures.note[paging.measure] || '';
    mn.textContent = t;                  // 不加「峰值：」前缀：说明本身就以「单用超出原文」开头（Nova 09:24）
    mn.hidden = !t;
  }
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
    renderCuts();                      // 切法这一趟也带着走（load 的缺省就是 paging.cut）⇒ chip 跟回显对齐
    renderPens();
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

// ---------------------------------------------------------------- 中枢切法那一组（卡 card-e346ede6-996）
// 形态跟「背驰看法」同一套（单选：`role=radiogroup` ＋ `aria-checked`），但**另起一组**、不并进那一排 ——
// 那一组换的是「买卖点按哪种力度比较算」，这一组换的是「中枢切在哪」，两件事各归各的；并成一排会让人
// 以为能同时选。★ 名字也是 Nova 10-05 拍的：两颗「延伸」「走势分段」。后台哪天加了第三种 ⇒ 原样印
// 代号、title 里说明白，**不吞**（跟 MEASURE_NAME 同一条规矩）。
// ★ 措辞表 CUT_NAME 在下面 RENDER_META 那一块里（图脚也用它，一处一份），见那块开头的注释。
function buildCuts() {
  const box = el('panel');
  const g = document.createElement('div');
  g.className = 'mgroup'; g.id = 'cgroup';
  g.setAttribute('role', 'radiogroup'); g.setAttribute('aria-label', '中枢切法');
  const cap = document.createElement('span');
  cap.className = 'mcap'; cap.textContent = '中枢切法';
  g.appendChild(cap);
  for (const id of cuts.list) {
    const [short, long] = CUT_NAME[id] || [id, `${id}（后台新加的切法，前端还没有中文名）`];
    const b = document.createElement('button');
    b.className = 'chip mchip'; b.type = 'button'; b.dataset.cut = id;
    b.textContent = short; b.title = long;
    b.setAttribute('role', 'radio');
    b.onclick = () => setCut(id);
    g.appendChild(b);
  }
  const mg = el('mgroup');
  if (mg) box.insertBefore(g, mg.nextSibling);   // 挨着「背驰看法」：两组都在图层那排**前面**
  else box.prepend(g);
  watchOverflow(box);                  // 又多了一排，手机上右边还有没有东西要重算
  renderCuts();
}

// 亮哪一颗**看回显**（paging.cut 是 adopt() 从响应里认来的），不看用户刚点的那一颗 —— 跟看法同一格。
// ★ 中枢那两层都关着 ⇒ 置灰不可点：这一组只换中枢画在哪，层关着的时候点它，屏幕上**什么都不会变**，
//   点了没反应会被当成坏了（判据只有 opts 一处，跟别的开关同一条账）。手机上没有 hover，所以
//   「为什么是灰的」也写进标题那一行。
function renderCuts() {
  const g = el('cgroup'); if (!g) return;
  const on = !!opts.pc || !!opts.sc;
  for (const b of g.querySelectorAll('.mchip')) {
    b.setAttribute('aria-checked', b.dataset.cut === paging.cut ? 'true' : 'false');
    b.disabled = !on;
  }
  const cap = g.querySelector('.mcap');
  if (cap) cap.textContent = on ? '中枢切法' : '中枢切法 · 中枢那两层都关着';
  if (on) g.removeAttribute('title');
  else g.title = '类中枢和线段中枢那两层都关着 —— 这一组只换中枢切在哪，先打开一层';
}

async function setCut(id) {
  if (!cuts.list.includes(id) || id === paging.cut || paging.loading) return;
  const own = state.data;
  const id0 = ++paging.reqId;          // 跟首屏／换看法共用同一个号：谁后发谁算数
  paging.loading = true;
  el('state').textContent = '换切法…'; el('state').className = 'badge';
  try {
    // 锚点跟换看法一样按**时间**抓：切开之后后面整段都要重画（小栋 10-05 那条要求），框会大改；
    // 但 **K 线一根不多不少**，按时间对回去视口就不动 —— 用户看到的是"同一段行情换了个切法"，
    // 而不是图跳了一下。真变了也不跳：这一手本来就是按时间放回去的，不押在"一定不变"上。
    const anchor = own ? anchorOf(own.bars, chart.timeScale().getVisibleLogicalRange()) : null;
    const d = await load(el('symbol').value, el('tf').value, paging.span, paging.measure, id);
    if (id0 !== paging.reqId) return;
    Object.assign(paging, adopt(paging, d));
    setUrl();
    if (anchor) draw(d, anchor); else draw(d);
    renderCuts();
    el('state').textContent = d.closed ? '已收盘' : '未收盘（最后一根还在走）';
    el('state').className = 'badge ' + (d.closed ? '' : 'live');
  } catch (e) {
    if (id0 !== paging.reqId) return;
    el('state').textContent = String(e.message || e); el('state').className = 'badge bad';
    renderCuts();                      // 没换成 ⇒ 亮回原来那一颗
  } finally {
    if (id0 === paging.reqId) paging.loading = false;
  }
}

// ---------------------------------------------------------------- 笔最少几根那一组（C3，卡 card-2e6bb3bd-4ae）
// 形态跟「中枢切法」同一套（单选 radiogroup ＋ aria-checked），另起一组：它换的是**笔怎么划**，往上线段、
// 中枢、走势、买卖点整段跟着重算 —— 跟切法、看法都不是一件事，并进去会让人以为能同时选。
// ★ 「（默认）」两个字跟着 `pens.def` 走，不写死在 6 或 7 上（第二步才把缺省翻过去）。
const PEN_TITLE = {
  6: '笔最少 6 根 K 线：顶分型和底分型之间可以没有独立 K 线（第 106 课「至少延伸6个基本K线单位」）',
  7: '笔最少 7 根 K 线：顶和底之间至少隔一根独立 K 线（第 62、77 课；第 62 课说只差这一根的「一般来说，也最好不算一笔」）',
  // 新笔（B-10＝C）。定义在镜像第 81 课**后附的帖子**里（Atlas b548e21 更正：不是第 81 课正文）；
  //   「用意」那半句是同一文件里 2007-09-19 的**答疑**，L81:129 原文逐字：「那主要是为了不同软件间可以减少不同」（Iris 核过）。
  new: '新笔：包含处理后顶、底分型不共用 K 线，且顶分型最高那根和底分型最低那根之间的原始 K 线至少 3 根；不按「最少几根」算（第 81 课后附帖子）。作者说用意是「那主要是为了不同软件间可以减少不同」（答疑，L81:129）',
};
function buildPens() {
  const box = el('panel');
  const g = document.createElement('div');
  g.className = 'mgroup'; g.id = 'pgroup';
  // 名单里有新笔 ⇒ 这一组就不只是「最少几根」了，组名改「笔」、老笔两颗带上「老笔」二字（新笔不读最少几根，三选一，
  //   不另起一组：分两组会让人以为能选「新笔＋7 根」，Bram 06:34 核过 far() 不读 min_gap）。没有新笔 ⇒ 跟原来一个字不差。
  const hasNew = pens.list.includes('new');
  const capText = hasNew ? '笔' : '笔最少几根 K 线';
  g.setAttribute('role', 'radiogroup'); g.setAttribute('aria-label', capText);
  const cap = document.createElement('span');
  cap.className = 'mcap'; cap.textContent = capText;
  g.appendChild(cap);
  for (const n of pens.list) {
    const b = document.createElement('button');
    b.className = 'chip mchip'; b.type = 'button'; b.dataset.pen = String(n);
    b.textContent = n === 'new' ? '新笔' : hasNew ? `老笔 ${n} 根` : `${n} 根`;
    b.title = (PEN_TITLE[n] || (n === 'new' ? '新笔' : `笔最少 ${n} 根 K 线（后台新加的一档，前端还没有说明）`)) + (n === pens.def ? '（默认）' : '');
    b.setAttribute('role', 'radio');
    b.onclick = () => setPen(n);
    g.appendChild(b);
  }
  const after = el('cgroup') || el('mgroup');
  if (after) box.insertBefore(g, after.nextSibling);   // 挨着前面两组：几组单选都在图层那排**前面**
  else box.prepend(g);
  watchOverflow(box);
  renderPens();
}
// 亮哪一颗看回显（paging.pen 是 adopt() 从响应里认来的）。笔这一层关着也照样能点：
//   它不只换笔，往上线段、中枢、走势全跟着变，屏上看得见差别，所以不置灰。
function renderPens() {
  const g = el('pgroup'); if (!g) return;
  for (const b of g.querySelectorAll('.mchip')) b.setAttribute('aria-checked', b.dataset.pen === String(paging.pen) ? 'true' : 'false');   // 按字符串比（混型名单）
}
async function setPen(n) {
  if (!pens.list.includes(n) || n === paging.pen || paging.loading) return;
  const own = state.data;
  const id0 = ++paging.reqId;
  paging.loading = true;
  el('state').textContent = n === 'new' ? '换成新笔…' : '换笔的根数…'; el('state').className = 'badge';
  try {
    // 锚点按**时间**抓：笔一变，后面全都重画，但 K 线一根不多不少，按时间对回去视口就不动。
    const anchor = own ? anchorOf(own.bars, chart.timeScale().getVisibleLogicalRange()) : null;
    const d = await load(el('symbol').value, el('tf').value, paging.span, paging.measure, paging.cut, n);
    if (id0 !== paging.reqId) return;
    Object.assign(paging, adopt(paging, d));
    setUrl();
    if (anchor) draw(d, anchor); else draw(d);
    renderPens();
    el('state').textContent = d.closed ? '已收盘' : '未收盘（最后一根还在走）';
    el('state').className = 'badge ' + (d.closed ? '' : 'live');
  } catch (e) {
    if (id0 !== paging.reqId) return;
    el('state').textContent = String(e.message || e); el('state').className = 'badge bad';
    renderPens();
  } finally {
    if (id0 === paging.reqId) paging.loading = false;
  }
}

// ---------------------------------------------------------------- 每根 K 线收盘自动重取
// （card-cf3ed018-795，Nova 2026-10-05 定；小栋要的是「当场看得见」）
//
// ★ 为什么非有它不可：「确认后又消失」**只有重新取数才看得见**。在那之前，页面上唯一的定时器是
//   底下那句 `setInterval(… stamp(state.data) …, 30000)` —— 它只刷新角上那行时间标签，**不发请求**
//   （Atlas 10-05 核实过）。也就是说用户开着不动，这个功能几乎永远不会自己触发，等于没有。
//   ⇒ 那一句留着（它是"多久之前"那句话的事），自动重取是**另加**的一条。
//
// 口径（四条，一条都不许省）：
//   ① 当前周期**每收盘一根**取一次。收盘时刻 = 手上这份数据**最后一根的开盘时间 ＋ 一个周期**，
//      再加 10 秒余量等后台把新那根拉进来。
//      ★ 按**最后一根**算，不按钟表算：数据旧了（后台卡住、离线样本、切回来时过了好几根）
//        钟表会去追一个已经过去的时刻，那才是真的空转 —— 按最后一根算，它自己会落到"下一根"。
//   ② **只在标签页可见时取**（切到后台就停）：没人在看的那些取数，白白敲后台，页面也不会因此多知道
//      什么（图在那儿谁也没看）。切回来**立刻补一次** —— 那时候已经过了一根就马上取。
//   ③ 一分钟内最多一次：周期算出来的时刻挨得太近、或者可见性来回切，都不许敲出连发。
//   ④ 走**同一条**取数＋绘制路径（跟 setMeasure 那份对齐）：档位/看法照旧带着、读数压住
//      （dataStale —— 数据在飞的时候屏上还是旧图，读数写着新数就是一句谎）、视口按**时间**放回原位。
//      ★ 少了 ④ 这一条，自动重取就会变成"图自己跳一下"——那比不刷新还烦人。
//   ⑤ **错峰**（Bram 10-05 量的）：收盘那一刻大家都来取，第一个请求才会让后台去币安拉新的那根，
//      而且它这次回的**还是旧**数据（SWR，头里 refreshing=true）。所以收盘后**随机**等 2–10 秒再取
//      （人分散开），并且回来看见 refreshing=true、或者最后一根还不是刚收的那根 ⇒ **这一趟当没跑**，
//      过几秒再补一次（有次数上限），而不是等一个整周期。
const TF_SEC = { '15m': 900, '30m': 1800, '1h': 3600, '2h': 7200, '4h': 14400 };
const AUTO_LAG_MIN = 2000;           // 收盘之后随机等这段时间再取（下界也是「过没过期」那道判据）
const AUTO_LAG_MAX = 10000;          // 上界（后台那一趟拉取不是瞬时的，10 秒够了）
const AUTO_MIN_GAP_MS = 60000;       // 一分钟内最多一次（③）
const AUTO_RETRY_MS = 5000;          // 回来的是旧数据 ⇒ 过几秒再补（②）
const AUTO_RETRY_MAX = 4;            // 补的次数上限：别把后台的一次卡顿敲成连环请求
let autoTimer = 0, autoAt = 0, autoTries = 0;   // autoAt ＝ 上一次**发起**自动取数的时刻

/** 手上这份数据里最后一根**该收盘的时刻**（ms）；算不出来（没数据、周期不认识）返回 null。 */
function autoCloseAt(d) {
  const step = (TF_SEC[d && d.tf] || 0) * 1000;
  const last = d && d.bars && d.bars.length ? d.bars[d.bars.length - 1].t : null;
  return step && last != null ? last + step : null;
}
/** 手上这份**已经过期**了吗：最后一根之后的那一根，按时间早该出来了（切回来补一次用这一条）。 */
function autoDue(d) {
  const at = autoCloseAt(d);
  return at != null && at + AUTO_LAG_MIN <= Date.now();
}
/** 刚取回来的这份**是不是真的换了一份新的**（⑤：SWR 的第一趟回的还是旧的）。
 *  两条判据（Bram 10-05）：①头里 `refreshing` ⇒ 后台还在去币安拿，这一趟不算；
 *  ②最后一根得**走到我们等的那一根**（≥ 上一份的"下一根该开盘"时刻）—— 连新那根都没有，
 *  这一趟就等于什么都没发生，不该为它等一个整周期。 */
function autoFresh(own, d) {
  if (d.refreshing === true) return false;
  const expect = autoCloseAt(own);
  const last = d.bars && d.bars.length ? d.bars[d.bars.length - 1].t : null;
  return expect == null || last == null ? true : last >= expect;
}
/** 排下一次。（每次 paint 都重排一次：数据一换，收盘时刻就该按**新那份**重算。） */
function autoPlan() {
  clearTimeout(autoTimer);
  const step = (TF_SEC[state.data && state.data.tf] || 0) * 1000;
  let at = autoCloseAt(state.data);
  if (at == null) return;
  // ★ 那个时刻**已经过去**了：
  //   · 这一根收盘以后**还没有自动取过一次**（autoAt < at）⇒ 照常错峰 2～10 秒补一趟，不往后推
  //     （card-7d3e8748-3d3，10-08：收盘后才打开的那一页，首屏拿到的就是过期的那份 —— 后台还没把新那根拉回来
  //       （SWR）。原来这里一律推到下一根，那人要等 15 分钟／4 小时才看到新那根）；
  //   · 已经为这一根取过了（切回来过了一根、后台卡着没动）⇒ 往前推到**下一根**再排。
  //     不推的话 `Math.max(1000, 过去 - 现在)` 会变成"每秒来一次"的空转 —— 一次取数都不发
  //     （③ 那道闸拦着），但一秒一个定时器白烧电，而且它掩盖了真正该问的问题：这一根到底取到没有。
  //   防连环请求还是那两道闸：一分钟一次（autoFire 里的 AUTO_MIN_GAP_MS）、补的次数上限（AUTO_RETRY_MAX）。
  if (at + AUTO_LAG_MIN <= Date.now()) {
    // 只认「刚收盘、手上就差最新这一根」（收盘不到一个周期）：旧了几根以上的（冻结的样本、停了的盘）不是这回事，
    //   照旧往后推 —— 否则每开一次页面都白多敲一趟（e2e more ⑨⑪ 用的就是冻结数据，当场多出一个请求，实测红过）。
    if (autoAt < at && Date.now() - at < step) at = Date.now();   // 没为这一根取过 ⇒ 从现在起错峰（下面加 2～10 秒）
    else while (at + AUTO_LAG_MIN <= Date.now()) at += step;
  }
  // ⑤ 错峰：每一根**重新摇一次**（不记住上一根摇的数 —— 记住了大家还是会在同一秒撞上）。
  const lag = AUTO_LAG_MIN + Math.random() * (AUTO_LAG_MAX - AUTO_LAG_MIN);
  // 看不见的时候到点了也**什么都不做**：这一次不是跳过，是留给 visibilitychange 那次补
  // （在后台偷偷取数既不划算也不礼貌）。
  autoTimer = setTimeout(() => { if (document.visibilityState === 'visible') autoFire(); },
                         Math.max(1000, at + lag - Date.now()));
}
/** 定时器到点 / 切回来补一次，都从这儿进（③ 那道闸只在这里判）。 */
function autoFire() {
  if (Date.now() - autoAt < AUTO_MIN_GAP_MS) { autoPlan(); return; }
  autoAt = Date.now();
  autoGo();
}
async function autoGo() {
  const fresh = await autoReload();
  // false ＝ 回的还是旧的（SWR 头一趟）⇒ 几秒后再补，别为它等一个整周期。
  if (fresh === false && autoTries < AUTO_RETRY_MAX) {
    autoTries++;
    clearTimeout(autoTimer);
    autoTimer = setTimeout(() => { if (document.visibilityState === 'visible') autoGo(); }, AUTO_RETRY_MS);
    return;
  }
  autoTries = 0;
  autoPlan();                        // 取到没取到都要排下一次：失败就当这一根没发生，下一根再来
}
/** 同一个桶（品种/周期/档位/看法）重取一份。**它换的不是桶，是"刷新"** —— 账本就是拿它跟前一份比的。
 *  返回：true ＝ 真换了一份新的；false ＝ 回的还是旧的（SWR）；null ＝ 这一趟没成（不补，等下一根）。 */
async function autoReload() {
  const own = state.data;
  if (!own || paging.loading) return null;    // 有别的请求在飞 ⇒ 让它把话说完，这一根让给它
  const id = ++paging.reqId;                  // 跟首屏/换看法/往左加载共用同一个号：谁后发谁算数
  paging.loading = true;
  dataStale = true;                           // 数据在飞：读数压住（跟换品种那条同一笔账）
  try {
    const anchor = own ? anchorOf(own.bars, chart.timeScale().getVisibleLogicalRange()) : null;
    const d = await load(el('symbol').value, el('tf').value, paging.span, paging.measure);
    if (id !== paging.reqId) return null;
    // ★ 取不到真后台时 load() 会**悄悄退回仓里的样本**（source 是「样本 x.json」，而且顺手把 span
    //   摁回 1、说自己「到最早」）。这一趟**绝不能当刷新画上去**：样本是另一份数据，账本会把它读成
    //   「屏上这些点全没了」—— 满屏假空心点；顺带还把档位和窗口一起洗掉（adopt 会吃它的 span/earliest）。
    //   宁可什么都不做：屏上这份照旧，下个收盘再说。（`source` 只有 load() 那头挂，页面别自己猜。）
    if (d.source !== 'api') {
      console.warn('自动重取没拿到真数据（退回样本），这一趟当没跑：', d.source);
      return null;
    }
    const fresh = autoFresh(own, d);
    // prevLen 传 undefined：这不是补数据，「要了却一根没多」那条判据在这儿不成立（同 setMeasure）。
    Object.assign(paging, adopt(paging, d));
    setUrl();
    if (anchor) draw(d, anchor); else draw(d);
    el('state').textContent = d.closed ? '已收盘' : '未收盘（最后一根还在走）';
    el('state').className = 'badge ' + (d.closed ? '' : 'live');
    return fresh;
  } catch (e) {
    // ★ 失败**不打扰用户**：屏上那份还是好的，角上那句也不改（别把一次后台抖动写成页面的错误）。
    console.warn('自动重取没成功（屏上这份照旧）：', e);
    return null;
  } finally {
    if (id === paging.reqId) { paging.loading = false; dataStale = false; }
  }
}
// ---------------------------------------------------------------- 实时跳价：只动最后一根（卡 card-f3fffac4-83d）
// 小栋 10-05 定的 A：最后一根 K 线的**价**跟着走，「结构」（笔/线段/中枢/买卖点）仍然**收盘才重算**。
// 后台那一半是 Bram 的 `/api/tick`（`agent/bram/live-tick` = 38938b2，契约见卡）：
//   `GET /api/tick?symbol=&tf=` —— **只认这两个参数**（多一个、少一个都 400）；
//   回 `{symbol, tf, t, o, h, l, c, v, fetched_at, stale, engine}`，`t` ＝ 这根的**开盘时间**；
//   按 (品种, 周期) 缓存 2.5 秒、**单飞**（几个页面同时来也只打币安一次 ⇒ 币安的请求数不随页面数涨，
//   这条是后台那半的账，前端只管"每个页面自己 5 秒问一次"）；
//   拉取失败 ⇒ 回上一次的值 ＋ `stale=true` ＋ `fetched_at` **冻在**上次成功那一刻；从来没成功过 ⇒ 503。
//
// ★★ 这一节最要紧的一条：**一次都不许走 paint()**。paint() 里有 ghostReconcile()（空心点记账）和
//   setData()（整份重画）—— 从那儿走就等于把「这是一份新数据」说了一遍：收盘前最后一根还在动，
//   点集按理一个没变，但账本会拿两份去比、整幅图跟着重画。所以这里**只有一个动作**：
//   改手上这份数据的最后一根，然后 `candle.update()` 那**一根** —— LWC 的 update 给的时间跟最后一根
//   一样就是"就地换掉这一根"，只重画那一小段；给早了/给晚了它才会 append，而那种情况根本不该发生。
const TICK_MS = 5000;                 // 每 5 秒一次（小栋定的）
let tickTimer = 0, tickBusy = false, tickWarned = false;
// 跳价这一趟的账：`tickAt` ＝ 价是**哪一刻**取回来的（stale 时后台冻着它 ⇒ 正好是"停在那一刻"），
// `tickStale` ＝ 这一趟没拉到新的。**不进 state.data**：那是后台那份 payload 的字段，跳价是另一笔账
// （页头/角上要的是"屏上这个价有多新"，见 renderLast / stamp）。paint() 一来就清掉（新的一份重新算）。
let tickAt = null, tickStale = false;

/** 排下一趟。**看不见就不排**（在后台偷偷取数既不划算也不礼貌 —— 跟自动重取同一条口径）；
 *  切回来由 visibilitychange 立刻补一次，不用等这 5 秒。 */
function tickPlan() {
  clearTimeout(tickTimer);
  if (document.visibilityState !== 'visible') return;
  tickTimer = setTimeout(tickFire, TICK_MS);
}
/** 取一趟。**每一道闸都在这里**：看不见不取、手上那份不是真后台的不取、图正在换的不取、上一趟还在飞的不取。
 *  （`source !== 'api'` 那条跟自动重取同一个道理：屏上是仓里的样本时，不存在"这个品种的价"这回事。） */
async function tickFire() {
  clearTimeout(tickTimer);
  const d = state.data;
  if (document.visibilityState !== 'visible' || tickBusy || paging.loading
      || !d || d.source !== 'api' || !d.symbol || !d.tf) { tickPlan(); return; }
  tickBusy = true;
  try {
    // 问的是**画在图上那一份**的品种/周期，不是下拉框里选的：换品种的那半秒里屏上还是旧那份图，
    // 要跳的就该是旧那份的价（新选的那个等它画上去再说）。**多一个参数少一个都 400**，别顺手多带。
    const q = `?symbol=${encodeURIComponent(d.symbol)}&tf=${encodeURIComponent(d.tf)}`;
    const r = await fetch('/api/tick' + q, { cache: 'no-store' });
    if (!r.ok) {
      // 503 ＝ 后台从来没取成功过（这一颗还没有任何可用的价）；别的非 2xx 也一样：
      // **屏上那份一个字都不改** —— 没有数就别编一个。这不是页面坏了，别写在角上吓人，
      // 每"连着失败一串"只嘀咕一句（不然 5 秒一句，控制台全是它）。
      if (!tickWarned) { console.warn('跳价没取到（屏上照旧）：HTTP ' + r.status); tickWarned = true; }
      return;
    }
    if (tickApply(await r.json())) tickWarned = false;
  } catch (e) {
    if (!tickWarned) { console.warn('跳价没取到（屏上照旧）：', e); tickWarned = true; }
  } finally {
    tickBusy = false;
    tickPlan();
  }
}
/** 把这一趟的价按上去。**只改最后一根**，别的一律不碰。返回 true ＝ 真按上去了。 */
function tickApply(j) {
  const d = state.data;
  if (!d || d.source !== 'api' || !d.bars || !d.bars.length) return false;
  // 这一趟问的和屏上这份**不是同一份**（问出去这几秒里换了品种/周期）⇒ 什么都不做
  if (j.symbol !== d.symbol || j.tf !== d.tf) return false;
  const last = d.bars[d.bars.length - 1];
  // ★★ `t` 是这根的**开盘时间**，跟图上最后一根**必须一样**才谈得上"就地换这一根"：
  //   · 比图上**新** ⇒ 那一根已经收盘、新的一根开盘了：**收盘那一刻交给已有的自动重取**
  //     （它本来就是按「最后一根 + 一个周期」排的，收盘后 2–10 秒自己会来，来了才发现得了结构），
  //     这儿抢着画一根结构还没的 K 线没有意义 —— 而且那是"往图上加一根"，不是这一节该干的事；
  //   · 比图上**旧** ⇒ 后台那份是旧的（缓存/时钟对不齐），更不能拿它往回改。
  //   两边都**一个字都不动**，屏上那份照旧。
  if (j.t !== last.t) return false;
  const o = Number(j.o), h = Number(j.h), l = Number(j.l), c = Number(j.c);
  if (![o, h, l, c].every(Number.isFinite)) return false;   // 后台换了形状 ⇒ 这一趟当没跑，别往图上写 NaN
  // ★ `v` **不动**：这一节只管**价**。量柱挂在另一条系列上（副图那三格也是按收盘算的）——
  //   顺手把它们一起刷就成了"跳价把量柱也重画了"，那是没人要的动静，要动是另一件事。
  last.o = o; last.h = h; last.l = l; last.c = c;
  candle.update({ time: last.t / 1000, open: o, high: h, low: l, close: c });
  // 价是这一趟拿回来的 ⇒ 页头和角上那两格跟着换（两处各有**一处**写法，见 renderLast / stamp）
  tickAt = j.fetched_at || tickAt;
  tickStale = j.stale === true;
  renderLast();
  stamp(d);
  readTick(d);              // 十字线正停在这根上的话，读数跟着换（图上动了、块里冻着就是一句谎）
  return true;
}

document.addEventListener('visibilitychange', () => {
  // 看不见了就都停：跳价那一串**清掉定时器**（tickPlan 在看不见时不排），跟自动重取同一条口径。
  if (document.visibilityState !== 'visible') { tickPlan(); return; }
  tickFire();                    // 切回来**立刻**跳一次价（它自己会重排下一趟）
  if (!state.data) return;
  // 切回来**立刻**补一次（⑤ 的错峰只管收盘那一刻：人都回来了，再随机等几秒就是白让用户看旧图）。
  if (autoDue(state.data)) autoFire(); else autoPlan();
});

function renderLegend() {
  const items = [];
  if (opts.pen) items.push(['line', CHART.pen, 1, '笔'], ['line-dash', CHART.pen, 1, '未完成的笔']);
  if (opts.seg) items.push(['line', CHART.seg, 2, '线段'], ['line-dash', CHART.seg, 2, '未完成的线段']);
  // ★ 「暂定」那一格**只在屏上真有暂定那一刀时才挂**：大多数图没有（25 张里 3 张），平白多一格会把图例顶折
  //   （见下面「会变」那段量过的账）。手机上没有悬停，所以说明不只靠 title：样例＋两个字就能对上屏上那个虚线圈。
  // RAW-SEGS: 暂定段只长在原始的未完成段上
  const tent = opts.seg && state.data && (state.data.segs || []).find((s) => s.tentative);
  // 样例圈的颜色跟屏上那个圈同一条：暂定段向上 ⇒ 那一刀是顶（红）；向下 ⇒ 底（绿）
  if (tent) items.push(['ring-dash', tent.dir === 'up' ? CHART.sell : CHART.buy, 0, '暂定',
    '先判出来的一刀：要等这一刀后面第一笔的两头谁先被突破，才知道它算不算数']);
  if (opts.pc) items.push(['box', CHART.pen, 2, '类中枢（与笔同色）'], ['box-split', CHART.pen, 2, '前三实线 / 延续虚线']);
  if (opts.sc) items.push(['box', CHART.seg, 4, '线段中枢（与线段同色）']);
  // ★ 「会变」那一档（§八 8，卡 card-06d7f9a1-3ad，小栋选的 C+）。挂**照旧那一格样例**：
  //   一个跟屏上同档淡下来的框，右边「会变」两个字 —— 屏上那个字就是这两个字，一眼对得上。
  //   ★ 判据是**框层开着**（`pc`/`sc`），不是 `trend`：淡的是框，阈值虽然读走势分段的 `bounds[1]`，
  //     但「这几个框靠不靠得住」跟「要不要把带子画出来」是两件事 —— 关掉走势分段，框该淡还是淡。
  //   ★ 样例文字就两个字、说明进 `title`（卡上那句原话就是「图例加一行」）。
  //   ★★ 这一格占多少宽度**量过三档**（1280 宽、同一张 ZEC 30m、改动前后各一遍）—— 先说结论：
  //     **默认那档是白捡的，可「买卖点」开着那档真的被顶折过**，为它让的是列间距（见 style.css）。
  //     ① 默认（8 格）：n 7→8、lastRight 787→861.5；`legendH` 31.5、`#chart` 663，一个字没动。
  //     ② **「买卖点」开（10 格）：改前 1 行（lastRight 1203.6，余 62.4px）⇒ 加这格 74.5px ⇒ 折
  //        成两行**（31.5→54、`#chart` 663→640.5、−22.5px）。`tools/web_readout_e2e.js` 的 ㉑
  //        就是按图底往上数 40px 处点指针的 —— 图一矮那一点就落到别处，**当场红**（实测 2/2）。
  //        ⇒ 这条是这一卡唯一一处真回归，修法在 `web/style.css` 的 `.legend`（列间距 16→12）。
  //     ③ 层开满（类中枢＋高一级＋买卖点，14 格）：改前**本来就两行**，加完还是两行、两个数没变
  //        —— 这一档不是被这格撑破的。★ 别拿这一档当"没事"的证据：它本来就折着，
  //        借它看不出问题（我先量了这档，差点就此收工）。
  //     ⇒ 要再来一格：**照 ② 那档重量**（默认那档余量大得会骗人），别再靠「应该还有地方」。
  if (opts.pc || opts.sc) items.push(['box-fade', CHART.seg, 4, '会变',
    '第 2 条分界线之前的框：那一段的位置会随窗口起点变']);
  if (opts.up) items.push(['box', CHART.up_pen, 2, '高一级：类中枢升的'], ['box', CHART.up_seg, 4, '高一级：线段中枢升的']);
  // ★ 「等确认」那条斜线带（§八 3，卡 card-60678062-8c2）。**这是补的，不是改的** ——
  //   走势分段那一层（card-c73ab37d-5a1）当初上线时**一条图例都没上**，这个器件在屏上就是一条斜线，
  //   小栋的原话「没有文字说明」是字面意思：屏上真的一个字都没有。
  //   悬停那句（`title`）用大白话，不写「中阴」「回抽段终点」这些内部叫法。
  if (opts.trend) items.push(['hatch', TREND.hatch, 0, '等确认',
    '从这个高点／低点出现，到它被确认为转折点的这段时间']);
  items.push(['tag', CHART.pen, 0, '价签：实底 ＋ 黑字']);
  if (opts.sig) items.push(['tri-fill', CHART.buy, 0, '买卖点（线段中枢层）'], ['tri-hollow', CHART.sell, 0, '空心「·笔」＝类中枢层，「?」＝待确认']);
  // ★ 价签那一格**不能用定宽 SVG**（2026-10-03 真机反馈：`[ZD,ZG]` 缺了右括号）。
  //   原来样例是 `<svg width="30">` ＋ 里面 `<text font-size="9">`：那串字**实测 35.23px**、起点 x=3
  //   ⇒ 越界 8.23px。注意这跟「真机太窄」无关 —— SVG 定宽 30，**桌面宽度下一样缺右括号**。
  //   改成 HTML 一格：宽由浏览器按字量出来，写死的那一头就没了（同一类账：图脚那把尺的 44 字预算）。
  //   样例文字与 Python 的图例一字不差（`full_common.py:270` 画的就是 `[ZD, ZG]`，带空格）。
  el('legend').innerHTML = items.map(([kind, col, w, name, tip]) => {
    const dash = kind === 'line-dash';
    const svg = kind === 'tag'
      ? `<span class="tagsw" style="background:${col};color:${CHART.tag_ink}">[ZD, ZG]</span>`
      : kind === 'tri-fill'
        ? `<svg width="30" height="14"><polygon points="15,1 6,13 24,13" fill="${col}"/></svg>`
        : kind === 'ring-dash'
          ? `<svg width="30" height="14"><circle cx="15" cy="7" r="5.5" fill="none" stroke="${col}" stroke-width="1.6" stroke-dasharray="3 2.3"/></svg>`
        : kind === 'tri-hollow'
          ? `<svg width="30" height="14"><polygon points="15,1 6,13 24,13" fill="none" stroke="${col}" stroke-width="2"/></svg>`
          : kind === 'box' || kind === 'box-split' || kind === 'box-fade'
            // 「会变」那一格：**同一支样例，只是整格降权**（`opacity` 把填充和框线一起乘下去 ——
            // 跟画布上 `drawFrame` 的 `fillAlpha * fade` ／ `235 * fade` 是同一条账）。
            // ★ 不换色、不改虚线：屏上变的也只有这一件事，图例自己变了样就不叫图例了。
            ? `<svg width="30" height="14"${kind === 'box-fade' ? ` opacity="${TREND.willChangeFade}"` : ''}><rect x="1" y="2" width="28" height="10" fill="${col}22" stroke="${col}" stroke-width="${Math.min(3, w * 0.6)}" ${kind === 'box-split' ? 'stroke-dasharray="6 4"' : ''}/></svg>`
            // 「等确认」那条带：样例要跟**屏上那条**同构 —— 一条贴顶的矮带子，里面 45° 斜线。
            // 画成一条细横线（就是下面那个兜底分支）会让人以为是"一条线"，而这一层最容易被读错的地方
            // 恰恰就是这个（见 layers.js 那句「不是一条从左下斜到右上的连线」）。
            : kind === 'hatch'
              ? `<svg width="30" height="14"><defs><pattern id="lgHatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="${col}" stroke-width="1.5"/></pattern></defs><rect x="1" y="3" width="28" height="9" fill="url(#lgHatch)"/></svg>`
              : `<svg width="30" height="14"><line x1="1" y1="7" x2="29" y2="7" stroke="${col}" stroke-width="${w}" ${dash ? 'stroke-dasharray="5 4"' : ''}/></svg>`;
    // `title` 是悬停提示（卡 card-60678062-8c2 要求一句大白话）。只有给了 tip 的那几条才挂。
    return `<span class="lg"${tip ? ` title="${tip}"` : ''}>${svg}${name}</span>`;
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
// 中枢切法：代号 → 人话（Nova 10-05 拍的）。跟 MEASURE_NAME 同一条规矩：后台加了第三种 ⇒ 原样印代号、
// **不吞**；这张表**控件和图脚共用**，所以跟 MEASURE_NAME 一样放在这一块里（见本块开头的注释）。
const CUT_NAME = {
  extend: ['延伸', '延伸：中枢照原文的延伸/扩展判定'],
  trend: ['走势分段', '走势分段：按 docs/spec/走势分段.md 的段定义切开 —— 死点之后本级别第一个反向三类点'
    + '确立分界，只在确立的分界处断开；中阴（还没立住）的框不断、画灰点线待定（默认；卡 card-51571a5f-dc2）'],
};
// 图脚那一格（跟「背驰看法」同一格、同一条规矩）：**认回显**（`d.cut`）—— 用户点的那颗可能失败，
// 屏上画的到底是哪种，只有后台回的那份说了算。旧后台和离线样本没有这个字段 ⇒ 这一格**不出现**。
// ★ **缺省（走势分段）也印**：图脚是一张图的记录 —— 两张对照图（延伸／走势分段）就靠这一格分开，
//   要是"只有换了才印"，切换前那张图上没有任何一处说得出它是哪种切法。
// ★ 老链接 `?cut=turn` 后台当 trend 收、**回显 trend** ⇒ 图脚印的是「走势分段」。这一格认的是回显，
//   所以**不用**在这里给 turn 留一个名字：留了反而会印出一个后台已经不用的档位。
function cutText(d) {
  const c = d.cut;
  if (typeof c !== 'string' || !c) return '';
  return ` ｜ 中枢切法 ${(CUT_NAME[c] || [c])[0]}`;
}
// 「消失的点」那个数（卡 card-cf3ed018-795）。★ 它是**单独一格浮层**（#ghostc），不并进图脚那行：
//   图脚是流内布局，这一格一出来就把 #chart 挤矮（1440 实量：foot 60→77、#chart 760→743，
//   整张图往下挪 3px —— 而它偏偏就是"消失的点刚出现"的那一刻，用户会看见图跳一下）；
//   窄屏那一档 `.foot` 整个 display:none，手机上这个数根本不存在。
// ★ 「本次打开」四个字不许省：回测那边报的是「150 个确认里 41 个被改掉」，分母是整段历史、起点固定；
//   这个数的分母是**这一次打开、有人看着的那段时间**，而且窗口还在往后滑。
//   两个数长得像 —— 混起来就是拿两个分母比大小，而屏幕上不会有任何一处会红。
// ★ 走 `el()` 而不是直接摸 document：`tools/web_footer_check.py` 把 renderMeta 抠出来配假 DOM 真跑
//   （它的 el 桩带 textContent / className 的 setter）—— 直接摸 document 那一格当场 ReferenceError。
function ghostText(d) {
  const g = d.ghosts;
  const n = Array.isArray(g) ? g.length : 0;
  el('ghostc-tx').textContent = n ? `消失的点 ${n}（本次打开）` : '';
  el('ghostc').className = n ? 'ghostc on' : 'ghostc';
}

function renderMeta(d) {
  // 「完成线段 N」数的是**图上画的那套**（小栋 10-10 05:18 问两套线段：原来数原始 ⇒ 跟屏上数出来的条数对不上，card-83915c20-9e3）。
  //   未完成段只在原始里有 ⇒ 「+M 未完成」照旧数原始里的 live。
  const live = (d.segs || []).filter((s) => s.live).length;   // RAW-SEGS: 未完成段只在原始里有
  const done = Array.isArray(d.segs_std) && d.segs_std.length ? d.segs_std.length
    : (d.segs || []).length - live;   // RAW-SEGS: 老后台没有 segs_std 时的退路
  el('meta').textContent =
    `${d.name || d.symbol} · ${d.tf} ｜ ${d.nbars} 根 ｜ 笔 ${d.pens.length} ｜ 类中枢 ${d.centers.length}`
    + ` ｜ 完成线段 ${done}（+${live} 未完成）｜ 线段中枢 ${d.seg_centers.length}`
    + ` ｜ 精度 ${d.meta?.tick} ｜ ${d.meta?.pen_rule === 'new' ? '新笔' : '老笔'}${Number.isFinite(d.pen_min) ? `（最少 ${d.pen_min} 根）` : ''}`
    + ` ｜ 买卖点 线段中枢层 ${sigTierText([...(d.signals?.seg || []), ...(d.trend?.xzd_seconds || [])])} · 类中枢层 ${sigTierText(d.signals?.pen || [])}`
    + measureText(d)
    + cutText(d)
    // 分界那一刀的说明（卡 card-22888623-1a7）。★ 它**只在这儿写一次**：这句是"整句说明"，
    // 图例那一行的写法（短名字 ＋ 整句进 `title`）本来就装不下它 —— 1280 ＋ 买卖点那档图例
    // 只剩 23.9px 余量，加一格最低消费 46px，Nova 10-06 拍了「进图脚、图例不动」。
    // ★ 措辞是 Nova 定稿的原话，一个字没改（第 29 课 L29:37-41）。
    // ★ 不写"什么时候不出现"：虚线分界这一层本来就在高低点上，这句说的是**个别那一刀**的来由 ——
    //   判据在后端（bound 上的 `rule`），前端不自己重推一遍。
    + ' ｜ 虚线分界一般在高低点；个别是大横盘后接一段趋势时补切的（第 29 课）'
    + ` ｜ 数据源 ${sourceLabel(d.source, d.stale)}`;
  ghostText(d);          // 那一格是浮层（见上），不在这句话里 —— 两处各写一遍就会分家
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
// ★ 2026-10-06 再改一次（card-e7554dd2-44a，小栋 06:4xZ）：这两格原本按 **UTC** 印。可它们答的是
//   「我手上这根什么时候开的／数据什么时候刷的」—— 那是**用户自己的钟**上的事，不是行情坐标。
//   一个 UTC+8 的人看到「本根 04:00 开盘」，得自己心算 +8 才知道是不是刚开的；这正是本地钟该干的事。
//   ⇒ 这两格一律按**浏览器本地时区**印，并在那一行末尾把偏移量写出来（`zoneTag`），
//     免得它跟图上那根 UTC 轴对不上时，用户以为是图错了。
//   ★★ **图上不动**：时间轴的刻度、光标读数（`timeLabel`）、画布上那些记号，**仍是 UTC** ——
//   那是行情自己的时间原点，全世界的图都拿它当坐标；跟页头这格不是一件事，别顺手一起改
//   （app.js:132 那段「只此一份」管的是**画布那一侧**：轴上的刻度、光标读数里的时刻，念同一句。
//    页头从来不在那句话的射程里 —— 它是「数据新不新」，不是「这一根在坐标系的哪儿」）。
function stamp(d) {
  const t = d.updated ? new Date(d.updated) : null;
  // ★ 跳价那一趟也是**取数**（card-f3fffac4-83d）：价是它拿回来的，所以「数据 … 刷新」说的是**最新那一次**。
  //   照旧只写 chart 那份的时间，角上就成了一句假话（价是刚取的、戳却是几分钟前的）。
  const src = tickAt || d.fetched_at;
  const f = src ? new Date(src) : null;
  const barTxt = shortLocal(d.updated);
  const srcTxt = shortLocal(src);
  const bar = barTxt ? `本根 ${barTxt} 开盘` : '数据时间未知';
  // ★ 印的就是上面判过的那个 `src` —— 判据用 `src`、印的却是 `d.fetched_at`，这一格就成了"两处各写一遍"
  //   （跳价取的价、配着 chart 那份的戳）。秒在角上只是噪音，所以只印到分。
  // ★ 「数据」那一格的**日期**：跟本根同一天（都按本地算）就省掉。两格挨着写两遍同一个日期全是噪音，
  //   而它正好占着窄屏那点预算 —— 手机 360 上这一行一共只有 344px，一个日期就是 60 多 px
  //   （见 style.css 手机那段）。少一个日期，才装得下后面的时区。
  //   ★★ 不同天**必须**写出来：后台停了一夜之后「数据 15:20 刷新」配着今天的本根，会被读成**今天**
  //     15:20 —— 那正是最该说清楚的一刻，省掉日期＝省掉它唯一的破绽。所以这条不是"好看点"，
  //     是"同意省略的前提是同一天"。本根印不出来（barTxt 空）时也照旧写全：没有可比的那一天。
  const sameDay = srcTxt && barTxt && srcTxt.slice(0, 10) === barTxt.slice(0, 10);
  const fresh = srcTxt ? ` ｜ 数据 ${sameDay ? srcTxt.slice(-5) : srcTxt} 刷新` : '';
  // 后台这轮没拉到币安、回的是上一次的结果时会带 stale=true：那这格的取数时间说的是**上一次**，
  // 不标出来它就是一句假话 —— 角上必须自己承认。字段没有 / 为 false 就照常。
  // ★ 跳价那一趟的 stale 也算：价卡住不动的时候，角上跟页头那一格（「价格停在 …」）说的是同一件事。
  const st = !!d.stale || tickStale;
  // 时区那一格（"UTC+8"）：**印过哪个时刻就按哪个时刻算偏移** —— 有夏令时的时区一年里会变，
  // 拿"现在"的偏移去标一个几小时前的时刻，那天正好跨了切换点就是假的（Europe/London 那类）。
  // 两个时刻都没有（离线样本）才退回到"现在"：那一行只剩一句「数据时间未知」，标着也不会更错。
  const zt = zoneTag(f && !isNaN(f) ? f : (t && !isNaN(t) ? t : new Date()));
  // ★ 这一格的字面量是 **`UTC+8`**，不是「本地 UTC+8」：省掉那两个字是有代价的，代价拿宽度换的。
  //   360 宽的机器上这一行只有 344px（style.css 手机那段），「本地」两个字恰好把它顶到两行 ——
  //   而顶栏每高一截，图就矮一截（card-c7f19e45-022 那一整笔账）。偏移量本身已经把话说完了：
  //   时刻后面跟着 `UTC+8`，就是"这一行按 UTC+8 念"（ISO 里 `+08:00` 也是这么收尾的）。
  //   它跟右边那根 UTC 轴怎么区分？—— 轴的刻度**不带**这个尾巴，页头这行**带**；两个钟只差这一处，
  //   一处就够。真要说清楚"这是你自己机器那个钟"，那句话在 title 里（下面那一句），一个字没省。
  // ★ 三段挨着排，别抽成常量表：顺序就是屏上读出来的语序，是版式决定，不是数据决定的。
  const base = `${bar}${fresh} ｜ ${zt}`;
  el('updated').textContent = st ? `${base} ｜ ★ 旧数据（本轮拉取失败）` : base;
  el('updated').className = 'badge' + (st ? ' warn' : '');
  // 相对时间（"3 小时前"）只放 title：角上那格宽度有限，而且相对时间依赖**客户端时钟**，
  // 钟不准就会说错话 —— 绝对时间不会。相对值在这里仍有用（一眼看出多旧），所以不删。
  const rel = f && !isNaN(f) ? `（${ago(f)}）` : '';
  // ★ 这两句里原来各写了一遍「（UTC）」—— 现在改成**一处**说清楚：两个时刻同一个钟，说一遍就够，
  //   说两遍反而像两个不同的时区。图上那根轴是另一件事，这里不提，免得用户以为页头也在 UTC。
  el('updated').title = st
    ? `这是上一次的结果：本轮拉取没成功（后台 stale=true）；「数据 … 刷新」说的是那一次的取数时间（本地时区 ${zt}）${rel}`
    : `两个时刻都按你机器的本地时区印（现在是 ${zt}）：本根＝最后一根 K 线的开盘时间，数据＝后台从币安取数的时间${rel}，价格随它更新`;
}
/** 那一刻的 UTC 偏移怎么念："UTC+8"／"UTC-3:30"／"UTC+0"。整点不带 ":00"（"UTC+8" 比 "UTC+8:00" 好读）。
 *  ★ 按**传进来的那一刻**算，不是模块加载时算一次：有夏令时的时区一年里会换偏移，
 *   开机算一次的那份在切换点之后就是错的（而且错得很难看 —— 它会在屏上理直气壮地写出来）。
 *  ★ getTimezoneOffset() 是**反的**（西区为正），所以取负号；分那一位用绝对值取，别让符号漏进去。 */
function zoneTag(d) {
  const m = -d.getTimezoneOffset();                      // 分钟，东为正
  const h = Math.trunc(m / 60), mm = Math.abs(m % 60);
  return `UTC${m < 0 ? '-' : '+'}${Math.abs(h)}${mm ? ':' + String(mm).padStart(2, '0') : ''}`;
}
/** "2026-09-29T14:50:00Z" → "14:50"（**浏览器本地时区**）。认不出来就返回空串 —— **不知道的事不编**
 *  （页头那一格写「价格停了」也不写一个瞎编的时刻）。跟 shortLocal 同一处口径。 */
const clockLocal = (s) => {
  const d = new Date(s);
  return isNaN(d.getTime()) ? '' : [d.getHours(), d.getMinutes()].map((n) => String(n).padStart(2, '0')).join(':');
};
/** "2026-09-29T00:00:00Z" → "2026-09-29 08:00"（**浏览器本地时区**）。
 *  ★ 认不出来 ⇒ 空串。**不猜、不洗** —— 原来那版是拿正则从 ISO 串里抠字，认不出来就把原串抹掉 T/Z
 *   吐回去；那串字未必是给人看的格式（后台真换了格式，屏上就会多一句谁也读不懂的话）。
 *    判据从"像不像 ISO"改成"Date 认不认"，是**收紧**：`null`/`""` 这些以前会漏进分支的值
 *    在这里必须显式挡掉 —— `new Date(null)` 不是 Invalid，它是 1970，会安安静静印出个假时刻。 */
const shortLocal = (s) => {
  if (s == null || s === '') return '';
  const d = new Date(s);
  if (isNaN(d.getTime())) return '';
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
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
  // 切法同理（缺省是 trend）：只有真切到「延伸」那份才写上去。★ 名单没到 ⇒ 也抹掉：
  // 那时候页面上根本没有这一组，地址栏却留着一个页面上不存在的词，是句假话（跟 load() 那条闸门对称）。
  // ★ 顺带把老链接的 `?cut=turn` 从地址栏换掉：认得出它的是**后台**（当 trend 收），前端这一格按
  //   `paging.cut` 重写 ⇒ 改名之后第一次 setUrl 就把它归一成 trend（或者直接抹掉）。
  if (cuts.list.length && paging.cut !== DEFAULT_CUT) q.set('cut', paging.cut);
  else q.delete('cut');
  // 笔的根数同理：跟**后台的缺省**一样就抹掉，不一样才写（`?pen=7`）；名单没到也抹掉。
  if (pens.list.length && paging.pen != null && paging.pen !== pens.def) q.set('pen', String(paging.pen));
  else q.delete('pen');
  // 副图那两颗同理：跟**这一屏的默认**（桌面开、手机关，见 SUB_DEF）不一样才写上去。
  // 这样地址栏永远只写"这一屏再从零打开会不一样的东西"—— 写着默认值是噪音，换屏时还得记得抹掉。
  for (const k of ['vol', 'macd']) {
    if (opts[k] === SUB_DEF) q.delete(k); else q.set(k, opts[k] ? '1' : '0');
  }
  // 走势分段那一层：**默认开**（Nova 17:09Z），所以这一头反过来写 —— **关着才写上去**（`?trend=0`）。
  // 跟上面两颗（vol/macd 缺省写不写）同一条账，方向相反而已。
  if (opts.trend) q.delete('trend'); else q.set('trend', '0');
  // 级别对照同理（card-01961644-68f）：**默认开** ⇒ 也是关着才写上去（`?lv=0`）。
  if (opts.lv) q.delete('lv'); else q.set('lv', '0');
  // 框编号：**默认关**（跟「走势分段」那颗反着来）⇒ 开着才写上去。
  if (opts.trendNum) q.set('trendnum', '1'); else q.delete('trendnum');
  // 入门防守：默认关 ⇒ 开着才写；周期「跟图」不写，另选了才写。
  if (opts.wolf) q.set('wolf', '1'); else q.delete('wolf');
  if (opts.wolf && wolfTf) q.set('wolftf', wolfTf); else q.delete('wolftf');
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
  // ★ 级别对照那一趟（card-01961644-68f）跟图表那份**并行**发 —— 绝不 `await` 在 `draw()` 之前：
  //   它是附加层，比图表那份小、通常先到，但**先到也不许把首屏推后**（首屏画完它再落上来，
  //   只重画走势那一层，见 `renderLevels`）。`loadLevels` 自己吞掉所有失败 ⇒ 拿不到就是 `null`。
  const lvReq = loadLevels(symbol, tf, paging.span);
  // ★ 新的这一趟一开跑，**上一份 levels 当场作废**：`levels.units` 跟框只有"同下标"这一条契约
  //   （没有身份字段，见 layers.js `lvAligned`），换了品种/周期/档位之后同一个下标指的不是同一个框
  //   —— 留着只会把标安到旁边那个框上（保守那一边：先全撤）。
  //   `renderLevels` 顺手把浮层那一行话也收干净（state.levels 已是 null ⇒ 那句话自己就没词了）。
  state.levels = null;
  renderLevels();
  try {
    const d = await load(symbol, tf, paging.span, paging.measure);
    if (id !== paging.reqId) return;
    Object.assign(paging, adopt(paging, d));     // ★ 首屏也认回显：一开始就 earliest 的品种不该白发请求
    setUrl();                                    // 后台钳过档的话（15m 要 16 钳到 4），地址栏写**真**档位
    draw(d);
    renderMeasures();                            // 亮哪一颗看回显（名单是后到的，首屏画完得补一次）
    renderCuts();
    renderPens();
    el('state').textContent = d.closed ? '已收盘' : '未收盘（最后一根还在走）';
    el('state').className = 'badge ' + (d.closed ? '' : 'live');
    // ★ levels 到这儿才落上来 —— **在 `draw()` 之后登记 `.then`**：先画图、标后补，顺序写死在这儿
    //   （levels 哪怕早就在手里，回调也是"登记之后"的微任务才跑，赶不上这次 draw 之前）。
    //   到了只重画走势那一层（`renderLevels`），**不 setData、不重排、不 fitContent** ——
    //   首屏那份已经画好了，再来一遍整图的活是白干，还会让视口跳一下。
    //   ★ 老规矩：这一趟要是已经被更新的一趟顶掉（`id` 对不上），这份丢掉 —— 别把上一趟的标画到下一种图上。
    lvReq.then((lv) => {
      if (id !== paging.reqId) return;
      state.levels = lv;
      renderLevels();
    });
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
// 跳价那一串**现在就开始数**（每 5 秒一趟）：头几趟手上还没有数据、或者图还没画上，
// tickFire 自己那几道闸会当没到点（见那一节），不用在这儿等首屏 —— 这样"打开页面到第一跳"
// 最多 5 秒，不会因为首屏慢就往后拖。
tickPlan();
// 看法那份名单跟首屏的图表请求**并行**发（不为一个小请求把首屏推后）。只有一个例外见下面：
const metaReady = loadMeasures();
(async () => {
  const q = new URLSearchParams(location.search);
  // ★ 地址栏**点名了**看法就得先等名单：名单外的名字发出去后台回 400，整张图会白挂在这一个词上
  //   （跟 `?load=` 超白名单会被钳是同一类账，只是那边前端能自己钳、这边得先问后台认哪几个）。
  //   没点名（绝大多数）⇒ 一个字都不等，立刻发第一趟；那一趟不带 measure，走后台自己的缺省。
  //   切法（`?cut=`）同一条：点名了就得等名单 —— 名单外的词发出去，挂掉的是整张图。
  //   笔的根数（`?pen=`）同一条：点名了就先等名单，不然首屏那一趟不带它 ⇒ 回显是缺省那档 ⇒ 地址栏被
  //   抹掉，分享出去的 `?pen=7` 一打开就弹回缺省（10-08 实测逮到）。
  if (q.has('measure') || q.has('cut') || q.has('pen')) await metaReady;
  // ?load=N：直接打开某一档（可分享 / 可截图复现；N 不在白名单上就退回它下面的那一档）
  go(ladderSpan(q.get('load')));
})();

// 给验收工装一个**只读**入口：并排截图要把网页这一格切到跟 Python 出图同一段 K 线、同一价格带，
// 那就得问图自己「第 i 根在哪个 x、这个价在哪个 y」（timeToCoordinate / priceToCoordinate）。
// 不是功能开关，页面上没有任何东西读它；去掉它，验收那两张图就没法对齐。
// ★ `fmtPrice` 也递出去：工装要证「页头那个价跟图上那个价是**同一个数**」，只能拿页面**自己这个格式器**
//   把图上那份印一遍去比 —— 工装自己再四舍五入一遍就是第二份规矩（`toFixed` 看二进制真值、
//   `toLocaleString` 看最短十进制，1313.995 这种正好落在半个末位上的值会差一分，判据在**没事**的时候红）。
// ★ `shortLocal`／`clockLocal`／`zoneTag` 跟 `fmtPrice` 同一个理由挂出去：页头那两个时刻的判据里，
//   期望值要**由页面自己印**（工装在 node 里另写一份 Date 取值器，就是第二份规矩 —— 时区一样、
//   但口径是抄的，抄的那份迟早跟页面分家；而这两个函数正是"本地钟怎么念"的唯一一份）。
//   ★ 它们**只是印**，不碰状态：跟下面那两条注释一样，工装拿到的是字，不是权限。
window.__app = { chart, state, opts, paging, measures, cuts, sub, fmtPrice, autoReload,
                 shortLocal, clockLocal, zoneTag,
                 // 工装只读出口（web_samelevel_e2e ⑧，D-3 C）：线段三条系列的数据，量「图上画的是哪一套」；repaint 只给塞假载荷后重画用
                 segSeries: { solid: segSolid, dash: segDash, stdLast: segStdLast }, repaint: () => paint(state.data) };   // autoReload：工装 readout_swap_probe 的 F 场景直接触发自动重取
