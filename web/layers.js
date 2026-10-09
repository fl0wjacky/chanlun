// 结构层：中枢框（含「拆两截」）、价签、买卖点、未收盘那根。
//
// lightweight-charts 自带的只有 K 线与折线；中枢的**水平带 + 分截虚实**、价签的实底黑字、
// 买卖点的空心/实心三角，都得自己往画布上画 —— 这就是这个文件。
//
// 画法不是重新设计的，是 `render/full_common.py` 一行行搬过来的：box_split 的三档（规则 B）、
// draw_signals 的尺寸与偏移、draw_labels 的「先到先得往上挪最多 12 行」。搬的时候保持同构，
// 是为了以后改 Python 那版时能一眼看出这边该改哪一段。
import { CHART, CANDLE, DASH, PAGE, SIG, SUB, TREND, WIDTH } from './theme.js';

// ---- 小工具 ----
const hex2rgb = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
const rgba = (h, a) => { const [r, g, b] = hex2rgb(h); return `rgba(${r},${g},${b},${a / 255})`; };
const lighter = (h, d = 40) => '#' + hex2rgb(h).map((v) => Math.min(255, v + d).toString(16).padStart(2, '0')).join('');

// 「高一级」那些框的点色：**按级别取，同一级同一色**（小栋 10-05 23:3xZ 定，卡 card-113a3b16-026 第 ② 条）。
//   线段中枢升上去的 ⇒ 品红（`up_seg`）；类中枢升上去的 ⇒ 淡紫（`up_pen`）。
// ★ 这一条现在有**三处**用，所以它得是一个函数、不是三处各写一遍的三目：
//   框层那两个 `z.up`（满 9 段升出来的，按**它底下那个框**的 `tier`）＋ 走势那一层的合成大框（定死 `seg`）。
//   分头写的话，哪天改配色就会改漏一处，而漏掉的那处**不会红**，只会让人在图上看见两种"高一级"不是一套色。
// ★ 合成大框为什么是 `seg`：走势分段这一层本来就是**在线段中枢那一级**分的（`docs/spec/走势分段.md`），
//   它扩展合成出来的当然是线段升一级 ⇒ 品红。不是"挑"的，是这一层在哪一级决定的。
const upColor = (tier) => (tier === 'seg' ? CHART.up_seg : CHART.up_pen);

// ---------------------------------------------------------------- 级别对照（卡 card-01961644-68f，L-9）
// 「对照图」—— 就是后台 `levels.ref_tf` 那一档 —— 的名字怎么念。★ **不在前端拿 4× 去推**：
// 2h／4h 这两档本来就**没有对照图**（后台给 `ref_tf: null`，屏上该说「跨度最大的一档，没有对照图」），
// 拿「自己 ×4」算出来的名字在那儿是**一句假话**。载荷给的是**代号**（'1h'/'2h'/'4h'），名字在这儿翻。
// ★ 认不出来（后台哪天加了第五档、或者载荷里是个没见过的词）⇒ 返回空串 ⇒ 不画、
// 不编 —— 「不知道的事不编」跟 measure/cut 那两处是同一条账。
// ★ `同名` 那张是给「对照图（…）还没取到」那句短话用的（去掉尾字「图」，括号里那一格不带"图"）。
const REF_TF_NAME = { '1h': '1 小时图', '2h': '2 小时图', '4h': '4 小时图' };
export const refTfName = (tf) => REF_TF_NAME[tf] || '';
/** 合成框的对照结论 → 框右沿那句短标（**≤8 字**，见 L-9 三档）。**只在 `mismatch` 上出字**：
 *   `match`（整个落在同一个对照中枢里）、`partial`（只落在图头/图尾那两截、不算分歧）、
 *   `unmeasured`（对照图没缓存）—— 这三档**一个字都不出**（L-9／Nova 13:37Z）。
 *  ★ 三档 mismatch 是**实拍**分出来的（Bram 线上 ZEC 15m 对 1h 真回了三档）：
 *    ① `share.length >= 2`：跨了两个以上对照中枢 ⇒ 「<对照图>上不一样」；
 *    ② `share.length === 1 且 gap>0`：一段落进中枢、一段落进两个中枢之间的空档 ⇒「中间一段空着」；
 *    ③ `share.length === 0 且 gap>0`（gap 100）：整个框落在空档里、一个中枢都没碰到 ⇒「<对照图>没有中枢」。
 *  ★ ①②③ 都要求 **gap>0**：L-9 说 mismatch 的两种来源是「有 gap」或「跨 ≥2 中枢」。`share.length>=2`
 *    就是跨了两个以上；`share.length===1` 只剩 gap 这一条路。三档之外的（比如 share 空又没 gap）
 *    ⇒ 返回空串：**宁可漏一个标，也不标错**（保守的那一边）。
 *  ★ `share[].pct` 的分母是**整个框**（`sum(share)+pre+gap+post=100`），所以这里只看档数、不看占比 ——
 *    占比是判状态时后台的事，前端不再算第二份。 */
export function lvTagText(u, refName) {
  if (!u || u.status !== 'mismatch') return '';
  const share = u.share || [];
  const gap = (u.outside || {}).gap || 0;
  if (share.length >= 2) return refName ? `${refName}上不一样` : '';
  if (share.length === 1 && gap > 0) return '中间一段空着';
  if (share.length === 0 && gap > 0) return refName ? `${refName}没有中枢` : '';
  return '';
}
// ★★ 把 `levels.units` 对到框上 —— **今天能走的只有"位置"这一条路**，先把代价说破：
//   实拍的载荷里，`levels.units` 每一条**只有一个 `{status, share, outside}`** —— 没有 `X0`、没有 `X1`、
//   没有 id，**一个身份字段都没有**（曾按 `X0` 配过，线上一个标都出不来：`u.X0 != null` 对每一条都是假，
//   字典是空的、字全没了，而屏上什么都看不出来）。
//   ⇒ 唯一有契约的凭据是**同下标**：`levels.py` 写的是「本图每个合成框（trend.units，**同下标**）」。
//     这是"今天只有这一条路"，不是"这条路最稳"：两份载荷的框数/次序一旦对不上，按下标就**整体错位**
//     （错位＝标安到旁边那个框上，屏上一样是"有字的"，看不出来）。
//   ⇒ 所以位置配对**必须另加闸**，`lvAligned` 就是那道闸：对不上就一个都不标（保守那一边）。
//   ★ 往后后台要是给每个框一个**身份字段**（哪怕就是 `X0`），按身份配严格更稳 —— 那时把这一支换掉，
//     别留着这段话当"已经够好了"。Bram 那边当作可选加固在要，不是拦路的。
/** 三道闸都过 ⇒ 返回可以按下标取的 `levels.units`；任何一条不过 ⇒ `null`（＝一个标都不画）。
 *  ① **框数**：跟这一帧的 `T.units` 一样多吗？少算/多算一个框，同下标就整体错位。
 *  ② **周期**：载荷回显的 `tf` 跟屏上这一份（`state.tf`）一样吗？
 *  ③ **档位**：`span` 一样吗？★ 这一道专治**旧快照** —— 往左补数据之后 span 变了，两份载荷的框数
 *     往往还一样（① 拦不住），而同一个下标在新旧两档上指的不是同一个框。
 *  ★ ②③ 比的是**屏上这一份**（`state.tf`/`state.span`），不是我们刚才发出去的请求参数：后台会钳档
 *    （15m 要 16 钳到 4），"我发了什么"不算数、回显才算 —— 跟 `adopt()` 那条账同一条。
 *  ★ **不拿 `symbol` 比**：换品种/换周期一律走 `go()`，那儿当场把 `state.levels` 清成 null（见 app.js），
 *    比 `symbol` 是第二道保险，而它一错（后台回显的写法跟请求不完全一致）就会把这一层整片关掉。
 *  ★ `span` 用字符串比：后台给 `1` 还是 `"1"` 都不该决定这一层画不画，缺字段（`null`/`undefined`）才算不过。 */
export function lvAligned(T, lv, tf, span) {
  if (!T || !Array.isArray(T.units) || !lv || !Array.isArray(lv.units)) return null;
  if (lv.units.length !== T.units.length) return null;
  if (lv.tf !== tf) return null;
  if (lv.span == null || span == null || String(lv.span) !== String(span)) return null;
  return lv.units;
}

const FONT = '12px -apple-system, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif';
const FONT_SM = '11px -apple-system, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif';
// D2-5 死点类型 → 图上的短名。★ 只在**图上**缩（Nova 10-09 00:38 定）：悬停第一行用后台 `death` 的原值，一个字不改写
//   （app.js `boundText`），跟 spec D2-5 的六类逐字对上。认不得的类型不写（不编）。
const DEATH_SHORT = { '趋势背驰': '趋势背驰', '盘整背驰': '盘整背驰', '小转大': '小转大',
  '盘整·未见背驰': '未见背驰', '比不了': '比不了', 'D2-8 补刀': '补刀' };
const DEATH_REAL = new Set(['趋势背驰', '盘整背驰', '小转大']);
// 框编号那几个字母（§八 6，card-c6644f52-2fa）：**加粗、比这一层别的字大半档（14px）**。
// ★★ 这是**看过图之后改的**，改了两处，理由都写在这儿：
//   ① **不用段的方向色**（第一版用绿／红）。绿字母落在 16% 的绿带上、红字母落在 16% 的红带上，
//      混出来的对比度低到看不清 —— 屏上就是一团暗红里几个更暗的红点。字母是**读图的记号**，
//      不是那一段的颜色编码（颜色已经由背景带说了）；这一层里"看得清"的参照是分界那个价格
//      —— 它是**墨色 ＋ 描边**。⇒ 字母跟它同一套：墨色 ＋ 描边。要区分"字母 ≠ 价格数字"靠
//      **加粗 ＋ 大一号**，不靠换个颜色。
//   ② 12px 太小：一枚编号要在满屏 K 线里被一眼找到，跟价格注释一样大就等于没有主次。
// ★ 字号变了 ⇒ `haloText` 那张包围盒表也得跟着变，所以下面那个函数要多收一个 `size`
//   （默认 12，老调用点一个字都不用改）。
const FONT_LET = 'bold 14px -apple-system, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif';
const SIZE_LET = 14;
// 字母表：§八 6 的原文语汇是 `a+A+b+B+c`（一句里最多见两个大写），拿 A…H 够用还有富余。
// ★ 一段里的中枢**超过 8 个**怎么办 —— 这一版**不发明记号**（原文里没有第九个字母这回事）：
//   画满 8 枚就停，超出的部分记在 `state.trendDrawn.num[].over` 里，让工装能看见，等人定。实测
//   ZEC 30m 上每段最多 3 个，这个口子现在够不着。
const TREND_LET = 'ABCDEFGH';
// 小写：**连接段**（§八 6，card-246fc7cf-a9e）。大写说的是"段里**这一个中枢**"，小写说的是
// "**两个中枢之间**那一段"。★ 跟大写**共用一切**：同一个开关（`trendNum`）、同一份框名单
// （下面那个 `zs`）、同一套尺（`FONT_LET`／`SIZE_LET`／同一个 `capMid`）。
//   ★ 为什么名单必须是同一份：§八 6 的语汇是 a A b B c —— 大小写**交替着读**。
//     小写要是另挑一份框，a 和 A 就会来自两套坐标，交替当场断掉，而账面上看不出任何异常。
// 字母表：一句里最多见 a+A+b+B+c，取 a…h 跟 A…H 一样富余（不够的那部分照大写的规矩记账、不发明记号）。
const LOWER_LET = 'abcdefgh';

// >>> SHOWN_LAYERS （tools/web_more_check.py 跟 app.js 的 EARLIER_PAGING 段一起抠出来、在 node 里真跑）
/**
 * 「屏幕上到底画了哪几层」。**画图**和**换档那句话的判据**共用这一份 —— 判据那边不许另写一份过滤：
 * 两份过滤迟早在某一格上错开，那时候判据说的就不是「屏幕上变了」，而是「我心里那份算变了」。
 *
 * ★ 为什么判据要看开关（Nova 2026-10-04 定的口径）：关着的层变了，用户在屏幕上什么也看不见，
 *   那时候喊一句「结构重算了」就是喊狼。判据只比当前打开的那几层。
 * ★ 买卖点**不止一个大开关**：下面还有六个 kind 的 chip（一买…三卖）和「显示待确认」
 *   （未确认的点默认不画）—— 高一级那层同理，跟着自己那个开关。
 */
export function shownOf(opts, data) {
  const o = opts || {}, kinds = o.sigKinds || {};
  // 同级别正式版（载荷 `trend_reading === 'same_level'`）：**「以上级别根本不考虑」**（L38 规则 C）——
  //   不升级、不合成（S6），第 33 课「满 9 段」那种升级框也属于「以上级别」⇒ `up`、`lv` 一律不画，芯片也藏起来
  //   （Nova 10-09 09:07 定：不留半个入口）。地址栏里带着 `up=1` 也一样不画 —— 意愿留着，换回现行口径照常。
  //   ★ 第二个参数**可以不给**（老调用点）：不给就当现行口径，跟改之前一个字不差。
  const sl = !!(data && data.trend_reading === 'same_level');
  return {
    pen: !!o.pen, seg: !!o.seg, pc: !!o.pc, sc: !!o.sc, up: !!o.up && !sl,
    // 走势分段那一层（v3 §八，卡 card-c73ab37d-5a1）：背景带／分界／中阴／待定／撤回／升级框，
    // **一个大开关**管全部 —— 它们是一件事（"这一段怎么走的"）的六个面，拆成六个芯片没人找得齐。
    // ★ 它跟 `cut`（中枢切法）不是一回事，别混：切法决定**中枢**切在哪儿，这一层画的是**走势段**。
    trend: !!o.trend,
    // 框编号（§八 6，card-c6644f52-2fa）：**默认关**的独立一层，但它画在走势那一层里面
    // ⇒ 走势层关着时它也没地方挂（字母说的是"这一段里的第几个中枢"）。两个都开才算画了。
    trendNum: !!o.trend && !!o.trendNum,
    // 级别对照（卡 card-01961644-68f，接口规则 L-9）：合成框跟**对照图**（后台 `ref_tf` 那一档）
    // 中枢对不上的那些，在框右沿标一句。★ 它标的是**合成框**（`T.units`），那一层归 `up` —— 框不画就没有地方挂字
    // ⇒ `lv` 跟 `up` **与**一下（跟 `trendNum` 跟 `trend` 与一下是同一条写法）。默认开。
    lv: !!o.lv && !!o.up && !sl,
    // 单个买卖点画不画：跟下面画三角那一段用的是**同一条**（大开关 ＋ kind chip ＋ 待确认）
    sigAt: (s) => !!o.sig && !!kinds[s.kind] && (!!s.confirmed || !!(o.sigPend && CHART.sig_pending)),
  };
}
// <<< SHOWN_LAYERS

/** 已完成线段（线段中枢只由它们算 —— 未完成段的高低点还会变，full_common 同一条） */
export const doneSegs = (segs) => segs.filter((s) => !s.live);

/**
 * 中枢的横跨区（bar 下标）。两层成员不是同一种东西：
 *   类中枢 host=笔（pens），线段中枢 host=**已完成**线段  ⇒ 别拿 segs[z.PI0] 去取。
 * 返回 {a, b, host, unfinishedJ}；unfinishedJ = host 里那根「还没走完」的成员下标（线段层恒为 null）。
 */
export function hostOf(data, tier) {
  if (tier === 'seg') {
    const done = doneSegs(data.segs);
    return { host: done, unfinishedJ: null };
  }
  const pens = data.pens;
  return { host: pens, unfinishedJ: pens.length - 1 };   // 最后一根笔的终点还会被更极端的分型替换
}

/** 中枢框：这一层要画的那些（`centers` ／ `seg_centers`）。
 *  ★ 形参 `preview`（「先看切后」）2026-10-06 退了（卡 card-3edd7fb3-412）：载荷顶层不再有 `cuts[]`
 *    （spec D4-2 中阴框不断 ⇒ 没有"切开会变成的框"这种来源），那个开关点着**一个像素都不变**。
 *  ★ 退的是**预览那套画法**；`drawFrame` 里「左沿改虚线」那条照旧留着 —— 它读的是 `z.provisional`，
 *    跟开关无关（后台哪天真在 `seg_centers` 上标这个键，它还接得住）。 */
export function boxes(data, tier) {
  const key = tier === 'seg' ? 'seg_centers' : 'centers';
  const { host, unfinishedJ } = hostOf(data, tier);
  const out = [];
  for (const z of data[key] || []) {
    const a = host[z.PI0], b = host[z.PI1];
    if (!a || !b) continue;
    out.push({ z, tier, i0: a.i0, i1: b.i1, unfinishedJ, host });
  }
  return out;
}

/** ★ 这里原本有一个 `pendingCuts`：把载荷顶层 `cuts[]` 里 `status=pending` 的那几刀认到「包住它的
 *  那个旧框」上，给标注层 ③.5 画那条「待定」竖线用。2026-10-06 整段退了（卡 card-3edd7fb3-412）——
 *  载荷不再产 `cuts`（spec D4-2：中阴框不断），这条路没有输入了。
 *  ★ 连带退掉的是一条**规矩**、不是搬走：这里原来立着「切点压在框沿上 ⇒ 只画线、不挂签」，理由是
 *    **那一刀不改这个框**（改的是它后面那一组从哪儿重算），挂「待定」会读成"这个框要被切"——正好是反的。
 *    v3 里框不再被切 ⇒ 这条规矩**失去了前提**。将来谁要再引入「框被切」的路，先回来看这一句。
 *  ★ 「待定」这件事**没有丢**：v3 自己那一条（`trend.pending`，见 `trendMarkView` ②）接住了它，
 *    位置守卫落在 `tools/web_measure_e2e.js`（灰点线必须钉在载荷说的那一根上）。 */

/** 规则 B（full_common.box_split 的同构版）→ {splitAt: bar 下标 | null, solid: bool} */
function boxSplit(z, i0, i1, host, unfinishedJ, iOfBar) {
  const j0 = z.PI0;
  const last = host.length - 1;
  if (unfinishedJ !== null && unfinishedJ !== undefined && j0 <= unfinishedJ && unfinishedJ < Math.min(j0 + 3, host.length)) {
    return { splitAt: null, solid: false };            // ① 前三里夹着没走完的 ⇒ 整框虚线
  }
  if (!z.live) return { splitAt: null, solid: true };  // ② 已结束 ⇒ 整框实线
  return { splitAt: iOfBar(host[Math.min(j0 + 2, last)].i1), solid: true };  // ③ 仍在延续 ⇒ 拆两截
}

