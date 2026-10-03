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
            target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
              const W = mediaSize.width;
              const vp = viewport(this._chart, state.candleSeries || this._series, data);
              for (const tier of ['pen', 'seg']) {              // 类中枢先、线段中枢后
                const on = tier === 'seg' ? opts.sc : opts.pc;
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
                  if (opts.up && bx.z.up && bx.z.up.length) {
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
            target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
              const W = mediaSize.width;
              const vp = viewport(this._chart, state.candleSeries || this._series, data);
              placed.length = 0;

              // ① 线段端点：顶红底绿（full_common 的 ellipse，半径 9 / 描边 4）
              if (opts.seg) {
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
              if (opts.sig) {
                for (const tier of ['seg', 'pen']) {
                  for (const s of data.signals?.[tier] || []) {
                    if (!opts.sigKinds[s.kind]) continue;
                    if (!s.confirmed && !(opts.sigPend && CHART.sig_pending)) continue;
                    const x = vp.xOfBar(s.bar), y = vp.yOfPrice(s.price);
                    if (!onScreen(x, W, 40) || y === null) continue;
                    sigs.push({ x, y0: drawSignalGlyph(ctx, x, y, s, tier), s, tier });
                  }
                }
              }

              // ③ 价签：线段中枢先（优先占位），类中枢后；升级标签跟着各自的框走
              //    （跟 Python 同序：`center_labels` 里价签在前、买卖点文字在后 ⇒ 价签优先占位）
              for (const tier of ['seg', 'pen']) {
                const on = tier === 'seg' ? opts.sc : opts.pc;
                if (!on) continue;
                const col = tier === 'seg' ? CHART.seg : CHART.pen;
                for (const bx of boxes(data, tier)) {
                  const x = vp.xOfBar(bx.i0), y = vp.yOfPrice(bx.z.ZG);
                  if (!onScreen(x, W, 8) || y === null) continue;   // 框滚出去了，价签也跟着走
                  tag(ctx, placed, x + 8, y - 8, `[${fmt(bx.z.ZD)}, ${fmt(bx.z.ZG)}]`, col, W);
                  if (opts.up && bx.z.up) {
                    for (const u of bx.z.up) {
                      const uy = vp.yOfPrice(u.ZG);
                      if (uy === null) continue;
                      const ucol = tier === 'seg' ? CHART.up_seg : CHART.up_pen;
                      tag(ctx, placed, x + 8, uy - 8, `↑高${'一两三四'[u.up - 1]}级 [${fmt(u.ZD)}, ${fmt(u.ZG)}]`, ucol, W);
                    }
                  }
                }
              }

              // ④ 买卖点**文字**：最后画，跟价签共用 `placed` ⇒ 文字之间互相避让、价签也避开它；
              //    压在三角上面 ⇒ 数字/字完整可读（与 Python 出图的结论一致）。
              //    `y0` 是②里画三角时算出来的底边 —— 传过来，免得「文字挂在哪条边」这个式子写两份。
              for (const g of sigs) drawSignalText(ctx, placed, g.x, g.y0, g.s, g.tier);

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

function fmt(v) { return Math.abs(v) >= 1000 ? String(Math.round(v)) : String(Math.round(v * 100) / 100); }

/** 线段的终点：未完成的画到**迄今的极值**（向上段最高、向下段最低），full_common 同一条 */
function segEnd(data, s) {
  if (!s.live) return { i: s.i1, p: s.p1 };
  const ext = s.dir === 'up' ? s.hi : s.lo;
  let k = s.PI0;
  for (let j = s.PI0; j <= s.PI1; j++) if (data.pens[j] && data.pens[j].p1 === ext) k = j;
  return { i: data.pens[k].i1, p: ext };
}

function tag(ctx, placed, x, y, text, col, W) {   // placed 由调用方传：模块级函数看不见 primitive 的闭包
  ctx.font = FONT_SM;
  const w = ctx.measureText(text).width + 10, h = 15;
  for (let n = 0; n < 12; n++) {                       // 跟 draw_labels 一样：最多往上挪 12 行
    const box = [x, y - h, x + w, y];
    const hit = placed.some((q) => box[0] < q[2] && q[0] < box[2] && box[1] < q[3] && q[1] < box[3]);
    if (!hit) break;
    y -= h + 4;
  }
  if (x + w > W - 2) x = W - 2 - w;
  ctx.fillStyle = rgba(col, CHART.tag_fill);           // 实底
  ctx.fillRect(x, y - h, w, h);
  ctx.fillStyle = CHART.tag_ink;                       // 黑字（两底都过 AA，见 style.py）
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText(text, x + 5, y - h / 2 + 0.5);
  placed.push([x, y - h, x + w, y]);
}

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

/** 买卖点的**文字**：无底色的那种标签，但**照样登记进 `placed`** ——
 *  Python 那边它走的是 `draw_labels()` 的默认背景那一支（`bg = BG + (215,)`），
 *  所以「登记」这件事它本来就有，只是网页当初没搬。避让节奏跟 `tag()` 用同一档（往上挪一行 19px），
 *  这样价签和文字挪在同一个网格上，不会一个挪 19、一个挪 36。 */
function drawSignalText(ctx, placed, x, y0, s, tier) {
  const buy = s.kind.endsWith('买');
  const base = buy ? CHART.buy : CHART.sell;
  const txt = s.kind + (s.weak ? SIG.weakText : '') + (tier === 'pen' ? '·笔' : '') + (s.confirmed ? '' : SIG.pendingMark);
  ctx.font = FONT_SM;
  const tw = ctx.measureText(txt).width;
  const h = 15;                                                          // 与 tag() 同高
  const anchor = y0 + (buy ? 13 : -6);                                   // 原来的字位，不许漂
  // ★ 挪动**只许在画布里**（2026-10-03）：Python 那张整幅图都在画布上、顶上还留着 `T = 300`
  //   的边距，所以「往上挪 12 行」怎么挪都还在图里；网页是个**视口**，最高的那个卖点本来就
  //   贴着顶边，照搬 12 行会把这个位置的标签**整条挪出画布** —— 不是被压住，是根本看不见
  //   （390px 实测：两个文字框 y 挪到 -12 和 -31，后者整框在画布外，图上什么都没了）。
  //   所以：候选位只接受**整框都在画布内**的；一个都不接受就退回锚点位、照实重叠 ——
  //   那正是没接 placed 之前的样子，不会比修前更差。
  let ty = anchor;
  for (let n = 0; n < 12; n++) {                                         // 同 draw_labels：最多挪 12 行
    const bx = [x - tw / 2 - 5, ty - h, x + tw / 2 + 5, ty + 4];
    if (!placed.some((q) => bx[0] < q[2] && q[0] < bx[2] && bx[1] < q[3] && q[1] < bx[3])) break;
    if (ty - h - (h + 4) < 0) { ty = anchor; break; }                    // 再挪一步就出画布 ⇒ 回锚点
    ty -= h + 4;                                                         // 12 行都占着 ⇒ 停在第 12 行（同 Python）
  }
  ctx.fillStyle = s.confirmed ? base : rgba(base, 180);
  ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
  ctx.fillText(txt, x, ty);
  ctx.textAlign = 'left';
  placed.push([x - tw / 2 - 5, ty - h, x + tw / 2 + 5, ty + 4]);
}
