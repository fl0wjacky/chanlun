// 「往左拖自动加载更早 K 线」的浏览器工装（card-d38154a0-e2d，2026-10-04）
//
// ★ 它**不是**六把尺里的一把：尺子是纯函数、秒级、谁都能跑；这一套要 playwright ＋ 真浏览器 ＋
//   一个静态服务，慢得多也脆得多。放在仓里是为了**别人能复跑**（Atlas 2026-10-04 提的）。
//
// 它管的是**尺 ⑥ 管不到的那半边**：接线。尺子把 `web/app.js` 的 `EARLIER_PAGING` 段抠出来单跑，
// 量纯函数（不跳 / 触发线 / 两句话 / 体检）；这里量「真拖一下之后浏览器里到底发生了什么」：
//   ① 打开页面**不许**自动去要下一档（?at 摆出来那一下的回声不能被当成用户拖）
//   ② 真按住往左拖 → 发出 span=2 的请求、**一次只飞一个**
//   ③ 数据换掉之后，同一根 K 线**在屏幕上同一个像素**（timeToCoordinate，不是拿算式推的）
//   ④ 加载中那句话真的出现；4 档也照样落在同一个像素上
//   ⑤ 到最早 ⇒ 印「已到最早」、不再发请求
//   ⑥ 后台回一份对不上的 ⇒ 图**一点都不许变**、提示说取不到、档位没被改坏
//   ⑦ ?load=4 打开就是 4 档、不印提示
//   ⑧ 到封顶（span_max=4 而币安还有更早的）⇒ 印「已到本周期可加载的最早」，**不再发请求**
//   ⑨ 地址栏写坏了（?load=32 / 64 / abc）⇒ 发出去之前先夹进白名单那五个值，首屏不许整张挂
//
// 假后台：拿仓里 zec_1h.json 的真 bars/结构当 1 档，往前补 n 段**编出来的**老 K 线（时间戳按样本
// 自己的步长往前推，价格贴着数据头），结构整体**平移**到新的下标上。★ 这么造的意思是：两档之间
// **结构故意不动** ——「结构跳不跳」是 Bram 那半边的账，只有真接口才量得了（Atlas 2026-10-04 讲过），
// 这里只量「位置跳不跳」和接线。编出来的那几根不是行情，别拿左边的图当行情看。
//
// 跑法（三样都要）：
//   1) 静态服务，**只绑回环**（部署纪律：不许绑全网卡）：
//        python3 -m http.server 8791 --bind 127.0.0.1 --directory web
//   2) playwright：`npm i playwright && npx playwright install chromium`（各机器一次）
//      node_modules 不在仓里 —— 在任何装好 playwright 的目录下跑，用 NODE_PATH 指过来即可。
//   3) node tools/web_more_e2e.js [输出目录] [页面地址]
//        输出目录默认 $TMPDIR/more-e2e（截图落这儿；不写进仓）
//        页面地址默认 http://127.0.0.1:8791/（服务换个端口就改这个）
const fs = require('fs');
const os = require('os');
const path = require('path');
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch (e) {
  console.error('✗ 没装 playwright。先 `npm i playwright && npx playwright install chromium`，' +
                '再用 NODE_PATH=<那个 node_modules> 跑这个文件。');
  process.exit(2);
}

const WEB = path.join(__dirname, '..', 'web');           // 仓相对：工装跟着仓走，不写死谁的家目录
const OUT = process.argv[2] || path.join(os.tmpdir(), 'more-e2e');
const PAGE = (process.argv[3] || 'http://127.0.0.1:8791/').replace(/\/?$/, '/');
const FULL = JSON.parse(fs.readFileSync(path.join(WEB, 'fixtures/zec_1h.json'), 'utf8'));
const STEP = FULL.bars[1].t - FULL.bars[0].t;
const PER = 2016;                    // 一档 ≈ 现在线上那 210 天（1h 档折成根数，比例不变）

let requests = [], inflight = 0, maxInflight = 0;
const PAGENAMES = new Map();          // 哪一页发的请求（多页同时开着，出问题时要能点名）
let delay = 0, earliestFlag = false, badNext = false, spanMax = 8;

