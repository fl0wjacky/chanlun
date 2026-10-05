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

  const clone = (x) => JSON.parse(JSON.stringify(x));
  /** 模子 → 这一趟要吐的 payload。drop 里是 "tier|kind|bar"；EDGE 那个点每次都注入（它量守卫）。 */
  const mk = (measure, drop) => {
    const d = clone(base);
    d.measure = measure;
    d.signals.pen.push({ kind: '三买', bar: EDGE_BAR, price: base.bars[EDGE_BAR].l, confirmed: true,
                         weak: false, level: 'pen', center: 1, unit: 3 });
    for (const tier of ['seg', 'pen']) {
      d.signals[tier] = (d.signals[tier] || []).filter((s) => !drop.has(`${tier}|${s.kind}|${s.bar}`));
    }
    return d;
  };
  const K = (tier, s) => `${tier}|${s.kind}|${s.bar}`;
  const D_TARGET = new Set([K(target.level || 'seg', target)]);
  const D_EDGE = new Set([`pen|三买|${EDGE_BAR}`]);
  const D_LINES = new Set([K(target.level || 'seg', target), K(control.level || 'pen', control)]);
  // 每一趟吐什么：序号从 1 起（每张页面自己数自己的）。
  // ★ 第 2 趟**还是全给**：这不是为了看鬼，是先空转一圈把图的几何站稳（见正片里那段账）——
  //   两次像素读数都得在"已经落定"的状态下取，否则量到的是图自己挪了 1px。
  const SEQ = [null, new Set(), new Set(), D_TARGET, new Set(), D_EDGE];
  const plan = (which, i) => {
    if (which === 'lines') return D_LINES;                       // 黄白线那份：少两个点（量 ⑥ 不造鬼）
    if (which === 'same') return new Set();                      // ⑨：每一次都吐一模一样的
    return i < SEQ.length ? SEQ[i] : new Set();
  };

  const b = await chromium.launch();
  const open = async (which) => {
    const c = await b.newContext({ viewport: { width: 1440, height: 900 } });
    const p = await c.newPage();
    const hits = {};
    p.on('console', (m) => { if (m.type() === 'error') console.log('    [page error] ' + m.text()); });
    p.on('pageerror', (e) => console.log('    [page error] ' + e.message));
    await p.route('**/api/chart*', async (route) => {
      const u = new URL(route.request().url());
      const m = u.searchParams.get('measure') || 'macd';
      hits[m] = (hits[m] || 0) + 1;
      const body = mk(m, plan(which, hits[m]));
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    });
    await p.goto(PAGE + QS, { waitUntil: 'domcontentloaded' });
    await p.waitForFunction(() => window.__app && window.__app.state && window.__app.state.data, null, { timeout: 60000 });
    await sleep(1200);                     // 等 /api/meta 那一趟（控件由它驱动）
    return { c, p, hits };
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
    return { ghosts: (d.ghosts || []).map((x) => ({ kind: x.kind, tier: x.tier, bar: x.bar, price: x.price, t: x.t })),
             meta: (document.getElementById('meta') || {}).textContent || '',
             // 只读那一格里的**文字**（壳里还有记号小样那个 svg；连壳一起读会把缩进也算进来）
             gc: g ? { txt: (t || {}).textContent || '', on: g.classList.contains('on'),
                       svg: !!g.querySelector('svg') } : null,
             measure: d.measure, tip: (document.getElementById('ghosttip') || {}).textContent || '' };
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
  ck('⑥ 换看法（面积→黄白线）⇒ 那边少着的两个点**一个都没报成消失**（桶里必须有「看法」）',
     sL.ghosts.length === 0 && sL.gc.txt === '' && !sL.gc.on,
     `黄白线那份少着 ${D_LINES.size} 个点；页面报 ${sL.ghosts.length} 个`);

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
  ck('④ 指着那颗记号 ⇒ 说明弹出来，写的是卡上那句',
     !!tip && tip.on && /出现过、后来消失了/.test(tip.txt || ''),
     tip ? `「${(tip.txt || '').replace(/\n/g, ' ⏎ ')}」` : '（页面上根本没有 ghosttip 这个元素）');
  ck('④b 那句话里带**这个点自己的时刻**（不是随手一句），而且标了 UTC',
     !!tip && tip.txt.includes('UTC') && /出现过、后来消失了/.test(tip.txt), '');

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

  await b.close();
  console.log(`\n${n - bad}/${n} 过　截图：${OUT}`);
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.error('✗ 炸了：' + (e && e.stack || e)); process.exit(2); });
