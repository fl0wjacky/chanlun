// 「背驰四选一」那个切换控件的浏览器工装（card-84091d2d-c97，2026-10-04）
//
// ★ 它**不是**六把尺里的一把：尺子是纯函数、秒级；这一套要 playwright ＋ 真浏览器 ＋ **真后台**
//   （web/server.py：这一格量的是「点一下之后后台真按那个看法重算了没有」，假后台证明不了）。
//   放仓里是为了**别人能复跑**（跟 tools/web_more_e2e.js 一个道理）。
//
// 量的是接线，不是算法（算法归 Bram 的探针）：
//   ① 控件由 /api/meta 的 measures 驱动：四颗、**名字是大白话**、选中态走 aria-checked（不是图层那排的 aria-pressed）
//   ② 点「黄白线」⇒ 那一趟请求带 measure=lines（**带的是被点的那个**，不是缺省）
//   ③ 图脚**跟着回显**换：「背驰看法 黄白线」（回显说了算，不拿点的那颗当准）
//   ④ 亮着的那颗也跟着回显换
//   ⑤ 切看法**结构逐字节不变**：bars/pens/segs/centers/seg_centers 前后全等（后台契约）
//      ★ 这一格**必须**是「同一趟币安取数」内的两份（fetched_at 对账 ＋ 撞上就重跑）：
//        后台每 60s 重拉，跨在重拉两边的两份本来就该不一样 —— 不闸住它就是随机红
//   ⑥ 买卖点**真的变了**：signals 前后不等（不然这一格是空转 —— 四选一要是没接上，五个断言全绿）
//   ⑦ **三角真的画出来了**（2026-10-04 补）：在买卖点那颗三角盘踞的那一小块上，把「买卖点」chip
//      关掉再点开，只认买卖点那两个颜色（±8）—— **多出来的**像素得够一颗三角。★ 这一格是补课：
//      线上出过一次「买卖点整层一颗不画」，而当时这句「屏幕真的变了」照样绿 —— 它量到的像素差
//      来自买卖点的**文字**，是替身。补的这格只取三角那一块、只认那两个颜色，差分看。
//   ⑧ 同一状态重拍，读数一模一样（⑦ 的防空洞：这一格量的是那个开关，不是抖动）
//   ⑨ 屏幕**真的变了**：图的像素前后不等（数据变了不等于画出来了；这条是拍照，不是读状态）
//   ⑩ 视口**一动没动**（切看法不换档，同一根 K 线还在同一个逻辑下标上）
//   ⑪ 档位那套**没被踩坏**：切完 nogain=false（把它当成「补数据没多出来」，下一拖就会印假话）
//   ⑫ ?measure=lines 直接打开 ⇒ **第一趟**图表请求就带 lines，图脚写「黄白线」
//   ⑬ ?measure=乱写 ⇒ 一个字都不发出去（名单外发出去是 400，整张图会白挂），页面照常画
//   ⑭ 旧后台（/api/meta 没有 measures）⇒ 控件**不出现**、请求**不带** measure、图脚**不多**那一格
//
// 跑法：
//   1) 真后台，**只绑回环**（部署纪律：不许绑全网卡）：
//        python3 web/server.py --port 8792
//   2) playwright：`npm i playwright && npx playwright install chromium`（各机器一次）
//      node_modules 不在仓里 —— 在装好 playwright 的目录下跑，用 NODE_PATH 指过来即可。
//   3) node tools/web_measure_e2e.js [输出目录] [页面地址]
//        输出目录默认 $TMPDIR/measure-e2e（截图落这儿；不写进仓）
//        页面地址默认 http://127.0.0.1:8792/
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

