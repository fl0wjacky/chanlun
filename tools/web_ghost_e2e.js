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
//      ⑮c 是**上线那一刻**：前一趟没有 engine、后一趟有（Bram 补的）—— 缺字段是独立的桶值，不是"跟谁都相等"。
//   ⑯ **实时跳价只动最后一根**（card-f3fffac4-83d，小栋 10-05 A）：最后一根的价跟着后台的 `/api/tick` 跳，
//      而「结构」（笔／线段／买卖点）和**已收盘的 K 线**一个字节都不许动、不触发空心点记账、也不顺手去重取。
//      `t` 比图上新（那一根已经收盘）⇒ 什么都不动，交给已有的自动重取；后台拉不到 ⇒ 价停住、页头写
//      「价格停在 HH:MM」；切到后台一趟都不取、切回来立刻补一趟。★ 跳价那几张页面的 /api/chart
//      每一趟都吐同一份（见 plan()）—— 不然"什么都没动"就分不出是跳价守住了还是别的原因。
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
const PAGE = (process.env.E2E_URL || process.argv[3] || 'http://127.0.0.1:8796/').replace(/\/?$/, '/');   // E2E_URL 优先（上线门统一给，card-9b0fe913-758）
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
  // 真后台的 `/api/meta` 原件（⑰h 拿它跟**页面**对账 —— 那一页只吃这一份，不吃假后台那份）。
  const RMETA = await (await fetch(`${PAGE}api/meta`)).json();

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
    // ⑮：引擎版本（后台带在 /api/chart 顶层那个字段）。用 `in` 不用真值判断 —— 「这一份**没有** engine」
    //   是一个要显式摆出来的状态（`engine: null`），不能靠"底那份刚好没有"（那样换成带 engine 的后台就假红）。
    if ('engine' in opt) d.engine = opt.engine;
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
  /** ⑰：一刀 `status=pending` 的切点 ＋（可选）「切开会变成的那两个框」。挑**最靠右**那个线段中枢
   *  —— 它一定落在最近这一段窗口里（工装把视口摆在哪儿都看得见）。取框、取 bar 的算法跟 layers.js
   *  的 `boxes()` **同一个出处**（host ＝ 已完成线段、`i0 = host[PI0].i0`、`i1 = host[PI1].i1`），
   *  这样"切点在框里"这件事不是工装自己编的。`boxes` 里的两个小框按 Bram 的契约拼：PI 指向
   *  已完成线段那一份，左边那个到切点为止、右边那个从切点起（右边那个就是「随切点」说的那种）。 */
  const mkCut = (d, withBoxes, edge) => {
    const done = (d.segs || []).filter((s) => !s.live);
    const zs = d.seg_centers || [];
    for (let n = zs.length - 1; n >= 0; n--) {
      const z = zs[n];
      const a = done[z.PI0], b = done[z.PI1];
      if (!a || !b || !(z.PI1 > z.PI0 + 1)) continue;      // 至少要三根成员才锯得开
      // ★ 切点得是**真的线段端点**（Bram 的 core/cut.py：`ends[k]` = 第 k 段的起点，`cut_bar = ends[k]`）。
      //   拿"框的中点那一根 bar"当刀，两个临时框的缝和切点竖线就落在两个地方 —— 屏上看着像两件事，
      //   而且这一格自己算出来的期望值也会跟着偏（第一版模子就是这么错的）。
      const mid = z.PI0 + 1 + Math.floor((z.PI1 - z.PI0) / 2);
      // ★ `edge`：切点**正好压在框的右沿**上（＝线上 ZEC 15m 那一刀：`cut_bar=19911`、框 19698..19911）。
      //   这种刀不改这个框、改的是它后面那一组从哪儿重算（Bram/Atlas 10-05）⇒ **只画线、不挂「待定」**
      //   （Nova 10-05 08:58 拍的）。工装必须能造出这个形状，否则这条规则没有尺子量。
      //   取 `done[z.PI1].i1` ＝ 框的右端（`boxes()` 里 `i1 = host[PI1].i1`，同一个出处）。
      const bar = edge ? done[z.PI1].i1 : done[mid].i0;
      const c = { cut_bar: bar, by: '笔·三买', level: 'seg', status: 'pending' };
      if (withBoxes) {
        // ★ 真引擎给的是**整组**的框，不只被切的那一个（`cut_centers`：`prev <= PI0 < next` 全收）——
        //   线上那一刀就是这样：两个临时框里有一个跟旧框**一模一样**（组里没被切到的那个）。
        //   把这个形状照抄进来，才能量到「同一组的框换上去、不许叠着画两遍」这件事（⑰i）。
        const pv = n > 0 ? zs[n - 1] : null;
        const okPv = pv && done[pv.PI0] && done[pv.PI1];
        c.boxes = [...(okPv ? [{ ...pv }] : []),
                   { ...z, PI0: z.PI0, PI1: mid - 1 }, { ...z, PI0: mid, PI1: z.PI1 }];
      }
      return c;
    }
    return null;
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
    // ⑯：跳价那几张页面的 /api/chart **每一趟都吐同一份全给**（跟 'same' 一个道理）：那一套量的是
    //   "跳价只动最后一根"，图上要是同时还有点在一个个少，"什么都没动"就分不出是谁的功劳了。
    if (which.startsWith('tick')) return NOTHING;
    // ⑰ 切法那几张：每一趟都吐同一份（这一套量的是开关和画法，不是记账；
    //   图片在动的话"屏上多了/少了一笔"就分不出是谁的功劳）。
    if (which === 'nocut' || which.startsWith('cut')) return NOTHING;
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
    // ⑮c：**上线那一刻**（Bram 10-05 补的那条）。线上后台现在**没有**这个字段，加上的那一瞬间，
    //   开着的页面从「没有 engine」变成「有 engine」—— 这本身**就是一次换引擎**。
    //   ⇒「缺字段」必须是**独立的桶值**（`''`），不能当成「跟谁都相等」，否则第一次上线就踩你要防的那个坑。
    if (which === 'engmiss') {
      return i <= 1 ? { opt: { engine: null } } : { drop: D_ROUND, opt: { engine: ENG1, grow: true } };
    }
    return { drop: i < SEQ.length ? SEQ[i] : new Set() };
  };

  // ⑯：跳价那一路的假后台。真后台那一半是 Bram 的 `agent/bram/live-tick`（38938b2），契约：
  //   `{symbol, tf, t, o, h, l, c, v, fetched_at, stale, engine}`，`t` ＝ 那根的**开盘时间**。
  //   ★ 收价在 [低, 高] **里面**动（五个值轮着来）：价格轴一点都不会被撑动 —— 不然"已收盘那根一个
  //     像素没动"那一格，会被我们自己把整幅图挪了而假红。
  const TICK_BASE = base.bars[base.bars.length - 1];
  const tickC = (k) => TICK_BASE.l + (TICK_BASE.h - TICK_BASE.l) * (0.2 + 0.1 * (k % 5));
  const tickBody = (which, k, shift) => {
    const t = TICK_BASE.t + shift;            // ＝图上最后一根的开盘时间（工装把整份数据平移过）
    const good = (fetched, kk) => ({ symbol: base.symbol, tf: base.tf, t, o: TICK_BASE.o, h: TICK_BASE.h,
                                     l: TICK_BASE.l, c: tickC(kk), v: TICK_BASE.v,
                                     fetched_at: fetched, stale: false, engine: ENG1 });
    // ⑯k：跳价**在飞的那两秒里换了品种**（Atlas 10-05 的建议）。这一趟回的是**老品种**的价，收价给一个
    //   一眼认得出的离谱值（真动了就看得见）；而它的 `t` 与新图上最后一根**一模一样**（同周期、同一份平移）
    //   —— 所以能挡住它的**只有**「symbol/tf 对不上就不动」那道闸。拆掉那道闸，这一格必须红。
    if (which === 'tickslow') return { ...good('2026-10-05T03:41:00.000Z', 1), c: TICK_BASE.c + 500 };
    // ⑯f：后台说**这一根已经收盘、新的一根开盘了**（t 比图上新）⇒ 页面该一个字都不动
    //   （收盘那一刻交给已有的自动重取）。收价给个一眼认得出的离谱值：真动了就看得见。
    if (which === 'tickroll') {
      return { ...good('2026-10-05T03:41:00.000Z', 0), t: t + STEP_MS, c: TICK_BASE.c + 500 };
    }
    // ⑯g：前两趟好着，之后后台**拉不到币安**了 ⇒ 回上一次的值 ＋ stale=true ＋ fetched_at
    //   **冻在**上次成功那一刻（03:41）。页面该：价停住、页头写「价格停在 03:41」、角上认账。
    if (which === 'tickstale' && k >= 3) return { ...good('2026-10-05T03:41:00.000Z', 2), stale: true };
    return good('2026-10-05T03:41:00.000Z', k);
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
               || which === 'engsame' || which === 'engine' || which === 'engmiss';
    const shift = (soon ? NOWP - STEP_MS + 3000 : NOWP) - lastT;      // soon：还差 3 秒收盘
    const reqAt = [];                                                 // 每次取数的时刻（⑬ 量错峰用）
    // ⑰：切法那几张页面（card-e346ede6-996）。控件是**名单驱动**的（`/api/meta` 的 `cut_modes`）——
    //   名单到没到，在这一层由工装说了算：`nocut` 那页量的是「名单没到 ⇒ 不画控件、也不发参数」，
    //   ⑰b–⑰g 那几张量的是名单到了之后的事。
    //   ★ 假后台只动这一个键，别的字段全是真后台的 —— 免得"控件出现了"这件事被别的东西带偏。
    //   ★ 这一层假后台**所有页面都挂**，而且默认把 `cut_modes` **拿掉**，只有切法那几张（⑰b–⑰g）才把它造出来。
    //     为什么非得"所有页面"：Bram 的 server.py 合进 main 之后，真后台**每一项都带 cut_modes** ⇒
    //     不挡的话别的格子（④c 量图高、⑤ 量那一小块）会凭空多出一排 chip，量的东西当场就不是原来那个了。
    //     工装得**合并前后都能跑**：「名单到没到」这件事在这里由我们说了算，不由碰巧连到哪个后台说了算。
    //   ★ `cutreal` 那一页**不挂**（⑰h 要的就是真后台那份原件，见那一格）。
    if (which !== 'cutreal') {
      await p.route('**/api/meta', async (route) => {
        const m = await (await fetch(`${PAGE}api/meta`)).json();
        if (which.startsWith('cut')) m.cut_modes = ['extend', 'turn'];
        else delete m.cut_modes;
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(m) });
      });
    }
    // ⑰：画布上**真画出来的东西**的一份记录。这一卡要量的两样（「待定」那枚签、切点那条竖虚线）
    //   都是**画出来的**、不落在任何 DOM 上 —— 只能从 ctx 这一层认。★ 只记不改行为（包一层转发）。
    //   `vseg` 只记**竖着的那一段**（x 不变、y 跨 4px 以上）＋ 落笔那一刻的虚线样式：
    //   切点那条线就是这个形状，而它的高度必须＝包住它的那个旧框的 ZD…ZG（Bram 10-05 的契约）。
    await p.addInitScript(() => {
      const proto = CanvasRenderingContext2D.prototype;
      const fx = { text: [], vseg: [] };
      Object.defineProperty(window, '__fx', { value: fx, configurable: true });
      const FT = proto.fillText;
      proto.fillText = function (t, x, y) {
        try { fx.text.push({ t: String(t), x: Math.round(x), y: Math.round(y),
                             font: String(this.font || '') }); } catch (e) {}
        return FT.apply(this, arguments);
      };
      const BP = proto.beginPath, MV = proto.moveTo, LN = proto.lineTo, ST = proto.stroke;
      proto.beginPath = function () { this.__seg = null; return BP.apply(this, arguments); };
      proto.moveTo = function (x, y) { this.__mv = [x, y]; return MV.apply(this, arguments); };
      proto.lineTo = function (x, y) { const m = this.__mv;
        if (m) this.__seg = [m[0], m[1], x, y]; return LN.apply(this, arguments); };
      proto.stroke = function () {
        try {
          const s = this.__seg;
          if (s && Math.abs(s[0] - s[2]) < 0.01 && Math.abs(s[1] - s[3]) > 4) {
            fx.vseg.push({ x: Math.round(s[0]), y0: Math.round(Math.min(s[1], s[3])),
                           y1: Math.round(Math.max(s[1], s[3])),
                           dash: Array.from(this.getLineDash ? this.getLineDash() : []) });
          }
        } catch (e) {}
        return ST.apply(this, arguments);
      };
    });
    const cutReq = [];                                                // 每次取数**带没带** `cut`、带的是哪个
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
      // ⑰ 切法（card-e346ede6-996）。Bram 那一半的契约：请求带 `cut`、**顶层回显** `cut`、
      //   `cuts[]` 报每一刀（`cut_bar` / `by` / `level` / `status`，`boxes` 只挂在 pending 上）。
      //   假后台照抄这个形状 —— 页面读的是**回显**，不是它自己点的那颗 chip（⑰c 就量这一条）。
      const wantCut = u.searchParams.get('cut');
      cutReq.push(wantCut);
      //   ★ 「回显撒谎」那一页是**故意的**：真后台不会这样，但契约里"回显是唯一的真相"这句话
      //     只有在回显与请求不一致时才量得出来（一致的话，跟"照点击画"永远分不开）。
      body.cut = which === 'cutlie' ? 'extend' : (wantCut || 'extend');
      if (which === 'cutvoid') {
        const c = mkCut(body, true);
        if (c) body.cuts = [{ cut_bar: c.cut_bar, by: '笔·三买', level: 'seg', status: 'done' },
                            { cut_bar: c.cut_bar + 12, by: '笔·三买', level: 'seg', status: 'void' }];
      } else if (which === 'cutturn' || which === 'cutpv' || which === 'cutedge') {
        const c = mkCut(body, which === 'cutpv', which === 'cutedge');
        if (c) body.cuts = [c];
      }
      // ⑯k：这一页认 `symbol` 入参 —— 换品种之后**手上那份数据的 symbol 真变了**（真后台本来就该这样）。
      //   不认的话，"换品种"在页面看来什么都没发生，那一格就成了空转（而且是看不出来的空转）。
      if (which === 'tickslow') body.symbol = u.searchParams.get('symbol') || body.symbol;
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    });
    // ⑯ 跳价那一路：**所有**页面都挂上（页面自己每 5 秒就会来问一次）。
    //   · 跳价那几张吐上面那份；
    //   · 'tick503' 那页吐 **503**（后台从来没取成功过 —— 这一颗还没有任何可用的价）；
    //   · 别的页面吐一份**正常但"不是我们手上那根"**的（t 比图上新 7 根）：这是**真会发生**的一种
    //     ——我们手上那份旧了。页面照样该一个字都不动（t 对不上就不许就地换）。
    //     ★ 别拿 404 当默认：浏览器会把每一条 404 记成 console error，5 秒一条，日志当场被刷满。
    // ★ n 在**请求进来那一下**就加（不是回完才加）：⑯k 要的就是"还在飞"这个中间态，靠它才看得见。
    //   done/doneAt 是**回完**那一下 —— ⑯k 用它证「那一趟落地的时候新图已经画上了」。
    const tick = { n: 0, done: 0, doneAt: 0, reqAt: [] };
    await p.route('**/api/tick*', async (route) => {
      tick.n++;
      tick.reqAt.push(Date.now());
      if (which === 'tick503') { await route.fulfill({ status: 503, body: 'never fetched' }); return; }
      // ⑯k：这一页的跳价**扣在手里 2 秒**才回 —— 要的就是"响应还在飞"的那一段（真网络抖一下就有，
      //   不是编出来的）：这 2 秒里把品种换掉，看那一趟回来会不会动**新图**的最后一根。
      if (which === 'tickslow') await sleep(2000);
      const body = which.startsWith('tick') ? tickBody(which, tick.n, shift)
                                            : { ...tickBody('tick', tick.n, shift), t: TICK_BASE.t + shift + 7 * STEP_MS };
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
      tick.done++; tick.doneAt = Date.now();
    });
    await p.goto(PAGE + qs, { waitUntil: 'domcontentloaded' });
    await p.waitForFunction(() => window.__app && window.__app.state && window.__app.state.data, null, { timeout: 60000 });
    await sleep(1200);                     // 等 /api/meta 那一趟（控件由它驱动）
    return { c, p, hits, reqAt, tick, cutReq, closeAt: NOWP + 3000 };
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
             // ⑯k：手上这份是**哪个品种**（换品种那一格要证"屏上真的已经是新的那份了"）＋ 数据那侧的最后一根
             symbol: d.symbol,
             lastBar: (d.bars && d.bars.length) ? { ...d.bars[d.bars.length - 1] } : null,
             lastTxt: (document.getElementById('last') || {}).textContent || '',
             updated: (document.getElementById('updated') || {}).textContent || '',
             // 「画在图上」的最后一根：读的是**系列自己**那份数据（跟十字线读数同一个出处，不是读 state）
             drawn: (() => { const a = window.__app.chart.panes()[0].getSeries()[0].data();
                             return a && a.length ? { ...a[a.length - 1] } : null; })(),
             // 同一根、用**页面自己那个格式器**印一遍（⑯b 比字不比数：工装不四舍五入）
             drawnTxt: (() => { const a = window.__app.chart.panes()[0].getSeries()[0].data();
                                return a && a.length
                                  ? window.__app.fmtPrice(a[a.length - 1].close, d.meta && d.meta.tick) : ''; })(),
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

  /** ⑯ 第 i 根 K 线在**屏上**占的那一小块（走图自己的 logicalToCoordinate/priceToCoordinate —— 跟记号
   *  那一套同一个出处）。★ 给的是**K 线那一根**（高→低那一竖条的宽度），不是记号。 */
  const barBox = async (p, i) => {
    const box = await p.locator('#chart').boundingBox();
    return p.evaluate(([i, box]) => {
      const b = window.__app.state.data.bars[i];
      if (!b) return null;
      const ch = window.__app.chart, ts = ch.timeScale(), s0 = ch.panes()[0].getSeries()[0];
      const x = ts.logicalToCoordinate(i), y1 = s0.priceToCoordinate(b.h), y2 = s0.priceToCoordinate(b.l);
      if (x === null || y1 === null || y2 === null) return null;
      const top = Math.min(y1, y2), bot = Math.max(y1, y2);
      return { x: Math.round(box.x + x - 3), y: Math.round(box.y + top - 1),
               w: 6, h: Math.max(3, Math.round(bot - top + 2)) };
    }, [i, box]);
  };
  /** 那一小块像素的**指纹**（每张画布都读，FNV 走一遍）。判"一个像素都没动"用它 ——
   *  ★ 只覆盖给的那一块，别拿它当"整幅图没变"的判据。`ink` ＝ 落了墨的点数（诊断用）。 */
  const pxHash = (p, bx) => p.evaluate((bx) => {
    if (!bx) return { h: null, ink: 0, hit: 0 };
    const cvs = [...document.querySelectorAll('#chart canvas')].map((c) => ({ c, r: c.getBoundingClientRect() }));
    let h = 0x811c9dc5, ink = 0, hit = 0;
    for (const { c, r } of cvs) {
      const x = Math.round(bx.x - r.left), y = Math.round(bx.y - r.top);
      if (x < 0 || y < 0 || x + bx.w > c.width || y + bx.h > c.height) continue;
      hit++;
      const px = c.getContext('2d').getImageData(x, y, bx.w, bx.h).data;
      for (let i = 0; i < px.length; i += 4) {
        if (px[i + 3] > 24) ink++;
        h ^= px[i]; h = Math.imul(h, 0x01000193); h ^= px[i + 1]; h = Math.imul(h, 0x01000193);
        h ^= px[i + 2]; h = Math.imul(h, 0x01000193); h ^= px[i + 3]; h = Math.imul(h, 0x01000193);
      }
    }
    return { h: (h >>> 0).toString(16), ink, hit };
  }, bx);
  /** ⑯：把视口摆成「最后一根贴着右沿」（用户平时看的样子 —— `park` 是 ±150 收在中间）。 */
  const tickPark = async (p, i) => {
    await p.evaluate((n) => window.__app.chart.timeScale().setVisibleLogicalRange({ from: n - 160, to: n + 8 }), i);
    await sleep(700);
  };
  /** 结构那一层（笔／线段／买卖点／账本）＋**已收盘那一段 K 线**的指纹：一串 JSON 的 FNV。
   *  ★ 不是"看着差不多"：跳价只许动 bars 的**最后一根**，这几样一个字节都不许变（卡上 ①⑤ 两条）。 */
  const structHash = (p) => p.evaluate(() => {
    const d = window.__app.state.data;
    const fp = (x) => { const s = JSON.stringify(x); let h = 0x811c9dc5;
      for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193); }
      return s.length + ':' + (h >>> 0).toString(16); };
    return { pens: fp(d.pens), segs: fp(d.segs), signals: fp(d.signals), ghosts: fp(d.ghosts || []),
             head: fp(d.bars.slice(0, -1)), nBars: d.bars.length };
  });
  /** 页头那一格里的**那串字**（摘掉「最新 」和「｜ 价格停在 …」的尾巴）—— 跟图上那份比，比的是字。 */
  // ★ 工装里**不许再四舍五入一遍**：`toFixed` 看的是二进制真值、页面用的 `toLocaleString` 看的是最短十进制，
  //   `1313.995` 这种正落在半个末位上的值两边差一分 ⇒ 判据在**没事**的时候红（m16 那一刀就这么假红过 ⑯b）。
  //   两边都由页面自己那个格式器印（`window.__app.fmtPrice`），工装只比字、一次都不算。
  const bare = (s) => String(s || '').replace(/^最新\s*/, '').split('｜')[0].trim();

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

  // ⑮c **上线那一刻**（Bram 10-05 补）：线上现在没有 engine，加上的那一瞬间，开着的页面从「没有」
  //   变成「有」—— 这本身就是一次换引擎。缺字段要当**独立的桶值**，不能当「跟谁都相等」。
  const ET = await open('engmiss');
  const et = ET.p;
  await et.locator('.chip[data-key="sig"]').click();
  const et0 = await snap(et);                                  // 打开那趟：这份**没有** engine
  { const t = Date.now(); while (ET.hits.macd < 2 && Date.now() - t < 40000) await sleep(500); }
  await sleep(1500);
  const et1 = await snap(et);
  ck('⑮c 上线那一刻：前一趟不带 engine、后一趟带 ⇒ **一个都不许报**（缺字段是独立的桶值，不是"跟谁都相等"）',
     et0.eng == null && et1.eng === ENG1 && et1.ghosts.length === 0 && (!et1.gc || !et1.gc.on),
     `引擎 ${et0.eng === null ? '（没有这个字段）' : et0.eng} → ${et1.eng}｜页面报 ${et1.ghosts.length} 个`
     + `｜那一格：「${et1.gc ? et1.gc.txt : '（没有）'}」`);

  // ---- ⑯ 实时跳价：只动最后一根（card-f3fffac4-83d，小栋 10-05 A）
  console.log('\n16 实时跳价：只动最后一根 —— 已收盘的 K 线和结构层一个字节都不许动（card-f3fffac4-83d）');
  const eq = (a, b) => a != null && b != null && Math.abs(a - b) < 1e-9;
  const LASTI = base.bars.length - 1;
  const TICKVALS = [1, 2, 3, 4, 5].map(tickC);
  // 结构记号那一块：挑**靠尾巴**的一个已确认点（真数据 bar<200 没有点，尾巴上该有 —— 挑不到就报出来，
  // 别让那一格变成"空转格"）。★ 离最后一根留出 4 根：记号那一块横着能盖住两三根，别蹭到要动的那一根。
  const tailPts = ['seg', 'pen'].flatMap((tier) => ((base.signals || {})[tier] || []).map((s) => ({ ...s, tier })))
                  .filter((s) => s.confirmed === true && s.bar > LASTI - 140 && s.bar <= LASTI - 4);
  const NEAR = tailPts[tailPts.length - 1];

  const TK = await open('tick');
  const tp = TK.p;
  await tp.locator('.chip[data-key="sig"]').click();       // 买卖点那一层开着：⑤ 要量的正是它记不记账
  await tickPark(tp, LASTI);
  await sleep(1500);
  const k0 = await snap(tp);
  const sh0 = await structHash(tp);
  const closedBox = await barBox(tp, LASTI - 4);
  const cl0 = await pxHash(tp, closedBox);
  const nbBox = NEAR ? await boxAt(tp, NEAR) : null;
  const nb0 = nbBox ? await pxHash(tp, nbBox) : null;
  { const t = Date.now(); while (TK.tick.n < 3 && Date.now() - t < 40000) await sleep(400); }
  await sleep(800);
  const k1 = await snap(tp);
  const sh1 = await structHash(tp);
  const cl1 = await pxHash(tp, closedBox);                 // ★ 仍用**原来那个框**：位置动一点都会变
  const nb1 = nbBox ? await pxHash(tp, nbBox) : null;

  ck('⑯a 跳价真的落在**画在图上**的那一根上（先证明这一套在这张页面上工作，否则下面几格全是空转）',
     TK.tick.n >= 3 && !!k1.drawn && !eq(k1.drawn.close, k0.drawn.close)
       && TICKVALS.some((v) => eq(v, k1.drawn.close)),
     `跳价 ${TK.tick.n} 趟｜图上最后一根的收价 ${k0.drawn && k0.drawn.close} → ${k1.drawn && k1.drawn.close}`);
  ck('⑯b 页头那个价跟**画在图上**的**是同一个数**（接线接对了，不是各写各的）',
     !!k1.drawnTxt && bare(k1.lastTxt) === k1.drawnTxt,
     `图上那一根印出来「${k1.drawnTxt}」（原值 ${k1.drawn && k1.drawn.close}）｜页头「${k1.lastTxt}」`);
  ck('⑯c 已收盘的 K 线**一个字节都不许改**：那一段 JSON 的指纹一样 ＋ 那一根那块像素一样',
     sh0.head === sh1.head && cl0.h === cl1.h && cl0.ink > 0,
     `已收盘那段 ${sh0.head} → ${sh1.head}｜第 ${LASTI - 4} 根那块 ${cl0.h}/${cl0.ink}点墨 → ${cl1.h}/${cl1.ink}点墨`);
  ck('⑯d 结构那一层（笔／线段／买卖点）**一个字节**都没动 —— 结构仍然收盘才重算',
     sh0.pens === sh1.pens && sh0.segs === sh1.segs && sh0.signals === sh1.signals,
     `笔 ${sh0.pens} → ${sh1.pens}｜线段 ${sh0.segs} → ${sh1.segs}｜买卖点 ${sh0.signals} → ${sh1.signals}`);
  ck('⑯d2 那个买卖点记号那一块**像素一模一样**（不是"数据没变"，是屏上真没动）',
     !!nb0 && !!nb1 && nb0.h === nb1.h && nb0.ink > 0,
     NEAR ? `${NEAR.tier}|${NEAR.kind}@${NEAR.bar} 那块 ${nb0 && nb0.h}/${nb0 && nb0.ink}点墨 → ${nb1 && nb1.h}/${nb1 && nb1.ink}点墨`
          : '★ 尾巴 140 根里没挑到已确认的点 —— 这一格**没量到东西**');
  ck('⑯e 跳价**不触发空心点记账**：账本空着、那一格没亮 ＋ `/api/chart` 还是 1 趟（没顺路去重取）',
     k1.ghosts.length === 0 && sh1.ghosts === sh0.ghosts && k1.gc.txt === '' && !k1.gc.on
       && (TK.hits.macd || 0) === 1,
     `账本 ${k1.ghosts.length} 个｜那一格「${k1.gc.txt}」(on=${k1.gc.on})｜chart 取数 ${JSON.stringify(TK.hits)}`
     + `｜跳价 ${TK.tick.n} 趟`);

  // ⑯i：十字线停在最后一根上 ⇒ 读数也得跟着跳（图上在动、块里冻着，两个数指着同一根 K 线就是一句谎）
  const cbx = await tp.locator('#chart').boundingBox();
  // 指针**真的**移到最后一根那一列上（走鼠标这条路，不是直接调 API 摆十字线）
  const lastX = await tp.evaluate(() => {
    const ch = window.__app.chart, d = window.__app.state.data;
    return document.getElementById('chart').getBoundingClientRect().x
         + ch.timeScale().logicalToCoordinate(d.bars.length - 1);
  });
  await tp.mouse.move(lastX, cbx.y + cbx.height / 2);
  await sleep(700);
  // 四样**一次读完**（读数那个数、页头那个数、图上那个数）—— 分几次读，中间落进来一趟跳价就又对不上了。
  const rd = (pp) => pp.evaluate(() => {
    const a = window.__app.chart.panes()[0].getSeries()[0].data();
    return { on: document.getElementById('readout').classList.contains('on'),
             time: (document.getElementById('ro-time') || {}).textContent || '',
             cTxt: (document.getElementById('ro-close') || {}).textContent || '',
             badgeTxt: String((document.getElementById('last') || {}).textContent || '')
                         .replace(/^最新\s*/, '').split('｜')[0].trim(),
             drawnTxt: window.__app.fmtPrice(a[a.length - 1].close,
                                            window.__app.state.data.meta && window.__app.state.data.meta.tick),
             drawn: a[a.length - 1].close };
  });
  const rd0 = await rd(tp);
  { const t = Date.now(); while (TK.tick.n < 5 && Date.now() - t < 40000) await sleep(400); }
  await sleep(800);
  const rd1 = await rd(tp);
  ck('⑯i 十字线停在最后一根上 ⇒ 读数跟着跳（图上在动、块里冻着就是一句谎）',
     rd0.on && rd1.on && rd0.time === rd1.time && rd1.cTxt !== rd0.cTxt
       && rd1.cTxt === rd1.drawnTxt && rd1.cTxt === rd1.badgeTxt,
     `读数 ${rd0.on ? '亮着' : '没亮'}｜同一根 ${rd0.time}｜收价 ${rd0.cTxt} → ${rd1.cTxt}`
     + `（页头 ${rd1.badgeTxt}、图上印出来 ${rd1.drawnTxt}｜原值 ${rd1.drawn}）`);

  // ⑯h：切到后台一趟都不取，切回来立刻补一趟（跟自动重取同一条口径）
  await setVisible(tp, 'hidden');
  await sleep(900);                                       // 等在飞的那一趟落地，再数
  const hv0 = TK.tick.n;
  await sleep(12000);                                     // 两个半周期
  const hv1 = TK.tick.n;
  await setVisible(tp, 'visible');
  await sleep(2500);
  ck('⑯h 切到后台**一趟都不取**；切回来**立刻**补一趟（跟自动重取同一条口径）',
     hv1 === hv0 && TK.tick.n > hv1,
     `切后台前 ${hv0} 趟 → 12 秒后 ${hv1} 趟（该一样）→ 切回来 ${TK.tick.n} 趟`);

  // ⑯f：`t` 比图上新（那一根已经收盘、新的一根开盘了）⇒ 页面一个字都不动，交给已有的自动重取
  const TR = await open('tickroll');
  const rp = TR.p;
  await sleep(1200);
  const rl0 = await snap(rp);
  const rH0 = await structHash(rp);
  { const t = Date.now(); while (TR.tick.n < 2 && Date.now() - t < 30000) await sleep(400); }
  await sleep(800);
  const rl1 = await snap(rp);
  const rH1 = await structHash(rp);
  ck('⑯f 后台说**新的一根已经开盘**（t 比图上新）⇒ 一个字都不动（收盘那一刻交给已有的自动重取）',
     TR.tick.n >= 2 && rl1.nBars === rl0.nBars && rH0.head === rH1.head
       && rl1.drawn.time === rl0.drawn.time && eq(rl1.drawn.close, rl0.drawn.close)
       && !/价格停在/.test(rl1.lastTxt),
     `跳价 ${TR.tick.n} 趟（每趟都说 t 比图上新）｜K 线 ${rl0.nBars} → ${rl1.nBars} 根｜图上最后一根 `
     + `${rl0.drawn.time} → ${rl1.drawn.time}｜收价 ${rl0.drawn.close} → ${rl1.drawn.close}`);

  // ⑯g：后台拉不到新的 ⇒ 价**停住**，页头写出来停在哪一刻；角上也得认账
  const TS = await open('tickstale');
  const stp = TS.p;
  await sleep(1200);
  { const t = Date.now(); while (TS.tick.n < 4 && Date.now() - t < 40000) await sleep(400); }
  await sleep(800);
  const g1 = await snap(stp);
  { const t = Date.now(); while (TS.tick.n < 6 && Date.now() - t < 40000) await sleep(400); }
  await sleep(800);
  const g2 = await snap(stp);
  ck('⑯g 后台拉不到新的（stale=true、fetched_at 冻住）⇒ 价**停住**，页头写出来停在哪一刻',
     TS.tick.n >= 6 && eq(g1.drawn.close, tickC(2)) && eq(g2.drawn.close, g1.drawn.close)
       && /价格停在 03:41/.test(g2.lastTxt),
     `跳价 ${TS.tick.n} 趟｜图上收价 ${g1.drawn.close} → ${g2.drawn.close}（该停在第 2 趟那个 ${tickC(2)}）`
     + `｜页头「${g2.lastTxt}」`);
  ck('⑯g2 价停住的时候角上也得承认（`★ 旧数据`），而且「数据 … 刷新」印的**必须**是后台冻住的那个时刻',
     /旧数据/.test(g2.updated) && /数据 2026-10-05 03:41 刷新/.test(g2.updated), `角上「${g2.updated}」`);

  // ⑯j：后台**从来没取成功过**（503）⇒ 屏上那份一个字都不改，页头也不许编一个"停在几点"
  const T5 = await open('tick503');
  const np = T5.p;
  await sleep(1200);
  const p0 = await snap(np);
  const ph0 = await structHash(np);
  { const t = Date.now(); while (T5.tick.n < 2 && Date.now() - t < 30000) await sleep(400); }
  await sleep(800);
  const p1 = await snap(np);
  const ph1 = await structHash(np);
  ck('⑯j 后台**从来没成功过**（503）⇒ 屏上一个字都不改，也不编一个「停在几点」给它',
     T5.tick.n >= 2 && eq(p1.drawn.close, p0.drawn.close) && ph0.head === ph1.head
       && /^最新 /.test(p1.lastTxt) && !/价格停在|价格停了/.test(p1.lastTxt),
     `跳价 ${T5.tick.n} 趟全 503｜图上收价 ${p0.drawn.close} → ${p1.drawn.close}｜页头「${p1.lastTxt}」`);

  // ⑯k：跳价**在飞的时候换品种**（Atlas 10-05 的建议）。那一趟回来时屏上已经是**另一个品种**的图，
  //   它带的是老品种的价，`t` 又跟新图上最后一根**完全一致** —— 能挡住它的只有 symbol/tf 那道闸。
  //   ★ 假后台认 `symbol` 入参（见 chart 路由）：不认的话"换品种"在页面看来什么都没发生 = 空转。
  const SL = await open('tickslow', QS);
  const slp = SL.p;
  await sleep(1200);
  // 先证明这张页面上跳价**真的**会落上去 —— 否则下面量到的"没被动"是"页面根本没在跳"冒充的
  { const t = Date.now(); while (SL.tick.done < 1 && Date.now() - t < 30000) await sleep(50); }
  await sleep(400);
  const sl0 = await snap(slp);
  // ★ 这一页的收价是**故意**给到区间外面的（`base.c + 500`，见 tickBody）：所以"落上去了"要拿**这个**值认，
  //   不能拿 TICKVALS 认 —— 第一次跑就是拿 TICKVALS 认的，`pre` 假红、⑯k 跟着红（那一格当时是假的）。
  const SLOWC = TICK_BASE.c + 500;
  const pre = eq(sl0.drawn && sl0.drawn.close, SLOWC) && eq(sl0.lastBar && sl0.lastBar.c, SLOWC);
  // 等**第二趟**在飞（n 已经加、done 还没加）—— 就在这 2 秒里换品种
  { const t = Date.now(); while (!(SL.tick.n >= 2 && SL.tick.done >= 1) && Date.now() - t < 30000) await sleep(50); }
  const nSwap = SL.tick.n, doneSwap = SL.tick.done, tSwap = Date.now();
  const flew = tSwap - (SL.tick.reqAt[nSwap - 1] || tSwap);
  await slp.evaluate((v) => { const s = document.getElementById('symbol'); s.value = v;
    s.dispatchEvent(new Event('change', { bubbles: true })); }, 'BTCUSDT');
  await slp.waitForFunction(() => window.__app.state.data && window.__app.state.data.symbol === 'BTCUSDT',
                            null, { timeout: 30000 });
  const swAt = Date.now();
  { const t = Date.now(); while (SL.tick.done < nSwap && Date.now() - t < 30000) await sleep(50); }
  await sleep(900);                        // 那一趟回来之后，页面该做的都做完了
  const sl1 = await snap(slp);
  ck('⑯k 跳价**还在飞**的时候换了品种 ⇒ 那一趟回来一个字都不许动（老品种的价、t 还跟新图对得上）',
     pre && flew < 2000 && doneSwap === nSwap - 1 && sl1.symbol === 'BTCUSDT' && SL.tick.doneAt > swAt
       && sl1.nBars === sl0.nBars
       && eq(sl1.drawn && sl1.drawn.close, TICK_BASE.c)
       && eq(sl1.lastBar && sl1.lastBar.c, TICK_BASE.c),
     `换的那一下：第 ${nSwap} 趟飞了 ${flew}ms（已回 ${doneSwap} 趟）｜换成 ${sl1.symbol} 画上用了 ${swAt - tSwap}ms`
     + `｜那一趟 ${SL.tick.doneAt > swAt ? '在新图画上**之后**才落地' : '★ 落得太早，这一格没量到东西'}`
     + `｜图上最后一根 ${sl1.drawn && sl1.drawn.time} 收价 ${sl1.drawn && sl1.drawn.close}`
     + `｜换之前那一下：${sl0.drawn && sl0.drawn.close}（＝老品种那一趟给的值，证明这张页面上跳价**真的**会落上去）`
     + `（数据那边 ${sl1.lastBar && sl1.lastBar.c}；老品种那一趟想写的是 ${SLOWC}）`);

  // ═══════════════════════════════════════════════════════════════════════════════════════════
  // ⑰ 中枢切法（卡 card-e346ede6-996，前端那半边）：名单驱动的切换 ＋ 「待定」的画法
  //   · 能切哪几种**以 /api/meta 的 `cut_modes` 为准**；名单没到 ⇒ 控件不画、参数不发
  //     （后台的白名单收到不认识的词就是 400 —— 前端多带一个参数就能把图打死）；
  //   · 默认「延伸」**永远不写进 URL**（它就是不切的那种，写上去等于每次都点名要它）；
  //   · **回显是唯一的真相**：chip 亮哪颗、图脚印哪一种，都看后台回的那份 `cut`；
  //   · `status=pending` 的刀 ⇒ 在 `cut_bar` 那根上真画一条竖虚线（高度＝包住它的那个旧框的 ZD…ZG）
  //     ＋ 一枚「待定」签；`done`/`void` 一根线都不画（不知道的事不编）；
  //   · 「先看切后」是**前端开关**、默认关（那一刀没立住之前，屏上摆的还是旧框）。
  //   量的都是**画布上真画出来的东西**（`window.__fx`，见 open()）—— 不是读 state 自说自话。
  // ═══════════════════════════════════════════════════════════════════════════════════════════
  /** 切法那几颗 chip ＋ 图脚那一格 ＋ 画布上真画出来的字/竖线（一份快照）。 */
  const cutUI = (p) => p.evaluate(() => {
    const g = document.getElementById('cgroup'), pv = document.getElementById('pvchip');
    return { has: !!g,
             cap: g ? (g.querySelector('.mcap') || {}).textContent : null,
             chips: g ? [...g.querySelectorAll('.mchip')].map((c) => ({
               cut: c.dataset.cut, on: c.getAttribute('aria-checked') === 'true',
               dis: c.disabled, txt: c.textContent })) : null,
             pv: pv ? { txt: pv.textContent, dis: pv.disabled,
                        on: pv.getAttribute('aria-pressed') === 'true' } : null,
             cut: window.__app.paging.cut, pvOn: !!window.__app.opts.cutPreview,
             url: location.search,
             foot: (document.getElementById('meta') || {}).textContent || '' };
  });
  const fxReset = (p) => p.evaluate(() => { window.__fx.text.length = 0; window.__fx.vseg.length = 0; });
  /** 画面上那一组签，**按落笔位置去重**：同一枚签不会被数成两枚（见 `fxOf` 里 `at` 那段注释）。
   *  返回 `文字@x,y`，所以读数本身就带证据 —— 数出来的几枚，各自画在哪儿，一眼能核。 */
  /** 这一刀给的**临时框**，各自在屏上的哪儿。`vis` ＝「露在屏上一截」（跟标注层 ③.6 挂签的判据同一件事：
   *  整只在屏外才不挂）—— 所以「该有几枚『随切点』」＝ `filter(b => b.vis).length`。 */
  const pvBoxes = (p) => p.evaluate(() => {
    const app = window.__app, d = app.state.data, ts = app.chart.timeScale();
    const done = (d.segs || []).filter((s) => !s.live);
    const c = (d.cuts || []).find((x) => x && x.status === 'pending');
    const W = document.getElementById('chart').getBoundingClientRect().width;
    return ((c && c.boxes) || []).map((z) => {
      const x0 = done[z.PI0] ? ts.logicalToCoordinate(done[z.PI0].i0) : null;
      const x1 = done[z.PI1] ? ts.logicalToCoordinate(done[z.PI1].i1) : null;
      return { PI: `${z.PI0}..${z.PI1}`, i0: done[z.PI0] && done[z.PI0].i0,
        x: x0 === null ? null : Math.round(x0),
        vis: x0 !== null && x1 !== null && x1 >= 0 && x0 <= W };
    });
  });
  const uniqTags = (fx) => [...new Set(fx.at.filter((s) => /^(待定|随切点)/.test(s)))];
  const rawTagN = (fx) => fx.text.filter((t) => /待定|随切点/.test(t)).length;
  const fxOf = (p) => p.evaluate(() => ({ text: window.__fx.text.map((x) => x.t),
                                          // 文字 ＋ 落笔位置。★ 为什么要有 `at`：LWC 一个视口变化可能**重画好几趟**
                                          //   （挪视口那一趟 + 跟着来的补画），同一枚签会被记好几遍 —— 只数 `text`
                                          //   会把「画了几个」数成「画了几笔」。按位置去重才是屏上真有几个。
                                          at: window.__fx.text.map((x) => `${x.t}@${x.x},${x.y}`),
                                          vseg: window.__fx.vseg.slice() }));
  /** 那一刀**该在屏上的哪儿**（x 走 timeScale，y 走包住它的旧框的 ZG/ZD），外加每张画布自己的偏移。
   *  ★ 记录器记的是**画布坐标**（ctx 那一层），跟页面坐标差一张画布的偏移 —— readBoxes 也是这么对的。 */
  const cutGeo = (p) => p.evaluate(() => {
    const app = window.__app, d = app.state.data;
    const ts = app.chart.timeScale(), s0 = app.chart.panes()[0].getSeries()[0];
    const box = document.getElementById('chart').getBoundingClientRect();
    const offs = [...document.querySelectorAll('#chart canvas')].map((c) => {
      const r = c.getBoundingClientRect();
      return { dx: Math.round(r.left - box.left), dy: Math.round(r.top - box.top) };
    });
    const done = (d.segs || []).filter((s) => !s.live);
    return { offs, cuts: (Array.isArray(d.cuts) ? d.cuts : []).map((c) => {
      const hit = (d.seg_centers || []).find((z) => done[z.PI0] && done[z.PI1]
        && done[z.PI0].i0 <= c.cut_bar && c.cut_bar <= done[z.PI1].i1);
      const x = ts.logicalToCoordinate(c.cut_bar);
      const yt = hit ? s0.priceToCoordinate(hit.ZG) : null;
      const yb = hit ? s0.priceToCoordinate(hit.ZD) : null;
      return { bar: c.cut_bar, status: c.status,
               x: x === null ? null : Math.round(x),
               y0: (yt === null || yb === null) ? null : Math.round(Math.min(yt, yb)),
               y1: (yt === null || yb === null) ? null : Math.round(Math.max(yt, yb)) };
    }) };
  });
  /** 那一段竖虚线在画布上**真画出来了没有**（x 对得上、高度也对得上才算 —— 只有"某处有条虚线"不算数）。
   *  虚线形（`dash` 至少两段）是判据之一：实线框边也是竖的，不认虚线样式的话这一格会把框边认成切点。 */
  const vsegAt = (fx, offs, g) => fx.vseg.filter((v) => v.dash.length >= 2 && g.x !== null
    && offs.some((o) => Math.abs(v.x - (g.x + o.dx)) <= 2
      && Math.abs(v.y0 - (g.y0 + o.dy)) <= 3 && Math.abs(v.y1 - (g.y1 + o.dy)) <= 3));
  const footCut = (txt) => (txt.match(/中枢切法[^｜]*/) || ['（没有这一格）'])[0].trim();

  // ⑰a：名单没到（这一页的假后台把 `cut_modes` 拿掉了）⇒ 控件不画、请求一个 `cut` 都不带。
  const NC = await open('nocut');
  await sleep(600);
  const nc0 = await cutUI(NC.p);
  ck('⑰a 名单没到（假后台这一份 `/api/meta` 里没有 `cut_modes`）⇒ 切法控件**不画**、请求里'
     + '**一个 `cut` 都不带**；回显给的那一档照样印在图脚上',
     !nc0.has && NC.cutReq.length >= 1 && NC.cutReq.every((x) => x === null)
       && nc0.cut === 'extend' && /中枢切法/.test(nc0.foot) && /延伸/.test(nc0.foot),
     `控件 ${nc0.has ? '★ 画出来了' : '没画'}｜请求带的 cut：${JSON.stringify(NC.cutReq)}`
     + `｜图脚「${footCut(nc0.foot)}」`);

  // ⑰h：**跟真后台对一次账** —— 这一页**不挂** meta 假后台，屏上是真后台那份 `cut_modes` 说了算。
  //   ★ 这一格是"合并前后都跑得动"的那种：它不假设后台有没有这一项，只钉**页面跟真后台说的是同一件事**
  //     （名单 ≥2 ⇒ 控件在、chip 数＝名单长度、`?cut=turn` 真发得出去；名单没到/只有一项 ⇒ 控件不在、
  //     一个 `cut` 都不发）。center-cut 合进 main 之后，这一格会**自己从"两边都没有"翻到"两边都有"**，
  //     翻不过去就是名字对不上（`cut_modes` 这个键、或者里头的两个词）——那种错只在合并后出现，
  //     而 ⑰b–⑰g 全是假后台喂的，永远逮不到它。
  const realModes = (() => RMETA && Array.isArray(RMETA.cut_modes)
    ? RMETA.cut_modes.filter((x) => typeof x === 'string' && x) : [])();
  const RU = await open('cutreal', QS + '&cut=turn');
  await sleep(1200);
  const ru = await cutUI(RU.p);
  const wantCtl = realModes.length >= 2;
  ck('⑰h 跟**真后台**对账（这一页不吃 meta 假后台）：屏上有没有那组控件、`cut` 发没发出去，必须跟 '
     + '`/api/meta` 真回的那份 `cut_modes` 一致 —— 名单 ≥2 ⇒ 控件在（chip 数＝名单长度、'
     + '**亮的那颗＝页面自报的切法**）且 `?cut=turn` 真的发出去了；名单没到或只有一项 ⇒ 控件不在、'
     + '一个 `cut` 都不发',
     // ★ 「亮的那颗」这一句第一版写的是「缺省那颗亮着」—— 而这一页是带 `?cut=turn` 打开的，亮的当然是
     //   turn ⇒ 合并后的第一趟就假红（页面全对）。判据该问的是**亮的那颗跟页面自报的切法一致不一致**
     //   （回显是唯一真源），不是"是不是缺省那颗"。
     ru.has === wantCtl
       && (wantCtl
         ? ru.chips.length === realModes.length && ru.cut === 'turn'
           && ru.chips.some((c) => c.cut === ru.cut && c.on)
           && RU.cutReq.includes('turn') && /cut=turn/.test(ru.url)
         : RU.cutReq.every((x) => x === null) && ru.cut === 'extend' && !/cut=/.test(ru.url)),
     `真后台 cut_modes=${JSON.stringify(realModes)}｜控件 ${ru.has ? '在' : '不在'}`
     + `${ru.has ? `（${ru.chips.length} 枚：${JSON.stringify(ru.chips.map((c) => c.cut))}）` : ''}`
     + `｜请求带的 cut：${JSON.stringify(RU.cutReq)}｜paging.cut=${ru.cut}｜URL「${ru.url}」`);

  // ⑰b/⑰c：名单到了 ⇒ 控件出现；默认那颗按**回显**亮着、默认照样不写进 URL；
  //   点「按转折切」⇒ 请求才带上 `cut=turn`。
  const CM = await open('cutmeta');
  const cmp = CM.p;
  await cmp.waitForSelector('#cgroup .mchip[data-cut="turn"]', { timeout: 15000 });
  await sleep(500);
  const cm0 = await cutUI(cmp);
  ck('⑰b 名单到了（`cut_modes: ["extend","turn"]`）⇒ 控件出现、默认那颗亮着，而且**默认不写进 URL、'
     + '也不发参数**（它就是不切的那种）；切法不是「按转折切」时那颗预览开关是**死的**',
     cm0.has && cm0.chips.length === 2
       && cm0.chips.some((c) => c.cut === 'extend' && c.on) && cm0.chips.some((c) => c.cut === 'turn' && !c.on)
       && cm0.chips.every((c) => !c.dis)
       && cm0.cut === 'extend' && !/cut=/.test(cm0.url)
       && CM.cutReq.every((x) => x === null)
       && cm0.pv && cm0.pv.dis === true
       && /中枢切法/.test(cm0.foot),
     `chips ${JSON.stringify(cm0.chips)}｜paging.cut=${cm0.cut}｜URL「${cm0.url}」`
     + `｜请求带的 cut：${JSON.stringify(CM.cutReq)}｜预览开关 ${cm0.pv ? (cm0.pv.dis ? '禁用着' : '★ 亮的') : '★ 没画'}`);

  await cmp.locator('.mchip[data-cut="turn"]').click();
  await cmp.waitForFunction(() => window.__app.paging.cut === 'turn', null, { timeout: 30000 });
  await sleep(900);
  const cm1 = await cutUI(cmp);
  const cmReq = CM.cutReq.filter((x) => x !== null);
  ck('⑰c 点「按转折切」⇒ 请求才带上 `cut=turn`；chip 亮哪颗看的是**后台回的那一份**，图脚也报当前切法',
     cmReq.length >= 1 && cmReq.every((x) => x === 'turn')
       && cm1.chips.some((c) => c.cut === 'turn' && c.on) && cm1.chips.some((c) => c.cut === 'extend' && !c.on)
       && /cut=turn/.test(cm1.url) && /按转折切/.test(cm1.foot),
     `请求带的 cut：${JSON.stringify(CM.cutReq)}｜chips ${JSON.stringify(cm1.chips)}`
     + `｜图脚「${footCut(cm1.foot)}」｜URL「${cm1.url}」`);

  // ⑰d：**回显是唯一的真相**。这一页后台"撒谎"：请求要的是 turn，回的却是 extend
  //   （真后台不会这样，但"照点击画"和"照回显画"只有在两者不一致时才分得开）。
  const LIE = await open('cutlie');
  const liep = LIE.p;
  await liep.waitForSelector('#cgroup .mchip[data-cut="turn"]', { timeout: 15000 });
  await sleep(400);
  await liep.locator('.mchip[data-cut="turn"]').click();
  await sleep(1200);
  const lie1 = await cutUI(liep);
  ck('⑰d 请求要了 turn、后台回音却是 extend ⇒ 屏上必须摆成「延伸」（chip ＋ 图脚），'
     + 'URL 里那把 `cut` 也得撤掉 —— 前台不许自作主张',
     LIE.cutReq.includes('turn') && lie1.cut === 'extend'
       && lie1.chips.some((c) => c.cut === 'extend' && c.on) && lie1.chips.some((c) => c.cut === 'turn' && !c.on)
       && !/cut=/.test(lie1.url) && /延伸/.test(lie1.foot),
     `请求带的 cut：${JSON.stringify(LIE.cutReq)}｜回显之后 paging.cut=${lie1.cut}`
     + `｜图脚「${footCut(lie1.foot)}」｜URL「${lie1.url}」`);

  // ⑰e：一刀 pending ⇒ 那一根上真画出**竖虚线**（虚线形 ＋ 高度＝旧框的 ZD…ZG）＋ 一枚「待定」签；
  //   同一份数据里 `done`/`void` 的刀**一根线都不画**（两张页面几何一样，只有 `status` 不同）。
  const CT = await open('cutturn', QS + '&cut=turn');
  const ctp = CT.p;
  await sleep(1200);
  const cg0 = await cutGeo(ctp);
  const pendCut = cg0.cuts[0];
  if (pendCut) await park(ctp, pendCut.bar);
  await fxReset(ctp);                       // 清账之后再摆一次视口 ⇒ 记下来的就是**这一屏**画的
  if (pendCut) await park(ctp, pendCut.bar);
  const cg1 = await cutGeo(ctp);
  const cfx = await fxOf(ctp);
  const CV = await open('cutvoid', QS + '&cut=turn');
  await sleep(1200);
  const vg0 = await cutGeo(CV.p);
  if (vg0.cuts[0]) await park(CV.p, vg0.cuts[0].bar);
  await fxReset(CV.p);
  await park(CV.p, vg0.cuts[0].bar);
  const vg1 = await cutGeo(CV.p);
  const vfx = await fxOf(CV.p);
  ck('⑰e 没立住的那一刀`pending` ⇒ 在 `cut_bar` 那一根上真画出竖虚线（虚线形、高度＝包住它的旧框的 '
     + 'ZD…ZG）＋ 一枚「待定」签；同一份数据里 `done`/`void` 的刀**一根线都不画**',
     // ★ 第一趟就得带着 `cut`（深链打开的那一趟）—— 少带了，后台按缺省回「延伸」，回显就把
     //   用户切好的那一刀弹回缺省，而屏上没有任何东西说过这件事（这一格第一次跑就是这么红的）。
     CT.cutReq[0] === 'turn'
       && !!pendCut && pendCut.x !== null && vsegAt(cfx, cg1.offs, cg1.cuts[0]).length >= 1
       && cfx.text.includes('待定')
       && vg1.cuts.length === 2 && vg1.cuts.every((c) => vsegAt(vfx, vg1.offs, c).length === 0)
       && !vfx.text.includes('待定') && !vfx.text.includes('随切点'),
     `pending 那一刀 bar=${pendCut && pendCut.bar} 该在画布 x≈${pendCut && pendCut.x}`
     + ` y=${pendCut && pendCut.y0}…${pendCut && pendCut.y1}；真画出来的竖虚线 `
     + `${JSON.stringify(cfx.vseg.filter((v) => v.dash.length >= 2))}`
     + `｜签「${cfx.text.filter((t) => /待定|随切点/.test(t)).join(' ')}」`
     + `‖ done/void 那两张：cuts=${JSON.stringify(vg1.cuts.map((c) => c.status))}`
     + `（x≈${vg1.cuts.map((c) => c.x).join(',')}）对上切点的虚线 `
     + `${vg1.cuts.reduce((k, c) => k + vsegAt(vfx, vg1.offs, c).length, 0)} 条、签 `
     + `${vfx.text.filter((t) => /待定|随切点/.test(t)).length} 枚`);

  // ⑰l：切点**压在框的右沿**上（线上 ZEC 15m 就是这一刀：`cut_bar=19911` ＝ 框 19698..19911 的右端）
  //   ⇒ **只画那条竖线、不挂「待定」**（Nova 10-05 08:58 拍：挂上去会让人以为那个框要被切，而那一刀
  //   **不改这个框**，改的是它后面那一组从哪儿重算）。
  //   ★ 这一格必须在**同一格**里同时量到两件：压边那页没有签、框内那页（⑰e 的 `cutturn`）照样有签。
  //     只量"没有签"的话，「签整条路崩了」也会让它绿 —— 那是假绿，这一卡最早就是这么假红过的。
  //   ★ 还要工装自己核一遍"这一刀**真**压在框沿上"（`edge`），否则模子哪天挪了，这一格会变成空转。
  const cutGeom = (p) => p.evaluate(() => {
    const d = window.__app.state.data;
    const done = (d.segs || []).filter((s) => !s.live);
    const c = (Array.isArray(d.cuts) ? d.cuts : [])[0];
    if (!c) return null;
    const z = (d.seg_centers || []).find((zz) => done[zz.PI0] && done[zz.PI1]
      && done[zz.PI0].i0 <= c.cut_bar && c.cut_bar <= done[zz.PI1].i1);
    if (!z) return null;
    const i0 = done[z.PI0].i0, i1 = done[z.PI1].i1;
    return { bar: c.cut_bar, i0, i1,
             edge: c.cut_bar === i1 || c.cut_bar === i0,
             inner: i0 < c.cut_bar && c.cut_bar < i1 };
  });
  const CE = await open('cutedge', QS + '&cut=turn');
  await sleep(1200);
  const eg0 = await cutGeo(CE.p);
  const egCut = eg0.cuts[0];
  if (egCut) await park(CE.p, egCut.bar);
  await fxReset(CE.p);
  if (egCut) await park(CE.p, egCut.bar);
  const eg1 = await cutGeo(CE.p);
  const efx = await fxOf(CE.p);
  const egG = await cutGeom(CE.p);
  const cgG = await cutGeom(ctp);                    // ⑰e 那一页（框内那一刀）做对照
  ck('⑰l 切点**压在框沿**上时（线上 ZEC 15m 那一刀：`cut_bar` ＝ 框的右端）⇒ **只画竖线、不挂「待定」**；'
     + '同一格拿框内的那一刀对照（照样挂签）',
     !!egG && egG.edge && !egG.inner && !!egCut && egCut.x !== null
       && vsegAt(efx, eg1.offs, eg1.cuts[0]).length >= 1 && rawTagN(efx) === 0
       && !!cgG && cgG.inner && cfx.text.includes('待定'),
     `压边那一刀 bar=${egG && egG.bar}（框 ${egG && egG.i0}..${egG && egG.i1}，工装自核 edge=${egG && egG.edge}）`
     + `｜真画出来的竖虚线 ${vsegAt(efx, eg1.offs, eg1.cuts[0]).length} 条、签 ${rawTagN(efx)} 枚`
     + `（签 ${JSON.stringify(efx.text.filter((t) => /待定|随切点/.test(t)))}）`
     + `‖ 对照（框内那一刀 bar=${cgG && cgG.bar}，inner=${cgG && cgG.inner}）签 `
     + `${JSON.stringify(cfx.text.filter((t) => /待定|随切点/.test(t)))}`);

  // ⑰g：切法是**这一屏**的属性 —— 换看法（换一次尺子）那几趟也得带着它走。
  //   ★ 这一格钉的是上面修掉的那个真 bug 最常踩的那条路：`setMeasure()` 原来没把 `cut` 传给 load()
  //     ⇒ 那一趟不带 `cut` ⇒ 后台按缺省回「延伸」⇒ 回显把用户切好的刀弹回缺省。
  const CTR = await open('cutturn', QS + '&cut=turn');
  await sleep(1200);
  // 买卖点那一层默认**关**着，关着的时候看法那排是灰的（renderMeasures 里那条闸）⇒ 先开层。
  await CTR.p.locator('.chip[data-key="sig"]').click();
  await sleep(600);
  await CTR.p.locator('.mchip[data-measure="lines"]').click();
  await CTR.p.waitForFunction(() => window.__app.state.data.measure === 'lines', null, { timeout: 30000 });
  await sleep(900);
  const ctg = await cutUI(CTR.p);
  ck('⑰g 换看法那一趟也带着 `cut`（切法不是"点完就丢"的临时状态，是这一屏的属性）：'
     + '换完之后请求里带的还是 `turn`，chip 和图脚都没被回显弹回「延伸」',
     CTR.cutReq.length >= 2 && CTR.cutReq.slice(1).every((x) => x === 'turn')
       && ctg.cut === 'turn' && /按转折切/.test(ctg.foot)
       && ctg.chips.some((c) => c.cut === 'turn' && c.on),
     `这一页请求带的 cut：${JSON.stringify(CTR.cutReq)}｜换完 paging.cut=${ctg.cut}`
     + `｜图脚「${footCut(ctg.foot)}」`);

  // ⑰f：「先看切后」是**前端开关**、默认关（切没立住之前屏上摆的还是旧框 ＋ 那条虚线）；
  //   点开 ⇒ 切后的框换上去（各带一枚「随切点」）、「待定」那组收掉（同一件事不说两遍）、URL 带 cutpv=1。
  const CP = await open('cutpv', QS + '&cut=turn');
  const cpp = CP.p;
  await sleep(1200);
  const cpg = await cutGeo(cpp);
  if (cpg.cuts[0]) await park(cpp, cpg.cuts[0].bar);
  await fxReset(cpp);                       // 清账 ＋ 挪 3 根 ⇒ 读到的就是"预览关着"这一帧
  await park(cpp, cpg.cuts[0].bar - 3);
  const cp0 = await cutUI(cpp);
  const cp0fx = await fxOf(cpp);
  await cpp.locator('#pvchip').click();
  await cpp.waitForFunction(() => window.__app.opts.cutPreview === true, null, { timeout: 15000 });
  await sleep(900);
  const cp1 = await cutUI(cpp);
  // ★ 点完之后**再清一次账**，然后挪一下视口逼出这一帧：不清的话，点之前那几帧（那时预览还关着）
  //   记下来的「待定」会混进来 —— 第一次跑就是这么假红的（读到「待定 待定 随切点 ×4」）。
  //   这一枪挪 3 根 ⇒ 视口真的变了 ⇒ 一定重画（同一个区间摆两次，LWC 可能一次都不画）。
  await fxReset(cpp);
  await park(cpp, cpg.cuts[0].bar + 3);
  const cp1fx = await fxOf(cpp);
  // 「随切点」是**按框**发的，临时框有几个就该有几枚 —— 屏上少一枚就是少一枚，读数里得能看出少的是哪个。
  const cp1pv = await pvBoxes(cpp);
  ck('⑰f 「先看切后」默认**关**（屏上摆的还是旧框 ＋ 那条待定虚线）；点开 ⇒ 切后的框换上去'
     + '（各带一枚「随切点」）、「待定」那组收掉、URL 带 cutpv=1',
     CP.cutReq[0] === 'turn' && cp0.pv && cp0.pv.on === false && cp0.pvOn === false && !/cutpv=/.test(cp0.url)
       && uniqTags(cp0fx).some((s) => s.startsWith('待定')) && !uniqTags(cp0fx).some((s) => s.startsWith('随切点'))
       && cp1.pvOn === true && cp1.pv.dis === false && cp1.pv.on === true
       && uniqTags(cp1fx).filter((s) => s.startsWith('随切点')).length === cp1pv.filter((b) => b.vis).length
       && !uniqTags(cp1fx).some((s) => s.startsWith('待定')) && /cutpv=1/.test(cp1.url),
     `关着：pvOn=${cp0.pvOn} 签「${uniqTags(cp0fx).join(' ')}」`
     + `‖ 点开：pvOn=${cp1.pvOn} 签「${uniqTags(cp1fx).join(' ')}」`
     + `（签后头是落笔位置；按位置去重前 ${rawTagN(cp0fx)}／${rawTagN(cp1fx)} 笔）`
     + `｜临时框 ${cp1pv.length} 个，露在屏上的 ${cp1pv.filter((b) => b.vis).length} 个`
     + `（${cp1pv.map((b) => `PI ${b.PI} i0=${b.i0} x≈${b.x}${b.vis ? '' : ' 屏外'}`).join('、')}）`
     + ` ⇒ 签必须一枚不少地跟露出来的框对得上｜URL「${cp1.url}」`);

  // ⑰i：预览那一趟**换上去**，不是"叠着画两遍"。真引擎的 `cuts[i].boxes` 是**整组**重算的结果 ——
  //   组里没被切到的那个框也在里头（线上那一刀就是这样：两个临时框里有一个跟旧框一模一样）。
  //   前端要是只换掉"包住 cut_bar 的那个旧框"，那个没变过的框就会**画两遍**（一遍旧的一遍临时的，
  //   左沿一实一虚、还多挂一枚「随切点」）——屏上看就是同一个框摞着两条边。
  //   ★ 量的是 `state.boxesDrawn`（这一帧真交给画框函数的那份清单，只读出口，跟 `state.labelBoxes`
  //     同性质）：**每画一帧重写一次**，所以不存在画布记录器那种"多帧累积"的假红。
  const cpd = await cpp.evaluate(() => (window.__app.state.boxesDrawn || [])
    .map((b) => ({ t: b.tier, i0: b.i0, i1: b.i1, pv: !!b.provisional })));
  const cPend = await cpp.evaluate(() => {
    const c = ((window.__app.state.data.cuts) || []).find((x) => x && x.status === 'pending');
    return c && Array.isArray(c.boxes) ? c.boxes.length : 0;
  });
  const uniq = new Set(cpd.map((b) => `${b.t}|${b.i0}|${b.i1}`)).size;
  const prov = cpd.filter((b) => b.pv).length;
  // 旧框只要跟某个临时框**真的**交叠（不是只共一个端点）就是没被换掉 —— 那正是「画两遍」。
  const stale = cpd.filter((b) => !b.pv
    && cpd.some((q) => q.pv && q.t === b.t && b.i0 < q.i1 && q.i0 < b.i1));
  ck('⑰i 预览那一趟是**换掉**同一组的旧框，不是叠着画两遍：这一帧交给画框函数的清单里，'
     + '同一个 (层, i0, i1) 只许出现一次；临时框的条数＝载荷给的那一组；跟临时框交叠的旧框一个都不许留',
     cpd.length > 0 && uniq === cpd.length && prov === cPend && stale.length === 0,
     `这一帧画了 ${cpd.length} 个框（临时 ${prov} / 旧 ${cpd.length - prov}），载荷那一组 ${cPend} 个；`
     + `去重之后 ${uniq} 个${uniq === cpd.length ? '' : ' ★ 有重复'}`
     + `｜没被换掉的旧框 ${stale.length} 个 ${JSON.stringify(stale)}`);

  // ⑰j：临时框**半只在屏外**时，那枚「随切点」照样得挂出来。切点前后那一组里，前面那个没被切到的框
  //   可以很长（线上那组：i0 在左边界外一千多像素）—— 判据要是写成"左沿在屏上才挂"，屏上就会出现一个
  //   **看得见、却没记号**的临时框：跟已经定了的框分不出来，正好把这一卡要解决的问题反过来。
  //   这一枪把视口左边界**挪进**左边那个临时框的肚子里：它露一半，签锚到看得见的那一端。
  const cp2w = await cpp.evaluate(() => {
    const app = window.__app, d = app.state.data, ts = app.chart.timeScale();
    const done = (d.segs || []).filter((s) => !s.live);
    const c = (d.cuts || []).find((x) => x && x.status === 'pending');
    const z = (c.boxes || []).find((b) => done[b.PI0] && done[b.PI1] && done[b.PI1].i1 - done[b.PI0].i0 > 20);
    if (!z) return null;
    const from = done[z.PI0].i0 + Math.floor((done[z.PI1].i1 - done[z.PI0].i0) / 2);
    const to = Math.min(from + 200, d.bars.length - 1);
    ts.setVisibleLogicalRange({ from, to });
    return { i0: done[z.PI0].i0, i1: done[z.PI1].i1, from, to };
  });
  await sleep(900);
  // 清账之后**再挪一根**（同一个区间摆两次 LWC 可能一趟都不画），挪的是刚设的那个窗口本身，
  // 不是 `park`（`park` 会把窗口整个换成 ±150，正好把"半只露在外头"这个情形抹掉）。
  await fxReset(cpp);
  if (cp2w) await cpp.evaluate((w) => window.__app.chart.timeScale()
    .setVisibleLogicalRange({ from: w.from + 1, to: w.to + 1 }), cp2w);
  await sleep(800);
  const cp2fx = await fxOf(cpp);
  const cp2pv = await pvBoxes(cpp);
  const cp2need = cp2pv.filter((b) => b.vis).length;
  const cp2got = uniqTags(cp2fx).filter((s) => s.startsWith('随切点')).length;
  ck('⑰j 临时框**只露半只**（左沿在屏外、身子进屏）时，「随切点」也得挂在**看得见的那一端**：'
     + '签数照样＝露在屏上的临时框数，不许因为"左沿不在屏上"就整个跳过（那样屏上会有个没记号的临时框）',
     !!cp2w && cp2pv.some((b) => b.x !== null && b.x < 0 && b.vis) && cp2got === cp2need && cp2need >= 1,
     `视口挪到 bar ${cp2w ? `${cp2w.from}..${cp2w.to}` : '(没挪成)'}：临时框 ${cp2pv.length} 个，露在屏上 ${cp2need} 个`
     + `（${cp2pv.map((b) => `i0=${b.i0} x≈${b.x}${b.vis ? '' : ' 屏外'}`).join('、')}）；`
     + `真画出来的「随切点」${cp2got} 枚「${uniqTags(cp2fx).join(' ')}」`
     + `${cp2pv.some((b) => b.x !== null && b.x < 0 && b.vis) ? '' : ' ★ 这一枪没造出"半只在屏外"的框（量了个空）'}`);

  // ⑰k：换框规则**直接量纯函数**（不经过画布、不经过后台）。⑰i 量的是"这一屏画出来的东西"，
  //   钉得住"画两遍"，但钉不住两条边界：① 两个框**只共一个端点**算不算交叠（算的话会把挨着的那组
  //   旧框误撤掉 —— 模子那份数据里两个框不共端点，屏上量不出来）；② 同一组被两刀同时切到时只摆第一刀。
  //   这两条都只在 `boxes()` 里，所以拿一份手写的小数据直呼它 —— `import('/layers.js')` 走的是页面
  //   自己加载的那份模块（跟屏上画的**同一份字节**）。
  const unit = await cpp.evaluate(async () => {
    const L = await import('/layers.js');
    // 四个线段**相邻**（9 那一根是共用的转折点）—— 中枢框按 PI 取成员，所以"共端点"这个情形
    // 只有数据这么排才造得出来。
    const segs = [{ i0: 0, i1: 9 }, { i0: 9, i1: 19 }, { i0: 19, i1: 29 }, { i0: 29, i1: 41 }];
    const mk = (PI0, PI1) => ({ PI0, PI1, ZG: 10, ZD: 5 });
    const base = { segs, seg_centers: [mk(0, 0), mk(1, 3)] };   // 旧框：0–9 与 9–41
    const half1 = mk(1, 1), half2 = mk(2, 3);                  // 待定那一刀切出来的两半：9–19、19–41
    const cut = (boxes) => ({ cut_bar: 19, by: 'x', level: 'seg', status: 'pending', boxes });
    const pick = (a) => a.map((b) => `${b.i0}-${b.i1}${b.z.provisional ? '*' : ''}`);
    return { old: pick(L.boxes(base, 'seg', false)),
             one: pick(L.boxes({ ...base, cuts: [cut([half1, half2])] }, 'seg', true)),
             two: pick(L.boxes({ ...base, cuts: [cut([half1, half2]), cut([half1, half2])] }, 'seg', true)) };
  });
  ck('⑰k 换框规则（直呼 `boxes()`）：① 预览关着 ⇒ 两个旧框照旧；② 预览开着 ⇒ 被切的那个换上两半、'
     + '**只共一个端点**的邻居（0–9）留着；③ 同一组被两刀同时切到 ⇒ 只摆第一刀（不是摆两遍）',
     JSON.stringify(unit.old) === JSON.stringify(['0-9', '9-41'])
       && JSON.stringify(unit.one) === JSON.stringify(['0-9', '9-19*', '19-41*'])
       && JSON.stringify(unit.two) === JSON.stringify(unit.one),
     `旧框「${unit.old.join(' ')}」‖ 预览「${unit.one.join(' ')}」‖ 同一组两刀「${unit.two.join(' ')}」`
     + `（带 * 的是临时框；跟两半**共端点**的邻居 0–9 必须留着）`);

  await b.close();
  console.log(`\n${n - bad}/${n} 过　截图：${OUT}`);
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.error('✗ 炸了：' + (e && e.stack || e)); process.exit(2); });
