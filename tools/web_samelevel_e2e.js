// 同级别正式版的前端三样（上线清单 #21 / 验收门 G10，卡 card-6273f71c-b72）：
//   ① 「盘整相连」（S5 刀，S12）图上 0 个字、悬停里有「死点：盘整相连」＋出处；
//   ② 刀上 `state`：pending ⇒ 空心点＋小字「待确认」，confirmed ⇒ 实心、不带「待确认」；
//   ③ 牙：载荷里**没有** state（现行后台）⇒ 一个空心点都没有、一个「待确认」都没有 —— 跟改之前一样。
// ★ 后台的 `state` 字段还没进引擎（Bram 08:34 起草、未提交），所以这里**在页面里改载荷**：挑屏上几把真刀，
//   把它们的 state／death 改掉再重画。量的是**前端读不读、怎么画**，不量后台给得对不对（那是 G2 回放＋check_parity 的事）。
// 跑法：真后台 `python3 web/server.py --port <端口> --no-prewarm`（要联网取币安），然后
//   E2E_URL=<E2E_URL> NODE_PATH=<playwright 的 node_modules> node tools/web_samelevel_e2e.js [出图目录]
// 退出码：0 全绿；1 有红；2 跑不动（页面没数据／屏上没刀 —— 查不了 ≠ 通过）
const { chromium } = require('playwright');
// 跟另外几套一样：E2E_URL 优先（上线门统一给，predeploy 那时把**出图目录**当第一个参数传进来）；没给就收「地址 [出图目录]」
const PAGE = (process.env.E2E_URL || process.argv[2] || '').replace(/\/?$/, '/');
const SHOTS = process.env.E2E_URL ? process.argv[2] : process.argv[3];
if (!/^https?:/.test(PAGE)) { console.error('要给页面地址'); process.exit(2); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let red = 0, n = 0;
const ck = (name, ok, msg) => { n++; if (!ok) red++; console.log(`${ok ? '✓' : '✗'} ${name}　${msg}`); };

(async () => {
  const b = await chromium.launch();
  const p = await (await b.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  await p.goto(PAGE + '?symbol=ZECUSDT&tf=15m', { waitUntil: 'domcontentloaded' });
  const ready = await p.waitForFunction(() => window.__app && window.__app.state.data && window.__app.state.data.trend
    && window.__app.state.trendDrawn, null, { timeout: 60000 }).then(() => true, () => false);
  if (!ready) { console.error('页面没数据（trend 层没起来）'); await b.close(); process.exit(2); }
  await sleep(1500);

  // 视口挑刀最多的一扇（同 measure ㊿ 的挑法；setVisibleLogicalRange 不能给大数偷懒，会夹到空白）
  await p.evaluate(async () => {
    const ts = window.__app.chart.timeScale(), v = ts.getVisibleLogicalRange(), w = Math.max(200, v.to - v.from);
    const bars = window.__app.state.data.trend.bounds.map((q) => q.bar);
    let best = [v.from, v.to], most = -1;
    for (const b0 of bars) { const k = bars.filter((x) => x >= b0 - 20 && x <= b0 - 20 + w).length; if (k > most) { most = k; best = [b0 - 20, b0 - 20 + w]; } }
    // 刀太稀（一屏不到 4 把）就往回放宽，一直放到最近 6 把都在屏上 —— 要挑三把不挨着屏边的刀
    if (most < 4 && bars.length >= 4) best = [bars[Math.max(0, bars.length - 6)] - 60, bars[bars.length - 1] + 60];
    ts.setVisibleLogicalRange({ from: best[0], to: best[1] }); await new Promise((r) => setTimeout(r, 900));
  });
  const nudge = () => p.evaluate(async () => {
    const ts = window.__app.chart.timeScale(), v = ts.getVisibleLogicalRange();
    ts.setVisibleLogicalRange({ from: v.from + 0.01, to: v.to + 0.01 }); await new Promise((r) => setTimeout(r, 700));
  });
  const read = () => p.evaluate(() => {
    const D = window.__app.state.trendDrawn;
    return { states: D.states || null, deaths: (D.deaths || []).map((r) => ({ bar: r.bar, death: r.death, state: r.state, txt: r.txt, mode: r.mode })) };
  });

  // ④ 真载荷（后台已经给 state 的话，4d09f3b 起）：屏上每把刀「空心 ⟺ 载荷 state=pending」；
  //   盘整相连且 confirmed ⇒ 图上 0 个字；pending 的字只能是「待确认」或「<短名>（待确认）」。后台没给 state 就跳过这格（不算过也不算红）。
  // ④ 选图：这一刻 ZEC 15m 可能一把 pending 都没有（行情走到全 confirmed）⇒ 另开一页换 ZEC 1h、AAPL 15m 接着找，
  //   找到一张有 pending 的就在那张上量；几张都没有才记跳过，并印出试过哪几张（Nova 10-09 15:33）。另开页不动 p（后面几格还在 p 上量）。
  const hasPend = (pg) => pg.evaluate(() => window.__app.state.data.trend.bounds.some((q) => q.state === 'pending'));
  const tried4 = ['ZECUSDT 15m'];
  let pp = p, pp2 = null;
  if (!(await hasPend(p))) {
    for (const [sym, tf] of [['ZECUSDT', '1h'], ['AAPLUSDT', '15m']]) {
      tried4.push(`${sym} ${tf}`);
      const q = await (await b.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
      await q.goto(PAGE + `?symbol=${sym}&tf=${tf}`, { waitUntil: 'domcontentloaded' });
      const ok = await q.waitForFunction(() => window.__app && window.__app.state.data && window.__app.state.data.trend && window.__app.state.trendDrawn,
        null, { timeout: 60000 }).then(() => true, () => false);
      if (ok) await sleep(1500);
      if (ok && await hasPend(q)) { pp = q; pp2 = q; break; }
      await q.context().close();
    }
  }
  const anyState = await pp.evaluate(() => window.__app.state.data.trend.bounds.some((q) => 'state' in q));
  if (anyState) {
    // 先把视口挪到**最后一把 pending 的刀**那一扇（图尾那几把 S5 一律待确认，D-4）—— 不挪的话屏上可能一把 pending 都没有，这格就空过了
    await pp.evaluate(async () => {
      const app = window.__app, ts = app.chart.timeScale(), v = ts.getVisibleLogicalRange(), w = v.to - v.from;
      const pd = app.state.data.trend.bounds.filter((q) => q.state === 'pending').map((q) => q.bar);
      if (pd.length) { const c = pd[pd.length - 1]; ts.setVisibleLogicalRange({ from: c - w * 0.6, to: c + w * 0.4 }); }
      await new Promise((r) => setTimeout(r, 900));
    });
    const real = await pp.evaluate(() => {
      const app = window.__app, T = app.state.data.trend, D = app.state.trendDrawn;
      const by = Object.fromEntries(T.bounds.map((q) => [q.bar, q]));
      return { states: (D.states || []).map((s) => ({ ...s, want: by[s.bar] ? by[s.bar].state : null, death: by[s.bar] ? by[s.bar].death : null })),
               deaths: (D.deaths || []).map((r) => ({ bar: r.bar, death: r.death, state: r.state, txt: r.txt, mode: r.mode })) };
    });
    const SH = { '趋势背驰': '趋势背驰', '盘整背驰': '盘整背驰', '小转大': '小转大', '盘整·未见背驰': '未见背驰', '比不了': '比不了', 'D2-8 补刀': '补刀' };
    const badDot = real.states.filter((s) => s.hollow !== (s.want === 'pending'));
    const badTxt = real.deaths.filter((r) => r.mode && (() => { const t = r.txt.replace(/^· | ·$/g, '');
      if (r.death === '盘整相连') return !(r.state === 'pending' && t === '待确认');
      return t !== (SH[r.death] || '') + (r.state === 'pending' ? '（待确认）' : ''); })());
    const nPend = real.states.filter((s) => s.want === 'pending').length;
    // 整份载荷一把 pending 都没有（行情走到哪都可能：比如 10-09 15:2x 的 ZEC 15m，30 把全 confirmed）⇒ 这一格没东西可量，记跳过，不记红也不记绿
    const anyPend = await hasPend(pp);
    if (!anyPend) console.log(`－ ④ 跳过：试过 ${tried4.join('、')}，这一刻都没有待确认的刀`);
    else ck(`④ 真载荷（${tried4.at(-1)}）：屏上每把刀「空心 ⟺ state=pending」；字跟 state／death 对得上（盘整相连 confirmed 不写字）`,
       real.states.length > 0 && nPend > 0 && !badDot.length && !badTxt.length,
       `屏上 ${real.states.length} 刀（pending ${nPend}）${badDot.length ? '　✗ 点不对 ' + JSON.stringify(badDot) : ''}${badTxt.length ? '　✗ 字不对 ' + JSON.stringify(badTxt) : ''}`);
  } else console.log('－ ④ 跳过：这个后台还不给 state');
  if (pp2) await pp2.context().close();

  // ⑤ 「高一级」「级别对照」两颗芯片（Nova 10-09 09:07；13:14 改：「级别对照」不藏、按灰、悬停写原因，只「高一级」藏）：
  //   而且就算 opts 里 up／lv 是开的（地址栏带着 up=1 进来的那种），画图那张判据 `shownOf` 也给 false；
  //   现行口径 ⇒ 两颗照常露着（牙：别把现行口径也藏了）。
  const chipsLv = await p.evaluate(async () => {
    const app = window.__app, { shownOf } = await import('/layers.js');
    const sl = (app.state.data || {}).trend_reading === 'same_level';
    const vis = (k) => { const e = document.querySelector(`.chip[data-key="${k}"]`); return e ? getComputedStyle(e).display !== 'none' : null; };
    const forced = shownOf({ ...app.state.opts, up: true, lv: true }, app.state.data);
    return { sl, up: vis('up'), lv: vis('lv'), forcedUp: forced.up, forcedLv: forced.lv };
  });
  ck(chipsLv.sl ? '⑤ 同级别正式版：「高一级」藏起来、「级别对照」露着；opts 里开着也不画（shownOf.up／lv＝false）'
                : '⑤ 现行口径：「高一级」「级别对照」两颗照常露着（牙）',
     chipsLv.sl ? (chipsLv.up === false && chipsLv.lv === true && !chipsLv.forcedUp && !chipsLv.forcedLv)
                : (chipsLv.up === true && chipsLv.lv === true && chipsLv.forcedUp === true),
     JSON.stringify(chipsLv));

  // ⑤b 「级别对照」在同级别下：露着、按灰、没按下、悬停写「同级别下不适用：…L38:35…」；切回现行口径 ⇒ 悬停说明撤掉（Nova 13:14 选 ①）。
  //   后台还没翻默认 ⇒ 页面里把 `trend_reading` 改成 same_level 再重画（量的是前端读不读这个字段，不是后台给不给）。
  const LV = await p.evaluate(async () => {
    const app = window.__app, d = app.state.data, was = d.trend_reading;
    const read = () => { const e = document.querySelector('.chip[data-key="lv"]'), u = document.querySelector('.chip[data-key="up"]');
      return { lvShown: getComputedStyle(e).display !== 'none', lvDis: e.disabled, lvPressed: e.getAttribute('aria-pressed'), title: e.getAttribute('title'),
               upShown: getComputedStyle(u).display !== 'none' }; };
    d.trend_reading = 'same_level'; app.repaint(); await new Promise((r) => setTimeout(r, 600));
    const sl = read();
    // 「切回现行」＝载荷里**没有** trend_reading（现行后台就是这样），不是「恢复原值」—— 真后台原值就是 same_level（9a9ba34 起），恢复它量不到现行
    delete d.trend_reading; app.repaint(); await new Promise((r) => setTimeout(r, 600));
    const back = read();
    if (was !== undefined) d.trend_reading = was;
    app.repaint(); await new Promise((r) => setTimeout(r, 600));
    return { sl, back };
  });
  ck('⑤b 同级别下「级别对照」露着、按灰、没按下，悬停写「同级别下不适用…L38:35…」；「高一级」藏着；切回现行 ⇒ 悬停说明撤掉',
     LV.sl.lvShown && LV.sl.lvDis && LV.sl.lvPressed === 'false' && /^同级别下不适用：/.test(LV.sl.title || '') && /L38:35/.test(LV.sl.title || '')
       && LV.sl.upShown === false && LV.back.title === null && LV.back.upShown === true,
     JSON.stringify(LV));

  // ③ 牙：把载荷里的 state 全拿掉（现行后台本来就没有）⇒ 0 个空心点、0 个「待确认」
  await p.evaluate(() => { for (const q of window.__app.state.data.trend.bounds) delete q.state; });
  await nudge();
  const base = await read();
  ck('③ 牙：载荷没有 state ⇒ 0 个空心点、0 个「待确认」',
     base.states !== null && base.states.length > 0
       && base.states.every((s) => !s.hollow) && base.deaths.every((r) => !(r.txt || '').includes('待确认')),
     `屏上 ${base.states ? base.states.length : 'null'} 刀　空心 ${base.states ? base.states.filter((s) => s.hollow).length : '-'}`);

  // 改载荷：现行后台刀很稀（ZEC 15m 两万根里十几把），一屏常常只有一两把 ⇒ 挑屏上**一把**刀，三种情形轮流套在它身上，
  //   每套一次重画一次、量一次。别的刀一律 confirmed（量「其余都实心」）。
  const pick = await p.evaluate(() => {
    const app = window.__app, ts = app.chart.timeScale(), T = app.state.data.trend;
    // 右边留 160px：字（「比不了（待确认） ·」）要放得下。原来写死 x < 1250，可画布才 1188 宽 —— 数据一往前走，挑到贴右沿的刀，
    //   图层照规矩不写字（㊿e：放不下就换格或不写），这一格就假红了（10-09 15:2x 在 Bram a5a7508 上撞到，跟后台无关）。
    const W = document.querySelector('#chart canvas').getBoundingClientRect().width;
    const on = T.bounds.filter((q) => { const x = ts.logicalToCoordinate(q.bar); return x !== null && x > 120 && x < W - 160; });
    if (!on.length) return { err: '屏上没有刀' };
    for (const q of T.bounds) q.state = 'confirmed';
    const t = on[on.length - 1];
    window.__slfe = { t, orig: { rule: t.rule, death: t.death, death_why: t.death_why } };
    const c = document.querySelector('#chart canvas').getBoundingClientRect();
    const SHORT = { '趋势背驰': '趋势背驰', '盘整背驰': '盘整背驰', '小转大': '小转大', '盘整·未见背驰': '未见背驰', '比不了': '比不了', 'D2-8 补刀': '补刀' };   // 期望表另写一份
    return { short: SHORT[t.death], bar: t.bar, death: t.death, x: Math.round(ts.logicalToCoordinate(t.bar)), cx: c.left, cy: c.top };
  });
  if (pick.err) { console.error(pick.err); await b.close(); process.exit(2); }
  const setCase = (k) => p.evaluate((k) => {
    const { t, orig } = window.__slfe;
    // 把这把刀的价挪到画格正中（同 measure ㊿e 的手法）：原位常贴着格顶、挤在价签堆里，小字三格都放不下就不写 ——
    //   那样「待确认」写没写出来就量不到了（第一版这么假绿过：A、C 两格字都是 null 也算过）。
    const app = window.__app, H = app.chart.panes()[0].getHeight();
    t.price = app.state.candleSeries.coordinateToPrice(H / 2);
    // A 量的是「D2 刀待确认」：挑到的刀要是 S5（盘整相连，没有短名，正式口径下图尾多半是它）⇒ 换成 D2 的「比不了」再量
    if (k === 'A') { Object.assign(t, orig, { state: 'pending' }); if (t.rule === 'S5' || t.death === '盘整相连' || !t.death) Object.assign(t, { rule: 'D2-2', death: '比不了' }); window.__slfe.shortA = t.death; }
    if (k === 'B') Object.assign(t, { rule: 'S5', death: '盘整相连', death_why: '不分类（同级别两个盘整的连接，L38:20；S12）', state: 'confirmed' });
    if (k === 'C') Object.assign(t, { rule: 'S5', death: '盘整相连', death_why: '不分类（同级别两个盘整的连接，L38:20；S12）', state: 'pending' });
  }, k);
  const one = async (k) => { await setCase(k); await nudge(); const r = await read();
    return { st: (r.states || []).find((s) => s.bar === pick.bar), dd: r.deaths.find((x) => x.bar === pick.bar), r }; };
  const desc = (o) => `点 ${o.st ? (o.st.hollow ? '空心' : '实心') : '没画'}　字 ${o.dd ? JSON.stringify(o.dd.txt) : '无'}`;
  const bare = (o) => (o.dd && o.dd.txt ? o.dd.txt.replace(/^· | ·$/g, '') : null);

  const A = await one('A');
  const SHORT_A = { '趋势背驰': '趋势背驰', '盘整背驰': '盘整背驰', '小转大': '小转大', '盘整·未见背驰': '未见背驰', '比不了': '比不了', 'D2-8 补刀': '补刀' }[await p.evaluate(() => window.__slfe.shortA)];
  ck('② 待确认（D2 刀）⇒ 空心点＋字「<短名>（待确认）」（刀挪到格中，必须写得出来）',
     !!A.st && A.st.hollow && !!A.dd && !!A.dd.mode && bare(A) === SHORT_A + '（待确认）', `刀 ${pick.bar}（量时 ${SHORT_A}）　${desc(A)}`);
  const othersSolid = (o) => (o.r.states || []).length > 0 && (o.r.states || []).filter((s) => s.bar !== pick.bar).every((s) => !s.hollow)
    && o.r.deaths.filter((x) => x.bar !== pick.bar).every((x) => !(x.txt || '').includes('待确认'));
  ck('②c 其余 confirmed 的刀：实心、不带「待确认」', othersSolid(A), `屏上 ${(A.r.states || []).length} 刀`);

  const B = await one('B');
  ck('① 盘整相连（confirmed）⇒ 实心点、图上 0 个字', !!B.st && !B.st.hollow && !(B.dd && B.dd.mode), desc(B));
  await p.mouse.move(pick.cx + pick.x, pick.cy + 300); await sleep(300);
  const tip = await p.evaluate(() => { const e = document.getElementById('ghosttip'); return e && e.classList.contains('on') ? e.textContent : ''; });
  ck('①b 悬停盘整相连 ⇒「死点：盘整相连」＋「出处：L38:20…」＋「状态：已确认」',
     tip.includes('死点：盘整相连') && /出处：L38:20/.test(tip) && tip.includes('状态：已确认'), JSON.stringify(tip.slice(0, 90)));
  await p.mouse.move(5, 5);

  const C = await one('C');
  ck('②b 待确认的盘整相连 ⇒ 空心点；字只有「待确认」，不出「盘整相连」',
     !!C.st && C.st.hollow && !!C.dd && !!C.dd.mode && bare(C) === '待确认', desc(C));

  // ⑥ 新笔三选一（B-10＝C，上线清单 #14／#21）：/api/meta 的 pen_min_options 里有 "new" ⇒
  //   组名「笔」、三颗（老笔 6 根／老笔 7 根／新笔）；点「新笔」⇒ 请求带 pen_min=new、回显 pen_rule=new、那颗亮、
  //   地址栏 pen=new、图脚说「新笔」且**不说「最少几根」**；带着 ?pen=new 重开一页 ⇒ 还是新笔（Number('new') 那个坑）。
  //   名单里没有 new（现行后台）⇒ 组名照旧「笔最少几根 K 线」、没有新笔那颗（牙）。
  const meta = await p.evaluate(async () => (await fetch('/api/meta')).json());
  const hasNew = Array.isArray(meta.pen_min_options) && meta.pen_min_options.includes('new');
  const grp = () => p.evaluate(() => {
    const g = document.getElementById('pgroup');
    if (!g) return null;
    return { cap: (g.querySelector('.mcap') || {}).textContent, chips: [...g.querySelectorAll('.mchip')].map((b) => [b.dataset.pen, b.textContent, b.getAttribute('aria-checked')]) };
  });
  const g0 = await grp();
  if (!hasNew) {
    ck('⑥ 现行后台（名单没有 new）：组名照旧、没有新笔那颗（牙）',
       !!g0 && g0.cap === '笔最少几根 K 线' && !g0.chips.some((c) => c[0] === 'new'), JSON.stringify(g0));
  } else {
    const reqs = []; p.on('request', (r) => { if (r.url().includes('/api/chart')) reqs.push(r.url()); });
    // ★ 等回显，不睡死：新笔那档后台第一次是冷算，8bf2941 上实测 2.5 s 左右才回，固定睡 2.5 s 会量在回来之前（假红过一次）
    await p.locator('.mchip[data-pen="new"]').click();
    await p.waitForFunction(() => (window.__app.state.data.meta || {}).pen_rule === 'new', null, { timeout: 20000 }).catch(() => {});
    await sleep(600);
    const after = await p.evaluate(() => ({ url: location.search, rule: (window.__app.state.data.meta || {}).pen_rule,
      foot: (document.getElementById('meta') || document.body).textContent }));
    const g1 = await grp();
    const sentNew = reqs.some((u) => /[?&]pen_min=new\b/.test(u));
    const footOk = /新笔/.test(after.foot) && !/新笔（最少/.test(after.foot);
    ck('⑥ 名单有 new：组名「笔」三颗；点新笔 ⇒ 请求 pen_min=new、回显 pen_rule=new、那颗亮、地址栏 pen=new、图脚不说「最少几根」',
       !!g0 && g0.cap === '笔' && g0.chips.length === 3 && g0.chips.some((c) => c[0] === 'new' && c[1] === '新笔')
         && sentNew && after.rule === 'new' && /[?&]pen=new\b/.test(after.url) && footOk
         && g1.chips.find((c) => c[0] === 'new')[2] === 'true',
       `组 ${JSON.stringify(g0)}　发出 pen_min=new ${sentNew}　回显 ${after.rule}　地址 ${after.url}　图脚新笔 ${footOk}`);
    const p2 = await (await b.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
    await p2.goto(PAGE + '?symbol=ZECUSDT&tf=15m&pen=new', { waitUntil: 'domcontentloaded' });
    await p2.waitForFunction(() => window.__app && window.__app.state.data && document.getElementById('pgroup'), null, { timeout: 60000 }).catch(() => {});
    await p2.waitForFunction(() => (window.__app.state.data.meta || {}).pen_rule === 'new', null, { timeout: 20000 }).catch(() => {});
    await sleep(600);
    const re = await p2.evaluate(() => ({ rule: (window.__app.state.data.meta || {}).pen_rule, url: location.search,
      on: (document.querySelector('.mchip[data-pen="new"]') || {}).getAttribute?.('aria-checked') }));
    ck('⑥b 带着 ?pen=new 打开 ⇒ 还是新笔（回显 pen_rule=new、那颗亮、地址栏不被抹掉）',
       re.rule === 'new' && re.on === 'true' && /[?&]pen=new\b/.test(re.url), JSON.stringify(re));
    await p2.context().close();
  }

  // ⑦ 已撤回（Q-6 选 A，小栋 10-09 12:47）：载荷顶层 `withdrawn`（Bram 12:22 方案，后台还没上 ⇒ **在页面里塞假数据**）。
  //   取屏上两根 K 线当「撤掉的」那一刀、那一条线段（开盘时间＋低点／高点），再塞一条 t 不在这一窗 K 线里的：
  //   ⇒ 屏上画 2 个叉（刀那条、线段那条），t 对不上的那条不画；叉的位置＝那根 K 线的 x、那个价的 y；
  //   字是「已撤回：笔回头改了（价）」／「线段已撤回：…」；「走势分段」关掉 ⇒ 一个都不画；载荷没有 withdrawn ⇒ 0 个（牙）。
  const WD = await p.evaluate(async () => {
    const app = window.__app, st = app.state, d = st.data, ts = app.chart.timeScale(), s = st.candleSeries;
    const W = document.querySelector('#chart canvas').getBoundingClientRect().width;
    // 叉只要一根 K 线的开盘时间和一个价，不必是真刀：取可视窗口 30%、60% 处那两根（一根拿低点、一根拿高点）
    const v = ts.getVisibleLogicalRange(), i1 = Math.round(v.from + (v.to - v.from) * 0.3), i2 = Math.round(v.from + (v.to - v.from) * 0.6);
    if (!d.bars[i1] || !d.bars[i2]) return { err: '可视窗口里没有 K 线' };
    const a = { bar: i1, kind: 'L', price: d.bars[i1].l }, z = { bar: i2, kind: 'H', price: d.bars[i2].h };
    const fake = [
      { kind: 'd2', t: d.bars[a.bar].t, dir: a.kind, price: a.price, at: d.bars[d.bars.length - 1].t },
      // 线段那条照 Bram 9a9ba34 的真形状：没有 price，起止是 (t,p0)→(t1,p1)，叉落在终点
      { kind: 'seg', t: d.bars[a.bar].t, t1: d.bars[z.bar].t, dir: 'up', p0: a.price, p1: z.price, at: d.bars[d.bars.length - 1].t },
      { kind: 's5', t: d.bars[0].t - 86400000 * 30, dir: 'L', price: a.price, at: d.bars[d.bars.length - 1].t },   // 不在这一窗 ⇒ 不画
    ];
    const redraw = async () => { const v = ts.getVisibleLogicalRange(); ts.setVisibleLogicalRange({ from: v.from + 0.01, to: v.to + 0.01 }); await new Promise((r) => setTimeout(r, 700)); };
    const want = (q) => ({ x: Math.round(ts.timeToCoordinate(d.bars[q.bar].t / 1000)), y: Math.round(s.priceToCoordinate(q.price)) });
    const noWd = (st.trendDrawn.withdrawn || []).length;
    d.withdrawn = fake; await redraw();
    const got = (st.trendDrawn.withdrawn || []).map((w) => ({ kind: w.kind, x: w.x, y: w.y }));
    const labels = (st.trendDrawn.labels || []).map((L) => L[4]).filter((t) => /已撤回/.test(t || ''));
    const chip = document.querySelector('.chip[data-key="trend"]'); chip.click(); await redraw();
    const off = (st.trendDrawn.withdrawn || []).length; chip.click(); await redraw();
    return { noWd, got, labels, want: [want(a), want(z)], off };
  });
  if (WD.err) { console.error(WD.err); await b.close(); process.exit(2); }
  const near = (g, w) => g && Math.abs(g.x - w.x) <= 1 && Math.abs(g.y - w.y) <= 1;
  ck('⑦ 已撤回：屏上那两条画了淡红叉、位置＝那根 K 线的开盘时间和那个价；t 不在这一窗的那条不画',
     WD.got.length === 2 && near(WD.got[0], WD.want[0]) && near(WD.got[1], WD.want[1]), JSON.stringify({ got: WD.got, want: WD.want }));
  ck('⑦b 字：刀写「已撤回：笔回头改了（价）」、线段写「线段已撤回：笔回头改了（价）」',
     WD.labels.length === 2 && /^已撤回：笔回头改了（/.test(WD.labels[0]) && /^线段已撤回：笔回头改了（/.test(WD.labels[1]), JSON.stringify(WD.labels));
  ck('⑦c 「走势分段」关掉 ⇒ 一个叉都不画；载荷没有 withdrawn（现行后台）⇒ 0 个（牙）', WD.off === 0 && WD.noWd === 0, `关掉 ${WD.off}　改前 ${WD.noWd}`);

  // ⑦d 已撤回的线段：起点在屏上、终点滚出右边（往左翻页就会这样）⇒ 屏上那一截淡红虚线照画，叉不打（终点不在屏上）。
  //   第一版先看终点在不在屏上、不在就整条跳过（card-6f97c999-ed0，Nova 14:36 审 088fe62 时看出来的）。
  const WE = await p.evaluate(async () => {
    const app = window.__app, d = app.state.data, ts = app.chart.timeScale(), st = app.state;
    const mid = Math.round(d.bars.length / 2); ts.setVisibleLogicalRange({ from: mid - 150, to: mid + 150 }); await new Promise((r) => setTimeout(r, 700));   // 视口摆中间：右边得有已加载、但不在屏上的 K 线
    const v = ts.getVisibleLogicalRange(), a = Math.round(v.from + (v.to - v.from) * 0.7), z = Math.min(d.bars.length - 1, Math.round(v.to) + 40);
    if (!d.bars[a] || !d.bars[z] || z <= v.to) return { err: '视口右边没有已加载的 K 线可当「屏外终点」' };
    d.withdrawn = [{ kind: 'seg', t: d.bars[a].t, t1: d.bars[z].t, dir: 'up', p0: d.bars[a].l, p1: d.bars[z].h, at: d.bars[d.bars.length - 1].t }];
    const redraw = async () => { const r = ts.getVisibleLogicalRange(); ts.setVisibleLogicalRange({ from: r.from + 0.01, to: r.to + 0.01 }); await new Promise((r) => setTimeout(r, 700)); };
    await redraw();
    const W = document.querySelector('#chart canvas').getBoundingClientRect().width;
    const out = { lines: (st.trendDrawn.withdrawnLines || []).slice(), crosses: (st.trendDrawn.withdrawn || []).length, W };
    delete d.withdrawn; await redraw(); return out;
  });
  if (WE.err) { console.error(WE.err); await b.close(); process.exit(2); }
  ck('⑦d 撤回的线段终点滚出屏外、起点在屏上 ⇒ 屏上那一截虚线照画（x0 在屏内、x1 在屏外右边），叉不打',
     WE.lines.length === 1 && WE.lines[0].x0 >= 0 && WE.lines[0].x0 <= WE.W && WE.lines[0].x1 > WE.W && WE.crosses === 0, JSON.stringify(WE));

  // ⑧ D-3 选 C（小栋 10-09 12:57）：载荷带 `segs_std`（标准化线段）⇒ 图上「线段」画它：除最后一条外实线、最后一条短虚线；
  //   未完成段照旧长虚线；没有 `segs_std`（现行后台）⇒ 照旧画原始段、短虚线那条是空的（牙）。
  //   后台还没出这个字段 ⇒ 页面里塞假的：拿原始已完成段，把最后两条并成一条当「标准化后」的样子。
  const SD = await p.evaluate(async () => {
    const app = window.__app, d = app.state.data, S = app.segSeries, t = (i) => d.bars[i].t / 1000;
    const pts = (ser) => ser.data().map((q) => [q.time, q.value]);
    const before = { solid: pts(S.solid).length, last: pts(S.stdLast).length };
    const done = d.segs.filter((s) => !s.live);
    if (done.length < 3) return { err: '已完成线段不到 3 条' };
    const a = done.at(-2), z = done.at(-1);
    const std = done.slice(0, -2).map((s) => ({ i0: s.i0, i1: s.i1, p0: s.p0, p1: s.p1, dir: s.dir }))
      .concat([{ i0: a.i0, i1: z.i1, p0: a.p0, p1: z.p1, dir: a.dir }]);
    d.segs_std = std; app.repaint();
    // 视口摆到最后一条标准化线段上（⑦ 那几格把视口挪去了刀最多的一扇，终点可能在屏外 ⇒ 字不画，那是空转）
    app.chart.timeScale().setVisibleLogicalRange({ from: a.i0 - 60, to: d.bars.length + 5 }); await new Promise((r) => setTimeout(r, 700));
    const solid = pts(S.solid), last = pts(S.stdLast), dash = pts(S.dash);
    const wantSolid = [[t(std[0].i0), std[0].p0]].concat(std.slice(0, -1).map((s) => [t(s.i1), s.p1]));
    const L = std.at(-1);
    // 字要等标注层下一帧画完：挪一下视口逼它重画
    const v = app.chart.timeScale().getVisibleLogicalRange(); app.chart.timeScale().setVisibleLogicalRange({ from: v.from + 0.01, to: v.to + 0.01 }); await new Promise((r) => setTimeout(r, 700));
    const lab = app.state.segStdLabel;
    const wantX = Math.round(app.chart.timeScale().timeToCoordinate(t(L.i1)));
    const realStd = d.segs_std;   // 真后台（9a9ba34 起）本来就送 segs_std；量「没有 segs_std」那一半得先拿掉、量完放回去
    delete d.segs_std; app.repaint(); await new Promise((r) => setTimeout(r, 400));
    app.chart.timeScale().setVisibleLogicalRange({ from: v.from + 0.02, to: v.to + 0.02 }); await new Promise((r) => setTimeout(r, 700));
    const labAfter = app.state.segStdLabel;
    const rawDone = d.segs.filter((s) => !s.live).length;
    return { lab, wantX, labAfter, before, std: std.length, solidOk: JSON.stringify(solid) === JSON.stringify(wantSolid), solidN: solid.length,
      last, wantLast: [[t(L.i0), L.p0], [t(L.i1), L.p1]], dashN: dash.length, after: { solid: pts(S.solid).length, last: pts(S.stdLast).length }, rawDone,
      restored: await (async () => { if (realStd) { d.segs_std = realStd; app.repaint(); await new Promise((r) => setTimeout(r, 300)); } return !!realStd; })() };
  });
  if (SD.err) { console.error(SD.err); await b.close(); process.exit(2); }
  ck('⑧c 短虚线那条的终点旁写「终点还可能挪」（跟长虚线的「未收盘」分得开）；撤掉 segs_std 字就没了',
     !!SD.lab && SD.lab.text === '终点还可能挪' && Math.abs(SD.lab.x - SD.wantX) <= 1 && SD.labAfter === null,
     `字 ${JSON.stringify(SD.lab)}　要的 x=${SD.wantX}　撤掉以后 ${JSON.stringify(SD.labAfter)}`);
  ck('⑧ D-3 C：有 segs_std ⇒ 实线＝标准化那套除最后一条（点逐个对上）；最后一条单独画短虚线、两头＝它的起止',
     SD.solidOk && JSON.stringify(SD.last) === JSON.stringify(SD.wantLast), `标准化 ${SD.std} 条　实线 ${SD.solidN} 点　短虚线 ${JSON.stringify(SD.last)}`);
  ck('⑧b 未完成段照旧画长虚线；载荷没有 segs_std ⇒ 照旧画原始段、短虚线那条是空的（牙）',
     SD.dashN > 0 && SD.after.last === 0 && SD.after.solid === SD.rawDone + 1,
     `长虚线 ${SD.dashN} 点　撤掉以后 ${JSON.stringify(SD.after)}（原始已完成 ${SD.rawDone} 条 ⇒ 要 ${SD.rawDone + 1} 点）　真后台本来就有 segs_std：${SD.restored}`);

  // ⑧d D-3 C 按 `state` 画虚线（Bram 提的 (C)：最后两条都算待确认；前端不写死条数，照载荷每条的 state）：
  //   最后两条 pending ⇒ 短虚线那条折线 3 个点（两条首尾相接）、实线少两条；全部 confirmed ⇒ 短虚线是空的、字也不写；
  //   没有 state ⇒ 退回「只有最后一条」（这一格是牙：老载荷不许变样）。
  const ST = await p.evaluate(async () => {
    const app = window.__app, d = app.state.data, S = app.segSeries;
    const done = d.segs.filter((s) => !s.live).map((s) => ({ i0: s.i0, i1: s.i1, p0: s.p0, p1: s.p1, dir: s.dir }));
    const real = d.segs_std, wait = async () => { app.repaint(); const ts = app.chart.timeScale(), v = ts.getVisibleLogicalRange(); ts.setVisibleLogicalRange({ from: v.from + 0.01, to: v.to + 0.01 }); await new Promise((r) => setTimeout(r, 700)); };
    const read = () => ({ solid: S.solid.data().length, dash: S.stdLast.data().length, label: !!app.state.segStdLabel });
    const ts = app.chart.timeScale(); ts.setVisibleLogicalRange({ from: done.at(-3).i0 - 40, to: d.bars.length + 5 }); await new Promise((r) => setTimeout(r, 600));
    d.segs_std = done.map((s, k) => ({ ...s, state: k >= done.length - 2 ? 'pending' : 'confirmed' })); await wait(); const two = read();
    d.segs_std = done.map((s) => ({ ...s, state: 'confirmed' })); await wait(); const none = read();
    d.segs_std = done; await wait(); const old = read();
    if (real) d.segs_std = real; else delete d.segs_std; await wait();
    return { n: done.length, two, none, old };
  });
  ck('⑧d 按 state 画：最后两条 pending ⇒ 短虚线 3 点、实线少两条、写字；全 confirmed ⇒ 没有短虚线、不写字；没有 state ⇒ 只有最后一条（老载荷不变样）',
     ST.two.dash === 3 && ST.two.solid === ST.n - 1 && ST.two.label && ST.none.dash === 0 && ST.none.solid === ST.n + 1 && !ST.none.label
       && ST.old.dash === 2 && ST.old.solid === ST.n && ST.old.label, JSON.stringify(ST));

  if (SHOTS) await p.screenshot({ path: require('path').join(SHOTS, 'samelevel-fe.png') });
  await b.close();
  console.log(red ? `✗ ${red} 格红（${n - red}/${n} 过）` : `${n}/${n} 过`);   // predeploy 认「N/N 过」这一行
  process.exit(red ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