function viewport(chart, series, data) {
  const ts = chart.timeScale();
  const n = data.bars.length;
  const tOfBar = new Array(n);
  for (let i = 0; i < n; i++) tOfBar[i] = data.bars[i].t / 1000;
  const xOfBar = (i) => { const x = ts.timeToCoordinate(tOfBar[i]); return x === null ? null : x; };
  const yOfPrice = (p) => series.priceToCoordinate(p);
  let spacing = 6;
  if (n > 1) {
    const x0 = ts.timeToCoordinate(tOfBar[n - 1]), x1 = ts.timeToCoordinate(tOfBar[n - 2]);
    if (x0 !== null && x1 !== null) spacing = Math.max(2, Math.abs(x0 - x1));
  }
  return { xOfBar, yOfPrice, spacing, tOfBar };
}

// ★ x 拿不到（时间不在数据里）⇒ 不画；**不夹回画布** —— 把屏幕外的两端夹到 0 / W 会把一个
//   窗口外的中枢拉成一条横贯全图的线（踩过一次）。画布自己会裁掉越界部分，那才是「滚出去了」的样子。
const onScreen = (x, W, pad = 0) => x !== null && x >= -pad && x <= W + pad;

// ---------------------------------------------------------------------------
// 幽灵点的**命中格**（卡 card-cf3ed018-795）。画布上的东西没有 DOM，悬停得自己做 ——
// 这一处只管「指针在不在某个幽灵上」，坐标换算留在**知道画布坐标系的地方**：
// `ctx.canvas` 是这个窗格的画布，`useMediaCoordinateSpace` 给的 mediaSize 就是它的 CSS 像素，
// 所以「客户端坐标 − getBoundingClientRect」正好落在同一个系里。app.js 那边只管把鼠标位置递进来、
// 把说明摆出来，一行换算都不做（换算抄两份，迟早在某一格上错开）。
// 每次画完由 `makeAnnotPrimitive` 重填；没有幽灵时是空数组 ⇒ 恒不命中。
export const ghostHits = { boxes: [], canvas: null };
export function ghostHitAt(clientX, clientY) {
  const c = ghostHits.canvas;
  if (!c) return null;
  const r = c.getBoundingClientRect();
  const x = clientX - r.left, y = clientY - r.top;
  for (const b of ghostHits.boxes) if (x >= b[0] && x <= b[2] && y >= b[1] && y <= b[3]) return b[4];
  return null;
}

// 分界（竖虚线）的**命中带**（卡 card-22888623-1a7）。跟 `ghostHits` 是同一套账：画布上的东西没有
// DOM，悬停得自己做；坐标换算只留在知道画布坐标系的地方（app.js 那边一行都不抄）。
// ★ 为什么是"带"、不拿那根线当靶子：分界是 `lineWidth 1.5` 的**竖虚线**，拿 1.5px 当悬停目标
//   等于瞄不中（手机上更别提）。**带只放宽命中，画法一个像素不动** —— 这是 Nova 10-06 拍的口径
//   （「只放宽悬停范围、看上去不变，不算另做样式」）。
// ★ 带里记的是**整条 bound**，不是某句话：哪一条该出哪句话是 app.js 的事（判据一处出处）。
//   这一层只管"指针压在哪一根上"，将来别的分界要加说明，这里一个字都不用改。
// ★ 竖线是**满高**的 ⇒ 只比 x，不比 y（y 怎么都在带子里）。
export const boundHits = { bands: [], canvas: null };
export function boundHitAt(clientX, clientY) {
  const c = boundHits.canvas;
  if (!c) return null;
  const r = c.getBoundingClientRect();
  const x = clientX - r.left;
  for (const b of boundHits.bands) if (x >= b.x0 && x <= b.x1) return b.bound;
  return null;
}

// ---------------------------------------------------------------------------
// 框层：类中枢（与笔同色）→ 线段中枢（与线段同色）→ 各自的「↑高N级」框
// 挂在 K 线系列上、zOrder=bottom ⇒ 画在 K 线底下，跟 Python 的落笔次序一致（框先、K 线后）。
// 盘整组标签的**命中格**（卡 card-9f7a80b6-e8a）：跟 `ghostHits` 同一套账，只登记那两块 chip
// （细轨、刻度不当靶子 —— 一条 2px 的线瞄不中，而它们说的是同一件事）。每帧由标注层重填。
export const pzHits = { boxes: [], canvas: null };
export function pzHitAt(clientX, clientY) {
  const c = pzHits.canvas;
  if (!c) return null;
  const r = c.getBoundingClientRect();
  const x = clientX - r.left, y = clientY - r.top;
  for (const b of pzHits.boxes) if (x >= b[0] && x <= b[2] && y >= b[1] && y <= b[3]) return b[4];
  return null;
}

// >>> PZ_GROUPS
/** 相邻盘整段 → 组（`走势分段.md` §八 第 9 条，小栋 10-07 选 C：**分界一条不动**，只在图上标成一组）。
 *  ★ 口径三条，都不是这儿定的，照抄：
 *    ① `type === '盘整'` 才算（「升级·盘整」的 type 也是盘整 ⇒ 算进；「无中枢」不算）；
 *    ② **图头不算**（第一把刀之前那段是被窗口截断的，方向都未定 —— D2-1／D6-3；
 *       Atlas `notes/b5/pz_merge.py` 的 `pairs()` 同样跳过 `head`，14 组 / 60 段就是这么数的）；
 *    ③ 连着 ≥2 段才成组。
 *  返回 [{ from, to, n, i0, i1, ends }]：`ends[k]` ＝ 组内第 k+1 段的右端 bar（最后一个就是组尾）。 */
export function pzGroups(T) {
  const segs = (T && T.segments) || [];
  const ok = (s) => s.type === '盘整' && !s.head;
  const G = [];
  for (let i = 0; i < segs.length;) {
    if (!ok(segs[i])) { i++; continue; }
    let j = i;
    while (j + 1 < segs.length && ok(segs[j + 1])) j++;
    if (j > i) G.push({ from: i, to: j, n: j - i + 1, i0: segs[i].i0, i1: segs[j].i1,
      starts: segs.slice(i, j + 1).map((s) => s.i0), ends: segs.slice(i, j + 1).map((s) => s.i1) });
    i = j + 1;
  }
  return G;
}

/** 视野 `[a, b]`（bar 下标，可以是小数）落在组里的哪几段：三个集合是**划分** ⇒
 *  `before + (hi − lo + 1) + after === n`（屏内一段都没有时 lo = hi = 0、中间那项记 0）。
 *  这条恒等式就是这段计数的自检（工装照着它断言；出图那一版第一次数错就是靠它抓到的）。 */
export function pzWhere(g, a, b) {
  let before = 0, after = 0, lo = 0, hi = 0;
  for (let k = 0; k < g.n; k++) {
    if (g.ends[k] < a) before++;
    else if (g.starts[k] > b) after++;
    else { if (!lo) lo = k + 1; hi = k + 1; }
  }
  return { before, after, lo, hi, inView: lo ? hi - lo + 1 : 0 };
}
// <<< PZ_GROUPS

// ---------------------------------------------------------------------------
export function makeBoxPrimitive(state) {
  return {
    attached(p) { this._chart = p.chart; this._series = p.series; this._request = p.requestUpdate; },
    detached() {},
    updateAllViews() {},
    paneViews() {
      return [{
        zOrder: () => 'bottom',
        renderer: () => ({
          draw: (target) => {
            // 验收用只读出口（跟 `state.labelBoxes` 同性质，只读不改画）：**这一帧**交给画框函数的清单。
            // ★ 每帧开头**重写**（不是 push）：一次 draw 可能因为多窗格/重绘跑好几趟，累积着记的话
            //   同一个框会被记好几遍 —— 工装量「同一个 (层,i0,i1) 只许出现一次」时会**假红**。
            state.boxesDrawn = [];
            const { data, opts } = state;
            if (!data || !this._chart) return;
            const sh = shownOf(opts, data);        // 开关只在这里读一次（判据那半边走的是同一个函数）
            target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
              const W = mediaSize.width;
              const vp = viewport(this._chart, state.candleSeries || this._series, data);
              // C+（卡 card-06d7f9a1）：第 2 条分界线**之前**的那一片框整体降一档 —— 那片的位置会随
              //   窗口起点变。阈值只算一次，两个 tier 共用（判据跟层无关，别在两处各推一遍）。
              const cutBar = willChangeCut(data);
              for (const tier of ['pen', 'seg']) {              // 类中枢先、线段中枢后
                const on = tier === 'seg' ? sh.sc : sh.pc;
                if (!on) continue;
                const col = tier === 'seg' ? CHART.seg : CHART.pen;
                const w = tier === 'seg' ? WIDTH.sc : WIDTH.pc;   // 框线宽跟 TradingView 调用点走（卡面口径）
                const fill = tier === 'seg' ? CHART.sc_fill : CHART.pc_fill;
                for (const bx of boxes(data, tier)) {
                  const x0 = vp.xOfBar(bx.i0), x1 = vp.xOfBar(bx.i1);
                  const yt = vp.yOfPrice(bx.z.ZG), yb = vp.yOfPrice(bx.z.ZD);
                  if (x0 === null || x1 === null || yt === null || yb === null) continue;
                  const { splitAt, solid } = boxSplit(bx.z, bx.i0, bx.i1, bx.host, bx.unfinishedJ, (i) => vp.xOfBar(i));
                  // 卡 card-e346ede6-996：`provisional`（这个框是从一个**还没立住**的切点之后重算出来的）
                  // ⇒ **左沿**改虚线。为什么是左沿：那个切点就是它的起点（起点一撤，整个框回并进原来那个大框）。
                  // ★ 2026-10-06：从前这儿还跟着一句「「待定」那根切点和签不在这儿画，在标注层 ③.5」——
                  //   那条路退了（卡 card-3edd7fb3-412），标注层整个 ③.5／③.6 都撤了。这条判定本身
                  //   **留着**：它读的是载荷的 `z.provisional`，跟「先看切后」那颗开关无关。
                  const openL = !!bx.z.provisional;
                  // C+：**整格落在第 2 条分界线之前**才算「会变」。判据取 `i1`（右沿）——
                  //   框是「这一段在哪儿」的画法，只要它的尾巴还压在会变的那片里，读者就不能拿它当定论。
                  //   ★ 严格不等号：`i1 === cutBar` 的框右沿正好停在分界线上，那片是**定住**的。
                  const wc = bx.i1 < cutBar;
                  const fade = wc ? TREND.willChangeFade : 1;
                  drawFrame(ctx, x0, yt, x1, yb, col, w, fill, splitAt, solid, W, openL, fade);
                  // 只记**底下那个框**：升级框跟它同 i0/i1，记进去会让「同一格只许出现一次」这把尺子
                  // 把自己量红（它们本来就是同一个框的另一种说法，不是画了两遍）。
                  // `willChange` 一并记下：验收要能问「这格该淡不该淡」，靠肉眼数框数不出来。
                  //   ★ 记的是**事实**（`wc`），不是「淡没淡」—— 哪天把 `willChangeFade` 调成 1，
                  //     这一格照样说得出「这些框本来是会变的那一批」。
                  state.boxesDrawn.push({ tier, i0: bx.i0, i1: bx.i1, provisional: openL, willChange: wc });
                  if (sh.up && bx.z.up && bx.z.up.length) {
                    for (const u of bx.z.up) {                  // 高一级别：满 9 段（第 33 课）
                      const uyt = vp.yOfPrice(u.ZG), uyb = vp.yOfPrice(u.ZD);
                      if (uyt === null || uyb === null) continue;
                      const ucol = upColor(tier);
                      // 升级框**不跟着拆两截**：高一级的「前三笔」没有定义（Python 同）
                      // 升级框跟它下面那个框同命：底下那个是 provisional，它也是（同一个切点撑着的）
                      // 升级框跟底下那个框**同一个 i0/i1** ⇒ 同一个 fade，不另算（它对「靠不靠得住」的
                      //   判断跟底框是同一件事；两处各算一遍就会出现半深半浅的一个框）。
                      drawFrame(ctx, x0, uyt, x1, uyb, ucol, w, CHART.up_fill, null, !bx.z.live, W, openL, fade);
                    }
                  }
                }
              }
            });
          },
        }),
      }];
    },
  };
}

/** `openL`（可缺省）＝ 左沿是不是「还没立住的切点」（provisional，卡 card-e346ede6-996）⇒ 左沿改虚线。
 *  只动**左沿那条竖线**，不整框变虚：这个框的价位区间和右端都还是真的事实，不确定的只有起点。
 *  ★ 为什么不整框虚：**整框虚/尾截虚已经是「未完成」的信号**（`boxSplit` 那三种），再叠一层就没法分了。 */
function drawFrame(ctx, x0, ytop, x1, ybot, col, width, fillAlpha, splitAt, solid, W, openL, fade = 1) {
  if (x0 > x1) [x0, x1] = [x1, x0];
  const y0 = Math.min(ytop, ybot), y1 = Math.max(ytop, ybot);
  // 填充整块只铺一次（Python 的注释：两截各铺一遍会在分界处叠出一条深缝）
  // `fade`（可缺省 1）＝ C+ 那一档「会变」的整体降权（卡 card-06d7f9a1）：**框线 ＋ 填充同乘**。
  //   ★ 为什么乘、不换色：形状和色相都要留着 —— 变的只是「这个位置靠不靠得住」，
  //     不是「这是另一种框」。换色会让人以为多了一个类别（§八 1 立过的账）。
  //   ★ 也不改成灰点线：灰点线在这一层**已经有主**（「待定」§八 3、「撤回」§八 4），再借一次
  //     三件事就糊成一件了。
  ctx.fillStyle = rgba(col, fillAlpha * fade);
  ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
  ctx.strokeStyle = rgba(col, 235 * fade);
  ctx.lineWidth = width;
  const split = splitAt !== null && splitAt !== undefined && splitAt > x0 && splitAt < x1 ? splitAt : null;
  const solidL = !!solid && !openL;                                  // 左沿：'provisional' ⇒ 虚（见上面那句）
  const edges = split === null
    ? [[x0, y0, x1, y0, solid], [x0, y1, x1, y1, solid], [x0, y0, x0, y1, solidL], [x1, y0, x1, y1, solid]]
    : [[x0, y0, split, y0, true], [x0, y1, split, y1, true], [x0, y0, x0, y1, solidL],
       [split, y0, x1, y0, false], [split, y1, x1, y1, false], [x1, y0, x1, y1, false]];
  for (const [ax, ay, bx, by, so] of edges) {
    ctx.setLineDash(so ? [] : DASH.box);
    ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke();
  }
  ctx.setLineDash([]);
}

