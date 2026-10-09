// 决策树页的浏览器工装（card-fe3aebd3-819，2026-10-09）
//
// 量的是**页面接线**，读 ?mock=1（decisions/mock.json，Atlas 那份数据的快照）：
//   predeploy 起的临时后台不一定有数据文件，后台那半（口令、回码、存取）归 web/check_decisions.py，这里不重复。
//   ① 左边树的条数 = 数据里的条数，层名照 layer_order，没有一条丢
//   ② 每条数据里写了「小栋定」且 verified 的，页上都挂「你选的」，挂在 status.choice 那一项上，而且只挂一项；
//      那一项还没填成卡片的（骨架条目），要有一行「你选的 X（详情还在填）」—— 10-09 S-4 就是这样，第一版这里什么都不挂
//   ③ 没核过的条目画虚圈（.dot.unver），不许亮绿
//   ④ 选项里写了的图**真的载进来了**（naturalWidth > 0）：路径写错时页面不报错、只是一张碎图
//   ⑤ 样例模式点「选这个 → 确认」：不发 POST（样例不保存），标签换到新的那一项
//   ⑥ 手机 390：树收成下拉、页面不横向溢出；下拉换条目 ⇒ 详情跟着换
//   ⑧ 原文定／不再适用：状态圈是自己那一档、没有「选这个」（10-09 这 9 条都还没选项，按钮那半要等带选项的出现才真咬得到）
//   ⑨ 子问题（parent）在树上紧跟母条目、缩进，详情里能点回母条目
//   ⑦ 主站顶栏有入口，点了到决策树页；手机上入口不另占一行（顶栏不变高）
// 用法：E2E_URL=<地址> node tools/web_decisions_e2e.js <输出目录>   退出码：0 全过，1 有红，2 跑不了
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = (process.env.E2E_URL || process.argv[2] || '').replace(/\/?$/, '/');
// 不给目录就写仓里的 out/（已 gitignore）——同机几家，不往 /tmp 写（Nova 11:35）
const OUT = process.argv[process.env.E2E_URL ? 2 : 3] || path.join(__dirname, '..', 'out', 'e2e-decisions');
if (!/^https?:/.test(BASE)) { console.log('✗ 没给地址（E2E_URL）'); process.exit(2); }
fs.mkdirSync(OUT, { recursive: true });

const res = [];
const chk = (name, ok, got) => { res.push(ok); console.log(`${ok ? '✓' : '✗'} ${name}${ok ? '' : '　得到：' + JSON.stringify(got)}`); };

