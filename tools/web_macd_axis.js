// 副图（MACD）那一格的**坐标轴**，跟画上去的数据对得上吗？（真后台；给 Nova 外测那两张截图的工装）
//
// 病症（Nova 2026-10-04 外测 82a47eb，线上 BTCUSDT）：
//   接口里 4h 的 DIF 是 -2497～3477、柱是 -612～833，可**副图轴上标到 -20000**；1h 标到 -2500。
//   Bram 先排了后端（逐根等于引擎），指名「要么轴拿了全量范围、没按可见窗口算，要么时间对齐错了」。
//
// 因：**不是**这两条。是副图那一格的右轴**跟着主图的对数轴**。
//   `web/app.js` 建图那句 `rightPriceScale: { mode: Logarithmic }` 铺的是**每一格**的 right 轴 ——
//   5.2.1 实测：`panes[0].priceScale('right')` 与 `panes[1].priceScale('right')` 是**两根不同对象**，
//   但 `mode` 都是 1（Logarithmic）。主图那根对数轴是故意的（对齐 chart_full_smooth.py 的 Y=log），
//   可 **MACD 的值跨 0、还有负数**，对数轴对这些点没有意义：实测（改前，4h BTCUSDT）
//       priceToCoordinate: -2000→156.3  -1000→153.4  **0→86.2**  1000→19.0  2000→16.1  3000→14.4
//   0→1000 走 67px，1000→2000 只走 3px —— 这不是任何一根按数据自适应的轴该有的样子，
//   刻度自然就成了 0.00 / -20000.00 这种跟数据量级无关的数，柱子也按错的比例尺画满整格。
//
// 判据（Atlas 定的那条 ＋ 它的另一半）：
//   ① **线性**：轴得是线性的（MACD 这一格的量法）。三点共线，残差 ≤ 1px。
//   ② **罩得住**：轴的上沿 ≥ 可见窗口里 hist/dif/dea 的 max，下沿 ≤ 它的 min。
//   ③ 零线在轴里（柱子是 base=0 画的，0 跑出轴就是错的）。
//   ④ **不虚胖**：轴跨 ≤ 2.5 × 窗口里数据的跨（防「拿了整份范围」）。
//   ⑤ **缩放跟着缩**：把可见窗口收到最近 200 根 ⇒ 轴跨要明显变小，且在新窗口上照样罩得住。
//   ⑥ 没误伤：主图那一格**仍然是对数**（mode=1）。
//   ⑧ **像素上的形状**（Nova 加的那条）：在**画出来的像素**上量三根柱子的高度，高度比要跟数据比一致
//      （±1.5px），而且符号对（正的在零线上边、负的在下边）。① 量的是比例尺、⑧ 量的是比例尺**画出来的结果**
//      —— 光有 ① 的话，「比例尺对了但柱子按别的比例画」这种还是能溜过去。
//   ★ ⑧ **只在缩放之后再量**（Atlas 2026-10-04 复核 d481554 时抓到的：首屏 1280px 宽、整份数据铺满
//     ⇒ barSpacing 0.5px，**一个像素列里挤着两根柱子**，`timeToCoordinate` 给的那一列量到的可能是邻居；
//     修后代码没变异的干净树上，1h 红了 3 格、15m 红 1 格 —— 是量具的错，不是页面的错）。
//     现在它自己挑一屏**柱距 ≥ 2px** 的窗口（挑「够大 × 拉得开」得分最高的那一段：比值拉不开这格没牙、
//     柱子太小量出来是噪声），量完把**原来的可见区间放回去**（后面 ⑤ 的 before/after 与那张截图都不受影响），
//     并且**跳过页头那块浮层（#subhead）盖住的柱尖**（它压在副图上沿，柱子最尖那几个像素是被它画掉的）。
//     判据一个字没动，动的只是「在哪一屏、量哪一根」。
//  ⑨ **页头不许盖数据**（Atlas 15m 截图上那条 · Nova 派的那件）：副图左上角那块头框（#subhead）是**浮层**，
//     它下沿以上不许有任何数据点。量法：把可见窗口里 hist/dif/dea **各自最极端**的那个点的 y 量出来
//     （priceToCoordinate），三个都要 ≥ 页头下沿；余量还要 ≤ 12px（让过头＝白挤数据，另一半的牙）。
//     ★ 为什么不是「有没有柱尖被盖住」：多数窗口里 DIF 比柱子大 ⇒ 柱子根本够不到顶，照那个量**首屏永远是 0**
//       —— 这正是它藏到现在的原因（首屏 2041 根里最高的柱子离页头还有 70px，可 DIF 的极值就在 y=13.4）。
//       按「这一条里有没有数据」量，跟缩放到哪一屏无关：轴的上沿就是这一屏最极端的那个点。
//     ★ 像素复核**有前提**（跟 ⑧ 同一条）：柱距 ≥ 2px 才量。首屏 0.5px/柱时一列挤两根，量到的是邻居
//       （实测 ZEC 15m 首屏：映射 y 62.4 vs 画布 84 ⇒ 差 21.6px，是量具的错）；那时这半边认「没量」，
//       明写在那一行里。判据的主半（映射出来的 y）不受影响 —— 变异跑证明了它有牙（见下）。
//     ★ 两半的牙各有一个变异（都跑过，都是 19/22、只红 ⑨ 那三格，干净地红）：
//       摘掉修法（`--mut=noreserve`）⇒ 余量 **-12.6px**；把留白让过头（`--mut=fat`，top 写死 0.35）⇒ **+32.8px**。
//   ★ ⑧ 的**诚实记录**（都是量具自己的账，不是页面的）：
//     1. 页头那条闸**第一版是死的**：对象里写 `bot:`、判据里念 `band.bottom` ⇒ 那个键不存在 ⇒
//        `108 <= undefined + 2` 恒 false ⇒「盖住」永远是 0。手工把带子撑大（x 拉到全宽、y 拉高 120px）
//        才当场逮到 —— 跟 readout 那次 ⑯ 的死条件同一个形状：**量不出来的闸，看着绿其实是没跑**。
//     2. 修好之后，这三次跑（4h/1h/15m）「盖住」仍然是 0（⑨ 修完之后更是恒 0：那一条数据根本不让进）。
//        修之前它一直是 0 是因为**柱子够不到最上面那 10%**（副图那格的轴是 DIF/DEA/hist 一起撑的，
//        DIF 通常比柱子大）—— 所以这条「跳过」是防着的，判决交给 ⑨（⑨ 量的正是那一条带子本身）。
//     3. 轴被钉死在全量范围上时（--mut=freeze），柱子会缩到 3～5px ⇒ 三根凑不齐 / 比例拉不开 ⇒
//        ⑧ 报**量不出来**（名字里就写着「不是画错了」），不是形状的判决：那种情况下形状其实还是对的，
//        该红的是 ⑤/④。这一支只在变异跑里出现，干净树上不会。
//     4. 第一屏量不出来时（凑不齐三根／拉不开）会自动换「柱子最大的那一屏」再试一次，两次都量不出来
//        才认「量不出来」；用的哪一屏、两次各量到几根、各多高，都印在那一行里。
//     5. ★★ **2026-10-06 那次红（卡 card-016a62a3-b36）：柱尖是被线盖住的，柱子本身没画矮。**
//        病症：`缩放后⑧` 在干净的 main（0c56820）上红 —— BTCUSDT 4h，值 316 那根量到 7.5px、偏差 1.7px。
//        当时的猜测是「柱距只有 2.78px，抗锯齿吃掉了柱尖那半像素」。**量下来不是**：
//          · 按轴映射反推，那根柱尖该在 119.4，量到 121 ⇒ 短 1.6px（不是半像素，是一整行还多）；
//          · 而且**放大到柱距 3.22px 反而更差**（该在 130.8，量到 133 ⇒ 短 2.2px）
//            ⇒ 「太挤」这个解释当场不成立（真要是挤，放大就该变好）；
//          · 那两行到底是谁画的？逐行看颜色：柱尖上一行是 rgb(186,220,223)、再上一行 rgb(85,183,176)
//            —— 都是**白线色 (234,238,246) 跟柱子色 (38,166,154) 的混合**（0.75/0.25 与 0.25/0.75，
//            对得上）；而白线（DIF）本身在这一列正好落在 120.5，离柱尖 1.1px。
//          · **判决实验**：把 dif/dea 两条线 `applyOptions({visible:false})` 藏起来，同一屏、同三根再量
//            ⇒ 柱尖差 0.2/0.1/0.2px（没藏时 0.1/2.2/0）。**柱子一分不差，是线把它盖住了。**
//        ⇒ 修的是**量法**（跟 Nova 定的同一路：画法不动、±1.5px 不放宽）：
//          柱尖被白线／黄线压住的那一根**跳过**（新增 `跳过.被线穿`），换下一根 —— 跟「被页头盖住的柱尖」同一类。
//        ⇒ **没有**按「把挑窗口要求从 ≥2px 提到 ≥4px」改：证据说那不是病因（放大更差），而且今天那三根
//          跨度 297 根，一屏塞进 297 根时柱距只有 3.22px —— ≥4px 与「同屏同三根」本身就凑不到一起。
//          真按 ≥4px 挑，挑到的是**另一屏另三根**，绿了也证明不了什么（Atlas 10-06 提醒的正是这条）。
//        ⇒ 三态落地（Nova＋Bram 10-06）：绿 / 红（量到了、形状错）/ **未量**（判据没被行使）；
//          退出码 有红退 1、只有未量退 2、全绿 0。
//   ⑦ **重建也管用**：点一次「MACD」那颗 chip（关 ⇒ 窗格收回去；开 ⇒ 重新建格、重新要数据），
//      回来之后 ①②③④ 必须照样绿 —— 修法长在 `buildSub()` 里，这条防的是「只在第一次打开生效」。
//      ★ 量之前先 `waitLayoutSettle()` 等页头贴住那一格的上沿（见那个函数的注释）——
//        ⑦ 原来会**偶发飘红**就是量在「页头还没被摆到位」那一拍上（页面那边也真有这一拍，
//        已在 `web/app.js` 的 `placeSubhead()` 里堵掉；这条是量之前的第二道）。
//   ⇒ 轴上刻度是从这根比例尺生成的，所以「轴的范围」就是「刻度的范围」：
//      ① 红＝刻度不是正经刻度，② 红＝刻度对不上数据的最大最小（Atlas 的原话）。
//
// 跑法（要真后台：
//   1) python3 web/server.py --port <端口> --no-prewarm      （只绑回环）
//   2) NODE_PATH=<playwright 的 node_modules> node tools/web_macd_axis.js [页面地址] [--mut=nofix|freeze]
//   不给 --mut ⇒ 只跑原样。--mut=nofix 摘掉那行修（＝复现外测那张图）；
//   --mut=freeze 换成「轴钉死在全量范围上」（＝Bram 猜的那条，用来证明 ⑤ 有牙）；
//   --mut=noreserve / --mut=fat 是 ⑨ 那两半的牙（摘掉让白 / 让过头）。
//
// ★ ⑦ **没有自己的变异**（不是忘了写）：试过「修法只在第一次建格时生效」，它照样绿 —— 关掉再打开时
//   LWC **复用** pane 1 那根 right 轴，mode 留在 Normal 上（拆了重建丢不掉）。所以 ⑦ 是**记录性**的一格：
//   它证明「关掉再打开 ⇒ 窗格回来、数据回来、轴还是对的」这条路径没坏，不是一条独立判据
//   （它只在 nofix 那种全局坏掉时跟着红）。假牙齿留着比没有更坏，所以那条变异删了。
//   退出码：0＝全绿；1＝有格红（把红的那条印出来）；2＝环境没搭好。
const path = require('path');
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch (e) {
  console.error('✗ 没装 playwright。先 `npm i playwright && npx playwright install chromium`，' +
                '再用 NODE_PATH=<那个 node_modules> 跑这个文件。');
  process.exit(2);
}
const PAGE = (process.env.E2E_URL || (process.argv[2] && !process.argv[2].startsWith('--')
  ? process.argv[2] : noUrl())).replace(/\/?$/, '/');   // E2E_URL 优先（上线门统一给，card-9b0fe913-758）
