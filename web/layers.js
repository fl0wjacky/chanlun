// 结构层：中枢框（含「拆两截」）、价签、买卖点、未收盘那根。
//
// lightweight-charts 自带的只有 K 线与折线；中枢的**水平带 + 分截虚实**、价签的实底黑字、
// 买卖点的空心/实心三角，都得自己往画布上画 —— 这就是这个文件。
//
// 画法不是重新设计的，是 `render/full_common.py` 一行行搬过来的：box_split 的三档（规则 B）、
// draw_signals 的尺寸与偏移、draw_labels 的「先到先得往上挪最多 12 行」。搬的时候保持同构，
// 是为了以后改 Python 那版时能一眼看出这边该改哪一段。
import { CHART, CANDLE, DASH, PAGE, SIG, WIDTH } from './theme.js';

// ---- 小工具 ----
const hex2rgb = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
const rgba = (h, a) => { const [r, g, b] = hex2rgb(h); return `rgba(${r},${g},${b},${a / 255})`; };
const lighter = (h, d = 40) => '#' + hex2rgb(h).map((v) => Math.min(255, v + d).toString(16).padStart(2, '0')).join('');

const FONT = '12px -apple-system, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif';
const FONT_SM = '11px -apple-system, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif';

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
export function shownOf(opts) {
  const o = opts || {}, kinds = o.sigKinds || {};
  return {
    pen: !!o.pen, seg: !!o.seg, pc: !!o.pc, sc: !!o.sc, up: !!o.up,
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
// 框层：类中枢（与笔同色）→ 线段中枢（与线段同色）→ 各自的「↑高N级」框
// 挂在 K 线系列上、zOrder=bottom ⇒ 画在 K 线底下，跟 Python 的落笔次序一致（框先、K 线后）。
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
            const { data, opts } = state;
            if (!data || !this._chart) return;
            const sh = shownOf(opts);        // 开关只在这里读一次（判据那半边走的是同一个函数）
            target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
              const W = mediaSize.width;
              const vp = viewport(this._chart, state.candleSeries || this._series, data);
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
                  drawFrame(ctx, x0, yt, x1, yb, col, w, fill, splitAt, solid, W);
                  if (sh.up && bx.z.up && bx.z.up.length) {
                    for (const u of bx.z.up) {                  // 高一级别：满 9 段（第 33 课）
                      const uyt = vp.yOfPrice(u.ZG), uyb = vp.yOfPrice(u.ZD);
                      if (uyt === null || uyb === null) continue;
                      const ucol = tier === 'seg' ? CHART.up_seg : CHART.up_pen;
                      // 升级框**不跟着拆两截**：高一级的「前三笔」没有定义（Python 同）
                      drawFrame(ctx, x0, uyt, x1, uyb, ucol, w, CHART.up_fill, null, !bx.z.live, W);
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

function drawFrame(ctx, x0, ytop, x1, ybot, col, width, fillAlpha, splitAt, solid, W) {
  if (x0 > x1) [x0, x1] = [x1, x0];
  const y0 = Math.min(ytop, ybot), y1 = Math.max(ytop, ybot);
  // 填充整块只铺一次（Python 的注释：两截各铺一遍会在分界处叠出一条深缝）
  ctx.fillStyle = rgba(col, fillAlpha);
  ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
  ctx.strokeStyle = rgba(col, 235);
  ctx.lineWidth = width;
  const split = splitAt !== null && splitAt !== undefined && splitAt > x0 && splitAt < x1 ? splitAt : null;
  const edges = split === null
    ? [[x0, y0, x1, y0, solid], [x0, y1, x1, y1, solid], [x0, y0, x0, y1, solid], [x1, y0, x1, y1, solid]]
    : [[x0, y0, split, y0, true], [x0, y1, split, y1, true], [x0, y0, x0, y1, true],
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
            const sh = shownOf(opts);        // 开关只在这里读一次（判据那半边走的是同一个函数）
            target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
              const W = mediaSize.width;
              const H = mediaSize.height;   // 视口下沿 —— 夹框/避让要两头都不出画布（见 fitBox）
              const vp = viewport(this._chart, state.candleSeries || this._series, data);
              placed.length = 0;

              // ① 线段端点：顶红底绿（full_common 的 ellipse，半径 9 / 描边 4）
              if (sh.seg) {
                for (const s of data.segs) {
                  const end = segEnd(data, s);
                  const pts = [[s.i0, s.p0], [end.i, end.p]];
                  const up = s.dir === 'up';
                  for (const [k, [i, p]] of pts.entries()) {
                    const x = vp.xOfBar(i), y = vp.yOfPrice(p);
                    if (!onScreen(x, W, 20) || y === null) continue;
                    ctx.beginPath(); ctx.arc(x, y, 4.5, 0, Math.PI * 2);
                    ctx.fillStyle = PAGE.bg; ctx.fill();
                    ctx.strokeStyle = (k === 0 ? up : !up) ? CHART.buy : CHART.sell;
                    ctx.lineWidth = 2; ctx.stroke();
                  }
                }
              }

              // ② 买卖点：**这一步只画三角**，文字留到 ④（判据在 core/signals.py，前端只画）
              //    ★ 次序是 2026-10-03 改的，改的就是次序：
              //      Python 在 chart_full_smooth.py:68 先 `draw_signals()` 画三角，然后把文字标签请求
              //      **并进 `center_labels`**，:72 跟中枢价签**同一次** `draw_labels(d, center_labels, f_n, CY, placed)`
              //      画出来 ⇒ ① 文字最后画、**压在三角上面**；② 买卖点文字和中枢价签**共用一个 placed**、互相避让。
              //      网页原来把「三角 ＋ 文字」一起放在价签**之后**画 ⇒ 三角压在价签上，价签数字被盖掉
              //      （390px 实测：倒三角把 `[1004, 1682]` 中间两位整个吃掉）。搬的时候丢了「文字走同一个注册表」这半。
              const sigs = [];
              if (sh.sig) {
                for (const tier of ['seg', 'pen']) {
                  for (const s of data.signals?.[tier] || []) {
                    if (!sh.sigAt(s)) continue;   // 大开关 ＋ kind chip ＋ 待确认，全在 shownOf 里
                    const x = vp.xOfBar(s.bar), y = vp.yOfPrice(s.price);
                    if (!onScreen(x, W, 40) || y === null) continue;
                    sigs.push({ x, y0: drawSignalGlyph(ctx, x, y, s, tier), s, tier });
                  }
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
                      const ucol = tier === 'seg' ? CHART.up_seg : CHART.up_pen;
                      tag(ctx, placed, x + 8, uy - 8, `↑高${'一两三四'[u.up - 1]}级 [${fmtG(u.ZD)}, ${fmtG(u.ZG)}]`, ucol, W, H);
                    }
                  }
                }
              }

              // ④ 买卖点**文字**：最后画，跟价签共用 `placed` ⇒ 文字之间互相避让、价签也避开它；
              //    压在三角上面 ⇒ 数字/字完整可读（与 Python 出图的结论一致）。
              //    `y0` 是②里画三角时算出来的底边 —— 传过来，免得「文字挂在哪条边」这个式子写两份。
              for (const g of sigs) drawSignalText(ctx, placed, g.x, g.y0, g.s, g.tier, H);

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

/** 线段的终点：未完成的画到**迄今的极值**（向上段最高、向下段最低），full_common 同一条 */
function segEnd(data, s) {
  if (!s.live) return { i: s.i1, p: s.p1 };
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
  const txt = s.kind + (s.weak ? SIG.weakText : '') + (tier === 'pen' ? '·笔' : '') + (s.confirmed ? '' : SIG.pendingMark);
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
