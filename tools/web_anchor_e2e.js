// 取数飞着的时候用户拖了图 ⇒ 数据回来、重画以后，视口必须留在**拖完的那一屏**（card-0d389a48-4cc）。
//
//   node tools/web_anchor_e2e.js [输出目录] [页面地址]      // E2E_URL 优先（上线门统一给）
//
// 为什么要它：换看法／换切法／收盘后自动重取，三处原来都在 `await load()` **之前**抓锚点，回来按那个锚点摆回去。
//   取数要好几秒（后台 SWR、币安慢），这几秒里用户拖过图，就会被摆回「拖之前」—— 那一下拖白拖了。
//   web_readout_e2e ⑭ 冷启动偶发的 `a 快滑 4740→4740` 就是这个：整点收盘后 2–10 秒的自动重取正好飞在快滑当中。
//   修法（Iris 定的写法）：要摆回去的那一屏，永远在「即将动数据」那一刻现读，不读任何缓存的那份。
// 怎么量：把那一趟 /api/chart 扣住 3 秒（page.route），这 3 秒里用真鼠标拖一下，放行，等画完，看视口在哪。
//   只量「换看法」这一处：自动重取要等收盘才发，这里够不着；换切法那组 chip 现在被 CUT_HIDDEN 收成一档、
//   页面上根本不画，用户够不着。三处是同一段写法（锚点挪到 draw 之前现读），靠这一处守住写法。
// ★ 先证明这一套在起作用：拖之前拖之后视口得真动了（不然「留住了」是空转）。
const path = require('path');
const os = require('os');
const { chromium } = require('playwright');

const OUT = process.argv[2] || path.join(os.tmpdir(), 'anchor-e2e');
const PAGE = (process.env.E2E_URL || process.argv[3] || 'http://127.0.0.1:8793/').replace(/\/?$/, '/');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const CASES = [
  // [名字, 扣住哪一趟请求, 点哪颗 chip 触发, 先要打开的图层 chip（看法/切法 chip 在对应图层关着时是灰的）, 等什么状态算回来了]
  ['换看法（setMeasure）', /\/api\/chart\?.*measure=slope/, '.mchip[data-measure="slope"]', 'sig',
   () => window.__app.state.data && window.__app.state.data.measure === 'slope'],
];

(async () => {
  const b = await chromium.launch();
  let pass = 0;
  for (const [name, re, chip, layer, done] of CASES) {
    const ctx = await b.newContext({ viewport: { width: 1280, height: 800 } });
    const p = await ctx.newPage();
    await p.route(re, async (route) => { await sleep(3000); await route.continue(); });
    await p.goto(PAGE + '?symbol=ZECUSDT&tf=1h&last=300', { waitUntil: 'domcontentloaded' });
    await p.waitForFunction(() => window.__app && window.__app.state.data, null, { timeout: 60000 });
    await sleep(1500);
    const vr = () => p.evaluate(() => window.__app.chart.timeScale().getVisibleLogicalRange().from);
    if (await p.locator(chip).isDisabled()) { await p.locator(`.chip[data-key="${layer}"]`).click(); await sleep(500); }
    const box = await p.locator('#chart').boundingBox();
    await p.locator(chip).click();
    await sleep(300);
    const f0 = await vr();
    const cx = box.x + box.width * 0.5, cy = box.y + box.height * 0.5;
    await p.mouse.move(cx, cy); await p.mouse.down();
    for (let i = 1; i <= 10; i++) { await p.mouse.move(cx + i * 20, cy); await sleep(16); }
    await p.mouse.up();
    await sleep(200);
    const f1 = await vr();
    await p.waitForFunction(done, null, { timeout: 30000 });
    await sleep(1500);
    const f2 = await vr();
    const moved = Math.abs(f1 - f0) > 5, kept = Math.abs(f2 - f1) < 1;
    const ok = moved && kept;
    pass += ok ? 1 : 0;
    console.log(`  ${ok ? '✓' : '✗'} ${name}：拖之前 ${f0.toFixed(2)} → 拖完 ${f1.toFixed(2)} → 数据回来以后 ${f2.toFixed(2)}`
                + (ok ? '' : moved ? `　★ 被摆回去了（离拖完差 ${Math.abs(f2 - f1).toFixed(2)} 根）` : '　★ 没拖动，这一格空转'));
    await ctx.close();
  }
  await b.close();
  console.log(`${pass}/${CASES.length} 过`);
  process.exit(pass === CASES.length ? 0 : 1);
})().catch((e) => { console.error('✗ 跑不起来：', e.message); process.exit(2); });