const MUT = (process.argv.find((a) => a.startsWith('--mut=')) || '--mut=none').split('=')[1];
const arg = (k, d) => (process.argv.find((a) => a.startsWith(`--${k}=`)) || `--${k}=${d}`).split('=')[1];
const SYMBOL = arg('symbol', 'BTCUSDT'), TF = arg('tf', '4h');   // Nova 外测那两张图是 1h 与 4h，都能量
const QUERY = `?symbol=${SYMBOL}&tf=${TF}&macd=1`;
const ZOOM_N = 200;                 // ⑤ 收到最近几根
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 变异锚点：各按**下一行/整行**认（行号会漂，句子不会）
const SITES = {
  // 摘掉修法那一行 ⇒ 副图那一格回到「跟着主图的对数轴」＝ 外测那张图
  nofix: { name: '摘掉「副图右轴掰回线性」那一行',
    re: /\n  ps\[1\]\.priceScale\('right'\)\.applyOptions\(\{ mode: LWC\.PriceScaleMode\.Normal \}\);/,
    rep: '' },
  // 轴钉死：第一次画完之后关掉 autoScale ⇒ 轴停在「全量范围」上，缩放它不跟
  //   （＝Bram 说的那半句「轴拿了全量范围、没按可见窗口算」）。锚在 paintSubData 的尾巴上。
  // ⑨ 的牙：把「给页头让出那一条」那一句摘掉 ⇒ 页头又压回柱尖上（＝ Atlas 15m 截图上那个样子）
  noreserve: { name: '摘掉「给页头让出比例尺上边留白」那一句（reserveSubhead 不叫了）',
    re: /\n  reserveSubhead\(\);[^\n]*/,
    rep: '' },
  // ⑨ 的另一半（余量 ≤12px）的牙：让过头 —— 页头那一条留得太多就是白挤数据，看着也不对
  fat: { name: '比例尺上边留白让过头（top 写死 0.35）',
    re: /const top = Math\.min\(0\.4, need \/ h\);[^\n]*/,
    rep: 'const top = 0.35;' },
  freeze: { name: '轴钉死在全量范围上（autoScale:false，画完之后）',
    re: /\n  renderSubHead\(\);\n  placeSubhead\(\);\n\}/,
    rep: '\n  renderSubHead();\n  placeSubhead();\n  sub.series.dif.priceScale().applyOptions({ autoScale: false });      // ← 变异：轴钉死\n}' },
};

