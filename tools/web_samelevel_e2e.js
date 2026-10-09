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
  const anyState = await p.evaluate(() => window.__app.state.data.trend.bounds.some((q) => 'state' in q));
  if (anyState) {
    // 先把视口挪到**最后一把 pending 的刀**那一扇（图尾那几把 S5 一律待确认，D-4）—— 不挪的话屏上可能一把 pending 都没有，这格就空过了
    await p.evaluate(async () => {
      const app = window.__app, ts = app.chart.timeScale(), v = ts.getVisibleLogicalRange(), w = v.to - v.from;
      const pd = app.state.data.trend.bounds.filter((q) => q.state === 'pending').map((q) => q.bar);
      if (pd.length) { const c = pd[pd.length - 1]; ts.setVisibleLogicalRange({ from: c - w * 0.6, to: c + w * 0.4 }); }
      await new Promise((r) => setTimeout(r, 900));
    });
    const real = await p.evaluate(() => {
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
    ck('④ 真载荷：屏上每把刀「空心 ⟺ state=pending」；字跟 state／death 对得上（盘整相连 confirmed 不写字）',
       real.states.length > 0 && nPend > 0 && !badDot.length && !badTxt.length,
       `屏上 ${real.states.length} 刀（pending ${nPend}）${badDot.length ? '　✗ 点不对 ' + JSON.stringify(badDot) : ''}${badTxt.length ? '　✗ 字不对 ' + JSON.stringify(badTxt) : ''}`);
  } else console.log('－ ④ 跳过：这个后台还不给 state');

  // ⑤ 「高一级」「级别对照」两颗芯片（Nova 10-09 09:07）：同级别正式版（trend_reading=same_level）⇒ 两颗**藏起来**，
  //   而且就算 opts 里 up／lv 是开的（地址栏带着 up=1 进来的那种），画图那张判据 `shownOf` 也给 false；
  //   现行口径 ⇒ 两颗照常露着（牙：别把现行口径也藏了）。
  const chipsLv = await p.evaluate(async () => {
    const app = window.__app, { shownOf } = await import('/layers.js');
    const sl = (app.state.data || {}).trend_reading === 'same_level';
    const vis = (k) => { const e = document.querySelector(`.chip[data-key="${k}"]`); return e ? getComputedStyle(e).display !== 'none' : null; };
    const forced = shownOf({ ...app.state.opts, up: true, lv: true }, app.state.data);
    return { sl, up: vis('up'), lv: vis('lv'), forcedUp: forced.up, forcedLv: forced.lv };
  });
  ck(chipsLv.sl ? '⑤ 同级别正式版：「高一级」「级别对照」两颗藏起来；opts 里开着也不画（shownOf.up／lv＝false）'
                : '⑤ 现行口径：「高一级」「级别对照」两颗照常露着（牙）',
     chipsLv.sl ? (chipsLv.up === false && chipsLv.lv === false && !chipsLv.forcedUp && !chipsLv.forcedLv)
                : (chipsLv.up === true && chipsLv.lv === true && chipsLv.forcedUp === true),
     JSON.stringify(chipsLv));

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
    const on = T.bounds.filter((q) => { const x = ts.logicalToCoordinate(q.bar); return x !== null && x > 120 && x < 1250; });
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
    await p.locator('.mchip[data-pen="new"]').click(); await sleep(2500);
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
    await sleep(2500);
    const re = await p2.evaluate(() => ({ rule: (window.__app.state.data.meta || {}).pen_rule, url: location.search,
      on: (document.querySelector('.mchip[data-pen="new"]') || {}).getAttribute?.('aria-checked') }));
    ck('⑥b 带着 ?pen=new 打开 ⇒ 还是新笔（回显 pen_rule=new、那颗亮、地址栏不被抹掉）',
       re.rule === 'new' && re.on === 'true' && /[?&]pen=new\b/.test(re.url), JSON.stringify(re));
    await p2.context().close();
  }

  if (SHOTS) await p.screenshot({ path: require('path').join(SHOTS, 'samelevel-fe.png') });
  await b.close();
  console.log(red ? `✗ ${red} 格红（${n - red}/${n} 过）` : `${n}/${n} 过`);   // predeploy 认「N/N 过」这一行
  process.exit(red ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
