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
function macdOf(bars, double) {
  const c = bars.map((b) => b.c);
  const e12 = ema(12, c), e26 = ema(26, c);
  const dif = e12.map((v, i) => v - e26[i]);
  const dea = ema(9, dif);
  const hist = dif.map((v, i) => (double ? (v - dea[i]) * 2 : v - dea[i]));
  return { params: [12, 26, 9], hist_def: 'dif-dea', t: bars.map((b) => b.t), dif, dea, hist };
}

module.exports = { macdOf };