// ---------------------------------------------------------------------------
// 标注层：价签（实底 + 黑字）、线段端点的圈、买卖点三角、未收盘那根
// 挂在最后加的线段系列上、zOrder=top ⇒ 压在 K 线与线段之上，跟 Python「标签最后画」一致。
// ---------------------------------------------------------------------------
export function makeAnnotPrimitive(state) {
  const placed = [];                       // 这一帧已经占位的文字框：先到先得，重叠就往上挪
  state.labelBoxes = placed;               // 验收用只读出口（跟 app.js 的 `window.__app` 同性质，只读不改画）：
                                           // 「文字之间零重叠」这条判据要**量**，不能靠眼睛 —— 拿这张表两两求交。
                                           // ★ 仓里没有这把尺：量它要真浏览器，而仓里不带 playwright 依赖
                                           //   （见 web/README.md「三把尺」那一节的分工）。
  return {
    attached(p) { this._chart = p.chart; this._series = p.series; },
    detached() {},
    updateAllViews() {},
    paneViews() {
      return [{
        zOrder: () => 'top',
        renderer: () => ({
          draw: (target) => {
            const { data, opts } = state;
            if (!data || !this._chart) return;
            const sh = shownOf(opts, data);        // 开关只在这里读一次（判据那半边走的是同一个函数）
            target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
              const W = mediaSize.width;
              const H = mediaSize.height;   // 视口下沿 —— 夹框/避让要两头都不出画布（见 fitBox）
              const vp = viewport(this._chart, state.candleSeries || this._series, data);
              placed.length = 0;

              // ① 线段端点：顶红底绿（full_common 的 ellipse，半径 9 / 描边 4）
              if (sh.seg) {
                // 暂定那一刀 V 同时是暂定段的终点和后面那一截的起点 ⇒ 只画一个圈（虚线那个）；
                // 两个都画，实线小圈套在虚线圈里，看着像齿轮（实测截图）。
                const tentEnds = new Set(data.segs.filter((s) => s.tentative).map((s) => `${s.i1}|${s.p1}`));
                // D-3 C：有 `segs_std` 时端点圈跟着标准化那一套走（图上的线段是哪套，圈就画在哪套的端点上），未完成段照旧取原始的
                const segsDrawn = Array.isArray(data.segs_std) && data.segs_std.length ? data.segs_std.concat(data.segs.filter((s) => s.live)) : data.segs;
                for (const s of segsDrawn) {
                  const end = segEnd(data, s);
                  const pts = [[s.i0, s.p0], [end.i, end.p]];
                  const up = s.dir === 'up';
                  for (const [k, [i, p]] of pts.entries()) {
                    const x = vp.xOfBar(i), y = vp.yOfPrice(p);
                    if (!onScreen(x, W, 20) || y === null) continue;
                    const tent = k === 1 && s.tentative;
                    if (k === 0 && tentEnds.has(`${i}|${p}`)) continue;
                    // ★ 未完成段的末端**不画圈**（card-23700ca2-307，Nova 10-08 16:06 定）：那一点只是「迄今的极值」，
                    //   还会被更极端的取代。画个实线圈就跟定了的端点长得一样；虚线圈又已经是「暂定」那一刀的记号，
                    //   不能再拿来表示「未完成」（两个意思撞在一起）。暂定段的终点是 V，照旧画虚线圈。
                    if (k === 1 && s.live && !s.tentative) continue;
                    const col = (k === 0 ? up : !up) ? CHART.buy : CHART.sell;
                    ctx.beginPath(); ctx.arc(x, y, tent ? 7 : 4.5, 0, Math.PI * 2);
                    ctx.fillStyle = PAGE.bg; ctx.fill();
                    ctx.strokeStyle = col;
                    ctx.lineWidth = tent ? 1.6 : 2;
                    // ★ 暂定的那一刀（S7 当场判、结局未定）：**虚线圈、大一号**，旁边小字「暂定」。
                    //   实线圈＝定了的端点；虚线圈＝先画出来的一刀，等第一笔两头谁先被破（S12）再定。
                    //   字放在圈外、远离线段那一侧（顶往上、底往下），登记 placed，后面的价签会避开它。
                    if (tent) ctx.setLineDash([3.2, 2.3]);   // 2/2 在这个半径上像齿轮（实测截图），拉长成 7 段左右
                    ctx.stroke();
                    if (tent) {
                      ctx.setLineDash([]);
                      const top = up;                        // 段向上 ⇒ 终点是顶（字往上）；向下 ⇒ 终点是底（字往下）
                      placed.push(haloText(ctx, x, top ? y - 12 : y + 22, '暂定', col, 'center').slice(0, 4));
                    }
                  }
                }
              }

              // ①b D-3 C：标准化线段的**最后一条**（app.js 画成短虚线）在它的终点旁写「终点还可能挪」（Nova 10-09 13:08）。
              //    短虚线（可能挪）跟未完成段的长虚线挨在一起，光靠虚线疏密分不出来 —— 照 D-3 示意图写一个字。
              //    字放在圈外、离开线段那一侧（终点是顶往上、是底往下），登记 placed，价签会避开它（跟「暂定」同一条）。
              state.segStdLabel = null;
              if (sh.seg && Array.isArray(data.segs_std) && data.segs_std.length) {
                const L = data.segs_std[data.segs_std.length - 1], x = vp.xOfBar(L.i1), y = vp.yOfPrice(L.p1);
                if (onScreen(x, W, 20) && y !== null) {
                  const top = L.dir === 'up';
                  const box = haloText(ctx, x, top ? y - 12 : y + 22, '终点还可能挪', CHART.seg, 'center');
                  placed.push(box.slice(0, 4));
                  state.segStdLabel = { x: Math.round(x), y: Math.round(y), box: box.slice(0, 4).map(Math.round), text: box[4] };
                }
              }

              // ② 买卖点：**这一步只画三角**，文字留到 ④（判据在 core/signals.py，前端只画）
              //    ★ 次序是 2026-10-03 改的，改的就是次序：
              //      Python 在 chart_full_smooth.py:68 先 `draw_signals()` 画三角，然后把文字标签请求
              //      **并进 `center_labels`**，:72 跟中枢价签**同一次** `draw_labels(d, center_labels, f_n, CY, placed)`
              //      画出来 ⇒ ① 文字最后画、**压在三角上面**；② 买卖点文字和中枢价签**共用一个 placed**、互相避让。
              //      网页原来把「三角 ＋ 文字」一起放在价签**之后**画 ⇒ 三角压在价签上，价签数字被盖掉
              //      （390px 实测：倒三角把 `[1004, 1682]` 中间两位整个吃掉）。搬的时候丢了「文字走同一个注册表」这半。
              // ★★ 这一层**不许**再包一层 `if (sh.sig)`：`shownOf()` 只给 `sigAt`，大开关就在它里面。
              //    2026-10-04 我在这儿写过一次 —— 那个键根本不存在 ⇒ 恒为假 ⇒ 买卖点**整层一颗不画**，
              //    而工装里「切看法后屏幕的像素变了」照样绿（量到的是买卖点的**文字**，是替身）。
              //    判据一处就够：每颗点过一遍 `sigAt`。
              const sigs = [];
              for (const tier of ['seg', 'pen']) {
                // ★ M29（买卖点.md:106，L53）：小转大那一刀的二类放在走势层 `trend.xzd_seconds`，不在 signals 里（J12：signals 不读分界）。
                //   画法、开关、避让都跟段级买卖点同一条路：过同一个 sigAt（大开关＋「二买／二卖」芯片），三角同一个样子，
                //   只是字不一样（见 sigLabel）。
                const extra = tier === 'seg' ? (data.trend?.xzd_seconds || []) : [];
                for (const s of [...(data.signals?.[tier] || []), ...extra]) {
                  if (!sh.sigAt(s)) continue;   // 大开关 ＋ kind chip ＋ 待确认，全在 shownOf 里
                  const x = vp.xOfBar(s.bar), y = vp.yOfPrice(s.price);
                  if (!onScreen(x, W, 40) || y === null) continue;
                  sigs.push({ x, y0: drawSignalGlyph(ctx, x, y, s, tier), s, tier });
                }
              }

              // ②.5 幽灵点（卡 card-cf3ed018-795）：本次打开期间**确认过、后来又没了**的买卖点。
              //   ★ 名单是 app.js 比的（它才知道上一份是什么、桶是什么），这儿只管画 —— 画图这一层
              //     不许自己判断"少没少"：判据一处就够，两份迟早在某一格上错开。
              //   ★ 画在活点**之后**：两批点按构造不会重合（幽灵的定义就是"活的那份里没有它"），
              //     但万一引擎在同一个 bar 上换了个 kind，后画的活点应当压过作废的那个。
              //   ★ 幽灵也走 `sigAt`：买卖点整层关着、或者某一类 kind 的芯片关了、就不画它 ——
              //     层关着还往外画东西，那就不是开关的语义了（跟「关着的层不算看得见」同一条账）。
              ghostHits.canvas = ctx.canvas;
              ghostHits.boxes = [];
              for (const g of data.ghosts || []) {
                if (!sh.sigAt(g)) continue;
                const x = vp.xOfBar(g.bar), y = vp.yOfPrice(g.price);
                if (!onScreen(x, W, 40) || y === null) continue;
                ghostHits.boxes.push([...drawSignalGhost(ctx, x, y, g, g.tier), g]);
              }

              // ②.9 C+（卡 card-06d7f9a1）：「会变」**只标一次** —— 标在最靠右的那个淡框的**框内右上角**。
              //   为什么只一次：这一片框淡下去交代的是**同一件事**（"这一片的位置会随窗口起点变"）。
              //     每个框都挂一个字，除了把图面糊满，还会读成"每个框各有一条不同的理由"。
              //   为什么取最靠右（`i1` 最大）的那个：它离分界线最近，是这一片的**内边界** ——
              //     标在那儿，读者顺着往左看，自然读出"往左这一串都打折"。
              //   ★ 用 `haloText` 不是 `tag()`：`tag()` 是这一层的**实价签**（实底 ＋ 黑字），
              //     价钱是这张图最响的一档，一句说明不该跟它抢。层级：价签 ＞ 这个字。
              //   ★★ "挑最靠右的那个"要加个前提：**那个框的右上角装得下这句话**。两条硬条件 ——
              //     ① 字得整个落在屏内（标一半等于没标）；② 不压格顶那条**「等确认」带**（§八 3 的东西，
              //     两件事叠在一处就分不清哪个字在说哪件事）。装不下就往左退一个淡框 —— 退到的那个
              //     还在同一串里，说明的还是同一件事；**一个都不合格就干脆不标**，不把字拖到边上凑
              //     （同 `fitBox` 那条"落点看不见就不画"的老账）。
              //   ★ 右沿**滚出屏外**不算不合格：那种框右边还有一大截在屏内，字贴着**屏右沿**里面画，
              //     照样落在框里（框内的右端就是它）。反而是"右沿刚出屏就整句不标"会让读者看着一片
              //     淡框找不到一句解释 —— 那是这条规矩唯一会伤到人的地方。所以夹的是**右沿本身**。
              {
                const WC = '会变';
                const cut = willChangeCut(data);
                ctx.font = FONT;                                  // ★ 量宽必须用 haloText 那一套字体
                const tw = ctx.measureText(WC).width;
                const yMin = TREND.hatchTop + TREND.hatchH + 2;   // 「等确认」那条带的下沿
                let pick = null;
                for (const tier of ['seg', 'pen']) {
                  if (!(tier === 'seg' ? sh.sc : sh.pc)) continue;
                  for (const bx of boxes(data, tier)) {
                    if (bx.i1 >= cut) continue;                        // 定住的那一片，不标
                    const bx1 = vp.xOfBar(bx.i1), yt = vp.yOfPrice(bx.z.ZG);
                    if (bx1 === null || yt === null) continue;
                    const xr = Math.min(bx1, W) - 8;
                    if (xr - tw < 8) continue;                         // ① 左沿留不下 ⇒ 这个框装不下
                    if (yt + 1 < yMin || yt + 15 > H) continue;        // ② 竖向也得出得来
                    if (!pick || bx.i1 > pick.bx.i1) pick = { tier, bx, xr, yt };
                  }
                }
                if (pick) {
                  const col = pick.tier === 'seg' ? CHART.seg : CHART.pen;
                  // 字落在**框内**：右沿退 8，基线压在框顶下 12（12px 那套的框顶在基线 −11 ⇒ 离框顶 1 px）。
                  //   ★★ 这个字用**满墨**（`col`），不乘 `willChangeFade` —— 试过，都画出来比过：
                  //     跟着框一起淡（0.55）跟淡一档（0.80）在 1 倍下都糊进框里，读不出来；满墨那一版
                  //     一眼就认得。为什么满墨不算抢：这一层最响的一档是**实底 ＋ 黑字**的价签，
                  //     这个字是 halo 字、两个字、小号，排在价签下面一档 —— 层级没乱（见上一条）。
                  //   ★ 基线**显式写上**：`haloText` 自己不设 `textBaseline`，而上面的 `tag()` 把它设成
                  //     `'middle'` 就没再改回来 —— 也就是说这里读到的是**上一位留下的**值。今天量出来是
                  //     `'alphabetic'`（所以图是对的），但这是碰巧：换个画法、换个次序，这个字会自己往上
                  //     挪半行，而且**不报错**。要的是「框顶下 1 px」这个确定的位置，就得自己把它钉住。
                  ctx.textBaseline = 'alphabetic';
                  placed.push(haloText(ctx, pick.xr, pick.yt + 12, WC, col, 'right').slice(0, 4));
                  //   ★ 推 `placed` 是让后面的**价签避让它**（跟 `tag()` 同一条账：画的框＝登记的框）。
                }
              }

              // ③ 价签：线段中枢先（优先占位），类中枢后；升级标签跟着各自的框走
              //    （跟 Python 同序：`center_labels` 里价签在前、买卖点文字在后 ⇒ 价签优先占位）
              for (const tier of ['seg', 'pen']) {
                const on = tier === 'seg' ? sh.sc : sh.pc;
                if (!on) continue;
                const col = tier === 'seg' ? CHART.seg : CHART.pen;
                for (const bx of boxes(data, tier)) {
                  const x = vp.xOfBar(bx.i0), y = vp.yOfPrice(bx.z.ZG);
                  if (!onScreen(x, W, 8) || y === null) continue;   // 框滚出去了，价签也跟着走
                  tag(ctx, placed, x + 8, y - 8, `[${fmtG(bx.z.ZD)}, ${fmtG(bx.z.ZG)}]`, col, W, H);
                  if (sh.up && bx.z.up) {
                    for (const u of bx.z.up) {
                      const uy = vp.yOfPrice(u.ZG);
                      if (uy === null) continue;
                      const ucol = upColor(tier);
                      tag(ctx, placed, x + 8, uy - 8, `↑高${'一两三四'[u.up - 1]}级 [${fmtG(u.ZD)}, ${fmtG(u.ZG)}]`, ucol, W, H);
                    }
                  }
                }
              }

              // ③.5 切点记号 ／ ③.6 「随切点」（卡 card-e346ede6-996）：**2026-10-06 整段退了**
              //   （卡 card-3edd7fb3-412）。载荷顶层不再有 `cuts[]`（spec D4-2：中阴框不断）⇒ 既没有
              //   "待定的刀"可标、也没有"切开会变成的框"可画；「先看切后」那颗开关点着**一个像素都不变**
              //   （本机探针连跑 3 次数过逐层像素），却还在**默认那一档**上撒谎（title 写着"把没立住的那几刀
              //   画成切开的框"）—— 开关和这套画法一起退。
              //   ★ 「待定」这件事**没有丢**：v3 自己那一条（`trend.pending`，见 `trendMarkView` ②）接住了
              //     它 —— 那是**整屏高**的灰点线，说的是"这里是候选极值"；旧的 ③.5 是**框高**、说的是
              //     "这个框要被切"。v3 只剩前一层意思，画法本来就该换，不是原样搬过去的。
              //   ★ 量法挪了个地方：`tools/web_measure_e2e.js` 里新补的那一格钉的就是"灰点线落在载荷
              //     那一根上"（原来钉这件事的是 ghost ⑰e，它量的是 `cuts[]` 这条路，跟着一起退了）。

              // ④ 买卖点**文字**：最后画，跟价签共用 `placed` ⇒ 文字之间互相避让、价签也避开它；
              //    压在三角上面 ⇒ 数字/字完整可读（与 Python 出图的结论一致）。
              //    `y0` 是②里画三角时算出来的底边 —— 传过来，免得「文字挂在哪条边」这个式子写两份。
              for (const g of sigs) drawSignalText(ctx, placed, g.x, g.y0, g.s, g.tier, H);

              // ④.5 盘整组（卡 card-9f7a80b6-e8a，小栋 10-07 选 C；`走势分段.md` §八 第 9 条）
              drawPzGroups(ctx, state, sh, vp, placed, this._chart, W, H);

              // ⑤ 未收盘的最后一根：虚线框 + 「未收盘」（Python dashed_rect + 琥珀字）
              //    ★ 这一句**不登记 placed** —— 跟 Python 一致：那边它也是直接画的、不在 draw_labels 里
              //      （所以 Python 图上「未收盘」会压在线段端点的圈上）。照搬，不擅自"顺手修好"。
              if (!data.closed && data.bars.length) {
                const i = data.bars.length - 1, b = data.bars[i];
                const x = vp.xOfBar(i), yh = vp.yOfPrice(b.h), yl = vp.yOfPrice(b.l);
                if (x !== null && yh !== null && yl !== null) {
                  const hw = Math.max(3, Math.min(24, vp.spacing / 2));
                  ctx.setLineDash(DASH.liveBox);
                  ctx.strokeStyle = CANDLE.open; ctx.lineWidth = 1.5;
                  ctx.strokeRect(x - hw - 1, yh - 6, hw * 2 + 2, yl - yh + 12);
                  ctx.setLineDash([]);
                  ctx.font = FONT_SM; ctx.fillStyle = CANDLE.open; ctx.textAlign = 'right';
                  ctx.fillText('未收盘', x - hw - 8, yl + 14);
                  ctx.textAlign = 'left';
                }
              }
            });
          },
        }),
      }];
    },
  };
}

// ---------------------------------------------------------------------------
// 走势分段那一层（v3，`docs/spec/走势分段.md` §八；卡 card-c73ab37d-5a1）
//
// 载荷：顶层 `trend` ＝ {bounds, retracted, pending, segments, units}。**只有 `cut=trend` 那一趟才有**
// （`cut=extend` 那份连这个键都没有 —— web/check_parity.py 两头各钉了一条断言）；没有就一笔不画。
//
// 分两层画，跟框层／标注层同一条理由（真像素量过：一根竖虚线画在框层那种位置会被密集 K 线整个吃掉，
// 同一个记号在空背景上读得出、压在 K 线上就没了 —— 那条账原来记在标注层 ③.5，2026-10-06 ③.5 退了，
// 结论照旧，见卡 card-3edd7fb3-412）：
//   · **背景带 ＋ 中阴那条斜线 ＋ 升级框** 挂 `bottom`（压在 K 线底下，跟 Python 落笔次序一致）；
//   · **分界竖虚线 ＋ 极值那个点 ＋ 价格 ＋ 待定／撤回 ＋「升级」二字** 挂 `top`（压在 K 线之上）
//     —— 一根竖虚线画在底下会被密集 K 线整个吃掉，那就等于没画。
// ---------------------------------------------------------------------------
const trendOf = (data) => {
  const T = data && data.trend;
  return T && Array.isArray(T.segments) ? T : null;
};

/** C+（卡 card-06d7f9a1-3ad，小栋 06:41Z 选）：**第 2 条分界线之前**的那一片框，位置会随窗口起点变。
 *  返回「第 2 条分界线落在哪一根」这个阈值。★ **分界线少于 2 条 ⇒ `Infinity`** —— 那意味着
 *  一个框都不受「第 2 刀之后」保护 ⇒ 卡面原话「所有框都算」自动成立，调用侧不必再写一支。
 *  ★ 调用侧一律用**严格不等号** `bx.i1 < 阈值`：正好压在第 2 条分界线上算**不会变**
 *    （沿用 card-e634f6e9-bb5 定下的口径：压边合法、共端点≠交叠；跨周期那一套判据一律严格）。
 *  ★ 降的只是**框线 ＋ 框填充**，**第 1 条分界线本身照常画**（小栋选的是不动它）。
 *  ★ 为什么读 `bounds[1]` 而不是 `bounds[0]`：会变的是「第 1 刀之前的一段跟着第 1 刀跳」
 *    （Atlas 26 个起点重算 ZEC 30m：第 2 刀起的线和框 26/26 不变）—— 所以第 2 刀就是分水岭。
 */
export function willChangeCut(data) {
  const T = trendOf(data);
  const bnd = (T && Array.isArray(T.bounds)) ? T.bounds : [];
  return bnd.length >= 2 ? bnd[1].bar : Infinity;
}

export function makeTrendPrimitive(state) {
  return {
    attached(p) { this._chart = p.chart; this._series = p.series; },
    detached() {},
    updateAllViews() {},
    paneViews() {
      return [
        { zOrder: () => 'bottom', renderer: () => ({ draw: (t) => trendBandView(t, state, this) }) },
        { zOrder: () => 'top', renderer: () => ({ draw: (t) => trendMarkView(t, state, this) }) },
      ];
    },
  };
}

/** bottom：走势背景带（§八 1，归「走势分段」）＋ 中阴那条斜线条（§八 3，同）＋ 合成大框
 *  （§八 5，**归「高一级」**）。
 *  ★★ 这一层现在挂着**两个不同的开关**（小栋 10-05 23:3xZ 定，卡 card-113a3b16-026）：
 *    「这一段怎么走的」那一组（背景带／中阴条／分界／待定／撤回）归 `trend`；
 *    合成出来的高一级框归 `up` —— 它跟框层那批"满 9 段"升上来的框**是同一件事**（都是"高一级"），
 *    所以小栋把它挪到那颗芯片底下，`up` 默认关 ⇒ 合成框也跟着默认不画。
 *    ⇒ 所以这儿的早退条件是 `两个都关`，不是 `trend 关`；两个 if 各自管自己那一组。
 */
