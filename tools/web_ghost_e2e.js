// 「确认过、后来又没了的买卖点」那套记账的浏览器工装（card-cf3ed018-795，小栋 10-05 ②A）
//
// ★ 这一套**必须配假后台**：真后台每次请求都是整段重算、不留历史，「让一个点消失」这件事
//   在现场造不出来 —— 而它恰恰是这一卡唯一要量的东西。（跟 web_measure_e2e.js 正好相反：
//   那一格量的是「后台真按那个看法重算了没有」，所以那边必须真后台。）
//   假后台的做法：**先从真后台取一份真数据**（20160 根 ZEC 15m），此后所有 /api/chart 都由它改出来 ——
//   只删/加 signals 里的条目，bars/pens/segs/centers 一个字节不动。这样：
//     · 除了被点名的那个点，屏幕上别的地方**逐像素一样**（下面的对照格就靠这一条）；
//     · 窗口起点不动 ⇒ 左沿守卫那一格量的是守卫本身，不是窗口滑动（那是另一回事，见下面 ⑦）。
//
// 量的是接线和画法，不是算法：
//   ① 同一桶里少了一个已确认的点 ⇒ 记下来、画出来、图脚报数（少了几个就报几个）
//   ② **那个记号画在哪**：拿 (时间, 价格) 自己在图上算出坐标（走 chart 的 timeToCoordinate /
//      priceToCoordinate），那一小块里必须真的出现这个记号 —— 位置对，不是"某处冒了一个"。
//      ★ 判据是 **alpha ＋ 色相**：`getImageData` 读回来的是**合成之前**的像素，画布是透明的，
//        幽灵那档和实心那档**色相一模一样**（同一个 base 色），只有 alpha 不同（180 / 255）。
//        只比色相 ⇒ 两种都算"实心"，这一格假绿。
//   ③ **画的是不是"作废"那个形状**：同一小块，实心那份**墨掉了**（alpha≥250 的像素掉够一颗三角）。
//      ★ 这两格是**像素**、量的是那个元素本身 —— 不是读 state、不是读 ghosts 数组长度。
//   ④b2 那一格里带着记号**本尊的小样**（图例里没有这一格 —— 形状得在它出现的地方认）
//   ④c 那一格是**浮层**：它出现的时候图的尺寸一个像素都不许动（并进图脚就会把图挤矮 —— 量过）
//   ④ 悬停在那颗记号上 ⇒ 说明弹出来，且写的是卡上那句「这个点 … 出现过、后来消失了」
//   ⑤ **对照格**：同一屏里另一个没被动的点，前后两次读数一样（证明变的是那一个点，不是整屏重绘）
//   ⑥ **换看法不造鬼**：切到「黄白线」，那边少着的两个点**一个都不许**报成消失 ——
//      桶是 (品种, 周期, 看法, 档位)，少一样，切看法就成了「旧尺子的点全没了」，屏幕上当场一片空心三角
//   ⑦ **左沿守卫**：删掉一个 bar 100 的已确认点（离窗口起点不到 200 根）⇒ **不许**报成消失。
//      窗口是定长的、起点会自己往后滑，那一段本来就会重算（量法见 app.js 里 GHOST_SLIDE_MUL 那段账）。
//      ⑦ 的牙齿来自 ①：同一个跑法里 bar 4004 的点**报得出来** ⇒ ⑦ 绿不是因为"这套记账根本不起作用"
//   ⑧ **同一个点又回来了** ⇒ 记号收掉（它现在就在图上，两个记号并列就是自相矛盾）
//   ⑨ **正常刷不误报**：同一份 payload 再要一遍（这就是"刷新"），一个鬼都不许有，屏幕逐像素不变
//   ⑩ **重开页面就清零**：出了鬼之后真 reload ⇒ 账本没了、图脚那一格也没了（"只记有人看着时发生的"）
//   ⑪ **档位进桶**：往左加载一档（真鼠标拖到左沿），那一档里少掉的点**不许**报（Bram 第 ① 条）
//   ⑫ **待确认 vs 已确认→待确认**：待确认的点没了不报；已确认变回待确认**要报**（Bram 第 ② 条）
//   ⑬ **收盘自动重取**（Nova 10-05 定）：没人碰页面，收盘后空心点**自己**出现；切到后台不发请求、
//      切回来立刻补一次；一分钟内最多一次
//   ⑮ **换引擎也不算重绘**（`engine` 进桶键）：core/*.py 一改、一部署，开着的页面拿到的就是点集不同的
//      一份 —— 不许把新旧两份比成满屏「消失」。两张工装页**只差 engine 一个字段**，一张该报、一张报 0。
//   ⑭ **后台挂了那一趟不许当刷新**：收盘时取不到真数据 ⇒ load() 会悄悄退回仓里的样本，
//      而样本是**另一份数据** —— 画上去账本当场把整屏读成"全没了"（满屏假空心点），顺带把档位也洗了
//   ★ 假后台**按请求里的 `measure` 路由**（不是按页面变体）—— 见 plan() 那段账：⑥ 原来是个空转格。
//
// 跑法：
//   1) 真后台（只用来取那份真数据 ＋ /api/meta），**只绑回环**（部署纪律：不许绑全网卡）：
//        python3 web/server.py --port 8796
//   2) node tools/web_ghost_e2e.js [输出目录] [页面地址]
//        （playwright 的 node_modules 不在仓里，用 NODE_PATH 指过来）
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

