// 手机上「图那一栏占屏高」＝多少？（卡 card-c7f19e45-022 的验收尺）★ 要**真后台**。
//
// 口径（跟 card-b9792318-91d 那次一致，能横向比）：
//   图那一栏 = `#chart` 的 getBoundingClientRect().height ÷ window.innerHeight，四舍五入成整数百分。
//   ★ 必须在**真后台**上量：离线样本缺 `fetched_at` ⇒ 角上少一句「数据 … 刷新」⇒ 徽标短 ⇒ 顶栏矮 ⇒
//     量出来的占比**偏高**（假后台 85%，真形状 82%）。这是这条尺存在的第一个理由。
//
// 为什么要写成尺：2026-10-04 我在页面上加了 `nowrap` 量出个 82%，实际是**内容冲出屏幕**（360 上超 116px），
//   不是「一行放得下」—— 拿溢出当放下的数**比没有数还坏**。所以这尺不只量占比，还量「有没有东西被挡」：
//     ①②③ 占比 ≥80%（360/390/430 三个宽）、顶栏 ≤ 两行、徽标那一行**不溢出**（scrollWidth ≤ clientWidth）
//     ④   收起开关（#fold）**不占行**：它得在图层条那一行里、body 的网格里没有它自己的一格
//     ⑤   图层条**滑到头**时，最后一颗 chip 不许停在开关底下（开关右边给的那一格够不够宽）
//     ⑥   桌面 1280×860 上角上是**全写**（带日期），开关不在（display:none）—— 防的是「为了手机改了桌面」
//
// 跑法：
//   1) cd <这个仓的一份检出> && python3 web/server.py --port <端口> --no-prewarm   （只绑回环）
//   2) NODE_PATH=<playwright 的 node_modules> node tools/web_mobile_share.js [页面地址]
//   退出码：0＝六条都过；1＝有判据没过（把没过的那条连数一起印出来）；2＝环境没搭好（没用真后台/页面没起来）。
const Page = (process.env.E2E_URL || (process.argv[2] && !process.argv[2].startsWith('--')
  ? process.argv[2] : noUrl())).replace(/\/?$/, '/');   // E2E_URL 优先（上线门统一给，card-9b0fe913-758）
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch (e) {
  console.error('✗ 没装 playwright。`npm i playwright && npx playwright install chromium`，'
                + '再用 NODE_PATH=<那个 node_modules> 跑这个文件。');
  process.exit(2);
}
const WIDTHS = [360, 390, 430];
const HEIGHT = 844;
const MIN_SHARE = 80;                        // 卡上写的目标
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** 在这一页上把该量的都量下来（都用 rect —— 像素证据，不看 computedStyle） */
const probe = (p) => p.evaluate(() => {
  const R = (e) => (e ? e.getBoundingClientRect() : null);
  const r2 = (x) => (x ? { top: Math.round(x.top), right: Math.round(x.right), bottom: Math.round(x.bottom),
                           left: Math.round(x.left), w: Math.round(x.width), h: Math.round(x.height) } : null);
  const box = document.querySelector('.badges');
  const badges = [...document.querySelectorAll('.badges .badge')];
  const panel = document.getElementById('panel');
  const fold = document.getElementById('fold');
  // 条子里**所有**东西（chip、组标题、组本身）—— 滑到头之后，最右边那一条边在哪
  const items = [...panel.querySelectorAll('.chip, .mcap, .mgroup')];
  panel.scrollLeft = panel.scrollWidth;                    // 滑到头：条子最右端的东西露不露得出来
  return {
    chart: r2(R(document.getElementById('chart'))),
    bar: r2(R(document.querySelector('header.bar'))),
    badges: r2(R(box)), badgeOver: box.scrollWidth - box.clientWidth,
    badgeRows: new Set(badges.map((e) => Math.round(e.getBoundingClientRect().top / 4))).size,
    badgeText: badges.map((e) => e.textContent.trim()),
    panel: r2(R(panel)), fold: r2(R(fold)), foldTx: (document.getElementById('fold-tx') || {}).textContent || null,
    panelPadRight: getComputedStyle(panel).paddingRight,
    foldDisplay: fold ? getComputedStyle(fold).display : null,
    // 滑到头之后条子里**最靠右**的那条边（不是"最后一个 DOM 元素"：看法那一组是 order:10，
    // DOM 里排在前、画在最后 —— 按 DOM 取会取到一颗**不在右边**的 chip，那一格就成了空转格）
    stripRight: items.length ? Math.max(...items.map((e) => Math.round(e.getBoundingClientRect().right))) : null,
    stripRightOf: items.length
      ? items.map((e) => [e.textContent.trim().slice(0, 6), Math.round(e.getBoundingClientRect().right)])
        .sort((a, b) => b[1] - a[1])[0]
      : null,
    // body 的网格行：开关要是还占着自己一格，这里就会多一行（40px 那种高度）
    bodyRows: getComputedStyle(document.body).gridTemplateRows,
    vh: window.innerHeight,
    state: (document.getElementById('state') || {}).textContent || '',
    updated: (document.getElementById('updated') || {}).textContent || '',
    // ★ 角上那两个时刻现在按**浏览器本地时区**印（card-e7554dd2-44a）。这一格量的是宽度，
    //   所以除了形状还得知道"本根那半真按本地印了"——期望值**由页面自己印**（不写死几点：
    //   写死的判据量的是跑工装那台机器的时区，不是页面）。payload 的 `updated` 跟跳价无关，不会飘。
    barLocal: window.__app.shortLocal((window.__app.state.data || {}).updated),
    // 「数据」那格用的是 `tickAt || fetched_at`（两者都在"现在"这一两分钟里，跨零点那一下可以忽略）。
    // 这里只要**日期**对不对，用 fetched_at 就够。
    fetchLocal: window.__app.shortLocal((window.__app.state.data || {}).fetched_at),
  };
});
const share = (m) => Math.round((m.chart.h / m.vh) * 100);
const overlap = (a, b) => (a && b ? Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)) : 0);