function trendBandView(target, state, prim) {
  const { data, opts } = state;
  const T = trendOf(data);
  const sh = shownOf(opts, data);
  if (!T || (!sh.trend && !sh.up)) return;
  target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
    const W = mediaSize.width, H = mediaSize.height;
    const vp = viewport(prim._chart, state.candleSeries || prim._series, data);
    // 只读出口（跟 `state.boxesDrawn` 同性质：**这一帧**交给这一层的清单，每帧开头重写）——
    // 「这一层到底画了哪几段、铺的什么色」要**量**，不能靠眼睛。
    state.trendDrawn = { bands: [], bounds: [], pending: [], retracted: [], units: [], num: [], states: [] };

    // ① 走势背景（§八 1）。★★ 10-08 起颜色**跟段型走**（小栋 12:35 选 B，卡 card-fedf32aa-59d）：
    //    上涨＝绿、下跌＝红，**盘整一律灰**（升级·盘整灰深一档）。原文：「盘整哪里有什么方向，只有趋势才有方向」
    //    （L31:217-218）。原先跟分界点类型走 —— 一段从低走到高的盘整涂的是跟上涨**同一个绿**，两者色差为 0，
    //    小栋说「盘整和上涨太难区分」就是这个。「这段从低到高还是从高到低」现在看分界虚线和极值标价。
    //    图头（第一把刀之前）照旧灰；最后一段（还在长）同色更浅（§八 1）。
    const segs = T.segments, bnd = T.bounds;
    // ①② 归「走势分段」那颗芯片。
    if (sh.trend) {
      for (let g = 0; g < segs.length; g++) {
        const s = segs[g];
        const x0 = vp.xOfBar(s.i0), x1 = vp.xOfBar(s.i1);
        if (x0 === null || x1 === null || x1 < 0 || x0 > W) continue;   // 滚出去的那几段不画
        let col, a;
        if (s.head || g === 0) { col = TREND.head; a = TREND.headA; }
        else if (s.type === '上涨' || s.type === '下跌') {
          // ★ 绿和红**不是同一个 alpha**：同一个 16% 在白纸上红本来就比绿实（ΔL* 8.55 vs 6.93），
          //   近黑底上要保住这个差，红得给得比绿多。`theme.js` 里那五个数逐个反解过，别拉齐。
          const up = s.type === '上涨';
          col = up ? TREND.up : TREND.dn;
          a = s.live ? (up ? TREND.liveUp : TREND.liveDn) : (up ? TREND.bandUp : TREND.bandDn);
        } else {
          // 盘整（含升级·盘整、以及后台哪天新加的段型）：没有方向 ⇒ 中性灰。**认不得的段型也落到这里** ——
          //   不知道它往哪去，就不给方向色（不编）。
          col = TREND.head;
          a = s.live ? TREND.rangeLive : (s.upgraded ? TREND.rangeUpA : TREND.rangeA);
        }
        ctx.fillStyle = rgba(col, Math.round(a * 255));
        ctx.fillRect(x0, 0, x1 - x0, H);
        state.trendDrawn.bands.push({ i0: s.i0, i1: s.i1, col, a: +a.toFixed(3), head: !!s.head, live: !!s.live });
      }

      // ② 中阴（§八 3）：极值那一根 → 回抽段终点（载荷的 `pullback_end_bar`）之间，**贴格顶一条窄带**，
      //    里面是 45° 斜线。★ 名字叫「等确认」（小栋 10-05 23:46Z：「没有文字说明」，10-06 定名），
      //    **不写「确立」**（Nova 10-05 16:43／16:48 定）——
      //    那一根不是"实时确立"的那一根：线段要等后面的 K 线才算走完，实时确立比它晚一截。
      //    ★ 形状说破一句：是**一条斜线填充的窄带**，不是"一条从左下斜到右上的连线"。两个字很容易读错。
      //
      //    ★★ **原来贴格底，现在贴格顶**（卡 card-60678062-8c2，小栋原话「挡住了交易量」）。
      //      成交量是挂在**主图下沿**的（`volSeries` 的 `scaleMargins.top = 0.82`，`app.js:161`），
      //      而这条带原先铺在 `H - hatchH` —— 正好压在成交量柱头上。挪到顶上就不相交了。
      //      ★ **跟成交量那颗开关无关**：关着也放顶部。位置跟着开关跳的话，同一个东西会有两个地方，
      //        截出来的两张图也说不清哪张是哪张。
      //      ★ 待定（`pending`）跟中阴**走同一个 `strip()`**，所以它一起挪 —— 它俩是同一个器件
      //        （极值已出、还没立住），压在成交量上这件事对两条**一样真**；只挪一条的话，
      //        屏上会同时有两个"斜线条"，底下的那个照样压着成交量。
      //        （撤回不在这一支：它是 `trendMarkView` 里的灰点线，本来就没铺带子。）
      const hatch = hatchFill(ctx);
      const strip = (i0, i1, key) => {
        // ★ 同级别正式版的 S5 刀（盘整相连）**没有** `pullback_end_bar`：它是两个已经走完的中枢之间的接缝，
        //   没有「极值已出、还没立住」那一截，也就没有中阴。缺这个键就不铺 —— 不缺省、不猜。
        //   （不挡的话 `xOfBar(undefined)` 一路传进 LWC，抛 `reading 'year'`，整层分界都画不出来；4d09f3b 真载荷实测踩到。）
        if (i0 == null || i1 == null) return;
        const x0 = vp.xOfBar(i0), x1 = vp.xOfBar(i1);
        if (x0 === null || x1 === null || x1 < 0 || x0 > W) return;
        if (x1 - x0 < 1) return;
        const y0 = TREND.hatchTop, y1 = y0 + TREND.hatchH;   // 格顶往上留 2 px（见上）
        ctx.fillStyle = hatch;
        ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
        // 像素区间一起记：工装要拿它跟**成交量柱的 y 范围**对账（"不相交"是这张卡的验收之一），
        // 让工装自己另推一遍带子在哪，改了位置它不会跟着走。
        state.trendDrawn[key].push({ i0, i1, y0, y1 });
      };
      for (const b of bnd) strip(b.bar, b.pullback_end_bar, 'bounds');
      // 图尾（或者图头）还没确立的候选极值：也得铺一条 —— 它跟已确立的那几条是同一件事
      // （极值已出、还没立住），只差"这一头还没走完"。铺到**它所在那一段走完**为止。
      for (const p of T.pending) {
        const s = segs.find((q) => q.i0 <= p.bar && p.bar <= q.i1);
        strip(p.bar, s ? s.i1 : data.bars.length - 1, 'pending');
      }
    }

    // ③ 合成大框（§八 5）：D3 合成出来的**高一级**中枢，范围取 `DD～GG`，横跨 `X0～X1`（载荷里
    //    就是 bar 下标，跟 `PI0/PI1` 那套不同 —— 别拿 host 去换）。本级别那几个小框照画在它里面
    //    （那是框层的事，这一层不动它们）。
    //    ★★ **归「高一级」那颗芯片，不跟 `trend` 走**（小栋 10-05 23:3xZ 定，卡 card-113a3b16-026）：
    //      它跟框层那批第 33 课"满 9 段"升出来的框（`z.up`）**是一件事**（都是"高一级的那个中枢"），
    //      所以跟它们**同一个开关**。那颗芯片默认关 ⇒ 合成框也跟着默认不画（以前是跟着 `trend` 默认就画）。
    //      先前这儿写的「它不归高一级管」是**上一版的判断，作废** —— 两套机制的名字撞了是真的，
    //      但"名字撞了"不等于"该分两个开关"：对看图的人来说，屏上就是两种高一级的框。
    //    ★ `T.units` 里**只有 n>1 的**（合成过的）：`core/trend.py:176` 那句 `if u["n"] > 1` 保证的。
    //      这儿**不重复过滤** —— 再加一道前端过滤是永远走不到的那半边（放不坏的守卫等于没守卫），
    //      而且它会让人以为"前端也管这件事"。这条保证的出处写在这儿，改后台那句的人要连这儿一起看。
    //    ★ 还在长的那一段里的合成中枢 ⇒ 整框虚线（跟框层同一条：没走完的东西不画实线）。
    if (sh.up) {
      for (const u of T.units) {
        const x0 = vp.xOfBar(u.X0), x1 = vp.xOfBar(u.X1);
        const yt = vp.yOfPrice(u.GG), yb = vp.yOfPrice(u.DD);
        if (x0 === null || x1 === null || yt === null || yb === null) continue;
        if (x1 < 0 || x0 > W) continue;
        const live = !!(segs[u.seg] || {}).live;
        // ★ **不填充**（`fillAlpha = 0`），跟参考图一致（那边 `boxes()` 画的全是 `fill="none"`）。
        //   这不是我挑的：合成出来的高一级中枢**可以很大** —— ZEC 15m 上有一个横跨 6684 根
        //   （全历史的三分之一）、上下 400 多点，铺 8% 的品红上去，屏上就是一大块紫，
        //   把底下的红带子（高→低）**染成紫色** —— 而"紫"是这张图的图例里根本没有的颜色，
        //   读的人只会以为那是第三种走势。框要说的本来是"这几个中枢合成一个高的"，
        //   那是**边**在说，不是面在说。出图看过才定的（第一版带填充，屏上一眼就不对）。
        //   ★ 框层那批 `z.up` 是**带填充**的（`CHART.up_fill`）：那些框小，8% 摊得开。同一条账的两头。
        const ucol = upColor('seg');
        drawFrame(ctx, x0, yt, x1, yb, ucol, WIDTH.sc, 0, null, !live, W, false);
        // `col` 进只读出口是给工装用的：它得能拿画上去的那个色跟 `/theme.js` 对账，
        // 而不是自己另外推一遍「这个级别该是什么色」（推的那套改了配色不会跟着走）。
        state.trendDrawn.units.push({ X0: u.X0, X1: u.X1, DD: u.DD, GG: u.GG, n: u.n, seg: u.seg, live, col: ucol });
      }
    }
  });
}

/** 45° 斜线填充（参考图的 `pattern rotate(45)`，线距 8 px、线宽 2）。贴图做一次缓存、每帧只
 *  建一个 pattern —— 这一条带子每帧现画几百条线会把整层变成性能问题，而它只有 12 px 高。 */
let hatchTile = null;
function hatchFill(ctx) {
  if (!hatchTile) {
    hatchTile = document.createElement('canvas');
    hatchTile.width = hatchTile.height = 8;
    const g = hatchTile.getContext('2d');
    g.strokeStyle = TREND.hatch; g.lineWidth = 2;
    g.beginPath(); g.moveTo(-1, 9); g.lineTo(9, -1); g.stroke();
  }
  return ctx.createPattern(hatchTile, 'repeat');
}

/** top：分界（§八 2）＋ 待定（§八 3）＋ 撤回（§八 4）＋ 框编号（§八 6，默认关）——**这四个归 `trend`**；
 *  「升级」二字（§八 5）——**归 `up`**（它挂在合成框上，跟框同一个开关，见 `trendBandView` 开头那段账）。 */
