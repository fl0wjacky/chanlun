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
//   ⑦ **重建也管用**：点一次「MACD」那颗 chip（关 ⇒ 窗格收回去；开 ⇒ 重新建格、重新要数据），
//      回来之后 ①②③④ 必须照样绿 —— 修法长在 `buildSub()` 里，这条防的是「只在第一次打开生效」。
//   ⇒ 轴上刻度是从这根比例尺生成的，所以「轴的范围」就是「刻度的范围」：
//      ① 红＝刻度不是正经刻度，② 红＝刻度对不上数据的最大最小（Atlas 的原话）。
//
// 跑法（要真后台：
//   1) python3 web/server.py --port 8799 --no-prewarm      （只绑回环）
//   2) NODE_PATH=<playwright 的 node_modules> node tools/web_macd_axis.js [页面地址] [--mut=nofix|freeze]
//   不给 --mut ⇒ 只跑原样。--mut=nofix 摘掉那行修（＝复现外测那张图）；
//   --mut=freeze 换成「轴钉死在全量范围上」（＝Bram 猜的那条，用来证明 ⑤ 有牙）。
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
const PAGE = (process.argv[2] && !process.argv[2].startsWith('--') ? process.argv[2]
  : 'http://127.0.0.1:8799/').replace(/\/?$/, '/');
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
  freeze: { name: '轴钉死在全量范围上（autoScale:false，画完之后）',
    re: /\n  renderSubHead\(\);\n  placeSubhead\(\);\n\}/,
    rep: '\n  renderSubHead();\n  placeSubhead();\n  sub.series.dif.priceScale().applyOptions({ autoScale: false });      // ← 变异：轴钉死\n}' },
};

const CELLS = [];
const ok = (id, name, pass, detail) => CELLS.push({ id, name, pass, detail });
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

async function judge(page, tag) {
  const a = await readAxis(page);
  const span = a.轴跨, wspan = a.窗口.跨;
  ok(`${tag}① 线性`, '轴是线性的（三点共线，残差 ≤1px）', a.线性残差 <= 1,
     `残差 ${r2(a.线性残差)}px；映射 ${JSON.stringify(a.映射)}`);
  ok(`${tag}② 罩得住`, '轴上沿 ≥ 窗口 max、下沿 ≤ 窗口 min', a.轴上沿 >= a.窗口.max - wspan * 0.01 && a.轴下沿 <= a.窗口.min + wspan * 0.01,
     `轴 ${a.轴下沿}～${a.轴上沿} vs 窗口 ${a.窗口.min}～${a.窗口.max}（${a.窗口.n} 根，logical ${a.窗口.from}～${a.窗口.to}）`);
  ok(`${tag}③ 零线`, '0 在轴里', a.零线y >= 0 && a.零线y <= a.H, `0 的 y=${a.零线y}，格高 ${a.H}`);
  ok(`${tag}④ 不虚胖`, '轴跨 ≤ 2.5 × 窗口数据跨', span <= 2.5 * wspan, `轴跨 ${span} vs 数据跨 ${wspan}（${r2(span / wspan)}×）`);
  ok(`${tag}⑥ 没误伤`, '主图那一格仍是对数（mode=1）', a.modes[0] === 1, `两格 mode=${JSON.stringify(a.modes)}（[0]=主图，[1]=副图）`);
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

  const red = CELLS.filter((x) => !x.pass);
  for (const x of CELLS) console.log(`${x.pass ? '✓' : '✗'} ${x.id} ${x.name} —— ${x.detail}`);
  console.log(`\n${CELLS.length - red.length}/${CELLS.length} 绿`);
  await b.close();
  process.exit(red.length ? 1 : 0);
})().catch((e) => { console.error('炸了：', e.message); process.exit(2); });
