// 配色 / 画法常量 —— ★ 一律从 render/style.py 抄，不许在这里发明颜色。
//
// 为什么要单独一个文件而不是散在 app.js 里：`tools/web_theme_sync.py` 要拿它跟
// render/style.py 的 CHART 对账（键名一一对应，色值逐个比）。散着写就对不了账，
// 而对不了账的「两边一致」只是一句口头承诺 —— 2026-10-03 改配色那次已经证明
// 这类「两处各写一份」最后一定分家（style.py 里那条注释记的就是同一格两条判据的账）。
//
// 抄的出处都写在右边；值改了、出处没改，就是这份表在说谎。

export const CHART = {
  pen: '#7a89a6',        // style.py CHART.pen      笔（退成灰蓝）
  seg: '#c48901',        // style.py CHART.seg      线段（金）
  pc_w: 2,               // style.py CHART.pc_w     类中枢框线宽
  sc_w: 4,               // style.py CHART.sc_w     线段中枢框线宽
  pc_fill: 20,           // style.py CHART.pc_fill  类中枢填充 0-255（8%）
  sc_fill: 26,           // style.py CHART.sc_fill  线段中枢填充 0-255（10%）
  up_pen: '#998dc5',     // style.py CHART.up_pen   高一级：类中枢升上去的（淡紫）
  up_seg: '#d946ef',     // style.py CHART.up_seg   高一级：线段中枢升上去的（品红）
  up_fill: 20,           // style.py CHART.up_fill  高一级填充 0-255
  tag_fill: 255,         // style.py CHART.tag_fill 价签底色不透明度（实底）
  tag_ink: '#000000',    // style.py CHART.tag_ink  价签字色（黑）
  buy: '#00aa68',        // style.py CHART.buy      买点绿
  sell: '#ff5656',       // style.py CHART.sell     卖点红
  sig_pending: true,     // style.py CHART.sig_pending 待确认也画（更淡、文字带 ?）
};

// 页面底色与文字：style.py 的深色那一套（CHANLUN_THEME=dark）
export const PAGE = {
  bg: '#101218',         // style.py BG
  card: '#191c24',       // style.py CARD
  panel: '#13161d',      // style.py PANEL
  line: '#343946',       // style.py LINE
  tx: '#eaeef6',         // style.py TX
  mu: '#8e96a8',         // style.py MU
  dim: '#646c80',        // style.py DIM
};

// K 线与「未收盘」标注：full_common / chart_full_smooth 的直接取值
export const CANDLE = {
  up: '#26a69a',         // style.py UP（阳线）
  dn: '#ef5350',         // style.py DN（阴线）
  open: '#ffbe3c',       // style.py AM = (255,190,60) 琥珀：最后一根未收盘的虚线框 + 「未收盘」
};

// 线宽跟着 TradingView（tradingview/chanlun.pine 的输入默认值），不是按 Python 成图等比缩 ——
// Python 那张是 17592 px 宽的位图（笔 2 px / 段 5 px），除到屏幕上只剩零点几像素，等于没线。
// 这一条两边本来就同源：pine 的 penW=1 / segW=2 是给小栋在真机上看的选择。
export const WIDTH = {
  pen: 1,                // chanlun.pine input.int(1, "线宽") —— 笔
  seg: 2,                // chanlun.pine input.int(2, "线宽") —— 线段
  pc: 1,                 // chanlun.pine drawCenter(…, penCol, 1, …) —— 类中枢框
  sc: 2,                 // chanlun.pine drawCenter(…, segCol, 2, …) —— 线段中枢框
};

// 虚线：lightweight-charts 只给几种预设，给不了 Python 那边的 dash_len/gap（16/10、26/16…）。
// ⇒ 「画法一致」在虚线上守的是**实/虚二分与谁虚**（未完成的笔、未完成的线段、中枢框的延续那截、
//   未收盘的最后一根），不去追 dash 的长度 —— 追不到，也不该为它换掉整个画布库。
export const DASH = {
  lineStyle: 'dashed',   // lightweight-charts LineStyle.Dashed
  longLineStyle: 'large',// 线段用更长的那一档，跟笔分开（对应 Python 笔 12/8、段 26/16 的长短关系）
  box: [6, 4],           // 画布上的中枢框虚线（setLineDash）
  liveBox: [5, 3],       // 未收盘那根的虚线框（Python dashed_rect 6/4）
};

// 副图（成交量 ＋ MACD，卡 card-68704ee6-a5a）。
// ★ 这里的每一支都是**从上面那三块借过来的**，一个十六进制字面量都没新造 ——
//   造了就没人能跟 render/style.py 对账（ruler ① 的名单管的是 CHART 那一组逐键比对，
//   这一组不在它名单里，但同一条账照旧：色只有一处出处）。
//   柱子用 K 线那对涨跌色（同一个红绿），两条线按原文的叫法「黄白线」：
//   core/signals.py 的 MEASURES 里那一项就叫「黄白线不创新高低」——
//   白线 ＝ DIF（用正文的近白），黄线 ＝ DEA（用 K 线那支琥珀，也就是未收盘那根用的色）。
export const SUB = {
  dif: PAGE.tx,          // 白线（DIF）
  dea: CANDLE.open,      // 黄线（DEA）＝ style.py AM，也就是未收盘那根用的琥珀
  up: CANDLE.up,         // 柱子（正）
  dn: CANDLE.dn,         // 柱子（负）
};

// 买卖点的几何：full_common.draw_signals 原样搬（sz / 上下偏移 / 待确认的淡化系数）
export const SIG = {
  penSize: 9,            // 类中枢层（空心，标「·笔」）
  segSize: 15,           // 线段中枢层（实心，大号）
  tip: 6,                // 三角尖端离点位 6 px
  pendingAlpha: 140,     // 待确认 255 → 140
  confirmedAlpha: 255,
  weakText: '(弱)',
  pendingMark: '?',
};