function trendMarkView(target, state, prim) {
  const { data, opts } = state;
  const T = trendOf(data);
  const sh = shownOf(opts, data);
  // ★ 命中带**每帧先清空**，而且清在早退**之前**：这一层没数据、或者两颗芯片都关着的时候也得清。
  //   留着上一帧的带子就是"层关了、指针压上去还有字"—— 那条比画错更难被发现：**图上什么都没画**。
  //   （这跟「关着的层不算看得见」不是同一条账：那条管**画**，这条管**命中**。）
  boundHits.bands = [];
  // 已撤回的只读清单同理：层关着也得清，不然工装读到的是上一帧画过的叉（⑦c 第一版就是这么红的）
  if (state.trendDrawn) state.trendDrawn.withdrawn = [];
  if (!T || (!sh.trend && !sh.up)) return;
  // ★ 这一层的字**一律不登记 `placed`**（价签那张避让表），理由两条，都说破：
  //   ① 它们钉在**一条竖线和一个价**上（分界价格、待定、撤回）—— 挪开它就不是那个价了，避让没有意义；
  //   ② 「升级」那两个字倒是可以避让，但避让表住在**标注层**那个 primitive 里，两边共用一张表只能
  //      靠"谁先画"，而这一层要压在 K 线之上、又得让价签压在自己之上（竖虚线切过价签的实底很难看）
  //      —— 两头的次序要求是**打架的**，硬凑出的一定是"避让晚一帧"这种说不清的半成品。
  //   ⇒ 折中：不参与避让，但把每一枚字的包围盒**记下来**（`state.trendDrawn.labels`），
  //     让工装能真去量「这一层的字跟价签压没压上」。**能测**比"看着还行"值钱。
  //     （「未收盘」那一句是同一条账的旧例，见 ⑤。真要给它一套避让，那是 card-c6644f52-2fa
  //      那一笔该管的事 —— 框编号本来就要重做这一层的标签系统。）
  target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
    const W = mediaSize.width, H = mediaSize.height;
    const vp = viewport(prim._chart, state.candleSeries || prim._series, data);
    const D = state.trendDrawn || (state.trendDrawn = { bands: [], bounds: [], pending: [], retracted: [], units: [], num: [], states: [] });
    D.labels = [];
    D.deaths = [];
    D.states = [];
    D.withdrawn = [];
    // 命中带的画布：跟 `ghostHits` 同一条账 —— `ctx.canvas` 就是这个窗格的画布，
    // `useMediaCoordinateSpace` 给的坐标就是它的 CSS 像素，所以「客户端坐标 − getBoundingClientRect」
    // 正好落在同一个系里。每帧重设：窗格重建过之后旧的 canvas 是个死元素，量出来的坐标全是错的。
    boundHits.canvas = ctx.canvas;
    // 这一层**自己**那张占位表：不跟别的层互相避让（理由见上），但自己这几类字之间得让开 ——
    // 分界那条贴着极值写，段的左上角又紧挨着同一个分界，不避让就是几个数字叠一坨。
    // 谁最"钉死"谁先占位：分界价格 → 待定 → 撤回（都钉在一个价上，不许挪）→ 框编号（钉在某个中枢上）
    // →「升级」（管一整段，可以挪）。**这条链就是画的顺序**，改顺序就得连这里一起改。
    const mine = [];

    // ①②③ 归「走势分段」那颗芯片。④ 归 `trendNum`（`shownOf` 里已经和 `trend` 与过了，见那边）。
    if (sh.trend) {
      // ① 分界（§八 2）：竖虚线 ＋ 极值处一个实心点 ＋ 标价格。画在 K 线**之上** —— 理由跟切点记号
      //    那一条是同一个（一根细虚线压在密集 K 线上就没了，真像素量过）。
      for (const b of T.bounds) {
        const x = vp.xOfBar(b.bar), y = vp.yOfPrice(b.price);
        if (x === null || y === null || !onScreen(x, W, 8)) continue;
        ctx.setLineDash(DASH.trendEdge);
        ctx.strokeStyle = rgba(TREND.edge, 200); ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
        ctx.setLineDash([]);
        // 命中带（卡 card-22888623-1a7）：**只记、不画** —— ±4px 的无形竖条，屏上跟改之前一模一样。
        // ★ 为什么 ±4：那根线是 1.5px，瞄准它得把指针当手术刀。4px 是"手不用屏住呼吸就能压上"，
        //   整条带子也才 8px 宽 —— 要误吃掉隔壁那根，两根得挨到 8px 以内，那时它们本来也读不成两根。
        // ★ 带子按**已确认画出来的**这一批登（跟线的 for 循环同一个门槛 `onScreen`）——
        //   屏外那根登进去，指针在边缘就会命中一根根本没画的线。
        boundHits.bands.push({ x0: x - 4, x1: x + 4, bound: b });
        // 那个点：填结构色、外面描一圈**页面底色** —— 参考图那边是"深点 ＋ 白圈"，这边正好反过来，
        // 干的是同一件事：把点从背后的带子里"抠"出来，别糊成一片。
        // ①D 待确认（D-5，Nova 10-09 06:42 定）：点画**空心**（里面填页面底色、外圈结构色），确认了才填实。
        //   ★ 不借「待定」那套灰点线：那是 D2-6 的**候选极值**（`trend.pending`），这里是**已经立了、还没坐稳的刀**，
        //     两件事要一眼分得开。分界竖虚线照画 —— 这把刀确实切开了段，只是还可能被撤。
        //   ★ 只认后台给的 `b.state`（S5 刀的也由后台按 D-4 派生好），前端一律不自己推（Bram／Nova 06:43 定）。
        const pending = b.state === 'pending';
        ctx.beginPath(); ctx.arc(x, y, 4.5, 0, Math.PI * 2);
        ctx.fillStyle = pending ? TREND.halo : TREND.edge; ctx.fill();
        ctx.strokeStyle = pending ? TREND.edge : TREND.halo; ctx.lineWidth = pending ? 1.8 : 2; ctx.stroke();
        // 价格跟着极值走：极值在上面就往上写、在下面就往下写（参考图的 dy -10 / +20），免得字压在带子上。
        // ★ 多一条**翻边**：极值本来就贴着格顶（ZEC 15m 那个 1699 就是）⇒ 往上写会顶出画布、
        //   只剩半行字。翻到下面去写 —— 位置仍然钉在那一根上，只是站到点的另一侧。
        let ly = y + (b.kind === 'H' ? -10 : 20);
        if (ly < 14) ly = y + 20;
        else if (ly > H - 6) ly = y - 10;
        // 读数是 `fmtG`，跟这张图上**所有**价格同一个格式（价签、图脚都是它）。
        D.labels.push(haloText(ctx, x, ly, fmtG(b.price), TREND.edge, 'center', mine));
        // 死点类型（D2-5，第六批 ②；后台 `death`／`death_why` 第四批就带着，前端原来一处没读）：价格字再往外一行、小一号。
        //   ★ 只标不改刀（spec D2-5：类型不决定刀落在哪）。全名放悬停（app.js `boundShow`），图上只写短名。
        //   ★ 深浅分两档：真判出来的三种（趋势背驰／盘整背驰／小转大）用结构色，编者口径那三种（盘整·未见背驰／比不了／D2-8 补刀）
        //     用静音灰 —— 「比不了」占了线上 15 张的六成，跟真死点一个颜色的话图上满眼都是它，读的人分不出哪几刀是真背驰。
        // ★ 「盘整相连」（S5 刀，S12）**故意不在 DEATH_SHORT 里**：图上不挂字，只在悬停里有（Nova 10-09 06:42 定）——
        //   S5 刀占正式口径一半多（194 把里 106），每把都挂字会把真背驰那几把淹掉。
        const dt0 = DEATH_SHORT[b.death];
        // ★ 连写用全角括号「趋势背驰（待确认）」，不用「 · 」：左格本来就在尾巴上接一个「 ·」，用点连会变成「趋势背驰 · 待确认 ·」（实截踩过）
        const dt = dt0 ? (pending ? dt0 + '（待确认）' : dt0) : (pending ? '待确认' : null);
        D.states.push({ bar: b.bar, state: b.state || null, hollow: pending });
        if (dt) {
          const col = dt0 && DEATH_REAL.has(b.death) ? TREND.edge : TREND.mut;
          // 候选格按顺序取第一个**不压字**的：价格字往外一行 → 同一行接在右边 → 同一行接在左边；都不行就不写
          //   （悬停里照样有全名，见 app.js `boundText`）。要躲的字有两张表：这一层自己的 `mine`，和标注层那张
          //   `placed`（价签／买卖点文字／盘整组 chip，`state.labelBoxes`，标注层先画，这一帧已经齐了）。
          //   ★ 实截踩过：1699 那种贴格顶的顶，往外一行压进「等确认」斜线带；改成接在右边，又压在 [1631.1, 1681.99] 价签上。
          ctx.font = FONT;
          const pw = ctx.measureText(fmtG(b.price)).width;
          const dy = ly + (b.kind === 'H' ? -14 : 14);
          const top = TREND.hatchTop + TREND.hatchH + 1;
          const cand = [
            [dy, 'center', x, dt],
            [ly, 'left', x + pw / 2 + 5, '· ' + dt],
            [ly, 'right', x - pw / 2 - 5, dt + ' ·'],
          ];
          const others = [...mine, ...(state.labelBoxes || [])];
          // 只读出口：每一刀记号落在哪一格（out＝往外一行／right／left／null＝三格都压、不写），工装拿它量「不压字」和配色
          const rec = { bar: b.bar, death: b.death, state: b.state || null, txt: null, mode: null, box: null, col };
          D.deaths.push(rec);
          for (const [yy, al, ax, txt] of cand) {
            ctx.font = FONT_SM;
            const w = ctx.measureText(txt).width;
            const x0 = al === 'center' ? ax - w / 2 : al === 'right' ? ax - w : ax;
            const box = [x0, yy - 11, x0 + w, yy + 3];
            if (box[1] < top || box[3] > H - 1 || box[0] < 2 || box[2] > W - 2 || hits(box, others)) continue;
            D.labels.push(haloText(ctx, ax, yy, txt, col, al, mine, FONT_SM, 11));
            Object.assign(rec, { txt, mode: al === 'center' ? 'out' : al, box });
            break;
          }
        }
      }

      // ② 待定（§八 3）：还没确立的候选极值 —— 灰点线 ＋ 旁边标「待定」。价格再过它（创了新极值）
      //    就换成新的一根（D2-6）：这是**候选换了**，不是刀撤回 —— 所以它跟下面那条必须分得开。
      for (const p of T.pending) {
        const x = vp.xOfBar(p.bar), y = vp.yOfPrice(p.price);
        if (x === null || y === null || !onScreen(x, W, 8)) continue;
        ctx.setLineDash(DASH.trendCand);
        ctx.strokeStyle = rgba(TREND.mut, 200); ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
        ctx.setLineDash([]);
        D.labels.push(haloText(ctx, x - 8, y + 4, `${fmtG(p.price)} 待定`, TREND.mut, 'right', mine));
      }

      // ③ 撤回（D2-7，§八 4）：确立过、后来被撤掉的那把刀。**跟「待定」分开**这件事
      //    靠两样东西，不只靠两个字：线的疏密不同（`trendCand` 2 4 ／ `trendBack` 1 3），字也不同。
      //    只靠字面分开，扫一眼是分不出来的 —— 而这两件事在图上都不常见，正是"难得一见"最容易被看错。
      for (const r of T.retracted) {
        const x = vp.xOfBar(r.bar), y = vp.yOfPrice(r.price);
        if (x === null || y === null || !onScreen(x, W, 8)) continue;
        ctx.setLineDash(DASH.trendBack);
        ctx.strokeStyle = rgba(TREND.mut, 200); ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
        ctx.setLineDash([]);
        D.labels.push(haloText(ctx, x + 8, y + 4, `${fmtG(r.price)} 撤回`, TREND.mut, 'left', mine));
      }

      // ③b 已撤回（Q-6 选 A，小栋 10-09 12:47；卡 card-fe3aebd3-819）：服务端记下的「送出去过、后来整个不见了」的刀和线段
      //    （载荷顶层 `withdrawn`，Bram 12:22 方案：`{kind: d2|s5|seg, t, dir, price, at}`，`t` 是那根 K 线的开盘时间）。
      //    跟上面 ③ `T.retracted` 是**两件事**：那是引擎一趟算里 D2-7 自己撤的；这是笔回头改了、上一趟确认的东西这一趟没了。
      //    画法照 Q-6 示意图：原位置一个**淡红叉**＋一条很淡的红虚线＋「已撤回：笔回头改了」。用 `t` 找位置不用下标 ——
      //    往左加载会让下标整体平移，开盘时间不会。`t` 不在这一窗的 K 线里 ⇒ 不画（不夹回画布）。
      const ts = prim._chart.timeScale(), sec = (t) => (t > 1e12 ? t / 1000 : t);
      for (const w of (Array.isArray(data.withdrawn) ? data.withdrawn : [])) {
        // 线段那条（Bram 9a9ba34）：`{kind:'seg', t, t1, dir:'up'|'down', p0, p1}` —— 没有 `price`，叉打在**终点**（t1, p1）上，
        //   整条原位置再描一道很淡的红虚线（「这条线段被撤了」）。刀那两类：`{t, dir:'H'|'L', price}`，叉打在刀上。
        const isSeg = w.kind === 'seg';
        const tt = sec(isSeg ? w.t1 : w.t), pp = isSeg ? w.p1 : w.price;
        const x = ts.timeToCoordinate(tt), y = vp.yOfPrice(pp);
        if (x === null || y === null || !onScreen(x, W, 8)) continue;
        if (isSeg) {
          const x0 = ts.timeToCoordinate(sec(w.t)), y0 = vp.yOfPrice(w.p0);
          if (x0 !== null && y0 !== null) {
            ctx.setLineDash(DASH.trendBack); ctx.strokeStyle = rgba(CHART.sell, 110); ctx.lineWidth = 1.5;
            ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x, y); ctx.stroke(); ctx.setLineDash([]);
          }
        }
        ctx.setLineDash(DASH.trendBack);
        ctx.strokeStyle = rgba(CHART.sell, 70); ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
        ctx.setLineDash([]);
        ctx.strokeStyle = rgba(CHART.sell, 160); ctx.lineWidth = 2.5;
        ctx.beginPath(); ctx.moveTo(x - 7, y - 7); ctx.lineTo(x + 7, y + 7); ctx.moveTo(x - 7, y + 7); ctx.lineTo(x + 7, y - 7); ctx.stroke();
        const what = isSeg ? '线段已撤回' : '已撤回';
        const top = isSeg ? w.dir === 'up' : w.dir === 'H';      // 叉在顶上 ⇒ 字往上写，在底下 ⇒ 往下写
        D.labels.push(haloText(ctx, x + 12, y + (top ? -14 : 16), `${what}：笔回头改了（${fmtG(pp)}）`, CHART.sell, 'left', mine));
        D.withdrawn.push({ kind: w.kind, t: w.t, price: pp, x: Math.round(x), y: Math.round(y) });
      }

      // ③.5「等确认」三个字（§八 3，卡 card-60678062-8c2）：那条斜线带的**名字写在带子自己头上**。
      //    小栋原话「没有文字说明」—— 说得对，而且比"名字不好"更彻底：这一层**从来没上图例**，
      //    这个器件在屏上就是一条斜线，没有任何一处告诉过他那是干什么的。
      //    ★ 数据源是 `D.bounds`（`trendBandView` 这一帧**真铺上去**的那几条），不是原始 `T.bounds`：
      //      一处算、两处用（跟「升级」同一条账）—— 层关着的时候不会留下"带子没了、字还在"。
      //    ★ 「字放不下就只写在最近一段」（小栋 10-05 23:46Z）：带宽够的**每条都写**；**一条都放不下**时，
      //      只写**最近的那一条**（`D.bounds` 是按载荷顺序登的，最后一条就是最新的那个极值）。
      //      两种情形分得很清，别读混：有够宽的时候，不够宽的那几条**就是不写**
      //      （写上去只会溢出到隔壁那条带子头上，读成"那一块也是等确认"，比不写更糟）；
      //      走"只写最近一条"这一支的时候，才允许字**溢出这条带子的右头**一点
      //      —— 那时屏上根本没有第二条带子，溢出不会指错人，而"一个字都不写"等于把小栋报的毛病原样留着。
      //      ★ 这一支**到今天为止没被走到过**：我拿 616 个视口（跨度 1～30 根 K）扫过，
      //        带子要么整条在屏外（`strip()` 当场 return），要么可见宽度就没低于过 49 px（字要 36.8＋12）。
      //        ⇒ 它是**防"载荷里出现一根 K 宽的带子"的保险**，不是现在能触发的东西。
      //        工装里 54 那格把"被走到几次"印出来了，别以为它验过。
      //    ★ 锚在**这条带子自己的左头**（可见部分的左沿）`+6`，跟「升级」同一个锚法。
      //      这里**允许夹到 x=0**，跟「升级」那条不一样：那条的框左沿能跑到屏幕外三千个像素、
      //      底下什么都没有，夹出来的就是"孤儿字"；这一条是**横铺**的带子，x=0 那一点底下
      //      **真的有这条带子**。★ 判据不是"夹没夹"，是"字底下到底有没有那个东西"。
      if (D.bounds.length) {
        const TXT = '等确认';
        ctx.font = FONT;
        const tw = ctx.measureText(TXT).width;
        const px = (b) => [vp.xOfBar(b.i0), vp.xOfBar(b.i1)];
        const visW = (b) => { const [x0, x1] = px(b);
          return (x0 === null || x1 === null) ? 0 : Math.min(x1, W) - Math.max(x0, 0); };
        const roomy = D.bounds.filter((b) => visW(b) >= tw + 12);
        const draw = roomy.length ? roomy : D.bounds.slice(-1);   // 都放不下 ⇒ 只写最近那一条
        for (const b of draw) {
          const [x0, x1] = px(b);
          if (x0 === null || x1 === null || visW(b) < 8) continue; // 带子只露一条缝 ⇒ 不写
          const lx = Math.min(Math.max(x0, 0) + 6, W - tw - 6);
          if (lx >= Math.min(x1, W)) continue;                     // 起笔点已经出了带子右头 ⇒ 不写
          // y：基线摆到带子底沿往上 2 px ⇒ 墨迹落 [2.1, 13.2]、描边落 [0.6, 14.7]，
          // 整个包在带子 [2, 14] 里（字是"写在带子上"，不是掉在带子下面）。
          // ★ 这几个数是**量出来的**，别凭感觉调：12 px 的 `FONT` 量到 asc 9.90 / desc 1.20。
          D.labels.push(haloText(ctx, lx, TREND.hatchTop + TREND.hatchH - 2, TXT, TREND.mut, 'left', mine));
        }
      }
    }

    // ④ 框编号 A／B／C（§八 6，card-c6644f52-2fa）：**段内按时间排，换一段重新从 A 起**。
    //    图上的记号只有字母，**段号不画**（段号是给人对表用的，画上去这一层就变成两个体系）。
    //    ★ 挂哪一级**不许猜**：载荷的 `trend_reading` 说了算（`docs/spec/走势分段.md:280`）——
    //      A ⇒ 升级段的字母挂**合成出来的高一级中枢**（`units`）、别的段挂本级别（`seg_centers`）；
    //      B ⇒ 一律挂本级别。★ D3 换边是**后台一个字段**的事，这一层一个字都不用改 ——
    //      A 和 B 两种排法这里都写好了，切的是数据不是代码。
    //    ★ 钉在**中枢自己的范围中心**（x 取 `X0..X1` 中点、y 取价格带中点）：字母要能一眼认出
    //      "这一枚说的是哪一个中枢"。钉在段的左上角就没有这个对应 —— 那是「升级」二字的锚法，
    //      它管的是"这一整段"，字母管的是"段里这一个中枢"，两种锚法不能混。
    //    ★ 颜色**用墨色**（跟分界那个价格同一套：墨 ＋ 描边），**不跟段的方向色走** ——
    //      第一版跟方向走，绿字母落在 16% 的绿带上、红字母落在红带上，看图当场就废了
    //      （一团暗红里几个更暗的红点）。理由写在 `FONT_LET` 上面那一段。**唯一的例外**：
    //      **还在长的那一段用灰** —— 它中枢数还会变、字母将来要重排，不该跟定下来的字母一样亮；
    //      那是"未定"的记号，"这一段往哪儿去"已经由背景带说了。
    if (shownOf(opts, data).trendNum) {
      // 缺字段按 A —— 后台的缺省就是 A（core/trend.py），而"猜不出来就画 B"会静默换掉一套口径
      const reading = data.trend_reading === 'B' ? 'B' : 'A';
      const lv = data.seg_centers || [], uni = T.units || [];
      const capMid = Math.round(SIZE_LET * 0.36);   // 把字母的**中线**摆到 y 上（haloText 的 y 是基线）
      // 一枚字母的宽 —— 小写让位要用（见下面 `letClear`）。★ 借 `ctx` 量一下就行，不用另开画布：
      // `haloText` 每次调用都自己把 `ctx.font` 设回去，所以在这里动一下字体不会漏到后面去。
      ctx.font = FONT_LET;
      const CW_LET = ctx.measureText('a').width, PAD_LET = 2;
      /** 小写那一枚落在哪儿：先按锚法给个位置，若跟**本段已经落下的字母**压上了就往外让。
       *  ★ 为什么需要它（Nova 10-06 加的硬约束）：缺口"极短"的时候（一根 K 线／跳空）框只有一两根宽，
       *    框的**中心**几乎就是缺口本身 ⇒ 小写正好落在旁边那枚大写上，两枚字叠成一团。
       *  ★ 让法有顺序，且**每一档都要求落点仍在屏内**（`free` 里判）：
       *    ① 沿 x 往外推（`dir` ＝ 往外那个方向；缺口两边都是框时 `dir` 为 0 ⇒ 两边都试，先近后远）
       *    ② x 让不开就纵着错开一格（先往下、再往上）—— 纵着错开不改"这一枚指的是谁"（缝还是块）
       *  ★ 都让不开就按原位落：宁可压一点，也**不许**把字母挪出屏（跟这一层 ㊼ 那条账同源）。
       *    这种情况工装量得出来（大小写那两组矩形会相交），是要报的，不是要藏的。
       *  ★ 只在**本段**里避让：这一层保证的是"自己不叠自己"；跟分界／待定／撤回那几层的避让是另一条账。 */
      const letClear = (x, y, dir, placed) => {
        const h0 = Math.round(SIZE_LET * 0.92), h1 = Math.round(SIZE_LET * 0.25), w = CW_LET / 2;
        const free = (xx, yy) => onScreen(xx, W, 8) && onScreen(yy, H, 8) && !placed.some((b) =>
          xx - w < b[2] + PAD_LET && b[0] < xx + w + PAD_LET
          && yy - h0 < b[3] + PAD_LET && b[1] < yy + h1 + PAD_LET);
        if (free(x, y)) return [x, y];
        const step = CW_LET + PAD_LET, cand = [];
        if (dir) for (let n = 1; n <= 3; n++) cand.push([x + dir * step * n, y]);
        else for (let n = 1; n <= 3; n++) { cand.push([x + step * n, y]); cand.push([x - step * n, y]); }
        for (const dy of [SIZE_LET + 3, -(SIZE_LET + 3)]) cand.push([x, y + dy]);
        for (const c of cand) if (free(c[0], c[1])) return c;
        return [x, y];
      };
      for (let i = 0; i < T.segments.length; i++) {
        const s = T.segments[i];
        const zs = ((reading === 'A' && s.upgraded) ? uni : lv).filter((z) => z.seg === i);
        const col = s.live ? TREND.mut : TREND.edge;
        let drawn = 0, offY = 0;
        const placed = [];   // 本段已经落下的字母矩形（大写先落）：小写拿它避让
        for (let k = 0; k < zs.length && k < TREND_LET.length; k++) {
          const z = zs[k];
          const lo = z.ZD !== undefined ? z.ZD : z.DD;      // 本级别是 ZD..ZG，高一级是 DD..GG
          const hi = z.ZG !== undefined ? z.ZG : z.GG;
          const x = vp.xOfBar(Math.round((z.X0 + z.X1) / 2)), y = vp.yOfPrice((lo + hi) / 2);
          // ★★ **x 和 y 都得在屏上** —— 这一处跟这一层别的字**不一样**，是踩过才知道的：
          //    分界／待定／撤回那几个是"一根竖线 ＋ 一个价"，纵着贯穿整屏 ⇒ 只看 x 就够了。
          //    字母是一个**钉在某个价上的点**，而读法 A 下那个价是**高一级中枢**的价格中点 ——
          //    那个中枢可以横跨大半段历史、上下几百点，它的中点**经常落在当前视野之外**。
          //    只判 x 的话，字母会被画到画布外面去（实测：y = −182，屏幕上一个字都看不见，
          //    而 `trendDrawn` 里照样记着它画了）——**账上有、屏上没有**，正是最难查的那种。
          //    ★ 不夹回画布（跟上面 `onScreen` 那条账同一条）：落点看不见就不画，别把它拖到边上
          //      假装它在那儿。代价是：读法 A 下这一层可能只画得出一部分字母 —— 这是**要报的**，
          //      不是要藏的（见卡 card-c6644f52-2fa 上那张图）。
          if (x === null || y === null || !onScreen(x, W, 8) || !onScreen(y, H, 8)) {
            // 「横着在屏上、纵着出去了」单独记一笔：这不是"滚到别处去了"（那种是正常的），
            // 是**这一枚的价当前看不见** —— 读法 A 下会真的发生，得让它量得出来。
            if (x !== null && onScreen(x, W, 8) && (y === null || !onScreen(y, H, 8))) offY++;
            continue;
          }
          const box = haloText(ctx, x, y + capMid, TREND_LET[k], col, 'center', mine, FONT_LET, SIZE_LET);
          D.labels.push(box);
          placed.push(box);
          drawn++;
        }
        // ── 小写 a、b、c：**两个框之间**那一段（§八 6，card-246fc7cf-a9e）────────────────────
        //    ★ 名单＝上面那个 `zs`，**不另挑一份**：交替 a A b B c 靠的就是"两套字母认同一份框"。
        //    ★ 缺口比框多一个：进第一个框之前＝a，框与框之间依次 b、c…，出最后一个框之后＝最后一个
        //      ⇒ 每段小写个数 ＝ **框数 ＋ 1**（框数 0 的段除外，见下）。
        //    ★ 框数 0 ⇒ **一个小写都不画**（并记 `nlo: 0`）：没有框就没有"框之间"，"进第一个框之前"
        //      也就无所指 —— 硬标一个 a 会跟 a 的定义打架。**编者口径**（已写进 spec）。
        //      ⇒ "框数 ＋ 1"这条公式**在框数 0 处故意不算**，那是规矩，不是漏算。
        //    锚法（Nova 10-06 认的这版）：x 取缺口在 bar 轴上的**中点**；y 取相邻两框中心价的**中点**，
        //      首／尾那个缺口只有一框 ⇒ 退化成那一框的中心 y（不另立一套规则）。
        //      ★ 中心价的取法跟大写**同一行**（`ZD..ZG`／高一级 `DD..GG`），不另写一套。
        const ordered = zs.slice().sort((p, q) => p.X0 - q.X0);
        // ★ `ord` 记的是"载荷给的就是按 X0 排好的吗"。为什么值得记：大写按**载荷顺序**发字母、
        //   小写的缺口按**几何**切，两者只在载荷有序时才必然一致。哪天后台换了顺序，交替会断，
        //   而这件事在别处**看不出来**（大写那格只数个数、不认位置）⇒ 记下来，让工装量得出来。
        const ord = zs.every((z, k) => k === 0 || zs[k - 1].X0 <= z.X0);
        const nlo = ordered.length === 0 ? 0 : ordered.length + 1;
        let drawnLo = 0, offYLo = 0, offXLo = 0, movedLo = 0;
        for (let k = 0; k < nlo && k < LOWER_LET.length; k++) {
          const prev = k === 0 ? null : ordered[k - 1];
          const next = k === nlo - 1 ? null : ordered[k];
          const mid = (z) => (z.ZD !== undefined ? (z.ZD + z.ZG) / 2 : (z.DD + z.GG) / 2);
          const pa = prev ? mid(prev) : null, na = next ? mid(next) : null;
          const b0 = prev ? prev.X1 : s.i0, b1 = next ? next.X0 : s.i1;
          const x0 = vp.xOfBar(Math.round((b0 + b1) / 2));
          const y0 = vp.yOfPrice(pa === null ? na : na === null ? pa : (pa + na) / 2);
          const xOk = x0 !== null && onScreen(x0, W, 8), yOk = y0 !== null && onScreen(y0, H, 8);
          if (!xOk || !yOk) {
            // 跟大写同一个账：「横着在屏上、纵着出去了」单独记一笔（读法 A 下真会发生）。
            // ★ 这里判的是**让位之前**的落点 —— 让位本身也要求不出屏（`letClear` 的每一档都判），
            //   所以"让完出屏"这件事在 `letClear` 里就被挡掉了，不会悄悄溜到屏外去。
            // ★★★ 这两栏合起来是一条**可以不重不漏算平的账**：循环里的每一枚小写
            //   **要么**画出来（`drawnLo`）、**要么**因为 x／y 出屏被跳过（`offXLo`／`offYLo`），
            //   没有第三条路；再加"字母表不够用"的 `overLo` ⇒ **`nlo` ≡ 三者之和**。
            //   ⇒ 将来谁在循环里加一条新的 `continue`，**必须同时给它一栏**，
            //     否则这个等式会破 —— 而破了是**看得出来**的（工装直接算这个和）。
            if (xOk) offYLo++; else offXLo++;
            continue;
          }
          // 「往外」是哪个方向：头那个往左（离开第一框）、尾那个往右（离开最后一框）；
          // 两边都是框时给 0，交给 `letClear` 两边都试。
          const dir = prev === null ? -1 : next === null ? 1 : 0;
          const [lx, ly] = letClear(x0, y0, dir, placed);
          // ★ 记一笔"这一枚让过位"。为什么要记：卡上那条「缺口极短时往外让」的**牙**只在
          //   **真的出现极短缺口**时才咬得到 —— 要是这份数据上一次都没走到这条路，
          //   「大小写不重叠」那格的绿就是**空过**（它没验到让位那条路），得换数据／缩 span 才咬得到。
          //   记下这个数，工装才能说清自己是"咬到了"还是"没遇到"。
          if (lx !== x0 || ly !== y0) movedLo++;
          const box = haloText(ctx, lx, ly + capMid, LOWER_LET[k], col, 'center', mine, FONT_LET, SIZE_LET);
          D.labels.push(box);
          placed.push(box);
          drawnLo++;
        }

        // ★ **每一段都记一笔，包括 0 枚的那些**。第一版是"有字母才记"，工装立刻逮到：
        //   出口里少了图头那一段 ⇒ 看的人分不清"这一段没有字母"和"这一段压根没算" ——
        //   而"图头 0 中枢 ⇒ 无字母"正是这一层最要说清的一件事之一。**零也要有行**。
        D.num.push({ seg: i, n: zs.length, drawn, offY, over: Math.max(0, zs.length - TREND_LET.length),
          nlo, drawnLo, offXLo, offYLo, movedLo, overLo: Math.max(0, nlo - LOWER_LET.length), ord });
      }
    }

    // ⑤ 「升级」二字：★★ **挂在合成出来的那个框上，不挂段**（§八 5 改；小栋 10-05 23:3xZ 定，
    //    卡 card-113a3b16-026 第 ③ 条）。
    //
    //    ★ 改之前是什么样，为什么改（这是小栋点名的那一条，原话"一直往右拖，左上角『升级』挂很久，会误会"）：
    //      旧画法遍历 `T.segments` 里 `upgraded` 的段，锚在**段的左上角**，并且把 x **夹进画布**：
    //      `Math.max(x, 4)`。而一段可以横跨整屏 —— 往右拖的时候 `s.i0` 早跑到屏左沿之外，夹出来的
    //      lx 就**一直是 4**：那两个字于是钉死在视口左上角不动。看上去不像"某一段升级了"，
    //      像"整个屏幕/整个图都升级了"。**钳位把一个会动的东西变成了一个不动的东西** —— 这是那个 bug 的全部。
    //
    //    ★ 新画法三条，一条都不许省：
    //      ① 锚在**框自己的可见左上角**：框动它动，读的人一眼看得出这俩是一套；
    //      ② 框整个出了屏 ⇒ **一个字都不画**（不夹回来 —— 夹回来就是旧 bug 的翻版）；
    //      ③ 只给**这一帧真画出来的那些框**写字：数据源是 `D.units`（上面 `trendBandView` 那一趟
    //         登记下来的），不是 `T.units` 原始载荷。**一处算、两处用** —— 否则开关关着的时候
    //         会画出"框没了、字还在"（那正是"账上有、屏上没有"的反面，一样是假账）。
    //    ★ 颜色 `upColor('seg')`：跟框、跟框层那批高一级框**同一条规则**（第 ② 条要的"同一级同一色"）。
    //    ★ y 跟着框的上沿走；框比屏幕高的时候落在**可见那一段**的顶上，不夹到视口外。
    //    ★ 仍然让位（`fitLabel`）：这一层里只有它是"可以挪"的 —— 分界价格钉在一个价上、
    //      待定／撤回钉在一根 bar 上、编号钉在某个中枢上，挪了就不是那个东西了；它挪一挪还在同一个框里。
    if (sh.up) {
      for (const u of D.units) {
        const x0 = vp.xOfBar(u.X0), x1 = vp.xOfBar(u.X1);
        const yt = vp.yOfPrice(u.GG), yb = vp.yOfPrice(u.DD);
        if (x0 === null || x1 === null || yt === null || yb === null) continue;
        // 框整个出了屏 ⇒ 一个字都不画
        if (x1 <= 0 || x0 >= W) continue;
        // 框纵向也整个出了屏 ⇒ 画面上根本没有这个框，别给它写字
        if (yb < 0 || yt > H) continue;
        // ① 锚在**框自己的左边线**内侧 `+6`。
        // ★★ 这条边**只要在屏外就不画**，绝不夹回 0 —— 夹回去正是旧 bug：钳位之后那两个字
        //    就钉在视口左边不动了（小栋原话"一直往右拖，左上角『升级』挂很久"）。
        //    **代价说破**（不藏）：比屏幕还宽的大框，左沿滚出屏外的时候这两个字不出来 ——
        //    那时候认这个框靠它的品红边和框编号。这是有意的取舍，等小栋看图再定；不许偷偷夹回去。
        const lx = x0 + 6;
        if (x0 < 0 || lx > Math.min(x1, W) - 6) continue;
        // 框上沿在屏外（框比屏幕高）⇒ 从可见的那一段顶上写；再夹进画布内，免得只剩半行字
        let ly = Math.max(yt, 0) + 15;
        if (ly > H - 6) ly = H - 6;
        D.labels.push(haloText(ctx, lx, fitLabel(ctx, lx, ly, '升级', mine, H), '升级', upColor('seg'), 'left', mine));
      }
    }

    // ⑥ 级别对照（卡 card-01961644-68f，接口规则 L-9）：合成框跟**对照图**（后台 `levels.ref_tf`
    //    那一档，不是前端拿 4× 推的）的中枢对不上的
    //    那些，在**框的右沿**标一句短话（三档见 `lvTagText`）。★ 这是「升级」的**镜像**，四条一条不省：
    //      ① 锚点搬到**右边线内侧** `x1 - 6`、`align:'right'` —— 左边已经住着「升级」，两个挤一块儿；
    //      ② 右沿**出屏就一个字都不画**（`x1 > W` 也 skip），**绝不夹回来** —— 夹回来就是
    //         card-113a3b16-026 那个「钉在视口边上不动」的旧 bug 的翻版（那段长注释在 ⑤ 里）；
    //      ③ 只给**这一帧真画出来的框**写字：★ 这一条比「升级」难 —— `levels.units` 跟框**没有**共同的
    //         身份字段（见 `lvAligned`），只能**同下标**。所以不遍历 `D.units`（那是筛过的子集，按下标取
    //         会错位），改为**遍历 `T.units` 取下标的 `levels.units[i]`**，再把下面这几条**画框那一趟
    //         一模一样的判据**重放一遍（x/y 取不到、横向出屏、纵向出屏）—— 同一个谓词 ⇒ 被标的那几个框
    //         跟真画出来的那几个框**是同一批**。开关关着时整支不跑，也就没有「框没了、字还在」。
    //      ④ 让位走**同一张表**（`mine` + `fitLabel`）：跟「升级」不许压在一起，也不压这一层别的字。
    //    ★ 颜色是中性灰（`TREND.lv`）：它讲的是"跟另一张图对不上"，不是涨跌 —— 不跟价签抢读法。
    //    ★ 开关 `sh.lv`（默认开），而它跟 `up` 与过（合成框那一层不画就没有地方挂字，见 `shownOf`）。
    if (sh.lv) {
      const lv = state.levels;
      // 三道闸（框数／周期／档位）全过才拿得到能按下标取的数组；任何一条不过 ⇒ `null` ⇒ 一个字都不标。
      const us = lvAligned(T, lv, state.tf, state.span);
      if (us) {
        const refName = refTfName(lv.ref_tf);
        for (let i = 0; i < T.units.length; i++) {
          const txt = lvTagText(us[i], refName);
          if (!txt) continue;
          // ★ 下标 `i` 是**同一把尺子**量出来的那一个框：`us[i]` 是后台对它的结论，`T.units[i]` 才是
          //   画它用的几何（下面的判据跟 `trendBandView` ③ 那一趟逐条对应）。
          const u = T.units[i];
          const x0 = vp.xOfBar(u.X0), x1 = vp.xOfBar(u.X1);
          const yt = vp.yOfPrice(u.GG), yb = vp.yOfPrice(u.DD);
          if (x0 === null || x1 === null || yt === null || yb === null) continue;
          // 框整个出了屏 ⇒ 不画；★ 右沿出屏（`x1 > W`）也**不画** —— 这一句就是"不许夹回来"的牙
          //   （「升级」那头没有这一条是因为它锚在左沿；这一头锚在右沿，右沿出去了就没地方站）。
          if (x1 <= 0 || x0 >= W || x1 > W) continue;
          // 框纵向也整个出了屏 ⇒ 画面上根本没有这个框，别给它写字（跟 ⑤ 同一条）
          if (yb < 0 || yt > H) continue;
          // ★★ 上面那条右沿 guard 只管"**锚点**在屏内"；右对齐的字是往**左**铺的 —— 锚点离左沿太近时
          //   整块会被画布左边切掉（「升级」那头的对偶：它是锚在左沿、用 `x0 < 0 ⇒ continue` 守的）。
          //   ⇒ 量出这一句的宽，`lx - w < 0` 就整块不画。**不夹、不截**，跟右沿同一条规矩
          //     （夹回来就是 card-113a3b16-026 那个「钉在视口边上」的旧 bug）。
          ctx.font = FONT;
          const tw = ctx.measureText(txt).width;
          const lx = x1 - 6;
          if (lx - tw < 0) continue;
          // y 跟「升级」同一条规矩：贴着框上沿往下 15；框比屏幕高就落在可见那一段的顶上。
          let ly = Math.max(yt, 0) + 15;
          if (ly > H - 6) ly = H - 6;
          // ★ `fitLabel` 必须收到跟 `haloText` 同一个 `align`（'right'）：测的盒子和登记的盒子要同向，
          //   否则它会去躲右边、留下左边真压着的「升级」/框线/编号（Nova 指出，见 fitLabel 那段账）。
          D.labels.push(haloText(ctx, lx, fitLabel(ctx, lx, ly, txt, mine, H, 'right'), txt, TREND.lv, 'right', mine));
        }
      }
    }
    // 盘整组的段界刻度（卡 card-9f7a80b6-e8a）：落点是标注层这一帧算好的（`state.pzDrawn`），见 `drawPzGroups`。
    drawPzTop(ctx, state, mine, W);
  });
}

