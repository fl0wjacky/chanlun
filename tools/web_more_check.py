#!/usr/bin/env python3
"""尺 ⑥ —— 往左拖自动加载更早 K 线（card-d38154a0-e2d）。判三样：

  ① **画面不跳**：换数据之后，视口**左沿那一刻的时间**必须跟换之前一模一样。
     这是这一支的**全部职责**（2026-10-04 小栋定：「换数据后按时间把画面放回原位，不许跳」）。
  ② **什么时候要 / 要哪一档 / 什么时候停**：离左沿不到 20 根才要；档是 1、2、4、8……翻倍；
     `earliest`、封顶、要了没多 三种「到头」各自停法。**还有两处「数从哪儿来」**：
     地址栏 `?load=N` 进来先**夹进白名单那五个值**（>16 当 16、非数字当 1，Nova 2026-10-04 定），
     以及 `adopt()` ——手上到底是第几档、是不是到头了，**一律以后台回显为准**，不信自己发出去的数
     （首屏和往左加载共用这一个口）。
  ③ **那两句话**：加载中／已到最早／已到本周期可加载的最早——★ 后两句**不许塌成一句**（见下）。

为什么要它：这三件事在浏览器里量不出来（要拖、要等网络、还要一个真后台），可真出错的地方
全在这三个纯函数里。所以把它们留在 `web/app.js` 的 `// >>> EARLIER_PAGING` 标记块里**抠出来单跑**
——量的是**真身**，不是尺子自己拼的替身（这条账见 `web/README.md` 与 verification-taxonomy「判据量了替身」）。

★ ①量的是**真样本**：把仓里的 `zec_1h.json` / `btc_4h.json` 从头切掉一段当作「手上那份」，
  整份当作「补过之后那份」——两边的 K 线都是真的，时间戳也是真的（不是拿 `i*3600` 编的）。
  「右边又新收盘了几根」那几根的时间戳是按样本自己的步长往后推的（价格是抄最后一根的）——
  本尺只看时间，那三根的价格不参与任何判据，这里说清楚，免得看着像造数据。
  ★ 前提是**K 线等距**（位置↔时间是线性的）：每个数据集先验一遍，不等距就当场抛 ——
    前提不成立还照样绿，那才是真的假绿。

★ ③为什么要分开两句话：`earliest=true` 是**币安真没有更早的数据了**；而 `span==span_max`
  是**我们自己封的顶**，那时候币安明明还有更早的 —— 印「已到最早」就是一句假话
  （跟图脚「数据源」那次同一类账）。一句话糊过去省事，但屏幕就开始撒谎了。

跑法：
    python3 tools/web_more_check.py            # 三条判据全跑
    python3 tools/web_more_check.py --selftest # 探针：每一格都必须在**对的地方**变红
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = os.path.join(R, "web/app.js")
BEGIN, END = "// >>> EARLIER_PAGING", "// <<< EARLIER_PAGING"
DATA = {"zec_1h": os.path.join(R, "web/fixtures/zec_1h.json"),
        "btc_4h": os.path.join(R, "web/fixtures/btc_4h.json")}
RED, GREEN, DIM, OFF = "\033[31m", "\033[32m", "\033[2m", "\033[0m"

# 场景：(k, from, to, 右边新收盘几根, 名字)。k<1 当**比例**（乘上该数据集长度，至少 1 根）；k>=1 当**根数**。
#   from/to 是**逻辑下标**（跟 lightweight-charts 的 setVisibleLogicalRange 同一套：整数＝那一根，
#   小数＝两根之间；负数＝拖到数据头左边去了）。
CASES = [
    (0.33, 0, 160, 0, "贴到最左沿"),
    (0.33, 19.4, 179.4, 0, "左沿离数据头 19.4 根（触发线里侧）"),
    (0.33, -3, 157, 0, "拖过数据头 3 根"),
    (1, 0, 160, 0, "只补进来一根"),
    (0.5, 40, 200, 0, "补一大段、而左沿离老数据头还有 40 根"),
    (0.33, 12.5, 172.5, 3, "同一个响应里右边还新收盘了 3 根"),
    (0.33, -8.25, 151.75, 5, "两头都动、左沿还拖过了头"),
]

# ---- ② 的期望值表（全写死；改口径就改这里，别改尺子去迁就代码）----
WANT_SPAN = [((1, 8), 2), ((2, 8), 4), ((4, 8), 8), ((8, 8), None),
             ((1, None), 2),          # 后台没给 span_max（旧后台 / 字段缺）＝不封顶，照翻
             ((1, 1), None),          # 离线样本：就这一档
             ((4, 6), None)]          # 封顶不是 2 的幂：下一档会越过去 ⇒ 宁可停，也不发白名单外的档
WANT_STOP = [({"span": 1, "spanMax": 8, "earliest": False}, None),
             ({"span": 8, "spanMax": 8, "earliest": False}, "cap"),
             ({"span": 1, "spanMax": 8, "earliest": True}, "earliest"),
             ({"span": 1, "spanMax": 1, "earliest": True}, "earliest"),   # 两个都成立 ⇒ 以「真没了」为准
             ({"span": 2, "spanMax": 8, "earliest": False, "nogain": True}, "nogain")]
WANT_ACT = [(0, {}, "load"), (19.9, {}, "load"), (20, {}, None), (99, {}, None), (-5, {}, "load"),
            (0, {"earliest": True}, "stop"), (0, {"span": 8, "spanMax": 8}, "stop"),
            (0, {"nogain": True}, "stop"), (25, {"earliest": True}, None)]   # 离左沿远：到头也不关我事
WANT_TEXT = [({"loading": True}, "加载更早数据…"),
             ({"stop": "earliest"}, "已到最早"),
             ({"stop": "cap"}, "已到本周期可加载的最早"),
             ({"stop": "nogain"}, "取不到更早数据"),
             ({"failed": True}, "更早的数据没取到"),
             ({}, "")]
WANT_LADDER = [("1", 1), ("2", 2), ("3", 2), ("4", 4), ("7", 4), ("8", 8), ("12", 8), ("16", 16),
               # ★ 契约只认 1、2、4、8、16（Nova 2026-10-04）：地址栏写超了必须**夹到 16**，
               #   照发 32/64 后台按契约回 400 ⇒ 首屏整张挂掉（Atlas 两头各打一次挑出来的）
               ("32", 16), ("64", 16), ("99", 16),
               ("0", 1), ("-1", 1), ("abc", 1), ("", 1), (None, 1), ("2.9", 2)]
# ---- ② 的「回显说了算」表：adopt(cur, d, prevLen) → 手上那份的状态 ----
#   cur＝现在手上的（span/spanMax/earliest），d＝后台回的那份（span/span_max/earliest/bars），
#   prevLen＝这一趟之前的根数（首屏传 null ＝ 没有「上一份」可比）。三个字段同一条规矩：回了听回显，没回维持现状。
WANT_ADOPT = [
    ("后台钳了档（15m 求 16 只给 4）", {"span": 16, "spanMax": None, "earliest": False},
     {"span": 4, "span_max": 4, "earliest": False, "bars": [{}] * 900}, None,
     {"span": 4, "spanMax": 4, "earliest": False, "nogain": False}),
    ("首屏后台就说没了（AAPL 那种：一档就到底）", {"span": 1, "spanMax": None, "earliest": False},
     {"span": 1, "span_max": 1, "earliest": True, "bars": [{}] * 900}, None,
     {"span": 1, "spanMax": 1, "earliest": True, "nogain": False}),
    ("没有回显（离线样本 / 老后台）⇒ 现状原样", {"span": 2, "spanMax": 8, "earliest": False},
     {"bars": [{}] * 900}, None,
     {"span": 2, "spanMax": 8, "earliest": False, "nogain": False}),
    ("补上来的没有更多（有基准 ⇒ 白要了一趟）", {"span": 4, "spanMax": 16, "earliest": False},
     {"span": 8, "span_max": 16, "earliest": False, "bars": [{}] * 600}, 600,
     {"span": 8, "spanMax": 16, "earliest": False, "nogain": True}),
    ("补上来的更多了 ⇒ 不是白要", {"span": 4, "spanMax": 16, "earliest": False},
     {"span": 8, "span_max": 16, "earliest": False, "bars": [{}] * 1200}, 600,
     {"span": 8, "spanMax": 16, "earliest": False, "nogain": False}),
    ("真到头的那一趟「没多」不算故障（earliest 优先）", {"span": 4, "spanMax": 16, "earliest": False},
     {"span": 8, "span_max": 16, "earliest": True, "bars": [{}] * 600}, 600,
     {"span": 8, "spanMax": 16, "earliest": True, "nogain": False}),
    ("首屏没有上一份可比 ⇒ 不判「白要」", {"span": 1, "spanMax": None, "earliest": False},
     {"span": 2, "span_max": 16, "earliest": False, "bars": [{}] * 10}, None,
     {"span": 2, "spanMax": 16, "earliest": False, "nogain": False}),
]
# ---- ⑤ 体检（badIndex / vetted）：结构里凡是用下标指位置的地方都得落在 bars 里 ----
VET = [("结构都在 bars 里", {"bars": [{}] * 100, "pens": [{"i0": 0, "i1": 5}],
                             "segs": [{"i0": 5, "i1": 99}]}, True),
       ("笔的下标越界（切了 bars 没重算结构）", {"bars": [{}] * 100, "pens": [{"i0": 5, "i1": 100}]}, False),
       ("线段的下标越界", {"bars": [{}] * 100, "segs": [{"i0": 0, "i1": 500}]}, False),
       ("负下标（-1 也是越界，不是从末尾数）", {"bars": [{}] * 100, "pens": [{"i0": -1, "i1": 5}]}, False),
       ("没有结构层（最小样本）", {"bars": [{}] * 100}, True)]


# ---- ④ 换档那句话（NOTICE）什么时候出：拿**真样本**切一个可视窗口，只动结构，看 structKey 认不认 ----
#   值＝「两次的 key 应该**相同**吗」。这一组量的是一条口径：**只认跟可视窗口有时间重叠的结构，
#   而且按时间戳比、不按下标比**；结构 ＝ **屏幕上看得见的那五层**（笔／线段／类中枢／线段中枢／买卖点）。
#   坐标是样本里第 240～420 根那一屏：**写死的**，挑的规矩也只有一条 —— 五层在这一屏里各至少有一个成员
#   （笔 15 / 线段 2 / 类中枢 3 / 线段中枢 1 / 买卖点 1）。不这么挑，「只有中枢变」那几格会落在空窗口上，
#   绿得毫无意义（跟工装 ⑬ 第一版同一个坑）。各层在窗口里的个数由 inWin 报出来，是 0 就当场红。
WANT_NOTICE = [
    ("窗口里动一处笔（改窗口里第一笔的 p0）", False),
    ("只有窗口外动一处笔（改窗口外第一笔的 p0）", True),
    ("往左补 500 根：下标全移、时间价格不动（＝真的换档）", True),
    ("贴着窗口左沿收尾的那一笔（边界含等号）", False),
    ("窗口落在数据右边之外（一根结构都没有）", True),
    # ★ 这四格是 2026-10-04 Nova 拍 (a) 之后补的：原来只记笔和线段，中枢/买卖点变了不出声。
    #   「只有线段中枢变」那格照着真实形状写的：BTC 4h 1↔2 就是只有线段中枢的 ZD 变了（笔和段没动）。
    ("只有窗口里的类中枢变了（框里的上下沿）", False),
    ("只有窗口里的线段中枢变了（BTC 4h 那处的形状）", False),
    ("窗口里的买卖点换了价（三角还在原位）", False),
    ("只有窗口外的中枢变了", True),
    ("只有窗口外的买卖点变了", True),
]
WANT_NOTICE_TEXT = "已接上更早的K线，左侧的笔、线段、中枢和买卖点按新的起点重算"
WANT_NOTICE_MS = 3000
NOTICE_KEY = {"窗口里动一处笔（改窗口里第一笔的 p0）": "same_in",
              "只有窗口外动一处笔（改窗口外第一笔的 p0）": "same_out",
              "往左补 500 根：下标全移、时间价格不动（＝真的换档）": "same_shift",
              "贴着窗口左沿收尾的那一笔（边界含等号）": "same_edge",
              "窗口落在数据右边之外（一根结构都没有）": "same_far",
              "只有窗口里的类中枢变了（框里的上下沿）": "same_cen",
              "只有窗口里的线段中枢变了（BTC 4h 那处的形状）": "same_segc",
              "窗口里的买卖点换了价（三角还在原位）": "same_sig",
              "只有窗口外的中枢变了": "same_cen_out",
              "只有窗口外的买卖点变了": "same_sig_out"}
# 「窗口里五层各至少几个成员」才不算空转 —— 少一层，跟那一层有关的用例就说明不了任何事
NOTICE_MIN = {"pens": 1, "segs": 1, "centers": 1, "segc": 1, "sigs": 1}


def block(path=JS, begin=BEGIN, end=END):
    """抠出标记之间那一段。抠不到就抛 —— 被测量没了，尺子绝不假装绿。"""
    src = open(path, encoding="utf-8").read()
    i, j = src.find(begin), src.find(end)
    if i < 0 or j < 0:
        raise SystemExit(f"✗ {path} 里找不到 {begin} … {end} 标记（被抠的那块没了）")
    return src[src.index("\n", i) + 1:j]


DRIVER = r"""
const fs = require('fs');
const P = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = { uniform: {}, anchor: [], spans: [], stops: [], acts: [], texts: [], lads: [], adopts: [] };