const OUT = process.argv[2] || path.join(os.tmpdir(), 'measure-e2e');
const PAGE = (process.argv[3] || 'http://127.0.0.1:8792/').replace(/\/?$/, '/');
const QS = '?symbol=ZECUSDT&tf=15m';       // 周期挑最短的那档：首屏快，且这一档的四种看法分得最开
let bad = 0, n = 0;
const ck = (name, ok, extra) => {
  n++;
  if (!ok) bad++;
  console.log(`  ${ok ? '✓' : '✗'} ${n}. ${name}${extra ? '　' + extra : ''}`);
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 页面上画出来的那份数据（比较用：结构四件套 + 买卖点）
const shape = (p) => p.evaluate(() => {
  const d = window.__app.state.data;
  const J = (x) => JSON.stringify(x);
  return {
    struct: [J(d.bars), J(d.pens), J(d.segs), J(d.centers), J(d.seg_centers), J(d.big)].join('#'),
    sigs: J(d.signals), nbars: d.bars.length, span: d.span, measure: d.measure,
    fetched: d.fetched_at,      // ★ ⑤ 那一格的闸：这两份是不是**同一趟币安取数**（见下面那段说明）
    range: window.__app.chart.timeScale().getVisibleLogicalRange(),
    paging: { span: window.__app.paging.span, nogain: window.__app.paging.nogain,
              measure: window.__app.paging.measure, spanMax: window.__app.paging.spanMax },
  };
});
const ui = (p) => p.evaluate(() => {
  const g = document.getElementById('mgroup');
  return {
    has: !!g,
    items: g ? [...g.querySelectorAll('.mchip')].map((b) => ({ id: b.dataset.measure, txt: b.textContent.trim(),
                                                              on: b.getAttribute('aria-checked'),
                                                              pressed: b.getAttribute('aria-pressed'),
                                                              role: b.getAttribute('role'), title: b.title })) : [],
    cap: g ? (g.querySelector('.mcap') || {}).textContent : null,
    meta: (document.getElementById('meta') || {}).textContent || '',
  };
});
const waitData = (p) => p.waitForFunction(() => window.__app && window.__app.state && window.__app.state.data, null, { timeout: 120000 });
// 只拍图那一栏（顶栏/图脚那些字不参与）：像素一样＝这一屏没变
const shotChart = async (p, tag) => {
  const box = await p.locator('#chart').boundingBox();
  const buf = await p.screenshot({ clip: box });
  fs.writeFileSync(path.join(OUT, `fig-${tag}.png`), buf);
  return buf;
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const b = await chromium.launch();
  const open = async (qs, opts = {}) => {
    const c = await b.newContext({ viewport: { width: 1440, height: 900 } });
    const p = await c.newPage();
    const reqs = [];
    p.on('request', (r) => { if (r.url().includes('/api/chart')) reqs.push(r.url()); });
    if (opts.meta) await p.route('**/api/meta', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(opts.meta) }));
    if (opts.oldBackend) {
      // 假装是**今天之前那个后台**：那时候没有 measure 这个参数 ⇒ /api/meta 里没有 measures、
      // 图表响应里也没有 measure 这个字段（**两头都抹掉**才算「旧后台」：只抹一头的话，
      // 图脚那份回显还是真的，「图脚不该多那一格」就永远量不到 —— 第一版就是这么假绿的）。
      await p.route('**/api/meta', (route) => route.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ symbols: ['ZECUSDT'], tfs: ['15m'] }) }));
      await p.route('**/api/chart*', async (route) => {
        if (/[?&]measure=/.test(route.request().url())) opts.sawMeasure = route.request().url();
        const r = await route.fetch();
        const j = await r.json();
        delete j.measure;
        await route.fulfill({ status: r.status(), contentType: 'application/json', body: JSON.stringify(j) });
      });
    }
    await p.goto(PAGE + qs, { waitUntil: 'domcontentloaded' });
    await waitData(p);
    await sleep(1200);                    // 等控件那一趟 /api/meta（并行发的，可能比图晚一拍）
    return { c, p, reqs, opts };
  };

  // ★★ 开跑①–⑨之前：等后台**刚拉过币安**。回显里的 fetched_at 就是那趟的时间，
  //    age 离 60s 还早就把场景摆进同一趟取数里（不然开页那趟跟点一下那趟会跨在重拉两边，⑤ 假红）。
  //    只在「快到点了」时才等（age > 35 才等），多数时候一眼就过。
  const stamp = async () => {
    const d = await (await fetch(PAGE + 'api/chart?symbol=ZECUSDT&tf=15m')).json();
    return { at: d.fetched_at, age: (Date.now() - Date.parse(d.fetched_at)) / 1000 };
  };
  if (typeof fetch === 'function') {
    const st = await stamp();
    if (st.age > 35) {
      console.log(`  等一趟重拉（手上这份数据已经 ${st.age.toFixed(0)}s 了）…`);
      // age ≥ 60 ⇒ 已经过点了，刚才那一问就已经把它踢去拉了，不用再睡；
      // 35 < age < 60 ⇒ 先睡到那一刻（注意别睡出负数：setTimeout 会把负的当 1ms）
      if (st.age < 60) await sleep((61 - st.age) * 1000);
      // 重拉是**懒**的：到点了也得有人来要它才拉（server.py get_chart），且这一趟先回旧缓存
      // ⇒ 得轮着问、直到 fetched_at 真换掉
      let i = 0;
      while (i < 20 && (await stamp()).at === st.at) { await sleep(1000); i++; }
      if (i >= 20) console.log('  ⚠ 等了 20s 也没换新的（后台这轮大概没拉到币安）—— 照跑，⑤ 会自己红');
    }
  }

  // ---- ①–⑨：普通那一页
  console.log('①–⑪ 打开页面、点一下「黄白线」');
  const { c, p, reqs } = await open(QS);
  const u0 = await ui(p);
  ck('/api/meta 把四颗控件渲染出来了', u0.has && u0.items.length === 4, u0.items.map((i) => i.id).join('/'));
  ck('名字是大白话（面积/斜率/黄白线/峰值），代号只在 data 里',
     JSON.stringify(u0.items.map((i) => i.txt)) === JSON.stringify(['面积', '斜率', '黄白线', '峰值']),
     u0.items.map((i) => i.txt).join(' '));
  ck('是**单选**的形状：role=radio ＋ aria-checked，不是图层那排的 aria-pressed',
     u0.items.every((i) => i.role === 'radio' && i.pressed === null) && u0.items.filter((i) => i.on === 'true').length === 1
     && u0.items.find((i) => i.on === 'true').id === 'macd');
  ck('图脚写着当前用的那种（默认＝面积）', u0.meta.includes('背驰看法 面积'), u0.meta.slice(-40));
  // ★ 买卖点默认是**关**的：不打开它，切看法屏幕上什么也不会变（这一格得先把它打开，否则 ⑥⑦ 是空转）
  await p.locator('.chip[data-key="sig"]').click();
  await sleep(900);
  // ★★ 拍像素之前先把视口**摆到两种看法真的不一样的地方**去。第一版直接拍当前这一屏 ⇒
  //    像素一模一样，看着像「切了看法屏幕没变」，其实是**那几处差异根本不在可视窗口里**
  //    （整段 20160 根、窗口在最后 300 根）。那是工装自己把两件事搞混了：图脚上的计数是**整段**的，
  //    像素只认**这一屏**。所以先问后台要两份、找出不一样的那几根，再摆过去。
  const diffBars = await p.evaluate(async () => {
    const get = async (m) => (await (await fetch(`/api/chart?symbol=ZECUSDT&tf=15m&measure=${m}`)).json());
    const key = (s) => s.bar + ':' + s.kind;
    const [a, b2] = [await get('macd'), await get('lines')];
    const all = (d) => (d.signals.seg || []).concat(d.signals.pen || []).map(key);
    const A = new Set(all(a)), B = new Set(all(b2));
    return [...new Set([...A].filter((x) => !B.has(x)).concat([...B].filter((x) => !A.has(x))))
      .values()].map((x) => Number(x.split(':')[0])).slice(0, 8);
  });
  if (diffBars.length) {
    const at = diffBars[Math.floor(diffBars.length / 2)];
    await p.evaluate((i) => window.__app.chart.timeScale().setVisibleLogicalRange({ from: i - 120, to: i + 120 }), at);
    await sleep(600);
  }
  // ★★ ⑤「结构逐字节不变」这一格的闸：**得是同一趟币安取数**。
  //    后台每 REFRESH_S=60s 重拉一次（web/server.py）；s0 是**页面开页那趟**拿到的，
  //    s1 是点一下之后**新发的那趟**拿到的 —— 中间撞上重拉，最后一根 K 线的收盘就在变，
  //    结构**真的会不一样**：那是后台的账，不是切看法的账。
  //    （第一版没管这个，⑤ 就随机红：同一份代码前一次绿、这一次红。当时查了半天，
  //      原因是「两次观测」根本不保证在同一趟取数里。）
  //    两道闸：① 开跑**之前**等后台刚拉过 —— 把整个场景摆进一趟取数里（见上面那段 wait）
  //            ② 收尾时拿 fetched_at 对账：对不上就切回默认重跑一对（最多三对），三对都撞上才红
  const sw = async (id) => {                    // 点一颗看法、等它真换过来；回这一趟发出的 measure
    const kk = reqs.length;
    await p.locator(`.mchip[data-measure="${id}"]`).click();
    await p.waitForFunction((m) => window.__app.state.data && window.__app.state.data.measure === m, id, { timeout: 60000 });
    await sleep(900);
    return reqs.slice(kk).map((u) => new URL(u).searchParams.get('measure'));
  };
  let s0, s1, px0, px1, sent, redo = 0;
  for (;;) {
    s0 = await shape(p); px0 = await shotChart(p, 'before');
    sent = await sw('lines');
    s1 = await shape(p); px1 = await shotChart(p, 'after');
    if (s0.fetched === s1.fetched || redo >= 2) break;
    redo++;                                     // 这两份不是一趟取数 ⇒ 切回去、重来一对
    await sw('macd');
  }
  const u1 = await ui(p);
  ck('点的是「黄白线」⇒ 发出去的就是 lines', sent.length === 1 && sent[0] === 'lines', `发出的 measure=${JSON.stringify(sent)}`);
  ck('图脚跟着**回显**换：背驰看法 黄白线', u1.meta.includes('背驰看法 黄白线'), u1.meta.slice(-40));
  ck('亮着的那颗也跟着回显换', u1.items.find((i) => i.on === 'true').id === 'lines');
  ck('结构逐字节不变（bars/pens/segs/centers/seg_centers）',
     s0.fetched === s1.fetched && s0.struct === s1.struct && s0.nbars === s1.nbars,
     s0.fetched === s1.fetched
       ? `同一趟取数 ${s0.fetched}${redo ? `（撞上重拉、重跑了 ${redo} 遍）` : ''}`
       : `★ 这两份不是同一趟取数：${s0.fetched} → ${s1.fetched}（后台重拉过，这一格量不准）`);
  ck('买卖点真的变了（不然这一格是空转）', s0.sigs !== s1.sigs,
     `段 ${JSON.parse(s0.sigs).seg.length}→${JSON.parse(s1.sigs).seg.length} 笔 ${JSON.parse(s0.sigs).pen.length}→${JSON.parse(s1.sigs).pen.length}`);

  // ★★ 三角到底画出来了没有 —— 2026-10-04 补的一格（线上真出过：买卖点**整层一颗不画**，而下面
  //    那格「屏幕真的变了」照样绿：它量到的像素差来自买卖点的**文字**，是替身）。
  //    口径（Atlas 2026-10-04）：只取**三角盘踞的那一小块**、只认**买卖点那两个颜色**，不拿整屏比。
  //    ★ 为什么是**关/开差分**而不是「开着得有、关掉得空」：那一小块正好落在波段顶/底上，
  //      里面本来就躺着同色的东西 —— 线段端点的空心圈（也是 CHART.buy/sell，跟买卖点同一个色）
  //      和挨着的阴线。所以两边都读一次、**看差**：差分里剩下的才是这一个开关管的那颗三角。
  //      （第一版写「关掉必须为 0」，红得对但红错了地方：那些像素根本不归这个开关管。）
  //    两问：① 点开买卖点 ⇒ 那块里多出来的买卖点色够一颗三角；② 这个读数是**稳的**（同一状态重拍一样）。
  const hex2rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const MARK = await p.evaluate(async () => {
    const m = await import('/theme.js');
    return { buy: m.CHART.buy, sell: m.CHART.sell, seg: m.SIG.segSize, pen: m.SIG.penSize, tip: m.SIG.tip };
  });
  const chartBox = await p.locator('#chart').boundingBox();
  const triBoxes = await p.evaluate(([MARK, box]) => {
    const ch = window.__app.chart, ts = ch.timeScale(), s0 = ch.panes()[0].getSeries()[0];
    const out = [];
    for (const tier of ['seg', 'pen']) for (const s of (window.__app.state.data.signals[tier] || [])) {
      if (!s.confirmed) continue;                       // 待确认默认不画，别拿它当样本
      const x = ts.logicalToCoordinate(s.bar), y = s0.priceToCoordinate(s.price);
      if (x === null || y === null || x < 60 || x > box.width - 60) continue;
      const hh = (tier === 'seg' ? MARK.seg : MARK.pen) * 0.55;   // ＝ layers.js 那个 0.55
      const d = s.kind.endsWith('买') ? 1 : -1;                   // 买点在点位下方、卖点在上方
      const yy = Math.min(y + d * MARK.tip * 0.6, y + d * (MARK.tip * 0.6 + 2 * hh));
      out.push({ tier, kind: s.kind, bar: s.bar, buy: s.kind.endsWith('买'),
                 x: Math.round(box.x + x - hh - 2), y: Math.round(box.y + yy - 2),
                 w: Math.round(2 * hh + 5), h: Math.round(2 * hh + 5) });
    }
    return out.sort((a, b) => (a.tier === b.tier ? 0 : a.tier === 'seg' ? -1 : 1)).slice(0, 3);
  }, [MARK, chartBox]);
  const countMarks = (bs) => p.evaluate(([bs, buy, sell]) => {
    // ★ 颜色**只认这两个**（±8）：放太宽会把阴线 `#ef5350`（跟卖点 `#ff5656` 只差 (16,3,6)）算进来，
    //   那一格就变成「在数量 K 线」。已确认的点 alpha=255，三角内部是**纯色**，收紧也数得到。
    const near = (a, b) => Math.abs(a - b) <= 8;
    const which = (r, g, b) => (near(r, buy[0]) && near(g, buy[1]) && near(b, buy[2])) ? 'buy'
      : (near(r, sell[0]) && near(g, sell[1]) && near(b, sell[2])) ? 'sell' : null;
    const cvs = [...document.querySelectorAll('#chart canvas')].map((c) => ({ c, r: c.getBoundingClientRect() }));
    return bs.map(({ x, y, w, h, buy }) => {
      // ★ 一张图上是**好几层画布**（K 线一层、primitive 另起一层）。买卖点画在哪一层是实现细节，
      //   所以**每一张盖住这一块的都要读**、个数相加；只读第一张的话，读错了层就是恒 0 的假红
      //   （第一版就是这么红的：图看着有三角，这一格说 0）。
      const hit = cvs.filter(({ r }) => x >= r.left && y >= r.top && x + w <= r.right && y + h <= r.bottom);
      if (!hit.length) return { miss: '那一块没落在任何一张画布上' };
      let n = 0;
      for (const { c, r } of hit) {
        const px = c.getContext('2d').getImageData(Math.round(x - r.left), Math.round(y - r.top), w, h).data;
        for (let i = 0; i < px.length; i += 4) if (which(px[i], px[i + 1], px[i + 2]) === (buy ? 'buy' : 'sell')) n++;
      }
      return { n };
    });
  }, [bs, hex2rgb(MARK.buy), hex2rgb(MARK.sell)]);
  const on = await countMarks(triBoxes);                       // 这一页的买卖点**已经点开**（见上面那一行）
  await p.locator('.chip[data-key="sig"]').click(); await sleep(800);
  const off = await countMarks(triBoxes);
  await p.locator('.chip[data-key="sig"]').click(); await sleep(800);    // 点回来；后面那格用的就是这一次
  const again = await countMarks(triBoxes);
  const desc = (a) => a.map((o, i) => `${triBoxes[i].kind}@${triBoxes[i].bar}${o.miss ? '（' + o.miss + '）' : '=' + o.n}`).join(' ');
  const need = (t) => (t === 'seg' ? 24 : 3);                  // 实心三角 ~136 格、空心笔层就几格描边
  const dlt = on.map((o, i) => o.n - (off[i] ? off[i].n : 0));
  ck('买卖点点开 ⇒ 三角那一块里**真多出一颗三角**（关/开同一块差分，只认买卖点那两个颜色）',
     triBoxes.length >= 2 && dlt.every((d, i) => d >= need(triBoxes[i].tier)),
     `${triBoxes.length} 颗样本：开着 ${desc(on)}｜关掉 ${desc(off)}｜多出来 ${JSON.stringify(dlt)}`);
  ck('同一状态重拍，读数一模一样（这一格量的是那个开关，不是抖动）',
     triBoxes.length >= 2 && again.every((o, i) => o.n === on[i].n),
     `两次都开着：${desc(on)} ／ ${desc(again)}`);
  ck('屏幕真的变了（把视口摆到两种看法真的不一样的那几根上，图的像素前后不等）',
     diffBars.length > 0 && !px0.equals(px1),
     `${diffBars.length} 根上不一样，视口摆在 bar=${diffBars[Math.floor(diffBars.length / 2)]}`);
  const dr = (a, b2) => Math.max(Math.abs(a.from - b2.from), Math.abs(a.to - b2.to));
  ck('视口一动没动（切看法不换档）', dr(s0.range, s1.range) < 0.001,
     `${s0.range.from.toFixed(2)}..${s0.range.to.toFixed(2)} → ${s1.range.from.toFixed(2)}..${s1.range.to.toFixed(2)}`);
  ck('档位那套没被踩坏：span 不变、nogain=false（当补数据判会印假话）',
     s1.paging.span === s0.paging.span && s1.paging.nogain === false && s1.paging.measure === 'lines',
     JSON.stringify(s1.paging));
  await c.close();

  // ---- ⑩：?measure=lines 直接打开
  console.log('⑫ ?measure=lines 直接打开');
  const d2 = await open(QS + '&measure=lines');
  const first = d2.reqs.length ? new URL(d2.reqs[0]).searchParams.get('measure') : null;
  const u2 = await ui(d2.p);
  ck('**第一趟**图表请求就带 lines（不是先要缺省再补一趟）', first === 'lines', `第一趟 measure=${first}，共 ${d2.reqs.length} 趟`);
  ck('图脚与选中态都说黄白线', u2.meta.includes('背驰看法 黄白线') && u2.items.find((i) => i.on === 'true').id === 'lines');
  await d2.c.close();

  // ---- ⑪：?measure=乱写
  console.log('⑬ ?measure=乱写');
  const d3 = await open(QS + '&measure=bogus');
  const seen = d3.reqs.map((u) => new URL(u).searchParams.get('measure'));
  const u3 = await ui(d3.p);
  ck('名单外的名字一个都不发（发出去后台 400，整张图白挂）', !seen.includes('bogus'), `发出的 measure=${JSON.stringify(seen)}`);
  ck('页面照常画出来、退回缺省那种', (await shape(d3.p)).measure === 'macd' && u3.meta.includes('背驰看法 面积'));
  await d3.c.close();

  // ---- ⑫：旧后台（没有 measures）
  console.log('⑭ 旧后台（/api/meta 没有 measures）');
  const d4 = await open(QS, { oldBackend: true });
  const u4 = await ui(d4.p);
  ck('控件不出现（不知道的事不编）', !u4.has);
  ck('请求里一个字都不带 measure（旧后台的查询白名单里没有它，多带一个就是 400）', !d4.opts.sawMeasure,
     d4.opts.sawMeasure || '没带');
  ck('图脚不多那一格', !u4.meta.includes('背驰看法'));
  await d4.c.close();

  await b.close();
  console.log(`\n${n - bad}/${n} 过${bad ? `，${bad} 条红` : ''}　截图：${OUT}`);
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.error('炸了：', e.message); process.exit(2); });