(async () => {
  const b = await chromium.launch();
  try {
    const data = await (await fetch(BASE + 'decisions/mock.json')).json();
    const items = data.decisions;
    const ctx = await b.newContext({ viewport: { width: 1400, height: 1000 } });
    const p = await ctx.newPage();
    const errs = []; const posts = [];
    p.on('pageerror', (e) => errs.push(String(e)));
    p.on('request', (r) => { if (r.method() === 'POST') posts.push(r.url()); });
    p.on('dialog', (d) => d.dismiss());
    await p.goto(BASE + 'decisions.html?mock=1', { waitUntil: 'domcontentloaded' });
    await p.waitForSelector('.node');

    // ①
    const ids = await p.$$eval('.node .id', (a) => a.map((x) => x.textContent.trim()));
    chk('① 树的条数 = 数据条数', ids.length === items.length, [ids.length, items.length]);
    const miss = items.map((x) => x.id).filter((x) => !ids.includes(x));
    chk('① 没有一条丢', miss.length === 0, miss.slice(0, 5));

    // ②④：逐条打开有 choice 或有图的
    const open = async (id) => {
      await p.evaluate((id) => [...document.querySelectorAll('.node')].find((n) => n.querySelector('.id').textContent.trim() === id).click(), id);
      await p.waitForFunction((id) => document.querySelector('#detail h2')?.textContent.startsWith(id), id);
    };
    const his = items.filter((x) => x.status && x.status.verified && x.status.kind === '小栋定' && x.status.choice);
    const bad2 = [];
    for (const x of his) {
      await open(x.id);
      const me = await p.$$eval('.opt', (a) => a.filter((o) => o.querySelector('.tagme')).map((o) => o.dataset.key));
      // 选项还没填的（骨架）：卡片上挂不了，就得有那一行「你选的 X（详情还在填）」
      const hasOpt = (x.options || []).some((o) => o.key === x.status.choice);
      const orphan = await p.$eval('#detail', (d) => d.querySelector('.orphan')?.textContent || '');
      const ok = hasOpt ? me.length === 1 && me[0] === x.status.choice : me.length === 0 && orphan.includes(x.status.choice);
      if (!ok) bad2.push([x.id, x.status.choice, me, orphan]);
    }
    chk(`② 小栋定的 ${his.length} 条都挂「你选的」、挂在 status.choice 上、只挂一项`, his.length > 0 && bad2.length === 0, bad2);

    const withFig = items.filter((x) => (x.options || []).some((o) => (o.figures || []).some((f) => typeof f === 'object' && f.src)));
    const broken = [];
    for (const x of withFig) {
      await open(x.id);
      await p.waitForFunction(() => [...document.querySelectorAll('.figs img')].every((i) => i.complete), null, { timeout: 15000 }).catch(() => {});
      const bad = await p.$$eval('.figs img', (a) => a.filter((i) => !i.naturalWidth).map((i) => i.getAttribute('src')));
      broken.push(...bad.map((s) => x.id + ' ' + s));
    }
    chk(`④ ${withFig.length} 条带图的，图都载进来了`, withFig.length > 0 && broken.length === 0, broken);

    // ③
    const unver = items.filter((x) => !(x.status && x.status.verified)).map((x) => x.id);
    const dots = await p.$$eval('.node', (a) => Object.fromEntries(a.map((n) => [n.querySelector('.id').textContent.trim(), n.querySelector('.dot')?.className || ''])));
    const lit = unver.filter((x) => !/\bunver\b/.test(dots[x] || ''));
    chk(`③ 没核过的 ${unver.length} 条都是虚圈`, lit.length === 0, lit.slice(0, 5));

    // ⑧ 原文定／不再适用：只给看，不许有「选这个」
    const ro = items.filter((x) => x.status && x.status.verified && ['原文定', '不再适用'].includes(x.status.kind));
    const roBad = [];
    for (const x of ro) {
      await open(x.id);
      const n = await p.locator('[data-pick]').count();
      const dot = await p.$eval('.status .dot', (d) => d.className);
      const tree = await p.$eval(`.node[data-id="${x.id}"] .dot`, (d) => d.className);   // 树上那颗走 KIND 表，状态行是另一条路，两处都要对
      const want = x.status.kind === '原文定' ? 'fixed' : 'void';
      if (n || !dot.includes(want) || !tree.includes(want)) roBad.push([x.id, n, dot, tree]);
    }
    chk(`⑧ 原文定／不再适用 ${ro.length} 条：状态圈对、没有「选这个」`, roBad.length === 0, roBad);

    // ⑨ 子问题（parent）：树上紧跟母条目、缩进；详情里有回母条目的链接
    const kidsD = items.filter((x) => x.parent && items.some((y) => y.id === x.parent && y.layer_order === x.layer_order));
    const kidBad = [];
    const order = await p.$$eval('.node', (a) => a.map((n) => [n.dataset.id, n.classList.contains('child')]));
    for (const x of kidsD) {
      const i = order.findIndex(([id]) => id === x.id), j = order.findIndex(([id]) => id === x.parent);
      const between = order.slice(j + 1, i).every(([id]) => items.find((y) => y.id === id)?.parent === x.parent);
      await open(x.id);
      const link = await p.$eval('#detail', (d) => d.querySelector('.rel a')?.dataset.go || '');
      if (!(j >= 0 && i > j && between && order[i][1] && link === x.parent)) kidBad.push([x.id, i, j, between, link]);
    }
    chk(`⑨ 子问题 ${kidsD.length} 条：紧跟母条目、缩进、能点回母条目`, kidsD.length > 0 && kidBad.length === 0, kidBad);

    // ⑤
    const x5 = his[0];
    await open(x5.id);
    const other = await p.$$eval('.opt', (a, c) => a.map((o) => o.dataset.key).find((k) => k !== c), x5.status.choice);
    await p.click(`[data-pick="${other}"]`);
    await p.click('#saveBtn');
    if (await p.locator('#impact[open]').count()) await p.click('#impactOk');
    await p.waitForFunction((k) => document.querySelector(`.opt[data-key="${k}"] .tagme`), other);
    const me5 = await p.$$eval('.opt', (a) => a.filter((o) => o.querySelector('.tagme')).map((o) => o.dataset.key));
    chk('⑤ 样例里换选项：标签跟到新的那一项、不发 POST', me5.length === 1 && me5[0] === other && posts.length === 0, { me5, posts });
    chk('页面没有报错', errs.length === 0, errs);
    await ctx.close();

    // ⑥
    const m = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    const mp = await m.newPage();
    await mp.goto(BASE + 'decisions.html?mock=1', { waitUntil: 'domcontentloaded' });
    await mp.waitForSelector('#treeSel option', { state: 'attached' });
    const lay = await mp.evaluate(() => ({ sel: getComputedStyle(document.getElementById('treeSel')).display, tree: getComputedStyle(document.getElementById('tree')).display }));
    await mp.selectOption('#treeSel', his[0].id);
    await mp.waitForFunction((id) => document.querySelector('#detail h2')?.textContent.startsWith(id), his[0].id, { timeout: 5000 }).catch(() => {});
    const h2 = await mp.textContent('#detail h2');
    const ov = await mp.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    chk('⑥ 手机：树收成下拉、下拉换条目详情跟着换、不横向溢出', lay.sel !== 'none' && lay.tree === 'none' && h2.startsWith(his[0].id) && ov <= 0, { lay, h2, ov });
    await mp.screenshot({ path: path.join(OUT, 'decisions_390.png') });
    await m.close();

    // ⑦
    for (const [w, mob] of [[1400, false], [390, true]]) {
      const c = await b.newContext({ viewport: { width: w, height: 800 }, isMobile: mob, hasTouch: mob });
      const q = await c.newPage();
      await q.goto(BASE, { waitUntil: 'domcontentloaded' });
      await q.waitForSelector('a.badge.link');
      const g = await q.evaluate(() => {
        const a = document.querySelector('a.badge.link').getBoundingClientRect();
        const rows = new Set([...document.querySelectorAll('.badges > *')].filter((x) => x !== document.querySelector('a.badge.link') && x.offsetParent).map((x) => Math.round(x.getBoundingClientRect().top)));
        return { top: Math.round(a.top), rows: [...rows], right: a.right, vw: innerWidth };
      });
      chk(`⑦ ${w}：入口跟别的徽章同一行（不另占一行）、在屏内`, g.rows.includes(g.top) && g.right <= g.vw, g);
      if (!mob) {
        await q.click('a.badge.link');
        await q.waitForSelector('#tree');
        chk('⑦ 点入口到决策树页', new URL(q.url()).pathname.endsWith('/decisions.html'), q.url());
      }
      await c.close();
    }
  } catch (e) {
    console.log('✗ 炸了：' + (e && e.message || e).toString().split('\n')[0]);
    await b.close(); process.exit(2);
  }
  await b.close();
  const n = res.filter(Boolean).length;
  console.log(`${n}/${res.length} 过`);
  process.exit(n === res.length ? 0 : 1);
})();