const OUT = process.argv[2] || path.join(os.tmpdir(), 'ghost-e2e');
const PAGE = (process.argv[3] || 'http://127.0.0.1:8796/').replace(/\/?$/, '/');
const QS = '?symbol=ZECUSDT&tf=15m';
const EDGE_BAR = 100;          // 注入的那个"离左沿很近"的已确认点（真数据里 bar<200 处没有点）
const TARGET_BAR = 4004;       // 拿它当"消失"的那个点（线段中枢层、实心，好量）
let bad = 0, n = 0;
const ck = (name, ok, extra) => {
  n++;
  if (!ok) bad++;
  console.log(`  ${ok ? '✓' : '✗'} ${n}. ${name}${extra ? '　' + extra : ''}`);
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const hex2rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
// rgba(色, a) 压在底色上之后**真正画出来的那个像素值** —— 判据那边就是拿它认的（跟 layers.js 的 rgba 同一条式子）
const over = (fg, a, bg) => fg.map((v, i) => Math.round((a / 255) * v + (1 - a / 255) * bg[i]));

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  // 真后台只在这一处被用到：取一份真数据当模子。
  const base = await (await fetch(`${PAGE}api/chart?symbol=ZECUSDT&tf=15m`)).json();
  if (!base.signals || !base.signals.seg) { console.error('✗ 真后台没回 signals —— 先确认后台起在 ' + PAGE); process.exit(2); }

  // ★ 兜底那一条**必须**离左沿够远：模子是**真后台**给的，窗口会滑、点位会挪（实测两次跑差过 1600 根），
  //   万一兜底挑到 bar<1000 的点，左沿守卫（200 根）会把它按住 ⇒ ④ 那一格变成假红，
  //   而真正的原因在工装自己挑错了点。这是**工装的**问题，不该让守卫背。
  const target = (base.signals.seg || []).find((s) => s.confirmed === true && s.bar === TARGET_BAR)
              || (base.signals.seg || []).find((s) => s.confirmed === true && s.bar >= 1000);
  const control = (base.signals.pen || []).find((s) => s.confirmed === true && Math.abs(s.bar - target.bar) < 200)
               || (base.signals.pen || []).find((s) => s.confirmed === true);
  if (!target || !control) { console.error('✗ 模子里找不到已确认的点，这一套没法量'); process.exit(2); }
  console.log(`模子：${base.symbol} ${base.tf} ${base.bars.length} 根 ｜ 目标点 ${target.kind}@${target.bar}(${target.price})`
            + ` ｜ 对照点 ${control.kind}@${control.bar}(${control.price})`);

  // ⑫ 用的那个**待确认**的点：真数据里那一段不一定有待确认的点，自己造一个（真后台也会吐这种点）。
  const PEND_BAR = 3200;
  const PEND_PT = { kind: '三买', bar: PEND_BAR, price: base.bars[PEND_BAR].l, confirmed: false,
                    weak: false, level: 'pen', center: 1, unit: 3, _pend: true };

  const clone = (x) => JSON.parse(JSON.stringify(x));
  /** 模子 → 这一趟要吐的 payload。drop 里是 "tier|kind|bar"；EDGE 那个点每次都注入（它量守卫）。
   *  `shift`＝整份数据的**时间平移**（ms，见 open() 那段账）。
   *  `opt.pend`＝这一份带上那个待确认的点；`opt.unconfirm`＝把这个键的点改回 `confirmed:false`。 */
  const mk = (measure, drop = new Set(), shift, opt = {}, span) => {
    const d = clone(base);
    d.measure = measure;
    // ★ 档位必须**照着请求回显**（真后台就是这么回的）。不回显的话页面 `adopt()` 会以为还在第 1 档，
    //   桶的键里那个 span 就不是 2 —— ⑪ 那一格量到的会是「工装没把档位说出来」，而不是记账本身。
    if (Number.isFinite(span)) d.span = span;
    if (shift) for (const b of d.bars) b.t += shift;
    d.signals.pen.push({ kind: '三买', bar: EDGE_BAR, price: base.bars[EDGE_BAR].l, confirmed: true,
                         weak: false, level: 'pen', center: 1, unit: 3 });
    // ⑤ 三根情形：`grow` ＝ 这一份**真的把新那根带回来了**（末尾接一根）；
    //    `refreshing` ＝ 后台还在去币安拿（SWR），这份还是旧的 —— 真后台就是这么回的。
    if (opt.grow) {
      const last = d.bars[d.bars.length - 1];
      d.bars.push({ ...last, t: last.t + STEP_MS, o: last.c, h: last.c, l: last.c, c: last.c });
    }
    if (opt.refreshing) d.refreshing = true;
    if (opt.engine) d.engine = opt.engine;      // ⑮：引擎版本（后台带在 /api/chart 顶层那个字段）
    if (opt.pend) d.signals[PEND_PT.level].push(clone(PEND_PT));
    for (const tier of ['seg', 'pen']) {
      d.signals[tier] = (d.signals[tier] || []).filter((s) => !drop.has(`${tier}|${s.kind}|${s.bar}`));
    }
    // ⑫ 的第三趟：点**还在**，只是从「已确认」变回「待确认」—— 这也要算消失（Bram 第 ② 条）。
    if (opt.unconfirm) {
      for (const tier of ['seg', 'pen']) {
        for (const s of d.signals[tier] || []) if (`${tier}|${s.kind}|${s.bar}` === opt.unconfirm) s.confirmed = false;
      }
    }
    return d;
  };
  const K = (tier, s) => `${tier}|${s.kind}|${s.bar}`;
  const D_TARGET = new Set([K(target.level || 'seg', target)]);
  const D_EDGE = new Set([`pen|三买|${EDGE_BAR}`]);
  const D_LINES = new Set([K(target.level || 'seg', target), K(control.level || 'pen', control)]);
  const NOTHING = { drop: new Set() };
  // ⑮：两把假「尺」（形状跟真的一样：10 位 hex）。真值是 core/*.py 的 sha256 前 10 位，由后台算
  //   （Bram 的 agent/bram/engine-version）—— 工装这里只需要「两个不同的值」。
  const ENG1 = 'e1e1e1e1e1', ENG2 = 'e2e2e2e2e2';
  // ⑮ 少掉的那一片：真实换引擎会少一大片，这里用目标＋对照＋左沿那个。
  //   ★ 左沿那个（bar 100）本来就被左沿守卫吃掉（⑦ 量过）⇒ 这张页面上该报的是 D_LINES.size 个。
  const D_ROUND = new Set([...D_LINES, ...D_EDGE]);
  // 正片每一趟吐什么：序号从 1 起（每张页面自己数自己的请求数）。
  // ★ 第 2 趟**还是全给**：这不是为了看鬼，是先空转一圈把图的几何站稳（见正片里那段账）——
  //   两次像素读数都得在"已经落定"的状态下取，否则量到的是图自己挪了 1px。
  const SEQ = [new Set(), new Set(), new Set(), D_TARGET, new Set(), D_EDGE];
  // ★★ 路由必须**看请求里的 `measure`**，不能只看页面变体 —— Atlas 2026-10-05 拿变异量出来的：
  //    原先按页面分流，切到黄白线那一趟也拿到"全给"那份 ⇒ ⑥ 是个**空转格**（那行写的「少着 2 个点」
  //    只是 D_LINES.size 这个常量，根本没在页面上量过）。现在 `m==='lines'` 一律吐 D_LINES，
  //    并且 ⑥ 里先断言「黄白线那份 `state.data.signals` 真比面积那份少 2 个」再判有没有鬼。
  const plan = (which, i, m, sp) => {
    if (which !== 'same' && m === 'lines') return { drop: D_LINES };
    if (which === 'same') return NOTHING;                                  // ⑨：每一趟都吐一模一样的
    if (which === 'span') return sp >= 2 ? { drop: D_TARGET } : NOTHING;   // ⑪：换档后重叠区里少掉一个
    if (which === 'pend') {                                                // ⑫
      if (i === 1) return { opt: { pend: true } };                         //   第 1 趟：带一个待确认的点
      if (i === 2) return NOTHING;                                         //   第 2 趟：它没了 ⇒ **不许报**
      return { opt: { unconfirm: K(target.level || 'seg', target) } };     //   第 3 趟：已确认→待确认 ⇒ **要报**
    }
    // ⑬：第 2 趟（收盘后自动重取那一趟）少了目标点，而且**真的带回了新那根**
    if (which === 'auto') return i <= 1 ? NOTHING : { drop: D_TARGET, opt: { grow: true } };
    // ⑬g/⑬i：第 1 趟之后**每一趟都还是旧数据**（头里 refreshing、末尾不带新那根）——
    //   这就是"后台一直没把新那根拉回来"那种情形：页面该补（⑬g），但**不许无限补**（补到上限就停，
    //   然后 ③ 那道闸要拦住可见性来回切）(⑬i)。
    if (which === 'swr') return i === 1 ? NOTHING : { drop: D_TARGET, opt: { refreshing: true } };
    // ⑮：换引擎 ≈ 换了一把尺。下面两张页面**只差 engine 这一个字段**（同样少那一片点、同样把新那根带回来）
    //   —— 差别只有这一个 ⇒ 报不报只能归因于它。'engsame' 是**对照**：先证明这一套在这张页面上真报得出来，
    //   否则 'engine' 那张报 0 也可能只是"这一套根本没工作"（空转格）。
    if (which === 'engsame' || which === 'engine') {
      const eng = which === 'engine' && i >= 2 ? ENG2 : ENG1;
      return i <= 1 ? { opt: { engine: eng } } : { drop: D_ROUND, opt: { engine: eng, grow: true } };
    }
    return { drop: i < SEQ.length ? SEQ[i] : new Set() };
  };

  const b = await chromium.launch();
  const STEP_MS = 15 * 60 * 1000;               // 这一套只用 15m
  const NOW0 = Date.now();
  const open = async (which, qs = QS) => {
    const c = await b.newContext({ viewport: { width: 1440, height: 900 } });
    const p = await c.newPage();
    const hits = {};
    p.on('console', (m) => { if (m.type() === 'error') console.log('    [page error] ' + m.text()); });
    p.on('pageerror', (e) => console.log('    [page error] ' + e.message));
    // ★ 整份数据的**时间平移**（见文件头 ⑬ 那条）：自动重取是按「最后一根 + 一个周期」排的，
    //   真数据最后一根多半是**正在走**的那一根 —— 它的收盘时刻离跑完这套工装可能只有几秒，
    //   那几格里会凭空多出一次取数，把 SEQ 的顺序打乱（假红）。所以：
    //     · 正片那几张：挪成「刚刚开盘」⇒ 下一个收盘在整整一个周期之后，跑不死它们；
    //     · 'auto' 那张：挪成「还差 5 秒收盘」⇒ 自动重取**自己**会发生（这正是 ⑬ 要量的）。
    // ★ 基准时刻要**按这一页打开的这一刻**算，不能用模块加载那一刻：这一套跑两分钟，用全局的
    //   NOW0 的话，后开的页面一上来"收盘"就已经是几十秒前的事了 —— 那 ⑬b 会**假绿**
    //   （定的定时器早就过点了，跟"切到后台不发请求"这道闸没关系）。
    const NOWP = Date.now();
    const lastT = base.bars[base.bars.length - 1].t;
    const soon = which === 'auto' || which === 'swr' || which === 'fallback'
               || which === 'engsame' || which === 'engine';
    const shift = (soon ? NOWP - STEP_MS + 3000 : NOWP) - lastT;      // soon：还差 3 秒收盘
    const reqAt = [];                                                 // 每次取数的时刻（⑬ 量错峰用）
    await p.route('**/api/chart*', async (route) => {
      const u = new URL(route.request().url());
      const m = u.searchParams.get('measure') || 'macd';
      const sp = Number(u.searchParams.get('span') || 1);
      hits[m] = (hits[m] || 0) + 1;
      reqAt.push(Date.now());
      // ⑭：收盘那一趟后台**挂了**（abort，不是"回旧数据"）⇒ load() 会退回仓里的样本。
      //    这条路的危险在于：样本是**另一份数据**，画上去账本会当场把整屏读成"全没了"。
      if (which === 'fallback' && hits[m] >= 2) { await route.abort(); return; }
      const { drop, opt } = plan(which, hits[m], m, sp);
      const body = mk(m, drop, shift, opt, sp);
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    });
    await p.goto(PAGE + qs, { waitUntil: 'domcontentloaded' });
    await p.waitForFunction(() => window.__app && window.__app.state && window.__app.state.data, null, { timeout: 60000 });
    await sleep(1200);                     // 等 /api/meta 那一趟（控件由它驱动）
    return { c, p, hits, reqAt, closeAt: NOWP + 3000 };
  };

  /** 切看法并等它落地（等的是**页面上那份数据**的 measure，不是请求 —— 请求回来之前那次不算数）。
   *  ★ **先把视图摆好，再点那颗 chip**：价格轴的宽度是在**取数那一下**按当时可见的价格区间算的，
   *    摆完再取数这个顺序，几何才由我们说了算。反过来（先取数、再摆视图）量到的是个薛定谔的数：
   *    1440 实测，同一段 K 线、同一个逻辑区间，价格轴会在 68px / 62px 之间换，plot 1182 ↔ 1188，
   *    同一个买卖点在屏幕上差 0.93px —— ⑤ 那一格会把它读成"整屏重绘"。 */
  const measure = async (p, id, bar) => {
    if (bar != null) await park(p, bar);
    await p.locator(`.mchip[data-measure="${id}"]`).click();
    await p.waitForFunction((m) => window.__app.state.data && window.__app.state.data.measure === m, id, { timeout: 30000 });
    await sleep(1000);
    return snap(p);
  };

  // 页面上那份数据的要点 ＋ 那一格浮层
  const snap = (p) => p.evaluate(() => {
    const d = window.__app.state.data;
    const g = document.getElementById('ghostc');
    const t = document.getElementById('ghostc-tx');
    const all = ['seg', 'pen'].flatMap((tier) => ((d.signals || {})[tier] || []).map((s) => ({ ...s, tier })));
    return { ghosts: (d.ghosts || []).map((x) => ({ kind: x.kind, tier: x.tier, bar: x.bar, price: x.price, t: x.t })),
             // ⑥ 要用它证明「黄白线那份**真的**少着点」；⑫ 要用它证明「那个待确认的点真的没了」
             nSig: all.length,
             pends: all.filter((s) => s.confirmed !== true).map((s) => `${s.tier}|${s.kind}|${s.bar}`),
             meta: (document.getElementById('meta') || {}).textContent || '',
             // 只读那一格里的**文字**（壳里还有记号小样那个 svg；连壳一起读会把缩进也算进来）
             gc: g ? { txt: (t || {}).textContent || '', on: g.classList.contains('on'),
                       svg: !!g.querySelector('svg') } : null,
             measure: d.measure, span: d.span,
             src: d.source, nBars: (d.bars || []).length, eng: d.engine,
             tip: (document.getElementById('ghosttip') || {}).textContent || '' };
  });
  const tipState = (p) => p.evaluate(() => {
    const t = document.getElementById('ghosttip');
    return t ? { on: t.classList.contains('on'), txt: t.textContent } : null;
  });
  const shotChart = async (p, tag) => {
    const box = await p.locator('#chart').boundingBox();
    fs.writeFileSync(path.join(OUT, `fig-${tag}.png`), await p.screenshot({ clip: box }));
  };
  // 一个点的记号在**屏幕上**占的那一小块（页面坐标）。几何只有一处出处：跟 layers.js 那两个函数同一套式子。
  const boxAt = async (p, pt) => {
    const box = await p.locator('#chart').boundingBox();
    return p.evaluate(([pt, box]) => {
      const ch = window.__app.chart, ts = ch.timeScale(), s0 = ch.panes()[0].getSeries()[0];
      const x = ts.logicalToCoordinate(pt.bar), y = s0.priceToCoordinate(pt.price);
      if (x === null || y === null) return null;
      const sz = (pt.tier === 'seg' ? 15 : 9) * 0.55;          // SIG.segSize / SIG.penSize × 0.55
      const d = String(pt.kind).endsWith('买') ? 1 : -1;
      const tip = y + d * 3.6, y0 = y + d * (3.6 + 2 * sz);    // SIG.tip(6) × 0.6
      const top = Math.min(tip, y0), bot = Math.max(tip, y0);
      return { buy: String(pt.kind).endsWith('买'), bar: pt.bar, kind: pt.kind, tier: pt.tier, price: pt.price,
               x: Math.round(box.x + x - sz - 3), y: Math.round(box.y + top - 1),
               w: Math.round(2 * sz + 6), h: Math.round(bot - top + 2) };
    }, [pt, box]);
  };
  /** 数那一小块里的像素。判据是 **alpha ＋ 色相**，不是色相一个数：
   *  `rgba(底色色相, ghostAlpha)` 压出来是什么样，是**浏览器合成之后**的样子；而 `getImageData`
   *  读回的是**合成之前**的 (色相, alpha) —— 画布是透明的，底下的 K 线在另一层画布上。
   *  只按色相比的话，实心和幽灵**色相一模一样**（同一个 base）⇒ 两个都算实心，那一格就假绿了。
   *  所以：实心 = 色相对 ＋ alpha ≥ 250；幽灵 = 色相对 ＋ alpha ≈ ghostAlpha。
   *  `ink` = 这一层真的落了墨的像素数（只当诊断看：K 线那层永远是墨，它不算判据）。 */
  const readBoxes = (p, bs, cols) => p.evaluate(([bs, cols]) => {
    const near = (a, b, t) => Math.abs(a - b) <= t;
    const cvs = [...document.querySelectorAll('#chart canvas')].map((c) => ({ c, r: c.getBoundingClientRect() }));
    return bs.map((bx) => {
      if (!bx) return { miss: '这一块没算出来（点不在可视区里）' };
      const hit = cvs.filter(({ r }) => bx.x >= r.left && bx.y >= r.top && bx.x + bx.w <= r.right && bx.y + bx.h <= r.bottom);
      if (!hit.length) return { miss: '那一块没落在任何一张画布上' };
      const pure = bx.buy ? cols.buy : cols.sell;
      let full = 0, ghost = 0, ink = 0;
      for (const { c, r } of hit) {
        const px = c.getContext('2d').getImageData(Math.round(bx.x - r.left), Math.round(bx.y - r.top), bx.w, bx.h).data;
        for (let i = 0; i < px.length; i += 4) {
          const a = px[i + 3];
          if (a < 24) continue;                                  // 这一层在这个像素上什么都没画
          ink++;
          if (!near(px[i], pure[0], 10) || !near(px[i + 1], pure[1], 10) || !near(px[i + 2], pure[2], 10)) continue;
          if (a >= 250) full++;
          else if (Math.abs(a - cols.ghostAlpha) <= 14) ghost++;
        }
      }
      return { full, ghost, ink };
    });
  }, [bs, cols]);

  // 视图**每次都重新摆一遍再量**：切一次看法，可见区可能差一格（anchored 还原不是逐位精确的），
  // 上一次量好的框就压在记号边上了 —— 读数随之变，看着像"整屏重绘"，其实是工装自己没站稳。
  // 摆回同一个位置，框才有可比性（⑤ 对照格、⑨b 逐像素那两格全靠这个）。
  const park = async (p, bar) => {
    await p.evaluate((i) => window.__app.chart.timeScale().setVisibleLogicalRange({ from: i - 150, to: i + 150 }), bar);
    await sleep(700);
  };
  /** 往右拖 ＝ 把更早的 K 线拖出来。★ **必须用真鼠标**：页面只认「用户真动过输入设备」
   *  （userDrove()），脚本摆视口一律不算 —— 这一条跟 tools/web_more_e2e.js 那段账同一个理由：
   *  工装得跟用户走同一条路，不然量的是「页面会不会响应脚本」。 */
  const dragLeft = async (p, px) => {
    const box = await p.locator('#chart').boundingBox();
    const cy = box.y + box.height / 2;
    await p.mouse.move(box.x + 40, cy);
    await p.mouse.down();
    const steps = Math.max(2, Math.round(px / 20));
    for (let i = 1; i <= steps; i++) await p.mouse.move(box.x + 40 + (px * i) / steps, cy, { steps: 2 });
    await p.mouse.up();
    await sleep(120);
  };
  /** 把标签页切成「看得见／看不见」（⑬ 量的是这条口径）。改的是 `document.visibilityState` 这个
   *  只读属性 ＋ 补一次真事件 —— 走的是页面**真的**那个 visibilitychange 回调，不是替身。 */
  const setVisible = (p, st) => p.evaluate((s) => {
    Object.defineProperty(document, 'visibilityState', { get: () => s, configurable: true });
    Object.defineProperty(document, 'hidden', { get: () => s !== 'visible', configurable: true });
    document.dispatchEvent(new Event('visibilitychange'));
  }, st);
  const viewOf = (p) => p.evaluate(() => {
    const r = window.__app.chart.timeScale().getVisibleLogicalRange();
    const c = document.getElementById('chart').getBoundingClientRect();
    const f = document.querySelector('footer').getBoundingClientRect();
    return { view: r ? [+r.from.toFixed(1), +r.to.toFixed(1)] : null,
             chart: [Math.round(c.width), Math.round(c.height)],
             foot: Math.round(f.height) };
  });
  /** 现量几何 → 读像素。视图由 measure() 在**取数之前**摆好（见那段账），这里不再动它 ——
   *  每次读数都按当前这份几何现量框：判的是"记号在不在算出来的那个地方"，不是"两次的框一样不一样"。 */
  const sample = async (p, pts, tag) => {
    const boxes = [];
    for (const pt of pts) boxes.push(await boxAt(p, pt));
    const view = await viewOf(p);
    if (tag) await shotChart(p, tag);
    return { boxes, view, read: await readBoxes(p, boxes, cols) };
  };

  // 色和几何从**页面自己的 theme.js** 里读（不在工装里另抄一份色值 —— 抄了就是第二处出处）。
  // 这张页面（'same' 脚本，每一趟都吐一模一样那份）底下 ⑨ 还要接着用。
  const probe = await open('same');
  const THEME = await probe.p.evaluate(async () => {
    const t = await import('/theme.js');
    return { buy: t.CHART.buy, sell: t.CHART.sell, bg: t.PAGE.bg, ghostAlpha: t.SIG.ghostAlpha,
             seg: t.SIG.segSize, pen: t.SIG.penSize, tip: t.SIG.tip };
  });
  const cols = { buy: hex2rgb(THEME.buy), sell: hex2rgb(THEME.sell), bg: hex2rgb(THEME.bg), ghostAlpha: THEME.ghostAlpha };
  cols.buyGhost = over(cols.buy, THEME.ghostAlpha, cols.bg);
  cols.sellGhost = over(cols.sell, THEME.ghostAlpha, cols.bg);
  console.log(`色：买 ${THEME.buy} ／ 卖 ${THEME.sell} ／ 底 ${THEME.bg} ｜ ghostAlpha=${THEME.ghostAlpha}`
            + `（判据认的是 alpha，不是这个合成值）`);

  // ================================================================ 正片：造一次「点消失」
  console.log('\n1–10 造一次「确认过的点消失了」（假后台：第 1 趟全给、第 2 趟抽掉一个）');
  const A = await open('vanish');
  const p = A.p;
  // 打开买卖点那一层（默认关着 —— 关着的时候 layers.js 一个记号都不画，那几格会假红）
  await p.locator('.chip[data-key="sig"]').click();
  await sleep(900);
  const s0 = await snap(p);
  ck('① 开页第一趟：一个消失的点都没有（账本刚上，只有一份数据）',
     s0.ghosts.length === 0 && s0.gc.txt === '' && !s0.gc.on,
     `那一格：「${s0.gc.txt}」（on=${s0.gc.on}）`);

  // ⑥ 切到「黄白线」：那边少着两个点 —— 一个都不许报（桶里有 measure）
  await measure(p, 'lines');
  const sL = await snap(p);
  // ★★ 先证明**场景真的发生了**，再判有没有鬼。原先假后台按页面变体分流（不按 measure），
  //    切黄白线那一趟拿到的还是"全给"那份 ⇒ 这一格从来没量到过东西（Atlas 2026-10-05 的变异：
  //    「桶里去掉看法」全绿）。那一行原来写的「少着 2 个」只是 D_LINES.size 这个常量。
  ck('⑥a 黄白线那份**真的**比面积那份少点（先证明场景发生了，否则 ⑥ 又是个空转格）',
     s0.nSig - sL.nSig === D_LINES.size,
     `面积那份 ${s0.nSig} 个点、黄白线这份 ${sL.nSig} 个（差 ${s0.nSig - sL.nSig}，要等于 ${D_LINES.size}）`);
  ck('⑥b 换看法（面积→黄白线）⇒ 那边少着的两个点**一个都没报成消失**（桶里必须有「看法」）',
     sL.ghosts.length === 0 && sL.gc.txt === '' && !sL.gc.on,
     `黄白线那份 ${sL.nSig} 个点（面积 ${s0.nSig} 个）；页面报 ${sL.ghosts.length} 个`);

  // ★ 先空转一圈（第 2 趟**还是全给**）再读第一份数：不是为了看鬼，是让图的几何**站稳**。
  //   价格轴宽度是跟着可见价格区间算出来的 —— 刚从 fitContent（整段 20160 根）切到我摆的那个
  //   小窗口时，轴还没收窄（1440 实测：轴 68px → 62px，plot 1182 → 1188，同一个点在屏幕上挪 0.93px）。
  //   两次像素读数必须在同一种"已落定"的状态下取，否则量到的是**图自己挪了一格**，
  //   而 ⑤ 那一格会把它误读成"整屏重绘"。
  //   ★ 这不是这一卡带出来的东西：空转那一趟 `ghosts` 是 0，图照样挪（真后台也复现）。
  //     记在卡上当发现 —— 换一次看法，整幅图的横向比例会动 6px。
  await measure(p, 'macd', target.bar);
  const A0 = await sample(p, [target, control], 'before');
  ck('①b 空转那一趟（还是全给）那两块里量到的是**实心**的墨（没有幽灵那一档）',
     (A0.read[0].ghost || 0) <= 6 && (A0.read[0].full || 0) > 24,
     `目标点那块 ${JSON.stringify(A0.read[0])} ｜ 视图 ${JSON.stringify(A0.view)}`);

  // 再转一圈：这一趟（第 3 趟）少掉目标点 ⇒ 该出鬼了
  await measure(p, 'lines', target.bar);
  await p.locator('.mchip[data-measure="macd"]').click();
  let appeared = true;
  try {
    await p.waitForFunction(() => (window.__app.state.data.ghosts || []).length > 0, null, { timeout: 20000 });
  } catch (e) { appeared = false; }
  await sleep(900);
  const s1 = await snap(p);
  const A1 = await sample(p, [target, control], 'after');
  const r0 = A0.read, r1 = A1.read;
  const what = `第 1 趟 ${target.kind}@${target.bar} 在、第 2 趟不在；页面报 ${JSON.stringify(s1.ghosts.map((g) => g.kind + '@' + g.bar))}`;
  ck('少掉的那个点被记下来了（而且**只有它**一个）',
     appeared && s1.ghosts.length === 1 && s1.ghosts[0].bar === target.bar && s1.ghosts[0].kind === target.kind, what);
  ck('那一格报出这个数，并且写明是「本次打开」（分母不许跟回测那个 41/150 混）',
     s1.gc.on && /^消失的点 1（本次打开）$/.test(s1.gc.txt), `那一格：「${s1.gc.txt}」（on=${s1.gc.on}）`);
  // ②③ 位置 ＋ 形状（像素）
  const dF = (r0[0].full || 0) - (r1[0].full || 0), dG = (r1[0].ghost || 0) - (r0[0].ghost || 0);
  ck('② 记号画在**算出来的那个位置**上：那一小块里凭空长出了幽灵档的墨（别处没有）',
     (r1[0].ghost || 0) >= 12 && (r0[0].ghost || 0) <= 6,
     `记号那一块：之前 ${JSON.stringify(r0[0])}，之后 ${JSON.stringify(r1[0])}`
     + `（框 ${A1.boxes[0] && [A1.boxes[0].x, A1.boxes[0].y, A1.boxes[0].w, A1.boxes[0].h]}；视图 ${JSON.stringify(A1.view)}）`);
  ck('③ 形状真的换成了"作废"那支：实心的墨**掉了一颗三角那么多**',
     dF >= 24,
     `实心 ${r0[0].full}→${r1[0].full}（−${dF}）｜幽灵档 ${r0[0].ghost}→${r1[0].ghost}（+${dG}）`);
  ck('⑤ 对照格：同一屏里**没被动过的**那个点，前后读数一样（变的是那一个点，不是整屏重绘）',
     JSON.stringify(r0[1]) === JSON.stringify(r1[1]),
     `对照点 ${control.kind}@${control.bar}：${JSON.stringify(r0[1])} → ${JSON.stringify(r1[1])}\n`
     + `       框 ${JSON.stringify(A0.boxes[1])} → ${JSON.stringify(A1.boxes[1])}\n`
     + `       视图 ${JSON.stringify(A0.view)} → ${JSON.stringify(A1.view)}`);
  // ★ 这一格是量到 ⑤ 的漂移之后补的：那一格的 3px 就是**图被挤矮了**（foot 60→77、#chart 760→743）。
  //   判据钉在这一条上：那一格浮层出现/消失，图的尺寸一个字都不许动。
  //   （原先它并进图脚那一行 —— 图脚是流内布局，多这 42 个字就折行；窄屏那一档图脚还整个隐藏。）
  ck('④b2 那一格里带着记号**本尊的小样**（图例里没有这一格了 —— 形状得在它出现的地方认）',
     !!(s1.gc && s1.gc.svg), `那一格外壳里有 svg：${s1.gc && s1.gc.svg}`);

  ck('④c 那一格是**浮层**：它出现的时候图的尺寸一个像素都没动（占位的写法会把图挤矮）',
     JSON.stringify(A0.view.chart) === JSON.stringify(A1.view.chart),
     `#chart ${JSON.stringify(A0.view.chart)} → ${JSON.stringify(A1.view.chart)}`
     + `（图脚 ${A0.view.foot} → ${A1.view.foot}）`);

  // ④ 悬停
  const boxT = A1.boxes[0];
  await p.mouse.move(boxT.x + boxT.w / 2, boxT.y + boxT.h / 2);
  await sleep(400);
  const tip = await tipState(p);
  // ★ 措辞按 Atlas 10-05 核的那条改过：原来是「这个点 04-02 13:30 出现过」，可那是**极值那根**的
  //   时间，点在这之后才确认 —— 那一刻它还没「出现」。现在这句说的是「极值在 … 的这个三买，之前确认过」。
  ck('④ 指着那颗记号 ⇒ 说明弹出来，写的是卡上那句',
     !!tip && tip.on && /之前确认过/.test(tip.txt || '') && /已经不在了/.test(tip.txt || ''),
     tip ? `「${(tip.txt || '').replace(/\n/g, ' ⏎ ')}」` : '（页面上根本没有 ghosttip 这个元素）');
  ck('④b 那句话里带着**这个点自己的两个时刻**（极值那根 ＋ 我们看着它没掉那一下），两个都标了 UTC',
     !!tip && (tip.txt.match(/UTC/g) || []).length >= 2 && /极值在/.test(tip.txt), '');

  // ⑧ 那个点又回来了 ⇒ 记号收掉
  await measure(p, 'lines');
  await measure(p, 'macd');                                   // 第 4 趟：全给（目标点回来了）
  const s3 = await snap(p);
  ck('⑧ 那个点又回来了 ⇒ 记号收掉（它现在就在图上，两个记号并列就是自相矛盾）',
     s3.ghosts.length === 0 && s3.gc.txt === '' && !s3.gc.on,
     `报 ${s3.ghosts.length} 个；那一格：「${s3.gc.txt}」（这页请求次数 ${JSON.stringify(A.hits)}）`);

  // ⑦ 左沿守卫：删掉 bar=100 那个点（离窗口起点不到 200 根）⇒ 不许报
  await measure(p, 'lines');
  await measure(p, 'macd');                                   // 第 5 趟：抽掉 EDGE
  const s4 = await snap(p);
  ck('⑦ 左沿守卫：bar 100 那个点掉了 ⇒ **不报**（窗口起点一滑，那一段本来就会重算）',
     s4.ghosts.length === 0 && s4.gc.txt === '',
     `第 3 趟它在、第 4 趟不在；页面报 ${s4.ghosts.length} 个（① 证明 bar ${target.bar} 的报得出来）`);

  // ⑩ 重开页面就清零
  await p.reload({ waitUntil: 'domcontentloaded' });
  await p.waitForFunction(() => window.__app && window.__app.state && window.__app.state.data, null, { timeout: 60000 });
  await sleep(1200);
  const s5 = await snap(p);
  ck('⑩ 重开页面 ⇒ 账本清零、图脚那一格也没了（它只记有人看着时发生的）',
     s5.ghosts.length === 0 && s5.gc.txt === '' && !s5.gc.on, `重开之后那一格：「${s5.gc.txt}」`);

  // ================================================================ ⑨：正常刷不误报
  console.log('\n9 正常刷新不误报（同一份 payload 再要一遍，屏幕上逐像素不变）');
  const B2 = probe;                       // 这张页面从头到尾每一趟都吐一模一样的那份
  const q = B2.p;
  await q.locator('.chip[data-key="sig"]').click(); await sleep(900);
  await park(q, target.bar);
  await measure(q, 'lines', target.bar);                 // 先空转一圈把几何站稳（同正片那笔账）
  const C0 = await sample(q, [target], null);
  const n0 = C0.read;
  const qL2 = await measure(q, 'lines', target.bar);
  const C1 = await sample(q, [target], null);
  const n1 = C1.read;
  const sS = await snap(q);
  ck('⑨ 转一圈回来、数据一模一样 ⇒ 一个鬼都没有，那一格也不出来',
     qL2.ghosts.length === 0 && sS.ghosts.length === 0 && sS.gc.txt === '' && !sS.gc.on,
     `黄白线那趟 ${qL2.ghosts.length} 个 ／ 回来这趟 ${sS.ghosts.length} 个（这页请求次数 ${JSON.stringify(B2.hits)}）`);
  ck('⑨b 那一小块**逐像素没变**（实心还是实心）',
     JSON.stringify(n0[0]) === JSON.stringify(n1[0]),
     `${JSON.stringify(n0[0])} → ${JSON.stringify(n1[0])}（视图 ${JSON.stringify(C0.view)} → ${JSON.stringify(C1.view)}）`);

  // ================================================================ ⑪ 档位进桶
  // Bram 第 ① 条：往左加载是**整段重算**，重叠区里的点本来就会变 —— 跟换看法一样，是换了一把尺。
  // ★ 假后台这一趟**不接更早那一段**（真后台会整段重算）：接上去得把所有按下标指位置的地方
  //   （笔 i0/i1、段 i0/i1/PI0/PI1、点的 bar）整体平移，工装自己写错了比不写更糟。
  //   这里量的是**桶里有没有 span**，服务端多给一段不影响这条判断。
  console.log('\n11 往左加载一档：重叠区里少掉的那个点不许报（桶里必须有 span —— Bram 第 ① 条）');
  const S = await open('span');
  const sp = S.p;
  await sp.locator('.chip[data-key="sig"]').click();
  await sleep(900);
  const sp0 = await snap(sp);
  ck('⑪a 第一档：一个鬼都没有', sp0.ghosts.length === 0 && !sp0.gc.on,
     `报 ${sp0.ghosts.length} 个（${sp0.nSig} 个点、档 ${sp0.span}）`);
  // 摆到最左边，再用**真鼠标**往右拖一下 —— 页面只认「用户真动过输入设备」，脚本摆视口不算（见 more 那套）。
  await sp.evaluate(() => window.__app.chart.timeScale().setVisibleLogicalRange({ from: 4, to: 190 }));
  await sleep(500);
  await dragLeft(sp, 90);
  let spanned = true;
  try { await sp.waitForFunction(() => window.__app.paging.span >= 2, null, { timeout: 25000 }); }
  catch (e) { spanned = false; }
  await sleep(1200);
  const sp1 = await snap(sp);
  ck('⑪b 真拖到左沿 ⇒ 页面确实去要了第 2 档，而且那一份**真的**少了点（先证明场景发生了）',
     spanned && sp1.span >= 2 && sp0.nSig - sp1.nSig === D_TARGET.size,
     `档 ${sp0.span}→${sp1.span}；点 ${sp0.nSig}→${sp1.nSig}（少 ${sp0.nSig - sp1.nSig}，要等于 ${D_TARGET.size}）`);
  ck('⑪c 换档之后少掉的那个点**一个都不许报**（桶里必须有 span：档位一变就是换了一把尺）',
     sp1.ghosts.length === 0 && sp1.gc.txt === '' && !sp1.gc.on,
     `页面报 ${sp1.ghosts.length} 个（① 证明同一个点在同档位里报得出来，见正片 ②）`);

  // ================================================================ ⑫ 待确认 vs 已确认→待确认
  // Bram 第 ② 条：待确认的点本来就会变，它没了不算「消失」；但**「已确认 → 变回待确认」要算** ——
  // 那种点确实从图上被拿掉了。（做法：账本只把已确认的收进基准，所以这条不用另写判据。）
  console.log('\n12 待确认的点没了不许报；已确认变回待确认要报（Bram 第 ② 条）');
  const P2 = await open('pend');
  const pd = P2.p;
  await pd.locator('.chip[data-key="sig"]').click();
  await sleep(900);
  const pd0 = await snap(pd);
  ck('⑫a 第一趟带进来一个**待确认**的点（先证明场景发生了）',
     pd0.pends.includes(`pen|三买|${PEND_BAR}`) && pd0.ghosts.length === 0,
     `待确认的点 ${JSON.stringify(pd0.pends)}`);
  await measure(pd, 'lines');                      // 换桶再换回来 ⇒ macd 桶拿到第 2 趟
  await measure(pd, 'macd');
  const pd1 = await snap(pd);
  ck('⑫b 那个**待确认**的点后来没了 ⇒ 一个鬼都不许有（它本来就会变，Bram 第 ② 条前半句）',
     !pd1.pends.includes(`pen|三买|${PEND_BAR}`) && pd1.ghosts.length === 0 && !pd1.gc.on,
     `待确认的点 ${JSON.stringify(pd1.pends)}；页面报 ${pd1.ghosts.length} 个`);
  await measure(pd, 'lines');
  await measure(pd, 'macd');                       // 第 3 趟：目标点**还在**，但已确认 → 待确认
  const pd2 = await snap(pd);
  ck('⑫c 一个**已确认**的点变回待确认（还在名单里、只是没确认）⇒ 要报，而且只报它一个（后半句）',
     pd2.pends.includes(K(target.level || 'seg', target)) && pd2.ghosts.length === 1
     && pd2.ghosts[0].bar === target.bar && pd2.ghosts[0].kind === target.kind,
     `待确认名单里有它：${pd2.pends.includes(K(target.level || 'seg', target))}；页面报 `
     + `${JSON.stringify(pd2.ghosts.map((g) => g.kind + '@' + g.bar))}`);

  // ================================================================ ⑬ 收盘自动重取
  // Nova 2026-10-05 定的四条：①每收盘一根取一次 ②只在标签页可见时取、切回来补一次 ③一分钟最多一次
  // ④走同一条路径（读数压住、视口按时间放回原位）。这一格量的是**没人碰页面，空心点自己出现**。
  // ★ 位置/形状那两格在正片 ②③ 里像素量过（同一段代码）；这一格量的是「它自己会发生」。
  console.log('\n13 收盘自动重取：没人碰页面，空心点自己出现（Nova 10-05 那四条）');
  const AU = await open('auto');
  const au = AU.p;
  await au.locator('.chip[data-key="sig"]').click();
  await sleep(900);
  await park(au, target.bar);                      // 把视图停在目标点上（脚本摆视口不触发取数）
  const au0 = await sample(au, [target], null);
  const auS0 = await snap(au);
  ck('⑬a 打开时：一个鬼都没有，而且**一次取数**（还没到收盘）',
     auS0.ghosts.length === 0 && AU.hits.macd === 1,
     `取数 ${JSON.stringify(AU.hits)}｜目标那块 ${JSON.stringify(au0.read[0])}`);
  // ② 切到后台：收盘那一刻**一个请求都不发**
  await setVisible(au, 'hidden');
  await sleep(13000);                              // 收盘（＋10 秒余量）早就过了
  ck('⑬b 标签页在后台 ⇒ 收盘那一刻**一个请求都不发**（谁也没看的取数是白敲后台）',
     AU.hits.macd === 1, `取数 ${JSON.stringify(AU.hits)}（还该是 1）`);
  // ② 切回来立刻补一次 ⇒ 那个点是在没人碰页面的情况下自己没的
  await setVisible(au, 'visible');
  let came = true;
  try { await au.waitForFunction(() => (window.__app.state.data.ghosts || []).length > 0, null, { timeout: 30000 }); }
  catch (e) { came = false; }
  await sleep(900);
  const au1 = await sample(au, [target], 'auto');
  const auS1 = await snap(au);
  ck('⑬c 切回来**立刻补一次**，那个点自己没了 ⇒ 空心点自己出现在算出来的位置上（没人碰过页面）',
     came && auS1.ghosts.length === 1 && auS1.ghosts[0].bar === target.bar
     && (au1.read[0].ghost || 0) >= 12 && (au1.read[0].full || 0) < (au0.read[0].full || 0),
     `取数 ${JSON.stringify(AU.hits)}｜目标那块 ${JSON.stringify(au0.read[0])} → ${JSON.stringify(au1.read[0])}`
     + `｜视图 ${JSON.stringify(au0.view.chart)} → ${JSON.stringify(au1.view.chart)}`);
  ck('⑬d 那一格报数，并且写明「本次打开」（分母不许跟回测那个 41/150 混）',
     auS1.gc.on && /^消失的点 1（本次打开）$/.test(auS1.gc.txt), `那一格：「${auS1.gc.txt}」`);
  ck('⑬e 自动重取没有把画面搞乱：图的尺寸没动、视口没跳（走的是同一条 paint 路径）',
     JSON.stringify(au0.view.chart) === JSON.stringify(au1.view.chart)
     && JSON.stringify(au0.view.view) === JSON.stringify(au1.view.view),
     `#chart ${JSON.stringify(au0.view.chart)} → ${JSON.stringify(au1.view.chart)}`
     + `｜视口 ${JSON.stringify(au0.view.view)} → ${JSON.stringify(au1.view.view)}`);
  // ---- ⑬g⑤ SWR：收盘那一刻后台回的**还是旧**那份（refreshing=true），页面得自己再补一趟
  //      （Bram 10-05 量的坑：第一个请求才触发后台去币安拉新的那根，那一次回的还是旧数据）。
  console.log('\n13g 收盘那一趟回的是旧数据（SWR refreshing）⇒ 页面自己再补一次（不等人碰）');
  const S2 = await open('swr');
  const s2 = S2.p;
  await s2.locator('.chip[data-key="sig"]').click();
  // 等页面**自己**补到第 3 趟（全程不碰页面；第 2 趟是 SWR 的旧数据，第 3 趟才把新那根带回来）
  const t0 = Date.now();
  while (S2.hits.macd < 3 && Date.now() - t0 < 45000) await sleep(500);
  await sleep(600);
  const s2s = await snap(s2);
  ck('⑬g 回的还是旧那份（头里 refreshing）⇒ 页面**自己**又补了一趟（三趟都在，没人碰页面）',
     S2.hits.macd >= 3 && s2s.ghosts.length === 1 && s2s.ghosts[0].bar === target.bar,
     `取数时刻 ${JSON.stringify(S2.reqAt.map((t) => t - S2.closeAt))}（相对收盘，ms）`
     + `｜macd ${S2.hits.macd}｜报 ${s2s.ghosts.length} 个`);
  ck('⑬h 错峰：收盘之后**没有**立刻取，也不是拖到下一个周期才取（随机 2–10 秒这一档）',
     S2.reqAt.length >= 2 && (S2.reqAt[1] - S2.closeAt) >= 1900 && (S2.reqAt[1] - S2.closeAt) <= 12000,
     `第一趟自动取数在收盘后 ${S2.reqAt.length >= 2 ? S2.reqAt[1] - S2.closeAt : '—'} ms（要落在 2000–10000 一带）`);
  // ② 的上界：补的次数有上限 —— 后台一直没把新那根拉回来时，不许变成连环请求
  const t1 = Date.now();
  while (S2.hits.macd < 5 && Date.now() - t1 < 60000) await sleep(500);
  await sleep(1500);
  ck('⑬i 一直补不到新数据 ⇒ 补到上限就停（不是无限连环请求）',
     S2.hits.macd === 5, `macd 一共 ${S2.hits.macd} 次（打开 1 ＋ 补 4，上限 4）`);
  // ③ 一分钟内最多一次：★ 先证明**这份数据现在确实是过期的**（不然这一格是空转）
  const overdue = await s2.evaluate(() => {
    const d = window.__app.state.data;
    return (d.bars[d.bars.length - 1].t + 900000) <= Date.now();
  });
  const b4 = S2.hits.macd;
  await setVisible(s2, 'hidden'); await sleep(400);
  await setVisible(s2, 'visible'); await sleep(2500);
  await setVisible(s2, 'hidden'); await sleep(400);
  await setVisible(s2, 'visible'); await sleep(2500);
  ck('⑬j 一分钟内最多一次：这份数据**确实还是过期的**，切回来两次也不许再敲第三个请求',
     overdue && S2.hits.macd === b4, `数据过期=${overdue}；切了两轮，取数 ${b4} → ${S2.hits.macd}`);

  // ---- ⑭ 收盘那一趟**后台挂了**（abort，不是"回旧数据"）：load() 会悄悄退回仓里的样本。
  //      为什么必须单钉一格：样本跟手上这份**是两份数据**，一旦画上去，账本会把整屏读成"全没了"
  //      —— 用户看到的是满屏空心点，而且他什么都没做。顺带 adopt() 还会吃掉样本硬塞的 span/earliest，
  //      把档位和窗口一起洗掉。所以这一趟只能"当没跑"。
  //      ★ 这一页挂在 BTCUSDT 4h 上：仓里**只有** btc_4h.json 这一份样本 —— 挂在正片那个品种上，
  //        load() 退回样本时是直接抛，"退回样本被画上去"这条危险路径根本走不到（那一格会假绿）。
  console.log('\n14 收盘那一趟后台挂了（退回样本）⇒ 页面当没跑，不许把样本当刷新画上去');
  const FB = await open('fallback', '?symbol=BTCUSDT&tf=4h');
  const fb = FB.p;
  await fb.locator('.chip[data-key="sig"]').click();
  // 先证明危险路径**是活的**：这一页退回样本时真拿得到一份（不然这一格是空转格）
  const hasFix = await fb.evaluate(() => fetch('fixtures/btc_4h.json').then((r) => r.ok).catch(() => false));
  const fb0 = await snap(fb);
  const t2 = Date.now();
  while (FB.hits.macd < 2 && Date.now() - t2 < 40000) await sleep(500);      // 等收盘后那一趟自己发生
  await sleep(2500);
  const fb1 = await snap(fb);
  ck('⑭a 那一趟没拿到真数据（退回样本）⇒ 屏上那份一个字节都没换，也没连环补',
     hasFix && FB.hits.macd === 2 && fb1.src === 'api' && fb1.nBars === fb0.nBars,
     `仓里有样本=${hasFix}｜取数 ${JSON.stringify(FB.hits)}（该正好 2：打开 1 ＋ 收盘那趟 1）`
     + `｜出处 ${fb0.src} → ${fb1.src}｜根数 ${fb0.nBars} → ${fb1.nBars}｜档 ${fb0.span} → ${fb1.span}`);
  ck('⑭b 而且一个假鬼都没有（样本跟手上这份是两回事，画上去就是满屏空心点）',
     fb1.ghosts.length === 0 && (!fb1.gc || !fb1.gc.on),
     `页面报 ${fb1.ghosts.length} 个｜那一格：「${fb1.gc ? fb1.gc.txt : '（没有）'}」`);

  // ---- ⑮ 换引擎（core/*.py 一改、部署）≈ 换了一把尺：不许拿新旧两份比出「消失」
  //      两张页面**只差 `engine` 这一个字段**：同样的点、同样少那一片、同样把新那根带回来。
  //      差别只有这一个 ⇒ 报不报只能归因于它。'engsame' 是对照组 —— 没有它，'engine' 报 0
  //      也可能只是"这一套在这张页面上根本没工作"（空转格）。
  console.log('\n15 换引擎（部署那一刻）不许比出「消失」—— 桶键里得有 engine');
  const ES = await open('engsame');
  const es = ES.p;
  await es.locator('.chip[data-key="sig"]').click();
  { const t = Date.now(); while (ES.hits.macd < 2 && Date.now() - t < 40000) await sleep(500); }
  await sleep(1500);
  const esS = await snap(es);
  ck('⑮a 对照：引擎没变、同样少那一片 ⇒ **照报**（先证明这一套在这张页面上报得出来）',
     esS.eng === ENG1 && esS.ghosts.length === D_LINES.size,
     `引擎 ${esS.eng}｜该少 ${D_LINES.size} 个（左沿那个被守卫吃掉，照 ⑦），页面报 ${esS.ghosts.length} 个`);
  const EG = await open('engine');
  const eg = EG.p;
  await eg.locator('.chip[data-key="sig"]').click();
  { const t = Date.now(); while (EG.hits.macd < 2 && Date.now() - t < 40000) await sleep(500); }
  await sleep(1500);
  const egS = await snap(eg);
  ck('⑮b 引擎变了（E1→E2）、点少得一模一样 ⇒ **一个都不许报**（换了把尺，不是重绘）',
     egS.eng === ENG2 && egS.ghosts.length === 0 && (!egS.gc || !egS.gc.on),
     `引擎 ${esS.eng} → ${egS.eng}｜页面报 ${egS.ghosts.length} 个｜那一格：「${egS.gc ? egS.gc.txt : '（没有）'}」`);

  await b.close();
  console.log(`\n${n - bad}/${n} 过　截图：${OUT}`);
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.error('✗ 炸了：' + (e && e.stack || e)); process.exit(2); });
