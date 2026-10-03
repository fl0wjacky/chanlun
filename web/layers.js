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
  const placed = [];                       // 这一帧已经占位的价签框：先到先得，重叠就往上挪
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

              // ② 价签：线段中枢先（优先占位），类中枢后；升级标签跟着各自的框走
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

              // ③ 买卖点：两层各一份（判据在 core/signals.py，前端只画）
              if (opts.sig) {
                for (const tier of ['seg', 'pen']) {
                  for (const s of data.signals?.[tier] || []) {
                    if (!opts.sigKinds[s.kind]) continue;
                    if (!s.confirmed && !(opts.sigPend && CHART.sig_pending)) continue;
                    const x = vp.xOfBar(s.bar), y = vp.yOfPrice(s.price);
                    if (!onScreen(x, W, 40) || y === null) continue;
                    drawSignal(ctx, x, y, s, tier);
                  }
                }
              }

              // ④ 未收盘的最后一根：虚线框 + 「未收盘」（Python dashed_rect + 琥珀字）
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

function drawSignal(ctx, x, y, s, tier) {
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
  const txt = s.kind + (s.weak ? SIG.weakText : '') + (tier === 'pen' ? '·笔' : '') + (s.confirmed ? '' : SIG.pendingMark);
  ctx.font = FONT_SM;
  ctx.fillStyle = s.confirmed ? base : rgba(base, 180);
  ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
  ctx.fillText(txt, x, y0 + (buy ? 13 : -6));
  ctx.textAlign = 'left';
}
