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
//   ⑩ 首屏就拿到 earliest ⇒ 只发一次请求，贴到左沿也不再多发
//   ⑪ **反着的一格**（脚本把视口摆到贴左沿＝那次回声）⇒ 一个请求都不许发（就是上一轮那个 bug 本身）
//   ⑫ 换数据那一刻的等值件都在（档位/条数/地址栏）
//   ⑬ 换档那句话：**只在可视窗口里的结构真变了**才印，3 秒自收。三格各自单开一页：
//      窗口外变⇒不印 ／ 窗口里笔段变⇒印 ／ **只有中枢变⇒也印**（Nova 2026-10-04 补的第三格）
//   ⑭ **鼠标只在图上悬停、一个键都不按** ⇒ 一个请求都不许发（Atlas 2026-10-04 多跑逮到的那格）
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
//   3) node tools/web_more_e2e.js [输出目录] [页面地址] [--throttle=N]
//        输出目录默认 $TMPDIR/more-e2e（截图落这儿；不写进仓）
//        页面地址默认 http://127.0.0.1:8791/（服务换个端口就改这个）
//        --throttle=N：把这一页的 CPU 拖慢 N 倍（CDP Emulation.setCPUThrottlingRate，默认 1＝不降速）。
//          ★ 什么时候该用它：这套里有一格量的是**时序竞争**（「打开页面没人拖，它自己会不会去要下一档」）。
//            竞争这种事**证不了不存在** —— 快机器上连跑 10 次全绿，说明的只是这台机器快。
//            所以验它的办法是**故意输**：把 CPU 拖慢（4～6 倍就够），让那个窗口真被错过。
//            规矩照旧：**改之前红、改之后绿**，才算这一格被验过（Atlas 2026-10-04 提的）。
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
// --throttle=4：把这一页的 CPU 拖慢 4 倍（CDP）。默认 1＝不降速。
// 为什么要有：这条工装里有一格量的是**时序竞争**（没人拖的时候会不会自己发请求）。
// 竞争**证不了不存在**——快机器上 10/10 绿什么都不说明。要验它，就得能故意把机器拖慢。
const THROTTLE = Number((process.argv.find((a) => a.startsWith('--throttle=')) || '').split('=')[1]) || 1;
const FULL = JSON.parse(fs.readFileSync(path.join(WEB, 'fixtures/zec_1h.json'), 'utf8'));
const STEP = FULL.bars[1].t - FULL.bars[0].t;
const PER = 2016;                    // 一档 ≈ 现在线上那 210 天（1h 档折成根数，比例不变）

// 换档那句话的**契约原文**（Nova 2026-10-04 定 (a)：中枢和买卖点也算 ⇒ 文案改成泛指）。
// 工装里两处断言都引这一个常量 —— 抄两份的话，改文案时改一处漏一处，红的是「另一处」。
const NOTICE_COPY = '已接上更早的K线，左侧的笔、线段、中枢和买卖点按新的起点重算';