function payload(span) {
  const extra = (span - 1) * PER, head = FULL.bars[0], older = [];
  // ★ 编出来的老 K 线**不许等距重复**：早先每根都是头一根的复制，图上就是一条等宽的红板子 ——
  //   那种地方「整屏平移一格」跟「没动」画出来一模一样，逐像素比也看不出来（假绿）。
  //   现在每根按序号有个确定的微小摆动：价格贴着数据头（接得上、不跳空），但**没有周期性**，
  //   错开一格看得出差别。这一处只动价格，时间戳照旧严格等距。
  for (let i = extra; i >= 1; i--) {
    const w = Math.sin(i / 7.3) * 0.0022 + Math.sin(i / 31.7) * 0.0011;
    const c = head.c * (1 + w), o = head.o * (1 + w * 0.93);
    older.push({ t: head.t - i * STEP, o, h: Math.max(o, c) * 1.0009, l: Math.min(o, c) * 0.9991, c });
  }
  const bars = older.concat(FULL.bars);
  const shift = (a) => (a || []).map((o) => Object.assign({}, o, { i0: o.i0 + extra, i1: o.i1 + extra }));
  const barsOf = (a) => (a || []).map((o) => Object.assign({}, o, { bar: o.bar + extra }));
  const d = Object.assign({}, FULL, {
    bars, nbars: bars.length, span, span_max: spanMax, earliest: !!earliestFlag,
    pens: shift(FULL.pens), segs: shift(FULL.segs) });
  if (FULL.signals) d.signals = { seg: barsOf(FULL.signals.seg), pen: barsOf(FULL.signals.pen) };
  // ⑥ 故意回一份**对不上**的：结构下标还留在老位置上（真实世界里＝后台切了 bars 却没重算结构）
  if (badNext) { badNext = false; d.pens = FULL.pens.map((o) => Object.assign({}, o, { i0: o.i0 + 90000, i1: o.i1 + 90000 })); }
  return d;
}

async function serve(ctx) {
  await ctx.route('**/api/chart*', async (route) => {
    const u = new URL(route.request().url());
    const span = Number(u.searchParams.get('span') || 1);
    requests.push(span);
    let who = '?';
    try { who = PAGENAMES.get(route.request().frame().page()) || '?'; } catch (e) { who = '已关'; }
    console.log('      · 后台收到 span=' + span + ' 来自第 ' + who + ' 号页');
    inflight++; maxInflight = Math.max(maxInflight, inflight);
    try {
      if (delay) await new Promise((r) => setTimeout(r, delay));
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload(span)) });
    } finally { inflight--; }
  });
  await ctx.route('**/fixtures/**', (r) => r.fulfill({ status: 404, body: '' }));   // 逼它只能走后台那条路
}

