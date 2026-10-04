// 「网页光标读数」的浏览器工装（card-4cdf628c-c84，2026-10-04）
//
// ★ 它**不是**六把尺里的一把：尺子是纯函数、秒级、谁都能跑；这一套要 playwright ＋ 真浏览器，
//   慢得多也脆得多。放在仓里是为了**别人能复跑**（跟 tools/web_more_e2e.js / web_measure_e2e.js 一个道理）。
//
// 量的是**接线**，不是算法：那一根的四个数从哪来、精度跟谁走、手势吃不吃得下、手机上长按认不认。
//   ① 一打开读数块**不显示**（默认看不见 —— 它不是一块常驻的膏药。注意它在浮层那排里**占着格**，
//      那是要的：换档那句话出来/收掉时，读数块的位置不许跳）
//   ② 桌面悬停 ⇒ 出现，而且四个数就是**指针底下那一根**的四个数（时间对得上、值在半个 tick 内）
//   ③ 小数位数 = decimals(tick) —— ★ tick 特意跟数据错开（数据两位小数、tick 0.1）：
//      写死两位、或者把数据原样吐出来，这一格都得红（不然「精度跟价签一致」是句空话）
//   ④ 第一行那一刻 = **时间轴**上念的那一句（同一个 timeLabel；格式抄一份就迟早在某处错开）
//   ⑤ 涨跌幅 = (收 − 前收)/前收（工装拿**同一份 bars** 自己算一遍），符号跟药丸底色一致
//   ⑥ 最左边那一根没有前收 ⇒ 印「—」，**不编**一个 0.00% 给它
//   ⑦ 悬停最右那一根：「收」跟页头「最新 …」**逐字相同** —— 两处读数不许说两个数（同一个 tick）
//   ⑧ 指针离开图 ⇒ 收掉，而且是**像素上真没了**（同一块区域、同一个十字线，摘掉 .on 前后必须不一样：
//      只读 class/visibility 是替身 —— `.more` 那次就是状态全对、整块被画布盖住）
//   ⑨ 不挡图：读数块**正中心**的 elementFromPoint 落在画布上（不是它自己）
//   ⑩ 不吃拖拽：**从读数块正中心**按下往左拖 ⇒ 视口真的动了（这一格量的是"浮层吃手势"的真身）
//   ⑪ 跟图上那句「换档重算」**不许叠**：两块同时在时盒子不相交（那句真出来了才判 ——
//      它没出来这一格就是空转，所以先断言它 `on`）
//   ⑫ 手机：**长按**出读数，读的是手指底下那一根
//   ⑬ 手机：长按之后横拖 ⇒ 读数跟着换、**视口一动没动**（读数在走，不是图在滚）
//   ⑭ 手机的手势出口（**换一页新起**，不接 ⑫⑬ 的尾巴 —— 库的触摸状态机有记忆，理由写在那一节）：
//      第一下快滑＝拖图；长按 ⇒ 读到、**抬手后还在**；这一下之后的横滑归十字线（视口不许动）；
//      **轻点一下**再快滑 ⇒ 视口平移、读数收掉。（⑭ 后半量的是**库的手势模型**，不是我们的浮层）
//
// 假后台：拿仓里 zec_1h.json 的真 bars/结构，只改 `meta.tick`（精度那几条的被测量）、
// 以及**第二份**（span≥2）把笔和线段的价格乘 1.002（⑪ 要的那句「结构重算了」得真够格触发）。
// 编出来的只是这两样，K 线是样本里那份真数据。
//
// 跑法（三样都要）：
//   1) 静态服务，**只绑回环**（部署纪律：不许绑全网卡）：
//        python3 -m http.server 8793 --bind 127.0.0.1 --directory web
//   2) playwright：`npm i playwright && npx playwright install chromium`（各机器一次）
//      node_modules 不在仓里 —— 在任何装好 playwright 的目录下跑，用 NODE_PATH 指过来即可。
//   3) node tools/web_readout_e2e.js [输出目录] [页面地址]
//        输出目录默认 $TMPDIR/readout-e2e（截图落这儿；不写进仓）
//        页面地址默认 http://127.0.0.1:8793/
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
const OUT = process.argv[2] || path.join(os.tmpdir(), 'readout-e2e');
const PAGE = (process.argv[3] || 'http://127.0.0.1:8793/').replace(/\/?$/, '/');
const FULL = JSON.parse(fs.readFileSync(path.join(WEB, 'fixtures/zec_1h.json'), 'utf8'));