const T0 = Date.now();               // 日志带相对时刻：时序那一族光看「收到 span=2」看不出早晚
let requests = [], inflight = 0, maxInflight = 0;
// ★★ 每份响应**是按哪个模式供出去的**，逐份记下来（⑬ 三格要用它证明「场景是干净的」）。
//   踩过的坑（m4 变异逮到的）：⑬ 第三格 `mk13` 建页时，上一格留下的 `winmode='in'` 还没清，
//   于是这一页的**首屏那份**也被人动过 ⇒ 换档后拿「被动的首屏」比「只在中枢上动的第二份」，
//   笔和线段自己就变了 —— 那句话是被**笔线段**点着的，跟中枢一格关系没有：
//   「不记中枢」的变异因此照样绿（假绿），量到的是空转。所以：**首屏那份必须一个模式都没带**。
let servedLog = [];
let bumped = 0;                       // ⑬ 第三格：后台真动过几个窗口内的中枢框（0 ⇒ 这一格是空转）
const PAGENAMES = new Map();          // 哪一页发的请求（多页同时开着，出问题时要能点名）
const servedFirst = new Set();        // 哪个页名已经供过第一份了（场景对账只在第一份上做）
// ★★★ 场景开关**只有这一份**（Atlas 2026-10-04）：原先它们是一堆平铺的 `let`，每格自己清自己那份，
//   于是「上一格留下的开关漏到下一格」这种事，只会在被它污染的那一格的**结论**里显形
//   （⑬ 第三格就是这么变成假绿的：上一格的 winmode 没清，这一页首屏那份数据也被动过）。
//   ⇒ 改成：所有开关放进 SCEN，**每格开页之前调一次 `scen({...})`**（先回默认，再盖这一格要的），
//     并且把「开页那一刻声明要的场景」记下来，跟后台**实际用的那份**逐字对 —— 对不上就红。
//   新增开关请加进 DEFAULT_SCEN，别在外面另起 `let`：漏进去的那一个，这条自检也看不见。
const DEFAULT_SCEN = { winmode: null, pageWin: null, earliestFlag: false, badNext: false, spanMax: 8, delay: 0 };
const SCEN = Object.assign({}, DEFAULT_SCEN);
const scenKeys = Object.keys(DEFAULT_SCEN).sort();
const scenSnap = () => scenKeys.map((k) => k + '=' + JSON.stringify(SCEN[k] === null ? null : SCEN[k])).join(',');
const declared = new Map();        // 页名 ⇒ 开页那一刻声明的场景（跟后台实际用的那份对）
const scenBad = [];                // 对不上的（跑完统一报红）
let lastOpenVer = 0;               // 上一次开页时的 scenVer（查「这一页之前声明过没有」）
let scenVer = 0;              // 每调一次 scen() 加一：开页时对一下，就知这一页是不是「声明过场景」的
const scen = (o) => { Object.assign(SCEN, DEFAULT_SCEN, o || {}); holdRelease = null; scenVer++; return scenSnap(); };
// ★★ 「响应扣在后台、由工装决定什么时候放行」（2026-10-04 改）。
//   原来靠 delay 跟拖拽赛跑：delay 是**时钟**，拖一下要多久是**机器快慢**决定的 ——
//   降速 4 倍时，一次拖拽能比 900ms 还长，等拖完再去看提示，那一趟早就落地了（实测「加载更早数据…」
//   只在 592ms~710ms 之间活过 118ms，全在拖拽过程里，工装根本没看到）。
//   那不是页面的错，是工装拿时钟当同步器。改成：非 null 时**请求先扣住**，工装说放才放 ——
//   「数据还在路上」从「多半还在」变成「一定还在」，任何倍率下都成立。
// ⑬ 换档那句话：假后台得把「整份重算」演出来。真实后台换档就是从头再算一遍，两边（窗口内/窗口外）都会动；
//    这里偏偏分开动 —— 只有分开，「按可视窗口判」这句话才有东西能证伪：
//    两边一起动的话，页面不管拿哪儿当判据都会出提示，'out' 那格就永远是绿的（量不到东西）。
//   SCEN.winmode：'in'＝只动跟可视窗口重叠的结构 ／ 'out'＝只动窗口外的
let holdRelease = null;
const holdNext = () => { let open; holdRelease = new Promise((r) => { open = r; });
                         return () => { const h = holdRelease; holdRelease = null; if (h) open(); }; };

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
    bars, nbars: bars.length, span, span_max: SCEN.spanMax, earliest: !!SCEN.earliestFlag,
    pens: shift(FULL.pens), segs: shift(FULL.segs) });
  if (FULL.signals) d.signals = { seg: barsOf(FULL.signals.seg), pen: barsOf(FULL.signals.pen) };
  // ⑬ 换档重算的替身：跟可视窗口**重叠**的（'in'）或**只在窗口外**的（'out'）结构动一下。
  //    判据跟页面 structKey 里那条一模一样（有时间重叠），不许各写各的 ——
  //    两边口径一旦错开，「窗口外变了」这个场景就摆不出来（会被页面按「窗口里也变了」判）。
  //   'in'     ＝ 跟窗口重叠的**笔和线段**动一下（'out' ＝ 只在窗口外的那些动）
  //   'in-cen' ＝ **只有窗口里的中枢**动一下，笔/线段/买卖点一个不碰
  //              （Nova 2026-10-04 要的那一格：屏幕上看得见的东西变了就该出声，
  //               而换档后先变的往往正是中枢 —— BTC 4h 1↔2 就是只有线段中枢的 ZD 变了）
  if (SCEN.pageWin && SCEN.winmode) {
    const ts = (i) => (d.bars[i] || {}).t;
    const overlap = (o) => ts(o.i0) != null && ts(o.i1) != null && ts(o.i1) >= SCEN.pageWin.t0 && ts(o.i0) <= SCEN.pageWin.t1;
    const tweak = (o) => Object.assign({}, o, { p0: o.p0 * 1.002, p1: o.p1 * 1.002 });
    if (SCEN.winmode === 'in-cen') {
      //   中枢的横跨区按 host 取（跟页面 structKey、layers.js 的 boxes() 同一个取法：
      //   类中枢 host=笔、线段中枢 host=**已完成**线段）。只动 ZD 一个数：框的上下沿变了，别的一根不碰。
      const done = (d.segs || []).filter((s) => !s.live);
      const boxOv = (z, host) => { const a = host[z.PI0], b = host[z.PI1];
                                   return !!a && !!b && ts(a.i0) != null && ts(b.i1) != null
                                          && ts(b.i1) >= SCEN.pageWin.t0 && ts(a.i0) <= SCEN.pageWin.t1; };
      const bump = (z) => { bumped++; return Object.assign({}, z, { ZD: z.ZD * 1.01 }); };
      d.centers = (d.centers || []).map((z) => (boxOv(z, d.pens || []) ? bump(z) : z));
      d.seg_centers = (d.seg_centers || []).map((z) => (boxOv(z, done) ? bump(z) : z));
    } else {
      const pick = SCEN.winmode === 'in' ? overlap : (o) => !overlap(o);
      d.pens = (d.pens || []).map((o) => (pick(o) ? tweak(o) : o));
      d.segs = (d.segs || []).map((o) => (pick(o) ? tweak(o) : o));
    }
  }
  // ⑥ 故意回一份**对不上**的：结构下标还留在老位置上（真实世界里＝后台切了 bars 却没重算结构）
  if (SCEN.badNext) { SCEN.badNext = false; d.pens = FULL.pens.map((o) => Object.assign({}, o, { i0: o.i0 + 90000, i1: o.i1 + 90000 })); }
  return d;
}

