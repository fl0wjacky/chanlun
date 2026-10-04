// 工装用的**假副图**（card-68704ee6-a5a）：从一份 bars 造出 /api/macd 那个形状的响应。
//
// 为什么不是随手编三个数组：副图的验收里有一条是「**跟前端算的无关**」——
// 页面画上去的柱子必须跟响应里的 hist 逐根相同，**不许自己再减一遍 DIF−DEA**。
// 要证这件事，假后台就得**故意撒谎**：`double=true` 时 hist 回一份 `(dif − dea) × 2`，
// 口径字段照样写 'dif-dea'（真实世界里＝后台改了柱子的定义却没改字段，或者谁在别处又减了一遍）。
// 页面要是自己算，画出来就会是 dif−dea ⇒ 工装当场红；页面照抄响应 ⇒ 绿。
// ★ 那个 ×2 **不许去掉**：去掉之后 dif−dea 恰好等于 hist，这一格就恒绿（空转），
//   量不出任何东西 —— 跟把判据换成「画了没有」是一回事。
//
//
// 第三个开关 `shift=true`（2026-10-04，Atlas 核 card-68704ee6-a5a 时点的那格）：
// 回一份 **t[] 错开一根** 的响应 —— 演的是线上那件事：页面先拿到 K 线，过一会儿（后台 60s 重拉）
// 才去要副图，那一下窗口已经滑了一根 ⇒ 后台手里是 [第 2 根 … 第 N 根] ＋ 一根刚开的，
// `t[]` 整体比页面那份晚一根、根数一样。
// ★ 这一份**不是撒谎的后台**：每个数都老老实实挂在自己那个时间戳上（值是按它自己那份窗口算的）。
//   要证的是**页面那一侧**：它必须按**时间**把数放回它自己那一根（`sub.at.get(b.t)`）；
//   按数组下标放（`bars.indexOf(b)`）整列错一根 —— 副图 vs 主图差一根，谁也看不出来。
//   ★ 那份位移**必须真的存在**，不然这一格是空转：页面第一根在响应里没有（该不画）、
//     响应最后一根在页面上没有（多出来的）—— 两个「错开」的见证，工装都印出来。
//
// dif/dea 用最常见的 EMA12/EMA26/DEA9 算（不是「真 MACD」也没关系：工装只量**谁说了算**，
// 不量数值对不对；数值那半边归 web/check_parity.py 和后台自己的自测）。
function ema(n, src) {
  const k = 2 / (n + 1);
  const out = [];
  let prev = null;
  for (const v of src) { prev = prev == null ? v : v * k + prev * (1 - k); out.push(prev); }
  return out;
}

// → { params, hist_def, t[], dif[], dea[], hist[] }
//   根数：shift=false 时＝bars.length；shift=true 时**也是** bars.length（少了第一根、多了新开的那根）
function macdOf(bars, double, shift) {
  let src = bars;
  if (shift && bars.length > 1) {
    const step = bars.at(-1).t - bars.at(-2).t;                  // 时间戳严格等距
    const born = { t: bars.at(-1).t + step, c: bars.at(-1).c };  // 刚开的那根：拿上一根的收当占位（工装不量数值）
    src = bars.slice(1).concat([born]);
  }
  const c = src.map((b) => b.c);
  const e12 = ema(12, c), e26 = ema(26, c);
  const dif = e12.map((v, i) => v - e26[i]);
  const dea = ema(9, dif);
  const hist = dif.map((v, i) => (double ? (v - dea[i]) * 2 : v - dea[i]));
  return { params: [12, 26, 9], hist_def: 'dif-dea', t: src.map((b) => b.t), dif, dea, hist };
}

module.exports = { macdOf };