const CELLS = [];
const ok = (id, name, pass, detail) => CELLS.push({ id, name, pass, detail });
// ★ 第三种结局：**未量**（判据没被行使 —— 挑不到能量的一屏、凑不齐三根、柱子太小）。
//   不是绿（没比过就不能算通过），也不是红（形状没被判决过，别冤枉页面）。
//   单独一栏印出来，计进 exit 2（Bram 2026-10-06：同一套里红压过未量 —— 有红退 1，只有未量才退 2）。
const 未量 = (id, name, detail) => CELLS.push({ id, name, pass: null, 未量: true, detail });
const r2 = (v) => Math.round(v * 100) / 100;

async function readAxis(page) {
  return page.evaluate((ZOOM_N) => {
    const A = window.__app, S = A.sub.series, panes = A.chart.panes();
    const H = panes[1].getHeight();
    const c = (v) => S.dif.priceToCoordinate(v);
    const c0 = c(0), c1 = c(1000);
    const perUnit = (c0 - c1) / 1000;                 // 每单位多少像素
    const valAt = (y) => (c0 - y) / perUnit;          // y 从窗格顶往下量 ⇒ 该处的值
    const win = () => {
      const vis = A.chart.timeScale().getVisibleLogicalRange();
      const i0 = Math.max(0, Math.ceil(vis.from)), i1 = Math.floor(vis.to);
      const slice = (s) => s.data().slice(i0, i1 + 1).map((x) => x.value).filter((v) => v != null);
      const all = [...slice(S.hist), ...slice(S.dif), ...slice(S.dea)];
      return { from: r2(vis.from), to: r2(vis.to), n: all.length,
               min: Math.min(...all), max: Math.max(...all) };
    };
    const r2 = (v) => Math.round(v * 100) / 100;
    const w = win();
    return {
      H, paneH: panes.map((p) => p.getHeight()),
      modes: panes.map((p) => p.priceScale('right').options().mode),
      映射: [-2000, -1000, 0, 1000, 2000, 3000].map((v) => [v, Math.round(c(v) * 100) / 100]),
      线性残差: Math.max(Math.abs(c(-1000) + c(1000) - 2 * c(0)), Math.abs(c(2000) - (2 * c(1000) - c(0)))),
      轴上沿: r2(valAt(0)), 轴下沿: r2(valAt(H)), 轴跨: r2(valAt(0) - valAt(H)),
      零线y: r2(c0),
      窗口: { from: w.from, to: w.to, n: w.n, min: r2(w.min), max: r2(w.max), 跨: r2(w.max - w.min) },
    };
  }, ZOOM_N);
}

// ⑧ 拿**像素**量柱子。三步：① 自己挑一屏（柱距够开、幅度比够宽）→ ② 缩放过去量 → ③ 把可见区间放回去。
// ★ 为什么非要在缩放之后量：首屏 barSpacing 0.5px ＝ 一列里两根柱子，「这一列的柱尖」可能是邻居那根。
//   量柱子这件事**只在这一屏分得开的时候才有意义** —— 分不开不是页面的毛病，是这一屏不适合量。
const PX_N_PER_3PX = 3;             // 一屏放多少根，按「每根 3px」算（1280px 宽 ⇒ ≈ 420 根）
const PX_SEP = 2;                   // 两根柱子至少要隔这么多像素才敢说「量到的是它自己」

