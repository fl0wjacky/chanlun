// 「换数据 ⇒ 读数收起」这件事，**在哪一刻**量得出来？（真后台；给 card-4cdf628c-c84 的对照工装）
//
// 缘由：Atlas 2026-10-04 核「光标读数」时点的缺口 —— `paint()` 里那句 `hideRead()` 删掉，
//   工装里没有一格变红。这个探针把「删了到底有没有区别」逐条摆出来，三种跑法各跑同一套场景：
//     原样            ：什么都不摘
//     摘 go 里那句     ：`go()` 换数据那一刻的 hideRead()（**工装 ⑮ 量的就是这一句**）
//     摘 paint 里那句  ：`paint()` 里的 hideRead()（＝ Atlas 点的那一处）
//
// 两个场景，量的是两个不同的时刻：
//   A/B「换完之后」：换品种 / 换周期，**等新数据画上来**再读。→ 三种跑法结论应当一样：
//        LWC 在 setData 之后会自己重发一次十字线，读数当场就用新那份重读了。
//        ⇒ 结论：`paint()` 那个位置**量不出来**，在那儿加格是空转格（删了不红，因为它本来就没在做事）。
//   C「换的那一刻」：把那一趟响应**扣在手里** 2.5s，在「新数据还在飞」的窗口里读一眼。
//        屏上还是旧图、十字线一动没动 ⇒ 读数该收。→ 原样：off；摘了 go 那句：**on 且是旧数**。
//        ⇒ 结论：真正盖住这段的是 go() 里那句；工装 ⑮ 量的是这里。
//   D「窗口里**动鼠标**」（2026-10-04 加，Nova 的口径）＋ D2「新图画上之后再动一下」＋
//     E「取数**失败**那一趟（503，新图没来）」：
//        口径是「取数那段时间读数**整个压住**，动鼠标也不亮，等新图画上再恢复」——⑮ 只量了指针不动的那一眼。
//        → 原样：D 窗口里连动 3 下都是 off、副图那三格是「—」；D2/E 动一下读数回来、且对得上当时画着的那一份。
//        → 修之前的形状（＝ `--mut=read`／`--mut=sub` 那两跑）：D 窗口里**当场亮回来、写着上一份的价**，
//          副图三格印着上一份的量级。实测数字在下面每一跑的台账里。
//
// ★★ A/B 那一族 2026-10-04 改过判据（原来是把「三种跑法读出来的那串字」逐条比）：
//    **那串字本身会跳一根**，跟删不删那句没关系 —— 同一个 URL 连开三次（没有任何变异）：
//      等完就读 83,686.4 2026-09-28 16:00 ／ 83,686.4 16:00 ／ 83,832.7 17:00（差一根）
//    数据没动（5040 根、首根、末根时刻三次全同）、盒子没动、指针没动；换一条路（直接开 BTC 页）
//    三次又完全一样。⇒ 换完之后**指针底下的那一根**在摆视口这一段里会跳一格，这是**量具的噪声**，
//    拿它当判据的话，红绿都是在报「这一趟正好跳到哪一根」，不是在报行为。
//    ⇒ 判据换成**每一跑对着当时画着的那一份**查：换完之后读数必须**亮着**，而且它那一刻在
//      `state.data.bars` 里**找得到**、close 对得上（＝读的是新那份，不是旧那份）。
//      这条对「读数停在旧数上」正是死穴（换品种时旧数是另一种价格量级；换周期时 1h 的时刻
//      根本不在 4h 那份里），而它**不**管落在相邻哪一根 —— 那件事本来就会跳，见上。
//
// 跑法（要**真后台**：两个品种都得有，8742 那个假后台只有一份数据）：
//   1) python3 web/server.py --port 8792          （只绑回环）
//   2) NODE_PATH=<playwright 的 node_modules> node tools/web_readout_swap_probe.js [页面地址]
//        [--mut=none|paint|go|read|sub|sticky|sticky2|stale]
//   不给 --mut ⇒ 八种跑法都跑（这才是完整对照）；给了 ⇒ 只跑那一种。
//   判据两条：① **原样**那一跑得是「该收的收、该回来的回来」（BASE 那张表）；② 每一种变异**该分叉在哪一格
//   就得在这一格分叉**（DIVERGE 那张表）—— 没分叉就是那一格没牙，探针退 1 并把哪一格没分叉印出来。
//   退出码：0＝三种跑法都符合上面那两条预期；1＝有跑法不符合（把不符合的那条印出来）；2＝环境没搭好。
// 指针的位置：**全程不离开图**（用 select 改 selection，不点控件、不挪鼠标）——
//   指针一走 LWC 就发 time==null，读数自己会收，那样量到的是「鼠标移开」不是「换了数据」。
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
  ? process.argv[2] : 'http://127.0.0.1:8792/')).replace(/\/?$/, '/');   // E2E_URL 优先（上线门统一给，card-9b0fe913-758）
