// 「背驰四选一」那个切换控件的浏览器工装（card-84091d2d-c97，2026-10-04）
//
// ★ 它**不是**六把尺里的一把：尺子是纯函数、秒级；这一套要 playwright ＋ 真浏览器 ＋ **真后台**
//   （web/server.py：这一格量的是「点一下之后后台真按那个看法重算了没有」，假后台证明不了）。
//   放仓里是为了**别人能复跑**（跟 tools/web_more_e2e.js 一个道理）。
//
// 量的是接线，不是算法（算法归 Bram 的探针）：
//   ① 控件由 /api/meta 的 measures 驱动：**后台给几颗就几颗**（★ 2026-10-04 改：原来写死「四颗」，
//      后台加第五种 `macd_or_lines` 之后这两格**假红**了 —— 名字明明是大白话，红出来的话是假的。
//      判据换成「页面名单 == /api/meta 的名单」）、**名字是大白话**（`名字 !== 代号`，且已知那四种
//      的老名字得原样）、选中态走 aria-checked（不是图层那排的 aria-pressed）
//   ② 点「黄白线」⇒ 那一趟请求带 measure=lines（**带的是被点的那个**，不是缺省）
//   ③ 图脚**跟着回显**换：「背驰看法 黄白线」（回显说了算，不拿点的那颗当准）
//   ④ 亮着的那颗也跟着回显换
//   ⑤ 切看法**结构逐字节不变**：bars/pens/segs/centers/seg_centers 前后全等（后台契约）
//      ★ 这一格**必须**是「同一趟币安取数」内的两份（fetched_at 对账 ＋ 撞上就重跑）：
//        后台每 60s 重拉，跨在重拉两边的两份本来就该不一样 —— 不闸住它就是随机红
//   ⑥ 买卖点**真的变了**：signals 前后不等（不然这一格是空转 —— 四选一要是没接上，五个断言全绿）
//   ⑦ **三角真的画出来了**（2026-10-04 补）：在买卖点那颗三角盘踞的那一小块上，把「买卖点」chip
//      关掉再点开，只认买卖点那两个颜色（±8）—— **多出来的**像素得够一颗三角。★ 这一格是补课：
//      线上出过一次「买卖点整层一颗不画」，而当时这句「屏幕真的变了」照样绿 —— 它量到的像素差
//      来自买卖点的**文字**，是替身。补的这格只取三角那一块、只认那两个颜色，差分看。
//   ⑧ 同一状态重拍，读数一模一样（⑦ 的防空洞：这一格量的是那个开关，不是抖动）
//   ⑨ 屏幕**真的变了**：图的像素前后不等（数据变了不等于画出来了；这条是拍照，不是读状态）
//   ⑩ 视口**一动没动**（切看法不换档，同一根 K 线还在同一个逻辑下标上）
//   ⑪ 档位那套**没被踩坏**：切完 nogain=false（把它当成「补数据没多出来」，下一拖就会印假话）
//   ⑫ ?measure=lines 直接打开 ⇒ **第一趟**图表请求就带 lines，图脚写「黄白线」
//   ⑬ ?measure=乱写 ⇒ 一个字都不发出去（名单外发出去是 400，整张图会白挂），页面照常画
//   ⑭ 旧后台（/api/meta 没有 measures）⇒ 控件**不出现**、请求**不带** measure、图脚**不多**那一格
//   ⑮ 买卖点那层**关着** ⇒ 看法这四颗**置灰点不动**（层关着时换看法，屏幕上一个像素都不会变 ⇒
//      点了没反应会被当成坏了）；而且理由要写在**标题那行**上，不能只塞 title（手机没有 hover）
//   ⑯ 把那层点开 ⇒ 那四颗又亮回来、标题回到「背驰看法」（⑮ 的防空洞：别修成一辈子灰着）
//   ⑰ 切看法**真的落到那几个点上**（2026-10-04 我补的，替掉原来那格「整屏像素前后不等」）：
//      只在那几个**差出来的点**盘踞的小块里、只认买卖点那两个颜色，两边各读一次，**看差**。
//      ★ 原来那句「屏幕的像素前后不等」是**替身**：它绿的来源跟买卖点没关系。我量到过两次 ——
//        (a) 最后一根的价签在跳（84936.4 → 84939.5），那一跳就够让它绿；
//        (b) 把后台**冻住**之后，切看法那一下整块画布重绘了 57367 个像素（横贯全图），
//            而同一次切法里**买卖点那层贡献的差是 0** —— 也就是说它绿得跟买卖点毫无关系。
//        现在这一格跟 ⑦ 同一套读法（同一小块、同一组颜色、只看差），所以它绿一定是因为那几个点。
//
//   ⑱ 「非原文」那枚标（2026-10-04 补，card-6381042d-03f，小栋定 ①A）：**标 ⇔ `/api/meta` 的
//      `measure_orig[看法] === false`**，不是前端认死「斜率」两个字。五格：真后台一致（后台还没这个
//      字段时要求**一个标都没有**）／旧形状没有 measure_orig ⇒ 不凭空冒标／**四颗全是原文 ⇒ 一个标都没有**
//      （牙齿，抓「写死斜率带标」）／只有斜率非原文 ⇒ 只它带标、名字不受污染、悬停那句在／名单换成
//      `[{id, orig}]` ⇒ 照吃。★ 每格都印两串（页面带标的 vs meta 说的），免得后台没字段时成为**死闸**。
//
//   ⑲ 后台**多一种量法**（2026-10-04 补，`macd_or_lines`，card-bead5f56-74b）：假后台给五颗 ⇒ 第五颗
//      上得是中文名。★ 断言是 `名字 !== id` 而不是比对某个字面量 —— **改名不该红，漏名才该红**；
//      这一格守的是「后台先上线、名字没跟上」那半天：屏幕上会是一串英文 id，不报错也认不出。
//
//   ㉜–㊳ **走势分段那一层**（2026-10-05 补，card-c73ab37d-5a1，v3 §八）：这一层**默认开**
//      （Nova 17:09Z：小栋要看的东西不能藏在 `?trend=1` 后面）。落在这套里是因为**它只有真后台
//      给得出** —— `trend` 那个对象是 Bram 在 dbda139 里新加的，`more` 那套的假后台没有它。
//      ①默认开（开关亮／地址栏不写／真画出带子）②**颜色跟段型走**（上涨⇒绿／下跌⇒红／盘整与图头⇒灰；10-08 小栋选 B），
//      不是跟段的 `type` 走 ③中阴那条斜线带铺在「极值 → 载荷的 `pullback_end_bar`」上（**不是段末**，
//      这是 §八 3 的牙）④分界的价格字横心钉在极值那一根上 ⑤「待定」和「撤回」各写各的、条数对得上
//      ⑥`?trend=0` 关得掉，且**那个色的像素真的清零**（数颜色，不数"前后两张图不等"—— 后者会拿
//      价签跳动当替身）⑦`cut=extend` 那档载荷没有 `trend` 键 ⇒ 开关按灰、一条不画、图照常画。
//      ⑤b（2026-10-06 补，card-3edd7fb3-412）那条「待定」的**灰点线钉在载荷说的那一根上** ——
//      量画布像素（局部对比 ＋ 点划周期 == `DASH.trendCand` ＋ 段数），不读 state。它是 ghost ⑰e
//      退休时的**接班的**：那格原先钉的就是"待定画在 `cut_bar` 那一根上"，位置守卫不能跟着退休。
//      ★ 判据的色号和不透明度都从 `/theme.js` 现读（`await import('/theme.js')`）：改配色这几格跟着走。
//
//   ★★ **全屏看图**（2026-10-06 补，card-5014b0cb-e4d）：卡里六条 ——
//      ① 别挡右轴/最新价标签：判据是**画布像素**里那条轴边框线（`--line` 色、顶部 26 行通高的一列），
//         按钮右沿必须落在它左边 ≥4px。**不用**"按钮 right ≥ 某个数"：那个数是我自己写进 CSS 的，
//         自己给自己判卷（跟 ⑤ 那条"不读自报出口"同一条账）。最新价标签就画在那条竖栏里。
//      ② 全屏里点一颗 chip 状态真翻、且那颗**在视口里**；③ 进全屏**视口一根 K 线都不跳**（Δ ≤ 1.5 根，
//         LWC 会把视口归一化微调一下，所以不是全等）；④ 退路（原生被禁的手机档自铺满窗口 ＋ Esc 退得掉）；
//      ⑤ 卡里"自动重画"那条是**量**出来的（画布高度跟着图的新尺寸走，不是"读代码知道 autoSize 会重画"）；
//      ⑥ 再点一次退得掉、尺寸和视口都回原样。
//      ★ 原生全屏在无头浏览器里可能被拒 ⇒ 每格都**印出走的是哪条路**：落到退路还把绿说成"原生验过了"，
//        那是假绿。⑦ 那一格用 `addInitScript` 把 `fullscreenEnabled` 按成 false，专门咬退路那条。
//
//   ★ 牙齿（2026-10-04 我补的）：把页面弄坏、看它**是红还是炸**。做法：去掉 web/app.js 里那句
//     `b.dataset.measure = id;`（芯片照常渲染四颗按钮，只是工装点不着 `.mchip[data-measure="lines"]`）。
//       摘掉修法 ⇒ rc=2「炸了：locator.click: Timeout 30000ms exceeded」——只印了 7 格，**没有判词**；
//       现在   ⇒ rc=1、**24 格全印**，⑧ 红在那一格上并写着「★ 那颗芯片**点不动**：…」，
//                ⑨⑩⑫⑮⑰⑲ 跟着红（后面那几格是这次没换成的后果，不是新账）。
//     ★ 两处都守住才算「不炸」：**点不动**（`sw()` 里 click 的 try）＋**读不到亮着的那颗**
//       （`lit()` 的 `(… || {}).id`）。原来只有前半边，坏页面会一路炸到第 ⑩ 格。
//
// 跑法：
//   1) 真后台，**只绑回环**（部署纪律：不许绑全网卡）：
//        python3 web/server.py --port <端口>
//   2) playwright：`npm i playwright && npx playwright install chromium`（各机器一次）
//      node_modules 不在仓里 —— 在装好 playwright 的目录下跑，用 NODE_PATH 指过来即可。
//   3) node tools/web_measure_e2e.js [输出目录] [页面地址]
//        输出目录默认 $TMPDIR/measure-e2e（截图落这儿；不写进仓）
//        页面地址：必须给 E2E_URL（或参数），本工装不带默认
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