async function readPixels(page) {
  // ① 挑窗口，挑**两屏**备着：
  //   `spread`＝「够大 × 拉得开」得分最高的那一段（⑧ 要比两个量级的高度：拉不开 ⇒ 这格自己没牙；
  //   柱子太小 ⇒ 量出来的是噪声）；
  //   `big`＝整份数据里柱子最大的那一段（万一第一屏量不出来 —— 比如轴被钉死在全量范围上、
  //   柱子缩成三个像素 —— 退到这一屏再试一次。两个都量不出来才认「量不出来」）。
  //   窗口从**整份数据**里挑，跟当前显示在哪一段无关。
  const plan = await page.evaluate(({ per3 }) => {
    const A = window.__app, S = A.sub.series, pane = A.chart.panes()[1].getHTMLElement();
    const d = S.hist.data();
    const W = pane.getBoundingClientRect().width;
    const N = Math.max(40, Math.min(d.length, Math.floor(W / per3)));
    const r2 = (v) => Math.round(v * 100) / 100;
    let 全局最大 = 0;
    for (const q of d) { const v = Math.abs(q.value == null ? 0 : q.value); if (v > 全局最大) 全局最大 = v; }
    let best = null, 最大的一屏 = null;
    const step = Math.max(1, Math.floor(N / 4));
    for (let i0 = 0; i0 + N <= d.length; i0 += step) {
      let mx = 0, mn = Infinity;
      for (let i = i0; i < i0 + N; i++) {
        const v = Math.abs(d[i].value == null ? 0 : d[i].value);
        if (v > mx) mx = v;
        // 只认「过零那几根以外的」小柱子：macd 在 0 附近是浮点噪声（1e-14 这种），
        //   拿它当分母 ⇒ 比变成 5e11，看着唬人、跟「这屏量不量得开」没关系
        if (v > 0) { if (!(v > mx * 1e-3)) continue; if (v < mn) mn = v; }
      }
      // 两个因子都要：① 这屏的柱子**够大**（够大才量得准 —— 轴被钉死在全量范围上时，
      //   小柱子会缩到 3px 那种，量出来的偏差是「量不准」不是「画错了」，别拿它当红）；
      //   ② 这屏的幅度**拉得开**（拉不开就比不出高度比，这格自己没牙）。只取①会挑到「大而齐」的一屏。
      const big = 全局最大 > 0 ? mx / 全局最大 : 0;
      const score = mn === Infinity ? 0 : big * (mx / mn);
      if (!best || score > best.score) best = { i0, score, mx, mn: mn === Infinity ? 0 : mn, big: r2(big) };
      if (!最大的一屏 || mx > 最大的一屏.mx) 最大的一屏 = { i0, mx, mn: mn === Infinity ? 0 : mn, big: 1 };
    }
    if (!best) return null;
    const vis = A.chart.timeScale().getVisibleLogicalRange();
    const win = (b) => ({ from: b.i0 - 0.5, to: b.i0 + N - 0.5,
                          极值: r2(b.mx), 最小: r2(b.mn), 大柱子占比: b.big, 得分: r2(b.score || 0) });
    return { N, 原区间: { from: vis.from, to: vis.to }, windows: { spread: win(best), big: win(最大的一屏) } };
  }, { per3: PX_N_PER_3PX }).catch(() => null);
  if (!plan) return { picks: [], meta: { err: '挑不出窗口（hist 是空的？）' } };

  // ② 量。挑三根：最大那根 ＋ 各**贴近 max/2、max/4** 的两根。
  // ★ 不能按名次挑（1st/3rd/8th）：hist 的头几名挤在一起（833/810/716），比值接近 1，量不出东西 ——
  //   第一版就是这么写的，绿不了不是数错，是**这一格自己没牙**。按目标量级挑，比值才拉得开（2×、4×）。
  // 两根柱子隔得太近（< 2px）⇒ 这一列量的可能不是它 ⇒ 换下一根（这就是首屏那次红的病根）。
  // 柱尖落在页头浮层盖住的那一段 ⇒ 换下一根（浮层把柱子最尖那几个像素画掉了，量出来的是被切过的柱）。
  const measure = () => page.evaluate(({ SEP }) => {
    const A = window.__app, S = A.sub.series, pane = A.chart.panes()[1].getHTMLElement();
    const d = S.hist.data(); const ts = A.chart.timeScale();
    const vis = ts.getVisibleLogicalRange();
    const i0 = Math.max(0, Math.ceil(vis.from)), i1 = Math.min(d.length - 1, Math.floor(vis.to));
    const win = d.slice(i0, i1 + 1);
    if (win.length < 10) return { picks: [], meta: { err: `这一屏只有 ${win.length} 根` } };
    const pr = pane.getBoundingClientRect();
    const 柱距 = Math.abs(ts.timeToCoordinate(win[Math.min(1, win.length - 1)].time) - ts.timeToCoordinate(win[0].time));
    // 页头那块浮层（压在副图上沿）：柱尖落进这个盒子就算被它画掉了
    const sh = document.getElementById('subhead');
    const on = sh && sh.classList.contains('on');
    const shb = on ? sh.getBoundingClientRect() : null;
    const band = shb ? { top: shb.top - pr.top, bot: shb.bottom - pr.top, left: shb.left - pr.left, right: shb.right - pr.left } : null;
    const hex = (c) => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
    // 判「这一像素算不算这根柱子」：**它是不是落在「柱子色 ↔ 背景色」这条线段上**（α 从 1 到 0）。
    //   走过两条弯路，都写在下面（都是**量错**，不是画错）：
    //   · 硬阈值（跟柱子色 ±6）⇒ 柱子顶端那几像素是跟背景**混**出来的，整条漏掉 ⇒ 矮柱子量矮 2.2px
    //   · 「调色板里离谁最近」⇒ 白线那一列的抗锯齿**灰尾**（87,90,96）离柱子色比离背景还近 ⇒ 被算成柱子（25px vs 真值 11px）
    //   灰尾不在那条线段上（它是「白线↔背景」那条线上的），落在线段外就判出去 —— 一句话把两种病一起治。
    const bgPal = [16, 18, 24];
    const onSegment = (px, q, bg) => {
      let best = Infinity;
      for (let a = 1; a >= 0.30; a -= 0.05) {
        const r = Math.abs(px[0] - (a * q[0] + (1 - a) * bg[0]))
                + Math.abs(px[1] - (a * q[1] + (1 - a) * bg[1]))
                + Math.abs(px[2] - (a * q[2] + (1 - a) * bg[2]));
        if (r < best) best = r;
      }
      return best <= 36;                 // 贴合那条线段（抗锯齿、以及跟网格线的轻微混合都容得下）
    };
    const canvases = [...pane.querySelectorAll('canvas')];
    const 零线y = Math.round(S.dif.priceToCoordinate(0) * 10) / 10;
    const ranked = win.slice().sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
    const mx = ranked[0];
    // 按「离目标量级多近」排，逐个试到能用为止
    const byNear = (base, f) => ranked.slice().sort((a, b) =>
      Math.abs(Math.abs(a.value) - Math.abs(base.value) * f) - Math.abs(Math.abs(b.value) - Math.abs(base.value) * f));
    const taken = []; const 跳过 = { 太挤: 0, 盖住: 0, 被线穿: 0, 量不到: 0 };
    // ★ 白线／黄线画在柱子**上头**（LWC 的绘制次序），穿过某一列时会把那根柱子的**柱尖那几行改画成线色**。
    //   那不是「柱子画矮了」，是**柱尖被盖住**了 —— 2026-10-06 查这一格红的时候抓到的，账记在文件头上。
    //   量柱尖得先知道柱尖在哪儿，所以这一关放在算出 `柱尖` 之后：线心离柱尖 ≤3px 就跳过这一根。
    //   3px 是这么来的：线宽 1px ＋ 上下各半像素抗锯齿 ≈ 2px，留 1px 余量。
    const 线的值 = new Map();
    for (const q of S.dif.data()) 线的值.set('dif:' + q.time, q.value);
    for (const q of S.dea.data()) 线的值.set('dea:' + q.time, q.value);
    const 被哪条线穿 = (柱尖, time) => {
      for (const [名, 键] of [['白线DIF', 'dif:'], ['黄线DEA', 'dea:']]) {
        const v = 线的值.get(键 + time);
        if (v == null) continue;
        if (Math.abs(S.dif.priceToCoordinate(v) - 柱尖) <= 3) return 名;
      }
      return null;
    };
    // 三个目标量级是相对**第一根真量到的那根**算的，不是死对 mx：最大那根要是被页头盖住/太挤被跳过，
    //   后面两根还按 mx 的 1/2、1/4 找，就会出现「第一根比第二根还小」—— 判据里的「拉得开」当场假红。
    let base = null;
    for (const f of [1, 0.5, 0.25]) {
      let got = null;
      for (const pt of byNear(base || mx, f)) {
        if (got) break;
        if (Math.abs(pt.value) === 0) { 跳过.量不到++; continue; }
        const x = ts.timeToCoordinate(pt.time);
        if (!isFinite(x)) { 跳过.量不到++; continue; }
        if (taken.some((p) => Math.abs(p.x - x) < SEP)) { 跳过.太挤++; continue; }
        const rgb = hex(pt.color || '#26a69a');
        let best = { px: 0, top: null, bot: null };
        for (const cv of canvases) {
          const cr = cv.getBoundingClientRect();
          if (!cv.width || !cr.width) continue;
          const s = cv.width / cr.width;
          const cx = Math.round((x + (cr.left - pr.left)) * s);      // 画布不在窗格左沿时也要对上（坐标平移量算进去）
          if (cx < 0 || cx >= cv.width) continue;
          const col = cv.getContext('2d').getImageData(cx, 0, 1, cv.height).data;
          const ys = [];
          for (let y = 0; y < cv.height; y++) {
            const px = [col[y * 4], col[y * 4 + 1], col[y * 4 + 2]];
            if (onSegment(px, rgb, bgPal)) ys.push(y / s);
          }
          // ★ 量的是**柱尖**，不是「数了多少像素」：黄白线画在柱子**上头**，穿过那一列时会把柱子**切断**，
          //   断成几截之后「数像素」就少算了（矮柱子 5.2px 量成 3px）。柱尖是那一列上柱子色**最远**的那一个像素，
          //   断不断都取得到；柱高 = 柱尖到零线的距离（hist 的 base 就是 0 —— 这也是 ③ 那一格在管的事）。
          if (ys.length > best.px) best = { px: ys.length, top: Math.min(...ys), bot: Math.max(...ys) };
        }
        if (best.px === 0) { 跳过.量不到++; continue; }
        // 正柱看顶、负柱看底 —— 那一个才是柱尖
        const 柱尖 = Math.round((pt.value >= 0 ? best.top : best.bot) * 10) / 10;
        // 柱尖被白线／黄线压着 ⇒ 量到的「最上面那个柱色像素」是线画的，不是柱子的边 —— 换下一根
        if (被哪条线穿(柱尖, pt.time)) { 跳过.被线穿++; continue; }
        // ★ 这里的字段名要跟上面那个对象**一模一样**（`bot`，不是 `bottom`）：第一版写成 `band.bottom`，
        //   对象里没这个键 ⇒ `108 <= undefined + 2` ⇒ **恒 false** —— 这条闸一直是死的（量出来永远
        //   「盖住 0」）。手工把带子撑大才逮到：跟 readout 那次 ⑯ 的死条件同一个形状。
        if (band && x >= band.left - 2 && x <= band.right + 2 && 柱尖 >= band.top - 2 && 柱尖 <= band.bot + 2) {
          跳过.盖住++; continue;                                     // 被页头那块浮层画掉了
        }
        got = { time: pt.time, value: pt.value, color: pt.color, x: Math.round(x * 10) / 10, 柱尖,
                高: Math.round(Math.abs(零线y - 柱尖) * 10) / 10, 零线y };
      }
      if (got) { taken.push(got); if (!base) base = got; }
    }
    // 这格有没有牙，看的是**三根柱子的数据比**（判据要求 ≥2），不是整屏的极值比
    const 牙 = taken.length === 3 ? Math.round(Math.abs(taken[0].value) / Math.abs(taken[2].value) * 100) / 100 : null;
    // ★★ 「挑了几根才凑够」（Nova 2026-10-06 定，Bram／Atlas 那条收敛后的版本）：这一屏为了凑够 3 根，
    //   **一共碰过几根候选**。为什么要它：上面那四栏「跳过」是按**原因**分的，读不出**分母** ——
    //   「跳过 9」到底是 3/12 还是 3/40，光看跳过数分不清。而真正要防的是「最后真量到的太少」：
    //   一屏要靠捞四十根才凑出三根，账面上的「3 根」会**读得比实际自信**。（Nova 原话要的就是 3/12、3/40
    //   这个形状；「跳过 > 1/3 就记未量」那条拍脑袋的阈值当场作废，不另立规矩。）
    //   ★ 这个数是**推出来的，不是另开一个计数器** —— 上面那个循环里每一根候选**要么**变成 `got`（进 taken），
    //     **要么**撞上四栏跳过之一 `continue`，没有第三条路 ⇒ 碰过的根数 ≡ Σ跳过 ＋ taken.length。
    //     反过来说：**将来谁在循环里加一条新的 `continue`，必须同时给它一栏跳过**，否则这个数会**静默少算**
    //     （跟 `band.bottom` 那个死条件同一个形状：不报错、闸不红，只是数变小了）。
    const 挑了几根 = 跳过.太挤 + 跳过.盖住 + 跳过.被线穿 + 跳过.量不到 + taken.length;
    return { picks: taken.map(({ x, ...q }) => q), meta: {
      柱距: Math.round(柱距 * 100) / 100, 屏内根数: win.length, 零线y, 三根数据比: 牙, 挑了几根,
      跳过, 页头盖住的一段: band ? { y: [Math.round(band.top), Math.round(band.bot)], x: [Math.round(band.left), Math.round(band.right)] } : null } };
  }, { SEP: PX_SEP });
  // 「这一屏量得开吗」＝ 判据里那三件事（三根都有、像素起步够高、数据比够宽）。
  // ★ 这是**量具的前提**，不是判据本身：判据一个字没动，动的是「在哪一屏上量」。
  const 量得开 = (q) => q.picks.length === 3 && q.picks[0].高 >= 8 && q.picks[2].高 >= 5
    && Math.abs(q.picks[0].value) / Math.abs(q.picks[1].value) >= 1.5
    && Math.abs(q.picks[0].value) / Math.abs(q.picks[2].value) >= 2.0;

  let m = null, 用的哪一屏 = null; const 试了 = [];
  for (const which of ['spread', 'big']) {
    const w = plan.windows[which];
    if (!w) continue;
    await page.evaluate((p) => window.__app.chart.timeScale().setVisibleLogicalRange({ from: p.from, to: p.to }), w);
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
    await sleep(300);
    const got = await measure();
    const readable = 量得开(got);
    试了.push({ 屏: which, 根数: got.picks.length, 高: got.picks.map((q) => q.高), 量得开: readable });
    if (!m || readable) { m = got; 用的哪一屏 = which; }
    if (readable) break;
  }

  // ③ 放回去（⑤ 的 before/after 与那张截图都在原来的区间上）
  await page.evaluate((o) => window.__app.chart.timeScale().setVisibleLogicalRange(o), plan.原区间);
  await sleep(150);
  const back = await page.evaluate((o) => {
    const v = window.__app.chart.timeScale().getVisibleLogicalRange();
    return { from: Math.round(v.from * 100) / 100, to: Math.round(v.to * 100) / 100, 一样: Math.abs(v.from - o.from) < 0.51 && Math.abs(v.to - o.to) < 0.51 };
  }, plan.原区间);

  return { picks: m.picks, meta: { ...m.meta, 用的哪一屏, 试了,
           挑的窗口: [plan.windows[用的哪一屏].from, plan.windows[用的哪一屏].to], 还回去了: back } };
}