// 时间轴：位置 x 处的时间 = 头一根的时间 + x*步长。★ 前提是等距（见文件头）。
function axis(bars) {
  const d = [];
  for (let i = 1; i < bars.length; i++) d.push(bars[i].t - bars[i - 1].t);
  return { t0: bars[0].t, step: d[0], uniform: d.every((x) => x === d[0]) };
}
// 「右边又新收盘了 n 根」：时间戳按样本自己的步长往后推（价格抄最后一根 —— 本尺只看时间）
function extras(bars, n) {
  const step = bars[1].t - bars[0].t, last = bars[bars.length - 1], out = [];
  for (let i = 1; i <= n; i++) out.push({ t: last.t + i * step, o: last.c, h: last.c, l: last.c, c: last.c });
  return out;
}

for (const [name, path] of Object.entries(P.data)) {
  const bars = JSON.parse(fs.readFileSync(path, 'utf8')).bars;
  const ax = axis(bars);
  out.uniform[name] = { n: bars.length, step: ax.step, uniform: ax.uniform };
  if (!ax.uniform) throw new Error('样本不是等距的，位置↔时间那套换算不成立：' + name);
  for (const c of P.cases) {
    const k = c.k < 1 ? Math.max(1, Math.floor(bars.length * c.k)) : c.k;
    const oldBars = bars.slice(k);                       // 手上那份（少了一段更早的）
    const newBars = c.extras ? bars.concat(extras(bars, c.extras)) : bars;   // 补过之后后台给的那份
    const a = anchorOf(oldBars, { from: c.from, to: c.to });
    const r = restoreRange(newBars, a);
    const j = Math.max(0, Math.ceil(c.from));            // 左沿右边那一根（离散的对照）
    out.anchor.push({
      name: name + '｜' + c.label,
      t_before: oldBars[0].t + c.from * ax.step,         // 换之前：左沿那一刻的时间
      t_after: newBars[0].t + r.from * ax.step,          // 换之后：同一个公式量一次
      w_before: c.to - c.from, w_after: r.to - r.from,
      bar_before: oldBars[j].t, bar_after: newBars[j + k].t,
      from: c.from, from_after: r.from, k: k,
    });
  }
}
out.spans = P.spans.map(([s, m]) => nextSpan(s, m));
out.stops = P.stops.map((s) => stopReason(s));
out.acts = P.acts.map(([from, s]) => onLeft(Object.assign({ from: from }, s)));
out.texts = P.texts.map((s) => moreText(s));
out.lads = P.lads.map((v) => ladderSpan(v));
out.adopts = P.adopts.map(([cur, d, prevLen]) => adopt(cur, d, prevLen));
out.vet = P.vet.map((d) => {
  let bad = null, throws = false;
  try { bad = badIndex(d); } catch (e) { bad = 'THROW'; }
  try { vetted(d); } catch (e) { throws = true; }
  return { bad: bad === null ? null : String(bad), throws: throws };
});
// ④ 换档那句话：拿真样本切一屏，只动结构，看 structKey 认不认（判据本身在围栏里，量的是真身）
//   ★ 每一格**只动一处、只动一层**：动得多看不出是哪一层在起作用（那正是「红得对 ≠ 红对了地方」）。
{
  const fx = JSON.parse(fs.readFileSync(P.data.zec_1h, 'utf8'));
  const bars = fx.bars, pens = fx.pens, segs = fx.segs;
  const centers = fx.centers || [], segc = fx.seg_centers || [];
  const sigs = fx.signals || { seg: [], pen: [] };
  const done = segs.filter((s) => !s.live);           // 线段中枢的 host（跟 layers.js doneSegs 同一条）
  const step = bars[1].t - bars[0].t;
  const A = 240, B = 420;                             // 写死的一屏：五层都有成员（见 Python 那边注释）
  const W = { t0: bars[A].t, t1: bars[B].t };
  const d0 = { bars: bars, pens: pens, segs: segs, centers: centers, seg_centers: segc, signals: sigs };
  const ov = (o) => bars[o.i0].t <= W.t1 && bars[o.i1].t >= W.t0;
  const bOv = (z, host) => { const a = host[z.PI0], b = host[z.PI1];
                             return !!a && !!b && bars[a.i0].t <= W.t1 && bars[b.i1].t >= W.t0; };
  const sOv = (s) => bars[s.bar].t >= W.t0 && bars[s.bar].t <= W.t1;
  const take = (o) => Object.assign({}, d0, o);
  const S = (o, w) => structKey(o, (w || W).t0, (w || W).t1);
  const base = S(d0);
  const iIn = pens.findIndex(ov), iOut = pens.findIndex((o) => !ov(o));
  const tweak = (a, i) => a.map((o, k) => (k === i ? Object.assign({}, o, { p0: o.p0 * 1.002 }) : o));
  const pre = []; for (let i = 500; i >= 1; i--) pre.push({ t: bars[0].t - i * step });
  const mk = (o) => Object.assign({}, o, { i0: o.i0 + 500, i1: o.i1 + 500 });
  //   买卖点的 bar 也是**下标**，补 500 根就得跟着 +500（少了这一步，这一格量的就成了
  //   「下标没跟着挪」——那是另一件事，真换档不会那样）。中枢不用挪：它存的是 host 里的位置（PI0/PI1）。
  const mkb = (s) => Object.assign({}, s, { bar: s.bar + 500 });
  // 贴着窗口左沿**收尾**的那一笔：i0 在窗口外、i1 正好落在窗口左沿上 —— 边界含等号它才在。
  //   ★ 量法是**只挪窗口左沿**（W3 = 压在那根上 ／ W4 = 往右 1ms 就不压了），不删结构：
  //     删一笔会让中枢的 PI0/PI1 整体错位（host 是笔数组），那样量到的就不是「边界在不在」了。
  const edge = pens.filter((o) => bars[o.i1].t >= W.t0 && bars[o.i0].t < W.t0)[0];
  const W3 = { t0: bars[edge.i1].t, t1: W.t1 };       // 窗口左沿正好＝那一笔收尾的那根
  const W4 = { t0: bars[edge.i1].t + 1, t1: W.t1 };   // 往右挪 1ms ⇒ 那一笔就不在窗口里了
  const far0 = bars[bars.length - 1].t + step, far1 = far0 + 9 * step;
  // 五层各挑一个「窗口里」和一个「窗口外」的成员：下面每格只动其中一个
  const cIn = centers.findIndex((z) => bOv(z, pens)), cOut = centers.findIndex((z) => !bOv(z, pens));
  const gIn = segc.findIndex((z) => bOv(z, done)),  gOut = segc.findIndex((z) => !bOv(z, done));
  const sIn = sigs.pen.findIndex(sOv),              sOut = sigs.pen.findIndex((s) => !sOv(s));
  const rep = (a, i, o) => a.map((x, k) => (k === i ? o : x));
  const zd = (z) => Object.assign({}, z, { ZD: z.ZD * 1.01 });
  const px = (s) => Object.assign({}, s, { price: s.price * 1.01 });
  out.notice = {
    inWin: { pens: pens.filter(ov).length, segs: segs.filter(ov).length,
             centers: centers.filter((z) => bOv(z, pens)).length,
             segc: segc.filter((z) => bOv(z, done)).length,
             sigs: sigs.pen.filter(sOv).length + sigs.seg.filter(sOv).length },
    same_in: S(take({ pens: tweak(pens, iIn) })) === base,
    same_out: S(take({ pens: tweak(pens, iOut) })) === base,
    same_shift: S({ bars: pre.concat(bars), pens: pens.map(mk), segs: segs.map(mk),
                    centers: centers, seg_centers: segc,
                    signals: { seg: sigs.seg.map(mkb), pen: sigs.pen.map(mkb) } }) === base,
    same_edge: S(d0, W3) === S(d0, W4),
    same_far: S(d0, { t0: far0, t1: far1 })
              === S({ bars: bars, pens: [], segs: [], centers: [], seg_centers: [],
                      signals: { seg: [], pen: [] } }, { t0: far0, t1: far1 }),
    same_cen: S(take({ centers: rep(centers, cIn, zd(centers[cIn])) })) === base,
    same_cen_out: S(take({ centers: rep(centers, cOut, zd(centers[cOut])) })) === base,
    same_segc: S(take({ seg_centers: rep(segc, gIn, zd(segc[gIn])) })) === base,
    same_sig: S(take({ signals: { seg: sigs.seg, pen: rep(sigs.pen, sIn, px(sigs.pen[sIn])) } })) === base,
    same_sig_out: S(take({ signals: { seg: sigs.seg, pen: rep(sigs.pen, sOut, px(sigs.pen[sOut])) } })) === base,
  };
  out.notice_text = NOTICE_TEXT;
  out.notice_ms = NOTICE_MS;
}
// 完全分类：白名单外的档一个都不许发出去
out.ladder_all_pow2 = [];
for (let v = 1; v <= 200; v++) out.ladder_all_pow2.push(ladderSpan(v));
out.next_all_pow2 = [];
for (const m of [null, 1, 2, 4, 8, 16]) for (const s of [1, 2, 4, 8]) out.next_all_pow2.push(nextSpan(s, m));
process.stdout.write(JSON.stringify(out));
"""


def node_eval(js, payload):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js)
        tmp = f.name
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as g:
        g.write(json.dumps(payload))
        arg = g.name
    try:
        p = subprocess.run(["node", tmp, arg], capture_output=True, text=True, timeout=120)
    finally:
        os.unlink(tmp)
        os.unlink(arg)
    if p.returncode != 0:
        raise SystemExit("✗ node 跑不起来：\n" + p.stderr.strip())
    return json.loads(p.stdout)


def payload():
    return {"data": DATA, "cases": [{"k": k, "from": f, "to": t, "extras": e, "label": n}
                                   for k, f, t, e, n in CASES],
            "spans": [[s, m] for (s, m), _ in WANT_SPAN],
            "stops": [s for s, _ in WANT_STOP],
            "acts": [[f, s] for f, s, _ in WANT_ACT],
            "texts": [s for s, _ in WANT_TEXT],
            "lads": [v for v, _ in WANT_LADDER],
            "adopts": [[c, d, p] for _, c, d, p, _ in WANT_ADOPT],
            "vet": [d for _, d, _ in VET]}


def failures(js=None, quiet=True):
    """→ ([(判据, 用例, 实际, 期望, 说明)], node 那份原始输出)；第一项空表＝全对。"""
    got = node_eval((js if js is not None else block()) + DRIVER, payload())
    bad = []
    for name, u in got["uniform"].items():
        if not u["uniform"]:
            raise SystemExit(f"✗ 样本 {name} 的 K 线不等距 —— 这把尺的换算前提没了，不能当绿")
    # ① 画面不跳
    for r in got["anchor"]:
        if abs(r["t_after"] - r["t_before"]) > 1e-6:
            bad.append(("①不跳", r["name"], "左沿进了 %+.0f ms（≈%+.2f 根）"
                        % (r["t_after"] - r["t_before"],
                           (r["t_after"] - r["t_before"]) / 3600000.0),
                        "左沿那一刻的时间不变", "换数据后按时间放回原位"))
        if abs(r["w_after"] - r["w_before"]) > 1e-9:
            bad.append(("①不跳", r["name"], "视口宽 %s" % r["w_after"], "%s" % r["w_before"], "宽度不该变"))
        if r["bar_after"] != r["bar_before"]:
            bad.append(("①不跳", r["name"], "左沿那根 %s" % r["bar_after"], "%s" % r["bar_before"],
                        "左沿那一根必须是同一根（时间对不上就是跳）"))
    # ② 要 / 哪一档 / 停
    for i, ((s, m), want) in enumerate(WANT_SPAN):
        g = got["spans"][i]
        if g != want:
            bad.append(("②规则", "nextSpan(span=%s, span_max=%s)" % (s, m), g, want, "下一档"))
    for i, (s, want) in enumerate(WANT_STOP):
        g = got["stops"][i]
        if g != want:
            bad.append(("②规则", "stopReason(%s)" % json.dumps(s, ensure_ascii=False), g, want, "为什么停"))
    for i, (f, s, want) in enumerate(WANT_ACT):
        g = got["acts"][i]
        if g != want:
            bad.append(("②规则", "onLeft(from=%s, %s)" % (f, json.dumps(s, ensure_ascii=False)), g, want,
                        "拖到左边该干什么（20 根那条线）"))
    notpow2 = [v for v in got["ladder_all_pow2"] if v & (v - 1)]
    if notpow2:
        bad.append(("②规则", "ladderSpan 1..200", notpow2[:5], "全是 2 的幂", "白名单外的档不许发出去"))
    if any(v is not None and (v & (v - 1)) for v in got["next_all_pow2"]):
        bad.append(("②规则", "nextSpan 全表", "有非 2 的幂", "全是 2 的幂 或 null", "同上"))
    # ③ 那两句话
    for i, (s, want) in enumerate(WANT_TEXT):
        g = got["texts"][i]
        if g != want:
            bad.append(("③话", "moreText(%s)" % json.dumps(s, ensure_ascii=False), g, want, "该说哪句"))
    cap_i = [i for i, (s, _) in enumerate(WANT_TEXT) if s.get("stop") == "cap"][0]
    ear_i = [i for i, (s, _) in enumerate(WANT_TEXT) if s.get("stop") == "earliest"][0]
    if got["texts"][cap_i] == got["texts"][ear_i]:
        bad.append(("③话", "封顶 vs 真到头", "两句话一样", "两句不同",
                    "封顶时币安还有更早的数据 ⇒ 印「已到最早」是假话"))
    for i, (v, want) in enumerate(WANT_LADDER):
        g = got["lads"][i]
        if g != want:
            bad.append(("②规则", "ladderSpan(%r)" % v, g, want, "地址栏进来的档"))
    # ② 回显说了算（首屏 / 往左加载共用的那一个口）
    for i, (name, _cur, _d, _p, want) in enumerate(WANT_ADOPT):
        g = got["adopts"][i]
        off = [k for k in ("span", "spanMax", "earliest", "nogain") if g.get(k) != want[k]]
        if off:
            bad.append(("②规则", "adopt：" + name,
                        "、".join("%s=%r" % (k, g.get(k)) for k in off),
                        "、".join("%s=%r" % (k, want[k]) for k in off),
                        "手上第几档/到头没有一律以后台回显为准"))
    # ④ 换档那句话：**只在可视窗口里的结构变了**的时候出
    #    ★ 先量这一屏有没有东西可比：**五层逐层报数**，缺哪层哪层的用例就是空转的绿。
    iw = got["notice"]["inWin"]
    for k, lo in NOTICE_MIN.items():
        if iw.get(k, 0) < lo:
            bad.append(("④那句话", "这一屏窗口里的「%s」有几个" % k, iw.get(k, 0), "≥%d" % lo,
                        "那一层一个都没有 ⇒ 跟它有关的用例是空转，绿不算绿"))
    for name, want_same in WANT_NOTICE:
        g = got["notice"][NOTICE_KEY[name]]
        if g != want_same:
            bad.append(("④那句话", name, "相同" if g else "不同", "相同" if want_same else "不同",
                        "只看可视窗口里的结构 ＋ 按时间戳比"))
    if got["notice_text"] != WANT_NOTICE_TEXT:
        bad.append(("④那句话", "提示的文案", got["notice_text"], WANT_NOTICE_TEXT, "契约原文，不许顺手改字"))
    if got["notice_ms"] != WANT_NOTICE_MS:
        bad.append(("④那句话", "提示停多久", got["notice_ms"], WANT_NOTICE_MS, "说好停 3 秒"))
    # ⑤ 体检：合格的那几行必须既不判坏也不抛；不合格的必须判坏 **且** vetted 抛（两件事一起错才叫没取到）
    for i, (name, _d, want) in enumerate(VET):
        g = got["vet"][i]
        ok_here = (g["bad"] is None) == want and g["throws"] == (not want)
        if not ok_here:
            bad.append(("⑤体检", name, "%s / %s" % (g["bad"], "抛了" if g["throws"] else "没抛"),
                        "合格" if want else "判坏并抛出", "对不上的数据不许画上去"))
    return bad, got


def report(quiet=False):
    bad, got = failures()
    if not quiet:
        print("往左拖自动加载更早 K 线（card-d38154a0-e2d / web/app.js 的 EARLIER_PAGING 段）\n")
        for name, u in got["uniform"].items():
            print("  样本 %-8s %5d 根 · 步长 %d ms · 等距 ✓" % (name, u["n"], u["step"]))
        print("\n  ① 画面不跳（左沿那一刻的时间，换数据前后必须一模一样）")
        for r in got["anchor"]:
            dt = r["t_after"] - r["t_before"]
            print("     %-46s from %-8s → %-9s  Δt %+.0f ms  %s"
                  % (r["name"], r["from"], round(r["from_after"], 3), dt,
                     "✓" if abs(dt) <= 1e-6 and r["bar_after"] == r["bar_before"] else "✗"))
        print("\n  ② 什么时候要 / 要哪一档 / 什么时候停")
        for i, ((s, m), want) in enumerate(WANT_SPAN):
            print("     nextSpan(%-2s, %-4s) ⇒ %-5s（要 %s）" % (s, m, got["spans"][i], want))
        for i, (f, s, want) in enumerate(WANT_ACT):
            print("     from=%-6s %-28s ⇒ %-5s（要 %s）"
                  % (f, json.dumps(s, ensure_ascii=False), got["acts"][i], want))
        for i, (v, want) in enumerate(WANT_LADDER):
            if i < 6 or v in ("32", "64", "abc"):
                print("     ?load=%-5r ⇒ %-4s（要 %s）" % (v, got["lads"][i], want))
        for i, (name, _c, _d, _p, want) in enumerate(WANT_ADOPT):
            g = got["adopts"][i]
            print("     %-34s ⇒ span=%-4s max=%-4s earliest=%-5s nogain=%-5s（要 %s/%s/%s/%s）"
                  % (name, g["span"], g["spanMax"], g["earliest"], g["nogain"],
                     want["span"], want["spanMax"], want["earliest"], want["nogain"]))
        print("\n  ⑤ 换数据前的体检（badIndex / vetted）")
        for i, (name, _d, want) in enumerate(VET):
            print("     %-38s ⇒ %-28s（要 %s）"
                  % (name, got["vet"][i]["bad"] or "合格", "合格" if want else "判坏"))
        print("\n  ④ 换档那句话（只在可视窗口里的结构变了才出）")
        for name, want_same in WANT_NOTICE:
            g = got["notice"][NOTICE_KEY[name]]
            print("     %-46s ⇒ 两次的 key %s（要 %s）"
                  % (name, "相同" if g else "不同", "相同" if want_same else "不同"))
        print("     窗口里 笔 %d · 线段 %d · 类中枢 %d · 线段中枢 %d · 买卖点 %d · 文案 %r · 停 %d ms"
              % (got["notice"]["inWin"]["pens"], got["notice"]["inWin"]["segs"],
                 got["notice"]["inWin"]["centers"], got["notice"]["inWin"]["segc"],
                 got["notice"]["inWin"]["sigs"], got["notice_text"], got["notice_ms"]))
        print("\n  ③ 那两句话")
        for i, (s, _) in enumerate(WANT_TEXT):
            print("     %-28s ⇒ %r" % (json.dumps(s, ensure_ascii=False), got["texts"][i]))
    if bad:
        print(f"{RED}✗{OFF} 有 {len(bad)} 处不对：")
        for j, case, g, w, why in bad:
            print(f"   {RED}✗{OFF} [{j}] {case}：实际 {g!r} ≠ 期望 {w!r} ← {why}")
        return 1
    if not quiet:
        print(f"\n{GREEN}✓{OFF} 左沿那一刻的时间换档前后不变（{len(got['anchor'])} 个场景 / 真样本）、"
              f"档位与停法逐格对得上、两个「到头」没塌成一句、"
              f"换档那句话只认可视窗口里的结构、五层都算数（{len(WANT_NOTICE)} 个场景 / 真样本）")
    return 0


def mutate(js, old, new):
    """探针里改源码**必须真落到抠出来那段上**：落不上就直接抛（否则探针红的原因是「没改着」）。"""
    if old not in js:
        raise SystemExit(f"✗ 探针改不动：抠出来的那段里没有 {old!r}")
    return js.replace(old, new)


# 探针：(名字, 改什么, 改前, 改后, 该在哪条判据上红, 哪个用例名该出现在红行里)
PROBES = [
    # ★ 这一格是最要紧的那一格：补进来 k 根、视口却**没跟着挪**（把 oldFrom 原样用回去）——
    #   真页面上就是「一加载完，画面嗖地跳到最老那头」。它必须**每个场景**都红。
    ("①不跳：换了数据但视口没跟着挪（忘了 +k）",
     "const from = i === null ? bars.length - anchor.oldLen + anchor.oldFrom : i + anchor.frac;",
     "const from = anchor.oldFrom;"),
    ("①不跳：锚点存下标（不存时间）", "t: bars[k].t,", "t: k,"),
    ("①不跳：丢掉小数（只对到整根）", "i + anchor.frac", "i"),
    ("①不跳：退回「按右端对」（不找时间）",
     "const from = i === null ? bars.length - anchor.oldLen + anchor.oldFrom : i + anchor.frac;",
     "const from = bars.length - anchor.oldLen + anchor.oldFrom;"),
    ("②规则：触发线从 20 挪到 0（只在贴死左端才要）", "s.from >= PAGE_FROM", "s.from >= 0"),
    ("②规则：档位不翻倍", "const s = span * 2;", "const s = span;"),
    ("②规则：无视封顶", "return spanMax != null && s > spanMax ? null : s;", "return s;"),
    ("②规则：无视 earliest（到最早还接着要）", "if (s.earliest) return 'earliest';", "if (false) return 'earliest';"),
    ("②规则：无视「要了没多」（会原地打转）", "if (s.nogain) return 'nogain';", "if (false) return 'nogain';"),
    ("②规则：地址栏的档不夹回白名单", "Math.floor(Math.log2(n))", "Math.round(Math.log2(n))"),
    # ★ 这一格是 Atlas 两头各打一次挑出来的：?load=64 照发 64 ⇒ 契约回 400 ⇒ 首屏整张挂掉
    ("②规则：地址栏的档不封在 16（?load=64 照发）",
     "Math.max(1, Math.min(SPAN_WL_MAX, Math.pow(2, Math.floor(Math.log2(n)))))",
     "Math.max(1, Math.pow(2, Math.floor(Math.log2(n))))"),
    # ★ 「回显说了算」：不信后台，只认自己发出去的那个数（首屏整张挂 / 停法印错都是这一个口出来的）
    ("②规则：不信回显，只认自己发出去的档",
     "span: Number.isFinite(d.span) ? d.span : cur.span,", "span: cur.span,"),
    ("②规则：回显说没了也当还有（earliest 不听回显）",
     "earliest: d.earliest == null ? cur.earliest : !!d.earliest,", "earliest: false,"),
    ("②规则：真到头那趟也判成「白要了一趟」",
     "s.nogain = prevLen != null && (d.bars || []).length <= prevLen && !s.earliest;",
     "s.nogain = prevLen != null && (d.bars || []).length <= prevLen;"),
    ("③话：封顶和真到头塌成一句", "if (s.stop === 'cap') return '已到本周期可加载的最早';",
     "if (s.stop === 'cap') return '已到最早';"),
    # ★ ④ 这一组是「那句话什么时候出」的**判据本身**：四条各打一处，缺哪条这条口径就漏哪一面。
    #   ①判据退化成「整个 payload 变没变」（不看窗口）②用下标比、不用时间戳比（补数据就当成变了）
    #   ③边界不含等号（贴着左沿收尾的那一笔漏掉）④文案/时长被顺手改掉。
    ("④那句话：判据不看可视窗口（整个 payload 变没变）",
     "const part = (a) => (a || []).filter(inWin).map(row).join('|');",
     "const part = (a) => (a || []).map(row).join('|');"),
    ("④那句话：按下标比，不按时间戳比（换档就当成变了）",
     "const row = (o) => `${ts(o.i0)}>${ts(o.i1)}@${o.p0},${o.p1}`;",
     "const row = (o) => `${o.i0}>${o.i1}@${o.p0},${o.p1}`;"),
    ("④那句话：窗口左沿的边界不含等号（贴着左沿收尾的那一笔漏掉）",
     "const ov = (a, b) => a != null && b != null && b >= t0 && a <= t1;",
     "const ov = (a, b) => a != null && b != null && b > t0 && a <= t1;"),
    ("④那句话：文案被顺手改了一个字",
     "const NOTICE_TEXT = '已接上更早的K线，左侧的笔、线段、中枢和买卖点按新的起点重算';",
     "const NOTICE_TEXT = '已接上更早的K线，左边的笔、线段、中枢和买卖点按新的起点重算';"),
    ("④那句话：3 秒被改成 0.3 秒", "const NOTICE_MS = 3000;", "const NOTICE_MS = 300;"),
    # ★★ 这四格是 2026-10-04 补的：**每一层都得真在判据里**，而且**都得按窗口筛**。
    #   只留「笔/线段」两层的话，屏幕上明明变了的框和三角不出声（Nova 拍 (a) 之前就是这个洞）。
    ("④那句话：不记类中枢（框里的上下沿变了也不出声）",
     "boxes(d.centers, d.pens || []),", "'',"),
    ("④那句话：不记线段中枢（BTC 4h 那种情形漏掉）",
     "boxes(d.seg_centers, done),", "'',"),
    ("④那句话：不记买卖点",
     "sigs((d.signals || {}).seg), sigs((d.signals || {}).pen)]",
     "'', '']"),
    ("④那句话：中枢不看窗口（窗口外动一下也当成变了）",
     ".filter((o) => o && ov(ts(o.i0), ts(o.i1)))", ".filter((o) => o)"),
    ("⑤体检：把越界当合格（照画不误）", "const n = (d.bars || []).length, over = (i) => !(i >= 0 && i < n);",
     "const n = (d.bars || []).length, over = (i) => false;"),
    ("⑤体检：负下标不算越界", "!(i >= 0 && i < n)", "!(i < n)"),
]


def selftest():
    """探针。★ 两件都要成立：**变了红** ＋ **红在对的地方**（判据名、用例名都对得上）——
    「红得对 ≠ 红对了地方」（Atlas 那次的教训）在这把尺里是一条断言，不是一句话。"""
    cases = []
    for name, a, z in PROBES:
        judge = ("①不跳" if name.startswith("①") else "③话" if name.startswith("③")
                 else "④那句话" if name.startswith("④") else "⑤体检" if name.startswith("⑤")
                 else "②规则")
        # ★ 探针「红」的原因也算判据：改得跑不起来（node 报错）或者**尺子自己在 Python 里炸了**，
        #   都不算红 —— 那正是「红得对 ≠ 红对了地方」要拦的事。红必须是**判据**判出来的。
        try:
            js = mutate(block(), a, z)
            bad, _ = failures(js)
        except SystemExit as e:
            if str(e).startswith("✗ 探针改不动"):
                raise
            cases.append((name, False, "node 跑不起来（不是判据判红的）：%s" % str(e)[:60], judge))
            continue
        except Exception as e:
            cases.append((name, False, "尺子自己在 Python 里炸了：%r" % (e,), judge))
            continue
        hit = [b for b in bad if b[0] == judge]
        cases.append((name, bool(bad) and bool(hit),
                      "%d 处红，其中 %d 处在 [%s]" % (len(bad), len(hit), judge),
                      judge))
    # 标记块被删 ⇒ 必须抛，不许静默少量一块
    try:
        src = open(JS, encoding="utf-8").read().replace(END, "// 没了")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(src)
            tmp = f.name
        try:
            block(tmp)
            cases.append(("标记块被删 ⇒ 报错", False, "没抛", "①不跳"))
        except SystemExit:
            cases.append(("标记块被删 ⇒ 报错", True, "抛了", "①不跳"))
        finally:
            os.unlink(tmp)
    except Exception as e:
        cases.append(("标记块被删 ⇒ 报错", False, str(e)[:40], "①不跳"))

    ok = True
    for name, hit, why, _ in cases:
        ok &= hit
        print("%s 探针「%s」：%s" % (GREEN + "✓" + OFF if hit else RED + "✗" + OFF, name,
                                    why if hit else "**没红 / 红错地方** —— " + why))
    print("%s 自检：%d/%d 格探针都能在对的判据上变红" % (GREEN + "✓" + OFF if ok else RED + "✗" + OFF,
                                                 sum(1 for c in cases if c[1]), len(cases)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(selftest())
    raise SystemExit(report())


if __name__ == "__main__":
    main()
