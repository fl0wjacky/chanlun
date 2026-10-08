// 「副图页头拿『格高 0』摆位置」这件事，能不能钉住？（真后台；card-9b0fe913-758）
//
// 缘由：macd_axis 工装「重建后⑨」那一格**忽红忽绿**（Iris 2026-10-05 抓了两头的读数，
//   改前 `62/63`、改后 `63/63`，同一棵树上也能翻）。那格的病灶在**页面**这一侧：
//
//   病灶：`placeSubhead()` 里页头的 top 是拿 `pane.getHeight()` 减出来的
//     （格高 172 ⇒ 该 514px）。窗格刚建、LWC 还没把它排出来时 `getHeight()` 是 **0**
//     ⇒ 按 0 算就是 686px ＝ 514＋172，**页头低一整格**、掉到副图下面去。
//     而这一拍之后**不一定还有下一趟**：`syncSub()` 认出「还是这一格」就直接返回，
//     不再取数、不再重画 ⇒ 错的值**一直挂着**（连点两次开关就进这个状态，等 2.6 秒也没人修）。
//   修法（`agent/iris/macd-axis-settle` ＝ `68decdd`）：拿不到格高就**不摆**，下一帧再试，
//     最多等 500ms（图被藏起来时高度永远是 0，不空转）。
//
// 判据（**一条**，看用户看得见的那一格）：
//   每一种「关 → 开」的节奏，等版面稳定之后，**页头必须贴着副图格顶**：相对格顶 ≤ 40px。
//   量的是 subhead 的 `rect.top` 减第二个 pane 的 `rect.top`：贴住时实测 **6px**，低一整格时 **178px**。
//   ★ 阈值 40 不是拍脑袋：实测两档分离度 6 vs 178，40 落在正中间。
//   ★ 「相对格顶」是**结构量**，不是像素复刻：换窗口／字号／格高，6 和 178 都跟着变，
//     但它们永远是「贴住」和「低一整格」两档，这条线不会因此翻。
//   ★ 为什么量「用户看得见的」而不是量「末趟调用的 h」：`h !== 0` 是**机制**，可能被别的写法实现；
//     页头贴不贴格顶是**结果**，怎么写都得对。机制写进台账（下面印 `h=…→…px` 那一串），
//     但它不参与判定。
//
// 跑法（要**真后台**：`web/app.js` 得能取到真数据）：
//   1) python3 web/server.py --port <端口> --no-prewarm      （只绑回环）
//   2) NODE_PATH=<playwright 的 node_modules> node tools/web_subhead_slot_probe.js [页面地址]
//        [--self-test]  牙齿自检：把 app.js 里那道「拿不到格高就不摆」的闸**改成 `if (false)`**
//                       （＝回到修之前），要求**至少一个节奏变红**。一个都不红 ⇒ 这条判据是死的 ⇒ 退 1。
//   页面地址：`E2E_URL` 优先（上线门统一给，card-9b0fe913-758），其次第一个**长得像 URL 的**参数，最后 8795。
//     ★ 只认 `http(s)://` 开头的参数：`tools/predeploy.sh` 给每一套传的 argv[2] 是**截图目录**，
//       不是地址（地址走 E2E_URL）。要是不加这道判，手跑一次 `node 本文件 /tmp/xxx` 就会把 tmp 路径当地址。
//   退出码：0＝每个节奏都贴住（`--self-test` 下＝确实变红了）；1＝有节奏没贴住／自检没牙；2＝环境没搭好或**没接上钩**。
//
// ★★ 两处「静默失效」一律记**没比成（2）**、**绝不当绿**：
//   ① 源码里那两处勾子（`function placeSubhead() {`、那道闸那一句）**一个都没命中** ⇒ 替换是空操作、
//      `__ph` 永远是空数组，量到的是「没插上」而不是「没毛病」；
//   ② 整跑一趟 `placeSubhead` **一次都没被调用过** ⇒ 同上（页面结构变了、函数改名了都会这样）。
//   这两条都印出来，别让它悄悄变成绿。
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch (e) {
  console.error('✗ 没装 playwright。先 `npm i playwright && npx playwright install chromium`，' +
                '再用 NODE_PATH=<那个 node_modules> 跑这个文件。');
  process.exit(2);
}
const PAGE = (process.env.E2E_URL
  || process.argv.slice(2).find((a) => /^https?:\/\//.test(a))
  || noUrl()).replace(/\/?$/, '/');
const SELFTEST = process.argv.includes('--self-test');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 帖住 vs 低一整格：实测 6 vs 178，这条线落在中间。
const LIMIT = 40;
// 勾子：把 placeSubhead 改名成 impl，再在同一作用域里补一个**记账版**（记下调用那一刻的格高和它摆出来的 top）。
//   名字里带 `Implementation` 就够独特了，不会有别的调用者。
const TOKEN_FN = 'function placeSubhead() {';
const TOKEN_GATE = 'if (!pane || !pane.getHeight()) {';
const WRAP = `
function placeSubhead() {
  const _p = chart.panes()[1];
  const _h = _p ? _p.getHeight() : null;
  _placeSubheadImpl();
  (window.__ph = window.__ph || []).push({ h: _h, after: subBox ? subBox.style.top : null });
}
`;

// 十二种「关 → 开」节奏：关多久（offms）／开完再等多久看它修不修回来（after）。
//   ★ 短关（0～150ms）＋ 不等，是**已实测能逼出红**的那几档（连点两次开关就是用户的真实操作）。
//   后面几档长间隔留着当对照：它们本来就一直是绿的，红了说明伤到了正常路径。
const ROUNDS = [[0, 0], [0, 50], [0, 300], [200, 500], [1200, 800], [2500, 2500],
                [0, 0], [0, 50], [0, 150], [0, 1000], [2600, 60], [2600, 60]];

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1280, height: 860 }, deviceScaleFactor: 2 });
  const c = await ctx.newPage();
  let hooked = 0, mutated = 0;
  await c.route('**/app.js*', async (route) => {
    const r = await route.fetch();
    let t = await r.text();
    if (t.includes(TOKEN_FN)) {
      hooked++;
      t = t.replace(TOKEN_FN, 'function _placeSubheadImpl() {') + WRAP;
    }
    if (SELFTEST) {
      if (t.includes(TOKEN_GATE)) { mutated++; t = t.replace(TOKEN_GATE, 'if (false) {'); }
    }
    await route.fulfill({ status: 200, contentType: 'text/javascript', body: t });
  });
  await c.goto(PAGE + '?symbol=BTCUSDT&tf=4h&macd=1', { waitUntil: 'domcontentloaded' });
  await c.waitForFunction(() => window.__app && window.__app.sub && window.__app.sub.series,
    null, { timeout: 60000 });

  // ★ 没接上钩：印清楚为什么，记**没比成**。
  if (hooked === 0 || (SELFTEST && mutated === 0)) {
    console.error(`✗ 没比成：${hooked === 0 ? `源码里找不到「${TOKEN_FN}」` : ''}` +
      `${SELFTEST && mutated === 0 ? `源码里找不到要变异的那道闸「${TOKEN_GATE}」` : ''}` +
      ' —— 勾子是空操作，量到的是「没插上」不是「没毛病」。');
    console.error('  看一眼 web/app.js 里 placeSubhead 是不是改名／改写法了，把 TOKEN_* 跟着改。');
    await b.close();
    process.exit(2);
  }

  const click = () => c.evaluate(() => document.querySelector('button.chip[data-key="macd"]').click());
  const read = () => c.evaluate(() => {
    const A = window.__app, p1 = A.chart.panes()[1];
    const pr = p1 && p1.getHTMLElement().getBoundingClientRect();
    const sh = document.getElementById('subhead');
    const sr = sh && sh.classList.contains('on') ? sh.getBoundingClientRect() : null;
    return {
      相对格顶: sr && pr ? Math.round((sr.top - pr.top) * 10) / 10 : null,
      styleTop: sh ? sh.style.top : null,
      ph: (window.__ph || []).slice(),
    };
  });

  await sleep(2500);
  let bad = 0, ran = 0, called = 0;
  for (const [after, offms] of ROUNDS) {
    await c.evaluate(() => { window.__ph = []; });
    await click(); await sleep(offms);                     // 关
    await click(); await sleep(Math.max(after, 600));      // 开，再等版面稳定（修法的额度是 500ms）
    const r = await read();
    called += r.ph.length;
    const 相对格顶 = r.相对格顶;
    if (相对格顶 == null) {                                // 页头没亮 ⇒ 这一轮没量到东西，别当绿
      console.log(`✗      关${String(offms).padStart(4)}ms/等${String(after).padStart(4)}ms  ` +
                  `页头没亮（subhead 不在 on 状态）⇒ 这一轮没比成`);
      continue;
    }
    ran++;
    const hit = 相对格顶 > LIMIT;
    if (hit) bad++;
    console.log(`${hit ? '✗ 红  ' : '绿    '} 关${String(offms).padStart(4)}ms/等${String(after).padStart(4)}ms  ` +
      `相对格顶=${String(相对格顶).padStart(6)}px  style.top=${String(r.styleTop).padStart(6)}  ` +
      `调用：${r.ph.map((q) => `h=${q.h}→${q.after}`).join(' ') || '（零趟）'}`);
  }
  await b.close();

  // ② 整跑一趟都没调到 placeSubhead ⇒ 同①，没比成。
  if (called === 0) {
    console.error('✗ 没比成：整跑一趟 placeSubhead 都没被调用过 —— 勾子接上了但页面没走那条路' +
                  '（副图开关的入口改了？），这一跑什么都没量到。');
    process.exit(2);
  }
  const tag = SELFTEST ? '（自检：闸已改成 if(false)）' : '';

  if (SELFTEST) {
    if (bad > 0) {
      console.log(`✓ 自检过了：把闸改成 if(false) 之后 ${bad}/${ran} 个节奏变红` +
                  ` —— 这条判据有牙，不是空转格。`);
      process.exit(0);
    }
    console.log(`✗ 自检没牙：把闸改成 if(false)（＝回到修之前）之后**一个都没红** ——` +
                ` 这条判据量不出那道闸，等于空转格。`);
    process.exit(1);
  }

  if (bad > 0) {
    console.log(`✗ ${bad}/${ran} 个节奏下页头没贴着副图格顶（相对格顶 > ${LIMIT}px）${tag}` +
                ` —— 页头掉到副图下面去了，看上面红的那几行的 h=…→…px。`);
    process.exit(1);
  }
  if (ran < ROUNDS.length) {
    console.log(`✗ 只有 ${ran}/${ROUNDS.length} 个节奏量到了读数（其余页头没亮）${tag} —— 没量全，不算过。`);
    process.exit(1);
  }
  console.log(`${ran}/${ran} 过 —— ${ran} 种「关→开」节奏下页头都贴着副图格顶（相对格顶 ≤ ${LIMIT}px）${tag}`);
  process.exit(0);
})().catch((e) => { console.error('✗ 炸了：', e.message); process.exit(2); });

// 不带默认页面地址（部署细节不进仓，card-58518cb5-357）：没给 E2E_URL、也没给地址参数，就直接报错、退出码 2（环境没搭好）。
// predeploy 会 export E2E_URL。写法跟 tools/web_fs_drag_e2e.js 一致。
function noUrl() {
  console.error('缺页面地址：请设 E2E_URL（或把页面地址当参数）。本工装不带默认地址。');
  process.exit(2);
}