// ⑨ 页头那块浮层**压在**副图上沿（它不是排在窗格上面，是盖上去的）—— 它下沿以上不许有数据。
// Atlas 15m 截图上那条：最高那根柱子的柱尖被它画掉了。见 app.js 的 reserveSubhead()。
// ★ 量的是**三个系列各自的最极端点**的 y（hist/dif/dea 都是那一格的轴在撑），不是「有没有柱子被盖住」：
//   柱尖够不够得到页头要看「这一屏里柱子是不是最极端的那个」，多数窗口里 DIF 比柱子大 ⇒ 柱子根本到不了顶，
//   照「柱子被盖住没有」量，首屏永远是 0 —— 那正是这个病藏了这么久的原因（Atlas 是缩放/换档之后才看见的）。
//   「页头那一条里有没有数据」这条判据跟窗口无关：轴的上沿就是这一屏最极端的那个点，它在哪一屏都贴着轴顶画。
//   外加像素复核：最极端那根**柱子**那一列，画布上第一个柱色像素要跟映射出来的 y 对上（±2px）
//   —— 证明「映射说它在下面」和「画出来确实在下面」是同一件事（⑧ 那格是同一个道理）。
async function readHeadBand(page) {
  return page.evaluate(() => {
    const A = window.__app, S = A.sub.series, paneEl = A.chart.panes()[1].getHTMLElement();
    const ts = A.chart.timeScale();
    const pr = paneEl.getBoundingClientRect();
    const sh = document.getElementById('subhead');
    const on = !!(sh && sh.classList.contains('on'));
    const sr = on ? sh.getBoundingClientRect() : null;
    const head = sr ? { top: Math.round((sr.top - pr.top) * 10) / 10, bot: Math.round((sr.bottom - pr.top) * 10) / 10,
                        left: Math.round((sr.left - pr.left) * 10) / 10, right: Math.round((sr.right - pr.left) * 10) / 10,
                        h: Math.round(sr.height * 10) / 10 } : null;
    const vis = ts.getVisibleLogicalRange();
    const r2 = (v) => Math.round(v * 100) / 100;
    // 每个系列在**可见窗口**里最极端的那个点：正负都算，取 y 最小（最靠上）的那个
    const peaks = {};
    for (const [k, s] of Object.entries({ hist: S.hist, dif: S.dif, dea: S.dea })) {
      const d = s.data();
      let best = null;
      for (let i = Math.max(0, Math.ceil(vis.from)); i <= Math.min(d.length - 1, Math.floor(vis.to)); i++) {
        const q = d[i]; if (!q || q.value == null) continue;
        const y = s.priceToCoordinate(q.value);
        if (!isFinite(y)) continue;
        if (!best || y < best.y) best = { i, v: r2(q.value), y: Math.round(y * 10) / 10 };
      }
      peaks[k] = best;
    }
    const minY = Math.min(...Object.values(peaks).filter(Boolean).map((q) => q.y));
    // 最极端的那根柱子（柱尖最靠上的）：像素复核它那一列
    const hd = S.hist.data();
    let tb = null;
    for (let i = Math.max(0, Math.ceil(vis.from)); i <= Math.min(hd.length - 1, Math.floor(vis.to)); i++) {
      const q = hd[i]; if (!q || q.value == null) continue;
      const y = S.hist.priceToCoordinate(q.value);
      if (isFinite(y) && (!tb || y < tb.y)) tb = { i, t: q.time, v: r2(q.value), color: q.color, y: Math.round(y * 10) / 10 };
    }
    // ★ 像素复核跟 ⑧ 同一条前提：**柱距 ≥ 2px** 才谈得上「这一列量到的是它自己」。
    //   首屏 1280px 铺 2000 根（0.5px/柱）时，一列里挤着两根 —— 量出来的是邻居（实测 ZEC 15m 首屏：
    //   映射 y 62.4、画布上第一个柱色像素 84 ⇒ 差 21.6px，**是量具的错，不是页面的错**）。
    //   那种时候这半边认「没量」，明写在那一行里；判据的**主半**（映射出来的极值 y）不受影响。
    const 柱距 = Math.abs(ts.timeToCoordinate(hd[Math.min(1, hd.length - 1)].time) - ts.timeToCoordinate(hd[0].time));
    let painted = null;
    if (tb && 柱距 >= 1.9) {
      const x = ts.timeToCoordinate(tb.t);
      const hex = (c) => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
      const bgPal = [16, 18, 24];
      const onSeg = (px, q, bg) => {
        let best = Infinity;
        for (let a = 1; a >= 0.30; a -= 0.05) {
          const dd = Math.abs(px[0] - (a * q[0] + (1 - a) * bg[0])) + Math.abs(px[1] - (a * q[1] + (1 - a) * bg[1]))
                   + Math.abs(px[2] - (a * q[2] + (1 - a) * bg[2]));
          if (dd < best) best = dd;
        }
        return best <= 36;
      };
      const rgb = hex(tb.color || '#26a69a');
      for (const cv of [...paneEl.querySelectorAll('canvas')]) {
        const cr = cv.getBoundingClientRect();
        if (!cv.width || !cr.width || !isFinite(x)) continue;
        const sc = cv.width / cr.width;
        const cx = Math.round((x + (cr.left - pr.left)) * sc);
        if (cx < 0 || cx >= cv.width) continue;
        const col = cv.getContext('2d').getImageData(cx, 0, 1, cv.height).data;
        const ys = [];
        for (let y = 0; y < cv.height; y++) {
          if (onSeg([col[y * 4], col[y * 4 + 1], col[y * 4 + 2]], rgb, bgPal)) ys.push(y / sc);
        }
        if (ys.length && (!painted || ys.length > painted.n)) painted = { n: ys.length, top: Math.round(Math.min(...ys) * 10) / 10 };
      }
    }
    return { on, head, 窗格高: Math.round(pr.height), peaks, minY: Math.round(minY * 10) / 10,
             余量: head ? Math.round((minY - head.bot) * 10) / 10 : null,
             柱尖: tb, 画出来: painted, 柱距: Math.round(柱距 * 100) / 100,
             像素差: painted && tb ? Math.round(Math.abs(painted.top - tb.y) * 10) / 10 : null,
             可见根数: Math.max(0, Math.min(hd.length - 1, Math.floor(vis.to)) - Math.max(0, Math.ceil(vis.from)) + 1) };
  });
}