/** 盘整组段界上的刻度 ＋ `k/N`。刻度线照画（它是结构）；**字**先放刻度右边，跟已经画上去的字
 *  （这一层的 `mine`：分界价格／待定／撤回／编号…；标注层的 `placed`：价签／买卖点文字／组的 chip）
 *  **像素有交叠**就换一格（上右 → 上左 → 下右 → 下左），四格都撞就只画刻度不写字（Bram 22:02 定：交叠才修，贴着不算）。
 *  ★ 字不登记任何一张表：它是最后画的，后面没有谁要躲它。 */
function drawPzTop(ctx, state, mine, W) {
  const P = state.pzDrawn;
  if (!P || P.railY === null) return;
  // chip ＋ 「还有 n 段」：位置是标注层定的（chip 已登记 `placed`），这里只是**最后落笔**，压在分界虚线上面。
  for (const g of P.groups) {
    for (const c of g.chips) pzChipPaint(ctx, c.box, c.text, c.main);
    ctx.font = FONT_SM; ctx.fillStyle = TREND.mut; ctx.textBaseline = 'alphabetic';
    if (g.before) { ctx.textAlign = 'left'; ctx.fillText(`◀ 左边还有 ${g.before} 段`, 8, P.railY - 20); }
    if (g.after) { ctx.textAlign = 'right'; ctx.fillText(`右边还有 ${g.after} 段 ▶`, W - 8, P.railY - 20); }
    ctx.textAlign = 'left';
  }
  // ★ 左下角那块留给 LWC 的 TradingView 标（最底下那一格窗格才有，手机上价格窗格就是最底下那格）：
  //   它不在任何占位表里，刻度字翻到细轨下面时会撞上它 —— 当成一块占位，桌面上只是少用 60px，代价很小。
  const y = P.railY, others = [...mine, ...(state.labelBoxes || []), [0, P.H - 32, 60, P.H]];
  ctx.font = FONT;
  for (const g of P.groups) {
    g.tickLabels = [];
    for (const { k, x } of g.tickAt) {
      ctx.strokeStyle = TREND.edge; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(x, y - 8); ctx.lineTo(x, y + 4); ctx.stroke();
      const t = `${k}/${g.n}`, tw = ctx.measureText(t).width;
      // 四个候选格，按顺序取第一个不撞的：细轨上方 右 → 左 → 细轨下方 右 → 左。
      //   下方那两格是手机上量出来要的（390 宽 35 个刻度里 17 个四周都被**它自己那条分界的价格字**占了：
      //   窗格矮，低点贴着底，价格字正好落在细轨上方那一行，而且居中压着刻度两边）。
      const cand = [
        ['r', [x + 5, y - 15, x + 5 + tw, y - 1], x + 5, y - 4, 'left'],
        ['l', [x - 5 - tw, y - 15, x - 5, y - 1], x - 5, y - 4, 'right'],
        ['rb', [x + 5, y + 4, x + 5 + tw, y + 18], x + 5, y + 15, 'left'],
        ['lb', [x - 5 - tw, y + 4, x - 5, y + 18], x - 5, y + 15, 'right'],
      ];
      const ok = (b) => b[0] >= 2 && b[2] <= W - 2 && b[3] <= P.H - 1 && !hits(b, others);
      const pick = cand.find((c) => ok(c[1])) || null;
      if (pick) haloText(ctx, pick[2], pick[3], t, TREND.edge, pick[4]);
      // `blockedR`：右上那一格被别的字占了（只为工装：它得证明"撞了"那条路真走到过，不然 ㊾b 是空转）
      g.tickLabels.push({ k, side: pick ? pick[0] : null, box: pick ? pick[1] : null, blockedR: hits(cand[0][1], others) });
    }
  }
}

/** 带描边的一行字（参考图的 `paint-order: stroke` ＋ 3 px 白边，这边那圈是页面底色）。
 *  → 返回 [x0, y0, x1, y1, 字]：**只记不避让**，给工装去量（见 trendMarkView 开头那段账）。
 *  ★ `font` / `size` **必须是一套的**（`FONT_LET` 配 `SIZE_LET`）：包围盒是按 `size` 算的
 *    （基线上 `0.92×`／下 `0.25×`，12px 时正好是 11／3，跟老调用点一字不差）。
 *    ⇒ 光换 `font` 不给 `size`，量出来的框就是假的 —— 那种错不会红，只会让人量到错的东西。 */