async function serve(ctx) {
  await ctx.route('**/api/chart*', async (route) => {
    const u = new URL(route.request().url());
    const span = Number(u.searchParams.get('span') || 1);
    requests.push(span);
    let who = '?';
    try { who = PAGENAMES.get(route.request().frame().page()) || '?'; } catch (e) { who = '已关'; }
    // 每一份响应**按哪个场景供的**、以及**是哪一页的第一份**（对账用）。
    const snap = scenSnap(), first = !servedFirst.has(who);
    servedLog.push({ who, span, winmode: SCEN.winmode, snap, first });
    if (first) {
      servedFirst.add(who);
      const want = declared.get(who);
      if (want == null) scenBad.push(`${who}：这一页开页前没声明场景（漏调 scen()）`);
      else if (want !== snap) scenBad.push(`${who}：开页时声明的是 [${want}]，后台实际用的是 [${snap}]`);
    }
    // 带上到达时刻和当时的 delay：时序那一族出了问题，光看「收到了 span=2」看不出它是几秒前发的
    console.log('      · 后台收到 span=' + span + ' 来自第 ' + who + ' 号页（t=' + ((Date.now() - T0) / 1000).toFixed(2) + 's, delay=' + SCEN.delay + '）');
    inflight++; maxInflight = Math.max(maxInflight, inflight);
    try {
      if (SCEN.delay) await new Promise((r) => setTimeout(r, SCEN.delay));
      if (holdRelease) await holdRelease;                 // ★ 工装扣住的那一趟：等它说放行
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
  // ★ 降速（Atlas 2026-10-04）：这一套里有一条**时序**判据（「打开页面没人拖，它自己该不该去要下一档」），
  //   而时序竞争**证明不了不存在** —— 我这台机器快，跑 10 次全绿也说明不了它在慢机器上不出来。
  //   所以给它一个能**故意输**的开关：CDP 的 Emulation.setCPUThrottlingRate 把这一页的 CPU 拖慢
  //   （rate=4 就是 4 倍慢），比赛条件被放大。规矩还是那条：改之前红、改之后绿才算验过。
  //   CDP session 是**按页**的（新页要自己再开一次），所以这里包一个 openPage。
  const openPage = async (name) => {
    // ★ 规矩：**每一页开之前都得有一次 scen()**（哪怕是 `scen()` 空调用＝全默认）。
    //   漏了就是「拿上一格剩下的开关开这一页」—— ⑬ 第三格那个假绿就是这么来的。
    //   所以这里不只对快照，还查「这一页之前到底有没有人声明过」：没有 ⇒ 当场记账，跑完报红。
    if (scenVer === lastOpenVer) {
      scenBad.push(`${name}：开这一页之前没有声明场景（漏调 scen()）—— 上一格留下的开关就是这么漏进来的`);
    }
    lastOpenVer = scenVer;
    const q = await ctx.newPage();
    PAGENAMES.set(q, name);
    declared.set(name, scenSnap());      // 开页这一刻声明要的场景：后台第一份必须跟它逐字相同
    if (THROTTLE > 1) await (await ctx.newCDPSession(q)).send('Emulation.setCPUThrottlingRate', { rate: THROTTLE });
    return q;
  };
  // ★ 首次响应故意慢一点：图刚建出来是 0 宽，那时候设视口会被随后的**布局重排**吃掉
  //   （真后台本来也没这么快）—— 这是工装的事，不是页面的事。**在开页之前声明**，
  //   这样「开页时声明的那份」跟后台实际用的那份才是同一份（⑮ 就是拿这两份对账的）。
  scen({ delay: 400 });
  const p = await openPage('1');
  const ok = [], bad = [];
  const t = (name, cond, extra = '') => {
    const line = `${name}${extra ? '：' + extra : ''}`;
    (cond ? ok : bad).push(line);
    console.log((cond ? '  ✓ ' : '  ✗ ') + line);          // 边跑边印：中途炸了也知道跑到哪
  };
  // ★ 截图必须**指定是哪一页**：工装同时开着好几页，写死第一页就会拿另一页的「没有这句提示」当失败
  //   （⑧ 那格就是这么假红过一次：提示明明在 4 号页上亮着）。
  // ★ 盯着一句话**出现过**（驱动侧轮询，不是页面侧 rAF 轮询）。
  //   为什么要自己轮：`page.waitForFunction` 默认按页面里的 requestAnimationFrame 轮询，
  //   CPU 一降速，页面侧那一套就跟着慢/掉帧 —— 量的是页面被拖慢之后还能不能及时跑判据，
  //   而不是「那句话有没有出现过」。而且是**出现过**就算数：提示到点会自己收（loading 不会，
  //   但「已到最早」会），拿「轮到判据那一刻它还挂着」当条件，就是拿收尾时刻当判据。
  //   顺手把看到过的都记下来：红的时候能看出它到底说了什么、还是压根没说。
  const waitPill = async (page, want, ms = 10000) => {
    const seen = [], t0 = Date.now();
    for (;;) {
      const s = await page.evaluate(() => {
        const m = document.getElementById('more');
        const g = window.__app && window.__app.paging;
        return { txt: m.textContent, on: m.classList.contains('on'),
                 loading: !!(g && g.loading), span: g && g.span, applying: !!(g && g.applying),
                 n: window.__app && window.__app.state.data.bars.length };
      });
      seen.push(s.on || s.txt === want ? s.txt
                 : `[${s.txt}](收起了) loading=${s.loading} span=${s.span} applying=${s.applying} bars=${s.n}`);
      if (s.txt === want) return { hit: true, seen };
      if (Date.now() - t0 > ms) return { hit: false, seen };
      await page.waitForTimeout(60);
    }
  };
  // ★ 盯「换档那句话」（#notice）：跟 waitPill 同一个理由用驱动侧轮询，另外**把 ON/OFF 的时刻都记下来** ——
  //   契约里写了「停 3 秒」，那是这句话的一部分，不量时长就等于没量它。采样交给调用方决定停在哪里。
  const watchNotice = async (page, ms) => {
    const t0 = Date.now();
    let onAt = null, offAt = null, txt = '', seen = [];
    for (;;) {
      const s = await page.evaluate(() => { const n = document.getElementById('notice');
        return { on: n.classList.contains('on'), txt: n.textContent }; });
      const dt = Date.now() - t0;
      if (s.on) { if (onAt == null) { onAt = dt; txt = s.txt; } }
      else if (onAt != null && offAt == null) offAt = dt;
      seen.push((s.on ? 'ON' : 'off') + '@' + dt);
      if (offAt != null || dt > ms) return { hit: onAt != null, onAt, offAt, txt, seen };
      await page.waitForTimeout(50);
    }
  };
  const shot = async (sel, file, page = p) => {
    if (await page.locator(sel).isVisible()) await page.locator(sel).screenshot({ path: `${OUT}/${file}` });
    else bad.push(`截图 ${file}：${sel} 没显示出来（这一页是空的 —— 是不是截错了页？）`);
  };
  // ★★ 视口只许用**真鼠标**推（2026-10-04 改）：页面现在只认「用户真动过输入设备」
  //   （pointerdown/move、wheel、touch…），**脚本摆视口一律不算**（那是对的：脚本摆一下不等于有人要看）。
  //   所以工装里原来那几处 `evaluate(setVisibleLogicalRange)` 全部换成真拖 —— 工装得跟用户走同一条路，
  //   不然它量的是「页面会不会响应脚本」，而不是「用户拖到左沿会怎样」。
  //   往**右**拖 = 把更老的 K 线拖出来（跟 ② 那一下同一个方向）。
  const dragLeft = async (page, px) => {
    const box = await page.locator('#chart').boundingBox();
    const cy = box.y + box.height / 2;
    await page.mouse.move(box.x + 40, cy);
    await page.mouse.down();
    const steps = Math.max(2, Math.round(px / 20));
    for (let i = 1; i <= steps; i++) await page.mouse.move(box.x + 40 + (px * i) / steps, cy, { steps: 2 });
    await page.mouse.up();
    await page.waitForTimeout(80);          // 让 LWC 把视口事件吐完再读
  };
  // 「用户滚到最左边、又拖了一下」＝ **摆到位（脚本）＋ 真拖一下（鼠标）**，两步都要，理由不同：
  //   ① 摆到位：换档之后，**老的那个左沿在新数据里已经是几千根开外**（1→2 档就是 +2016 根），
  //      390px 的屏一下拖不了那么远，要拖几十下 —— 而这一步是**布置场景**（模拟「用户已经滚到最左」），
  //      不是用户动作。页面**本来就该忽略脚本摆视口**，那是它对的（⑪ 那格专门盯着这一点）。
  //   ② 真拖一下：**这才是用户动作**。页面现在只认真实输入事件，所以这一下必须真按鼠标 ——
  //      脚本摆完不拖，页面不发请求是对的（⑪ 就是据此判的），拿它当「该发请求」就是量错了东西。
  //   ★ 两条合起来才跟 766d053 那版工装的语义等价（那版只用 ①，而且**①本身就会误触发**，正是这次的 bug）。
  const pushLeft = async (page, from = 3, px = 110) => {
    await page.evaluate((from) => { const c = window.__app.chart; const r = c.timeScale().getVisibleLogicalRange();
                                    c.timeScale().setVisibleLogicalRange({ from, to: r.to - r.from + from }); },
                        from);
    await page.waitForTimeout(120);
    await dragLeft(page, px);
    return await snap(page);
  };

  try {
    // ?at/&span 是既有的**视口**参数（跟数据档 ?load 不是一回事）：先把视口摆到左沿附近，
    // 再让**真鼠标**把最后那 20 根拖出来。
    await p.goto(PAGE + '?symbol=ZECUSDT&tf=1h&at=40&span=180', { waitUntil: 'load' });
    await p.waitForFunction(() => window.__app && window.__app.state.data);
    await p.waitForTimeout(900);
    SCEN.delay = 0;
    const a = await snap(p);
    t('① 打开页面不自动要下一档（开在左沿也不许）', requests.length === 1 && requests[0] === 1,
      `请求 ${JSON.stringify(requests)}，视口 from=${a.from}`);

    // ② 真按住往左拖（把更老的 K 线拖出来）。★ 这一档的响应故意慢：要在**请求在飞**的时候抓一张「换之前」，
    //    不然「换数据前后」四个字就没有基准可对（响应一瞬就回来了，抓到的是换完之后的第二张）。
    //    ★ 「还在路上」现在由**后台那道闸**保证（holdNext），不再拿 delay 跟拖拽赛跑：
    //      拖一下要多久是机器快慢决定的，降速时能比 delay 还长 —— 那时候「换之前」那张早就是换完之后的第二张了。
    const rel3 = holdNext();                             // 这一趟的响应扣在后台，等这一格量完再放
    const nReq0 = requests.length;
    const box = await p.locator('#chart').boundingBox();
    const cy = box.y + box.height / 2;
    await p.mouse.move(box.x + 40, cy);
    await p.mouse.down();
    for (let i = 0; i < 12; i++) await p.mouse.move(box.x + 40 + i * 20, cy, { steps: 2 });
    await p.mouse.up();
    await p.waitForTimeout(200);
    const before3 = await snap(p);                      // 手离开鼠标之后、数据**一定**还没回来的那一屏（还是 1 档）
    const w3 = await waitPill(p, '加载更早数据…', 8000); // 「在飞」不只是内部状态，那句话也要真印出来
    const T3 = before3.anchor, x3 = await xAt(p, T3);   // 挑一根（按时间挑），记下它在屏幕上的像素
    t('③ 量之前先确认数据确实还在路上（不然这一格是空转）', w3.hit,
      `提示 ${JSON.stringify(before3.more)}`);
    rel3();                                             // 放行：这一趟该落地了
    // ★ 等**状态**，不等时钟：慢机器上（工装可以 --throttle 降速）3 秒不一定够，等不到就量成
    //   「一根没多」—— 那是工装的假红，不是页面的错。这一格原来就是靠睡 3 秒，降速一跑就红。
    await p.waitForFunction((n) => window.__app.state.data.bars.length > n, before3.n, { timeout: 20000 })
           .catch(() => {});
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

    // ④ 加载中那句话（响应同样扣在后台，看得见才放）
    const rel4 = holdNext();
    await pushLeft(p);                                   // 真鼠标再往左拖一下（脚本摆视口页面现在不认）
    const w4 = await waitPill(p, '加载更早数据…');       // 等那句「加载更早数据…」**出现过**
    const loading = await snap(p);
    const T4 = loading.anchor, x4 = await xAt(p, T4);   // 同样：按**时间**挑一根当基准
    t('④ 加载中印「加载更早数据…」', w4.hit,
      w4.hit ? '' : `看了一路（前4）：${JSON.stringify(w4.seen.slice(0, 4))} （后2）：${JSON.stringify(w4.seen.slice(-2))}`);
    await shot('#more', 'more_loading.png');
    await p.locator('#chart').screenshot({ path: `${OUT}/more_s2_loading.png` });   // 证据图：换档**前**这一屏
    rel4();
    await p.waitForFunction((n) => window.__app.state.data.bars.length > n, after2.n, { timeout: 20000 })
           .catch(() => {});
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
    SCEN.earliestFlag = true;
    // 顺手把 #more 的每一次变化记下来：红了要能看出它到底说过什么、几点说的（挂在页面上，不影响页面）
    await p.evaluate(() => { window.__log5 = []; const m = document.getElementById('more');
      window.__t5 = performance.now();
      new MutationObserver(() => window.__log5.push([Math.round(performance.now() - window.__t5),
        JSON.stringify(m.textContent), m.className]))
        .observe(m, { attributes: true, childList: true, subtree: true, characterData: true }); });
    const rel5 = holdNext();
    await pushLeft(p);                                   // 真拖一下：到最早之后**该不再发请求**（⑤ 后一条量这个）
    const w5a = await waitPill(p, '加载更早数据…', 8000);
    rel5();
    const w5 = await waitPill(p, '已到最早');            // 这句话说 2.6 秒自己收 —— 量「出现过」，不量「此刻还挂着」
    const hist5 = JSON.stringify(await p.evaluate(() => window.__log5.slice(0, 40)));
    const end = await snap(p);
    t('⑤ 到头印「已到最早」', w5.hit,
      w5.hit ? '' : `在飞时印的是 ${JSON.stringify(w5a.hit)}，变化史 ${hist5}，看了一路（前2）：${JSON.stringify(w5.seen.slice(0, 2))} （后2）：${JSON.stringify(w5.seen.slice(-2))}`);
    await shot('#more', 'more_earliest.png');
    const nReq = requests.length;
    await pushLeft(p);                                   // 再真拖一下（这一下**不许**再发请求）
    await p.waitForTimeout(400);
    t('⑤ 到最早之后不再发请求（不打转）', requests.length === nReq, `${nReq} → ${requests.length}`);
    await p.locator('#chart').screenshot({ path: `${OUT}/more_chart.png` });

    // ⑥ 后台回一份对不上的（结构下标越界）⇒ 图**一点都不许变**，而且老实说取不到。
    //    ★ 单开一页：上一段已经把 earliest 置真了，那种状态下页面**本来就不该再要数据**（⑤ 验过了），
    //      留在同一页上量到的会是「不打转」，量不到「回来的那份被judge掉了」这条。
    //    ★ 量法：先自己把视口挪到左沿（挪完先记一笔），再等那一份回来 —— 回来之后视口必须**还停在我挪到的地方**。
    //    ★ 先把这个假后台的开关**摆回干净状态**：不摆回，⑤ 留下的 earliest 会被这一页正经地认下来
    //      （那正是 adopt() 的职责），页面连请求都不会发，量到的就不是「判掉了」而是「压根没试」。
    scen();                                             // 开关回默认（含 earliest／span_max）
    const p3 = await openPage('3');
    await p3.goto(PAGE + '?symbol=ZECUSDT&tf=1h&load=4', { waitUntil: 'load' });
    await p3.waitForFunction(() => window.__app && window.__app.state.data);
    await p3.waitForTimeout(500);
    const beforeBad = await snap(p3);
    SCEN.delay = 1200; SCEN.badNext = true;             // 下一份（span=8 那份）故意回一份对不上的
    await pushLeft(p3);                                 // 真拖一下：请求在飞的时候抓「换之前」那一张
    const w6 = await waitPill(p3, '加载更早数据…');      // 等它真在路上（等「出现过」，不等时钟）
    const inFlight = await snap(p3);
    await p3.waitForFunction(() => window.__app.paging && !window.__app.paging.loading,
                             null, { timeout: 20000 }).catch(() => {});  // 等那一份回来（而不是睡 1.2 秒）
    const afterBad = await snap(p3);
    SCEN.delay = 0;
    t('⑥ 那一下确实发过请求（不是压根没试）', w6.hit && requests.at(-1) === 8,
      `提示${w6.hit ? '出现过' : '一路没出现' + JSON.stringify(w6.seen.slice(0, 8))}，最后一次请求 span=${requests.at(-1)}`);
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
    scen();                                            // 这一页要的也是全默认
    const p2 = await openPage('2');
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
    scen({ spanMax: 4 });                               // 4 档就是这个周期的顶（而且后台没说「到头」）
    const p4 = await openPage('4');
    await p4.goto(PAGE + '?symbol=ZECUSDT&tf=1h&load=4&tag=p4', { waitUntil: 'load' });
    await p4.waitForFunction(() => window.__app && window.__app.state.data);
    await p4.waitForTimeout(400);
    // ★ 基准必须在**首屏那一发落地之后**取：这一页自己也有一发（load=4），拿它当「多出来的」就是冤枉。
    const base8 = requests.length;
    await pushLeft(p4);                                 // 真拖一下（这一次内部该去要下一档）
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
      scen();                                          // 这一页要的也是全默认（顺带把「声明过」记上）
      const q = await openPage('9-' + raw);            // ★ 页名唯一：三页都叫 '9' 的话记账会当成同一页
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
    scen();
    // ⑩ 首屏就撞上「币安真没了」（AAPL 那种一档就到底的）：**一个多余请求都不许发**，
    //    打开就是一句话「已到最早」。Nova 的契约里点名的那条 —— 首屏不认回显就会白发一趟。
    scen({ earliestFlag: true, spanMax: 16 });
    const p5 = await openPage('10');
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
    await pushLeft(p5);                                 // 真拖一下（贴到最左沿）
    await p5.waitForTimeout(500);
    const aa2 = await snap(p5);
    t('⑩ 贴到最左沿：印「已到最早」', aa2.more === '已到最早' && aa2.moreOn,
      `实际 ${JSON.stringify(aa2.more)} on=${aa2.moreOn}（首屏 span=${aa.span}）`);
    t('⑩ 贴到最左沿：一个额外请求都没有', requests.slice(baseA).length === 1,
      `请求 ${JSON.stringify(requests.slice(baseA))}`);
    await p5.close();
    scen();

    // ⑪ ★★ **反着量的一格**（Atlas 2026-10-04 提的）：**脚本**把视口摆到贴左沿
    //    （from 取负数，就是现场那个 -50 → LWC 归一化回 -53.373 的回声），**一个请求都不许发**。
    //    这一格量的就是 2026-10-04 那个 bug 本身：别的格子全改成真鼠标拖之后，只剩它守着
    //    「页面会不会把自己的回声当成用户在拖」。规矩照旧 —— **改之前红、改之后绿**，
    //    拿 766d053 当「改之前」跑这一格必须是红的（它会在这里发出 span=8）。
    const p6 = await openPage('11');
    const base11 = requests.length;
    await p6.goto(PAGE + '?symbol=ZECUSDT&tf=1h&load=4&tag=echo', { waitUntil: 'load' });
    await p6.waitForFunction(() => window.__app && window.__app.state.data);
    await p6.waitForTimeout(600);
    const before11 = await snap(p6);
    // 两下，**都不按鼠标**：①先摆到远离左沿的地方 ②再摆回贴左沿（from=-50，就是现场那个值）。
    // ★ 为什么要两下：只摆一下的话，如果视口本来就在那儿，LWC 根本不发视口事件，
    //   这一格就成了空转（老页面也能假绿 —— 第一版就是这么绿过一次）。② 那一下**一定会**改变视口。
    const jump = (from) => p6.evaluate((from) => {
      const c = window.__app.chart, r = c.timeScale().getVisibleLogicalRange();
      c.timeScale().setVisibleLogicalRange({ from, to: r.to - r.from + from });
    }, from);
    await jump(200);
    await p6.waitForTimeout(400);                       // 老页面那个 40ms 窗口早过了（bug 就在窗口外）
    await jump(-50);
    await p6.waitForTimeout(2000);                      // 够回声 + 可能的下一档跑完（这一格量「什么都不该发生」）
    const after11 = await snap(p6);
    t('⑪ 脚本摆视口贴到左沿（＝那次回声）⇒ 一个请求都不许发', requests.slice(base11).length === 1,
      `首屏之外 ${JSON.stringify(requests.slice(base11, base11 + 4))}，from ${before11.from} → ${after11.from}`);
    await p6.close();

    // ⑬ ★★ 换档那句话：**只在可视窗口里的结构真变了**的时候出，3 秒，自己收。
    //    Atlas 2026-10-04 要的两格一对：窗口外变 ⇒ 不出 ／ 窗口里变 ⇒ 出。
    //    ★ 两格各自**单开一页**（同一个地址），不是同一页连着拖两下：假后台的老 K 线是编出来的，
    //      换过一次档之后，视口底下那一屏就全是编出来的 K 线了 —— 那一段**一根笔都没有**，
    //      「窗口里的结构变没变」在那儿恒等于「没变」。第一版就是这么绿的/红的（量到的是空转，不是页面）。
    //      每格都用「第一次换档」：那一屏还是真 K 线，窗口里确实有笔有线段。
    const mk13 = async (name) => {
      // ★ 建页之前先回默认场景（⑬ 三格各自的开关在下面单独盖）：
      //   上一格留下的 winmode 会顺手改了这一页的**首屏**，那就不是「只有中枢动」的场景了。
      scen();
      const q = await openPage(name);
      await q.goto(PAGE + '?symbol=ZECUSDT&tf=1h&at=40&span=180', { waitUntil: 'load' });
      await q.waitForFunction(() => window.__app && window.__app.state.data);
      await q.waitForTimeout(700);
      // 场景干净自检：这一页**首屏**那份，后台实际用的场景 ＝ 开页时声明的那份（逐字相同）。
      //   对不上 ⇒ 有开关从上一格漏过来了，这一格量到的就不是它想量的东西（⑬ 第三格踩过）。
      const base = servedLog.find((e) => e.who === name && e.first);
      t(`⑬ 场景干净（第 ${name} 页）：首屏那份是照开页时声明的场景供的`,
        !!base && base.snap === declared.get(name),
        `开页声明 [${declared.get(name)}]／后台实际 [${base && base.snap}]`);
      return q;
    };
    // 可视窗口 → 时间区间（跟页面 windowOf 一个口径；这是**场景**，不是判据）
    const readWin = (q) => q.evaluate(() => {
      const { chart, state } = window.__app;
      const r = chart.timeScale().getVisibleLogicalRange(), b = state.data.bars;
      const a = Math.max(0, Math.ceil(r.from)), z = Math.min(b.length - 1, Math.floor(r.to));
      return { t0: b[a].t, t1: b[z].t };
    });
    // 窗口里到底有没有东西：**没有的话这一格是空转**（判据恒等于「没变」，红绿都说明不了什么）。
    //   ★ 五层逐层报数 —— 少报一层，跟那层有关的格就是「空转的绿」。
    const winStructs = (q, w) => q.evaluate((w) => {
      const d = window.__app.state.data, ts = (i) => (d.bars[i] || {}).t;
      const ov = (o) => ts(o.i0) != null && ts(o.i1) != null && ts(o.i1) >= w.t0 && ts(o.i0) <= w.t1;
      const host = (z, h) => { const a = h[z.PI0], b = h[z.PI1]; return !!a && !!b && ov({ i0: a.i0, i1: b.i1 }); };
      const done = (d.segs || []).filter((s) => !s.live);
      const at = (s) => ts(s.bar) != null && ts(s.bar) >= w.t0 && ts(s.bar) <= w.t1;
      const sig = d.signals || { seg: [], pen: [] };
      return { pens: (d.pens || []).filter(ov).length, segs: (d.segs || []).filter(ov).length,
               centers: (d.centers || []).filter((z) => host(z, d.pens || [])).length,
               segc: (d.seg_centers || []).filter((z) => host(z, done)).length,
               sigs: sig.seg.filter(at).length + sig.pen.filter(at).length };
    }, w);
    const noticeOn = (q) => q.evaluate(() => ({ on: document.getElementById('notice').classList.contains('on'),
                                                txt: document.getElementById('notice').textContent }));

    // —— 第一格：窗口**外**的结构变了、窗口里一根没动 ⇒ 一个字都不许印
    const qA = await mk13('13a');
    const wA = await readWin(qA);
    scen({ pageWin: wA, winmode: 'out' });
    const cntA = await winStructs(qA, wA);
    const nA0 = (await snap(qA)).n;
    const relA = holdNext();
    await pushLeft(qA);
    const pillA = await waitPill(qA, '加载更早数据…', 8000);
    const watchA = watchNotice(qA, 2500);
    relA();
    await qA.waitForFunction((n) => window.__app.state.data.bars.length > n, nA0, { timeout: 20000 }).catch(() => {});
    const A = await watchA;
    const nA1 = (await snap(qA)).n;
    await qA.waitForTimeout(400);                      // 真出了的话它要停 3 秒，躲不过这一段
    const A2 = await noticeOn(qA);
    t('⑬ 第一格不是空转：可视窗口里真有笔/线段', cntA.pens + cntA.segs > 0,
      `窗口里 笔 ${cntA.pens}／线段 ${cntA.segs}`);
    t('⑬ 变化只落在可视窗口**外** ⇒ 不印那句话',
      !A.hit && !A2.on && nA1 > nA0 && pillA.hit,
      `请求真发过=${pillA.hit}，bars ${nA0} → ${nA1}，落定后 ${JSON.stringify(A2)}，采样 ${JSON.stringify(A.seen.slice(0, 5))}`);
    await qA.close();

    // —— 第二格：同一段时间窗，让变化落在窗口**里** ⇒ 那句话必须出现，而且要停满 3 秒
    const qB = await mk13('13b');
    const wB = await readWin(qB);
    scen({ pageWin: wB, winmode: 'in' });
    const cntB = await winStructs(qB, wB);
    const nB0 = (await snap(qB)).n;
    const relB = holdNext();
    await pushLeft(qB);
    const pillB = await waitPill(qB, '加载更早数据…', 8000);
    const watchB = watchNotice(qB, 4500);
    relB();
    await qB.waitForFunction((n) => window.__app.state.data.bars.length > n, nB0, { timeout: 20000 }).catch(() => {});
    const B = await watchB;
    t('⑬ 第二格不是空转：可视窗口里真有笔/线段', cntB.pens + cntB.segs > 0,
      `窗口里 笔 ${cntB.pens}／线段 ${cntB.segs}`);
    t('⑬ 可视窗口里结构变了 ⇒ 印那句话（一个字都不许改）',
      B.hit && B.txt === NOTICE_COPY && pillB.hit,
      `实际 ${JSON.stringify(B.txt)}，请求真发过=${pillB.hit}，采样 ${JSON.stringify(B.seen.slice(0, 5))}`);
    t('⑬ 那句话停 3 秒（说了 3 秒，不是 0.3 秒也不是 30 秒）',
      B.hit && B.offAt != null && Math.abs(B.offAt - B.onAt - 3000) < 400,
      `亮 ${B.onAt}ms → 收 ${B.offAt}ms ＝ ${B.offAt == null ? '没收' : B.offAt - B.onAt}ms`);
    await qB.close();

    // —— 第三格（Nova 2026-10-04 补）：**只有中枢变**（笔/线段/买卖点一根不动）⇒ 也得印那句话。
    //   这一格为什么必要：原来的 structKey 只记笔和线段，中枢变了屏幕上的框明明动了却不出声；
    //   而换档后先变的往往正是中枢（BTC 4h 1↔2 只有线段中枢的 ZD 变了）。这也是最像真换档的一格。
    const qC = await mk13('13c');
    const wC = await readWin(qC);
    scen({ pageWin: wC, winmode: 'in-cen' });
    const cntC = await winStructs(qC, wC);
    bumped = 0;
    const nC0 = (await snap(qC)).n;
    const relC = holdNext();
    await pushLeft(qC);
    const pillC = await waitPill(qC, '加载更早数据…', 8000);
    const watchC = watchNotice(qC, 4500);
    relC();
    await qC.waitForFunction((n) => window.__app.state.data.bars.length > n, nC0, { timeout: 20000 }).catch(() => {});
    const C = await watchC;
    t('⑬ 第三格不是空转：可视窗口里真有中枢/买卖点', cntC.centers + cntC.segc + cntC.sigs > 0,
      `窗口里 类中枢 ${cntC.centers}／线段中枢 ${cntC.segc}／买卖点 ${cntC.sigs}`);
    t('⑬ 第三格场景不是空转：后台真动过窗口里的中枢框', bumped > 0, `动了 ${bumped} 个`);
    t('⑬ 只有中枢变了 ⇒ 也印那句话（屏幕上看得见的东西变了就得说）',
      C.hit && C.txt === NOTICE_COPY && pillC.hit,
      `实际 ${JSON.stringify(C.txt)}，请求真发过=${pillC.hit}，采样 ${JSON.stringify(C.seen.slice(0, 5))}`);
    await qC.close();
    scen();

    // ⑭ ★★ 光**悬停鼠标、一个键都不按** ⇒ 一个请求都不许发（Atlas 2026-10-04 多跑的那一格）。
    //   机理：pointermove 不管按没按键都在刷 ⇒「1.5 秒内动过输入设备」成立，视口一点变化就被当成
    //   「用户在拖」。桌面上从链接点进来、鼠标正好停在图上是最常见的情形 —— 没人拖，页面自己翻一档。
    //   ★ 这一格**不按任何键**，只把鼠标在图上挪；改前（pointermove 不看 buttons）红，改后绿。
    scen({ spanMax: 16 });
    const p14 = await openPage('14');
    const base14 = requests.length;
    //   悬停**从加载中就开始**（Atlas 那格就是这么复现的：加载那一下的视口回声离 pointermove 最近，
    //   等页面全落定了再开始晃，可能一个回声都赶不上 —— 那就成了「量不到」而不是「没问题」）。
    await p14.goto(PAGE + '?symbol=ZECUSDT&tf=1h&at=40&span=180', { waitUntil: 'domcontentloaded' });
    const box14 = await p14.evaluate(() => { const r = document.getElementById('chart').getBoundingClientRect();
                                             return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; });
    await p14.mouse.move(box14.x, box14.y);
    for (let k = 0; k < 10; k++) {
      await p14.mouse.move(box14.x + (k % 2 ? 6 : -6), box14.y + (k % 3 ? 3 : -3));
      await p14.waitForTimeout(120);
    }
    await p14.waitForFunction(() => window.__app && window.__app.state.data).catch(() => {});
    await p14.waitForTimeout(2200);                     // 够回声 + 可能的下一档跑完（这一格量「什么都不该发生」）
    const after14 = await snap(p14);
    //   这一页**只准有首屏那一趟**（span=1）。基线抓在 goto 之前，所以首屏那趟也在 seen 里 ——
    //   写清「首屏除外」比事后挪基线干净：挪基线的话，基线之后新冒出来的第一趟就分不清是首屏还是闯进来的。
    const seen14 = requests.slice(base14);
    t('⑭ 鼠标只在图上悬停（一个键都不按）⇒ 除了首屏那一趟，一个请求都不许发',
      seen14.length === 1 && seen14[0] === 1,
      `这一页发过 ${JSON.stringify(seen14)}（只许 [1]），视口 from=${after14.from}`);
    await p14.close();
  } catch (e) {
    bad.push('工装半路炸了：' + String(e.message || e).split('\n')[0]);
  }
  await b.close();
  // ★★ 场景对账的账在这里收（Atlas 2026-10-04 提的「别一处一处补」）：
  //   每一页**第一份**响应，后台实际用的场景必须跟开页那一刻声明的那份逐字相同。
  //   多一条开关从上一格漏过来（或者谁又起了个平铺的 `let` 忘了进 DEFAULT_SCEN），
  //   这一条就红 —— 它是**跨格**的守卫，不是单格自检。
  t('⑮ 每一页首屏那份数据，用的都是开页时声明的场景（开关没从上一格漏过来）',
    scenBad.length === 0, scenBad.length ? scenBad.join('；') : `${declared.size} 页逐页对过`);
  // ★ 降速值必须印在结果里：同一份代码「绿」和「红」的差别就在这一行，不印出来，
  //   贴出来的结果说不清是哪一档跑出来的（报数带尺，尺也得带参数）。
  console.log('请求序列：', JSON.stringify(requests));
  console.log('CPU 降速：', THROTTLE > 1 ? `${THROTTLE}×（CDP setCPUThrottlingRate）` : '不降速');
  console.log('截图落在：', OUT);
  if (bad.length) {
    console.log(`\n${bad.length} 处不对：`);
    for (const x of bad) console.log('  ✗ ' + x);
  } else {
    console.log(`\n全部 ${ok.length} 条都对`);
  }
  process.exit(bad.length ? 1 : 0);
})();