const OUT = process.argv[2] || path.join(os.tmpdir(), 'measure-e2e');
const PAGE = (process.env.E2E_URL || process.argv[3] || noUrl()).replace(/\/?$/, '/');   // E2E_URL 优先（上线门统一给，card-9b0fe913-758）
const QS = '?symbol=ZECUSDT&tf=15m';       // 周期挑最短的那档：首屏快，且这一档的四种看法分得最开
let bad = 0, n = 0;
const ck = (name, ok, extra) => {
  n++;
  if (!ok) bad++;
  console.log(`  ${ok ? '✓' : '✗'} ${n}. ${name}${extra ? '　' + extra : ''}`);
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 页面上画出来的那份数据（比较用：结构四件套 + 买卖点）
const shape = (p) => p.evaluate(() => {
  const d = window.__app.state.data;
  const J = (x) => JSON.stringify(x);
  return {
    // ★ 最后一根的 o/h/l/c **不进比较**：跳价（app.js `tickApply`，card-f3fffac4-83d）会就地改它，
    //   两份快照之间撞上一趟跳价 ⇒「同一趟取数」照样不等，这一格白红（10-08 两次实测：15:25Z、16:00Z）。
    //   跳价只动最后一根的价、不动开盘时间也不动结构，所以最后一根只比 `t`，其余照旧逐字节比。
    struct: [J(d.bars.slice(0, -1)), J(d.bars.length ? d.bars[d.bars.length - 1].t : null),
             J(d.pens), J(d.segs), J(d.centers), J(d.seg_centers), J(d.big)].join('#'),
    sigs: J(d.signals), nbars: d.bars.length, span: d.span, measure: d.measure,
    fetched: d.fetched_at,      // ★ ⑤ 那一格的闸：这两份是不是**同一趟币安取数**（见下面那段说明）
    range: window.__app.chart.timeScale().getVisibleLogicalRange(),
    paging: { span: window.__app.paging.span, nogain: window.__app.paging.nogain,
              measure: window.__app.paging.measure, spanMax: window.__app.paging.spanMax },
  };
});
const ui = (p) => p.evaluate(() => {
  const g = document.getElementById('mgroup');
  return {
    has: !!g,
    items: g ? [...g.querySelectorAll('.mchip')].map((b) => ({
      // ★ `txt` 是**名字**，**不含**那枚「非原文」小标（`.nonorig`）—— 标是标记，不是名字的一部分。
      //   拿整条 `textContent` 当名字的话，「名字是大白话」那一格会跟着标记一起变，两件事量成一件事，
      //   而且以后换了标记的措辞，那一格会无缘无故地红。
      id: b.dataset.measure,
      txt: [...b.childNodes].filter((nd) => !(nd.nodeType === 1 && nd.classList.contains('nonorig')))
                            .map((nd) => nd.textContent).join('').trim(),
      mark: (b.querySelector('.nonorig') || {}).textContent || null,
      on: b.getAttribute('aria-checked'),
      pressed: b.getAttribute('aria-pressed'),
      disabled: b.disabled,
      role: b.getAttribute('role'), title: b.title })) : [],
    cap: g ? (g.querySelector('.mcap') || {}).textContent : null,
    meta: (document.getElementById('meta') || {}).textContent || '',
  };
});
const waitData = (p) => p.waitForFunction(() => window.__app && window.__app.state && window.__app.state.data, null, { timeout: 120000 });
// 「亮着的那颗是哪个」——**读不到就回 undefined**（`(… || {}).id`），别当场炸。
// ★ 一处炸了整支工装就 rc=2、后面的格一个字都不印 ⇒ 页面坏的时候是**没有判词**的，比红还糟。
//   三处 `items.find(…).id` 原来都是裸链（⑩⑲ 那两处会真炸：页面上没有一颗 aria-checked=true 时
//   find 回 undefined）。判据一个字没改：undefined !== 'lines' 照样红，只是红得出来。
const lit = (u) => (u.items.find((i) => i.on === 'true') || {}).id;
// 只拍图那一栏（顶栏/图脚那些字不参与）：像素一样＝这一屏没变
const shotChart = async (p, tag) => {
  const box = await p.locator('#chart').boundingBox();
  const buf = await p.screenshot({ clip: box });
  fs.writeFileSync(path.join(OUT, `fig-${tag}.png`), buf);
  return buf;
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const b = await chromium.launch();
  const open = async (qs, opts = {}) => {
    const c = await b.newContext({ viewport: { width: 1440, height: 900 } });
    const p = await c.newPage();
    const reqs = [];
    p.on('request', (r) => { if (r.url().includes('/api/chart')) reqs.push(r.url()); });
    if (opts.meta) await p.route('**/api/meta', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(opts.meta) }));
    if (opts.oldBackend) {
      // 假装是**今天之前那个后台**：那时候没有 measure 这个参数 ⇒ /api/meta 里没有 measures、
      // 图表响应里也没有 measure 这个字段（**两头都抹掉**才算「旧后台」：只抹一头的话，
      // 图脚那份回显还是真的，「图脚不该多那一格」就永远量不到 —— 第一版就是这么假绿的）。
      await p.route('**/api/meta', (route) => route.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ symbols: ['ZECUSDT'], tfs: ['15m'] }) }));
      await p.route('**/api/chart*', async (route) => {
        if (/[?&]measure=/.test(route.request().url())) opts.sawMeasure = route.request().url();
        const r = await route.fetch();
        const j = await r.json();
        delete j.measure;
        await route.fulfill({ status: r.status(), contentType: 'application/json', body: JSON.stringify(j) });
      });
    }
    await p.goto(PAGE + qs, { waitUntil: 'domcontentloaded' });
    await waitData(p);
    await sleep(1200);                    // 等控件那一趟 /api/meta（并行发的，可能比图晚一拍）
    return { c, p, reqs, opts };
  };

  // ★★ 开跑①–⑨之前：等后台**刚拉过币安**。回显里的 fetched_at 就是那趟的时间，
  //    age 离 60s 还早就把场景摆进同一趟取数里（不然开页那趟跟点一下那趟会跨在重拉两边，⑤ 假红）。
  //    只在「快到点了」时才等（age > 35 才等），多数时候一眼就过。
  const stamp = async () => {
    const d = await (await fetch(PAGE + 'api/chart?symbol=ZECUSDT&tf=15m')).json();
    return { at: d.fetched_at, age: (Date.now() - Date.parse(d.fetched_at)) / 1000 };
  };
  if (typeof fetch === 'function') {
    const st = await stamp();
    if (st.age > 35) {
      console.log(`  等一趟重拉（手上这份数据已经 ${st.age.toFixed(0)}s 了）…`);
      // age ≥ 60 ⇒ 已经过点了，刚才那一问就已经把它踢去拉了，不用再睡；
      // 35 < age < 60 ⇒ 先睡到那一刻（注意别睡出负数：setTimeout 会把负的当 1ms）
      if (st.age < 60) await sleep((61 - st.age) * 1000);
      // 重拉是**懒**的：到点了也得有人来要它才拉（server.py get_chart），且这一趟先回旧缓存
      // ⇒ 得轮着问、直到 fetched_at 真换掉
      let i = 0;
      while (i < 20 && (await stamp()).at === st.at) { await sleep(1000); i++; }
      if (i >= 20) console.log('  ⚠ 等了 20s 也没换新的（后台这轮大概没拉到币安）—— 照跑，⑤ 会自己红');
    }
  }

  // ---- ①–⑨：普通那一页
  console.log('1–17 打开页面、点一下「黄白线」（含 5-7 那三格：层关着时那组该置灰）');
  const { c, p, reqs } = await open(QS);
  const u0 = await ui(p);
  // ★ 名单**不写死条数和名字**（2026-10-04 改，Bram 加了第五种 macd_or_lines 之后这两格假红）：
  //   后台加一种量法，是后台的事，页面照它给的渲染就是对的 —— 写死「四颗」等于把工装焊在
  //   当时那份名单上，改一次后台就红一次，而红出来的两格说的都是**假话**（名字明明是大白话）。
  //   判据换成「页面 == /api/meta」，这才是这一段真正要量的东西（控件由 /api/meta 驱动）。
  const metaJson = await (await fetch(PAGE + 'api/meta')).json();
  const wantIds = Array.isArray(metaJson.measures) ? metaJson.measures : [];
  ck('控件的名单**就是 /api/meta 说的那个**（顺序也一样 —— 不是前端自己凑的四颗）',
     u0.has && wantIds.length > 0 && JSON.stringify(u0.items.map((i) => i.id)) === JSON.stringify(wantIds),
     `页面 ${u0.items.map((i) => i.id).join('/')} ／ meta ${wantIds.join('/')}`);
  // ★ 名字仍然有牙齿：**每颗都得是中文名**（`名字 !== 代号`），而且**已知那四种的老名字没被改坏**。
  //   后半句是关键 —— 只说「不等于代号」，把「面积」改成「MACD」也照样绿。
  const NAME4 = { macd: '面积', slope: '斜率', lines: '黄白线', peak: '峰值' };
  ck('每颗都是中文名、不是代号，且已知那四种的名字没被改坏',
     u0.items.every((i) => i.txt && i.txt !== i.id)
     && Object.keys(NAME4).every((id) => { const it = u0.items.find((x) => x.id === id); return !it || it.txt === NAME4[id]; }),
     u0.items.map((i) => `${i.id}:${i.txt}`).join(' '));
  ck('是**单选**的形状：role=radio ＋ aria-checked，不是图层那排的 aria-pressed',
     u0.items.every((i) => i.role === 'radio' && i.pressed === null) && u0.items.filter((i) => i.on === 'true').length === 1
     && lit(u0) === 'macd');
  ck('图脚写着当前用的那种（默认＝面积）', u0.meta.includes('背驰看法 面积'), u0.meta.slice(-40));
  // ★ 买卖点默认是**关**的：这一组只换**买卖点**的画法 ⇒ 层关着的时候换看法，屏幕上**什么都不会变**，
  //   那就得**点不动**（点了没反应，用户会当成坏了）。手机没有 hover，所以标题那行也得说。
  ck('买卖点还关着 ⇒ 看法那组**点不动**（四颗都 disabled）',
     u0.items.every((i) => i.disabled), u0.items.map((i) => i.disabled).join('/'));
  ck('关着的时候标题那行也写了原因（不能只写在 title 里，手机没有 hover）',
     (u0.cap || '').includes('买卖点'), `cap=${JSON.stringify(u0.cap)}`);
  // ★ 买卖点默认是**关**的：不打开它，切看法屏幕上什么也不会变（这一格得先把它打开，否则 ⑥⑦ 是空转）
  await p.locator('.chip[data-key="sig"]').click();
  await sleep(900);
  const u0b = await ui(p);
  ck('打开买卖点 ⇒ 那组又能点了、标题回到「背驰看法」',
     u0b.items.every((i) => !i.disabled) && (u0b.cap || '') === '背驰看法',
     `disabled=${u0b.items.map((i) => i.disabled).join('/')} ｜ cap=${JSON.stringify(u0b.cap)}`);
  // ★★ 拍像素之前先把视口**摆到两种看法真的不一样的地方**去。第一版直接拍当前这一屏 ⇒
  //    像素一模一样，看着像「切了看法屏幕没变」，其实是**那几处差异根本不在可视窗口里**
  //    （整段 20160 根、窗口在最后 300 根）。那是工装自己把两件事搞混了：图脚上的计数是**整段**的，
  //    像素只认**这一屏**。所以先问后台要两份、找出不一样的那几根，再摆过去。
  //    ⑰（下面那格）还要拿这几个点的**完整信息**（tier/kind/bar/price）去量「墨多没多」，
  //    所以这里直接回对象，不只回 bar 号。
  const diffSigs = await p.evaluate(async () => {
    const get = async (m) => (await (await fetch(`/api/chart?symbol=ZECUSDT&tf=15m&measure=${m}`)).json());
    const [a, b2] = [await get('macd'), await get('lines')];
    const map = (d) => { const o = new Map();
      for (const tier of ['seg', 'pen']) for (const s of (d.signals[tier] || [])) o.set(s.bar + ':' + s.kind, { ...s, tier });
      return o; };
    const A = map(a), B = map(b2), out = [];
    for (const [k, s] of B) if (!A.has(k)) out.push({ ...s, only: 'lines' });   // 换成黄白线**多出来**的
    for (const [k, s] of A) if (!B.has(k)) out.push({ ...s, only: 'macd' });    // 换成黄白线**没了**的
    return out;
  });
  const diffBars = diffSigs.map((s) => s.bar).slice(0, 8);
  if (diffBars.length) {
    const at = diffBars[Math.floor(diffBars.length / 2)];
    await p.evaluate((i) => window.__app.chart.timeScale().setVisibleLogicalRange({ from: i - 120, to: i + 120 }), at);
    await sleep(600);
  }
  // ★★ ⑤「结构逐字节不变」这一格的闸：**得是同一趟币安取数**。
  //    后台每 REFRESH_S=60s 重拉一次（web/server.py）；s0 是**页面开页那趟**拿到的，
  //    s1 是点一下之后**新发的那趟**拿到的 —— 中间撞上重拉，最后一根 K 线的收盘就在变，
  //    结构**真的会不一样**：那是后台的账，不是切看法的账。
  //    （第一版没管这个，⑤ 就随机红：同一份代码前一次绿、这一次红。当时查了半天，
  //      原因是「两次观测」根本不保证在同一趟取数里。）
  //    两道闸：① 开跑**之前**等后台刚拉过 —— 把整个场景摆进一趟取数里（见上面那段 wait）
  //            ② 收尾时拿 fetched_at 对账：对不上就切回默认重跑一对（最多三对），三对都撞上才红
  const hex2rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const MARK = await p.evaluate(async () => {
    const m = await import('/theme.js');
    return { buy: m.CHART.buy, sell: m.CHART.sell, seg: m.SIG.segSize, pen: m.SIG.penSize, tip: m.SIG.tip };
  });
  const chartBox = await p.locator('#chart').boundingBox();
  // 把一个买卖点的「三角盘踞的那一小块」算成屏幕像素框（⑦ 拿它量开关，⑰ 拿它量切看法）
  const boxOf = (list) => p.evaluate(([list, MARK, box]) => {
    const ch = window.__app.chart, ts = ch.timeScale(), s0 = ch.panes()[0].getSeries()[0];
    const out = [];
    for (const s of list) {
      const x = ts.logicalToCoordinate(s.bar), y = s0.priceToCoordinate(s.price);
      if (x === null || y === null || x < 60 || x > box.width - 60) continue;   // 屏幕外的样本不量
      const hh = (s.tier === 'seg' ? MARK.seg : MARK.pen) * 0.55;   // ＝ layers.js 那个 0.55
      const d = s.kind.endsWith('买') ? 1 : -1;                     // 买点在点位下方、卖点在上方
      const yy = Math.min(y + d * MARK.tip * 0.6, y + d * (MARK.tip * 0.6 + 2 * hh));
      out.push({ tier: s.tier, kind: s.kind, bar: s.bar, only: s.only, buy: s.kind.endsWith('买'),
                 x: Math.round(box.x + x - hh - 2), y: Math.round(box.y + yy - 2),
                 w: Math.round(2 * hh + 5), h: Math.round(2 * hh + 5) });
    }
    return out;
  }, [list, MARK, chartBox]);
  const countMarks = (bs) => p.evaluate(([bs, buy, sell]) => {
    // ★ 颜色**只认这两个**（±8）：放太宽会把阴线 `#ef5350`（跟卖点 `#ff5656` 只差 (16,3,6)）算进来，
    //   那一格就变成「在数量 K 线」。已确认的点 alpha=255，三角内部是**纯色**，收紧也数得到。
    const near = (a, b) => Math.abs(a - b) <= 8;
    const which = (r, g, b) => (near(r, buy[0]) && near(g, buy[1]) && near(b, buy[2])) ? 'buy'
      : (near(r, sell[0]) && near(g, sell[1]) && near(b, sell[2])) ? 'sell' : null;
    const cvs = [...document.querySelectorAll('#chart canvas')].map((c) => ({ c, r: c.getBoundingClientRect() }));
    return bs.map(({ x, y, w, h, buy }) => {
      // ★ 一张图上是**好几层画布**（K 线一层、primitive 另起一层）。买卖点画在哪一层是实现细节，
      //   所以**每一张盖住这一块的都要读**、个数相加；只读第一张的话，读错了层就是恒 0 的假红
      //   （第一版就是这么红的：图看着有三角，这一格说 0）。
      const hit = cvs.filter(({ r }) => x >= r.left && y >= r.top && x + w <= r.right && y + h <= r.bottom);
      if (!hit.length) return { miss: '那一块没落在任何一张画布上' };
      let n = 0;
      for (const { c, r } of hit) {
        const px = c.getContext('2d').getImageData(Math.round(x - r.left), Math.round(y - r.top), w, h).data;
        for (let i = 0; i < px.length; i += 4) if (which(px[i], px[i + 1], px[i + 2]) === (buy ? 'buy' : 'sell')) n++;
      }
      return { n };
    });
  }, [bs, hex2rgb(MARK.buy), hex2rgb(MARK.sell)]);
  const need = (t) => (t === 'seg' ? 24 : 3);                  // 实心三角 ~136 格、空心笔层就几格描边

  // ★★ ⑰ 的「切之前」这一读：视口刚摆到差异点上，此刻还是**面积**。
  const diffBoxes = (await boxOf(diffSigs)).slice(0, 4);
  const nBefore = await countMarks(diffBoxes);

  // ★★ 等它换过来，但**超时不许把整支工装炸掉**（Atlas 2026-10-04 核的：变异「切的时候发旧看法」
  //    原来在这行 Timeout 炸了、rc=2，一个字都没印出来）。**炸掉不等于红** ——
  //    红要红在某一格上，并且说出它当时看到了什么（发出的是什么、回显是什么、图脚写的什么）。
  //    所以超时收成一个返回值，让下面几格照实报。
  //    ★ 同一笔账的另一半（2026-10-04 我补的）：**点不动也不许炸**。上面那句守的是「点了之后没换过来」，
  //      可 `.mchip[data-measure=…]` 本身找不着／被置灰时，**click() 自己就会抛**（Playwright 等
  //      actionability 等满 30s 再扔），一样是 rc=2、一个字都不印 —— 而且它比超时更早、更靠前，
  //      栽在它上面的话连「发出的是什么」都读不到。所以点成了才去等；没点成就把原因写进 clk，
  //      让 ②③④ 那几格照旧红、并且红的时候说得出「芯片点不动：…」。
  const sw = async (id) => {                    // 点一颗看法、等它真换过来；回这一趟发出的 measure ＋ 当时的状态
    const kk = reqs.length;
    let ok = true, clk = null;
    try {
      await p.locator(`.mchip[data-measure="${id}"]`).click();
    } catch (e) { ok = false; clk = String((e && e.message) || e).split('\n')[0]; }
    if (ok) {
      try {
        await p.waitForFunction((m) => window.__app.state.data && window.__app.state.data.measure === m, id, { timeout: 30000 });
      } catch (e) { ok = false; }
    }
    await sleep(900);
    const got = await p.evaluate(() => ({
      echo: window.__app.paging.measure,
      drawn: window.__app.state.data && window.__app.state.data.measure,
      footer: (document.getElementById('meta') || {}).textContent || '',
    }));
    return { ok, id, clk, sent: reqs.slice(kk).map((u) => new URL(u).searchParams.get('measure')), got };
  };
  let s0, s1, px0, px1, sent, redo = 0;
  for (;;) {
    s0 = await shape(p); px0 = await shotChart(p, 'before');
    sent = await sw('lines');
    s1 = await shape(p); px1 = await shotChart(p, 'after');
    if (!sent.ok || s0.fetched === s1.fetched || redo >= 2) break;
    redo++;                                     // 这两份不是一趟取数 ⇒ 切回去、重来一对
    const back = await sw('macd');
    if (!back.ok) break;                        // 切回去都没换成 ⇒ 别再空转，让下面照实报
  }
  const u1 = await ui(p);
  const nAfter = await countMarks(diffBoxes);      // ⑰ 的「切之后」这一读（此刻已经是黄白线）
  const why = `发出的 measure=${JSON.stringify(sent.sent)}；回显=${JSON.stringify(sent.got.echo)}` +
              `、画的是=${JSON.stringify(sent.got.drawn)}；图脚尾=…${sent.got.footer.slice(-28)}` +
              (sent.clk ? `；★ 那颗芯片**点不动**：${sent.clk}` : '');
  ck('点的是「黄白线」⇒ 发出去的就是 lines', sent.ok && sent.sent.length === 1 && sent.sent[0] === 'lines', why);
  ck('图脚跟着**回显**换：背驰看法 黄白线', u1.meta.includes('背驰看法 黄白线'), u1.meta.slice(-40));
  ck('亮着的那颗也跟着回显换', lit(u1) === 'lines');
  ck('结构逐字节不变（bars/pens/segs/centers/seg_centers）',
     s0.fetched === s1.fetched && s0.struct === s1.struct && s0.nbars === s1.nbars,
     s0.fetched === s1.fetched
       ? `同一趟取数 ${s0.fetched}${redo ? `（撞上重拉、重跑了 ${redo} 遍）` : ''}`
       : `★ 这两份不是同一趟取数：${s0.fetched} → ${s1.fetched}（后台重拉过，这一格量不准）`);
  ck('买卖点真的变了（不然这一格是空转）', s0.sigs !== s1.sigs,
     `段 ${JSON.parse(s0.sigs).seg.length}→${JSON.parse(s1.sigs).seg.length} 笔 ${JSON.parse(s0.sigs).pen.length}→${JSON.parse(s1.sigs).pen.length}`);

  // ★★ 三角到底画出来了没有 —— 2026-10-04 补的一格（线上真出过：买卖点**整层一颗不画**，而下面
  //    那格「屏幕真的变了」照样绿：它量到的像素差来自买卖点的**文字**，是替身）。
  //    口径（Atlas 2026-10-04）：只取**三角盘踞的那一小块**、只认**买卖点那两个颜色**，不拿整屏比。
  //    ★ 为什么是**关/开差分**而不是「开着得有、关掉得空」：那一小块正好落在波段顶/底上，
  //      里面本来就躺着同色的东西 —— 线段端点的空心圈（也是 CHART.buy/sell，跟买卖点同一个色）
  //      和挨着的阴线。所以两边都读一次、**看差**：差分里剩下的才是这一个开关管的那颗三角。
  //      （第一版写「关掉必须为 0」，红得对但红错了地方：那些像素根本不归这个开关管。）
  //    两问：① 点开买卖点 ⇒ 那块里多出来的买卖点色够一颗三角；② 这个读数是**稳的**（同一状态重拍一样）。
  //    （读法 boxOf/countMarks 挪到上面去了：⑰ 得在「切之前」就能读一次。）
  const sigsNow = await p.evaluate(() => {
    const out = [];
    for (const tier of ['seg', 'pen']) for (const s of (window.__app.state.data.signals[tier] || []))
      if (s.confirmed) out.push({ tier, kind: s.kind, bar: s.bar, price: s.price, only: null });  // 待确认默认不画，别拿它当样本
    return out.sort((a, b) => (a.tier === b.tier ? 0 : a.tier === 'seg' ? -1 : 1));
  });
  // ★ 先按「在不在这一屏里」筛，**再**取前 3 个样本 —— 原来 `slice(0,3)` 在筛之前，样本会随行情飘：
  //   屏幕上明明有 3 颗，取到的却是「全段前 3 颗」里两颗在屏幕外的（实测 x=-214），
  //   这一格就白红了（读数其实一模一样）。红得对，但红错了地方。
  // ★ 默认视口里不够 2 颗就挪视口去找 2 颗（C3 默认翻成 6 根以后实测：ZEC 15m 默认视口只剩 1 颗已确认点，
  //   13/14 两格白红 —— 不是三角没画，是样本不够）。挪到「最后两颗」上，量完把视口还回去，后面的格不受影响。
  let viewBack = null;
  if ((await boxOf(sigsNow)).length < 2 && sigsNow.length >= 2) {
    viewBack = await p.evaluate(() => window.__app.chart.timeScale().getVisibleLogicalRange());
    const last2 = [...sigsNow].sort((a, b) => a.bar - b.bar).slice(-2).map((s) => s.bar);
    const mid = (last2[0] + last2[1]) / 2, half = Math.max(150, (last2[1] - last2[0]) / 2 + 60);
    await p.evaluate(([f, t]) => window.__app.chart.timeScale().setVisibleLogicalRange({ from: f, to: t }), [mid - half, mid + half]);
    await sleep(1200);
  }
  const triBoxes = (await boxOf(sigsNow)).slice(0, 3);
  const on = await countMarks(triBoxes);                       // 这一页的买卖点**已经点开**（见上面那一行）
  await p.locator('.chip[data-key="sig"]').click(); await sleep(800);
  const off = await countMarks(triBoxes);
  await p.locator('.chip[data-key="sig"]').click(); await sleep(800);    // 点回来；后面那格用的就是这一次
  const again = await countMarks(triBoxes);
  const desc = (a) => a.map((o, i) => `${triBoxes[i].kind}@${triBoxes[i].bar}${o.miss ? '（' + o.miss + '）' : '=' + o.n}`).join(' ');
  const dlt = on.map((o, i) => o.n - (off[i] ? off[i].n : 0));
  ck('买卖点点开 ⇒ 三角那一块里**真多出一颗三角**（关/开同一块差分，只认买卖点那两个颜色）',
     triBoxes.length >= 2 && dlt.every((d, i) => d >= need(triBoxes[i].tier)),
     `${triBoxes.length} 颗样本：开着 ${desc(on)}｜关掉 ${desc(off)}｜多出来 ${JSON.stringify(dlt)}`);
  ck('同一状态重拍，读数一模一样（这一格量的是那个开关，不是抖动）',
     triBoxes.length >= 2 && again.every((o, i) => o.n === on[i].n),
     `两次都开着：${desc(on)} ／ ${desc(again)}${viewBack ? '（默认视口不够 2 颗，挪到最后两颗上量的）' : ''}`);
  if (viewBack) { await p.evaluate((r) => window.__app.chart.timeScale().setVisibleLogicalRange(r), viewBack); await sleep(1200); }
  // ★★ ⑰ 切看法**真的落到那几个点上**（替掉原来那句「整屏像素前后不等」—— 那句是替身，见文件头上 ⑰ 的说明）。
  //    只在「两种看法差出来的那个点」盘踞的小块里、只认买卖点那两个颜色，切之前读一次、切之后读一次，**看差**：
  //    多出来的点必须**多出够一颗三角的墨**，少掉的点必须**少掉**那么多。（差分是必须的：那一小块落在
  //    波段顶/底上，里面本来就躺着同色的线段端点空心圈 —— 这正是 ⑦ 踩过的那个坑。）
  const oD = (a, tag) => a.map((o, i) => `${tag}${diffBoxes[i].kind}@${diffBoxes[i].bar}${o.miss ? '（' + o.miss + '）' : '=' + o.n}`).join(' ');
  const sign = (t) => (t === 'lines' ? 1 : -1);                 // 黄白线多出来的点 ⇒ 墨该多；少掉的 ⇒ 墨该少
  const dD = nBefore.map((o, i) => sign(diffBoxes[i].only) * ((nAfter[i] && nAfter[i].n ? nAfter[i].n : 0) - (o.n || 0)));
  ck('切看法 ⇒ 那几个**差出来的点**上真的多／少了买卖点的墨（只认那两个颜色，看差）',
     diffBoxes.length > 0 && sent.ok && dD.every((d, i) => d >= need(diffBoxes[i].tier)),
     `${diffBoxes.length} 个差出来的点（${diffBoxes.map((b) => b.only).join('/')}）：${oD(nBefore, '切前')}｜${oD(nAfter, '切后')}` +
     `｜差 ${JSON.stringify(dD)}（每个至少 ${diffBoxes.map((b) => need(b.tier)).join('/')}）` +
     `｜顺带记一笔：整屏字节前后${px0.equals(px1) ? '相等' : '不等'}（这句只是旁注，不当判据 —— 它会因为最后一根价签在跳而变）`);
  const dr = (a, b2) => Math.max(Math.abs(a.from - b2.from), Math.abs(a.to - b2.to));
  ck('视口一动没动（切看法不换档）', dr(s0.range, s1.range) < 0.001,
     `${s0.range.from.toFixed(2)}..${s0.range.to.toFixed(2)} → ${s1.range.from.toFixed(2)}..${s1.range.to.toFixed(2)}`);
  ck('档位那套没被踩坏：span 不变、nogain=false（当补数据判会印假话）',
     s1.paging.span === s0.paging.span && s1.paging.nogain === false && s1.paging.measure === 'lines',
     JSON.stringify(s1.paging));
  await c.close();

  // ---- ⑩：?measure=lines 直接打开
  console.log('18–19 ?measure=lines 直接打开');
  const d2 = await open(QS + '&measure=lines');
  const first = d2.reqs.length ? new URL(d2.reqs[0]).searchParams.get('measure') : null;
  const u2 = await ui(d2.p);
  ck('**第一趟**图表请求就带 lines（不是先要缺省再补一趟）', first === 'lines', `第一趟 measure=${first}，共 ${d2.reqs.length} 趟`);
  ck('图脚与选中态都说黄白线', u2.meta.includes('背驰看法 黄白线') && lit(u2) === 'lines');
  await d2.c.close();

  // ---- ⑪：?measure=乱写
  console.log('20–21 ?measure=乱写');
  const d3 = await open(QS + '&measure=bogus');
  const seen = d3.reqs.map((u) => new URL(u).searchParams.get('measure'));
  const u3 = await ui(d3.p);
  ck('名单外的名字一个都不发（发出去后台 400，整张图白挂）', !seen.includes('bogus'), `发出的 measure=${JSON.stringify(seen)}`);
  ck('页面照常画出来、退回缺省那种', (await shape(d3.p)).measure === 'macd' && u3.meta.includes('背驰看法 面积'));
  await d3.c.close();

  // ---- ⑫：旧后台（没有 measures）
  console.log('22–24 旧后台（/api/meta 没有 measures）');
  const d4 = await open(QS, { oldBackend: true });
  const u4 = await ui(d4.p);
  ck('控件不出现（不知道的事不编）', !u4.has);
  ck('请求里一个字都不带 measure（旧后台的查询白名单里没有它，多带一个就是 400）', !d4.opts.sawMeasure,
     d4.opts.sawMeasure || '没带');
  ck('图脚不多那一格', !u4.meta.includes('背驰看法'));
  await d4.c.close();

  // ---- ⑱：「非原文」那枚标（card-6381042d-03f，小栋 2026-10-04 定 ①A：留着，标明）
  //  判据一句话：**标 ⇔ `/api/meta` 的 `measure_orig[看法] === false`**。两半都得量，少一半就有洞：
  //    只量「斜率带标」⇒ 前端写死「斜率那颗挂标」照样绿（那一半是 ㉗ 抓的）；
  //    只量「全是原文就一个标都没有」⇒ 该标的时候没标也照样绿（那一半是 ㉕㉘ 抓的）。
  //  ★ 这一组的**每一格都自带见证**：把「页面上带标的」和「/api/meta 说的非原文」两串都印出来。
  //    光印 ✓ 的话，真后台还没这个字段时那是**死闸**——绿的是「没跑」，不是「没事」。
  console.log('25–29 「非原文」那枚标（谁是原文由 /api/meta 说，前端不许写死）');
  const META4 = ['macd', 'slope', 'lines', 'peak'];
  const fakeMeta = (measures, measure_orig) => ({ symbols: ['ZECUSDT'], tfs: ['15m'], measures, measure_orig });
  // ㉕：真后台。两件事一起判（卡上要的「标记在」＋「默认不变」），因为「默认」那一半跟 ④ 同页同状态。
  const real = await (async () => { try { return await (await fetch(PAGE + 'api/meta')).json(); } catch (e) { return null; } })();
  const said = (real && typeof real.measure_orig === 'object' && real.measure_orig) || null;
  const got = u0.items.filter((i) => i.mark).map((i) => i.id);
  const want = said ? u0.items.filter((i) => said[i.id] === false).map((i) => i.id) : [];
  ck('真后台：带标的那颗 ⇔ /api/meta 的 measure_orig 说它不是原文；且**默认没动**（亮着面积、图脚写面积）',
     JSON.stringify(got) === JSON.stringify(want) && lit(u0) === 'macd' && u0.meta.includes('背驰看法 面积'),
     `页面带标 ${JSON.stringify(got)} ／ meta 说非原文 ${said ? JSON.stringify(want) : '（**后台还没有 measure_orig** ⇒ 这一格要求一个标都没有）'}`
     + ` ｜ 亮着 ${lit(u0)}、图脚…${u0.meta.slice(-16)}`);
  // ㉖：旧形状（字符串列表、**没有** measure_orig）—— 新前端配旧后台就是这个状态，不许凭空冒标。
  const d5 = await open(QS, { meta: { symbols: ['ZECUSDT'], tfs: ['15m'], measures: META4 } });
  const u5 = await ui(d5.p);
  ck('旧后台（有 measures、没有 measure_orig）⇒ 四颗照常、**一个标都没有**（读不到就不编）',
     u5.items.length === 4 && u5.items.every((i) => !i.mark),
     `带了 ${u5.items.length} 颗：${u5.items.map((i) => `${i.id}${i.mark ? '+' + i.mark : ''}`).join(' ')}`);
  await d5.c.close();
  // ㉗：全是原文 —— 牙齿。铁了心「斜率那颗挂标」的话，只有这一格抓得住。
  const d6 = await open(QS, { meta: fakeMeta(META4, { macd: true, slope: true, lines: true, peak: true }) });
  const u6 = await ui(d6.p);
  ck('**四颗全是原文** ⇒ 一个标都不许有（牙齿：写死「斜率那颗带标」在这一格当场红）',
     u6.items.length === 4 && u6.items.every((i) => !i.mark),
     u6.items.map((i) => `${i.id}${i.mark ? '+' + i.mark : ''}`).join(' '));
  await d6.c.close();
  // ㉘：只有斜率非原文 —— 标挂在**该挂的那颗**上，且不污染名字、悬停那句在。
  const d7 = await open(QS, { meta: fakeMeta(META4, { macd: true, slope: false, lines: true, peak: true }) });
  const u7 = await ui(d7.p);
  const slope7 = u7.items.find((i) => i.id === 'slope') || {}, macd7 = u7.items.find((i) => i.id === 'macd') || {};
  ck('只有斜率那颗带标、其余三颗不带，且**名字还是「斜率」**（标不许混进名字里）',
     JSON.stringify(u7.items.map((i) => [i.id, i.mark]))
       === JSON.stringify([['macd', null], ['slope', '非原文'], ['lines', null], ['peak', null]])
     && JSON.stringify(u7.items.map((i) => i.txt)) === JSON.stringify(['面积', '斜率', '黄白线', '峰值']),
     u7.items.map((i) => `${i.id}:${i.txt}${i.mark ? '+' + i.mark : ''}`).join(' '));
  ck('悬停那句话说出来了（「非原文」出现在页面上，就得答得出「那原文是什么」）',
     /非原文/.test(slope7.title || '') && !/非原文/.test(macd7.title || ''),
     `斜率 title=${JSON.stringify(slope7.title)}`);
  await d7.c.close();
  // ㉙：名单换成对象数组 —— **形状变了不许把整组静默抹掉**（Bram 选「旁边挂一张表」正是为了这个）。
  const d8 = await open(QS, { meta: { symbols: ['ZECUSDT'], tfs: ['15m'],
    measures: META4.map((id) => ({ id, orig: id !== 'slope' })) } });
  const u8 = await ui(d8.p);
  ck('名单换成 `[{id, orig}]` ⇒ 四颗照常渲染、标跟着走（这是「空数组 ⇒ 整组消失」那条路的护栏）',
     u8.items.length === 4 && u8.items.filter((i) => i.mark).map((i) => i.id).join() === 'slope',
     u8.has ? u8.items.map((i) => `${i.id}${i.mark ? '+' + i.mark : ''}`).join(' ') : '★ 整组没了 —— 这正是要防的静默消失');
  await d8.c.close();
  // ㉚：后台**多一种量法**（Bram 的 `macd_or_lines`）⇒ 芯片上得是中文名，不许露代号。
  //   ★ 这是「后台加一种看法」这类改动的常态护栏：名字还没跟上的那半天里，屏幕上就是一串英文 id
  //     —— 不报错、也不红，但没人认得出那是什么。断言写成 `名字 !== id`（不是比对某个字面量），
  //     所以**改了名字不算红，漏了名字才红**。
  console.log('30 后台新加的第五种看法：名字跟上了没有');
  const d9 = await open(QS, { meta: fakeMeta(META4.concat(['macd_or_lines']),
    { macd: true, slope: false, lines: true, peak: true, macd_or_lines: true }) });
  const u9 = await ui(d9.p);
  const or9 = u9.items.find((i) => i.id === 'macd_or_lines') || {};
  ck('后台多一种 `macd_or_lines` ⇒ 芯片上是中文名、不是代号，且它按原文**不带**「非原文」的标',
     u9.items.length === 5 && !!or9.txt && or9.txt !== or9.id && !or9.mark,
     u9.items.map((i) => `${i.id}:${i.txt}${i.mark ? '+' + i.mark : ''}`).join(' '));
  await d9.c.close();

  // ───────────────────────────────────────────────────────────────────────────
  // ㉜–㊳ 走势分段那一层（v3 §八，卡 card-c73ab37d-5a1）
  //
  // ★ 为什么落在这套里：这一层**只有真后台给得出** —— `trend` 那个对象是 Bram 在 dbda139 里新加的，
  //   `web_more_e2e.js` 那一套的假后台（仓里的 fixtures）里没有它。这套是唯一一套跑真后台的。
  // ★ 判据一律**跟载荷对、跟 `theme.js` 对**，不跟"我看着像"对：色号和不透明度都从 `/theme.js`
  //   现读（`await import('/theme.js')`），所以哪天有人改 `TREND.bandUp`／`bandDn`，这几格跟着走 ——
  //   写死一个 16% 混出来的色号当准，改一次配色就红一次，红出来的还是假话。
  // ★ 这一层自带一个只读出口 `window.__app.state.trendDrawn`（跟 `state.boxesDrawn` 同性质：
  //   **这一帧**交给这一层的清单，每帧开头重写）—— 画了一条带它上面就有一条。量它，比截图找颜色稳，
  //   红了也说得清错在哪一条。
  console.log('32–38 走势分段那一层：默认开、颜色跟段型走、斜线带铺到载荷说的那根、'
            + '「待定」那条线钉在载荷说的那一根上、关得掉、extend 不炸');
  const TQ = '?symbol=ZECUSDT&tf=15m';
  // 只读出口 ＝ 清单 ＋ **这一帧的视口口径**（每一根该落在哪个像素由工装自己算，不靠页面喂）。
  // 载荷那几件事实一起带回来，**断言的两边都印得出来** —— 后台哪天回了空对象，这几格是红，不是死闸。
  const trendState = (pg) => pg.evaluate(() => {
    const a = window.__app, D = a.state.trendDrawn || {}, T = a.state.data.trend || null;
    const ts = a.chart.timeScale(), bars = a.state.data.bars;
    // ★ 画布宽要跟**画图那把尺**一致：图层画东西用的是 `useMediaCoordinateSpace` 给的 mediaSize
    //   ＝ **主图那一格的画布**，不是 `#chart` 的 clientWidth —— 后者把右轴（还有整个副图）也算进去了。
    //   实测 1440×900 的窗口：`#chart` **1250**、那一格 **1194**（差 56 ＝ 右轴那一条）。
    //   差这 56 px，右边缘那一条上的「在不在屏上」会判反（card-4700b9cc-35e 就是这么假红出来的）。
    const W = (() => { const c = document.querySelector('#chart canvas');
      return c ? c.getBoundingClientRect().width : 0; })();
    // ★ `/1000` 那一除是要紧的：`bars[].t` 是**毫秒**，`timeToCoordinate` 认的是**秒** ——
    //   不除就一直回 null，而 null 会让下面每一条「屏上本来就没东西」的断言**假装通过**。
    //   这一行跟 `layers.js` 的 `viewport()` 里那句 `tOfBar[i] = data.bars[i].t / 1000` 是同一个口径。
    const at = (i) => ({ x: bars[i] ? ts.timeToCoordinate(bars[i].t / 1000) : null });
    const vis = (o) => o.x !== null && o.x >= 0 && o.x <= W;      // 滚出屏幕那几根不量（图层也不画）
    return {
      T, on: a.state.opts.trend, W, url: location.search, hasTrendKey: 'trend' in a.state.data,
      chip: (() => { const c = document.querySelector('.chip[data-key="trend"]');
        return c ? { pressed: c.getAttribute('aria-pressed'), disabled: c.disabled } : null; })(),
      bands: D.bands || [], strips: D.bounds || [], units: D.units || [], labels: D.labels || [],
      // 框编号那一层（㊴）：它记的是**每段有几个中枢**（`n`）和**实际画上去几枚**（`drawn`）。
      // `letters` 从价签那张表里挑出单个字母（这一层的字只有它和「升级」是一两个字的，
      // 而字母一定是 A–H 的单个字符 —— 段号不画，所以不会跟别的字撞）。
      num: D.num || [],
      letters: (D.labels || []).filter((L) => /^[A-H]$/.test(L[4])).map((L) => L[4]).join(''),
      // 小写那一路（card-246fc7cf-a9e）：同一张表里挑小写单字母。★ 大写的正则 `[A-H]` 挑不到它们，
      //   所以上面那格 `letters` 的口径一个字都没变（这一层照样只报大写）。
      lettersLo: (D.labels || []).filter((L) => /^[a-h]$/.test(L[4])).map((L) => L[4]).join(''),
      // ★ 图层画字用的是**主图那一格的画布**尺寸（`useMediaCoordinateSpace` 给的 mediaSize），
      //   不是 `#chart` 的 clientWidth/clientHeight —— 后者连价格轴和副图一起算进去了
      //   （实测 1410×809 vs 那一格 1348×584）。判据要跟画图用**同一把尺**，所以另取一份。
      pane: (() => { const c = document.querySelector('#chart canvas');
        if (!c) return null; const r = c.getBoundingClientRect(); return { w: r.width, h: r.height }; })(),
      segs: (T || {}).segments || [],
      bounds: ((T || {}).bounds || []).map((b) => Object.assign({}, b, at(b.bar))).filter(vis),
      pending: ((T || {}).pending || []).map((b) => Object.assign({}, b, at(b.bar))).filter(vis),
      retracted: ((T || {}).retracted || []).map((b) => Object.assign({}, b, at(b.bar))).filter(vis),
      kinds: [...new Set(((T || {}).bounds || []).map((b) => b.kind))].sort().join(''),
    };
  });
  // 等这一层真的画过一帧（`trendDrawn` 是它写的；层关着 / 载荷没有 trend 时它一直不出现）
  const waitBand = (pg) => pg.waitForFunction(
    () => window.__app.state.trendDrawn && window.__app.state.trendDrawn.bands, null, { timeout: 120000 });

  // ㉜ 默认开（Nova 2026-10-05 17:09Z 定的：这一层就是小栋要看的那个东西）
  const dA = await open(TQ);
  await waitBand(dA.p);
  const A = await trendState(dA.p);
  // ★ 色号和不透明度从 `/theme.js` **现读**，写死一个 16% 混出来的色号当准就是焊在今天的配色上
  //   （★ 从**这一页**读：本套开头那个 `p` 到这儿早就关了，拿它 evaluate 当场炸）。
  const TREND = await dA.p.evaluate(async () => (await import('/theme.js')).TREND);
  ck('走势分段那一层**默认就开着**（不带任何参数打开：开关亮、地址栏里没有 `trend`、真画出带子）',
     A.on === true && !!A.chip && A.chip.pressed === 'true' && !/trend=/.test(A.url)
       && A.bands.length >= 1,
     `开=${A.on}　chip=${JSON.stringify(A.chip)}　带子=${A.bands.length}　地址栏=${A.url || '(空)'}`);

  // ㉝ 颜色跟**段型**走（小栋 10-08 12:35 选 B，卡 card-fedf32aa-59d）：上涨绿、下跌红、盘整（含升级·盘整）灰
  //   ★ 这一格抓两种改法：退回「跟分界点走」（一段从低点起的盘整又会被涂成绿 —— 小栋说「分不开」的那个），
  //     或者把红绿画反。期望色、不透明度都从 /theme.js 现读，不焊死数。
  //   ★★ 牙：默认那一屏不一定有「从低点起的盘整」（那一段在旧规则下是绿、新规则下是灰，是唯一能把两条规则
  //     分开的段）。所以先在载荷里**找一段这样的**，把视口挪过去再量；载荷里一段都没有 ⇒ 这一格红（空转比红坏）。
  //     实测（10-08）：把 layers.js 退回旧规则，这一格红在那一段上。
  const segByI0 = new Map(A.segs.map((s, g) => [s.i0, g]));
  const wantOf = (b) => {
    const g = segByI0.get(b.i0), s = A.segs[g] || {};
    if (g === 0 || s.head) return [TREND.head, TREND.headA];
    if (s.type === '上涨') return [TREND.up, s.live ? TREND.liveUp : TREND.bandUp];
    if (s.type === '下跌') return [TREND.dn, s.live ? TREND.liveDn : TREND.bandDn];
    return [TREND.head, s.live ? TREND.rangeLive : (s.upgraded ? TREND.rangeUpA : TREND.rangeA)];
  };
  const fromLow = (g) => { const s = A.segs[g] || {};
    return g > 0 && !s.head && s.type !== '上涨' && s.type !== '下跌' && (A.T.bounds[g - 1] || {}).kind === 'L'; };
  const gBite = A.segs.findIndex((s, g) => fromLow(g));
  // ★ 另开一页去挪视口：后面几格（㊲ 等）认的是**默认那一屏**，在 dA 上挪了会把它们带红（10-08 实测）。
  let B33 = A.bands;
  if (gBite > 0) {
    const sB = A.segs[gBite];
    const d33 = await open(TQ); await waitBand(d33.p);
    await d33.p.evaluate(([i0, i1]) => window.__app.chart.timeScale().setVisibleLogicalRange({ from: i0 - 50, to: Math.min(i1, i0 + 600) }),
                         [sB.i0, sB.i1]);
    await d33.p.waitForTimeout(1200);
    B33 = (await trendState(d33.p)).bands;
    await d33.c.close();
  }
  const wantBand = B33.map(wantOf);
  const bit = B33.some((b) => fromLow(segByI0.get(b.i0)));
  ck('背景带的颜色跟**段型**走（上涨⇒绿／下跌⇒红／盘整与图头⇒灰，升级·盘整深一档），不再跟分界点的高低走'
     + '（挪到一段**从低点起的盘整**上量：它在旧规则下是绿，现在必须是灰）',
     bit && B33.length >= 1 && wantBand.every((w, i) => w[0] === B33[i].col && Math.abs(w[1] - B33[i].a) < 1e-3),
     `画出来的 ${B33.map((b) => `${b.col}@${b.a}`).join(' ')}　该是 ${wantBand.map((w) => `${w[0]}@${w[1]}`).join(' ')}　`
     + `（屏上段型 ${B33.map((b) => (A.segs[segByI0.get(b.i0)] || {}).type).join('／')}）`
     + (gBite > 0 ? '' : '　★ 载荷里一段「从低点起的盘整」都没有 ⇒ 这一格量不到东西'));

  // ㉞ §八 3 的牙：那条斜线带铺到**载荷说的那一根**（`pullback_end_bar`）为止，不是铺到段末
  //   ★ 有人把 `pullback_end_bar` 换成 `s.i1`（"铺满这一段"读起来更顺）⇒ 当场红。
  //     把载荷那一头也印出来：万一哪天这两个数正好相等，格是绿的但**牙没了**，那得看得见。
  const endOf = new Map(A.T.bounds.map((b) => [b.bar, b.pullback_end_bar]));
  ck('中阴那条斜线带铺在「极值那一根 → 载荷的 `pullback_end_bar`」上（**不是段末**）',
     A.strips.length >= 1 && A.strips.every((s) => endOf.get(s.i0) === s.i1),
     `画了 ${A.strips.length} 条 ${A.strips.map((s) => `${s.i0}>${s.i1}`).join(' ')}　／　`
     + `载荷（屏上）${A.bounds.map((b) => `${b.bar}>${b.pullback_end_bar}`).join(' ')}`);

  // ㉟ 分界那枚价格的横心钉在极值那一根上（字跟着点走，不是随便摆的）
  const mid = (L) => (L[0] + L[2]) / 2;
  const pinned = A.bounds.filter((b) => A.labels.some((L) =>
    Math.abs(mid(L) - b.x) <= 1.5 && Math.abs(parseFloat(L[4]) - b.price) < 0.01));
  ck('分界的价格字钉在极值那一根上（横心 == `timeToCoordinate(那一根)` ±1.5px，读数就是那个价）',
     A.bounds.length >= 1 && pinned.length === A.bounds.length,
     `对上 ${pinned.length}/${A.bounds.length}　屏上那几个极值：${A.bounds.map((b) => b.price).join(' ')}`);

  // ㊱ 「待定」和「撤回」是两件事（候选换了 vs 刀撤回了），两句话得分开写、各配各的条数
  const pendLbl = A.labels.filter((L) => /待定$/.test(L[4])).map((L) => L[4]);
  const retrLbl = A.labels.filter((L) => /撤回$/.test(L[4])).map((L) => L[4]);
  ck('「待定」和「撤回」各写各的（屏上各有几枚 ⇒ 载荷里各有几条），不混用一个词',
     pendLbl.length === A.pending.length && retrLbl.length === A.retracted.length,
     `载荷 待定 ${A.pending.length} ／ 撤回 ${A.retracted.length}　屏上 待定 ${pendLbl.length}`
     + ` ／ 撤回 ${retrLbl.length}　${JSON.stringify([...pendLbl, ...retrLbl])}`);

  // ㊱b 那条「待定」的灰点线**钉在载荷说的那一根上**（2026-10-06 补，卡 card-3edd7fb3-412）
  //   ★ 为什么补这一格：退掉「先看切后」那套画法的时候，ghost ⑰e 跟着退了 —— 它当时量的正是
  //     "那一刀画在 `cut_bar` 那一根上"。**位置守卫不能跟着退休**：v3 自己那条 `trend.pending`
  //     灰点线接住了「待定」这件事（见 `layers.js` 的 `trendMarkView` ②），它要是画歪了、或者哪天
  //     有人动了那个换算，屏上那条线就指着**另一根 K 线** —— 而画面看起来**完全正常**。
  //     这正是"掉牙"那种坏法：格子还绿着，量的东西早没了。所以这一格量的是**画布上的像素**。
  //   ★ 认的是**那一条线**，不是"某处有条竖线"，三层一起认：
  //     ① 这一列上的墨要比左右各 2px 都亮（局部对比 —— 蜡烛边也亮，所以光有这条不够）；
  //     ② 墨的**点划周期** == `/theme.js` 的 `DASH.trendCand`（`[2,4]` ⇒ 6px）。同屏另外两条竖线是
  //        `trendEdge`（7px）和 `trendBack`（4px），三个周期互不相同 ⇒ 认不错；
  //     ③ 墨的占比够大、段数够多（一条贯穿整屏的点线有八十来段，蜡烛那点边凑不出这个形状）。
  //   ★ 容差 ±1px：线画出来占两列（round 之后），且 `timeToCoordinate` 给的是小数，四舍五入差 1 是正常的。
  //   ★ 牙齿（交这一卡时手验过，工装不会自己去改页面）：把 `trendMarkView` ② 里那个 x 的换算挪 5 根，
  //     这条线跟着挪 5 根 ⇒ 本格当场红（5 根远超出 ±1px）。
  const DASH = await dA.p.evaluate(async () => (await import('/theme.js')).DASH);
  const CAND_P = (DASH.trendCand || []).reduce((a, b) => a + b, 0);      // 点划一个周期的长度
  // 在 `X ± win` 这几列里找「待定那条点线」的形状。返回：认出来的那几列（相对 X 的偏移）＋ 全窗口的读数。
  const candCols = (pg, X, win) => pg.evaluate(([X, win, P]) => {
    const c0 = document.querySelector('#chart canvas'), r0 = c0.getBoundingClientRect();
    const one = (Xc) => {
      let best = null;
      for (const c of document.querySelectorAll('#chart canvas')) {
        const r = c.getBoundingClientRect(), sx = c.width / r.width;
        const cx = Math.round((Xc - (r.left - r0.left)) * sx);
        if (cx < 8 || cx + 8 >= c.width) continue;
        let img;
        try { img = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; } catch (e) { continue; }
        const lum = (x, y) => { const i = (y * c.width + x) * 4; return img[i] + img[i + 1] + img[i + 2]; };
        const off = Math.max(2, Math.round(2 * sx));
        const ink = new Uint8Array(c.height);
        for (let y = 0; y < c.height; y++) {
          const L = lum(cx, y);
          ink[y] = (L - lum(cx - off, y) > 90 && L - lum(cx + off, y) > 90) ? 1 : 0;
        }
        const runs = [];
        for (let y = 0; y < ink.length; ) {
          if (!ink[y]) { y++; continue; }
          const s0 = y; while (y < ink.length && ink[y]) y++;
          runs.push([s0, y - s0]);
        }
        const gaps = runs.slice(1).map((q, i) => q[0] - runs[i][0]).sort((p, q) => p - q);
        const s = { frac: runs.reduce((k, q) => k + q[1], 0) / ink.length,
                    gap: gaps.length ? gaps[gaps.length >> 1] / sx : 0, runs: runs.length };
        if (!best || s.frac > best.frac) best = s;
      }
      return best;
    };
    const hits = [], all = [];
    for (let d = -win; d <= win; d++) {
      const s = one(X + d);
      all.push({ d, frac: s ? +s.frac.toFixed(3) : null, gap: s ? +s.gap.toFixed(1) : null,
                 runs: s ? s.runs : null });
      if (s && s.frac >= 0.25 && s.runs >= 20 && Math.abs(s.gap - P) <= 1) hits.push(d);
    }
    return { hits, all };
  }, [X, win, CAND_P]);
  const CG = [];
  for (const p of A.pending) CG.push(Object.assign({ bar: p.bar, x: Math.round(p.x) },
    await candCols(dA.p, Math.round(p.x), 8)));
  const topOf = (g) => g.all.reduce((a, b) => ((b.frac || 0) > (a.frac || 0) ? b : a));
  ck(`那条「待定」的灰点线**钉在载荷说的那一根上**（认形状：点划周期 == \`DASH.trendCand\` ＝ ${CAND_P}px）`
     + '—— 屏上每一根「待定」都得在**它自己那个 x** 上认得出这条线，而且窗口里别处不许认出来',
     A.pending.length >= 1 && CG.every((g) => g.hits.length >= 1 && g.hits.every((d) => Math.abs(d) <= 1)),
     // ★ 载荷里一根「待定」都没有 ⇒ 这一格**什么都没量到**，红着让人来看，不是绿（假绿比红坏）。
     (A.T.pending || []).length === 0
       ? '★ 载荷里一根「待定」都没有 ⇒ 这一格是**空的**'
       : (A.pending.length === 0 ? '★ 载荷有「待定」，但一根都不在屏上 ⇒ 这一格是**空的**' : '')
         + CG.map((g) => `bar=${g.bar} 载荷 x=${g.x}｜认出来的列 `
             + (g.hits.length ? JSON.stringify(g.hits) : '★ 一列都没有')
             + `（${g.all.length} 列里占比最高的是 x${topOf(g).d >= 0 ? '+' : ''}${topOf(g).d}：`
             + `占比 ${topOf(g).frac}／周期 ${topOf(g).gap}／段数 ${topOf(g).runs}）`).join('；'));

  // ㊲ 关得掉 ＋ **那个色真的画到屏幕上了**
  //   ★ 「这一层真画了没有」数的是**它自己那个色**的像素：16% 的绿铺在近黑上，混出来是什么色
  //     是算得出来的（色号 α 都从 /theme.js 现读）。**不**用"前后两张截图不等"当判据 ——
  //     那个会拿"最后一根的价签在跳"当替身，这套工装的 ⑦⑰ 两条账上都吃过这个亏（见文件头）。
  const blend = (hex, a, bg = [16, 18, 24]) =>
    hex2rgb(hex).map((v, i) => Math.round(bg[i] + (v - bg[i]) * a));
  const bandPixels = (pg, want) => pg.evaluate(([want, tol]) => {
    const near = (a, b) => Math.abs(a - b) <= tol;
    let n = 0;
    for (const c of document.querySelectorAll('#chart canvas')) {
      const w = c.width, h = c.height, px = c.getContext('2d').getImageData(0, 0, w, h).data;
      for (let y = 0; y < h; y += 2) for (let x = 0; x < w; x += 2) {      // 抽稀：铺满整格的带子抽不没
        const i = (y * w + x) * 4;
        if (px[i + 3] > 250
            && near(px[i], want[0]) && near(px[i + 1], want[1]) && near(px[i + 2], want[2])) n++;
      }
    }
    return n;
  }, [want, 6]);
  // ★ 10-08 起底色跟段型走：默认窗口里不一定有上涨段（最新那段常是盘整，灰）。所以数的是**屏上最宽那条带**
  //   自己的色（色号、不透明度都从 trendDrawn 读，trendDrawn 又是从 /theme.js 来的），不焊死绿。
  const widest = A.bands.slice().sort((x, y) => (y.i1 - y.i0) - (x.i1 - x.i0))[0] || { col: TREND.up, a: TREND.bandUp };
  const upGreen = blend(widest.col, widest.a);
  const dOff = await open(TQ + '&trend=0');
  const OFF = await trendState(dOff.p);
  const nOn = await bandPixels(dA.p, upGreen), nOff = await bandPixels(dOff.p, upGreen);
  ck('`?trend=0` 关得掉：开关灭、地址栏留着 `trend=0`（可分享）、一条带不画、**那个色的像素清零**',
     OFF.on === false && !!OFF.chip && OFF.chip.pressed === 'false' && /trend=0/.test(OFF.url)
       && OFF.bands.length === 0 && nOn >= 5000 && nOff <= 50,
     `开=${OFF.on}　带子=${OFF.bands.length}　地址栏=${OFF.url}　带子像素：开 ${nOn} ／ 关 ${nOff}`
     + `（数的是屏上最宽那条带的色 ${widest.col}@${widest.a} ⇒ ${JSON.stringify(upGreen)} ±6）`);
  await dOff.c.close();

  // ㊳ `cut=extend` 那档：载荷**连 `trend` 这个键都没有** ⇒ 开着也画不出东西
  //   ★ 牙齿：把置灰那半句删掉 ⇒ 屏上会留一颗"点了没反应"的开关（这一套 ⑮ 那条账的同一个道理）。
  const dE = await open(TQ + '&cut=extend');
  const E = await trendState(dE.p);
  ck('`cut=extend` 那档：载荷没有 `trend` 键 ⇒ 那颗开关**按灰**、一条带子都不画、图照常画',
     E.hasTrendKey === false && !!E.chip && E.chip.disabled === true
       && E.on === true && E.bands.length === 0,
     `有 trend 键=${E.hasTrendKey}　chip=${JSON.stringify(E.chip)}　带子=${E.bands.length}`);
  await dE.c.close();

  // ㊴ 框编号那一层（§八 6，卡 card-c6644f52-2fa）：**默认关**、开关指名才开、字母挂哪一级听载荷的
  //   ★ 这一格真正的牙是**读法**：`trend_reading` 说 A 就挂合成出来的高一级中枢（`units`）、
  //     说 B 就一律挂本级别（`seg_centers`）。把读法**写死**（或两边画反）⇒ 当场红。
  //     **两边都算出来**：哪天的数据上 A 和 B 恰好一样，格还是绿的但牙没了 —— 那得看得见（跟 ㉞ 同一条账）。
  console.log('\n39–42 框编号那一层：默认关、指名才开、字母挂哪一级听 `trend_reading` 的、钉在中枢自己的中心');
  // 期望值在**页内**算：坐标一律问这一页自己的换算（`timeToCoordinate` / `priceToCoordinate`），
  // 工装自己不推 —— 推的那套迟早跟图上错开半格，然后红出来的是一句假话。
  const numExpect = (pg, rd) => pg.evaluate((force) => {
    const a = window.__app, d = a.state.data, T = d.trend;
    const ts = a.chart.timeScale(), bars = d.bars, LET = 'ABCDEFGH';
    const reading = force || (d.trend_reading === 'B' ? 'B' : 'A');
    const per = [], boxes = [];
    for (let i = 0; i < T.segments.length; i++) {
      const s = T.segments[i];
      const zs = ((reading === 'A' && s.upgraded) ? T.units : d.seg_centers).filter((z) => z.seg === i);
      per.push(zs.length);
      zs.slice(0, LET.length).forEach((z, k) => {
        const lo = z.ZD !== undefined ? z.ZD : z.DD, hi = z.ZG !== undefined ? z.ZG : z.GG;
        const bar = bars[Math.round((z.X0 + z.X1) / 2)];
        boxes.push({ i, ch: LET[k], x: bar ? ts.timeToCoordinate(bar.t / 1000) : null,
          y: a.state.candleSeries.priceToCoordinate((lo + hi) / 2) });
      });
    }
    return { reading, payloadReading: d.trend_reading, per, boxes };
  }, rd || null);
  const midX = (L) => (L[0] + L[2]) / 2;
  const dN = await open(TQ + '&trendnum=1');
  await waitBand(dN.p);
  const N = await trendState(dN.p);
  const expN = await numExpect(dN.p), expB = await numExpect(dN.p, 'B');
  const nChip = await dN.p.evaluate(() => {
    const c = document.querySelector('.chip[data-key="trendNum"]');
    return c ? { pressed: c.getAttribute('aria-pressed'), disabled: c.disabled } : null;
  });
  ck('框编号那一层：`?trendnum=1` 开了它就画（开关亮、地址栏留着参数、真画出字母）',
     !!nChip && nChip.pressed === 'true' && nChip.disabled === false
       && /trendnum=1/.test(N.url) && N.letters.length >= 1 && N.num.length >= 1,
     `chip=${JSON.stringify(nChip)}　地址栏=${N.url}　屏上字母「${N.letters}」　`
     + `每段（载荷 ${expN.reading}）：${JSON.stringify(N.num.map((r) => r.n))}`);

  // ★★ 这一格是这张卡的牙：**每一段的中枢数按 `trend_reading` 算出来，跟层里记的逐段比**
  const same = (x, y) => x.length === y.length && x.every((v, i) => v === y[i]);
  const abSame = same(expN.per, expB.per);
  ck('字母挂哪一级**听载荷的 `trend_reading`**（A⇒升级段挂 `units`／B⇒挂本级别）：每段的中枢数逐段对上',
     N.num.length >= 1 && same(N.num.map((r) => r.n), expN.per),
     `载荷说 ${expN.reading}（原始值 ${expN.payloadReading}）　该是 ${JSON.stringify(expN.per)}　`
     + `层里是 ${JSON.stringify(N.num.map((r) => r.n))}　`
     + `★ 另一种读法（${expN.reading === 'A' ? 'B' : 'A'}）在这份数据上是 ${JSON.stringify(expN.reading === 'A' ? expB.per : expN.per)}`
     + `　⇒ ${abSame ? '两种读法在这份数据上**恰好一样，这一格的牙现在是空的**（得换一份数据）'
       : '两种读法在这份数据上**确实不一样，牙是实的**'}`);

  // ㊴b 小写 a、b、c（card-246fc7cf-a9e）：**每段小写个数 ＝ 框数 ＋ 1**；框数 0 的段 ⇒ **0 个**
  //     （0 个框没有"框之间"，也没有"进第一个框之前" ⇒ 硬标一个 a 会跟 a 的定义打架。编者口径，已进 spec）
  //     ★ 比的是**该画几个**（`nlo`），不是"画上去几个"：读法 A 下字母会整枚落到屏外，那一层不画它
  //       （见 ㊼）⇒ 拿 `drawnLo` 去比会在那些段上假红。
  const expLo = expN.per.map((n) => (n === 0 ? 0 : n + 1));
  ck('小写那一层：**每段小写个数 ＝ 框数 ＋ 1**（逐段对 `nlo`），0 框的段是 0 个',
     N.num.length >= 1 && same(N.num.map((r) => r.nlo), expLo),
     `载荷（${expN.reading}）每段框数 ${JSON.stringify(expN.per)} ⇒ 该画小写 ${JSON.stringify(expLo)}　`
     + `层里 nlo＝${JSON.stringify(N.num.map((r) => r.nlo))}　实际画上去 ${JSON.stringify(N.num.map((r) => r.drawnLo))}`
     + `　★ 后两个数不一样是**正常的**（整枚落在屏外的那几枚不画）`);

  // ㊴c ★★ 卡上点名的那条硬判据：**大小写不许叠**（缺口极短时小写往外让）。
  //     ★ 这条之所以能做成硬量：`haloText` 返回的就是**矩形** `[x0,y0,x1,y1,字]`，
  //       大小写进的是同一张 `trendDrawn.labels` ⇒ 直接两两做矩形相交，不用看图、不用另算几何。
  //     ★★ 牙在哪儿：`movedLo` 记的是"真的让过位的枚数"。这份数据上一次都没让过位的话，
  //       这一格的绿只是"没有极短缺口"的绿 —— 让位那半没验到。所以报告里必须把这个数说出来。
  const upR = N.labels.filter((L) => /^[A-H]$/.test(L[4]));
  const loR = N.labels.filter((L) => /^[a-h]$/.test(L[4]));
  const hits = [];
  for (const a of upR) for (const b of loR) {
    if (a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3]) hits.push(`${a[4]}×${b[4]}`);
  }
  const moved = N.num.reduce((t, r) => t + (r.movedLo || 0), 0);
  ck('**大小写不叠**（缺口极短时小写往外让）：大写那组与小写那组矩形两两不相交',
     loR.length >= 1 && upR.length >= 1 && hits.length === 0,
     `屏上小写「${N.lettersLo}」／大写「${N.letters}」　相交 ${hits.length} 对 ${hits.slice(0, 6).join('／')}　`
     + `★ 让位次数 ${moved} ⇒ ${moved === 0
       ? '**这份数据上一次都没走到让位那条路**，这一格的绿是"没遇到极短缺口"的绿 —— 让位那半的牙是空的，得换数据／缩 span 才咬得到'
       : '让位那条路真的走到了，这一格的牙是实的'}`);

  // ㊴d 小写的账**要算得平**：`nlo` ≡ 画出来 ＋ x 出屏 ＋ y 出屏 ＋ 字母表不够用
  //     （跟 ⑧ 那栏「挑了几根才凑够」是同一条账：循环里每一枚要么画、要么撞上某一栏跳过，没有第三条路）。
  const bal = N.num.filter((r) => r.nlo !== r.drawnLo + r.offXLo + r.offYLo + r.overLo);
  ck('小写的账**算得平**：每段 `nlo` ＝ 画出来 ＋ x 出屏 ＋ y 出屏 ＋ over（没有第三条路）',
     N.num.length >= 1 && bal.length === 0,
     `不平的段 ${bal.length} 个${bal.length ? `：${JSON.stringify(bal.slice(0, 3))}` : ''}　`
     + `逐段 [nlo, 画, x屏外, y屏外, over]＝${JSON.stringify(N.num.map((r) => [r.nlo, r.drawnLo, r.offXLo, r.offYLo, r.overLo]))}`);

  // ㊴e 画上去的小写**都在屏内**（沿用 ㊼：落点看不见就不画，不夹回画布）
  const paneW = (N.pane || {}).w || 0, paneH = (N.pane || {}).h || 0;
  const outLo = loR.filter((L) => L[0] < 0 || L[2] > paneW || L[1] < 0 || L[3] > paneH);
  ck('小写字母也**不许出屏**（x、y 都要在屏上；不夹回画布假装它在那儿）',
     loR.length >= 1 && outLo.length === 0,
     `屏上小写 ${loR.length} 枚、出屏 ${outLo.length} 枚　那一格 ${Math.round(paneW)}×${Math.round(paneH)}`
     + (outLo.length ? `　出界：${outLo.map((L) => `${L[4]}(${[L[0], L[1], L[2], L[3]].map(Math.round).join(',')})`).join('　')}` : ''));

  // ㊴f ★ 「让位那条路」**到底有没有牙**：默认那一屏上 `movedLo` 是 0 ⇒ 上面 ㊴c 的绿只是"没遇到极短缺口"的绿。
  //     这里换**很多个视口**再问同一个硬判据（大小写矩形两两不相交），并把让位被走到几次**照实印出来**：
  //     120 根（贴脸放大）→ 2600 根（这一页缩到底，`barSpacing` 已压到它自己的下界 0.5）。
  //     尾巴、腰上各扫一遍，扫完把视口**放回原样**（后面的 ㊶ 还要用这一页）。
  //     ★ 跟 54 那格同一个形状、同一条账：走不到就把次数印出来 —— 不拿"没遇到"当"验过了"。
  const r0 = await dN.p.evaluate(() => window.__app.chart.timeScale().getVisibleLogicalRange());
  const swp = await dN.p.evaluate(async ({ spans }) => {
    const a = window.__app, st = a.state, ts = a.chart.timeScale(), n = st.data.bars.length;
    const frame = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    const rows = [];
    for (const span of spans) for (const to of [n, Math.round(n * 0.5)]) {
      ts.setVisibleLogicalRange({ from: to - span, to });
      await frame(); await frame();
      const D = st.trendDrawn || {};
      const up = (D.labels || []).filter((L) => /^[A-H]$/.test(L[4]));
      const lo = (D.labels || []).filter((L) => /^[a-h]$/.test(L[4]));
      let hits = 0;
      for (const u of up) for (const l of lo) {
        if (u[0] < l[2] && l[0] < u[2] && u[1] < l[3] && l[1] < u[3]) hits++;
      }
      const num = D.num || [];
      rows.push({ span, to, up: up.length, lo: lo.length, hits,
        moved: num.reduce((t, r) => t + (r.movedLo || 0), 0),
        nlo: num.reduce((t, r) => t + (r.nlo || 0), 0),
        drawn: num.reduce((t, r) => t + (r.drawnLo || 0), 0) });
    }
    return rows;
  }, { spans: [120, 300, 600, 1200, 2000, 2600] });
  await dN.p.evaluate((r) => window.__app.chart.timeScale().setVisibleLogicalRange(r), r0);
  await dN.p.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
  const swBad = swp.filter((x) => x.hits > 0);
  const swBoth = swp.filter((x) => x.up >= 1 && x.lo >= 1);
  const swMoved = swp.reduce((t, x) => t + x.moved, 0);
  ck('缩放到**很多个视口**（120→2600 根，尾巴和腰上各一遍）大小写仍然不叠',
     swBoth.length >= 2 && swBad.length === 0,
     `扫 ${swp.length} 个视口，其中**大小写同时在屏上**（这一格才比得出东西）的 ${swBoth.length} 个　`
     + `有叠的 ${swBad.length} 个${swBad.length ? `：${JSON.stringify(swBad.slice(0, 3))}` : ''}　让位合计 ${swMoved} 次　`
     + `每格 [span, 大写, 小写, 叠, 让位, nlo, 画出]＝${JSON.stringify(swp.map((x) => [x.span, x.up, x.lo, x.hits, x.moved, x.nlo, x.drawn]))}　`
     + `★ ${swMoved === 0
       ? '让位那条路**这些视口上一次都没走到**（缺口都不算"极短"）⇒ 这一格验到的是"不叠"这条性质在多视口下成立，**让位分支本身仍是没走到的路**'
       : '让位那条路真的走到了，这一格的牙是实的'}`);

  // ㊶ **钉在枢自己的范围中心**（不是段的左上角 —— 那是「升级」二字的锚法）
  //   牙齿：把锚改成 `s.i0`（"标在段头上"读起来很顺）⇒ 当场红。
  //   ★ 默认视口只开在**尾巴那 ~2683 根**上 ⇒ 第一次跑只量到 **1 枚**字母，那格的绿是"一枚样本的绿"。
  //     而且**一屏装不下全部**：这份载荷上 7 枚字母散在 20160 根里，一屏最多装得下 2 枚
  //     （§4 那两枚，差 582 根）—— 这是视口封顶算出来的，不是这一层的问题。
  //   ⇒ 不摆"一屏"，摆**若干屏**：按 2000 根一簇把字母分组，每簇开一页、把那一簇里的每一枚都量到。
  //     页子自己的口子（`?at=&span=`，app.js:637；外部的 fitContent 在这页上是白调的，实测过）。
  const clusters = await dN.p.evaluate(() => {
    const a = window.__app, d = a.state.data, T = d.trend;
    const reading = d.trend_reading === 'B' ? 'B' : 'A';
    const mids = [];
    for (let i = 0; i < T.segments.length; i++) {
      const s = T.segments[i];
      for (const z of ((reading === 'A' && s.upgraded) ? T.units : d.seg_centers).filter((q) => q.seg === i)) {
        mids.push(Math.round((z.X0 + z.X1) / 2));
      }
    }
    mids.sort((x, y) => x - y);
    const W = 2000, PAD = 480, out = [];   // 簇宽＋两边各 240 根（PAD）≤ 2480 < 15m 一屏封顶；120 根的边在读法 B（22 枚）下会把簇最左那枚挤出屏（x<−8）
    for (let i = 0; i < mids.length;) {
      let j = i;
      while (j + 1 < mids.length && mids[j + 1] - mids[i] <= W) j++;
      out.push({ at: Math.round((mids[i] + mids[j]) / 2), span: Math.max(PAD, mids[j] - mids[i] + PAD) });
      i = j + 1;
    }
    return { n: mids.length, out };
  });
  const pin = { want: clusters.n, got: 0, hits: 0, pages: clusters.out.length, offY: 0, offY_B: 0 };
  for (const w of clusters.out) {
    const dw = await open(`${TQ}&trendnum=1&at=${w.at}&span=${w.span}`);
    await waitBand(dw.p);
    const W_ = await trendState(dw.p);
    const expW = await numExpect(dw.p);
    const pane = W_.pane || { w: W_.W, h: 1e6 };
    // 跟图层同一个判据：**x 和 y 都得在那一格里**（pad 8，见 layers.js 那两行）
    const onW = expW.boxes.filter((b) => b.x !== null && b.y !== null
      && b.x >= -8 && b.x <= pane.w + 8 && b.y >= -8 && b.y <= pane.h + 8);
    // ★ 「横着在屏上、纵着出去了」—— 读法 A 下真的会发生（高一级中枢的价格中点跑到视野外）。
    //   这一格**要把它数出来**：不然它长得跟"这一段本来就没字母"一模一样，红都红不出来。
    const winOff = (boxes) => boxes.filter((b) => b.x !== null && b.x >= -8 && b.x <= pane.w + 8
      && (b.y === null || b.y < -8 || b.y > pane.h + 8)).length;
    pin.offY += winOff(expW.boxes);
    // ★★ **把「B 会怎样」也算出来**（只是算，不是画 —— 画哪种由后台的 `trend_reading` 定）。
    //    不然"读法 A 的锚点太大所以画不出来"就只是我一句推测。同一个窗口、同一套换算，两边各数一遍。
    pin.offY_B += winOff((await numExpect(dw.p, 'B')).boxes);
    pin.got += onW.length;
    pin.hits += onW.filter((b) => W_.letters.includes(b.ch)
      && W_.labels.some((L) => L[4] === b.ch && Math.abs(midX(L) - b.x) <= 1.5)).length;
    await dw.c.close();
  }
  ck('每枚字母钉在**它说的那个中枢**的横向中心（`(X0+X1)/2` 那一根的 x，±1.5px）：逐枚都量到',
     pin.want >= 1 && pin.got === pin.want - pin.offY && pin.hits === pin.got,
     `载荷里 ${pin.want} 枚字母，分 ${pin.pages} 屏摆完（一屏封顶装不下全部，见上面那段账）　`
     + `量到 ${pin.got} 枚，对上 ${pin.hits} 枚　`
     + `★ 另有 ${pin.offY}/${pin.want} 枚**横向在屏上、但落点的价在视野外** ⇒ 按这一层的规矩不画（不夹回画布）　`
     + `★★ 同样的窗口**照读法 B 算一遍**：只有 ${pin.offY_B}/${pin.want} 枚会落出视野`
     + `（B 的锚是本级别中枢，价格带就在眼前；A 的锚是横跨几千根的高一级中枢 —— 这是**算出来的**，不是推的）　`
     + `（默认视口下屏上只有 ${N.letters.length} 枚，那点样本不作准）`);

  // ㊷ **默认关** ＋ 走势那层关掉时它按灰（能点却画不出东西的开关是骗人的）
  const dN0 = await open(TQ);
  await waitBand(dN0.p);
  const N0 = await trendState(dN0.p);
  const n0Chip = await dN0.p.evaluate(() => {
    const c = document.querySelector('.chip[data-key="trendNum"]');
    return c ? { pressed: c.getAttribute('aria-pressed'), disabled: c.disabled } : null;
  });
  const dNT = await open(TQ + '&trendnum=1&trend=0');
  const NT = await trendState(dNT.p);
  const ntChip = await dNT.p.evaluate(() => {
    const c = document.querySelector('.chip[data-key="trendNum"]');
    return c ? { pressed: c.getAttribute('aria-pressed'), disabled: c.disabled } : null;
  });
  ck('框编号**默认关**（不带参数：开关灭、地址栏没有它、一枚字母都不画）；`trend=0` 时那颗开关**按灰**',
     !!n0Chip && n0Chip.pressed === 'false' && !/trendnum/.test(N0.url)
       && N0.letters.length === 0 && N0.num.length === 0
       && !!ntChip && ntChip.disabled === true && NT.letters.length === 0,
     `默认：chip=${JSON.stringify(n0Chip)}　地址栏=${N0.url || '(空)'}　字母「${N0.letters}」　`
     + `／ 把走势那层关掉（trend=0）：chip=${JSON.stringify(ntChip)}　字母「${NT.letters}」`);
  await dN0.c.close(); await dNT.c.close(); await dN.c.close();
  await dA.c.close();

  // ───────────────────────────────────────────────────────────────────────────
  // ㊸–㊽ **合成出来的高一级框**归哪颗开关、按级别上什么色、「升级」二字钉在哪
  //        （v3 §八 5，卡 card-113a3b16-026，小栋 10-05 23:3xZ 定）
  //
  // ★ 这张卡的三件事：①合成框（载荷的 `T.units`）从「走势分段」挪到**「高一级」**底下 ——
  //   它跟框层那批"满 9 段"升上来的框**是同一件事**（都是"高一级"），所以跟着那颗芯片、默认不画；
  //   ②框**按级别上色**，三处调用共用一个 `upColor(tier)`（分头写的话，哪天改配色就会改漏一处，
  //   而漏掉的那处**不会红** —— 所以这一格量的是"画上去的那个色"跟 `/theme.js` 对得上）；
  //   ③段头那两个字**挪到框上、跟着框走**。老代码把它夹在 `Math.max(x, 4) + 6` 上：
  //   框一宽、左沿一滚出屏幕，那两个字就**钉死在视口左上角不动了** —— 小栋看见的就是这个。
  //
  // ★ 视口**不写死下标**（数据是活的 210 天，写死迟早指着空处）：先开一页读载荷，挑一个合成框，
  //   把它的**左沿摆在屏内左边**，再把视口往右推四档（框就在屏上往左走，最后一档把它推出屏）——
  //   "字跟着框走"和"左沿出屏就不画"这两半都得量到。
  // ★ 色号从 `/theme.js` 现读（跟 ㉜–㊳ 同一条账），画上去的色从 `trendDrawn.units[].col` 现读
  //   （那一格是画的时候顺手记的），**两边都印出来** —— 不然改了配色这格就成死闸。
  console.log('\n43–48 合成大框：跟着「高一级」开关走、按级别上色、「升级」二字钉在框上（不是视口左上角）');
  const upState = (pg) => pg.evaluate(() => {
    const a = window.__app, st = a.state, D = st.trendDrawn || {};
    const ts = a.chart.timeScale(), bars = st.data.bars;
    const r1 = (x) => (x === null || x === undefined ? null : Math.round(x * 10) / 10);
    const px = (i) => { const b = bars[i]; const x = b ? ts.timeToCoordinate(b.t / 1000) : null; return x === null ? null : r1(x); };
    const c = document.querySelector('#chart canvas');
    const pane = c ? { w: c.getBoundingClientRect().width, h: c.getBoundingClientRect().height } : { w: 0, h: 0 };
    const T = st.data.trend || {};
    return {
      // ★ `W` 也换成 mediaSize 那把尺（＝下面 `want` 用的 `pane.w`）：原先这里写的是 `#chart` 的
      //   clientWidth（1250 vs 1194），虽然这一行只是印出来给人看、没进判据，但留着**一把错的尺**
      //   迟早被人拿去用（card-4700b9cc-35e 就是这么假红出来的）。
      up: st.opts.up, trend: st.opts.trend, W: Math.round(pane.w),
      chip: (() => { const k = document.querySelector('.chip[data-key="up"]');
        return k ? { pressed: k.getAttribute('aria-pressed'), disabled: k.disabled } : null; })(),
      bands: (D.bands || []).length,
      // 载荷里**本该画上去**的那些：跟 layers.js 同一个判据（`x1 < 0 || x0 > W` 就跳过，
      // `W` 用的是 mediaSize —— 也就是这一格的画布，不是 `#chart`）。
      want: (T.units || []).map((u) => ({ seg: u.seg, n: u.n, X0: u.X0, X1: u.X1, x0: px(u.X0), x1: px(u.X1) }))
        .filter((u) => u.x0 !== null && u.x1 !== null && !(u.x1 < 0 || u.x0 > pane.w)).length,
      // 这一帧**真画上去**的（只读出口）：像素区间是工装拿页面自己的换算折的，不是页面喂的。
      got: (D.units || []).map((u) => ({ seg: u.seg, n: u.n, col: u.col,
        x0: px(u.X0), x1: px(u.X1), yt: (() => { const s = st.candleSeries; const y = s ? s.priceToCoordinate(u.GG) : null; return r1(y); })(),
        yb: (() => { const s = st.candleSeries; const y = s ? s.priceToCoordinate(u.DD) : null; return r1(y); })() })),
      upLabels: (D.labels || []).filter((L) => L[4] === '升级').map((L) => ({ x: r1(L[0]), y: r1(L[1]), col: L[5] })),
      pane,
    };
  });

  const dU = await open(TQ);
  await waitBand(dU.p);
  const US0 = await upState(dU.p);                       // 默认那一档：「高一级」没勾
  const upChip0 = US0.chip;
  // ★ 级别色在 `theme.js` 的 **`CHART`** 那一段（`up_pen` 淡紫／`up_seg` 品红），**不在 `TREND` 里** ——
  //   这一层虽然画的是走势那层的东西，取色走的却是框层那套（它俩本来就是一回事）。读错了当场红成假话。
  const UCHART = await dU.p.evaluate(async () => (await import('/theme.js')).CHART);
  const pick = await dU.p.evaluate(() => {
    const us = ((window.__app.state.data.trend || {}).units) || [];
    if (!us.length) return null;
    // 挑**最靠后**的那一个：它离视口右沿近，屏幕上一开就能看见（前面那些老框的像素 x 是负的）。
    const u = us[us.length - 1];
    return { X0: u.X0, X1: u.X1, seg: u.seg, n: u.n };
  });
  await dU.c.close();

  ck('合成大框**默认不画**（「高一级」没勾 ⇒ 一个框、一个「升级」字都没有），但走势那一层照常画',
     !!upChip0 && upChip0.pressed === 'false' && US0.got.length === 0 && US0.upLabels.length === 0
       && US0.bands > 0,
     `载荷里这一屏也该画 ${US0.want} 个框　「高一级」chip=${JSON.stringify(upChip0)}　`
     + `画上去 ${US0.got.length} 个框／${US0.upLabels.length} 个字　背景带 ${US0.bands} 条`
     + `（带子是 0 就说明整层没画，不是开关的功劳）`);

  // 把那个框的左沿摆在屏内左边，再把视口往右推四档（最后一档要把它推出屏去）。
  const SWEEP = pick ? [150, 230, 310, 400].map((d) => ({ at: pick.X0 + d, span: 600 })) : [];
  const pages = [];
  for (const w of SWEEP) {
    const dw = await open(`${TQ}&at=${w.at}&span=${w.span}`);
    await waitBand(dw.p);
    const was = await upState(dw.p);
    const chip = dw.p.locator('.chip[data-key="up"]');
    let clickErr = null;
    try { await chip.click(); await sleep(900); } catch (e) { clickErr = e.message; }
    const now = await upState(dw.p);
    pages.push({ w, off: was, on: now, clickErr });
    await dw.c.close();
  }
  const onP = pages.map((p) => p.on);
  const clicked = onP.find((s) => s.chip && s.chip.pressed === 'true');
  const anyUnit = onP.find((s) => s.got.length);
  const offStill = pages.every((p) => p.off.got.length === 0 && p.off.upLabels.length === 0);

  ck('勾上「高一级」⇒ 合成框**才**画，且画了几个 == 载荷里落在这一屏的几个（逐个对，不是"大于零"）',
     !!clicked && !!anyUnit && onP.every((s) => s.got.length === s.want)
       && pages.filter((p) => p.clickErr).length === 0,
     (clicked ? '' : '★ 那颗芯片点不动：' + (pages.map((p) => p.clickErr).filter(Boolean)[0] || '(没报错)') + '　')
       + pages.map((p, i) => `at+${SWEEP[i].at - (pick ? pick.X0 : 0)}：载荷 ${p.on.want} / 画了 ${p.on.got.length}`
         + `（关着时 ${p.off.got.length}）`).join('　'));

  ck('框**按级别上色**：画上去的那个色 == `/theme.js` 的级别色（这一层的合成框都是**线段中枢升的** ⇒ `up_seg`）',
     !!anyUnit && onP.every((s) => s.got.every((u) => u.col === UCHART.up_seg)),
     `画上去的色 ${JSON.stringify([...new Set(onP.flatMap((s) => s.got.map((u) => u.col)))])}`
       + `　theme 的 up_seg=${UCHART.up_seg}　up_pen=${UCHART.up_pen}（两个色相同时这格就成死闸：印出来）`);

  // ★★ 这一格是这张卡的牙之一：「升级」二字得**落在它那个框里**，横向差恒为 6 px。
  const owned = onP.flatMap((s) => s.upLabels.map((L) => {
    const u = s.got.find((u) => u.x0 !== null && u.x0 >= -1 && L.x >= u.x0 - 1 && L.x <= u.x1 + 1);
    return { L, u };
  }));
  const dxs = owned.filter((o) => o.u).map((o) => Math.round((o.L.x - o.u.x0) * 10) / 10);
  ck('「升级」二字的 x **在它那个框里**，且贴左沿 6 px（不是段的左上角、更不是视口的左上角）',
     !!anyUnit && owned.length > 0 && owned.every((o) => !!o.u) && dxs.every((d) => Math.abs(d - 6) <= 1.5),
     `${owned.length} 个字：` + owned.map((o, i) => o.u
       ? `x=${o.L.x} ∈ 框[${o.u.x0}, ${o.u.x1}]（差 ${dxs[i]}）`
       : `★ x=${o.L.x} **不在任何一个框里**`).join('　'));

  // ★★ 这张卡的正题：老代码把那个字夹在 `Math.max(x, 4) + 6` 上 ⇒ 框左沿一滚出屏，
  //    字就**钉死在视口左上角**（x≈10）。判据：**每一个**「升级」字，都必须有一个"左沿在屏内"的框认领它。
  //    防空洞是后半边：这一趟里**真出现过**左沿出屏的框 —— 不然这格是空转（什么都没量到也能绿）。
  const sawOffLeft = onP.some((s) => s.got.some((u) => u.x0 !== null && u.x0 < 0));
  const orphans = onP.flatMap((s) => s.upLabels.filter((L) =>
    !s.got.some((u) => u.x0 !== null && u.x0 >= 0 && L.x >= u.x0 - 1 && L.x <= u.x1 + 1)));
  ck('框左沿滚出屏幕 ⇒ 那个「升级」**一个字都不画**（老毛病：夹在 `Math.max(x,4)` 上钉死在视口左上角）',
     !!anyUnit && sawOffLeft && orphans.length === 0,
     `这一趟里左沿出屏的框：` + onP.map((s, i) => `${s.got.filter((u) => u.x0 < 0).length} 个`).join('／')
       + `　没人认领的字：${orphans.length}${orphans.length ? '　★ ' + orphans.map((L) => `x=${L.x}`).join(',') : ''}`
       + `（"没人认领"= 那个字右边没有一个左沿在屏内、把它罩住的框）`);

  // 关着的那一档：四档全都一个框都不画（上面第一格只量了默认那一次，这一格把推过的四档也量了）
  ck('这四档里「高一级」没勾的那一帧，也一个框都不画（不是"默认那一次碰巧没画"）',
     offStill,
     pages.map((p, i) => `第 ${i + 1} 档：框 ${p.off.got.length}／字 ${p.off.upLabels.length}`).join('　'));

  // ───────────────────────────────────────────────────────────────────────────
  // 49–53 「等确认」那条斜线带：挪到格顶（不再压成交量）＋ 条上写「等确认」＋ 图例里也有它
  //        （v3 §八 3，卡 card-60678062-8c2；小栋 10-05 23:46Z 两句原话：「挡住了交易量」「没有文字说明」）
  //
  // ★ 小栋报的两件事底下是**同一件事**：那条带子铺在 `H - hatchH` ＝ 主图下沿，
  //   而成交量也挂在主图下沿（`volSeries` 的 `scaleMargins.top = 0.82`，`app.js:161`）——
  //   两边各自都没写错，叠在一起就是「带子压在柱子上」。
  //   所以 49 量的是**两个 y 区间相交不相交**，不是"带子在哪一行"：哪天主图高度变了、
  //   或者把成交量挪到副图，写死行号的判据当场变成假话，而"相交不相交"照样成立。
  //
  // ★★ 成交量的 y 范围**不许由页面自报**。`trendDrawn` 只能证明"这一层画在哪"，
  //    拿它当成交量的准就是自说自话（把带子挪回格底，两边一起变，这格照样绿）。
  //    所以走 **LWC 自己的 API**：`chart.panes()[0].getSeries()` 里那根 Histogram ＋ 它自己的
  //    `priceToCoordinate(0 / v)` —— 柱顶落在哪一行是**库**算的，跟这一层的代码一个字都不沾。
  //
  // ★ 50 是**另一路**、只读画布的像素判据：成交量占的那几行里，斜线色一个都不许有。
  //    它跟 49 互不依赖（49 量几何、50 量像素），两条都绿才叫"真的不相交"。
  //    挑画布那一步本身就是正对照：`TREND.hatch` 这个色**只有 `hatchFill()` 一处会画**，
  //    探测器一旦读错色 ⇒ 一张画布都挑不出来 ⇒ 这格是**红**（写着"没量到"），不是绿。
  console.log('\n49–53 「等确认」斜线带：铺在格顶（不压成交量）＋ 条上写「等确认」＋ 图例里也有它');
  const r2 = (x) => (x === null || x === undefined ? null : Math.round(x * 100) / 100);

  const hatchState = (pg, search) => pg.evaluate(async (sq) => {
    const TH = await import('/theme.js');
    const a = window.__app, st = a.state, D = st.trendDrawn || {};
    const ts = a.chart.timeScale(), bars = st.data.bars;
    // ★ 同前：mediaSize（主图那一格）≠ `#chart` 的 clientWidth（1250 vs 1194，差 56 ＝ 右轴）。
    //   这里 W 只用来把远处的成交量柱滤掉（±40 px 的松口径），但尺子还是用同一把 —— 免得将来有人
    //   在这里写死一个紧判据，又踩同一个坑（card-4700b9cc-35e）。
    const W = (() => { const c = document.querySelector('#chart canvas');
      return c ? c.getBoundingClientRect().width : 0; })();
    const r1 = (x) => (x === null || x === undefined ? null : Math.round(x * 10) / 10);
    const px = (i) => { const b = bars[i]; const x = b ? ts.timeToCoordinate(b.t / 1000) : null; return x === null ? null : r1(x); };
    const band = (r) => ({ i0: r.i0, i1: r.i1, x0: px(r.i0), x1: px(r.i1), y0: r.y0, y1: r.y1 });

    // ── 成交量那一侧：LWC 自己的 API，这一层一个字都不参与 ────────────────────
    const pane = a.chart.panes()[0];
    const H = pane.getHeight();
    const hv = pane.getSeries().find((s) => { try { return s.seriesType() === 'Histogram'; } catch (e) { return false; } });
    let volMargins = null; const cols = [];
    if (hv) {
      volMargins = hv.priceScale().options().scaleMargins;
      const yZero = hv.priceToCoordinate(0);
      for (const d of hv.data()) {
        const x = ts.timeToCoordinate(d.time);
        if (x === null || x < -40 || x > W + 40) continue;          // 屏外的柱不参与
        const yTop = hv.priceToCoordinate(d.value);
        if (yTop === null || yZero === null) continue;
        cols.push({ x: r1(x), yTop: r1(yTop), yBot: r1(yZero) });
      }
    }
    // 一根柱横向占多宽：拿相邻两根的间距（柱宽随缩放走，不写死）
    let colHalfW = 0;
    for (let i = 1; i < cols.length; i++) { const g = cols[i].x - cols[i - 1].x; if (g > 0) { colHalfW = g / 2; break; } }

    const B = { bounds: (D.bounds || []).map(band), pending: (D.pending || []).map(band) };
    // 每条带子：落在这条带子 x 区间里的柱，柱顶最高的那一行
    const perStrip = [];
    for (const kind of ['bounds', 'pending']) for (const s of B[kind]) {
      if (s.x0 === null || s.x1 === null) continue;
      const inS = cols.filter((c) => c.x + colHalfW >= Math.max(s.x0, 0) && c.x - colHalfW <= Math.min(s.x1, W));
      perStrip.push({ kind, s, n: inS.length, colTop: inS.length ? Math.min(...inS.map((c) => c.yTop)) : null });
    }

    // ── 像素那一侧：只读画布 ─────────────────────────────────────────────────
    const hex = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
    const hatch = hex(TH.TREND.hatch);
    const cvs = [...document.querySelectorAll('#chart canvas')];
    // 挑带子**不写下标**：取第一条"在屏上真的露出一截"的（数据是活的，第 0 条哪天滚出屏外就量空了）
    const s0 = [...B.bounds, ...B.pending].find((s) =>
      s.x0 !== null && s.x1 !== null && Math.min(s.x1, W) - Math.max(s.x0, 0) > 0) || null;
    const cy0 = s0 ? s0.y0 : TH.TREND.hatchTop, cy1 = s0 ? s0.y1 : TH.TREND.hatchTop + TH.TREND.hatchH;
    const cx0 = s0 && s0.x0 !== null ? Math.max(0, Math.round(s0.x0)) : 0;
    const cx1 = s0 && s0.x1 !== null ? Math.min(W, Math.round(s0.x1)) : 0;
    const volTopRow = cols.length ? Math.max(0, Math.floor(Math.min(...cols.map((c) => c.yTop)))) : null;
    let pix = null, which = -1;
    if (cx1 > cx0) {
      const cnt = (img, x0, x1, y0, y1) => { let c = 0;
        for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) { const i = (y * img.w + x) * 4;
          if (Math.abs(img.d[i] - hatch[0]) <= 6 && Math.abs(img.d[i + 1] - hatch[1]) <= 6 && Math.abs(img.d[i + 2] - hatch[2]) <= 6) c++; }
        return c; };
      const grab = (cv) => ({ d: cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data, w: cv.width, h: cv.height });
      for (let k = 0; k < cvs.length && which < 0; k++) if (cnt(grab(cvs[k]), cx0, cx1, cy0, cy1) > 0) which = k;
      if (which >= 0) {
        const img = grab(cvs[which]);
        pix = { canvas: which, inBand: cnt(img, cx0, cx1, cy0, cy1),
          volRows: volTopRow === null ? null : [volTopRow, H],
          inVolRows: volTopRow === null ? null : cnt(img, cx0, cx1, volTopRow, H) };
      }
    }

    // ── 字那一侧：页面现量的字体度量 ─────────────────────────────────────────
    // ★ 字体串**是从 `layers.js:25` 抄过来的**（那边是模块内的 const，导不出来）。
    //   抄一份就有走样的风险 —— 所以 51 拿"字盒宽度"跟这里 `measureText` 的宽度对一次账：
    //   真走样了那条判据会红，不会静静地量到别的字号上去。
    const mctx = document.createElement('canvas').getContext('2d');
    mctx.font = '12px -apple-system, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif';
    const m = mctx.measureText('等确认');
    const labels = (D.labels || []).filter((L) => L[4] === '等确认')
      .map((L) => ({ x0: r1(L[0]), x1: r1(L[2]), w: r1(L[2] - L[0]),
        base: L[3] - 3 }));                 // `haloText` 的框下沿 = 基线 + round(12×0.25) = 基线 + 3
    return {
      url: sq, W, H, hatchTop: TH.TREND.hatchTop, hatchH: TH.TREND.hatchH, hatchCol: TH.TREND.hatch,
      bounds: B.bounds, pending: B.pending, nStrip: B.bounds.length + B.pending.length,
      perStrip, nCols: cols.length, volMargins, colTopMin: cols.length ? r1(Math.min(...cols.map((c) => c.yTop))) : null,
      pix, measure: { w: r1(m.width), asc: r1(m.actualBoundingBoxAscent), desc: r1(m.actualBoundingBoxDescent) },
      labels, haloHalf: 1.5,                // `haloText` 的 `lineWidth = 3`
      legend: [...document.querySelectorAll('#legend .lg')].map((s) => ({ t: s.textContent, tip: s.title || '' })),
      trendOn: !!st.opts.trend,
    };
  }, search);

  const dH = await open(TQ);
  await waitBand(dH.p);
  const HS = await hatchState(dH.p, TQ);
  await dH.c.close();

  // 49 几何：**每一条**带子（中阴 ＋ 待定走的是同一个 `strip()`）的 y 区间，都在成交量柱顶之上
  const badTop = HS.perStrip.filter((p) => p.n === 0 || p.colTop === null || !(p.s.y1 <= p.colTop));
  ck('斜线条的 y 区间与**成交量柱**的 y 区间**不相交**（中阴＋待定一起量；柱顶走 LWC 的 `priceToCoordinate` 现算）',
     HS.nStrip > 0 && HS.nCols > 0 && badTop.length === 0,
     `带子 ${HS.nStrip} 条：` + (HS.perStrip.length ? HS.perStrip.map((p) => `[${p.kind}] y[${p.s.y0}, ${p.s.y1}]`
       + `　该区间内 ${p.n} 根柱、柱顶最高 ${p.colTop}（不相交=${p.n > 0 && p.colTop !== null && p.s.y1 <= p.colTop}）`).join('　')
       : '★ 一条带子都没有') + `　主图高 ${HS.H}　成交量价格尺 scaleMargins=${JSON.stringify(HS.volMargins)}`
     + `　（★ 老位置 H-hatchH = [${HS.H - HS.hatchH}, ${HS.H}]：柱顶最高 ${HS.colTopMin} ⇒ **压在柱子上、这格会红**，判据不是空转）`);

  // 50 像素：成交量那几行里，斜线色一个都不许有
  const Pix = HS.pix;
  ck('像素判据（不读任何自报出口）：成交量占的那几行里，斜线色**一个像素都没有**（挑不到画布就是红，不是绿）',
     !!Pix && Pix.inVolRows === 0 && Pix.inBand > 0,
     Pix ? `画布 #${Pix.canvas}　带子那几行里斜线色 ${Pix.inBand} 个（正对照）　成交量那几行 y[${Pix.volRows}] 里斜线色 ${Pix.inVolRows} 个（要 0）　斜线色 ${HS.hatchCol}`
       : `★ 一张含斜线色（${HS.hatchCol}）的画布都没挑到 —— 没量到，不算绿`);

  // 51 条上有可见文字：字盒宽度跟现量字体对得上（防抄字体串走样）＋ 墨迹和 3px 描边整个落在带子里
  const labH = HS.labels[0] || null;
  // 认领这个字的那条带子：**谁罩住它算谁的**（不写"第 0 条"—— 屏上不止一条带子时那样会认错）
  const S0 = (labH && [...HS.bounds, ...HS.pending].find((s) => s.x0 !== null && s.x1 !== null
    && labH.x0 >= Math.min(s.x0, s.x1) - 1 && labH.x0 <= Math.max(s.x0, s.x1) + 1))
    || HS.bounds[0] || HS.pending[0] || null;
  const wMatch = !!labH && Math.abs(labH.w - HS.measure.w) <= 0.5;
  const inkTop = labH ? r2(labH.base - HS.measure.asc) : null;
  const inkBot = labH ? r2(labH.base + HS.measure.desc) : null;
  const haloTop = inkTop === null ? null : r2(inkTop - HS.haloHalf);
  const haloBot = inkBot === null ? null : r2(inkBot + HS.haloHalf);
  const intoStrip = (S0 && labH && S0.x0 !== null && S0.x1 !== null)
    ? (labH.x0 >= Math.min(S0.x0, S0.x1) - 1 && labH.x0 <= Math.max(S0.x0, S0.x1) + 1) : false;
  const insideBand = !!(S0 && inkTop !== null) && inkTop >= S0.y0 && inkBot <= S0.y1;
  ck('那条带子上**写了「等确认」**：字起在带子里、墨迹连同 3px 描边整个落在带子里，且**没有越过画布上沿**（不切字）',
     !!labH && intoStrip && wMatch && haloTop >= 0 && insideBand,
     labH ? `字盒 x[${labH.x0}, ${labH.x1}]（宽 ${labH.w}，现量 ${HS.measure.w}${wMatch ? '' : '　★ 对不上'}）　基线 ${labH.base}`
       + `　墨迹 y[${inkTop}, ${inkBot}]　带描边 y[${haloTop}, ${haloBot}]　带子 y[${S0 ? S0.y0 + ', ' + S0.y1 : '?'}]`
       + `　起笔在带子里=${intoStrip}　整个包在带子里=${insideBand}`
       + `（★ 带子贴着 y=0、基线 hatchH-2 的老做法：描边顶到 ${r2(HS.hatchH - 2 - HS.measure.asc - HS.haloHalf)} ⇒ 被上沿切，这格会红）`
     : '★ 一条「等确认」都没画（`trendDrawn.labels` 里没有）');

  // 52 图例：有这一项、写的是「等确认」、悬停是一句人话（老术语名不许还在）
  const lgH = HS.legend.find((e) => e.t === '等确认');
  const jargon = HS.legend.filter((e) => /极值|回抽|段终点/.test(e.t));
  ck('图例里有「等确认」这一项 ＋ 一句人话的悬停说明，而「极值到回抽段终点」那套老术语**一个字都不剩**',
     !!lgH && !!lgH.tip && jargon.length === 0,
     `图例 ${HS.legend.length} 项：${HS.legend.map((e) => e.t + (e.tip ? `⟨${e.tip}⟩` : '（无悬停说明）')).join(' | ')}`
     + `　老术语残留 ${jargon.length}${jargon.length ? '　★ ' + jargon.map((e) => e.t).join(',') : ''}`);

  // 53 关掉走势那一层 ⇒ 带子、字、图例项**一起**没（不许留"字还在、带子没了"的半截状态）
  const dHO = await open(`${TQ}&trend=0`);
  await dHO.p.waitForFunction(() => window.__app && window.__app.state.data, null, { timeout: 120000 });
  await dHO.p.waitForTimeout(2500);        // 层关着 ⇒ `trendDrawn.bands` 一直不出现，这里不能用 waitBand
  const HS_HO = await hatchState(dHO.p, `${TQ}&trend=0`);
  await dHO.c.close();
  ck('把走势那一层关掉：带子、条上的字、图例里那一项**一起**没（不许留下"字还在、带子没了"这种半截状态）',
     HS.trendOn && !HS_HO.trendOn && HS.nStrip > 0
       && HS_HO.nStrip === 0 && HS_HO.labels.length === 0 && !HS_HO.legend.some((e) => e.t === '等确认'),
     `开着：带子 ${HS.nStrip} 条／字 ${HS.labels.length} 个／图例项 ${HS.legend.length}`
     + `　关掉：带子 ${HS_HO.nStrip} 条／字 ${HS_HO.labels.length} 个／图例项 ${HS_HO.legend.length}`
     + `（图例里还剩「等确认」=${HS_HO.legend.some((e) => e.t === '等确认')}）`);

  // 54 ② 的前半句「够宽的每条都写」得在**很多个视口**上成立，不是"默认那一屏碰巧写了"。
  //    ★ 后半句「一条都放不下就只写最近那一段」**这一格量不到** —— 我拿 616 个视口扫过：
  //      带子要么整条在屏外（`strip()` 当场 return），要么可见宽度就没低于过 49 px（字要 36.8＋12），
  //      **一次都没进过那个分支**。所以这里只印它被走到了几次、**不拿它当绿**；
  //      那半句是防"载荷里出现一根 K 宽的带子"的保险，今天的数据造不出来（`layers.js` 那段有说明）。
  const dW = await open(TQ);
  await waitBand(dW.p);
  const SW54 = await dW.p.evaluate(async () => {
    const a = window.__app, st = a.state, ts = a.chart.timeScale(), bars = st.data.bars;
    // ★★ 这一格原先拿 `#chart` 的 clientWidth 当画布宽 ⇒ **假红**（card-4700b9cc-35e）：
    //    图层判「这条带子够不够宽、要不要写字」用的是 mediaSize（主图那一格，**1194**），
    //    这里用 1250 会把右轴那一条也算成"带子露在屏上" ⇒ 那条带子按 1250 看 82px 宽（够）、
    //    按 1194 看只有 26px（不够）⇒ 工装说"该写字"、图层没写 ⇒ 判成漏写。
    //    （闸门里那趟刚好没落在这个窗口上 ⇒ 绿；单独重跑两遍都红 —— 一颗会假红也会假绿的牙。）
    //    W 跟画图同一把尺：mediaSize ＝ `#chart` 那张主图画布的宽度；`#chart` 那个数只印出来对照。
    const W = (() => { const c = document.querySelector('#chart canvas');
      return c ? c.getBoundingClientRect().width : 0; })();
    const Wchart = document.getElementById('chart').clientWidth;
    // ★ 第三个数：**问图自己要**轴有多宽 —— 这样印出来那句话自带验算（`W ＋ 轴宽 == Wchart`），
    //   读的人不用信我"这两把尺差的就是那条轴"，当场能加一遍。加不平就说明 W 取错了地方。
    const psW = (() => { const p = a.chart.panes()[0];
      if (!p) return null; const ps = p.priceScale('right');
      return ps && typeof ps.width === 'function' ? Math.round(ps.width() * 10) / 10 : null; })();
    const mctx = document.createElement('canvas').getContext('2d');
    mctx.font = '12px -apple-system, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif';
    const tw = mctx.measureText('等确认').width;
    const frame = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    const px = (i) => { const b = bars[i]; const x = b ? ts.timeToCoordinate(b.t / 1000) : null; return x === null ? null : x; };
    const wins = [];
    for (const span of [1, 3, 8, 30]) for (let from = 4000; from <= 16000; from += 271) wins.push({ from, span });
    let nWin = 0, nWithStrip = 0, orphans = 0, mismatch = 0, fellBack = 0, maxLabels = 0, worst = null;
    // ★ 这一格绿的时候也得让人看见**它真的走到过门槛附近**：记下"离门槛最近的那条带子"。
    //   不记的话，"0 个不平"可能只是因为所有带子都在门槛外老远 —— 那种绿是够不着的绿。
    //   顺带把**旧那把尺**（`#chart` 的 clientWidth）会怎么判也带上：这就是假红的那个窗口。
    let near = { d: Infinity };
    for (const s of wins) {
      ts.setVisibleLogicalRange({ from: s.from, to: s.from + s.span });
      await frame(); await frame();
      const D = st.trendDrawn || {};
      const bs = (D.bounds || []).map((b) => { const x0 = px(b.i0), x1 = px(b.i1);
        const vis = (x0 === null || x1 === null) ? 0 : Math.min(x1, W) - Math.max(x0, 0);
        const visC = (x0 === null || x1 === null) ? 0 : Math.min(x1, Wchart) - Math.max(x0, 0);
        return { x0: x0 === null ? null : Math.round(x0), x1: x1 === null ? null : Math.round(x1),
          vis: Math.round(vis), visChart: Math.round(visC), roomy: vis > 0 && vis >= tw + 12 }; });
      for (const b of bs) {
        if (b.vis <= 0) continue;
        const d = Math.abs(b.vis - (tw + 12));
        if (d < near.d) near = { d: Math.round(d * 10) / 10, from: s.from, span: s.span,
          x0: b.x0, vis: b.vis, visChart: b.visChart, roomy: b.roomy, roomyChart: b.visChart >= tw + 12 };
      }
      const labs = (D.labels || []).filter((L) => L[4] === '等确认');
      const roomy = bs.filter((b) => b.roomy);
      const vis = bs.filter((b) => b.vis > 0);
      nWin++; if (vis.length) nWithStrip++;
      maxLabels = Math.max(maxLabels, labs.length);
      // 孤儿：这个字右边没有一个"露在屏上、罩得住它"的带子（跟 47 那条「升级」同一个判据）
      orphans += labs.filter((L) => !bs.some((b) => b.vis > 0
        && L[0] >= Math.min(b.x0, b.x1) - 1 && L[0] <= Math.max(b.x0, b.x1) + 1)).length;
      if (roomy.length) {
        if (labs.length !== roomy.length) { mismatch++; if (!worst) worst = { from: s.from, span: s.span, vis: bs.map((b) => b.vis), labs: labs.length }; }
      } else if (vis.length) fellBack++;
    }
    return { nWin, nWithStrip, orphans, mismatch, fellBack, maxLabels, tw: Math.round(tw * 10) / 10, worst,
      near: near.d === Infinity ? null : near, W: Math.round(W), Wchart, psW };
  });
  await dW.c.close();
  ck('「够宽的带子**每条都写字**、一个字都不许落在没有带子的地方」在**很多个视口**上都成立（不是"默认那一屏碰巧"）',
     // ★ 最后那一条是**这把尺自己的牙**：`W ＋ 轴宽 == #chart 的 clientWidth`。加不平就说明
     //   `document.querySelector('#chart canvas')` 拿到的**不是主图那一格的画布**（`#chart` 里有 11 张画布：
     //   主图 1182、右轴 68、副图 1182……），那这一格量的是个来路不明的矩形 ⇒ **必须红**，不许绿。
     SW54.nWithStrip >= 20 && SW54.orphans === 0 && SW54.mismatch === 0 && SW54.maxLabels >= 1
       && SW54.psW !== null && Math.abs(SW54.W + SW54.psW - SW54.Wchart) <= 1,
     // ★ 这句自带验算：`画布宽 ＋ 轴宽 == #chart 的 clientWidth`。加不平 ⇒ W 取错了地方（读的人当场能加一遍，不用信我）。
     `画布宽（mediaSize，跟图层同一把尺）${SW54.W} ＋ 轴宽（问图要的）${SW54.psW} = ${SW54.Wchart}`
     + `（＝ \`#chart\` 的 clientWidth ⇒ 差的正好是右轴那一条）　`
     + `字宽 ${SW54.tw} px ⇒ 「够宽」的门槛 ${Math.round((SW54.tw + 12) * 10) / 10} px　`
     + `扫了 ${SW54.nWin} 个视口（其中 ${SW54.nWithStrip} 个屏上有带子）　孤儿字 ${SW54.orphans} 个　`
     + `"写字数 ≠ 够宽的条数"的视口 ${SW54.mismatch} 个${SW54.worst ? '　★ ' + JSON.stringify(SW54.worst) : ''}　`
     + `一屏最多写了 ${SW54.maxLabels} 个字　`
     // ★ 绿也要让人看见"这颗牙咬到过门槛附近"，否则"0 个不平"可能只是所有带子都离门槛老远。
     + `离门槛最近的那条带子：宽 ${SW54.near ? SW54.near.vis : '—'} px（门槛 ${Math.round((SW54.tw + 12) * 10) / 10}，`
     + `差 ${SW54.near ? SW54.near.d : '—'}）@from=${SW54.near ? SW54.near.from : '—'} `
     + `⇒ 同一刻按旧那把尺（\`#chart\` ${SW54.Wchart}）算是 ${SW54.near ? SW54.near.visChart : '—'} px、`
     + `判「${SW54.near && SW54.near.roomyChart ? '够宽' : '不够宽'}」（图层判「${SW54.near && SW54.near.roomy ? '够宽' : '不够宽'}」）`
     + `${SW54.near && SW54.near.roomyChart !== SW54.near.roomy ? '　★ 两把尺在这一格判反了 ⇒ 修前这里就是假红/假绿的现场' : ''}　`
     + `（★「一条都放不下就只写最近那一段」这一趟被走到 ${SW54.fellBack} 次`
     + ` ⇒ ${SW54.fellBack ? '量到了' : '**没量到**，那半句这格不算数'}）`);

  // ---------------------------------------------------------------- 全屏看图（卡 card-5014b0cb-e4d）
  // 卡里六条，逐个对着量：
  //   ① **别挡右轴和最新价标签** —— 判据是**像素**：从画布上找出右轴那条竖栏的左沿（`--line` 色的
  //      一列、通高），按钮的右沿必须落在它左边。为什么不用「按钮的 right ≥ 某个数」：那个数是我自己
  //      写进 CSS 的，等于自己给自己判卷（跟 ⑤ 那条「不读自报出口」同一条账）。
  //      最新价标签就画在那条竖栏里 ⇒ 压在轴上就是压住标签。
  //   ② 开关照点　③ 视口不跳　④ 退路　⑤ 自动重画（**真量**，不是"读代码知道 autoSize 会重画"）　⑥ 退出
  // ★ 原生全屏在无头浏览器里**可能被拒**（那条路要用户手势/浏览器策略）—— 被拒就落到自铺那一档。
  //   所以这组每格都**印出走的是哪条路**：落到退路还把绿说成"原生验过了"，那是假绿。
  const fsState = (p) => p.evaluate(() => {
    const q = (s) => { const n = document.querySelector(s); if (!n) return null; const r = n.getBoundingClientRect();
      return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height),
               right: Math.round(r.right), bottom: Math.round(r.bottom) }; };
    const pane = window.__app.chart.panes()[0];
    const ps = pane && pane.priceScale('right');
    // ★ 按钮的**矩形**必须跟 chart/main 一样过 q()：`btn` 本身另留一份（computed style／属性要从元素上读）。
    //   头一版这里直接把 DOM 元素当矩形返回 ⇒ 61/62 两格读到的是 `undefined×undefined` 的假红。
    const btnEl = document.querySelector('#fs');
    const btn = q('#fs');
    // ④ 要量的是**主图那一格自己那张画布**。不能拿"最高的那张"顶替：副图（成交量/MACD）在场时，
    //   最高的那张跟 `#chart` 的高矮本来就不是一回事（实测 1182×653 vs 图那栏 900）。
    const paneCv = (() => {
      if (!pane || typeof pane.getHTMLElement !== 'function') return null;
      const el = pane.getHTMLElement(); if (!el) return null;
      const c = el.querySelector('canvas') || el; const r = c.getBoundingClientRect();
      return { w: Math.round(r.width), h: Math.round(r.height) };
    })();
    return {
      btn, hasBtn: !!btnEl, chart: q('#chart'), main: q('main'),
      pe: btnEl ? getComputedStyle(btnEl).pointerEvents : null,
      paneCv,
      paneH: pane && typeof pane.getHeight === 'function' ? Math.round(pane.getHeight()) : null,
      inOverlays: !!(document.querySelector('.overlays #fs')),
      psVar: parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ps-right')) || null,
      psW: ps && typeof ps.width === 'function' ? Math.round(ps.width()) : null,
      full: !!document.fullscreenElement, fake: document.body.classList.contains('fs-fake'),
      onCls: document.body.classList.contains('fs-on'),
      pressed: btnEl ? btnEl.getAttribute('aria-pressed') : null,
      range: window.__app.chart.timeScale().getVisibleLogicalRange(),
      cvs: [...document.querySelectorAll('#chart canvas')].map((c) => ({ w: c.width, h: c.height })),
      vw: innerWidth, vh: innerHeight, dpr: devicePixelRatio,
    };
  });
  // 右轴那条竖栏的左沿在哪一列：顶部那几行里，某一列**通高**都是 `--line` 色 ⇒ 那是轴的边框线。
  // （顶部那 8% 是比例尺留白，那儿不会有 K 线；时间轴那条横线、窗格分隔线都不在这几行里。）
  const axisEdge = (p) => p.evaluate(() => {
    const hx = getComputedStyle(document.documentElement).getPropertyValue('--line').trim().replace('#', '');
    const want = [parseInt(hx.slice(0, 2), 16), parseInt(hx.slice(2, 4), 16), parseInt(hx.slice(4, 6), 16)];
    const cols = [];
    for (const cv of document.querySelectorAll('#chart canvas')) {
      const W = cv.width, H = cv.height;
      if (!W || !H) continue;
      // ★ 印出来的必须是**页面里的位置**，不是"这张画布自己的第几像素列"。
      //   头一版忘了加画布在页面里的偏移 ⇒ 68 宽那张轴画布的边框线（它自己的 x=0）
      //   被印成「轴左沿 0.0」，判据就永远红（那一列实际在页面 x=1182）。
      const r = cv.getBoundingClientRect();
      const k = W ? r.width / W : 1;              // 画布像素 → CSS px
      const rows = Math.min(26, H);
      const d = cv.getContext('2d').getImageData(0, 0, W, rows).data;
      const hits = [];
      for (let x = 0; x < W; x++) {
        let k2 = 0;
        for (let y = 0; y < rows; y++) { const i = (y * W + x) * 4;
          if (d[i] === want[0] && d[i + 1] === want[1] && d[i + 2] === want[2]) k2++; }
        if (k2 >= rows * 0.7) hits.push(x);
      }
      if (hits.length) {
        const x0 = Math.min(...hits);
        cols.push({ cw: W, ch: H, x: x0, page: Math.round((r.x + x0 * k) * 10) / 10,
                    edge: x0 <= 1 });   // edge＝这条竖线就画在它自己那张画布的最左边（轴边框线长这样）
      }
    }
    return { cols, dpr: devicePixelRatio, canvas: [...document.querySelectorAll('#chart canvas')].length };
  });
  const dFS = await open(QS);
  let FS = await fsState(dFS.p);

  // ① 那颗按钮在图上、是**能点**的一颗（不在 .overlays 里 —— 那个盒子整块 pointer-events:none）
  ck('全屏那颗按钮在图的右上角、而且**点得着**（不是挂在 `.overlays` 那个 pointer-events:none 的盒子里）',
     !!FS.btn && FS.pe !== 'none' && !FS.inOverlays && !!FS.chart
       && FS.btn.right <= FS.chart.right + 1 && FS.btn.x > FS.chart.x + FS.chart.w / 2
       && FS.btn.y < FS.chart.y + FS.chart.h / 2 && FS.btn.w >= 24 && FS.btn.h >= 24,
     FS.btn ? `按钮 ${FS.btn.w}×${FS.btn.h} @(${FS.btn.x},${FS.btn.y})　图 x[${FS.chart.x}, ${FS.chart.right}] y[${FS.chart.y}, ${FS.chart.bottom}]`
       + `　pointer-events=${FS.pe}　在 .overlays 里=${FS.inOverlays}` : '★ 页面上没有 #fs');

  // ② 别挡右轴（也就不会压住画在轴上的最新价标签）：像素找轴左沿 ＋ 布局算式两条一起印
  const AX = await axisEdge(dFS.p);
  // 只认「竖线就画在它自己那张画布最左边」的那种命中列（面板之间的分隔线长这样），取**页面坐标**里最左的一条。
  const edges = AX.cols.filter((c) => c.edge);
  const axLeft = edges.length ? Math.min(...edges.map((c) => c.page)) : null;
  ck('按钮**不挡右轴那一条**：它的右沿落在轴的左沿左边（判据是**画布像素**找出来的轴边框线，不是我自己写的数）',
     axLeft !== null && !!FS.btn && FS.btn.right <= axLeft - 4,
     `按钮右沿 ${FS.btn ? FS.btn.right : '?'}　轴左沿 ${axLeft === null ? '★ 像素里没找到那条竖线' : axLeft.toFixed(1)}`
     + `（画布 ${AX.canvas} 张／命中列 ${JSON.stringify(AX.cols)}／dpr ${AX.dpr}）`
     + `　页面自己读的轴宽 ${FS.psW}、CSS 变量 --ps-right=${FS.psVar}`
     + `　⇒ 让开的距离 ${axLeft === null ? '?' : (axLeft - (FS.btn ? FS.btn.right : 0)).toFixed(1)} px（要 ≥ 4）`);

  // ③ 进全屏：走的是哪条路 ＋ **视口不跳** ＋ 图真的变大
  const before = FS;
  await dFS.p.locator('#fs').click();
  await dFS.p.waitForTimeout(900);
  const after = await fsState(dFS.p);
  const path = after.full ? '原生全屏' : after.fake ? '自铺（退路）' : '★ 两条都没走成';
  const dFrom = after.range && before.range ? Math.abs(after.range.from - before.range.from) : NaN;
  const dTo = after.range && before.range ? Math.abs(after.range.to - before.range.to) : NaN;
  const grew = !!before.chart && !!after.chart && (after.chart.h > before.chart.h + 20 || after.main.h > before.main.h + 20);
  ck('点一下进全屏：图那栏**真的变大**，而**可视窗一根 K 线都没跳**（进全屏要的是"这一屏放大"，不是"换一屏看"）',
     (after.full || after.fake) && grew && dFrom <= 1.5 && dTo <= 1.5 && after.onCls && after.pressed === 'true',
     `走的是 **${path}**　图 ${before.chart.h}px → ${after.chart.h}px 高、main ${before.main.h}px → ${after.main.h}px`
     + `　视口 [${before.range.from.toFixed(2)}, ${before.range.to.toFixed(2)}] → [${after.range.from.toFixed(2)}, ${after.range.to.toFixed(2)}]`
     + `（Δ＝${dFrom.toFixed(2)} / ${dTo.toFixed(2)} 根，要 ≤ 1.5）　body.fs-on=${after.onCls}　aria-pressed=${after.pressed}`);

  // ④ 卡里 ⑤「自动重画」——**量**出来的：画布跟着图的新尺寸重排了，不是"读代码知道 autoSize 会重画"
  // ★ 量的是**主图那一格自己那张画布**（`panes()[0].getHTMLElement()` 里的），不是"最高的那张"：
  //   副图（成交量/MACD）在场时，画布的高矮跟 `#chart` 的高矮本来就不是一回事 —— 头一版拿最高的那张
  //   去比对图那栏（1182×653 vs 900），差 247px，量出来的是我自己的假设，不是页面。
  //   这一格要的是两件事：① 它**长高了**（真重排，不是纹丝不动）② 它跟图自己报的那一格高**对得上**。
  const pc = after.paneCv, pc0 = before.paneCv;
  const dPane = pc && pc0 ? pc.h - pc0.h : NaN;
  ck('卡里 ⑤ 那条（进出全屏自动重画）是**量**出来的：**主图那一格的画布**跟着新尺寸重排了（不是"读代码知道 autoSize 会重画"）',
     !!pc && !!pc0 && dPane > 20 && (after.paneH === null || Math.abs(pc.h - after.paneH) <= 2),
     pc ? `主图画布 ${pc0 ? pc0.w + '×' + pc0.h : '?'} → ${pc.w}×${pc.h} CSS px（长高 ${dPane} px，要 > 20）`
       + `　图自己报的那一格高 ${after.paneH === null ? '（读不到 getHeight）' : after.paneH + ' px'}`
       + `　差 ${after.paneH === null ? '?' : (pc.h - after.paneH).toFixed(1)} px（要 ≤ 2）`
       : '★ 读不到主图那一格的画布（panes()[0].getHTMLElement()）');

  // ⑤ 全屏里开关照点（卡里 ②）：点一颗 chip，aria-pressed 真翻，且它**还在视口里**（点得着）
  // ★★ 必须挑**图层那排**的开关（`.chip[data-key]`，多选、`aria-pressed`），不能拿 `querySelector('.chip')`：
  //    DOM 里第一颗 `.chip` 是「背驰看法」那组的**单选**（`aria-checked`、没有 `data-key`），而且
  //    **买卖点那层关着的时候它是 disabled 的** ⇒ 点不动、`aria-pressed` 读出来是 `null → null`，
  //    这一格会**假红**（实拍探针头一回就是这么红的：`{"id":"面积","before":null,"after":null}`）。
  //    同理不能挑 disabled 的：`click()` 对 disabled 的按钮不产生任何事。
  const inFs = await dFS.p.evaluate(() => {
    const c = [...document.querySelectorAll('.chip[data-key]')].find((x) => !x.disabled);
    if (!c) return null;
    const key = c.dataset.key;
    const b4 = c.getAttribute('aria-pressed');
    const r = c.getBoundingClientRect();
    c.click();
    return { key, before: b4, after: c.getAttribute('aria-pressed'),
      inside: r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight };
  });
  ck('全屏里开关**照点**（卡里 ②）：点一颗 chip 它的状态真翻了，而且那颗**在视口里**（全屏没把图层栏挡掉或推出屏幕）',
     !!inFs && inFs.before !== inFs.after && inFs.inside,
     inFs ? `点的是图层那颗「${inFs.key}」：aria-pressed ${inFs.before} → ${inFs.after}　在视口里=${inFs.inside}`
       : '★ 页面上没有可点的图层开关（`.chip[data-key]` 全 disabled 或一个都没有）');
  // 点回来（按 key 找回同一颗 —— 再点别的就换了一颗，那不叫"点回来"）
  if (inFs && inFs.before !== inFs.after) {
    await dFS.p.evaluate((k) => document.querySelector(`.chip[data-key="${k}"]`).click(), inFs.key);
    await dFS.p.waitForTimeout(900);   // 图例会跟着图层变（流内 ⇒ 挤高矮），等它落定再量⑥的尺寸
  }

  // ⑥ 退出：再点一次 ⇒ 回原状（两条状态都清掉、图回到原来的尺寸、视口还是没跳）
  await dFS.p.locator('#fs').click();
  await dFS.p.waitForTimeout(900);
  const out = await fsState(dFS.p);
  const oFrom = out.range && before.range ? Math.abs(out.range.from - before.range.from) : NaN;
  const oTo = out.range && before.range ? Math.abs(out.range.to - before.range.to) : NaN;
  ck('再点一次**退得掉**：全屏状态清干净、图回到原来的尺寸、视口还是那一屏（进出全屏都不许换档）',
     !out.full && !out.fake && !out.onCls && out.pressed === 'false'
       && Math.abs(out.chart.h - before.chart.h) <= 1 && Math.abs(out.chart.w - before.chart.w) <= 1
       && oFrom <= 1.5 && oTo <= 1.5,
     `full=${out.full} fs-fake=${out.fake} fs-on=${out.onCls} aria-pressed=${out.pressed}`
     + `　图 ${after.chart.w}×${after.chart.h} → ${out.chart.w}×${out.chart.h}（原来是 ${before.chart.w}×${before.chart.h}）`
     + `　视口 Δ＝${oFrom.toFixed(2)} / ${oTo.toFixed(2)} 根`);

  // ⑧ 「换档那句话」（`.notice`）**跟按钮同一条横带**：它是 `align-self: stretch`（横贯整栏），
  //    而按钮就摆在右上角 ⇒ 字会不会钻到按钮底下。★ 这句是**最长的那句**（NOTICE_TEXT，31 字），
  //    手机那一档（⑨）才是真会撞的地方 —— 桌面 1230px 宽，一句 31 字根本够不着右端。
  //    判据量的是**字的墨迹**（Range 的盒子），不是那个横贯盒子的边 —— 盒子照样横贯（设计如此）。
  //    ★ 这一格是**给我自己那处改动的牙**：`.notice` 的左右内边距改成 `ps+44` 就是为了这件事，
  //    没有这一格，"我让开了"就只是我一句推测。
  const inkOf = (pg) => pg.evaluate((txt) => {
    const n = document.getElementById('notice');
    if (!n) return null;
    n.textContent = txt; n.classList.add('on');          // 造出真身那一档：字最长、横贯整栏
    const rg = document.createRange(); rg.selectNodeContents(n);
    const k = rg.getBoundingClientRect();                 // 墨迹（不含内边距）
    const b = document.getElementById('fs').getBoundingClientRect();
    const hit = !(k.right <= b.left || k.left >= b.right || k.bottom <= b.top || k.top >= b.bottom);
    return { ink: { l: Math.round(k.left), r: Math.round(k.right), t: Math.round(k.top), b: Math.round(k.bottom) },
      btn: { l: Math.round(b.left), r: Math.round(b.right), t: Math.round(b.top), b: Math.round(b.bottom) },
      hit, gap: Math.round(b.left - k.right), pad: getComputedStyle(n).paddingLeft,
      box: Math.round(n.getBoundingClientRect().width), vw: innerWidth };
  }, '已接上更早的K线，左侧的笔、线段、中枢和买卖点按新的起点重算');
  const INK = await inkOf(dFS.p);
  await dFS.p.evaluate(() => document.getElementById('notice').classList.remove('on'));
  ck('「换档那句话」的**字**不钻到全屏按钮底下（桌面档：那个横贯盒子照样横贯，让开的是字）',
     !!INK && !INK.hit && INK.gap >= 4,
     INK ? `字 ${INK.ink.l}→${INK.ink.r}（宽 ${INK.ink.r - INK.ink.l}）　按钮 ${INK.btn.l}→${INK.btn.r}`
       + `　⇒ 字右沿离按钮左沿 ${INK.gap} px（要 ≥ 4）　那句话的盒子宽 ${INK.box}（视口 ${INK.vw}）`
       + `　左右内边距 ${INK.pad}` : '★ 页面上没有 #notice');
  await dFS.c.close();

  // ⑦ 退路那一档（卡里 ④）：注入「浏览器不给原生全屏」（iPhone Safari 对非 video 元素就是这样），
  //    手机档 390×844 ⇒ 必须自铺满窗口、chip 照点、**Esc 退得掉**（原生那条路 Esc 归浏览器，这儿得自己听）
  const cM = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  const pM = await cM.newPage();
  await pM.addInitScript(() => { Object.defineProperty(document, 'fullscreenEnabled', { get: () => false }); });
  await pM.goto(PAGE + QS, { waitUntil: 'domcontentloaded' });
  await waitData(pM);
  await pM.waitForTimeout(1500);
  const mB = await fsState(pM);
  await pM.locator('#fs').click();
  await pM.waitForTimeout(900);
  const mA = await fsState(pM);
  const mChip = await pM.evaluate(() => {
    const c = [...document.querySelectorAll('.chip[data-key]')].find((x) => !x.disabled);
    const b4 = c.getAttribute('aria-pressed'); c.click();
    return { before: b4, after: c.getAttribute('aria-pressed'), n: document.querySelectorAll('.chip[data-key]').length };
  });
  await pM.keyboard.press('Escape');
  await pM.waitForTimeout(700);
  const mE = await fsState(pM);
  // ⑨ 同一件事在**手机那一档**（真会撞的地方）：一句 31 字在 390px 宽里装不下，
  //    没让开的话它的右端正好从按钮底下穿过去。★ 这一格在没改内边距时会红 —— 那正是我要的牙。
  const mINK = await inkOf(pM);
  await cM.close();
  const covers = mA.fake && Math.abs(mA.main.x) <= 1 && Math.abs(mA.main.y) <= 1
    && Math.abs(mA.main.w - mA.vw) <= 1 && Math.abs(mA.main.h - mA.vh) <= 1;
  ck('退路那一档（原生全屏被禁的手机档）：自己**铺满窗口**、图层开关照点、**Esc 退得掉**',
     covers && mChip.before !== mChip.after && !mE.fake && !mE.full,
     `原生被禁 ⇒ fake=${mA.fake}　main ${mB.main.w}×${mB.main.h} → ${mA.main.w}×${mA.main.h} @(${mA.main.x},${mA.main.y})　视口 ${mA.vw}×${mA.vh}`
     + `　铺满=${covers}　图层开关 ${mChip.before} → ${mChip.after}（全屏里能点的图层开关共 ${mChip.n} 颗）`
     + `　Esc 之后 fake=${mE.fake}／full=${mE.full}`
     + `　★ 按钮在这档里 ${mA.btn.w}×${mA.btn.h}（触控目标要 ≥ 24）`);

  ck('手机那一档：同一句话（31 字）在窄屏里也**不许钻到按钮底下**（桌面宽，这一格量不出来才要单开）',
     !!mINK && !mINK.hit && mINK.gap >= 4,
     mINK ? `屏 ${mINK.vw}　字 ${mINK.ink.l}→${mINK.ink.r}（宽 ${mINK.ink.r - mINK.ink.l}）　按钮 ${mINK.btn.l}→${mINK.btn.r}`
       + `　⇒ 字右沿离按钮左沿 ${mINK.gap} px（要 ≥ 4）　那句话的盒子宽 ${mINK.box}　左右内边距 ${mINK.pad}`
       + `　字换了几行：${mINK.ink.b - mINK.ink.t} px 高` : '★ 页面上没有 #notice');

  // ---------------------------------------------------------------- 盘整组（卡 card-9f7a80b6-e8a，小栋 10-07 选 C）
  // 相邻盘整段在图上标成一组：细轨 ＋ 段界 k/N ＋ 吸左的标签 ＋「屏内 第 a–b 段」＋ 两头「还有 n 段」＋ 悬停引原文。
  // ★ 线上有没有组**看行情**（今天有、明天可能没有）⇒ 画的那几格不等行情：拿真载荷，把图头以外的段
  //   **就地改成盘整**再重画一帧 —— 量的是画法和接线，组从哪儿来不归这一格管（分组口径在 ㊵ 用纯函数钉）。
  //   不改的话这几格会在"今天这张图恰好没有组"时变成死闸：一格都没量，照样绿。
  const pPZ = await (await b.newContext({ viewport: { width: 1600, height: 900 } })).newPage();
  await pPZ.goto(PAGE + QS, { waitUntil: 'domcontentloaded' });
  await waitData(pPZ);
  await pPZ.waitForTimeout(1500);
  // ㊵ 分组口径（纯函数，`走势分段.md` §八 第 9 条）：盘整连排 ≥2 段成组；升级·盘整算；无中枢断开；**图头不算**
  const pzPure = await pPZ.evaluate(async () => {
    const L = await import('/layers.js');
    const S = (type, i0, i1, x = {}) => ({ type, i0, i1, ...x });
    const run = (segs) => L.pzGroups({ segments: segs }).map((g) => [g.from, g.to]);
    const cases = {
      head: run([S('盘整', 0, 9, { head: true }), S('盘整', 9, 20), S('上涨', 20, 30)]),             // 图头 + 1 段 ⇒ 不成组
      upg: run([S('盘整', 0, 9, { head: true }), S('盘整', 9, 20, { upgraded: true }), S('盘整', 20, 30)]),  // ⇒ [[1,2]]
      wu: run([S('盘整', 0, 9), S('无中枢', 9, 20), S('盘整', 20, 30)]),                              // 无中枢断开 ⇒ []
      two: run([S('下跌', 0, 9), S('盘整', 9, 20), S('盘整', 20, 30), S('盘整', 30, 40), S('上涨', 40, 50), S('盘整', 50, 60), S('盘整', 60, 70)]),
    };
    // 划分自检：一个 9 段的组，扫一遍各种视野，`左在外 + 屏内 + 右在外 = 9` 必须处处成立
    const g = L.pzGroups({ segments: Array.from({ length: 9 }, (_, k) => S('盘整', k * 100, (k + 1) * 100)) })[0];
    let worst = null, tried = 0;
    for (let a = -50; a < 950; a += 37) for (let w = 10; w < 700; w += 61) {
      const r = L.pzWhere(g, a, a + w); tried++;
      if (r.before + r.inView + r.after !== g.n && !worst) worst = { a, w, ...r };
    }
    return { cases, tried, worst };
  });
  ck('㊵ 盘整组的口径（纯函数）：图头不算／升级·盘整算／「无中枢」断开／一张图里可以有几组；划分自检 左在外＋屏内＋右在外＝组内段数',
     JSON.stringify(pzPure.cases) === JSON.stringify({ head: [], upg: [[1, 2]], wu: [], two: [[1, 3], [5, 6]] }) && !pzPure.worst,
     `${JSON.stringify(pzPure.cases)}　视野扫了 ${pzPure.tried} 种${pzPure.worst ? '　✗ 对不上：' + JSON.stringify(pzPure.worst) : '，处处对得上'}`);

  // 强行造一组：图头以外全改盘整，视野放在组的中间（两头都在屏外）
  const pzForce = await pPZ.evaluate(async () => {
    const app = window.__app, ts = app.chart.timeScale(), segs = app.state.data.trend.segments;
    for (const s of segs) if (!s.head) s.type = '盘整';
    const body = segs.filter((s) => !s.head);
    const v = ts.getVisibleLogicalRange(), w = Math.min(v.to - v.from, (body.at(-1).i1 - body[0].i0) / 3);
    const m = (body[0].i0 + body.at(-1).i1) / 2;
    ts.setVisibleLogicalRange({ from: m - w / 2, to: m + w / 2 });
    await new Promise((r) => setTimeout(r, 900));
    const d = app.state.pzDrawn, lb = app.state.labelBoxes, vv = ts.getVisibleLogicalRange();
    const g = d.groups[0] || null;
    // 屏内几段：自己另数一遍（不抄 pzWhere）
    const mine = g ? body.filter((s) => s.i1 >= vv.from && s.i0 <= vv.to).length : -1;
    const tail = g ? lb.slice(-g.chips.length).map((b) => b.slice(0, 4).map(Math.round).join(',')) : [];
    // 刻度字跟这一帧已经画上去的字（走势那层的 labels ＋ 标注层的 placed）**像素不交叠**
    const others = [...((app.state.trendDrawn || {}).labels || []), ...lb];
    const hit = (b) => others.some((q) => b[0] < q[2] && q[0] < b[2] && b[1] < q[3] && q[1] < b[3]);
    const tl = g ? g.tickLabels : [];
    const tlBad = tl.filter((t) => t.box && hit(t.box)).map((t) => t.k);
    return { nBody: body.length, H: d.H, pane: app.chart.panes()[0].getHeight(),
      chartH: Math.round(document.querySelector('#chart').getBoundingClientRect().height), railY: d.railY,
      tl: tl.map((t) => [t.k, t.side]), tlBad, nOthers: others.length,
      groups: d.groups.length, g, mine, tail, chipBoxes: g ? g.chips.map((c) => c.box.map(Math.round).join(',')) : [] };
  });
  const pg = pzForce.g;
  ck('㊶ 盘整组画出来了：一组、标签写组内实数、两头都在屏外 ⇒ 位置 chip ＋ 两头「还有 n 段」都在',
     pzForce.groups === 1 && !!pg && pg.n === pzForce.nBody && pg.chips[0]?.text === `同一更大横盘 · ${pzForce.nBody} 段`
       && pg.chips.length === 2 && pg.before > 0 && pg.after > 0,
     pg ? `组 ${pzForce.groups}　段 ${pg.n}（载荷里图头以外 ${pzForce.nBody}）　chip ${JSON.stringify(pg.chips.map((c) => c.text))}`
       + `　左在外 ${pg.before}／屏内 ${pg.inView}（第 ${pg.lo}–${pg.hi}）／右在外 ${pg.after}　刻度 ${JSON.stringify(pg.ticks)}` : '★ 一组都没画');
  ck('㊷ 划分自检（真画的那一帧）：左在外＋屏内＋右在外＝组内段数，屏内段数跟另数的一遍对得上',
     !!pg && pg.before + pg.inView + pg.after === pg.n && pg.inView === pzForce.mine,
     pg ? `${pg.before} + ${pg.inView} + ${pg.after} = ${pg.before + pg.inView + pg.after}（组 ${pg.n}）　另数屏内 ${pzForce.mine}` : '');
  ck('㊸ 细轨贴的是**价格窗格**的底边：H ＝ panes()[0] 的高、≠ #chart 的高（底下还有成交量／MACD）',
     pzForce.H === pzForce.pane && pzForce.H !== pzForce.chartH && pzForce.railY < pzForce.H,
     `H ${pzForce.H}　价格窗格 ${pzForce.pane}　#chart ${pzForce.chartH}　细轨 y=${pzForce.railY}`);
  ck('㊹ 避让：两块 chip **最后登记**（买卖点文字 → 价签 → 我）⇒ 让路的是我，老标签不动',
     pzForce.tail.length > 0 && JSON.stringify(pzForce.tail) === JSON.stringify(pzForce.chipBoxes),
     `登记表末尾 ${JSON.stringify(pzForce.tail)}　chip ${JSON.stringify(pzForce.chipBoxes)}`);

  ck('㊾ 刻度字 k/N 不压别的字：跟分界价格字、价签、买卖点文字、chip 像素都不交叠（撞了翻边，两边都撞就只画刻度）',
     pzForce.tl.length > 0 && pzForce.tlBad.length === 0,
     `刻度 ${JSON.stringify(pzForce.tl)}（r＝右／l＝左／null＝只画刻度）　比了 ${pzForce.nOthers} 块字　交叠的 ${JSON.stringify(pzForce.tlBad)}`);

  // ㊾b 牙：把一条分界的价格**挪到刻度字正上方**（那个价字会落进刻度字右边那一格），再画一帧 ——
  //   刻度字必须翻边或者不写，而且 `blockedR` 得是真的（证明这一帧真撞过，不是碰巧没东西挨着）。
  const pzBump = await pPZ.evaluate(async () => {
    const app = window.__app, ts = app.chart.timeScale(), T = app.state.data.trend;
    const g = app.state.pzDrawn.groups[0]; if (!g || !g.tickAt.length) return { err: '没有刻度' };
    const { k, x } = g.tickAt[0]; const bar = Math.round(ts.coordinateToLogical(x));
    const b = T.bounds.reduce((m, q) => (Math.abs(q.bar - bar) < Math.abs(m.bar - bar) ? q : m));
    const y = app.state.pzDrawn.railY + (b.kind === 'H' ? 6 : -24);
    b.price = app.state.candleSeries.coordinateToPrice(y);
    const v = ts.getVisibleLogicalRange(); ts.setVisibleLogicalRange({ from: v.from + 0.01, to: v.to + 0.01 });
    await new Promise((r) => setTimeout(r, 700));
    const gg = app.state.pzDrawn.groups[0], t = gg.tickLabels.find((q) => q.k === k);
    const others = [...app.state.trendDrawn.labels, ...app.state.labelBoxes];
    const hit = (bx) => others.some((q) => bx[0] < q[2] && q[0] < bx[2] && bx[1] < q[3] && q[1] < bx[3]);
    return { k, kind: b.kind, side: t.side, blockedR: t.blockedR, overlap: !!(t.box && hit(t.box)) };
  });
  ck('㊾b （牙）分界价格字挪到刻度字右边那一格上 ⇒ 刻度字换一格或只画刻度，仍然不交叠',
     !pzBump.err && pzBump.blockedR === true && pzBump.side !== 'r' && !pzBump.overlap,
     JSON.stringify(pzBump));

  // ㊺ 悬停那块标签 ⇒ 出原文那句（第 38 课正文 ＋ 第 45 课答疑）
  const chipBox = pg && pg.chips[0] ? pg.chips[0].box : null;
  let tipTxt = '';
  if (chipBox) {
    const cr = await pPZ.evaluate(() => { const c = document.querySelector('#chart canvas'); const r = c.getBoundingClientRect(); return { x: r.left, y: r.top }; });
    await pPZ.mouse.move(cr.x + (chipBox[0] + chipBox[2]) / 2, cr.y + (chipBox[1] + chipBox[3]) / 2);
    await pPZ.waitForTimeout(300);
    tipTxt = await pPZ.evaluate(() => { const t = document.getElementById('ghosttip'); return t && t.classList.contains('on') ? t.textContent : ''; });
  }
  ck('㊺ 悬停标签 ⇒ 说明里引第 38 课正文和第 45 课答疑，并说明分界没动',
     /第 38 课/.test(tipTxt) && /第 45 课答疑/.test(tipTxt) && /分界照旧/.test(tipTxt),
     tipTxt ? `「${tipTxt.slice(0, 40)}…」` : '★ 没出说明');

  // ㊻ 组头滚到屏内 ⇒ 标签贴组头；组头滚出左边 ⇒ 标签吸视口左边（x=8）
  const pzEdge = await pPZ.evaluate(async () => {
    const app = window.__app, ts = app.chart.timeScale(), body = app.state.data.trend.segments.filter((s) => !s.head);
    const v = ts.getVisibleLogicalRange(), w = v.to - v.from, i0 = body[0].i0;
    ts.setVisibleLogicalRange({ from: i0 - w * 0.3, to: i0 + w * 0.7 });
    await new Promise((r) => setTimeout(r, 700));
    const a = app.state.pzDrawn.groups[0];
    const xa = ts.logicalToCoordinate(i0);
    return { inX: a ? Math.round(a.chips[0].box[0]) : null, xa: Math.round(xa), leftOut: a ? a.leftOut : null, before: a ? a.before : null };
  });
  ck('㊻ 组头在屏内 ⇒ 标签贴着组头（不吸左边）、左边不写「还有 n 段」',
     pzEdge.leftOut === false && pzEdge.before === 0 && Math.abs(pzEdge.inX - Math.max(8, pzEdge.xa + 6)) <= 1,
     `组头 x=${pzEdge.xa}　标签左沿 ${pzEdge.inX}　leftOut=${pzEdge.leftOut}　左在外 ${pzEdge.before}`);
  ck('㊼ 组头在屏外 ⇒ 标签吸视口左边（x=8）',
     !!pg && pg.leftOut && Math.round(pg.chips[0].box[0]) === 8, pg ? `标签左沿 ${Math.round(pg.chips[0].box[0])}` : '');

  // ㊽ 「走势分段」芯片关掉 ⇒ 组一笔不画、命中格也清空（指着原来那块不再出话）
  await pPZ.evaluate(() => document.querySelector('.chip[data-key="trend"]').click());
  await pPZ.waitForTimeout(700);
  const pzOff = await pPZ.evaluate(() => ({ g: window.__app.state.pzDrawn.groups.length,
    on: document.querySelector('.chip[data-key="trend"]').getAttribute('aria-pressed') }));
  let tipOff = '';
  if (chipBox) {
    const cr = await pPZ.evaluate(() => { const c = document.querySelector('#chart canvas'); const r = c.getBoundingClientRect(); return { x: r.left, y: r.top }; });
    await pPZ.mouse.move(cr.x + 3, cr.y + 3);
    await pPZ.mouse.move(cr.x + (chipBox[0] + chipBox[2]) / 2, cr.y + (chipBox[1] + chipBox[3]) / 2);
    await pPZ.waitForTimeout(300);
    tipOff = await pPZ.evaluate(() => { const t = document.getElementById('ghosttip'); return t && t.classList.contains('on') ? t.textContent : ''; });
  }
  ck('㊽ 关掉「走势分段」⇒ 盘整组一笔不画，原来标签那块也不再出说明',
     pzOff.on === 'false' && pzOff.g === 0 && !/第 45 课答疑/.test(tipOff),
     `芯片 aria-pressed=${pzOff.on}　画了 ${pzOff.g} 组　悬停 ${tipOff ? '「' + tipOff.slice(0, 20) + '…」' : '无'}`);
  await pPZ.context().close();

  await b.close();
  console.log(`\n${n - bad}/${n} 过${bad ? `，${bad} 条红` : ''}　截图：${OUT}`);
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.error('炸了：', e.message); process.exit(2); });

// 不带默认页面地址（部署细节不进仓，card-58518cb5-357）：没给 E2E_URL、也没给地址参数，就直接报错、退出码 2（环境没搭好）。
// predeploy 会 export E2E_URL。写法跟 tools/web_fs_drag_e2e.js 一致。
function noUrl() {
  console.error('缺页面地址：请设 E2E_URL（或把页面地址当参数）。本工装不带默认地址。');
  process.exit(2);
}