// ⑦ **注入一条 iPhone 底部安全区**（34px，就是那条横条）：收起／展开两态，开关都得贴在图层条那一行里。
//   为什么非得注入：playwright 给的 `env(safe-area-inset-bottom)` 是 0 —— 这个病在工装里**天然量不到**，
//   是真机上才会踩的（Atlas 2026-10-04 复核 e72d11e 时抓到的：他把 CSS 里那几处 env() 换成 34px 才看见）。
//   病的形状：`.fold` 的 bottom **一直**加着安全区，而 `.panel` 只在**收起**时加 ⇒ 展开态开关比自己那一行
//   高 34px：390×844 上开关 589–619、图在 614 结束 ⇒ **压住图的最底下 25px**，还离开了图层条（条在 614–661）。
//   注入口径：把送出去的 style.css 里 `env(safe-area-inset-bottom, 0px)` 全换成 34px（跟真机上那条一样宽）。
//   ★ 锚点先数：一处都没换到 ⇒ 这格是空的（rc=2 报出来），不许静悄悄绿。
const SAFE_PX = 34;
// ★ 基准取**条子里那些 chip 自己**的上下沿（＝那一行的内容），**不是 `#panel` 的 rect**：
//   rect 里含着收起时那 42px 的安全区内边距，拿它当基准，收起态会算出一个假的 -42px（第一版就是这么错的）。
const probeFold = (p) => p.evaluate(() => {
  const r = (e) => { const b = e.getBoundingClientRect();
    return { top: Math.round(b.top), bottom: Math.round(b.bottom), left: Math.round(b.left), right: Math.round(b.right) }; };
  const panel = document.getElementById('panel');
  const chips = [...panel.querySelectorAll('.chip')].map((e) => e.getBoundingClientRect());
  return { chart: r(document.getElementById('chart')), panel: r(panel),
           row: chips.length ? { top: Math.round(Math.min(...chips.map((c) => c.top))),
                                 bottom: Math.round(Math.max(...chips.map((c) => c.bottom))) } : null,
           padBottom: getComputedStyle(panel).paddingBottom,
           fold: r(document.getElementById('fold')), tx: document.getElementById('fold-tx').textContent };
});