const MUT = (process.argv.find((a) => a.startsWith('--mut=')) || '--mut=none').split('=')[1];
// 「新数据还在飞」那段撑多久。★ 2026-10-04 从 2500 提到 6000：D 段要在**同一段窗口**里连动三下，
//   而真后台这一页是 5040 根（比工装那份样本重得多，每次 evaluate/move 都慢）—— 2500 那次跑，第三下
//   已经看见了新数据（台账上写着 `on 81,722.9`，那是 BTC 的价，不是 ZEC 的），那一眼就是替身。
//   ⇒ 撑长一点，让「窗口内样本数」自己说话（D 那一段会把它记下来，不足 3 就该报空转，见 obs()）。
const HOLD = 6000;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 变异的锚点：各按**下一行**认（行号会漂，下一行这句话不会）
const SITES = {
  go:    { name: 'go()（换数据那一刻）', re: /\n  hideRead\(\);\n(  el\('state'\)\.textContent = '取数…';)/ },
  paint: { name: 'paint()',             re: /\n  hideRead\(\);\n(  const bars = d\.bars\.map)/ },
  // ★ 这条**不是**「哪句 hideRead 该放哪」的对照，是 A/B 那条判据的**牙齿**自己：
  //   读数块照样亮着，但**字只印第一次** ⇒ 换完之后 DOM 上留着的是旧那份的数（＝「停在旧数上」）。
  //   跑 `--mut=stale` 应当看到 A/B 那两格红、报「读数上的 close 跟当时那一份里那一刻对不上」——
  //   红得出来，那条判据才不是空转格。（2026-10-04 加：原来的判据比的是「三种跑法读出的那串字」，
  //   无变异也会跳一根，见文件头。）
  //   ★ 头一版写的是「整个 showRead 只跑第一次」——那会把块也一起掐灭（读数再也不亮），
  //     量到的是「读数没了」不是「字是旧的」，报出来是空转格。掐字不掐块才对得上这条判据。
  // ★★ 2026-10-04 加的三条，是工装 ⑰⑱⑲⑳ 那四格的牙（每一条只红它该红的那一格）：
  //   read  ：摘掉 `showRead` 里那道闸（dataStale）⇒ **⑰ 红**（窗口里动鼠标，读数当场亮回来、写着旧数）。
  //           这一跑量出来的样子**就是修之前**的样子 —— 所以它也是「现状」那一步的对照跑。
  //   sub   ：摘掉 `refreshSubVals` 里那道 ⇒ **⑱ 红**（副图那三格还印着上一份的量级）。
  //   sticky：把 `finally` 里那句放开（`dataStale = false`）删掉 ⇒ 标志**永不放开** ⇒ **⑯⑲⑳ 红**
  //           （⑮⑰⑱ 照旧绿：压得住但回不来，正是「收死了」那个 bug 的形状）。
  read:   { name: 'showRead 里那道闸（dataStale）', re: /\n(  if \(dataStale\) return;\n)/, rep: '\n' },
  sub:    { name: 'refreshSubVals 里那道闸（dataStale）', re: /\n(  if \(dataStale\) \{ subDom\.cells[^\n]*\n)/, rep: '\n' },
  // ★ sticky 只认 go() 那一句：app.js 里「自动重取」那条路的 finally 也有一句一模一样的（后加的），
  //   不锚的话命中 2 处、这一跑整个不算数（Iris 10-05 判：工装老红，跟页面无关）。锚在 go() 那句头上的注释。
  sticky: { name: '放开那一句（go() 的 finally 里的 dataStale = false）',
            re: /(它自己有始有终。\n\s*if \(id === paging\.reqId\) \{ paging\.loading = false;) dataStale = false;/,
            rep: '$1' },
  // sticky2：同一句，**自动重取**那条路（autoReload 的 finally）—— 删了它，收盘自动重取一趟以后读数就收死（⇒ F 红）。
  sticky2: { name: '放开那一句（自动重取 autoReload 的 finally 里的 dataStale = false）',
             re: /(自动重取没成功[^\n]*\n\s*return null;\n\s*\} finally \{\n\s*if \(id === paging\.reqId\) \{ paging\.loading = false;) dataStale = false;/,
             rep: '$1' },
  stale: { name: 'showRead()（字只印第一次，块照样亮）', re: /\n(function showRead\(b\) \{\n)/,
           rep: '\n$1  if (window.__ro0) { el(\'readout\').classList.add(\'on\'); readShown = true; return; }'
              + ' window.__ro0 = 1;      // ← 变异：字只印第一次\n' },
};
const read = (p) => p.evaluate(() => {
  const r = document.getElementById('readout');
  const d = window.__app.state.data;
  const pad = (n) => String(n).padStart(2, '0');
  const label = (ms) => { const x = new Date(ms);            // 跟读数上那串字同一套（UTC，分）
    return `${x.getUTCFullYear()}-${pad(x.getUTCMonth() + 1)}-${pad(x.getUTCDate())} `
         + `${pad(x.getUTCHours())}:${pad(x.getUTCMinutes())} UTC`; };
  const tm = document.getElementById('ro-time').textContent;
  const cs = document.getElementById('ro-close').textContent;
  const num = Number(cs.replace(/,/g, ''));
  // 读数上那一刻，在**当前画着的这一份**里是哪一根？（找不到 ⇒ 读的不是这一份）
  const bar = d ? d.bars.find((b) => label(b.t) === tm) : null;
  // 副图那一格的头：DIF/DEA/柱 三个数（②③ 里也是「跟着光标走的读数」，D 段量它）
  const sh = document.getElementById('subhead');
  const sub = sh ? Array.from(sh.querySelectorAll('.cell b')).map((b) => b.textContent).join('|') : '(没有副图头)';
  return { on: r.classList.contains('on'), c: cs, tm, sub,
           sym: document.getElementById('symbol').value,
           tf: document.getElementById('tf').value, badge: (document.getElementById('state') || {}).textContent || '',
           drawn: d ? d.bars.length : 0,
           first: d ? d.bars[0].o : 0,                       // 换品种/换周期都变 → 用它认「新那份画上来了」
           在这份里: !!bar,
           对得上: !!bar && Math.abs(bar.c - num) <= Math.max(0.051, Math.abs(bar.c) * 1e-6) };
});
const show = (x) => `${x.on ? 'on ' : 'off'} ${x.c} ${x.tm}`.trim();

async function run(b, mode) {
  const c = await b.newContext({ viewport: { width: 1280, height: 800 } });
  let hit = null;
  if (mode !== 'none') {
    const site = SITES[mode];
    await c.route('**/app.js*', async (route) => {
      const r = await route.fetch();
      const t = await r.text();
      const n = (t.match(new RegExp(site.re.source, 'g')) || []).length;
      hit = n;
      if (n !== 1) {                       // 命不中就得当场炸：变异没生效的探针＝白跑
        await route.fulfill({ status: 200, contentType: 'text/javascript', body: t });
        return;
      }
      // ★ 替换要**留住那个换行**（'\n$1'，不是 '$1'）：$1 是**下一行的缩进**，
      //   少了换行它会被并进上一行的注释里 —— 那样删掉的就不只是 hideRead()，
      //   连同下一句一起变成了注释（paint 那处会让整页画不出来，量到的是「页面坏了」）。
      await route.fulfill({ status: 200, contentType: 'text/javascript',
                            body: t.replace(site.re, site.rep || '\n$1') });
    });
  }
  let FAIL = false;                       // E 段用：**下一趟** BTC 那个请求直接 503（量「取数失败」那一趟）
  // 换品种那一趟扣在手里：C/D 要的就是「新数据还在飞」那一段
  await c.route('**/api/chart*', async (route) => {
    if (FAIL) return route.fulfill({ status: 503, body: '' });
    const r = await route.fetch();
    const j = await r.json();
    if (new URL(route.request().url()).searchParams.get('symbol') === 'BTCUSDT') await sleep(HOLD);
    await route.fulfill({ status: r.status(), contentType: 'application/json', body: JSON.stringify(j) });
  });
  // ★ 样本那一口**也关掉**（跟 web_readout_e2e 同一条理由）：后台取不到时页面会退回仓里的样本，
  //   E 段要量的「取数失败」就会变成「换成了一份样本」—— 那一格当场空转（而且看不出是空转）。
  await c.route('**/fixtures/**', (route) => route.fulfill({ status: 404, body: '' }));
  const p = await c.newPage();
  await p.goto(PAGE + '?symbol=ZECUSDT&tf=1h&last=300', { waitUntil: 'domcontentloaded' });
  await p.waitForFunction(() => window.__app && window.__app.state.data, null, { timeout: 60000 });
  await sleep(1200);
  const box = await p.locator('#chart').boundingBox();
  const mx = Math.round(box.x + box.width * 0.5), my = Math.round(box.y + box.height - 40);
  const swap = (id, v) => p.evaluate(([i, val]) => { const s = document.getElementById(i);
    s.value = val; s.dispatchEvent(new Event('change', { bubbles: true })); }, [id, v]);
  const out = {};
  // A/B：换完之后（等新数据画上来再读）—— 每一跑都对着**当时画着的那一份**查（见文件头）
  for (const [label, id, v] of [['A 换品种 → BTCUSDT', 'symbol', 'BTCUSDT'], ['B 换周期 → 4h', 'tf', '4h']]) {
    await p.mouse.move(mx, my); await sleep(500);
    const before = await read(p);
    await swap(id, v);
    // 等**新那份**画上来：认首根（两个品种的根数一样多，认根数会白等满超时）
    await p.waitForFunction((f0) => window.__app.state.data.bars[0].o !== f0, before.first, { timeout: 30000 })
      .catch(() => {});
    await sleep(1200);                       // 数据画上之后（re-emit 已经发生过）
    const after = await read(p);
    out[label] = { 换前: show(before), 换后: show(after), 换前在不在: before.on,
                   换后亮着: after.on, 换后在这份里: after.在这份里, 换后对得上: after.对得上,
                   换后时刻: after.tm, 这份根数: after.drawn };
  }
  // C：换的那一刻（窗口里）—— 这一格才是分叉的地方
  await p.mouse.move(mx, my); await sleep(500);
  await swap('symbol', 'ZECUSDT');           // 先换回来，好让 C 有一趟**真的**被扣住
  await p.waitForFunction(() => window.__app.state.data.bars[0].o < 3000, null, { timeout: 30000 }).catch(() => {});
  await sleep(1200);
  await p.mouse.move(mx, my); await sleep(500);
  const c1 = await read(p);
  const t0 = Date.now();
  await swap('symbol', 'BTCUSDT');
  await sleep(Math.max(0, 700 - (Date.now() - t0)));
  const mid = await read(p);
  out['C 换的那一刻（响应扣住 2.5s 里那一眼）'] = { 换前: show(c1), 窗口里: show(mid), 页面此刻写着: mid.badge,
    指针下那根还是旧那份: mid.first === c1.first, 换前在不在: c1.on };
  // D：**同一段窗口里动鼠标**（⑰⑱）。★ 承着 C 的那一段做，别等数据到 —— 等到了量的是另一件事。
  const mv = [];
  for (const f of [0.42, 0.58, 0.35]) {
    await p.mouse.move(Math.round(box.x + box.width * f), my, { steps: 6 });
    await sleep(120);
    const x = await read(p);
    // ★ 每一下都当场记：**这一眼还在不在窗口里**（状态写着「取数…」＋ 屏上还是旧那份）。
    //   不记这一笔，窗口没撑住的那一下就会冒充「读数在窗口里亮着」——2026-10-04 第一次跑就是这样漏的。
    mv.push(Object.assign({ 在窗口里: x.badge.includes('取数') && x.first === c1.first,
                            t: Date.now() - t0 }, x));
  }
  const inw = mv.filter((x) => x.在窗口里);
  out['D 窗口里动鼠标（⑰⑱）'] = {
    换前在不在: c1.on, 换前副图三格: c1.sub,
    窗口里动了3下: mv.map((x) => `${x.在窗口里 ? '' : '【窗口外】'}${x.on ? 'on ' + x.c : 'off'}(${x.t}ms)`).join(' / '),
    窗口内样本数: `${inw.length}/3`,
    副图三格: [...new Set(inw.map((x) => x.sub))].join(' ／ ') || '(窗口里一个样本都没有)' };
  // D2：新图画上**之后**再动一下（⑲）—— 压住的一头是 ⑰，这一头量的是「不许压死」
  await p.waitForFunction((f0) => window.__app.state.data.bars[0].o !== f0, c1.first, { timeout: 30000 }).catch(() => {});
  await sleep(1200);
  await p.mouse.move(Math.round(box.x + box.width * 0.62), my, { steps: 6 });
  await sleep(300);
  const d2 = await read(p);
  out['D2 新图画上之后再动（⑲）'] = { 动一下: show(d2), 亮着: d2.on, 在这份里: d2.在这份里, 对得上: d2.对得上 };
  // F：**收盘自动重取**那一趟之后再动一下（sticky2 的牙）—— 自动重取也会把读数压住，回来必须放开。
  //   直接调 autoReload()（不等真收盘）；它跟换品种走的是两条 finally。
  await p.mouse.move(mx, my); await sleep(300);
  const f1 = await read(p);
  const fr = await p.evaluate(() => window.__app.autoReload());
  await sleep(500);
  await p.mouse.move(Math.round(box.x + box.width * 0.55), my, { steps: 6 });
  await sleep(300);
  const f2 = await read(p);
  out['F 自动重取那一趟之后再动'] = { 换前在不在: f1.on, 那一趟回: String(fr), 动一下: show(f2),
    亮着: f2.on, 在这份里: f2.在这份里, 对得上: f2.对得上 };
  // E：**取数失败**那一趟（⑳）—— 先回 ZEC，再让下一趟 BTC 的 /api/chart 503
  await swap('symbol', 'ZECUSDT');
  await p.waitForFunction(() => window.__app.state.data.bars[0].o < 3000, null, { timeout: 30000 }).catch(() => {});
  await sleep(1200);
  await p.mouse.move(mx, my); await sleep(400);
  const e1 = await read(p);
  FAIL = true;
  await swap('symbol', 'BTCUSDT');
  await sleep(1500);                        // 这一趟是 503，当场就回来
  const eMid = await read(p);
  await p.mouse.move(Math.round(box.x + box.width * 0.45), my, { steps: 6 });
  await sleep(300);
  const eBack = await read(p);
  out['E 取数失败那一趟（⑳）'] = { 换前在不在: e1.on, 那一趟写着: eMid.badge, 失败后那一瞬: show(eMid),
    再动一下: show(eBack), 亮着: eBack.on, 在这份里: eBack.在这份里, 对得上: eBack.对得上 };
  await c.close();
  return { hit, mode, out };
}

(async () => {
  const b = await chromium.launch();
  const modes = MUT === 'none' ? ['none', 'paint', 'go', 'read', 'sub', 'sticky', 'sticky2', 'stale'] : [MUT];
  const res = [];
  for (const m of modes) {
    const label = m === 'none' ? '原样' : `摘 ${SITES[m].name}`;
    const r = await run(b, m);
    const ok = m === 'none' || r.hit === 1;
    console.log(`\n== ${label} ==${m === 'none' ? '' : `　[变异命中 ${r.hit} 处${ok ? '（好）' : '　★ 不是 1 —— 这次跑的是原样，下面的数不算数'}］`}`);
    for (const [k, v] of Object.entries(r.out)) {
      console.log(`  ${k}\n      ${Object.entries(v).map(([a, x]) => `${a}: ${x}`).join('　｜　')}`);
    }
    res.push({ m, label, ...r });
  }
  await b.close();
  const single = modes.length < 3;                 // --mut=X 只跑一种：跨跑对照判不了，但每跑自己那几条照样判
  const ref = res.find((r) => r.m === 'none') || res[0];
  const bad = [];
  // 每一跑的**粗口径**观测：只记 on/off、对不对得上、「—」还是旧数 —— **不描那串字**
  //   （换完之后落在相邻哪一根本来就会跳一根，见文件头：拿它当判据，红绿都在报噪声）。
  const obs = (r) => {
    const o = r.out, K = (p) => Object.keys(o).find((x) => x.startsWith(p));
    const A = o[K('A')], B = o[K('B')], C = o[K('C')], D = o[K('D ')], D2 = o[K('D2')], E = o[K('E')], F = o[K('F')];
    const 对得上 = (x) => (!x.亮着 ? '没亮' : (x.在这份里 && x.对得上 ? '对得上' : '对不上'));
    return {
      前提: !!(A.换前在不在 && B.换前在不在 && C.换前在不在 && D.换前在不在 && E.换前在不在 && F.换前在不在),
      A: A.换后亮着 ? (A.换后在这份里 && A.换后对得上 ? '对得上' : '对不上') : '没亮',
      B: B.换后亮着 ? (B.换后在这份里 && B.换后对得上 ? '对得上' : '对不上') : '没亮',
      C: /^off/.test(C.窗口里) ? 'off' : 'on',
      // ★ D/Dsub 只看**窗口内**的样本：窗口外那一眼量的是另一件事（新图都画上了，读数本来就该亮）
      D: D.窗口内样本数 === '3/3' ? (/(^| )on /.test(D.窗口里动了3下) ? 'on' : 'off') : `窗口不够(${D.窗口内样本数})`,
      Dsub: D.窗口内样本数 === '3/3' ? (D.副图三格.includes('—') ? '—' : '旧数') : `窗口不够(${D.窗口内样本数})`,
      D2: 对得上(D2),
      E: 对得上(E),
      F: 对得上(F),
    };
  };
  // 原样那一跑**该长什么样**（这几条就是工装 ⑮⑯⑰⑱⑲⑳ 的判据，在这儿量的是它们各自的前提与对照）
  const BASE = { A: '对得上', B: '对得上', C: 'off', D: 'off', Dsub: '—', D2: '对得上', E: '对得上', F: '对得上' };
  // 每一种变异**该分叉在哪一格**（★ 这就是「那一格有没有牙」的全部）：
  const DIVERGE = {
    none: [], paint: [],                       // paint：一条都不该分叉（＝「那个位置量不出来」，见文件头）
    go: ['C'],                                 // 摘 go 那句 ⇒ ⑮ 红
    read: ['D'],                               // 摘 showRead 那道闸 ⇒ ⑰ 红
    sub: ['Dsub'],                             // 摘 refreshSubVals 那道闸 ⇒ ⑱ 红
    sticky: ['A', 'B', 'D2', 'E'],             // 永不放开 ⇒ ⑯⑲⑳ 红（⑮⑰⑱ 照旧绿：压得住但回不来）
    sticky2: ['F'],                            // 自动重取那句不放开 ⇒ 自动重取一趟以后读数收死
    stale: ['A', 'B', 'D'],                    // ★ D 也分叉：这条变异的「字只印第一次」摆在闸**前面**，
  };                                           //   窗口里照样点亮 —— 是它自己的形状，不是 ⑰ 没牙
  const base = obs(ref);
  if (base.前提) {
    for (const [k, v] of Object.entries(BASE)) {
      if (base[k] !== v) bad.push(`原样那一跑的「${k}」实际是 ${base[k]}，该是 ${v}`);
    }
  } else bad.push('原样那一跑有场景**换之前读数就不在** ⇒ 那几个场景是空转（多半页面还没起稳），下面的数都不算数');
  for (const r of res) {
    if (r.m === 'none') continue;
    if (r.hit !== 1) { bad.push(`${r.label}：变异命中 ${r.hit} 处（要正好 1）⇒ 这一跑没在量它该量的东西`); continue; }
    const o = obs(r);
    // 窗口没撑住的那一跑**一律不算数**（不然「读数在窗口外亮着」会冒充「窗口里亮着」，正好把牙变成假的）
    const short = Object.keys(o).filter((k) => String(o[k]).startsWith('窗口不够'));
    if (short.length) {
      bad.push(`${r.label}：「${short.join('、')}」那一段窗口没撑住（${short.map((k) => o[k]).join('、')}）`
        + ' ⇒ 这一跑量到的不是它该量的东西，数不算数（把 HOLD 再撑长一点）');
      continue;
    }
    const diff = Object.keys(o).filter((k) => k !== '前提' && o[k] !== base[k]);
    const want = DIVERGE[r.m] || [];
    for (const k of want) {
      if (!diff.includes(k)) bad.push(`${r.label}：该分叉的「${k}」**没分叉**（还是 ${o[k]}）⇒ 那条判据没牙`);
    }
    if (r.m === 'paint' && diff.length) bad.push(`paint 那一跑本该一条都不分叉，实际分了：${diff.join('、')}`);
    console.log(`     分叉：${diff.length ? diff.map((k) => `${k} ${base[k]}→${o[k]}`).join('、') : '（一条都没有）'}`);
  }
  // 落在相邻哪一根会跳（无变异也会跳，见文件头）—— 这条只做**记录**，不当判据
  for (const k of Object.keys(ref.out).filter((x) => x.startsWith('A') || x.startsWith('B'))) {
    const seen = res.filter((r) => r.out[k].换前在不在).map((r) => `${r.label}：${r.out[k].换后}`);
    console.log(`\nⓘ 「${k}」换完之后落在哪一根 —— ${seen.join('　｜　')}\n   （差一根是量具自己的事：同一个 URL 连开三次、无变异，也会跳一根）`);
  }
  console.log('\n' + (bad.length ? '★ 有对照不符合预期：\n  ' + bad.join('\n  ')
    : (single ? `✓ 这一跑（${ref.label}）该分叉的地方都分了。跨跑那几条要全部跑一遍才算（不给 --mut 就是全跑）。`
      : '✓ 全都对上了：原样那一跑 ⑮ 窗口里 off／⑰ 动鼠标也不亮／⑱ 副图三格「—」／⑲⑳ 回来且对得上；'
        + '四条 hideRead 摆法各自分叉在它该分叉的那一格（`paint` 一条都不分叉＝那个位置量不出来）。')));
  process.exit(bad.length ? 1 : 0);
})().catch((e) => { console.error('探针自己炸了：', e.message); process.exit(2); });