// 按**时间**问图：「这根 K 线现在在屏幕哪个 x」。★ 同一个时间戳前后各问一次，
// 两次一样就是「同一根 K 线钉在同一个像素」——这才是「画面不跳」，跟「左沿那根」那种按下标挑的不是一回事。
const xAt = (p, t) => p.evaluate((t) => window.__app.chart.timeScale().timeToCoordinate(t / 1000), t);
const snap = (p) => p.evaluate(() => {
  const { chart, state, paging } = window.__app;
  const r = chart.timeScale().getVisibleLogicalRange();
  const bars = state.data.bars;
  const i = Math.max(0, Math.ceil(r.from));
  const t = bars[i].t;
  const m = document.getElementById('more'), bb = m.getBoundingClientRect();
  return { from: +r.from.toFixed(4), to: +r.to.toFixed(4), n: bars.length, anchor: t,
           x: chart.timeScale().timeToCoordinate(t / 1000),
           more: m.textContent,
           // 提示「在不在」跟「写没写」是两件事：话说完 2.6 秒会自己收掉（.on 拿掉 ⇒ visibility:hidden），
           // 但 textContent 还留着。只读字串会以为「还挂在图上」——截图那几格就是被这一条骗的。
           moreOn: m.classList.contains('on'), moreVis: getComputedStyle(m).visibility,
           moreBox: [Math.round(bb.width), Math.round(bb.height)],
           span: paging.span, url: location.search };
});

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3 });
  await serve(ctx);
  const p = await ctx.newPage(); PAGENAMES.set(p, '1');
  const ok = [], bad = [];
  const t = (name, cond, extra = '') => {
    const line = `${name}${extra ? '：' + extra : ''}`;
    (cond ? ok : bad).push(line);
    console.log((cond ? '  ✓ ' : '  ✗ ') + line);          // 边跑边印：中途炸了也知道跑到哪
  };
  // ★ 截图必须**指定是哪一页**：工装同时开着好几页，写死第一页就会拿另一页的「没有这句提示」当失败
  //   （⑧ 那格就是这么假红过一次：提示明明在 4 号页上亮着）。
  const shot = async (sel, file, page = p) => {
    if (await page.locator(sel).isVisible()) await page.locator(sel).screenshot({ path: `${OUT}/${file}` });
    else bad.push(`截图 ${file}：${sel} 没显示出来（这一页是空的 —— 是不是截错了页？）`);
  };

  try {
    // ?at/&span 是既有的**视口**参数（跟数据档 ?load 不是一回事）：先把视口摆到左沿附近，
    // 再让**真鼠标**把最后那 20 根拖出来。
    delay = 400;                       // ★ 首次响应故意慢一点：图刚建出来是 0 宽，那时候设视口会被随后的
                                       //   布局重排吃掉（真后台本来也没这么快）—— 这是工装的事，不是页面的
    await p.goto(PAGE + '?symbol=ZECUSDT&tf=1h&at=40&span=180', { waitUntil: 'load' });
    await p.waitForFunction(() => window.__app && window.__app.state.data);
    await p.waitForTimeout(900);
    delay = 0;
    const a = await snap(p);
    t('① 打开页面不自动要下一档（开在左沿也不许）', requests.length === 1 && requests[0] === 1,
      `请求 ${JSON.stringify(requests)}，视口 from=${a.from}`);

    // ② 真按住往左拖（把更老的 K 线拖出来）。★ 这一档的响应故意慢：要在**请求在飞**的时候抓一张「换之前」，
    //    不然「换数据前后」四个字就没有基准可对（响应一瞬就回来了，抓到的是换完之后的第二张）。
    delay = 2500;                                       // ★ 慢到「拖完了、数据还在路上」，才量得到「换数据那一刻放不跳」
    const nReq0 = requests.length;
    const box = await p.locator('#chart').boundingBox();
    const cy = box.y + box.height / 2;
    await p.mouse.move(box.x + 40, cy);
    await p.mouse.down();
    for (let i = 0; i < 12; i++) await p.mouse.move(box.x + 40 + i * 20, cy, { steps: 2 });
    await p.mouse.up();
    await p.waitForTimeout(200);
    const before3 = await snap(p);                      // 手离开鼠标之后、数据还没回来的那一屏（还是 1 档）
    const T3 = before3.anchor, x3 = await xAt(p, T3);   // 挑一根（按时间挑），记下它在屏幕上的像素
    t('③ 量之前先确认数据确实还在路上（不然这一格是空转）', before3.more === '加载更早数据…',
      `提示 ${JSON.stringify(before3.more)}`);
    await p.waitForTimeout(3000);                       // 拖出来那一下发的请求已经回来了
    delay = 0;
    t('② 真拖一下（用户动作）确实要了下一档（且只要了一次）',
      requests.length === nReq0 + 1 && requests.at(-1) === 2,
      `请求 ${JSON.stringify(requests)}，拖后 from=${before3.from}`);

    // ③ 换数据前后：**同一根 K 线的屏幕像素**必须一样（这才是「画面不跳」）。
    //    ★ 量的口径：拿**同一个时间戳**去问两次图（timeToCoordinate），不是「左沿那根」——
    //      「左沿那根」是按下标挑的，换完数据下标就换了一根，拿它比是拿两根不同的 K 线在对账。
    const after2 = await snap(p);
    const x3b = await xAt(p, T3);
    t('③ 换档后根数确实变多了', after2.n > before3.n, `${before3.n} → ${after2.n}`);
    // 容差 0.01px：真跳一下至少是一根 K 线的宽度（这个缩放下 ≈1.8px），0.01 卡得住；
    // 浮点噪声（实测 4e-13）不算跳。
    t('③ 同一根 K 线的屏幕 x 没动', x3 !== null && x3b !== null && Math.abs(x3b - x3) < 0.01,
      `t=${T3}：x ${x3} → ${x3b}（Δ${x3b === null ? '?' : (x3b - x3).toExponential(1)}px）`);
    t('③ 一次只飞一个请求', maxInflight === 1, `最大并发 ${maxInflight}`);
    t('③ 地址栏写上了 load=2', /(^|[?&])load=2(&|$)/.test(after2.url), after2.url);

    // ④ 加载中那句话（把延迟拉长，看得见）
    delay = 900;
    await p.evaluate(() => { const c = window.__app.chart; const r = c.timeScale().getVisibleLogicalRange();
                             c.timeScale().setVisibleLogicalRange({ from: 3, to: r.to - r.from + 3 }); });
    await p.waitForTimeout(250);
    const loading = await snap(p);
    const T4 = loading.anchor, x4 = await xAt(p, T4);   // 同样：按**时间**挑一根当基准
    t('④ 加载中印「加载更早数据…」', loading.more === '加载更早数据…', `实际 ${JSON.stringify(loading.more)}`);
    await shot('#more', 'more_loading.png');
    await p.locator('#chart').screenshot({ path: `${OUT}/more_s2_loading.png` });   // 证据图：换档**前**这一屏
    await p.waitForTimeout(1200);
    delay = 0;
    const after4 = await snap(p);
    await p.locator('#chart').screenshot({ path: `${OUT}/more_s3_after.png` });     // 证据图：换档**后**同一屏
    t('④ 4 档也落地了', after4.n > after2.n, `${after2.n} → ${after4.n}`);
    // ★ 这一档（2→4）跟 ③ 那一档（1→2）走的是同一条路，量的是同一个映射：
    //   不看画面像不像，而是问图「这根 K 线在哪个像素」（编出来的老 K 线不做周期性摆动的话，
    //   整屏平移一格画出来也一模一样 —— 那是假绿，所以 payload 里那处摆动不是装饰）。
    const x4b = await xAt(p, T4);
    t('④ 4 档：同一根 K 线还在同一个像素上', x4 !== null && x4b !== null && Math.abs(x4b - x4) < 0.01,
      `t=${T4}：x ${x4} → ${x4b}（Δ${x4b === null ? '?' : (x4b - x4).toExponential(1)}px）`);
    t('④ load=4 写进地址栏', /(^|[?&])load=4(&|$)/.test(after4.url), after4.url);

    // ⑤ 到最早：后台说 earliest，再拖一次
    earliestFlag = true;
    await p.evaluate(() => { const c = window.__app.chart; const r = c.timeScale().getVisibleLogicalRange();
                             c.timeScale().setVisibleLogicalRange({ from: 2, to: r.to - r.from + 2 }); });
    await p.waitForTimeout(800);
    const end = await snap(p);
    t('⑤ 到头印「已到最早」', end.more === '已到最早', `实际 ${JSON.stringify(end.more)}`);
    await shot('#more', 'more_earliest.png');
    const nReq = requests.length;
    await p.evaluate(() => { const c = window.__app.chart; const r = c.timeScale().getVisibleLogicalRange();
                             c.timeScale().setVisibleLogicalRange({ from: 1, to: r.to - r.from + 1 }); });
    await p.waitForTimeout(400);
    t('⑤ 到最早之后不再发请求（不打转）', requests.length === nReq, `${nReq} → ${requests.length}`);
    await p.locator('#chart').screenshot({ path: `${OUT}/more_chart.png` });

    // ⑥ 后台回一份对不上的（结构下标越界）⇒ 图**一点都不许变**，而且老实说取不到。
    //    ★ 单开一页：上一段已经把 earliest 置真了，那种状态下页面**本来就不该再要数据**（⑤ 验过了），
    //      留在同一页上量到的会是「不打转」，量不到「回来的那份被judge掉了」这条。
    //    ★ 量法：先自己把视口挪到左沿（挪完先记一笔），再等那一份回来 —— 回来之后视口必须**还停在我挪到的地方**。
    //    ★ 先把这个假后台的开关**摆回干净状态**：不摆回，⑤ 留下的 earliest 会被这一页正经地认下来
    //      （那正是 adopt() 的职责），页面连请求都不会发，量到的就不是「判掉了」而是「压根没试」。
    earliestFlag = false; spanMax = 8;
    const p3 = await ctx.newPage(); PAGENAMES.set(p3, '3');
    await p3.goto(PAGE + '?symbol=ZECUSDT&tf=1h&load=4', { waitUntil: 'load' });
    await p3.waitForFunction(() => window.__app && window.__app.state.data);
    await p3.waitForTimeout(500);
    const beforeBad = await snap(p3);
    delay = 1200; badNext = true;                       // 下一份（span=8 那份）故意回一份对不上的
    await p3.evaluate(() => { const c = window.__app.chart; const r = c.timeScale().getVisibleLogicalRange();
                              c.timeScale().setVisibleLogicalRange({ from: 5, to: r.to - r.from + 5 }); });
    await p3.waitForTimeout(700);                       // 请求还在飞；我摆的那个视口早落定了
    const inFlight = await snap(p3);
    await p3.waitForTimeout(1200);                      // 回来了（而且是被判掉的那一份）
    const afterBad = await snap(p3);
    delay = 0;
    t('⑥ 那一下确实发过请求（不是压根没试）', inFlight.more === '加载更早数据…' && requests.at(-1) === 8,
      `提示 ${JSON.stringify(inFlight.more)}，最后一次请求 span=${requests.at(-1)}`);
    t('⑥ 对不上的数据：一根都不换', afterBad.n === beforeBad.n, `${beforeBad.n} → ${afterBad.n}`);
    // 视口这条要拿**我自己挪到的地方**当基准（挪完、还没回来那一笔）：拿「挪之前」比就是拿我自己的动作当差。
    // ★ 只比「回来前后一不一样」，不钉它必须等于 5：LWC 会把摆进去的值自己归一化一手（这是库的事，不是页面的事）。
    //   真要是把那份数据画上去了，place() 会按时间把它摆到一个**离得很远**的位置（约 2000 根开外）—— 这一比就露。
    t('⑥ 对不上的数据：视口也没动', inFlight.from < 20 && afterBad.from === inFlight.from,
      `我挪到左沿 from=${inFlight.from}，回来后 ${afterBad.from}`);
    t('⑥ 对不上的数据：老实说取不到', afterBad.more === '更早的数据没取到', `实际 ${JSON.stringify(afterBad.more)}`);
    t('⑥ 档位没被改坏（还是 4 档）', afterBad.span === 4, `span=${afterBad.span}`);
    await p3.close();

    // ⑦ ?load=4 打开直接是 4 档
    const p2 = await ctx.newPage(); PAGENAMES.set(p2, '2');
    const base = requests.length;
    await p2.goto(PAGE + '?symbol=ZECUSDT&tf=1h&load=4&tag=p2', { waitUntil: 'load' });
    await p2.waitForFunction(() => window.__app && window.__app.state.data);
    await p2.waitForTimeout(400);
    const s4 = await p2.evaluate(() => ({ n: window.__app.state.data.bars.length, span: window.__app.paging.span,
                                          more: document.getElementById('more').textContent }));
    t('⑦ ?load=4 打开就是 4 档', requests.slice(base)[0] === 4 && s4.span === 4,
      `请求 ${JSON.stringify(requests.slice(base))}，paging.span=${s4.span}`);
    t('⑦ 4 档打开时不印任何提示', s4.more === '', JSON.stringify(s4.more));
    await p2.close();

    // ⑧ 封顶那一档（后台说 span_max=4，币安其实还有更早的）：到头了要说「已到本周期可加载的最早」，
    //    而且**不许**再发请求。★ 这一格是尺 ⑥ 量不到的那半边：尺子只判该印哪句话，这里看它真印出来没有。
    //    ★ 这一格正是首屏不认回显那个 bug 的现场：不认 span_max 就会再发一次 span=8（页面上白发一趟）。
    spanMax = 4; earliestFlag = false;                  // 4 档就是这个周期的顶（而且后台没说「到头」）
    const p4 = await ctx.newPage(); PAGENAMES.set(p4, '4');
    await p4.goto(PAGE + '?symbol=ZECUSDT&tf=1h&load=4&tag=p4', { waitUntil: 'load' });
    await p4.waitForFunction(() => window.__app && window.__app.state.data);
    await p4.waitForTimeout(400);
    // ★ 基准必须在**首屏那一发落地之后**取：这一页自己也有一发（load=4），拿它当「多出来的」就是冤枉。
    const base8 = requests.length;
    await p4.evaluate(() => { const c = window.__app.chart; const r = c.timeScale().getVisibleLogicalRange();
                              c.timeScale().setVisibleLogicalRange({ from: 2, to: r.to - r.from + 2 }); });
    await p4.waitForTimeout(500);
    const cap = await snap(p4);
    t('⑧ 到封顶印的是「已到本周期可加载的最早」（不是「已到最早」）',
      cap.more === '已到本周期可加载的最早' && cap.moreOn, `实际 ${JSON.stringify(cap.more)} on=${cap.moreOn}`);
    t('⑧ 到封顶之后不再发请求', requests.length === base8, `${base8} → ${requests.length}`);
    await shot('#more', 'more_cap.png', p4);
    await p4.close();

    // ⑨ 地址栏写坏了：**发出去之前**必须先夹进契约里那五个值（Nova 2026-10-04 定）。
    //    不夹的话 ?load=32/64 会被后台按契约回 400，首屏整张挂掉；?load=abc 会 NaN 出去。
    //    ★ 这一格是尺 ⑥ 的 ladderSpan 那几格在真页面上的回声：尺子量算式，这里量「地址栏进去到底发了什么」。
    for (const [raw, want] of [['32', 16], ['64', 16], ['abc', 1]]) {
      const q = await ctx.newPage(); PAGENAMES.set(q, '9');
      const b9 = requests.length;
      await q.goto(PAGE + `?symbol=ZECUSDT&tf=1h&load=${raw}&tag=bad-${raw}`, { waitUntil: 'load' });
      await q.waitForFunction(() => window.__app && window.__app.state.data);
      await q.waitForTimeout(300);
      const st = await q.evaluate(() => ({ span: window.__app.paging.span,
                                           n: window.__app.state.data.bars.length,
                                           err: document.getElementById('chart').children.length }));
      t(`⑨ ?load=${raw} 发出去的是 ${want}（夹进白名单）`,
        requests.slice(b9).length === 1 && requests.slice(b9)[0] === want && st.span === want,
        `请求 ${JSON.stringify(requests.slice(b9))}，paging.span=${st.span}`);
      t(`⑨ ?load=${raw} 首屏画出来了（没整张挂）`, st.n > 1, `bars=${st.n}`);
      await q.close();
    }
    spanMax = 8;
    // ⑩ 首屏就撞上「币安真没了」（AAPL 那种一档就到底的）：**一个多余请求都不许发**，
    //    打开就是一句话「已到最早」。Nova 的契约里点名的那条 —— 首屏不认回显就会白发一趟。
    earliestFlag = true; spanMax = 16;
    const p5 = await ctx.newPage(); PAGENAMES.set(p5, '10');
    const baseA = requests.length;
    await p5.goto(PAGE + '?symbol=ZECUSDT&tf=1h&load=4&tag=aap', { waitUntil: 'load' });
    await p5.waitForFunction(() => window.__app && window.__app.state.data);
    await p5.waitForTimeout(600);
    const aa = await p5.evaluate(() => ({ span: window.__app.paging.span,
                                          more: document.getElementById('more').textContent }));
    t('⑩ 首屏就拿到 earliest ⇒ 只发一次请求（不白发一趟）',
      requests.slice(baseA).length === 1 && requests.slice(baseA)[0] === 4,
      `请求 ${JSON.stringify(requests.slice(baseA))}`);
    // 首屏是 fitContent（整段铺满），那句话是**回答拖**的，开着不动不印也说得过去；
    // 所以这里真把它拖到左沿，量「贴到最左沿也不发请求、并老实说已到最早」。
    await p5.evaluate(() => { const c = window.__app.chart; const r = c.timeScale().getVisibleLogicalRange();
                              c.timeScale().setVisibleLogicalRange({ from: 1, to: r.to - r.from + 1 }); });
    await p5.waitForTimeout(500);
    const aa2 = await snap(p5);
    t('⑩ 贴到最左沿：印「已到最早」', aa2.more === '已到最早' && aa2.moreOn,
      `实际 ${JSON.stringify(aa2.more)} on=${aa2.moreOn}（首屏 span=${aa.span}）`);
    t('⑩ 贴到最左沿：一个额外请求都没有', requests.slice(baseA).length === 1,
      `请求 ${JSON.stringify(requests.slice(baseA))}`);
    await p5.close();
    earliestFlag = false;
    spanMax = 8;
  } catch (e) {
    bad.push('工装半路炸了：' + String(e.message || e).split('\n')[0]);
  }
  await b.close();
  console.log('请求序列：', JSON.stringify(requests));
  console.log('截图落在：', OUT);
  if (bad.length) {
    console.log(`\n${bad.length} 处不对：`);
    for (const x of bad) console.log('  ✗ ' + x);
  } else {
    console.log(`\n全部 ${ok.length} 条都对`);
  }
  process.exit(bad.length ? 1 : 0);
})();