(async () => {
  const b = await chromium.launch();
  const bad = [], lines = [];
  const say = (ok, name, detail) => {
    lines.push(`  ${ok ? '✓' : '★'} ${name}\n      ${detail}`);
    if (!ok) bad.push(name);
  };
  {
    const ctx = await b.newContext({ viewport: { width: 390, height: HEIGHT }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
    const p = await ctx.newPage();
    let hits = 0;
    await p.route('**/style.css*', async (route) => {
      const r = await route.fetch();
      const t = await r.text();
      hits = (t.match(/env\(safe-area-inset-bottom, 0px\)/g) || []).length;
      await route.fulfill({ status: 200, contentType: 'text/css',
        body: t.replace(/env\(safe-area-inset-bottom, 0px\)/g, `${SAFE_PX}px`) });
    });
    await p.goto(`${Page}?symbol=ZECUSDT&tf=1h`, { waitUntil: 'domcontentloaded' });
    await p.waitForFunction(() => window.__app && window.__app.state.data, null, { timeout: 30000 }).catch(() => {
      console.error('✗ 注入那一格：页面没起来（后台没起？）'); process.exit(2); });
    await sleep(1000);
    if (!hits) { console.error('✗ 注入那一格：style.css 里一处 env(safe-area-inset-bottom, 0px) 都没换到 —— 锚点没命中，这格是空的。'); process.exit(2); }
    const shut = await probeFold(p);
    await p.evaluate(() => document.getElementById('fold').click());
    await sleep(400);
    const open = await probeFold(p);
    await p.evaluate(() => document.getElementById('fold').click());     // 点回去，别影响别的格
    // 收起／展开两态：开关都跟**那一行的 chip** 同一条底边（安全区两处一起加、或者一起不加）
    const 对齐 = (m) => m.row && Math.abs(m.fold.bottom - m.row.bottom) <= 2;
    // 展开：不压图 —— 真实的矩形相交，不是比谁的下沿大（开关在图的下面、各有各的带子）
    const 压图 = (m) => Math.max(0, Math.min(m.fold.bottom, m.chart.bottom) - Math.max(m.fold.top, m.chart.top));
    say(对齐(shut) && 对齐(open) && 压图(open) <= 1,
      `⑦ 390 注入 ${SAFE_PX}px 底部安全区：收起／展开两态开关都跟 chip 同一条底边、且不压图`,
      `换了 ${hits} 处 env()；收起：开关底 ${shut.fold.bottom} vs chip 行底 ${shut.row.bottom}`
      + `（差 ${shut.fold.bottom - shut.row.bottom}px，条内边距 ${shut.padBottom}）；`
      + `展开：开关 ${open.fold.top}–${open.fold.bottom} vs chip 行 ${open.row.top}–${open.row.bottom}、`
      + `图 ${open.chart.top}–${open.chart.bottom}（开关「${open.tx}」）⇒ 压图 ${压图(open)}px`
      + (对齐(shut) && 对齐(open) && 压图(open) <= 1 ? ''
         : '　★ 两态的安全区口径必须一样（跟 `.panel` 那条）：收起时两边一起加、展开时两边一起不加'));
    await ctx.close();
  }
  for (const W of WIDTHS) {
    const ctx = await b.newContext({ viewport: { width: W, height: HEIGHT }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
    const p = await ctx.newPage();
    await p.goto(`${Page}?symbol=ZECUSDT&tf=1h`, { waitUntil: 'domcontentloaded' });
    try {
      await p.waitForFunction(() => window.__app && window.__app.state.data, null, { timeout: 30000 });
    } catch (e) {
      console.error(`✗ ${W} 宽上页面没起来（等不到 window.__app.state.data）—— 这是假后台或者后台没起，不是页面错。`);
      process.exit(2);
    }
    await sleep(1000);                                     // 让布局（含 LWC 的 resize）定下来
    const m = await probe(p);
    say(share(m) >= MIN_SHARE, `① ${W}×${HEIGHT} 图那一栏占屏高 ≥${MIN_SHARE}%`,
      `图 ${m.chart.h}px / 屏 ${m.vh}px = **${share(m)}%**；顶栏 ${m.bar.h}px、图层条 ${m.panel.h}px`);
    say(m.badgeRows <= 2, `② ${W} 顶栏里徽标 ≤ 两行`,
      `徽标 ${m.badgeRows} 行、各占 ${m.badges.h}px 高；顶栏共 ${m.bar.h}px`);
    say(m.badgeOver <= 1, `③ ${W} 徽标那一行**没有**冲出屏幕`,
      `内容 ${m.badges.w + m.badgeOver}px / 框 ${m.badges.w}px ⇒ 溢出 ${m.badgeOver}px`
      + '（溢出＝看不见的字；`nowrap` 那次的 82% 就是这么来的）');
    // ④ 开关「不占行」怎么量：它是 body 的一格时，body 的网格里会有 20–40px 的一行（那行是 29.5px）。
    const rows = m.bodyRows.split(/\s+/).map(parseFloat).filter((v) => v > 0);
    const inPanel = m.fold && m.fold.top >= m.panel.top - 1 && m.fold.bottom <= m.panel.bottom + 1;
    say(!!inPanel && !rows.some((h) => h >= 20 && h <= 40),
      `④ ${W} 收起开关钉在图层条那一行里、自己不占一行`,
      `开关 y ${m.fold.top}–${m.fold.bottom}「${m.foldTx}」；图层条 y ${m.panel.top}–${m.panel.bottom}；`
      + `body 网格行 ${m.bodyRows}（非零行 ${rows.join('/')} —— 那个 29.5px 的一行该没了）`);
    say(m.stripRight !== null && m.fold && m.stripRight <= m.fold.left + 1,
      `⑤ ${W} 图层条滑到头，条子里最右的东西不藏在开关底下`,
      `滑到头后最靠右的是「${m.stripRightOf[0]}」（右边缘 ${m.stripRightOf[1]}）；开关左边 ${m.fold.left}`
      + ` ⇒ ${m.stripRight <= m.fold.left + 1 ? '露出一条缝' : `**被盖住 ${m.stripRight - m.fold.left}px**`}`
      + `（条子右边留的那一格 padding-right=${m.panelPadRight}）`);
    await ctx.close();
  }
  // ⑥ 桌面：一个字不动（角上是全写：带日期；开关不显示）
  const ctx = await b.newContext({ viewport: { width: 1280, height: 860 } });
  const p = await ctx.newPage();
  await p.goto(`${Page}?symbol=ZECUSDT&tf=1h`, { waitUntil: 'domcontentloaded' });
  await p.waitForFunction(() => window.__app && window.__app.state.data, null, { timeout: 30000 }).catch(() => process.exit(2));
  await sleep(1000);
  const d = await probe(p);
  // ★ 串的形状必须**整条**对上 —— 这一格量的是宽度（徽标多长 ⇒ 顶栏多高 ⇒ 图占比），
  //   少写一段就少量一截。末尾那格 `UTC+8` 是 card-e7554dd2-44a 加的，必须算进宽度里。
  //   ★ 「数据」那格的日期是**可选**的：跟本根同一天（本地）时页面会省掉它（app.js 的 sameDay，
  //     那两个日期重复本来就只是噪音，省下来正好付时区那格的账）。所以这里不能钉死带日期那种，
  //     否则真后台跑在正常的一天里这条会**假红**。
  //   ★ 只钉形状、不钉"具体几点"：那个归 web_ghost_e2e ⑯g2（那边拿页面自己印的字当期望值）。
  //   ★ 尾部不锚 `$`：stale 的时候后面还会跟一句「｜ ★ 旧数据（…）」。
  const full = /^本根 \d{4}-\d{2}-\d{2} \d{2}:\d{2} 开盘 ｜ 数据 (\d{4}-\d{2}-\d{2} )?\d{2}:\d{2} 刷新 ｜ UTC[+-]\d{1,2}(:\d{2})?/.test(d.updated);
  // ★ 省日期这件事只在**同一天**才许发生 —— 判据得自己盯着这条前提，不然"哪一格少写了"
  //   会变成一种没人守的静默自由（少了日期的那格读起来跟本根同一天，这是它成立的全部理由）。
  //   `barLocal`／`fetchLocal` 都是页面自己印的本地字，工装只比前缀。
  const sameDay = d.barLocal.slice(0, 10) === d.fetchLocal.slice(0, 10);
  const dateOk = sameDay ? !/数据 \d{4}-\d{2}-\d{2}/.test(d.updated) : /数据 \d{4}-\d{2}-\d{2} \d{2}:\d{2} 刷新/.test(d.updated);
  // ★ 再钉一条**它真的是本地钟**：`barLocal` 是页面拿本地取值器印出来的同一刻。这条是冲着
  //   「有人把它改回 UTC」去的 —— 只钉形状的判据在 UTC 机器上照样绿，挡不住那个错。
  //   空串要先挡掉（印不出来 ⇒ 红），不然 `startsWith('本根  开盘')` 那种恒假/恒真的空隙会漏。
  const localOk = d.barLocal !== '' && d.updated.startsWith(`本根 ${d.barLocal} 开盘`);
  const liveFull = /^(已收盘|未收盘（最后一根还在走）)$/.test(d.state);
  say(full && localOk && dateOk && liveFull && d.foldDisplay === 'none',
    '⑥ 桌面 1280×860 角上还是**全写**、开关不在',
    `「${d.updated}」／「${d.state}」；本根那一刻本地念「${d.barLocal || '（印不出来 ⇒ 红）'}」；`
    + `两个时刻${dateOk ? '' : '**日期该省没省 / 该写没写** ⇒ 红'}；`
    + `开关 display:${d.foldDisplay}，图 ${d.chart.h}/${d.vh} = ${share(d)}%`);
  await ctx.close();
  await b.close();
  console.log(`\n== 手机图占比（真后台 ${Page}）==\n` + lines.join('\n'));
  console.log(bad.length
    ? `\n★ ${bad.length} 条没过：\n  - ` + bad.join('\n  - ')
    : `\n✓ 七条全过（${WIDTHS.join('/')} 三个宽都 ≥${MIN_SHARE}%）—— 改前是 78%（徽标两行 106px）`
      + `＋ 收起开关自己占 29.5px 一行；⑦ 那条（注入 ${SAFE_PX}px 安全区）改前展开态压住图 25px。`);
  process.exit(bad.length ? 1 : 0);
})().catch((e) => { console.error('尺自己炸了：', e.message); process.exit(2); });

// 不带默认页面地址（部署细节不进仓，card-58518cb5-357）：没给 E2E_URL、也没给地址参数，就直接报错、退出码 2（环境没搭好）。
// predeploy 会 export E2E_URL。写法跟 tools/web_fs_drag_e2e.js 一致。
function noUrl() {
  console.error('缺页面地址：请设 E2E_URL（或把页面地址当参数）。本工装不带默认地址。');
  process.exit(2);
}