function haloText(ctx, x, y, text, col, align, mine, font, size) {
  ctx.font = font || FONT;
  const sz = size || 12;
  ctx.textAlign = align || 'left';
  ctx.lineWidth = 3; ctx.strokeStyle = TREND.halo; ctx.lineJoin = 'round';
  ctx.strokeText(text, x, y);
  ctx.fillStyle = col;
  ctx.fillText(text, x, y);
  const w = ctx.measureText(text).width;
  ctx.textAlign = 'left';
  const x0 = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
  const box = [x0, y - Math.round(sz * 0.92), x0 + w, y + Math.round(sz * 0.25), text];
  if (mine) mine.push(box.slice(0, 4));            // 占位（只占位、不避让；避让见 fitLabel）
  return box;
}

/** 给「升级」（左对齐）和「级别对照」（右对齐）共用的让位：拿同一套 `fitBox` 在自己这张表上找一个
 *  不压人的基线（先上后下、最多 12 行，跟价签那条尺子是同一个函数）。找不到就按原位画 ——
 *  宁可压一点，也不许挪出画布。
 *  ★★ `align` 必须跟 `haloText` 收到的那一个**一模一样**（Nova 指出）：`fitBox` 只挪 y，可 x 是用来
 *    `hits()` 的 —— 盒子测错了方向，右对齐那句就会「不去躲它左边真压着的东西（升级／框线／编号），
 *    反倒空躲右边没东西的地方」。而且 `haloText` **登记**的是 `align` 修正后的盒子（`x0 = x - w`），
 *    测试盒子若还是 `[x, x+w]`，就变成"测的是一块、占的是另一块"—— 让位表当场说谎。
 *    ⇒ 这里跟 `haloText` 用同一行 `x0` 算法，两处永远同向。不传 `align` ＝ left（「升级」原样）。 */
function fitLabel(ctx, x, y, text, mine, H, align) {
  ctx.font = FONT;
  const w = ctx.measureText(text).width;
  const x0 = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
  return fitBox([x0, y - 11, x0 + w, y + 3], mine, H)[3] - 3;
}

// >>> FMT_G —— tools/web_fmt_check.py 把这一段抠出来单跑，逐值与 Python 的 `"%g" % round(v, 2)`
//     对账（抠不到就报红）。★ 判据只许有一处：格式的定义在 Python 那边，这边是它的同构实现。
/** 与 Python 的 `"%g" % round(z["ZD"], 2)` 逐字对齐 —— 中枢上下沿是判三买三卖的价
 *  （1681.99 显示成 1682 看起来像「破了」，其实没破），所以这里不是审美问题，是**读数**问题。
 *  语义照抄 C 的 `%g`（默认 6 位有效数字）：先两位小数，再去尾零；指数在 ≥1e6 或 <1e-4 时出现。
 *  ★ 不能写成 `String(Math.round(v))`：那是网页原来那版，1000 以上一律取整。
 *  ★ 取整那一步**不能交给 `toFixed` / `toPrecision`**：它俩的规则是「正好一半就进位」，
 *    而 Python 的 `round()` / `%g` 是「一半取偶」。实测 100000.5 两边差 1（Python `100000`、
 *    toFixed `100001`），123456.5 同理（`123456` 对 `123457`）—— 跟上面是**同一个病**：
 *    读数差 1 看着就像破了。所以这里把数字摊成 20 位有效数字的字符，第 7 位起自己判
 *    「是不是正好一半」，再按取偶走。这条由 `tools/web_fmt_check.py` 的值表＋探针钉住。
 *  ★ 已知且**碰不到**的差异：`-0.0`（Python 给 `-0`，这里给 `0`）—— 要走到得先有 −0.0 的价，
 *    那是数据出问题，不是格式问题；另见 web_fmt_check.py 头部关于「>2 位小数且卡在半位」那条。 */
export function fmtG(v) {
  if (!Number.isFinite(v)) return String(v);
  let x = Math.round(v * 100) / 100;                        // Python: round(v, 2)
  if (x === 0) return '0';
  const sign = x < 0 ? '-' : '';
  x = Math.abs(x);
  const str = x.toExponential(19);                          // 20 位有效数字（double 17 位就摊平，留 3 位余量）
  const E = Number(str.slice(str.indexOf('e') + 1));        // 首位数字的权 ⇒ x ≈ d[0].d[1…] × 10^E
  const dg = str.slice(0, str.indexOf('e')).replace('.', '');
  let head = Number(dg.slice(0, 6));                        // 6 位有效数字（整数 100000…999999）
  const tail = dg.slice(6);                                 // 第 7 位起 ⇒ 判「有没有过半」
  if (tail[0] > '5' || (tail[0] === '5' && (/[1-9]/.test(tail.slice(1)) || head % 2 === 1))) head += 1;
  let e = E;
  if (head === 1000000) { head = 100000; e += 1; }          // 进位跨过阈值：999999.5 → 1e+06
  if (e >= 6 || e < -4) {                                   // %g 的指数那一支
    const m = String(head).replace(/0+$/, '');
    return sign + (m.length > 1 ? m[0] + '.' + m.slice(1) : m) + 'e' + (e < 0 ? '-' : '+') + String(Math.abs(e)).padStart(2, '0');
  }
  let out = String(head);                                   // 十进制那一支：小数位 = 5 − e
  const pad = 5 - e;
  if (pad < 0) out += '0'.repeat(-pad);                     // e > 5：整数后面补零
  else if (pad > 5) out = '0.' + '0'.repeat(pad - 6) + out;  // 值 < 1：前面补零（0.0001 这种）
  else if (pad > 0) out = out.slice(0, 6 - pad) + '.' + out.slice(6 - pad);
  if (out.indexOf('.') >= 0) out = out.replace(/0+$/, '').replace(/\.$/, '');   // 去尾零（Python 的 %g 同）
  return sign + out;
}
// <<< FMT_G

/** ④.5 盘整组：相邻的盘整段在图上标成一组 ——「这几段是同一个更大的盘整」。出处：主引 L38 原博正文
 *  （非同级别分解下不允许盘整+盘整）和 `L45:60`（盘整+盘整就是中枢延伸、扩展出来的）；附 `L33:162`
 *  （镜像答疑：「盘整+盘整还是盘整，但加多了就是级别大的盘整」）。**分界一条不动**，只加记号。
 *  形态是 07:51Z 定的 C（卡上【实现要点】那一条），量出来的，不是挑的：
 *    · **细轨贴价格窗格底边**，不套框 —— 一屏装不下任何一组（ZEC 1h 一组跨十几屏），套框画不出来；
 *      `H` 是**这个窗格**的高（primitive 挂在 K 线那一格上），不是 `#chart` 的高（底下还有成交量／MACD）。
 *    · 组内每条**段界**一根刻度 ＋ `k/N` —— 一屏往往只落得下一两条界，刻度回答的是「我在组的哪儿」
 *      （落点在这儿算，**画在走势那一层的最后**，见 `drawPzTop`：要躲的分界价格字住在那一层）；
 *    · 主标签：组头在屏内就贴组头，组头滚出左边就**吸视口左边**（吸着组头等于没标签）；
 *    · 有段落在屏外时，右边再排一块「屏内 第 a–b 段」，两头写明「◀ 左边还有 n 段」「右边还有 n 段 ▶」。
 *  ★ 避让：两块 chip **最后登记** `placed`（买卖点文字 → 价签 → 我）⇒ `fitBox` 挪的是我，老标签一个像素不动。
 *    细轨、刻度、两头那两句**不登记**：整屏宽的一条线登记进去会把所有价签上下推（卡上量过）。
 *    挤不下就保持原样（`fitBox` 的 `return out`），那是"没地方放"，不是回归。
 *  ★ 归「走势分段」那颗芯片：组是走势段的事，芯片关了就一笔不画（命中格也清空）。 */
// 细轨离窗格底边 34：最底下那一格窗格的左下角是 LWC 的 TradingView 标（手机上价格窗格就是最底下那格），
//   标顶约在底边上 29 —— 贴得更低，「◀ 左边还有 n 段」和细轨都会被它盖住（390 宽实测截图）。
const PZ_RAIL = 34;
const FONT_PZ = 'bold 12px -apple-system, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif';
function drawPzGroups(ctx, state, sh, vp, placed, chart, W, H) {
  pzHits.canvas = ctx.canvas;
  pzHits.boxes = [];
  state.pzDrawn = { H, railY: null, groups: [] };
  const T = trendOf(state.data);
  if (!T || !sh.trend || !chart) return;
  const G = pzGroups(T);
  if (!G.length) return;
  const v = chart.timeScale().getVisibleLogicalRange();
  if (!v) return;
  const railY = Math.round(H - PZ_RAIL);
  state.pzDrawn.railY = railY;
  const xs = (i) => vp.xOfBar(i);
  for (const g of G) {
    if (g.i1 < v.from || g.i0 > v.to) continue;                 // 整组在屏外
    const w = pzWhere(g, v.from, v.to);
    const xa = xs(g.i0), xb = xs(g.i1);
    const leftOut = g.i0 < v.from, rightOut = g.i1 > v.to;
    // 细轨：两端在屏外就让它溢出（画布自己裁），**不夹回 0／W** —— 夹回来就成了"组只有这么宽"。
    const x0 = xa === null ? -10 : xa, x1 = xb === null ? W + 10 : xb;
    ctx.strokeStyle = rgba(TREND.mut, 0.7 * 255); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(x0, railY); ctx.lineTo(x1, railY); ctx.stroke();
    // 两端下钩（端点在屏内才画；在外的那头由「还有 n 段」那句交代）
    ctx.strokeStyle = TREND.mut;
    for (const [out, x] of [[leftOut, xa], [rightOut, xb]]) {
      if (out || x === null) continue;
      ctx.beginPath(); ctx.moveTo(x, railY - 10); ctx.lineTo(x, railY + 6); ctx.stroke();
    }
    // 段界刻度 k/N：**这里只算落点，画在走势那一层**（`drawPzTop`）。理由：刻度字要躲的是分界那几个价格字，
    //   而那些字住在走势那一层自己的占位表（`mine`）里、而且**在这一层之后才画** —— 在这儿画，同一帧里根本看不见它们。
    //   走势那层排在最后，画到它那儿时 `placed`（价签／买卖点文字／我的 chip）和它自己的 `mine` 都已经是这一帧的了。
    const ticks = [];
    for (let k = 1; k < g.n; k++) {
      const x = xs(g.ends[k - 1]);
      if (onScreen(x, W, 0)) ticks.push({ k, x });
    }
    // 主标签 ＋ 位置 chip
    const lx = leftOut || xa === null ? 8 : Math.max(8, xa + 6);
    const title = `同一更大横盘 · ${g.n} 段`;   // N＝2 也写「· 2 段」：Nova 21:28 定统一一种写法（Bram 22:02 审出代码跟 spec 两套）
    // 位置 chip 只在**有段落在屏外**时出：组头／组尾只是半截出屏、段一条没少的时候，「屏内 第 1–2 段」是废话。
    const pos = w.inView < g.n
      ? (w.inView === 1 ? `屏内 第 ${w.lo} 段` : `屏内 第 ${w.lo}–${w.hi} 段`) : null;
    const chips = [];
    let cx = lx;
    const top = railY - 56;                                       // chip 一行 → 「还有 n 段」一行 → 刻度字 → 细轨
    for (const [text, main] of [[title, true], [pos, false]]) {
      if (!text) continue;
      const box = pzChip(ctx, placed, cx, top, text, main, W, H);
      if (!box) continue;
      pzHits.boxes.push([...box, g]);
      chips.push({ text, box, main });
      cx = box[2] + 6;
    }
    // ★ chip、「还有 n 段」、刻度**这里都不画**：位置在这一层定（chip 要登记 `placed`），**笔画放到走势那一层最后**
    //   （`drawPzTop`）。走势那层排在这一层之后，它的分界竖虚线会从这儿画的字上横穿过去（手机实截：
    //   「屏内 第 6–7 段」中间被一根虚线劈开）。字要压在线上面，就得最后画。
    state.pzDrawn.groups.push({ n: g.n, from: g.from, to: g.to, i0: g.i0, i1: g.i1, leftOut, rightOut, ...w,
      ticks: ticks.map((t) => t.k), tickAt: ticks, tickLabels: [], chips });
  }
}

/** 一块 chip 的**落位**：量宽 → `fitBox` → 登记 `placed`，返回框（画在 `pzChipPaint`，见上）。
 *  ★ 不用 `tag()`：`tag()` 是**价签**（彩色实底黑字），价钱是这张图最响的一档，一句说明不能长得跟它一样。 */
function pzChip(ctx, placed, x, y, text, main, W, H) {
  ctx.font = main ? FONT_PZ : FONT;
  const tw = ctx.measureText(text).width;
  let box = [x, y, x + tw + 14, y + 20];
  if (box[2] > W - 2) return null;                       // 一行放不下就不画（不截字、不缩字）
  box = fitBox(box, placed, H);
  placed.push(box);
  return box;
}
/** chip 的笔画：页面底色实底 ＋ 静音灰细边 ＋ 亮字。画的框＝`pzChip` 登记的那个框。 */
function pzChipPaint(ctx, box, text, main) {
  ctx.font = main ? FONT_PZ : FONT;
  ctx.fillStyle = PAGE.bg;
  ctx.strokeStyle = rgba(TREND.mut, (main ? 0.9 : 0.6) * 255); ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect ? ctx.roundRect(box[0] + 0.5, box[1] + 0.5, box[2] - box[0] - 1, box[3] - box[1] - 1, 4)
    : ctx.rect(box[0] + 0.5, box[1] + 0.5, box[2] - box[0] - 1, box[3] - box[1] - 1);
  ctx.fill(); ctx.stroke();
  ctx.fillStyle = main ? PAGE.tx : TREND.mut;
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText(text, box[0] + 7, (box[1] + box[3]) / 2 + 0.5);
  ctx.textBaseline = 'alphabetic';
}

/** 线段的终点：未完成的画到**迄今的极值**（向上段最高、向下段最低），full_common 同一条 */
function segEnd(data, s) {
  // ★ 暂定段（S7 当场判，`tentative`）也带 `live`，但它的终点是**判出来的那一刀 V**（段的 i1/p1），不是迄今的极值：
  //   后面那一截才是真正还在走的未完成段（暂定之后不再往下切，见 core/segment.py）。
  if (!s.live || s.tentative) return { i: s.i1, p: s.p1 };
  const ext = s.dir === 'up' ? s.hi : s.lo;
  let k = s.PI0;
  for (let j = s.PI0; j <= s.PI1; j++) if (data.pens[j] && data.pens[j].p1 === ext) k = j;
  return { i: data.pens[k].i1, p: ext };
}

// >>> FIT_BOX  （被 tools/web_fitbox_check.py 抠出来跑：段内不许引用段外的东西 —— 只放纯函数和常量）
const NUDGE = 19;                    // 挪一行的步长（往上那条一直用它；往下的新那条同一条尺 —— 原 tag() 的 h+4：15 + 4）
const TAG_H = 15;                    // 价签框高（**没动**，2026-10-02 那版就是这个数）
// 买卖点文字框：基线上 11、基线下 4 ⇒ 高 15 ＝ **价签那一档**（横向同为 ±5）。
// 固定值，不按字量 —— 理由见下面 `drawSignalText` 的注释（含浏览器按字给不同字体框的实测）。
const SIG_UP = 11;
const SIG_DN = 4;

/** 框跟登记表里任一个相交？—— 避让判据**只有这一份**（上/下两条路共用） */
function hits(box, placed) {
  return placed.some((q) => box[0] < q[2] && q[0] < box[2] && box[1] < q[3] && q[1] < box[3]);
}

/** 整框移进视口 `[0, H]`（**不改高**）：上沿 < 0 往下压、下沿 > H 往上顶。
 *  网页是个视口，两头都没有 Python 整幅图的边距（顶上 `T = 300`、底下也留白）
 *  ⇒ 夹两头是**同一个**视口带来的偏离。 */
function intoPane(box, H) {
  if (box[1] < 0) return [box[0], 0, box[2], box[3] - box[1]];
  if (box[3] > H) return [box[0], box[1] - (box[3] - H), box[2], H];
  return box;
}

/** ★ 文字落框的**唯一**一份（价签和买卖点文字共用 —— 原先各写一遍，改一处漏一处）：
 *  ① **框不得出视口**：网页是个视口，没有 Python 整幅图顶上那 `T = 300` 的边距，
 *     最高的那个卖点本来就贴着顶边 ⇒ 照搬「往上挪」会把它整条推出画布（390px 实测过：y 挪到 −12/−31）。
 *     两头都夹（上沿压到 0 / 下沿顶到 H），**整框移、不改高**，夹完照样走下面的避让。
 *  ② 避让跟 `draw_labels` 同一条：与已登记的框重叠就往上挪一行（`font.size + 12` 的网页档＝19）。
 *     步数跟 Python 的 `for n in range(12)` 同构：**判 12 个候选行**（原位 ＋ 往上 11 格），
 *     第 12 次位移的结果不再判 —— 这一条是照搬，不是这里另立的规矩（下面往下那条一字不差地镜像它）。
 *  ③ **往上挪不动了就回头往下试**（同样 12 个候选行、同样不许出视口）—— Nova 2026-10-03 拍板。
 *     起因（第二条发现）：⑦ 给买卖点文字补上实体深底之后，「二卖」的框正好压住左上角价签的左半截
 *     （墨盒实测相交 22.5×3.75px），而那一簇已被顶边钉在 y=0 ⇒ 只会往上挪的避让在那儿一步都挪不动。
 *     两头都试完还是挤不下 ⇒ 停在往上那条的终点（跟改之前一样，不会更糟）。
 *  ④ 返回的框**就是**调用方要画的那个框：画的框和 `placed.push` 的框**同一个变量**
 *     （两处各写一遍式子就是「判据有两处」的老毛病）。
 *  ★ 坐标系（照抄 Python 的数字会差一个字高）：Python `draw_labels` 的 (x, y) 是**左锚 + 字顶**、
 *    框 = (x−6, y−2, x+tw+6, y+size+8)；网页 x 是**居中**（价签是左锚）、y 是 **alphabetic 基线**。
 *    所以这里只搬**判式**，框由各自的锚现算。 */