// 假后台的开关（跟 web_more_e2e 一样：一格一格摆场景，**开页之前**声明）
//   tick ：这一页的价格精度。★ 默认 0.1，而样本里的价是两位小数 —— 故意错开：
//          「读数几位小数」那一格要是空转（写死两位也能过），它就白写了。
//   bend ：**第二份**数据（span≥2）把笔/线段的价格乘 1.002 ⇒ 可视窗口里的结构真变了 ⇒ 那句提示该出来。
//   fail ：/api/chart 直接 503（留给后面加「取不到」那一族，这一套现在不用）
const DEFAULT_SCEN = { tick: 0.1, bend: false, fail: false };
const SCEN = Object.assign({}, DEFAULT_SCEN);
const scen = (o) => { Object.assign(SCEN, DEFAULT_SCEN, o || {}); };

const decimals = (t) => { const s = String(t); return s.includes('.') ? s.split('.')[1].length : 0; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function payload(span) {
  const d = JSON.parse(JSON.stringify(FULL));
  d.meta.tick = SCEN.tick;
  d.source = 'api';
  d.fetched_at = new Date().toISOString();
  d.span = span; d.span_max = 4; d.earliest = false;
  d.measure = 'macd';
  // ★ 只有**第二份**才动结构：两份都动、动的还一样，等于没动（那句提示永远不触发，⑪ 就成了空转）
  if (SCEN.bend && span >= 2) {
    d.pens = d.pens.map((p) => Object.assign({}, p, { p0: p.p0 * 1.002, p1: p.p1 * 1.002 }));
    d.segs = d.segs.map((s) => Object.assign({}, s, { p0: s.p0 * 1.002, p1: s.p1 * 1.002 }));
  }
  return d;
}

// 工装自己那份「此刻读的是哪一根」：拿页面里**同一份** bars 按时间找（页面走的就是这一条）
const barUnder = (p, pageX, box) => p.evaluate(([x, bx]) => {
  const { chart, state } = window.__app;
  const t = chart.timeScale().coordinateToTime(x - bx);            // 秒
  const bars = state.data.bars, i = bars.findIndex((b) => b.t === t * 1000);
  return { t, i, bar: i < 0 ? null : bars[i], prev: i > 0 ? bars[i - 1] : null, tick: state.data.meta.tick };
}, [pageX, box.x]);

// ★ 元素**不在**也要能读数（返回 exists:false），不许让它把工装炸掉 ——
//   「改之前」跑这一套，页面上就是没有这块：那必须是**一格一格报红**，而不是"工装自己炸了"。
//   （炸掉看起来也"没通过"，但它没告诉你哪一格没通过，也分不出是页面坏了还是工装坏了。）
const shown = (p) => p.evaluate(() => {
  const r = document.getElementById('readout');
  if (!r) return { exists: false, on: false, vis: 'absent', bx: 0, by: 0, bw: 0, bh: 0,
                   time: '', o: '', h: '', l: '', c: '', pct: '', pctBg: '',
                   last: (document.getElementById('last') || {}).textContent || '' };
  const b = r.getBoundingClientRect();
  return { exists: true, on: r.classList.contains('on'), vis: getComputedStyle(r).visibility,
           op: getComputedStyle(r).opacity,
           bx: b.x, by: b.y, bw: b.width, bh: b.height,
           time: document.getElementById('ro-time').textContent,
           o: document.getElementById('ro-open').textContent,
           h: document.getElementById('ro-high').textContent,
           l: document.getElementById('ro-low').textContent,
           c: document.getElementById('ro-close').textContent,
           pct: document.getElementById('ro-pct').textContent,
           pctBg: getComputedStyle(document.getElementById('ro-pct')).backgroundColor,
           last: document.getElementById('last').textContent };
});

const rgbOf = (hex) => 'rgb(' + [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)).join(', ') + ')';

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const b = await chromium.launch();
  const errors = [];
  const ok = [], bad = [];
  const t = (name, cond, extra = '') => {
    const line = `${name}${extra ? '：' + extra : ''}`;
    (cond ? ok : bad).push(line);
    console.log((cond ? '  ✓ ' : '  ✗ ') + line);
  };
  const watch = (p) => {
    p.on('pageerror', (e) => errors.push('pageerror: ' + e));
    p.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  };
  // 假后台：/api/chart 一律我们答；/fixtures 关掉（逼它只能走后台那条路，跟线上同一条）
  const newCtx = async (opts) => {
    const ctx = await b.newContext(opts);
    await ctx.route('**/api/chart*', (r) => {
      if (SCEN.fail) return r.fulfill({ status: 503, body: '' });
      const span = Number(new URL(r.request().url()).searchParams.get('span') || 1);
      return r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload(span)) });
    });
    // 看法名单照常给（不然静态服务回 404，控制台会多出一条与本事无关的报错，
    // 而这一套把"页面报错"也算红 —— 报错清单里混进假警报，真出问题时就没人看了）
    await ctx.route('**/api/meta', (r) => r.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ measures: ['macd', 'slope', 'lines', 'peak'] }) }));
    await ctx.route('**/fixtures/**', (r) => r.fulfill({ status: 404, body: '' }));
    return ctx;
  };
  const open = async (ctx, q) => {
    const p = await ctx.newPage();
    watch(p);
    await p.goto(PAGE + (q || ''), { waitUntil: 'domcontentloaded' });
    await p.waitForFunction(() => window.__app && window.__app.state.data, null, { timeout: 30000 });
    await sleep(600);                                  // 等首屏那点收尾（fitContent 的回声、图脚）
    return p;
  };
  const boxOf = (p) => p.locator('#chart').boundingBox();

  // ================================================================ 桌面
  scen({ tick: 0.1 });
  const ctx = await newCtx({ viewport: { width: 1280, height: 800 } });
  const p = await open(ctx, '?symbol=ZECUSDT&tf=1h&last=300');       // 右端那一段：⑦ 要悬停最后一根
  const box = await boxOf(p);
  const MARK = await p.evaluate(async () => {                        // 涨跌色从 theme.js 读，不在这儿再抄一份
    const m = await import('/theme.js');
    return { up: m.CANDLE.up, dn: m.CANDLE.dn, ink: m.CHART.tag_ink };
  });
  const botY = Math.round(box.y + box.height - 40);                  // 往下一点，别贴着上沿那块浮层
  const midX = Math.round(box.x + box.width * 0.5);

  // ① 一打开不显示
  // ★ 这里**故意不量宽度**：读数块在浮层那一竖排里是 `visibility:hidden`，而 hidden **照样占位**
  //   （宽 131，那是它自己那几格文字量出来的）—— 占位是**要的**：那句话出来/收掉时读数块不许上下跳。
  //   要量的是"看不看得见"，那就量 opacity 和 visibility，别拿宽度当替身。
  const r0 = await shown(p);
  t('① 一打开读数块不显示（默认看不见：不是一块常驻的膏药）',
    r0.exists && !r0.on && r0.vis === 'hidden' && r0.op === '0',
    `这块在不在=${r0.exists} on=${r0.on} vis=${r0.vis} opacity=${r0.op}`);

  // ② 悬停 ⇒ 出现，四个数 = 指针下那一根
  await p.mouse.move(midX, botY);
  await sleep(300);
  const r1 = await shown(p);
  const u1 = await barUnder(p, midX, box);
  const half = Math.pow(10, -decimals(u1.tick)) / 2 + 1e-9;
  const near = (txt, v) => Math.abs(Number(String(txt).replace(/,/g, '')) - v) <= half;
  t('② 悬停 ⇒ 读数出现，四个数就是指针底下那一根（开/高/低/收）',
    r1.on && r1.vis === 'visible' && !!u1.bar && near(r1.o, u1.bar.o) && near(r1.h, u1.bar.h)
      && near(r1.l, u1.bar.l) && near(r1.c, u1.bar.c),
    `指针下第 ${u1.i} 根 ${u1.bar ? [u1.bar.o, u1.bar.h, u1.bar.l, u1.bar.c].join('/') : '?'} ⇒ 读到 ${[r1.o, r1.h, r1.l, r1.c].join('/')}`);

  // ③ 小数位数 = decimals(tick)
  const dec = decimals(u1.tick);
  const decOf = (s) => (String(s).includes('.') ? String(s).split('.')[1].length : 0);
  t('③ 读数的小数位数 = 精度（decimals(tick)），不是写死的两位',
    [r1.o, r1.h, r1.l, r1.c].every((v) => decOf(v) === dec),
    `tick=${u1.tick} ⇒ 要 ${dec} 位，读到 ${[r1.o, r1.h, r1.l, r1.c].map(decOf).join('/')}`);

  // ④ 时刻那一行 = 时间轴上念的那一句
  const wantTime = new Date(u1.t * 1000).toISOString().slice(0, 16).replace('T', ' ') + ' UTC';
  t('④ 第一行那一刻 = 时间轴上念的那一句（同一个 timeLabel）', r1.time === wantTime, `读「${r1.time}」要「${wantTime}」`);

  // ⑤ 涨跌幅 = (收 − 前收)/前收；符号跟药丸底色一致
  const wantPct = u1.prev ? (u1.bar.c - u1.prev.c) / u1.prev.c * 100 : null;
  const gotPct = r1.pct === '—' ? null : Number(r1.pct.replace('%', ''));
  const wantBg = wantPct == null ? null : wantPct > 0.005 ? rgbOf(MARK.up) : wantPct < -0.005 ? rgbOf(MARK.dn) : 'rgba(0, 0, 0, 0)';
  t('⑤ 涨跌幅 = (收 − 前收)/前收，符号跟药丸底色一致（涨=阳线色、跌=阴线色）',
    gotPct != null && wantPct != null && Math.abs(gotPct - wantPct) < 0.005 && r1.pctBg === wantBg,
    `读到 ${r1.pct}（底 ${r1.pctBg}），要 ${wantPct == null ? '?' : wantPct.toFixed(2) + '%'}（底 ${wantBg}）`);

  // ⑦ 最右那一根：「收」跟页头「最新 …」逐字相同
  const xLast = await p.evaluate(() => { const { chart, state } = window.__app;
    return chart.timeScale().timeToCoordinate(state.data.bars.at(-1).t / 1000); });
  await p.mouse.move(Math.round(box.x + Math.min(xLast, box.width - 4)), botY);
  await sleep(250);
  const r7 = await shown(p);
  const head = (r7.last || '').replace(/^最新\s*/, '');
  t('⑦ 悬停最右那一根：「收」跟页头「最新 …」逐字相同（同一个 tick、同一份数据）',
    !!head && r7.c === head, `读数「${r7.c}」页头「${r7.last}」`);

  // ⑧⑨⑩ 都要**拿读数块自己那块地方**来量。块不在页面上（＝改之前）时，这三格**报红**，
  //   不是让工装炸掉：炸掉看着也"没通过"，但它不说哪一格没通过，也分不出是页面坏了还是工装坏了。
  if (!r1.exists) {
    t('⑧ 指针离开图 ⇒ 读数收掉，而且像素上真没了', false, '页面上没有读数块 ⇒ 这一格摆不出来');
    t('⑨ 不挡图：读数块正中心的 elementFromPoint 落在画布上', false, '页面上没有读数块 ⇒ 这一格摆不出来');
    t('⑩ 不吃拖拽：从读数块正中心按下往左拖 ⇒ 视口真的动了', false, '页面上没有读数块 ⇒ 这一格摆不出来');
  } else {
    await p.mouse.move(midX, botY);
    await sleep(250);
    const rb = await p.evaluate(() => { const q = document.getElementById('readout').getBoundingClientRect();
      return { x: Math.round(q.x), y: Math.round(q.y), width: Math.round(q.width), height: Math.round(q.height) }; });
    const shotOn = await p.screenshot({ clip: rb });
    await p.evaluate(() => document.getElementById('readout').classList.remove('on'));   // 只摘类：十字线一动不动
    await sleep(250);
    const shotOff = await p.screenshot({ clip: rb });
    await p.evaluate(() => document.getElementById('readout').classList.add('on'));       // 摆回去，别影响后面
    await p.mouse.move(Math.round(box.x + box.width - 2), Math.round(box.y - 24));       // 指针移出图
    await sleep(400);
    const r8 = await shown(p);
    t('⑧ 指针离开图 ⇒ 读数收掉；而且**像素上真没了**（同一块区域摘掉 .on 前后不一样）',
      !shotOn.equals(shotOff) && !r8.on && r8.vis === 'hidden',
      `同一块区域${shotOn.equals(shotOff) ? '**一模一样**（读数根本没画出来）' : '变了'}；移出后 on=${r8.on} vis=${r8.vis}`);

    await p.mouse.move(midX, botY);
    await sleep(250);
    const r9 = await shown(p);
    const cx9 = Math.round(r9.bx + r9.bw / 2), cy9 = Math.round(r9.by + r9.bh / 2);
    const hit = await p.evaluate(([x, y]) => { const e = document.elementFromPoint(x, y);
      return e ? e.tagName + (e.className ? '.' + e.className : '') : 'null'; }, [cx9, cy9]);
    t('⑨ 不挡图：读数块正中心的 elementFromPoint 落在画布上（不是它自己）', /^CANVAS/.test(hit), `命中 ${hit}`);

    const v0 = await p.evaluate(() => window.__app.chart.timeScale().getVisibleLogicalRange().from);
    await p.mouse.move(cx9, cy9);
    await p.mouse.down();
    for (let i = 1; i <= 6; i++) { await p.mouse.move(cx9 - i * 20, cy9); await sleep(30); }
    await p.mouse.up();
    await sleep(250);
    const v1 = await p.evaluate(() => window.__app.chart.timeScale().getVisibleLogicalRange().from);
    t('⑩ 不吃拖拽：从读数块正中心按下往左拖 ⇒ 视口真的动了', Math.abs(v1 - v0) > 1, `from ${v0.toFixed(2)} → ${v1.toFixed(2)}`);
  }
  await p.screenshot({ path: path.join(OUT, 'desktop.png'), clip: { x: box.x, y: box.y, width: 620, height: 180 } });
  await p.close();

  // ⑥ 最左边那一根没有前收 ⇒ 印「—」（单独一页：得让第 0 根真在屏上）
  const p6 = await open(ctx, '?symbol=ZECUSDT&tf=1h&at=0&span=120');
  const box6 = await boxOf(p6);
  const y6 = Math.round(box6.y + box6.height * 0.5);
  const x0 = await p6.evaluate(() => { const { chart, state } = window.__app;
    return chart.timeScale().timeToCoordinate(state.data.bars[0].t / 1000); });
  if (x0 == null) t('⑥ 最左边那一根没有前收 ⇒ 印「—」', false, '第 0 根不在屏上 ⇒ 这一格摆不出来（空转）');
  else {
    await p6.mouse.move(Math.round(box6.x + x0), y6);
    await sleep(250);
    const r6 = await shown(p6);
    const u6 = await barUnder(p6, Math.round(box6.x + x0), box6);
    t('⑥ 最左边那一根没有前收 ⇒ 印「—」（不编一个 0.00% 给它）',
      r6.on && u6.i === 0 && r6.pct === '—', `指针下第 ${u6.i} 根，涨跌幅读到「${r6.pct}」`);
  }
  await p6.close();

  // ⑪ 跟「换档重算」那句话不许叠（那句真出来了才判）
  scen({ tick: 0.1, bend: true });
  const p2 = await open(ctx, '?symbol=ZECUSDT&tf=1h&at=40&span=180');   // 贴着左沿：拖一下就该去要下一档
  const box2 = await boxOf(p2);
  const y2 = Math.round(box2.y + box2.height * 0.5);
  const x2 = Math.round(box2.x + box2.width * 0.55);
  await p2.mouse.move(x2, y2);
  await sleep(200);
  const vv0 = await p2.evaluate(() => window.__app.chart.timeScale().getVisibleLogicalRange().from);
  await p2.mouse.down();
  for (let i = 1; i <= 4; i++) { await p2.mouse.move(x2 - i * 6, y2); await sleep(40); }
  await p2.mouse.up();
  let noticeOn = false;
  for (let i = 0; i < 40 && !noticeOn; i++) { await sleep(150); noticeOn = await p2.evaluate(() => document.getElementById('notice').classList.contains('on')); }
  const vv1 = await p2.evaluate(() => window.__app.chart.timeScale().getVisibleLogicalRange().from);
  await p2.mouse.move(Math.round(box2.x + box2.width * 0.5), y2 + 20);   // 挪一下，把读数叫回来
  await sleep(300);
  const [rn, rr] = await p2.evaluate(() => {
    const g = (id) => { const e = document.getElementById(id);
      if (!e) return { exists: false, on: false, y: 0, h: 0 };
      const q = e.getBoundingClientRect();
      return { exists: true, on: e.classList.contains('on'), y: q.y, h: q.height }; };
    return [g('notice'), g('readout')];
  });
  const apart = rn.on && rr.on && (rn.y + rn.h <= rr.y + 0.5 || rr.y + rr.h <= rn.y + 0.5);
  t('⑪ 读数块跟「换档重算」那句话不许叠（两块同时在时盒子不相交）',
    apart, `那句 on=${rn.on}（没出来这一格就是空转）／读数 on=${rr.on}；那句底 ${(rn.y + rn.h).toFixed(1)}、读数顶 ${rr.y.toFixed(1)}；拖了 from ${vv0.toFixed(1)}→${vv1.toFixed(1)}`);
  await p2.screenshot({ path: path.join(OUT, 'desktop-overlap.png'), clip: { x: box2.x, y: box2.y, width: 700, height: 200 } });
  await p2.close();
  await ctx.close();

  // ================================================================ 手机
  scen({ tick: 0.01 });
  const mctx = await newCtx({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  const mp = await open(mctx, '?symbol=ZECUSDT&tf=1h&last=300');
  const mbox = await boxOf(mp);
  const cdp = await mctx.newCDPSession(mp);
  const T = (type, pts) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: pts });
  const tx = Math.round(mbox.x + mbox.width * 0.5), ty = Math.round(mbox.y + mbox.height * 0.5);

  // ⑫ 长按 ⇒ 出读数，读的是手指底下那一根
  await T('touchStart', [{ x: tx, y: ty }]);
  await sleep(900);                                    // 长按门槛（实测 ~500ms 才出十字线）
  const rm = await shown(mp);
  const um = await barUnder(mp, tx, mbox);
  const halfM = Math.pow(10, -decimals(um.tick)) / 2 + 1e-9;
  const nearM = (txt, v) => Math.abs(Number(String(txt).replace(/,/g, '')) - v) <= halfM;
  t('⑫ 手机长按 ⇒ 出读数，读的是手指底下那一根',
    rm.on && !!um.bar && nearM(rm.o, um.bar.o) && nearM(rm.c, um.bar.c),
    `手指下第 ${um.i} 根 ${um.bar ? [um.bar.o, um.bar.h, um.bar.l, um.bar.c].join('/') : '?'} ⇒ 读到 o=${rm.o} c=${rm.c}`);

  // ⑬ 长按后横拖 ⇒ 读数跟着换、视口一动没动
  const mv0 = await mp.evaluate(() => window.__app.chart.timeScale().getVisibleLogicalRange().from);
  for (let i = 1; i <= 6; i++) { await T('touchMove', [{ x: tx + i * 14, y: ty }]); await sleep(60); }
  const rm2 = await shown(mp);
  const mv1 = await mp.evaluate(() => window.__app.chart.timeScale().getVisibleLogicalRange().from);
  const um2 = await barUnder(mp, tx + 84, mbox);
  t('⑬ 手机长按后横拖 ⇒ 读数跟着换、视口一动没动（读数在走，不是图在滚）',
    rm2.on && rm2.c !== rm.c && Math.abs(mv1 - mv0) < 0.001 && um2.i !== um.i,
    `收 ${rm.c} → ${rm2.c}（第 ${um.i} 根 → 第 ${um2.i} 根）；视口 from ${mv0.toFixed(3)} → ${mv1.toFixed(3)}`);
  await T('touchEnd', []);
  await sleep(300);

  // ⑭ 手机的手势出口。四小节，缺一节这条就红：
  //   a) 新起一页的**第一下**快滑 ⇒ 拖图（读数不显示）—— 先证明这页上"拖＝拖图"是底态
  //   b) 长按 ⇒ 读到；**抬手后读数还在**（手指挪开了还能读那个数 —— 长按读数一半的好处就在这）
  //   c) 这一下之后的横滑 ⇒ **视口不动、读数还在**（库把它当成继续拖十字线）
  //   d) **轻点一下** ⇒ 读数收掉；再快滑 ⇒ 视口动、读数收掉（点一下就是库给的出口）
  //
  // ★★ 这一格**换一页新起**，故意不接 ⑫⑬ 的尾巴：lightweight-charts 5.2.1 的触摸状态机**有记忆** ——
  //   实测（探针跑法记在 notes/ 里）：⑬ 那种「长按＋横拖」之后再长按、抬手，读数会被收掉（b 那半节就红）；
  //   而同一段逻辑在新起的一页上跑四遍，逐字一样。**测库的状态机不能带着上一段的记忆去测**。
  // ★ (c) 量的不是"我们的功能"，是**库的手势模型**（长按过一次之后，下一次触摸拖拽仍归十字线，直到轻点一下）。
  //   哪天它变红，先读这段：多半是库换了模型，手机上那套说法（长按读、点一下放）要跟着重写 ——
  //   不是我们的浮层吃了手势（⑨⑩ 量了浮层那一半）。
  //   顺手试过 `chart.clearCrosshairPosition()`：**没用**，粘的是触摸状态机、不是那根线，页面这边没有小修的办法。
  // ★ 顺带记一笔实测的边界（**不在这条里断言**，免得把库的状态机当成我们的验收点）：
  //   「轻点 → 快滑(平移) → 长按」这一串，长按会被吞掉一次（读到空），但**正常人的节奏**
  //   「长按读 → 轻点点掉 → 长按读」连着四轮都稳（见过 4/4）。真机上要是别扭，那是另一个卡的事。
  await mp.reload({ waitUntil: 'domcontentloaded' });
  await mp.waitForFunction(() => window.__app && window.__app.state.data, null, { timeout: 30000 });
  await sleep(800);
  const mbox2 = await boxOf(mp);
  const tx2 = Math.round(mbox2.x + mbox2.width * 0.5), ty2 = Math.round(mbox2.y + mbox2.height * 0.5);
  const vFrom = () => mp.evaluate(() => window.__app.chart.timeScale().getVisibleLogicalRange().from);
  const swipe = async () => {
    const f0 = await vFrom();
    await T('touchStart', [{ x: tx2, y: ty2 }]);
    for (let i = 1; i <= 6; i++) { await T('touchMove', [{ x: tx2 - i * 16, y: ty2 }]); await sleep(28); }
    await T('touchEnd', []);
    await sleep(450);
    return { f0, f1: await vFrom() };
  };
  const a = await swipe();  const ra = await shown(mp);                 // a) 新页第一下：快滑 = 拖图
  await T('touchStart', [{ x: tx2, y: ty2 }]);                          // b) 长按 → 抬手
  await sleep(900);
  const rHold = await shown(mp);
  await T('touchEnd', []);
  await sleep(450);
  const rLift = await shown(mp);
  const c = await swipe();  const rc = await shown(mp);                 // c) 抬手后横滑：归十字线
  await T('touchStart', [{ x: tx2, y: ty2 }]);                          // d) 轻点一下，再快滑
  await sleep(55);
  await T('touchEnd', []);
  await sleep(350);
  const rTap = await shown(mp);
  const d = await swipe();  const rd = await shown(mp);
  t('⑭ 手机：第一下快滑拖图；长按抬手后读数还在；抬手后横滑归十字线（视口不动）；点一下再滑 ⇒ 视口动、读数收掉',
    a.f1 - a.f0 > 0.5 && !ra.on
      && rHold.on && rLift.on
      && Math.abs(c.f1 - c.f0) < 0.001 && rc.on
      && !rTap.on && d.f1 - d.f0 > 0.5 && !rd.on,
    `a 快滑 ${a.f0.toFixed(3)}→${a.f1.toFixed(3)} 读数 on=${ra.on}`
      + `｜b 长按中 on=${rHold.on} 抬手后 on=${rLift.on}`
      + `｜c 横滑 ${c.f0.toFixed(3)}→${c.f1.toFixed(3)} 读数 on=${rc.on}`
      + `｜d 点一下后 on=${rTap.on}，再滑 ${d.f0.toFixed(3)}→${d.f1.toFixed(3)} 读数 on=${rd.on}`);
  await mp.screenshot({ path: path.join(OUT, 'mobile.png') });
  await mp.close();
  await mctx.close();

  await b.close();
  console.log(`\n${ok.length}/${ok.length + bad.length} 绿`
    + (errors.length ? `　★ 页面报错 ${errors.length} 条：\n   ` + errors.slice(0, 5).join('\n   ') : ''));
  if (bad.length) { console.log('红的：'); for (const x of bad) console.log('  ✗ ' + x); }
  console.log('截图 →', OUT);
  process.exit(bad.length || errors.length ? 1 : 0);
})().catch((e) => { console.error('工装自己炸了：', e); process.exit(3); });