// ★ 量之前先等版面落定（卡-9b0fe913-758 · Nova 派的「量早了一格」）。
//   ⑦ 重建那一格原来**偶发飘红**，读数长这样：绿的时候「页头 y=[6,27]」，红的时候「页头 y=[178,199]」
//   —— 正好**下移一格高**（同一条读数里就印着 `格高 172`）。看着像页头盖住了数据，其实是
//   **量在了页面还没把页头摆到位的那一拍上** —— 那一拍页面自己也确实是错的（下一段），两件事都要治：
//   页面那边堵掉「照错的格高摆」(`web/app.js` 的 `placeSubhead()`)，这边保证「不量没落定的版面」。
//
//   真身（2026-10-05 探针量出来的，不是猜的）：点开 MACD 时 `app.js` 的 `syncSub()` 是
//   `buildSub()`（建窗格）**紧接着**就 `paintSubData()`（里面叫 `placeSubhead()`）——
//   那一刻 LWC **还没把新窗格排出来**，`pane.getHeight()` 是 **0**，于是：
//     · `reserveSubhead()` 头一句 `if (!h) return;` ⇒ 让白那一趟整个没跑；
//     · `placeSubhead()` 按「格高 0」算 top ⇒ 页头被写到**低一整格**的地方。
//   探针实测三趟调用：`h=0 → top 686px`、`h=0 → top 686px`、`h=172 → top 514px`（686−514 ＝ 172 ＝ 格高）。
//   ⇒ **修回来的那一趟是后面才到的**（换格/取数那一趟 paint）。工装原来只 `sleep(800)` 就量，
//     落在 686 那一段上就红、落在 514 之后才绿 —— 这就是"飘"的来源。
//
//   ★ 等的**不是**「几何不动了」：686 那个状态是**稳的**，稳着不动地错。等的是**页面自己把页头摆到位**：
//     页头得贴住副图那一格的上沿（`SUBHEAD_TOP=4`，实测 6px）。等不到就照量 —— **红了就是真红**，
//     绝不因为「等超时」就当绿（判据一个字没改，见下面 ⑨）。
const 页头贴住了 = (page) => page.evaluate(() => {
  const A = window.__app;
  const pane = A && A.chart && A.chart.panes()[1];
  const sh = document.getElementById('subhead');
  if (!pane || !sh || !sh.classList.contains('on')) return true;   // 没开／没那一格 ⇒ 不归这条等
  const pr = pane.getHTMLElement().getBoundingClientRect();
  if (!pr.height) return false;                                     // 窗格还没排出来（就是 getHeight()===0 那一拍）
  const sr = sh.getBoundingClientRect();
  return Math.abs(sr.top - pr.top) <= 24;                           // 贴着上沿；错的时候是 178（一整格高）
});