function fitBox(box, placed, H) {
  let out = intoPane(box, H);                                         // ① 先夹进视口
  for (let n = 0; n < 12; n++) {                                      // ② 跟 draw_labels 一样：最多 12 行
    if (!hits(out, placed)) return out;
    if (out[1] - NUDGE < 0) break;                                    // 再挪一步就出画布 ⇒ 这条路走到头
    out = [out[0], out[1] - NUDGE, out[2], out[3] - NUDGE];
  }
  let dn = intoPane(box, H);                                          // ③ 往上挪不动 ⇒ 从原位往下试
  for (let n = 0; n < 12; n++) {
    if (!hits(dn, placed)) return dn;
    if (dn[3] + NUDGE > H) break;                                     // 往下同样不许出画布
    dn = [dn[0], dn[1] + NUDGE, dn[2], dn[3] + NUDGE];
  }
  return out;                                                         // 两头都挤不下 ⇒ 保持原行为
}
// <<< FIT_BOX

// >>> TAG_BOX  （tools/web_fitbox_check.py 也抠这一段的**顺序**：夹右边界必须在 fitBox 之前）
function tag(ctx, placed, x, y, text, col, W, H) {   // placed 由调用方传：模块级函数看不见 primitive 的闭包
  ctx.font = FONT_SM;
  const tw = ctx.measureText(text).width;
  let box = [x, y - TAG_H, x + tw + 10, y];            // 几何没动：左锚，字从 x+5 起、右留 5
  // 右边界先夹、**再**避让（Atlas 2026-10-03 指出：原先的顺序是避让在前、推右边界在后，
  // 推回来的框没有再查一遍碰撞 ⇒ 可能直接压在已登记的框上。这是 6634be9 之前就在的老顺序。）
  // 夹的是**几何**（贴到 W−2），所以它该在避让**之前** —— 避让要看见的才是最后要画的那个框。
  // 反过来写的话，「画的框＝登记的框」还成立，但**避让看见的框**不是它，判据就漏了一处。
  if (box[2] > W - 2) box = [W - 2 - (box[2] - box[0]), box[1], W - 2, box[3]];
  box = fitBox(box, placed, H);                        // ★ 守卫（跟买卖点文字同一个）
  ctx.fillStyle = rgba(col, CHART.tag_fill);           // 实底
  ctx.fillRect(box[0], box[1], box[2] - box[0], box[3] - box[1]);
  ctx.fillStyle = CHART.tag_ink;                       // 黑字（两底都过 AA，见 style.py）
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText(text, box[0] + 5, (box[1] + box[3]) / 2 + 0.5);
  placed.push(box);                                    // ★ 与 fillRect 同一个 box
}
// <<< TAG_BOX

// ★ 2026-10-06 退了一个 `tagRight`（右锚的签）：它只服务标注层 ③.5 那条「待定」竖线，那条路跟着
//   `cuts[]` 一起退了（卡 card-3edd7fb3-412）。将来要挂右锚的签，`tag()` 那一份框式子照旧能用，
//   右锚 = 左锚减去字宽（见 ③.5 退掉的那一版的 git 历史）。

/** 买卖点的**三角**（只画形状）。文字拆到 `drawSignalText` —— 拆开是为了让三角先落地、
 *  文字最后走 `placed`，跟 Python `draw_signals()` 与 `draw_labels()` 的分工同构。 */
function drawSignalGlyph(ctx, x, y, s, tier) {
  const buy = s.kind.endsWith('买');
  const base = buy ? CHART.buy : CHART.sell;
  const a = s.confirmed ? SIG.confirmedAlpha : SIG.pendingAlpha;
  const sz = tier === 'seg' ? SIG.segSize * 0.55 : SIG.penSize * 0.55;   // 屏幕尺寸：按 pine/屏幕缩到 0.55
  const d = buy ? 1 : -1;                                                // 买点在下、卖点在上
  const tip = y + d * (SIG.tip * 0.6), y0 = y + d * (SIG.tip * 0.6 + 2 * sz);
  ctx.beginPath();
  ctx.moveTo(x, tip); ctx.lineTo(x - sz, y0); ctx.lineTo(x + sz, y0); ctx.closePath();
  if (tier === 'seg') { ctx.fillStyle = rgba(base, a); ctx.fill(); }
  else { ctx.strokeStyle = rgba(base, a); ctx.lineWidth = 1.5; ctx.stroke(); }
  return y0;                                                             // 文字要挂在三角的底边
}

/** 「曾经有过、后来没了」的那个点（卡 card-cf3ed018-795）：**空心三角 ＋ 划一刀**。
 *
 *  为什么不是「把三角调淡一点」：这个图上**空心三角已经名花有主**了 —— 空心的那支是
 *  「类中枢层（·笔）」（见图例）。再让幽灵也空心、只靠深浅分，屏幕上就有三种点共用两种形状，
 *  而深浅差是最先消失的那种差别（缩略图、手机、弱光）。所以幽灵必须有一个**别人没有的形状**：
 *  三角上划一刀。它读作「这个标记作废了」，而且**实心那支（线段中枢层）的幽灵也会变空心** ——
 *  「曾经是什么」和「现在是什么」不许长得一样。
 *
 *  位置就画在它**当初被画的**那个 (时间, 价格) 上，不挪到别处：
 *  这不是重放的点（第二步那个离线标注文件才是），它就是**这一张图、这一次打开**里画过又撤掉的那一个，
 *  画回原位才是它（「我刚才在这儿看见一个卖点」—— 用户认的是那个位置）。
 *  代价是它落在价格轴上，看起来像句「这里能交易」的断言 —— 所以旁边三样东西一起兜着：
 *  形状（划掉了）、图例里那一格、悬停那句「这个点 … 出现过、后来消失了」，以及图脚「本次打开」那个数。
 *
 *  没有文字（不像真的买卖点带「一买」/「·笔」）：文字要走 `placed` 跟价签互相避让，
 *  让一批作废的点去挤价签不值得；它是谁、什么时候没的，悬停里说。 */
function drawSignalGhost(ctx, x, y, s, tier) {
  const buy = s.kind.endsWith('买');
  const base = buy ? CHART.buy : CHART.sell;
  const sz = tier === 'seg' ? SIG.segSize * 0.55 : SIG.penSize * 0.55;   // 大小仍按层级分：它当初是哪个层级，还认得出
  const d = buy ? 1 : -1;
  const tip = y + d * (SIG.tip * 0.6), y0 = y + d * (SIG.tip * 0.6 + 2 * sz);
  ctx.strokeStyle = rgba(base, SIG.ghostAlpha);
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(x, tip); ctx.lineTo(x - sz, y0); ctx.lineTo(x + sz, y0); ctx.closePath();
  ctx.stroke();
  // 那一刀：从左下划到右上，**两头各探出 2px** —— 探出去才读得成「划掉」，停在顶点上读起来像三角自己的一条边。
  // 方向**不跟着买/卖翻**（买卖那一对三角是上下镜像的）：同一个记号在整张图上得长一个样。
  const top = Math.min(tip, y0) - 2, bot = Math.max(tip, y0) + 2;
  ctx.beginPath();
  ctx.moveTo(x - sz - 2, bot); ctx.lineTo(x + sz + 2, top);
  ctx.stroke();
  return [x - sz - 3, top - 1, x + sz + 3, bot + 1];                     // 命中格：整个记号 ＋ 一点余量
}

/** 买卖点的**文字**：底色跟 Python 的默认那支一样是 `BG + (215,)` ——
 *  Python 那边它走 `draw_labels()` 的**默认背景**（`full_common.py:212`：不给第四项就 `bg = BG + (215,)`），
 *  网页当初**只搬了「登记」、没搬「底色」**，所以字直接压在 K 线上。
 *  ★ 补底色不是装饰：登记的框就是判据量的那个框 —— 裸字时那圈留白是看不见的，
 *    有了底色，**画的框 = 登记的框**，判据和被量的东西才是同一个东西（Nova 2026-10-03 拍板，第 7 项）。
 *  框：横向 ±5、纵向**固定 11/4**（高 15）—— 两轴都是**价签那一档**（`tag()` 就是 ±5 / 15），
 *  一个标签类型一套留白，不再按字量。
 *  ★ 为什么不按字量（Nova 2026-10-03 拍板）：这台浏览器的 `fontBoundingBoxAscent/Descent`
 *    **帧内按字给不同的值** —— 同一个 ctx、同一个 font 字符串、同一帧里量，「一卖」给 8.05/7.95、
 *    后面几条给 12/4（两者和都是 16）。和相同 ⇒ 框高看不出问题，但**基线在框里的位置差 4px**，
 *    那一格的字会明显偏上。这条**不在本支里追**，记在卡上当发现；本支改成固定框，
 *    框是「壳」，留白不该由里面写的是哪两个字决定。
 *  ★ 这里**有意不照字面搬** Python 的框高，账写在这儿（复核时按这行看）：
 *    Python `f_n = F(24)`、PIL `ascent 26 / descent 7`，框 = `[字顶−2, 字顶+size+8]` ⇒ 高 **size+10 = 34 = 1.42em**
 *    （ink 外留白 8 上 / 3 下）。那个 `+10` 是**绝对像素**、给 24px 字号调的；照字面搬到网页 11px
 *    ⇒ 高 21 = **1.91em**，形状就变了。网页这一版当初搬 `tag()` 时用的就是**固定档**
 *    （11px 配 15 高的价签框 = 1.36em）；这里同样取 15 —— Python 那边两种标签**本来就同高**
 *    （同一个框式子），同构的是这个。
 *  `ty = 框底 − 4` 是 alphabetic 基线 —— 没被夹/没被挪时它就等于原来的锚点（**字位不许漂**）；
 *  被夹顶边时字**跟着框一起下来**（否则框进了画布、字还是被切，第 1 项就白做了）。
 *  避让/夹边都走 `fitBox()`，跟价签同一个守卫（原先这里另写了一份，两处各一套就是老毛病）。 */
function drawSignalText(ctx, placed, x, y0, s, tier, H) {
  const buy = s.kind.endsWith('买');
  const base = buy ? CHART.buy : CHART.sell;
  const txt = sigLabel(s, tier);
  ctx.font = FONT_SM;
  const tw = ctx.measureText(txt).width;
  const anchor = y0 + (buy ? 13 : -6);                                   // 原来的字位，不许漂
  const box = fitBox([x - tw / 2 - 5, anchor - SIG_UP, x + tw / 2 + 5, anchor + SIG_DN], placed, H);
  const ty = box[3] - SIG_DN;                                            // 基线由框反推 ⇒ 画的框就是登记的框
  ctx.fillStyle = rgba(PAGE.bg, 215);                                    // Python: draw_labels 默认 bg = BG+(215,)
  ctx.fillRect(box[0], box[1], box[2] - box[0], box[3] - box[1]);
  ctx.fillStyle = s.confirmed ? base : rgba(base, 180);
  ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
  ctx.fillText(txt, x, ty);
  ctx.textAlign = 'left';
  placed.push(box);                                                      // ★ 与 fillRect 同一个 box

}

/** 买卖点的字。★ M29 以后二类带 `why`（core/signals.py，Atlas m29-code）：
 *    不创新低／不创新高 ⇒ 就是「二买／二卖」；创新低（高）＋盘整背驰 ⇒ 「二买·盘背」；
 *    小转大（走势层 xzd_seconds）⇒ 「二买·小转大（事后才确认）」，创新了又有盘整背驰的在「小转大」后面加「·盘背」。
 *  其余（一类、三类、不创新的二类）不加字。★ `weak`／「(弱)」第六批 ② 下线（后台 Bram weak-off 636d5b3 不再出这个字段，
 *    「创新低／创新高」改从 `why` 读）—— 这里原来那条「没 why 就退回 weak」的路一起拆掉。 */
export function sigLabel(s, tier) {
  const w = typeof s.why === 'string' ? s.why : '';
  let tag;
  // 小转大：固定带「（事后才确认）」、不写日期（Nova 10-08 16:46 定）—— 点画在第二段终点，可当时并不知道那一刀是小转大；
  //   具体哪天才出现只放在给小栋的图上（Bram m29-figs），后台也不带这个字段（Atlas c84a098 去掉了 known_bar）。
  if (w.startsWith('小转大')) tag = '·小转大' + (w.includes('盘整背驰') ? '·盘背' : '') + '（事后才确认）';
  else if (w.includes('盘整背驰')) tag = '·盘背';
  else tag = '';
  return s.kind + tag + (tier === 'pen' ? '·笔' : '') + (s.confirmed ? '' : SIG.pendingMark);
}

// ---------------------------------------------------------------------------
// 入门防守（T13，均线.md 六.7；后台 /api/wolf，卡 card-441d2f86-db3）：MACD 两条线都在 0 轴下的区间。
// ★ 画成**贴格底的一条窄带**，不铺满全高：全高那一层已经归「走势分段」（绿／红背景带），两层都铺满
//   就叠成一片浑色，谁也读不出来；格顶那条窄带归「中阴／等确认」。格底这条是空着的，正好给它。
// ★ 色取 SUB.dn（MACD 负柱那个色）：这条带讲的就是「黄白线在 0 轴下」，跟副图负柱同一件事、同一个色。
// ★ 区间按**时间**给（[t0 毫秒, t1 毫秒 或 null]）：周期由用户另选，可能跟这张图不是一个周期，
//   所以不能按根数对。落到这张图上取「t ≥ t0 的第一根」到「t ≤ t1 的最后一根」；t1 为 null ＝ 到现在还在下面。
// ★ 这一层**不进任何判据**，图上只是一条提示；左端那句字把这件事说出来。
export const WOLF_STRIP = 6;          // 带高（px）；量图的工装认这个数
export function makeWolfPrimitive(state) {
  return {
    attached(p) { this._chart = p.chart; this._series = p.series; this._request = p.requestUpdate; },
    detached() {},
    updateAllViews() {},
    paneViews() {
      // ★ 挂 `top`：格底那一截是成交量柱的地盘（主图下沿），挂 bottom 会整条压在量柱底下看不见（1440 实截过）。
      return [{ zOrder: () => 'top', renderer: () => ({ draw: (t) => wolfView(t, state, this) }) }];
    },
  };
}
function wolfView(target, state, prim) {
  const w = state.wolf, data = state.data;
  state.wolfDrawn = [];                              // 只读出口：这一帧画了哪几段（量，不靠眼睛）
  if (!w || !w.on || !Array.isArray(w.below) || !data || !data.bars || !data.bars.length) return;
  target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
    const W = mediaSize.width, H = mediaSize.height;
    const vp = viewport(prim._chart, state.candleSeries || prim._series, data);
    const ts = data.bars.map((b) => b.t), n = ts.length;
    const firstGE = (t) => { let lo = 0, hi = n; while (lo < hi) { const m = (lo + hi) >> 1; if (ts[m] < t) lo = m + 1; else hi = m; } return lo; };
    const lastLE = (t) => firstGE(t + 1) - 1;
    const y0 = H - WOLF_STRIP;
    // ★ 后台没算到的那一截（from_t 之前；用户选的周期比图细、span 被钳时会有）：同一条道上画**斜线灰**，
    //   跟「站上 0 轴」（空着）分得开 —— 空着说的是「算了，不在下面」，斜线说的是「没算」。
    let uncomputed = false;
    if (typeof w.fromT === 'number' && ts[0] < w.fromT) {
      const iEnd = firstGE(w.fromT) - 1;
      const xa = vp.xOfBar(0), xb = vp.xOfBar(Math.min(iEnd, n - 1));
      if (xa !== null && xb !== null && xb >= 0) {
        const x0 = Math.max(0, xa - vp.spacing / 2), x1 = Math.min(W, xb + vp.spacing / 2);
        ctx.save();
        ctx.beginPath(); ctx.rect(x0, y0, x1 - x0, WOLF_STRIP); ctx.clip();
        ctx.fillStyle = rgba(PAGE.bg, 255); ctx.fillRect(x0, y0, x1 - x0, WOLF_STRIP);
        ctx.strokeStyle = rgba(PAGE.mu, 150); ctx.lineWidth = 1;
        ctx.beginPath();
        for (let x = x0 - WOLF_STRIP; x < x1; x += 4) { ctx.moveTo(x, y0 + WOLF_STRIP); ctx.lineTo(x + WOLF_STRIP, y0); }
        ctx.stroke(); ctx.restore();
      }
      uncomputed = true;
    }
    let labelX = 44;                                 // 让开左下角 TradingView 那枚标（MACD 副图关着时它就落在主图这一格左下角）
    for (const [t0, t1] of w.below) {
      const i0 = firstGE(t0), i1 = t1 == null ? n - 1 : lastLE(t1);
      if (i0 >= n || i1 < 0 || i1 < i0) continue;   // 整段落在这份数据外面
      const half = vp.spacing / 2;
      const xa = vp.xOfBar(i0), xb = vp.xOfBar(i1);
      if (xa === null || xb === null) continue;
      const x0 = xa - half, x1 = xb + half;
      if (x1 < 0 || x0 > W) continue;
      // 先垫一层底色再铺色：这一截下面是量柱，不垫的话红量柱和这条带混成一片（1440 实截过，读不出哪段是带）。
      //   代价：带所在的那几段，量柱最底下 6px 被盖住 —— 量柱读的是高度，底下 6px 不改读数。
      ctx.fillStyle = rgba(PAGE.bg, 255);
      ctx.fillRect(x0, y0, x1 - x0, WOLF_STRIP);
      ctx.fillStyle = rgba(SUB.dn, 190);
      ctx.fillRect(x0, y0, x1 - x0, WOLF_STRIP);
      state.wolfDrawn.push({ i0, i1, open: t1 == null });
    }
    const extra = uncomputed && w.fmt ? `只算到 ${w.fmt(w.fromT)} 之后` : '';
    if (w.label) {
      // 左下角固定一处（开着就写，滚动时不跟着跳）。字底下垫一块底色（量柱就在这一截，不垫读不清）。
      // ★ 一行放不下（手机 390 上「只算到 …」那半句接上去会出画布）就折成两行，后半句在上面那一行。
      ctx.font = '11px system-ui, sans-serif';
      ctx.textBaseline = 'bottom'; ctx.textAlign = 'left';
      const one = extra ? `${w.label} · ${extra}` : w.label;
      const lines = ctx.measureText(one).width <= W - labelX - 8 ? [one] : [extra, w.label].filter(Boolean);
      lines.forEach((line, k) => {
        const yb = y0 - 3 - (lines.length - 1 - k) * 15;
        const tw = ctx.measureText(line).width;
        ctx.fillStyle = rgba(PAGE.bg, 220);
        ctx.fillRect(labelX - 3, yb - 14, tw + 6, 15);
        ctx.fillStyle = rgba(PAGE.mu, 255);
        ctx.fillText(line, labelX, yb);
      });
    }
  });
}
