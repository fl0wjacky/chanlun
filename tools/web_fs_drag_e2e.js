// 拖动以后进/出全屏，视口还在不在**拖过的那一屏**（card-c90f0f08-3ac）
//
// 为什么单开一个：tools/web_measure_e2e.js 的全屏那几格是**没拖过**就进全屏，所以那时 viewSet 正好等于屏上
//   那一屏 —— 修之前它也 69/69 全绿，量不到这个毛病（2026-10-08 实测）。这里先用鼠标真拖一下（真输入，
//   userDrove 认得），再点全屏按钮，比进、出前后的逻辑范围。
// 判据：拖动确实挪了视口（> 20 根，防空转）；进全屏、出全屏各自跟拖完那一屏差 ≤ 1.5 根。桌面和手机两档。
// 牙：把 app.js 的 toggleFs／keepView 改回「viewSet 优先」，桌面跳回 938 根、手机 292 根 ⇒ 红（2026-10-08 实测）。
//
// 跑法（跟 web_measure_e2e.js 一样，要 playwright ＋ 真后台，只绑回环）：
//   python3 web/server.py --port 8792
//   NODE_PATH=<装了 playwright 的 node_modules> node tools/web_fs_drag_e2e.js [页面地址]
const { chromium } = require('playwright');
const PAGE = (process.env.E2E_URL || process.argv[2] || 'http://127.0.0.1:8792/').replace(/\/?$/, '/');
(async () => {
  const b = await chromium.launch(); let bad = 0;
  for (const [dev, o] of [['桌面 1440', { viewport: { width: 1440, height: 900 } }],
                          ['手机 390', { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true }]]) {
    const c = await b.newContext(o); const p = await c.newPage(); const errs = []; p.on('pageerror', (e) => errs.push(e.message));
    await p.goto(`${PAGE}?symbol=ZECUSDT&tf=15m`, { waitUntil: 'load' });
    await p.waitForFunction(() => { const s = window.__app && window.__app.state; return s && s.data && s.data.bars.length > 100; }, null, { timeout: 90000 });
    await p.waitForTimeout(2500);
    const rng = () => p.evaluate(() => { const r = window.__app.chart.timeScale().getVisibleLogicalRange(); return r && [r.from, r.to]; });
    const box = await p.locator('#chart').boundingBox();
    const y = box.y + box.height * 0.4;
    await p.mouse.move(box.x + box.width * 0.3, y); await p.mouse.down();
    await p.mouse.move(box.x + box.width * 0.75, y, { steps: 12 }); await p.mouse.up();
    await p.waitForTimeout(1200);
    const r0 = await rng();
    await p.locator('#fs').click(); await p.waitForTimeout(1500); const rin = await rng();
    await p.locator('#fs').click(); await p.waitForTimeout(1500); const rout = await rng();
    const d = (a, b2) => Math.max(Math.abs(a[0] - b2[0]), Math.abs(a[1] - b2[1]));
    const start = r0;   // 拖完那一屏
    const ok = rin && rout && d(start, rin) <= 1.5 && d(start, rout) <= 1.5 && !errs.length;
    const dragged = start && start[1] < (await p.evaluate(() => window.__app.state.data.bars.length)) - 20;
    if (!dragged) { console.log(`  ✗ ${dev}：拖动没挪动视口（空转，这一格量不到东西）`); bad++; }
    else if (!ok) { console.log(`  ✗ ${dev}：拖完 [${start.map((v) => v.toFixed(1))}] → 进全屏差 ${d(start, rin).toFixed(1)} 根、出全屏差 ${d(start, rout).toFixed(1)} 根（要 ≤ 1.5）${errs.length ? '　页面错：' + errs[0] : ''}`); bad++; }
    else console.log(`  ✓ ${dev}：拖完 [${start.map((v) => v.toFixed(1))}]，进全屏差 ${d(start, rin).toFixed(1)} 根、出全屏差 ${d(start, rout).toFixed(1)} 根`);
    await c.close();
  }
  await b.close();
  console.log(bad ? `${bad} 格红` : '全过'); process.exit(bad ? 1 : 0);
})();