async function waitLayoutSettle(page, { 最多 = 5000 } = {}) {
  const t0 = Date.now();
  for (;;) {
    if (await 页头贴住了(page)) return { ok: true, 等了: Date.now() - t0 };
    if (Date.now() - t0 >= 最多) return { ok: false, 等了: Date.now() - t0 };
    await sleep(50);
  }
}

async function judge(page, tag) {
  const settle = await waitLayoutSettle(page);
  if (!settle.ok) console.error(`⚠ ${tag}：页头 ${settle.等了}ms 内没贴住副图上沿 —— 照量（量到的是没落定的版面，红了是真红）`);
  const a = await readAxis(page);
  // ⑨ 页头那条带子：压在上面就不许盖住数据（每一趟都量 —— 它跟缩放到哪一屏无关）。
  const hb = await readHeadBand(page);
  ok(`${tag}⑨ 页头不盖数据`, 'hist/dif/dea 最极端的点都在页头下沿以下，且让出来的正是那一条（余量 0～12px）',
     hb.on && hb.head && hb.minY >= hb.head.bot && hb.余量 <= 12 && (hb.像素差 == null || hb.像素差 <= 2),
     `页头 y=${hb.head ? JSON.stringify([hb.head.top, hb.head.bot]) : '没开'}（高 ${hb.head && hb.head.h}，格高 ${hb.窗格高}）`
     + `；三个系列的极值 y ${JSON.stringify(Object.fromEntries(Object.entries(hb.peaks).map(([k, q]) => [k, q && q.y]))) }`
     + `（hist 最极端那根：值 ${hb.柱尖 && hb.柱尖.v} → y ${hb.柱尖 && hb.柱尖.y}）`
     + `｜像素复核：${hb.像素差 == null
        ? `★ 没量（柱距 ${hb.柱距}px < 2 ⇒ 一列里挤着不止一根，量到的是邻居 —— 跟 ⑧ 同一条前提）；判据的主半还是量出来的`
        : `画布上第一个柱色像素 y ${hb.画出来.top}，跟映射差 ${hb.像素差}px`}`
     + `｜最小 y ${hb.minY} vs 页头下沿 ${hb.head && hb.head.bot} ⇒ 余量 ${hb.余量}px（负＝盖住了；>12＝让过头，白挤数据）`
     + `｜窗口里 ${hb.可见根数} 根`);
  const span = a.轴跨, wspan = a.窗口.跨;
  ok(`${tag}① 线性`, '轴是线性的（三点共线，残差 ≤1px）', a.线性残差 <= 1,
     `残差 ${r2(a.线性残差)}px；映射 ${JSON.stringify(a.映射)}`);
  ok(`${tag}② 罩得住`, '轴上沿 ≥ 窗口 max、下沿 ≤ 窗口 min', a.轴上沿 >= a.窗口.max - wspan * 0.01 && a.轴下沿 <= a.窗口.min + wspan * 0.01,
     `轴 ${a.轴下沿}～${a.轴上沿} vs 窗口 ${a.窗口.min}～${a.窗口.max}（${a.窗口.n} 根，logical ${a.窗口.from}～${a.窗口.to}）`);
  ok(`${tag}③ 零线`, '0 在轴里', a.零线y >= 0 && a.零线y <= a.H, `0 的 y=${a.零线y}，格高 ${a.H}`);
  ok(`${tag}④ 不虚胖`, '轴跨 ≤ 2.5 × 窗口数据跨', span <= 2.5 * wspan, `轴跨 ${span} vs 数据跨 ${wspan}（${r2(span / wspan)}×）`);
  ok(`${tag}⑥ 没误伤`, '主图那一格仍是对数（mode=1）', a.modes[0] === 1, `两格 mode=${JSON.stringify(a.modes)}（[0]=主图，[1]=副图）`);
  // ⑧ 像素：三根柱子的**画出来**的高度比 vs 数据比。
  // ★ 只在标签非空时量 ＝ **缩放之后**才量（首屏 barSpacing 0.5px，一列两根柱子，量到的是邻居）。
  //   它自己挑一屏、量完放回原区间 —— 所以这一次调用里 ⑤ 读到的 before/after 不受影响。
  if (tag) {
    const P = await readPixels(page);
    const px = P.picks, meta = P.meta || {};
    const 量具前提 = meta.柱距 >= PX_SEP * 0.9;          // 每根柱子得有自己的一列（首屏 0.5px 就是这么红的）
    if (px.length < 3 || !量具前提) {
      // ★ 这一支是**量不出来**（不是画错了）：柱距不够／凑不齐三根。写在名字里，别让复核的人把它读成形状的判决。
      // ★★ 它**既不算绿、也不算红**：走「未量」这一档 —— 不计进 `red`，但计进 exit code 的 2（见文件尾）。
      //    理由（Nova 2026-10-06）：不算绿是显然的；不算红是因为它**没比成**，
      //    而「红」这个词得留给「量到了、形状确实不对」。两者混在一个 `pass:false` 里，
      //    复核的人分不清「这格坏了」和「这格今天没量着」。
      未量(`${tag}⑧ 像素形状`, '**量不出来**（柱距不够／凑不齐三根，不是画错了）；判据本身不降级',
         (px.length < 3 ? `只量到 ${px.length} 根` : `柱距只有 ${meta.柱距}px（< ${PX_SEP}）—— 一列里挤着不止一根，量不准`)
         + `；${JSON.stringify(meta)}`);
    } else {
      const k = px[0].高 / Math.abs(px[0].value);        // 拿最大那根定比例尺（px / 单位）
      const 偏差 = px.map((q) => Math.round(Math.abs(q.高 - k * Math.abs(q.value)) * 10) / 10);
      const 符号对 = px.every((q) => (q.value >= 0 ? q.柱尖 <= q.零线y + 2 : q.柱尖 >= q.零线y - 2));
      const 比值 = px.map((q) => Math.round(q.高 / Math.abs(q.value) * 1e6) / 1e6);
      // 「拉得开」按**数据**判（数据比 2× / 4× 才谈得上比高度比），像素上是 8px 起步才量得准
      const d0 = Math.abs(px[0].value);
      const 缩得开 = px[0].高 >= 8 && px[2].高 >= 5 && d0 / Math.abs(px[1].value) >= 1.5 && d0 / Math.abs(px[2].value) >= 2.0;
      // 三态在这里分开：符号错／偏差超 ⇒ **红**（量到了，形状确实不对）；
      //   这三根太小够不着、比例拉不开 ⇒ **未量**（判据没被行使）；两者都不是 ⇒ 绿。
      const 判词 = (缩得开 ? '' : '★ 这一屏的柱子太小／拉不开 ⇒ **这一格量不出来**（不是画错了）；')
         + (符号对 ? '' : '★ 符号错了（正柱跑到零线下边／负柱跑到上边）；')
         + px.map((q, i) => `值 ${Math.round(q.value)}→柱尖 ${q.柱尖}（零线 ${q.零线y}，高 ${q.高}px，偏差 ${偏差[i]}px）`).join('；')
         + `；px/单位 ${比值.join('/')}`
         + `｜量在哪一屏：${meta.用的哪一屏}（试了 ${JSON.stringify(meta.试了)}）、柱距 ${meta.柱距}px、屏内 ${meta.屏内根数} 根、三根数据比 ${meta.三根数据比}`
         + `｜跳过 太挤 ${meta.跳过.太挤}/盖住 ${meta.跳过.盖住}/**被线穿 ${meta.跳过.被线穿}**/量不到 ${meta.跳过.量不到}`
         + `｜挑了几根才凑够 **${px.length}/${meta.挑了几根}**（这一屏碰过的候选 ÷ 真量到的）`
         + `｜页头盖住 y=${JSON.stringify((meta.页头盖住的一段 || {}).y)}`
         + `｜原区间还回去了：${meta.还回去了 && meta.还回去了.一样 ? '是' : `否（${JSON.stringify(meta.还回去了)}）`}`;
      if (!符号对 || (缩得开 && !偏差.every((x) => x <= 1.5))) {
        ok(`${tag}⑧ 像素形状`, '三根柱子的高度比＝数据比（±1.5px）、符号对、且比例拉得开', false, 判词);
      } else if (!缩得开) {
        未量(`${tag}⑧ 像素形状`, '**量不出来**（这三根太小／拉不开，判据没被行使；不是画错了）', 判词);
      } else {
        ok(`${tag}⑧ 像素形状`, '三根柱子的高度比＝数据比（±1.5px）、符号对、且比例拉得开', true, 判词);
      }
    }
  }
  return a;
}

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1280, height: 860 }, deviceScaleFactor: 2 });
  const c = await ctx.newPage();
  const site = SITES[MUT];
  if (MUT !== 'none' && !site) { console.error(`✗ 没有这个变异：${MUT}（有 none/${Object.keys(SITES).join('/')}）`); process.exit(2); }
  if (site) {
    await c.route('**/app.js*', async (route) => {
      const r = await route.fetch();
      const t = await r.text();
      if (!site.re.test(t)) { console.error(`✗ 变异锚点没命中（${MUT}）—— app.js 变了？`); process.exit(2); }
      await route.fulfill({ status: 200, contentType: 'text/javascript', body: t.replace(site.re, site.rep) });
    });
  }
  const errs = [];
  c.on('pageerror', (e) => errs.push(String(e)));
  await c.goto(PAGE + QUERY, { waitUntil: 'domcontentloaded' });
  await c.waitForFunction(() => window.__app && window.__app.sub && window.__app.sub.series, null, { timeout: 60000 });
  await sleep(2500);
  if (errs.length) { console.error('✗ 页面报错：', errs.slice(0, 3).join(' | ')); process.exit(2); }

  console.log(`跑法：${MUT === 'none' ? '原样' : '变异 · ' + site.name}   ${PAGE}${QUERY}`);
  const before = await judge(c, '');
  const shotBox = await c.evaluate(() => { const r = document.getElementById('chart').getBoundingClientRect();
    const p = window.__app.chart.panes(); return { x: r.x, y: r.y + p[0].getHeight(), w: r.width, h: p[1].getHeight() }; });
  await c.screenshot({ path: `/tmp/macd-axis-${SYMBOL}-${TF}-${MUT}.png`, clip: { x: shotBox.x, y: shotBox.y, width: shotBox.w, height: shotBox.h } });

  // ⑤ 缩放跟着缩
  const n = await c.evaluate(() => window.__app.state.data.bars.length);
  await c.evaluate(({ n, ZOOM_N }) => window.__app.chart.timeScale().setVisibleLogicalRange({ from: n - ZOOM_N, to: n }), { n, ZOOM_N });
  await sleep(900);
  const after = await judge(c, '缩放后');
  const shrunk = after.轴跨 < before.轴跨 * 0.9;
  ok('⑤ 缩放跟着缩', `收到最近 ${ZOOM_N} 根后轴跨明显变小（<0.9×）`, shrunk,
     `${before.轴跨} → ${after.轴跨}（窗口数据跨 ${before.窗口.跨} → ${after.窗口.跨}）`);

  // ⑦ 重建：点一次 MACD 那颗 chip（真用户路径：关掉 ⇒ 窗格收回去；打开 ⇒ 重新建格、重新要数据）
  const clickChip = () => c.evaluate(() => {
    const b = document.querySelector('button.chip[data-key="macd"]');
    if (!b) return false; b.click(); return true;
  });
  if (!(await clickChip())) { ok('⑦ 重建', '关掉再打开 MACD ⇒ 窗格照旧是对的', false, '找不到 MACD 那颗 chip'); }
  else {
    await sleep(1200);
    await clickChip();
    let back = false, data = false;
    try {
      await c.waitForFunction(() => !!(window.__app.sub.series && window.__app.chart.panes().length > 1), null, { timeout: 20000 });
      back = true;
      await c.waitForFunction(() => !!(window.__app.sub.series && window.__app.sub.series.hist.data().length > 100), null, { timeout: 20000 });
      data = true;
    } catch (e) { /* back/data 保持 false，下面按实情报 */ }
    ok('⑦ 重建', '关掉再打开 MACD ⇒ 窗格回来、数据回来', back && data,
       back ? (data ? '窗格与数据都回来了' : '窗格回来了，20s 内没等到数据') : '20s 内窗格没回来');
    if (back && data) { await sleep(800); await judge(c, '重建后'); }
  }

  const red = CELLS.filter((x) => x.pass === false);
  const 未 = CELLS.filter((x) => x.pass === null);
  for (const x of CELLS) console.log(`${x.pass === true ? '✓' : x.pass === null ? '◻' : '✗'} ${x.id} ${x.name} —— ${x.detail}`);
  console.log(`\n${CELLS.filter((x) => x.pass === true).length}/${CELLS.length} 绿`
    + (未.length ? `、${未.length} 未量（不是红：判据没被行使）` : '')
    + (red.length ? `、${red.length} 红` : ''));
  // 红压过未量（Bram）：有红退 1，没红只有未量退 2（＝「没比成」，predeploy 不放行），否则 0
  if (red.length) console.log(`红的：${red.map((x) => x.id).join('、')}`);
  if (未.length) console.log(`未量的：${未.map((x) => x.id).join('、')}`);
  await b.close();
  process.exit(red.length ? 1 : (未.length ? 2 : 0));
})().catch((e) => { console.error('炸了：', e.message); process.exit(2); });

// 不带默认页面地址（部署细节不进仓，card-58518cb5-357）：没给 E2E_URL、也没给地址参数，就直接报错、退出码 2（环境没搭好）。
// predeploy 会 export E2E_URL。写法跟 tools/web_fs_drag_e2e.js 一致。
function noUrl() {
  console.error('缺页面地址：请设 E2E_URL（或把页面地址当参数）。本工装不带默认地址。');
  process.exit(2);
}
