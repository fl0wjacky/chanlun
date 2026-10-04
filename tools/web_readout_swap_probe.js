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
//   2) NODE_PATH=<playwright 的 node_modules> node tools/web_readout_swap_probe.js [页面地址] [--mut=go|paint|none]
//   不给 --mut ⇒ 三种跑法都跑（这才是完整对照）；给了 ⇒ 只跑那一种。
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
const PAGE = (process.argv[2] && !process.argv[2].startsWith('--') ? process.argv[2]
  : 'http://127.0.0.1:8792/').replace(/\/?$/, '/');
const MUT = (process.argv.find((a) => a.startsWith('--mut=')) || '--mut=none').split('=')[1];
const HOLD = 2500;                       // 「新数据还在飞」那段撑多久（撑不出来就没窗口可量）
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
  return { on: r.classList.contains('on'), c: cs, tm, sym: document.getElementById('symbol').value,
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
  // 换品种那一趟扣在手里：C 要的就是「新数据还在飞」那一段
  await c.route('**/api/chart*', async (route) => {
    const r = await route.fetch();
    const j = await r.json();
    if (new URL(route.request().url()).searchParams.get('symbol') === 'BTCUSDT') await sleep(HOLD);
    await route.fulfill({ status: r.status(), contentType: 'application/json', body: JSON.stringify(j) });
  });
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
  await c.close();
  return { hit, mode, out };
}

(async () => {
  const b = await chromium.launch();
  const modes = MUT === 'none' ? ['none', 'paint', 'go'] : [MUT];
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
  // 判据：每一跑的**前提**得成立（换之前读数在）；A/B 换完之后读数**亮着**且读的是**当时画着的那一份**；
  // C 只有「摘 go」那一跑分叉（原样 off、摘了那张还亮着旧数）
  const ref = res.find((r) => r.m === 'none') || res[0];
  const bad = [];
  for (const r of res) {
    if (r.m !== 'none' && r.hit !== 1) continue;          // 变异没命中：这一跑的数不算数（上面已经大字报了）
    for (const [k, v] of Object.entries(r.out)) {
      if (!v.换前在不在) bad.push(`${r.label} 的「${k}」**换之前读数就不在** ⇒ 这一跑是空转，数不算数（多半是页面还没起稳）`);
    }
    for (const [k, v] of Object.entries(r.out)) {
      if (k.startsWith('C') || !v.换前在不在) continue;
      if (!v.换后亮着) bad.push(`${r.label} 的「${k}」换完之后读数**没亮着**：${v.换后}`);
      else if (!v.换后在这份里) bad.push(`${r.label} 的「${k}」换完之后读数上那一刻**不在当时画着的那一份里**：`
        + `${v.换后}（这份 ${v.这份根数} 根）—— 读数没跟着新数据走`);
      else if (!v.换后对得上) bad.push(`${r.label} 的「${k}」换完之后读数上的 close 跟当时那一份里「${v.换后时刻}」对不上：`
        + `${v.换后} ⇒ 停在旧数上了`);
    }
  }
  const ck = Object.keys(ref.out).find((k) => k.startsWith('C'));
  if (!single) {                                   // C 那两条是**跨跑**比出来的：只跑一种时没有对照
    const goRun = res.find((r) => r.m === 'go');
    if (ref.out[ck].换前在不在) {
      if (!/^off/.test(ref.out[ck].窗口里)) bad.push(`原样在窗口里应当是 off，实际 ${ref.out[ck].窗口里}（⑮ 的前提不成立）`);
      if (!ref.out[ck].指针下那根还是旧那份) bad.push('原样那一跑：窗口里那一眼指针下已经不是旧那份了 ⇒ 那一眼没落在窗口里，数不算数');
    }
    if (goRun && goRun.hit === 1 && goRun.out[ck].换前在不在) {
      if (!/^on/.test(goRun.out[ck].窗口里)) bad.push(`摘了 go 那句，窗口里应当**还亮着旧数**，实际 ${goRun.out[ck].窗口里}`);
      if (!goRun.out[ck].指针下那根还是旧那份) bad.push('摘 go 那一跑：窗口里那一眼没落在窗口里，数不算数');
    }
  }
  // 落在相邻哪一根会跳（无变异也会跳，见文件头）—— 这条只做**记录**，不当判据
  for (const k of Object.keys(ref.out).filter((x) => !x.startsWith('C'))) {
    const seen = res.filter((r) => r.out[k].换前在不在).map((r) => `${r.label}：${r.out[k].换后}`);
    console.log(`\nⓘ 「${k}」换完之后落在哪一根 —— ${seen.join('　｜　')}\n   （差一根是量具自己的事：同一个 URL 连开三次、无变异，也会跳一根）`);
  }
  console.log('\n' + (bad.length ? '★ 有对照不符合预期：\n  ' + bad.join('\n  ')
    : (single ? `✓ 这一跑（${ref.label}）自己那几条都成立：换完之后读数亮着、而且读的是**当时画着的那一份**。`
              + ' 跨跑那两条（三种 hideRead 摆法的对照）要三种都跑才算。'
      : '✓ 三条预期都成立：换完之后每一跑读数都亮着、而且读的是**当时画着的那一份**（三种跑法都成立）'
        + ' ⇒ `paint()` 那个位置量不出来；分叉只在「换的那一刻」，而且正是 go() 那句管着。')));
  process.exit(bad.length ? 1 : 0);
})().catch((e) => { console.error('探针自己炸了：', e.message); process.exit(2); });
