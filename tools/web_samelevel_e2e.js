// 同级别正式版的前端三样（上线清单 #21 / 验收门 G10，卡 card-6273f71c-b72）：
//   ① 「盘整相连」（S5 刀，S12）图上 0 个字、悬停里有「死点：盘整相连」＋出处；
//   ② 刀上 `state`：pending ⇒ 空心点＋小字「待确认」，confirmed ⇒ 实心、不带「待确认」；
//   ③ 牙：载荷里**没有** state（现行后台）⇒ 一个空心点都没有、一个「待确认」都没有 —— 跟改之前一样。
// ★ 后台的 `state` 字段还没进引擎（Bram 08:34 起草、未提交），所以这里**在页面里改载荷**：挑屏上几把真刀，
//   把它们的 state／death 改掉再重画。量的是**前端读不读、怎么画**，不量后台给得对不对（那是 G2 回放＋check_parity 的事）。
// 跑法：真后台 `python3 web/server.py --port 8797 --no-prewarm`（要联网取币安），然后
//   NODE_PATH=<playwright 的 node_modules> node tools/web_samelevel_e2e.js http://127.0.0.1:8797/ [出图目录]
// 退出码：0 全绿；1 有红；2 跑不动（页面没数据／屏上没刀 —— 查不了 ≠ 通过）
const { chromium } = require('playwright');
const PAGE = (process.env.E2E_URL || process.argv[2] || '').replace(/\/?$/, '/');
if (!/^https?:/.test(PAGE)) { console.error('要给页面地址'); process.exit(2); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let red = 0;
const ck = (name, ok, msg) => { if (!ok) red++; console.log(`${ok ? '✓' : '✗'} ${name}　${msg}`); };

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

  // ③ 牙先跑：原样载荷（现行后台没有 state）
  const base = await read();
  const anyState = await p.evaluate(() => window.__app.state.data.trend.bounds.some((q) => 'state' in q));
  ck('③ 牙：载荷没有 state ⇒ 0 个空心点、0 个「待确认」',
     base.states !== null && base.states.length > 0 && !anyState
       && base.states.every((s) => !s.hollow) && base.deaths.every((r) => !(r.txt || '').includes('待确认')),
     `屏上 ${base.states ? base.states.length : 'null'} 刀　载荷带 state=${anyState}　空心 ${base.states ? base.states.filter((s) => s.hollow).length : '-'}`);

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
    if (k === 'A') Object.assign(t, orig, { state: 'pending' });
    if (k === 'B') Object.assign(t, { rule: 'S5', death: '盘整相连', death_why: '不分类（同级别两个盘整的连接，L38:20；S12）', state: 'confirmed' });
    if (k === 'C') Object.assign(t, { rule: 'S5', death: '盘整相连', death_why: '不分类（同级别两个盘整的连接，L38:20；S12）', state: 'pending' });
  }, k);
  const one = async (k) => { await setCase(k); await nudge(); const r = await read();
    return { st: (r.states || []).find((s) => s.bar === pick.bar), dd: r.deaths.find((x) => x.bar === pick.bar), r }; };
  const desc = (o) => `点 ${o.st ? (o.st.hollow ? '空心' : '实心') : '没画'}　字 ${o.dd ? JSON.stringify(o.dd.txt) : '无'}`;
  const bare = (o) => (o.dd && o.dd.txt ? o.dd.txt.replace(/^· | ·$/g, '') : null);

  const A = await one('A');
  ck('② 待确认（D2 刀）⇒ 空心点＋字「<短名>（待确认）」（刀挪到格中，必须写得出来）',
     !!A.st && A.st.hollow && !!A.dd && !!A.dd.mode && bare(A) === pick.short + '（待确认）', `刀 ${pick.bar}（${pick.death}）　${desc(A)}`);
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

  if (process.argv[3]) await p.screenshot({ path: require('path').join(process.argv[3], 'samelevel-fe.png') });
  await b.close();
  console.log(red ? `✗ ${red} 格红` : '✓ 全绿');
  process.exit(red ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
