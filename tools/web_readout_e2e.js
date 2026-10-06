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
//      ★ 偶发（2026-10-04，Iris 记）：同一份代码连跑 6 遍，⑭ 红过 **1** 次 ——
//        `a 快滑 4740.000→4740.000`（第一下快滑没拖动视口），复跑即绿。**不加重试**（Atlas 定的：
//        重试会把偶发变成看不见）。见红先按这句读：多半是库的触摸状态机，不是这一格要量的东西。
//   ⑮ 换数据**那一刻**读数就收：把那一趟响应扣在手里 ⇒ 在「新数据还在飞」的窗口里读一眼，
//      屏上还是旧图、十字线也没动，读数不许写着**上一份**的数。⑯ 是它的另一头：收了要能回来，
//      且回来时写的是**新那份刻度**上的数（指针全程没离开图）。
//      ★ 为什么量的是**窗口**而不是「换完之后」：`paint()` 里那句 `hideRead()` 的位置**量不出来**
//        （LWC 在 setData 后会自己重发十字线，读数当场就用新那份重读）—— 在那里加格是空转格。
//        实测与对照（含变异跑法）在 `tools/web_readout_swap_probe.js`，理由写在 ⑮⑯ 那一节。
//   ⑰ 窗口里**动鼠标**：⑮ 只量了「指针不动」的那一眼 —— 口径是「取数那段时间读数**整个压住**」，
//      指针一动，`showRead()` 就又被叫了一次。修之前实测：块里当场亮回来、写的是**上一份**的价
//      （ZEC→BTC 那一趟扣住 2.5s，指针一扫，块里是 `1,655.24`，页头写着 BTCUSDT）。
//      ⇒ ⑰ 量的是**动过之后**还不亮（并且那一刻确实还在窗口里：状态写着「取数…」、屏上还是旧那份）。
//   ⑱ 同一个窗口、同一条账的**另一处**：副图那一格的三个数（DIF/DEA/柱）也是**跟着光标走**的读数，
//      修之前同样印着上一份的量级（实测 DIF -11.69，而 BTC 那份是 -121.11）⇒ 这段里印「—」。
//      ★ 前提先断言：换之前这三格**是有数的**（不然「—」是空转 —— 本来就写着「—」也能过）。
//   ⑲ ⑰ 的另一头：新图**画上之后**再动鼠标 ⇒ 读数要回来，而且写的是**当时画着的那一份**上的数。
//      （⑯ 量的是「不用动鼠标、LWC 自己重发」那条路；⑲ 管的是**动**那条路不许被压死。）
//   ⑳ 取数**失败**那一趟（只让点名的那趟 503）⇒ 也不许把读数压死：新图没来、屏上还是旧那份，
//      老读数跟它还是同一份 ⇒ 动一下就该回来，而且对得上**当时画着的那一份**。
//      ★ 这一格是修法里「放在 finally 而不是 draw() 后面」那一条的牙。
//   ㉑ **换看法不压读数**（口径见下：压的只有换品种/换周期，换看法和往左补数据不压）。
//      这一格是 Atlas 核 readout-hold 时点的缺口：变异「换看法时也立起 dataStale」全绿、没一格看见。
//      摆法上三个坑都绕开了（换看法在**页面里**点，指针不许离开图；先开买卖点那层，不然芯片是灰的；
//      先断言「换之前就亮着 ＋ 回显真换了」）—— 理由写在 ㉑ 那一节。
//   ㉓–㉚ **级别联动那一层**（卡 card-01961644-68f，L-9；后台 `GET /api/levels` 这一支**不在 main 上**，
//      所以一律用 Playwright 的 `page.route` 把那一趟拦下来喂载荷）。这一族量的都是**"该不该出字"**：
//      ㉓ 三档 mismatch 各出各的那句话、且锚在框**右沿**｜㉔ match/partial **不出字**（★ 必须在
//      **同一份载荷**里跟 mismatch 一起量：整层没画也是"没字"，那种绿是假的）｜㉕ 两颗芯片的从属
//      关系（`lv` 与 `up` 与过：关掉 lv 标全没、框还在；关掉 up 标也没，且 lv 那颗按灰）｜
//      ㉖ 起点那句（L-7）报三截事实，且**不许下"算不算分歧"的裁决**（Nova 14:09Z）｜
//      ㉗ `levels: null`（这一层不存在）⇒ 一个标都不画、一个字都不说（fail-closed），而且那一行话
//      摆在 `.overlays` 里、**不占流**（`#chart` 高度跟有那一行话时一模一样 —— 图脚的账见 `#ghostc`）｜
//      ㉘ `unmeasured` 只许说「没比成」，读不出"对得上"｜㉙ `start.status: 'same'` ⇒ 一个字都不说
//      （在"一样"上贴一句话＝凭空捏一个分歧出来）｜㉚ **对齐闸**：`levels.units` 跟框只有"同下标"这一条
//      契约（实拍的那一条**没有身份字段**，连 X0 都没有）⇒ 回显的周期／档位／条数有一条对不上，
//      就一个标都不画。
//      ★★ 这一族第一版是**假绿**：工装自己给 `levels.units` 每条编了个 `X0`（照 spec 想当然），
//        七格全绿、线上一个标都出不来 —— 量的是替身。教训写在这儿：**假后台要照实拍载荷写**，
//        不是照 spec 写；spec 里那句"按 box start 对齐"跟线上报文对不上（Bram 抓的载荷里没有这个字段）。
//
// 判据的牙齿（每一条都跑得红，跑法与数在 `tools/web_readout_swap_probe.js` 的 D/E 段）：
//   摘掉 `showRead` 里那道闸 ⇒ ⑰ 红；摘掉 `refreshSubVals` 里那道 ⇒ ⑱ 红；
//   那个标志**永不放开** ⇒ ⑯⑲⑳ 红。⑮ 的牙还是原来那条（摘 go() 里那句）。
//   **在 `setMeasure()` 里也立起 `dataStale`** ⇒ ㉑ 红（只红这一格：㉑ 自己一页，不牵连后面）。
//   级别那一族（㉓–㉚）逐格变异验过，改法与结果见 `tools/web_readout_e2e.js` 那一节末尾 ——
//   一句话：㉓ 把 `share.length >= 2` 那句掐空 ⇒ 红；㉔ 让没状态的框也出「对标」⇒ 红；
//   ㉕ `lv` 的 disabled 恒 false ⇒ 红；㉖ 摘掉「会变」那截 ⇒ 红；㉗ 把浮层搬进 `.foot`（流内）
//   ⇒ 高度那一句红；㉘ `unmeasured` 不计数 ⇒ 红；㉙ 放行 `same` ⇒ 红；㉚ 把对齐闸摘掉（`lvAligned`
//   恒返回 `units`）⇒ 红。★ 另有一条**假绿**的旧账（值得记）：第一版工装给载荷编了个 `X0` 身份字段，
//   七格全绿而线上全瞎 —— 那一版的绿，量的是工装自己编的替身。
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
const { macdOf } = require('./fake_macd.js');    // 假副图（见上面 /api/macd 那条路由）
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
const PAGE = (process.env.E2E_URL || process.argv[3] || 'http://127.0.0.1:8793/').replace(/\/?$/, '/');   // E2E_URL 优先（上线门统一给，card-9b0fe913-758）
const FULL = JSON.parse(fs.readFileSync(path.join(WEB, 'fixtures/zec_1h.json'), 'utf8'));

// 假后台的开关（跟 web_more_e2e 一样：一格一格摆场景，**开页之前**声明）
//   tick ：这一页的价格精度。★ 默认 0.1，而样本里的价是两位小数 —— 故意错开：
//          「读数几位小数」那一格要是空转（写死两位也能过），它就白写了。
//   bend ：**第二份**数据（span≥2）把笔/线段的价格乘 1.002 ⇒ 可视窗口里的结构真变了 ⇒ 那句提示该出来。
//   fail ：/api/chart 直接 503（留给后面加「取不到」那一族，这一套现在不用）
//   symShift：⑮ 用 —— 换成 BTCUSDT 之后那份把价整体乘 1.5。
//          ★ 不乘的话两份一模一样，「换了数据之后读数该不该收」这件事在屏幕上**分不出来**
//            （指针底下还是同一根），那一格就是空转。
//   hold   ：⑮⑰⑱ 用 —— 这趟请求**扣住**多少毫秒再回（holdSym 是扣哪一趟，默认 BTCUSDT）。
//          ★ 这一段里 ⑮ 读一眼、⑰⑱ 还要**连动三下鼠标**，窗口得撑得住这三下（现在是 6000ms；
//            2500 那次真跑红了 ⑰：第三下落在窗口外面，量到的是新图上的读数）。
//          ★ 不扣住就没有「新数据还在飞」那一段可量：静态假后台回得太快，
//            ⑮ 量的那一眼会落在数据到了之后 —— 那正是**量不出来**的位置（见下面 ⑮ 那段注释）。
//   failSym：⑳ 用 —— **只让点名那一趟** 503（`fail` 是整页都失败，那样首屏起不来，⑳ 摆不出来）。
//   holdMeasure：㉑ 用 —— 把**带 measure 的那一趟**（＝换看法那一趟）扣住。
//          ★ 不扣住就没有「看法还在换」这段窗口可量：静态假后台秒回，㉑ 那一眼会落在换完之后，
//            于是「换的那一刻压一下、换完才放开」这个形状**量不出来**（那正是 ㉑ 要防的）。
//   units  ：㉓–㉗ 用 —— 塞进 `/api/chart` 的 `trend.units`（合成框）。仓里样本一个 units 都没有，
//            这一族不自己合成就没框可标（见上面 lvBox 那段）。默认 null ⇒ 老的那些格逐字节不变。
//   levels ：㉓–㉗ 用 —— `/api/levels` 回什么。默认 **null** ⇒ 回一个 JSON `null`（＝这一层不存在），
//            页面一个字、一个标都不出。★ 回 `'fail'` 就是 503（留给"接口挂了"那条路，这一套不摆它）。
const DEFAULT_SCEN = { tick: 0.1, bend: false, fail: false, failSym: null, symShift: false, hold: 0,
                       holdSym: 'BTCUSDT', holdMeasure: 0, units: null, levels: null };
const SCEN = Object.assign({}, DEFAULT_SCEN);
const scen = (o) => { Object.assign(SCEN, DEFAULT_SCEN, o || {}); };

const decimals = (t) => { const s = String(t); return s.includes('.') ? s.split('.')[1].length : 0; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function payload(span, sym, measure) {
  const d = JSON.parse(JSON.stringify(FULL));
  d.meta.tick = SCEN.tick;
  d.source = 'api';
  d.fetched_at = new Date().toISOString();
  d.span = span; d.span_max = 4; d.earliest = false;
  // ★ 回显点名的那一种（没点名才落到 macd 缺省）。原来这儿写死 `'macd'` ⇒ 点「斜率」那趟回来还是
  //   「面积」⇒ 页面按**回显**点亮芯片（renderMeasures 认的是 paging.measure），当场亮回原来那颗 ——
  //   换看法**根本没换**。真后台是回显你点的那种，假后台也得是；不然 ㉑ 是一格空转（量的是"没换"）。
  d.measure = measure || 'macd';
  if (sym) d.symbol = sym;
  // ★ 换品种那一格（⑮）：另一份**真的不一样**，不然「读数收了没有」看不出来（见 DEFAULT_SCEN 那段）
  if (SCEN.symShift && sym === 'BTCUSDT') {
    d.bars = d.bars.map((b) => ({ ...b, o: b.o * 1.5, h: b.h * 1.5, l: b.l * 1.5, c: b.c * 1.5 }));
  }
  // ★ 只有**第二份**才动结构：两份都动、动的还一样，等于没动（那句提示永远不触发，⑪ 就成了空转）
  if (SCEN.bend && span >= 2) {
    d.pens = d.pens.map((p) => Object.assign({}, p, { p0: p.p0 * 1.002, p1: p.p1 * 1.002 }));
    d.segs = d.segs.map((s) => Object.assign({}, s, { p0: s.p0 * 1.002, p1: s.p1 * 1.002 }));
  }
  // ★ ㉓–㉗：这一族要「屏上有合成框」才谈得上标 —— 样本里一个都没有 ⇒ 自己塞（`trendWith` 见上）。
  if (SCEN.units) d.trend = trendWith(SCEN.units);
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

// ★ ⑰⑱ 那一眼要一起看四样：读数块的状态、副图那三格、**这一眼确实还在窗口里**的两个证据
//   （状态写着「取数…」＋ 屏上那份还是旧的）。少一样就可能量在数据到了之后 —— 那一眼是替身。
const midProbe = (p) => p.evaluate(() => {
  const g = (id) => (document.getElementById(id) || {}).textContent || '';
  const sh = document.getElementById('subhead');
  const d = window.__app.state.data;
  const cells = sh ? Array.from(sh.querySelectorAll('.cell b')).map((b) => b.textContent) : null;
  return { on: document.getElementById('readout').classList.contains('on'),
           c: g('ro-close'), time: g('ro-time'), badge: g('state'),
           firstO: d ? d.bars[0].o : 0, subCells: cells };
});
// ★ ⑲⑳：读数上那一刻，在**当时画着的那一份**里是哪一根？（`timeLabel` 是 UTC 到分 —— 那串字抄一份就迟早在某处错开）
const inDrawn = (p) => p.evaluate(() => {
  const d = window.__app.state.data;
  const tm = (document.getElementById('ro-time') || {}).textContent || '';
  const cs = Number(String((document.getElementById('ro-close') || {}).textContent || '').replace(/,/g, ''));
  const pad = (n) => String(n).padStart(2, '0');
  const label = (ms) => { const x = new Date(ms);
    return `${x.getUTCFullYear()}-${pad(x.getUTCMonth() + 1)}-${pad(x.getUTCDate())} `
         + `${pad(x.getUTCHours())}:${pad(x.getUTCMinutes())} UTC`; };
  const bar = d ? d.bars.find((b) => label(b.t) === tm) : null;
  return { tm, c: cs, found: !!bar, firstO: d ? d.bars[0].o : 0,
           match: !!bar && Math.abs(bar.c - cs) <= Math.max(0.051, Math.abs(bar.c) * 1e-6) };
});
// 「换成了新那份」的分界。★ 假后台那份是 `ZEC 样本 × 1.5`（首根 195.7 → 293.6），拿 300 当分界会**永远**判成
//   旧那份 —— ⑯ 里原来那句 `> 300` 就是个死条件（真后台的首根才是 6 万，这个数搬不到假后台来）。
const NEW_FIRST = 250;
const rgbOf = (hex) => 'rgb(' + [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)).join(', ') + ')';

// ---------------------------------------------------------------- 级别对照（㉓–㉚，卡 card-01961644-68f，L-9）
// ★ 仓里三份样本的 `d.trend` 都**没有 `units`**（1h 那份连 `trend` 键都没有）⇒ 这一族必须**自己合成**
//   几个「合成框」喂给 `/api/chart`。
//   ★★ 假的 `/api/levels` 必须照着**实拍载荷**写，不是照着 spec 写：Bram 线上抓回来的那一条
//      `levels.units[i]` 是 `{"status":"unmeasured","share":[],"outside":null}` —— **没有 X0、没有 X1，
//      一个身份字段都没有**。第一版工装自己给每条编了个 `X0`（照 spec 的"按 box start 对齐"想当然），
//      于是七格全绿，而线上一个标都出不来 —— **量的是替身**。这一族现在按**同下标**对齐，
//      工装也照着真形状喂；谁再往这份载荷里加字段，先问一句"这是后台真回的吗"。
//   ★ DD/GG 取那一段**真 bars 的低/高**（不是编一个价）：框一定落在价格轴的可见范围里，不会因为
//     "纵坐标出屏"被跳过 —— 被跳过就成了"根本没摆出来"，那种绿是假的。
//   ★ X0/X1 落在**最后 200 根**里（这一族一律带 `?last=200` 打开）⇒ 一定在可视窗口里。
const lvBox = (i0, i1, n) => {
  let lo = Infinity, hi = -Infinity;
  for (let i = i0; i <= i1; i++) { const b = FULL.bars[i]; if (b.l < lo) lo = b.l; if (b.h > hi) hi = b.h; }
  return { X0: i0, X1: i1, DD: lo, GG: hi, n: n || 2, seg: 0, live: false };
};
// `trendOf()` 只认 `T.segments` 是数组的那份载荷（不是数组 ⇒ 整层不画）⇒ 合成 units 时必须
// 连这一层最小的壳一起给：一条盖住全序列的「走势分段」（图头那条，画灰，不影响这一族量的东西）。
const SEG_ALL = () => [{ i0: 0, i1: FULL.bars.length - 1, type: '盘整', head: true, live: false, upgraded: false }];
const trendWith = (units) => ({ segments: SEG_ALL(), bounds: [], pending: [], retracted: [], units });
// 那一趟 levels 的报文字段（前端只读 tf／span／ref_tf／finest_tf／start／units／data_at；
//   其余按真报文补齐，读起来像真的）。
//   ★ `tf`／`span` **不是编的**：路由那一段拿**请求里那两个参数**回显（真后台就是这么回的），
//     页面的对齐守卫拿它们跟屏上这一份比（`lvAligned`）。这一格要是写成死的，那一格判据就永远为真。
const LV_BASE = { engine: 'v3', symbol: 'ZECUSDT', tf: '1h', span: 1, finest_tf: '15m', ref_tf: '1h',
                  start: null, data_at: { here: '2026-10-06', finest: '2026-10-06', ref: '2026-10-06' } };
// 探针：把「这一帧真画上去的标」和「浮层那一行话」一次读齐。
//   ★ 标从 `state.trendDrawn.labels` 读 —— 跟价签/图脚同一个**只读出口**（layers.js 里 `haloText` 记的），
//     不截屏、不数像素；`tx` 就是那一句字本身。
const lvProbe = (p) => p.evaluate(() => {
  const s = window.__app.state;
  const lab = ((s.trendDrawn || {}).labels || []).map((l) => ({ x0: l[0], y0: l[1], x1: l[2], y1: l[3], tx: String(l[4]) }));
  const boxes = ((s.trendDrawn || {}).units || []).map((u) => ({ X0: u.X0, X1: u.X1 }));
  const h = document.getElementById('lvhead');
  return { labels: lab, boxes,
           head: h ? (h.textContent || '') : null,
           headOn: h ? h.classList.contains('on') : null,
           headVis: h ? getComputedStyle(h).visibility : null,
           chartH: document.getElementById('chart').getBoundingClientRect().height };
});
// 「框右沿那枚标」的锚点真值：走**跟 layers.js 同一个坐标变换**（`timeToCoordinate(bars[X1].t/1000)`），
//   不自己另推一份 —— 锚点 = 那个 x 减 6（⑥ 那段写死的 6）。
const tagAnchor = (p, X1) => p.evaluate((k) => {
  const { chart, state } = window.__app;
  const b = state.data.bars[k];
  const c = b ? chart.timeScale().timeToCoordinate(b.t / 1000) : null;
  return c === null ? null : c - 6;
}, X1);

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
  // ★ ⑳ 那一段我们**故意**让那一趟 503（连带页面去够样本时的 404）—— 那两条是**摆的场景**，不是页面出毛病。
  //   不过滤掉，报错清单里就混进假警报 —— 这一套把「页面报错」也算红，假警报一多，真出问题时就没人看了。
  let expectNet = false;
  const NET_EXPECTED = /Failed to load resource: the server responded with a status of (404|503)/;
  const watch = (p) => {
    p.on('pageerror', (e) => errors.push('pageerror: ' + e));
    p.on('console', (m) => {
      if (m.type() !== 'error') return;
      if (expectNet && NET_EXPECTED.test(m.text())) return;      // 摆出来的那几条（见上）
      errors.push('console: ' + m.text());
    });
  };
  // 假后台：/api/chart 一律我们答；/fixtures 关掉（逼它只能走后台那条路，跟线上同一条）
  const newCtx = async (opts) => {
    const ctx = await b.newContext(opts);
    await ctx.route('**/api/chart*', async (r) => {
      const u = new URL(r.request().url());
      const sym = u.searchParams.get('symbol');
      // ★ ⑳：点名的那一趟单独失败（别的趟照常答 —— 整页都 503 的话首屏都起不来）
      if (SCEN.fail || (SCEN.failSym && sym === SCEN.failSym)) return r.fulfill({ status: 503, body: '' });
      const span = Number(u.searchParams.get('span') || 1);
      const meas = u.searchParams.get('measure');
      const body = JSON.stringify(payload(span, sym, meas));
      // ★ ㉑ 要的那段「看法还在换」：只扣**带 measure 的那一趟**（首屏那一趟不带）
      if (SCEN.holdMeasure && meas) await sleep(SCEN.holdMeasure);
      // ★ ⑮ 要的那段「新数据还在飞」：把点名的那一趟扣住 hold 毫秒再回（不扣住就没有窗口可量）
      if (SCEN.hold && sym === SCEN.holdSym) await sleep(SCEN.hold);
      return r.fulfill({ status: 200, contentType: 'application/json', body });
    });
    // 看法名单照常给（不然静态服务回 404，控制台会多出一条与本事无关的报错，
    // 而这一套把"页面报错"也算红 —— 报错清单里混进假警报，真出问题时就没人看了）
    await ctx.route('**/api/meta', (r) => r.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ measures: ['macd', 'slope', 'lines', 'peak'] }) }));
    // 副图那个口（card-68704ee6-a5a）：**桌面**打开的页面默认就要它（手机上默认关着）。
    // 不铺这条路由，页面会去静态服务拿到 404、副图那格写着「MACD 取不到」——
    // 那是工装的错不是页面的错（这一套还要看控制台报错，假警报混进去就没人看真警报了）。
    // 数值用 tools/fake_macd.js 那份假 MACD（double=false：这一套不管"谁说了算"，
    // 那条判据归 web_more_e2e ⑲）。
    await ctx.route('**/api/macd*', (r) => {
      const span = Number(new URL(r.request().url()).searchParams.get('span') || 1);
      const d = payload(span);
      return r.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify(Object.assign({ span, span_max: 4, earliest: false,
          symbol: 'ZECUSDT', tf: '1h' }, macdOf(d.bars, false))) });
    });
    await ctx.route('**/fixtures/**', (r) => r.fulfill({ status: 404, body: '' }));
    // 级别对照那个口（card-01961644-68f）。★ **一定要铺**：页面每次 go() 都会去要它，
    //   不铺就落到静态服务拿 404 —— 那会在控制台留一条与本事无关的报错，而这一套把页面报错也算红。
    //   默认回 `null`（＝这一层不存在，页面一个字都不出）；SCEN.levels 给了就回那份；`'fail'` ⇒ 503。
    await ctx.route('**/api/levels*', (r) => {
      if (SCEN.levels === 'fail') return r.fulfill({ status: 503, body: '' });
      if (SCEN.levels == null) return r.fulfill({ status: 200, contentType: 'application/json', body: 'null' });
      // ★ 回显**请求里那两个参数**（真后台就是回显）：`tf`／`span` 是页面那道对齐闸要比的两个数
      //   （见 layers.js `lvAligned`）。编死成 1h/1 的话，"档位对不对得上"这件事在工装里永远为真。
      //   ★ `SCEN.levels` 最后合并 ⇒ 想摆"回了一份错档的载荷"就显式写进去（㉚ 就是这么摆的）。
      const u = new URL(r.request().url());
      const echo = { tf: u.searchParams.get('tf') || LV_BASE.tf,
                     span: u.searchParams.has('span') ? Number(u.searchParams.get('span')) : LV_BASE.span };
      const body = JSON.stringify(Object.assign({}, LV_BASE, echo, SCEN.levels));
      return r.fulfill({ status: 200, contentType: 'application/json', body });
    });
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

  // ================================================================ ⑮⑯ 换数据**那一刻** ⇒ 读数当场就收
  // ★ 这一族是 Atlas 2026-10-04 核「光标读数 bf4d833」时点的缺口：`paint()` 里那句 `hideRead()`
  //   删掉，工装里**没有一格**变红。查下去发现**病不在那个位置**，量出来两条：
  //   ① **`paint()` 那个位置量不出来**：LWC 在 `setData` 之后会自己重发一次十字线 ⇒ 读数当场
  //      就用**新那份**重读了。实测（`tools/web_readout_swap_probe.js`，真后台）：换品种／换周期／
  //      换看法 × 指针三个位置 × 按住拖动中 —— **摘掉那句与不摘，逐条读数一模一样**。
  //      在那儿加格＝加一格**空转格**（这正是这一整天在抓的那种）。
  //   ② 真正露在外面的是**换的那一刻 → 新数据到手**这一整段：屏上还是旧图、十字线一动没动，
  //      读数写的却是**上一份**的数（真后台实测：把响应扣住 2.5s，整整那段都是 `on 1,582.47`，
  //      而屏上标签早写着 BTCUSDT 了）。⇒ 修法是把那句挪到**换的那一刻**（app.js 的 `go()`），
  //      `paint()` 那句留着给不走 `go()` 的入口。
  // ★★ 所以这一格量的就是**那段窗口**：把那一趟响应扣在手里 2.5s，在窗口里读一眼。它才有齿：
  //     摘掉 `go()` 里那句 ⇒ ⑮ 红（⑯ 照旧绿，它量的是另一头）。
  // ★★ 换的时候**不许让指针离开图**。去点 chip、或挪到别的控件上，指针一走 LWC 发 `time==null`，
  //    读数自己就收了 —— 那样量到的是「鼠标移开」不是「换了数据」，又是一格替身。
  //    所以这里用 select 换品种：只改 selection，指针原地不动、十字线也不动。
  // ★ 扣 6000ms（原来 2500）：这一段里要连做三件事 —— ⑮ 那一眼、⑰⑱ 连动三下、然后等新图上来。
  //   2500 撑不住：真跑过一轮 19/20，第三下鼠标落在窗口**外面**（那一眼读数是「亮着 2,283.8」、
  //   状态已经是「已收盘」）—— ⑰ 当场报红而不是假绿，但那是**量具的窗口太短**，不是页面的毛病。
  scen({ tick: 0.1, symShift: true, hold: 6000 });
  const sctx = await newCtx({ viewport: { width: 1280, height: 800 } });
  const sp = await open(sctx, '?symbol=ZECUSDT&tf=1h&last=300');
  const sbox = await boxOf(sp);
  const sx = Math.round(sbox.x + sbox.width * 0.5), sy = Math.round(sbox.y + sbox.height - 40);
  await sp.mouse.move(sx, sy);
  await sleep(300);
  const rA = await shown(sp);                                  // 换之前：在、写着具体的数
  const seen = [];
  sp.on('request', (r) => { if (r.url().includes('/api/chart')) seen.push(r.url()); });
  const t0 = Date.now();
  await sp.evaluate(() => { const s = document.getElementById('symbol');
    s.value = 'BTCUSDT'; s.dispatchEvent(new Event('change', { bubbles: true })); });
  await sleep(Math.max(0, 700 - (Date.now() - t0)));           // 那一趟还扣在手里（扣 6000ms）
  const rMid = await shown(sp);
  const midState = await sp.evaluate(() => ((document.getElementById('state') || {}).textContent || ''));
  t('⑮ 换数据**那一刻**读数就收（新数据还在飞：屏上还是旧图，读数不许留着上一份的数）',
    rA.on && !rMid.on && midState.includes('取数'),
    `换之前 on=${rA.on}（这格不成立就是空转）、收盘=${rA.c}；窗口里那一眼 on=${rMid.on}` +
    `，块里${rMid.on ? '**还亮着**（里面那行字还是 ' + rMid.c + '）' : '已经收起'}` +
    `｜那一刻页面写着「${midState}」（不是"取数"里就说明这眼没落在窗口里）｜请求 ${seen.length} 趟`);
  // ================================================================ ⑰⑱ 窗口里**动鼠标**（口径：这一整段都压住）
  // 见文件头 ⑰⑱。★ 这三下必须落在**同一段窗口**里（响应还扣着）：紧接着 ⑮ 那一眼做，别等。
  await sp.mouse.move(Math.round(sbox.x + sbox.width * 0.5), sy);
  await sleep(80);
  const beforeSub = (await midProbe(sp)).subCells;          // 前提：换之前副图那三格是**有数的**
  const win = [];
  for (const f of [0.42, 0.58, 0.35]) {
    await sp.mouse.move(Math.round(sbox.x + sbox.width * f), sy, { steps: 6 });
    await sleep(120);
    win.push(await midProbe(sp));
  }
  const stillOld = win.every((x) => x.firstO > 0 && x.firstO < NEW_FIRST);      // 屏上还是旧那份（ZEC）
  const inWin = win.every((x) => x.badge.includes('取数'));
  t('⑰ 取数那一段里**动鼠标**读数不许亮回来（口径是整段压住，不是只压「换的那一刻」）',
    rA.on && stillOld && inWin && win.every((x) => !x.on),
    `换之前 on=${rA.on}（这格不成立就是空转）｜窗口里连动 3 下 ⇒ `
    + `${win.map((x) => (x.on ? `亮着(${x.c})` : 'off')).join(' / ')}`
    + `｜那三眼状态＝${[...new Set(win.map((x) => x.badge))].join('、')}、屏上首根 o=${win[0].firstO}（旧那份 <${NEW_FIRST}）`);
  t('⑱ 同一段里，副图那三个数（DIF/DEA/柱）也不许印上一份的旧量级（写「—」）',
    Array.isArray(beforeSub) && beforeSub.length === 3 && beforeSub.every((v) => v && v !== '—')
      && win.every((x) => x.subCells && x.subCells.length === 3 && x.subCells.every((v) => v === '—')),
    `换之前那三格＝${JSON.stringify(beforeSub)}（得是有数的，不然这格空转）｜窗口里＝`
    + JSON.stringify(win.map((x) => x.subCells)));
  // ★ ⑯ 两件事一起量：(a) 不是「收死了」—— 新数据画上之后读数得**回来**（不然这格是在奖励一个 bug）；
  //   (b) 回来时写的是**新那份刻度**上的数（symShift 那份整体 ×1.5，两份差着 1.5 倍，写旧答案对不上）。
  //   ★ 指针全程没离开图 ⇒ 这一格不是「鼠标回来把它叫醒」那笔账。
  let back = { on: false, c: '0' };
  for (let i = 0; i < 40; i++) {
    await sleep(200);
    back = await shown(sp);
    const drawn = await sp.evaluate((f) => !!(window.__app.state.data && window.__app.state.data.bars[0].o > f), NEW_FIRST);
    if (drawn && back.on) break;
  }
  const num = (s) => parseFloat(String(s).replace(/,/g, '')) || 0;
  t('⑯ （⑮ 的另一头：收了要能回来，且写的是**新那份**的数）',
    back.on && num(back.c) > num(rA.c) * 1.2,
    `换之前 收盘=${rA.c} → 回来 收盘=${back.c}（新那份是 ×1.5 那一档；指针全程没离开图）`);

  // ================================================================ ⑲ 新图画上之后再**动**一下 ⇒ 回来，且是当时那份的数
  await sp.mouse.move(Math.round(sbox.x + sbox.width * 0.62), sy, { steps: 6 });
  await sleep(300);
  const r19 = await shown(sp);
  const l19 = await inDrawn(sp);
  t('⑲ 新图画上之后再动鼠标 ⇒ 读数回来，且写的是**当时画着的那一份**上的数（防压死）',
    r19.on && l19.found && l19.match,
    `动一下 ⇒ on=${r19.on}，读到 ${r19.c} ${r19.time}；当时那份（首根 o=${l19.firstO}）里 `
    + (l19.found ? (l19.match ? '找得到同一根、数对得上' : '找得到那一刻但 close 对不上 ⇒ 停在旧数上')
                 : '根本没有那一刻 ⇒ 读的不是这一份'));
  await sp.close();
  await sctx.close();

  // ================================================================ ⑳ 取数**失败**那一趟 ⇒ 也不许把读数压死
  // 见文件头 ⑳：修法里「放开」那一句放在 `finally` 而不是 `draw()` 后面，这一格就是它的牙。
  scen({ tick: 0.1, failSym: 'BTCUSDT' });          // ★ 只让**换过去那一趟** 503：整页都失败的话首屏都起不来
  expectNet = true;                                 // 这一段的 503/404 是摆出来的（见 watch 上面那段）
  const fctx = await newCtx({ viewport: { width: 1280, height: 800 } });
  const fp = await open(fctx, '?symbol=ZECUSDT&tf=1h&last=300');
  const fbox = await boxOf(fp);
  const fy = Math.round(fbox.y + fbox.height - 40);
  await fp.mouse.move(Math.round(fbox.x + fbox.width * 0.5), fy);
  await sleep(300);
  const fA = await shown(fp);
  await fp.evaluate(() => { const s = document.getElementById('symbol');
    s.value = 'BTCUSDT'; s.dispatchEvent(new Event('change', { bubbles: true })); });
  await sleep(1500);                                  // 这一趟是 503（没扣住），当场就回来
  const fBadge = await fp.evaluate(() => (document.getElementById('state') || {}).textContent || '');
  const fMid = await shown(fp);
  await fp.mouse.move(Math.round(fbox.x + fbox.width * 0.45), fy, { steps: 6 });
  await sleep(300);
  const f19 = await shown(fp);
  const fl = await inDrawn(fp);
  t('⑳ 取数**失败**那一趟（新图没来）⇒ 读数不许被压死：动一下得回来，写的还是屏上那份的数',
    fA.on && !/取数…/.test(fBadge) && /取不到|失败|HTTP/.test(fBadge) && f19.on && fl.found && fl.match,
    `换之前 on=${fA.on}；那一趟回来写着「${fBadge}」（不是失败那一趟的话这格是空转）｜`
    + `失败后那一瞬 on=${fMid.on}｜再动一下 on=${f19.on}，读到 ${f19.c} ${f19.time}，当时那份（首根 o=${fl.firstO}）里 `
    + (fl.found ? (fl.match ? '数对得上' : '**对不上**') : '**没有那一刻**'));
  await fp.close();
  await fctx.close();
  expectNet = false;

  // ================================================================ ㉑ 换看法**不压**读数
  // Atlas 2026-10-04 核 readout-hold 时点的缺口：变异「换看法时也立起 dataStale」⇒ 全绿，没有一格看见。
  //   代码里那条口径是对的（`dataStale` 全文只在 `go()` 里出现一次），但「换看法不被压」这半句**没有闸门**。
  // ★ 怎么摆才不是替身：
  //   ① 先去点 chip **把指针挪开** ⇒ 指针一走 LWC 就发 `time==null`，读数自己收了 —— 量到的是「鼠标移开」，
  //      不是「换看法」。所以换看法那一下在**页面里**点（`el.click()`），指针全程钉在图上不动。
  //   ② 那四颗看法芯片**只换买卖点的画法**，买卖点那层关着时它们是 `disabled`（renderMeasures 里），
  //      点了等于没点 ⇒ 先开 `sig`。
  //   ③ 前提先断言「换之前就亮着」＋「回显真的换了」（fake 后台回显点名的那种，见 payload 那段）——
  //      没换成的话这一格是空转，不是"过了"。
  //   ④ 三半都量：**(0)** 换的那一趟**还扣在手里**时读数就得亮着（＝换看法这段**不许压**；这一半在
  //      「立起来、等换完再放开」那个形状下红 —— 那正是这次要防的）；**(a)** 换完**不碰指针**也得亮着
  //      （这一半在「立起来、没人放开」那个形状下红）；**(b)** 再动一下指针还亮着、写的还是**当时那份**
  //      上的数（Atlas 的原话）。★ 只量 (b) 不行：那两个形状它都漏。
  scen({ tick: 0.1, holdMeasure: 2500 });      // ④ 那一半要一段真窗口（秒回的假后台没有窗口可量）
  const xctx = await newCtx({ viewport: { width: 1280, height: 800 } });
  const xp = await open(xctx, '?symbol=ZECUSDT&tf=1h&last=300');
  const xbox = await boxOf(xp);
  const xx = Math.round(xbox.x + xbox.width * 0.5), xy = Math.round(xbox.y + xbox.height - 40);
  const sigOn = await xp.evaluate(() => {                      // ② 先开买卖点那层（不开，看法芯片是灰的）
    const c = document.querySelector('button.chip[data-key="sig"]');
    if (!c) return false;
    if (c.getAttribute('aria-pressed') !== 'true') c.click();
    return true;
  });
  await sleep(500);
  await xp.mouse.move(xx, xy);                                 // ① 指针钉在图上，之后不再挪开（除了 (b) 那一下）
  await sleep(350);
  const xA = await shown(xp);
  const m0 = await xp.evaluate(() => window.__app.paging.measure);
  const clicked = await xp.evaluate(() => {                    // 换看法：页面里点，指针不动
    const g = document.getElementById('mgroup');
    if (!g) return null;
    const b = [...g.querySelectorAll('.mchip')].find((e) => !e.disabled && e.dataset.measure !== window.__app.paging.measure);
    if (!b) return null;
    b.click();
    return b.dataset.measure;
  });
  // ④(0) 这一趟还扣在手里（2500ms）⇒ 窗口里读一眼：读数得**亮着**，状态写着「换看法…」
  //    （状态不是「换看法…」就说明这一眼落在换完之后 —— 那是替身，这半格当场报红，不装作量过了）
  await sleep(700);
  const xW = await shown(xp);
  const wBadge = await xp.evaluate(() => ((document.getElementById('state') || {}).textContent || ''));
  const seq = [];                                              // 换完之后读数亮不亮（光看末态会把"闪一下"藏掉）
  let m1 = m0, badge = '';
  for (let i = 0; i < 40; i++) {
    await sleep(150);
    const r = await xp.evaluate(() => ({ on: document.getElementById('readout').classList.contains('on'),
      m: window.__app.paging.measure, s: (document.getElementById('state') || {}).textContent || '' }));
    seq.push(r.on ? '1' : '0'); m1 = r.m; badge = r.s;
    if (m1 === clicked && !/换看法/.test(badge)) break;
  }
  const xB = await shown(xp);                                  // (a) 全程没动过指针
  const lB = await inDrawn(xp);
  await xp.mouse.move(xx + 40, xy, { steps: 6 });              // (b) 再动一下指针
  await sleep(350);
  const xC = await shown(xp);
  const lC = await inDrawn(xp);
  t('㉑ 换看法**不压**读数：换的那一趟还在飞时亮着、换完不碰指针也亮着、再动一下还亮着且数是对的',
    sigOn && xA.on && !!clicked && /换看法/.test(wBadge) && xW.on && m1 === clicked
      && xB.on && lB.found && lB.match && xC.on && lC.found && lC.match,
    `换之前 ${m0}（on=${xA.on} 收=${xA.c}${xA.on ? '' : ' ⇒ 这格是空转'}）⇒ 点「${clicked}」，`
    + `回显变成 ${m1}（没变就是没换成）｜那趟还扣在手里时 on=${xW.on}（状态「${wBadge}」——不是"换看法"就说明这眼落在换完之后）`
    + `｜指针没动那一段：${seq.join('')}（1=亮）⇒ on=${xB.on} 收=${xB.c} ${lB.tm}`
    + `（当时那份首根 o=${lB.firstO}，${lB.found ? (lB.match ? '数对得上' : '**close 对不上**') : '**没有那一刻**'}）`
    + `｜再动一下 on=${xC.on} 收=${xC.c} ${lC.match ? '对得上' : '**对不上**'}｜状态「${badge}」`);
  await xp.screenshot({ path: path.join(OUT, 'measure-swap.png'), clip: { x: xbox.x, y: xbox.y, width: 620, height: 180 } });
  await xp.close();
  await xctx.close();

  // ================================================================ ㉒ 署名那颗日期按**本地钟**
  // Nova 2026-10-06 12:28Z 定的口径：这一格答的是「今天几号」，读的人是看图的人 ⇒ 跟页头那两格同类，
  //   按浏览器本地时区印。作者侧的那颗时间戳本来就不该跟着"打开页面的时刻"变。
  // ★ 怎么摆才不是替身：挑两个**相差 25 小时**的时区 —— +14 和 −11。差 25h > 24h ⇒ 它们的日历
  //   **永远不是同一天**，两支页面印出来的日期**必须不同**。
  //   写成 UTC 那版（老代码）两支印的是同一个 UTC 日期 ⇒ 这一格必红。
  //   ★ 这一半**跟"现在几点"无关**：跑在一天里的任何一刻判据都咬得住，不会像"挑个时段才红"的摆法那样空转。
  // ★ 但它只证「两边不一样」，不证「值是对的」（印成 UTC+X 的胡编也能不一样）⇒ 再各自对一次**真值**：
  //   同一刻用 Intl 在那个时区里算出来的今天。真值那半留 ±1 小时容差 —— 读页面的那一刻正好压在这两个
  //   时区的午夜上时，本地日期会自然翻页，那是**时间在走**、不是页面错。（容差只够跨一次午夜，
  //   咬 UTC 那版的两半各差 14h／11h，仍然咬得住。）
  scen({ tick: 0.1 });
  const TZ_A = 'Pacific/Kiritimati';                         // UTC+14
  const TZ_B = 'Pacific/Midway';                             // UTC−11
  const dateIn = (tz, d) => new Intl.DateTimeFormat('sv-SE',
    { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' }).format(d || new Date());
  const nearToday = (tz) => [...new Set([-3600e3, 0, 3600e3]
    .map((k) => dateIn(tz, new Date(Date.now() + k))))];
  const readToday = async (tz) => {
    const c = await newCtx({ viewport: { width: 1280, height: 800 }, timezoneId: tz });
    const q = await open(c, '?symbol=ZECUSDT&tf=1h&last=300');
    const v = ((await q.locator('#today').textContent()) || '').trim();
    await q.close();
    await c.close();
    return v;
  };
  const todayA = await readToday(TZ_A);
  const expA = nearToday(TZ_A);
  const todayB = await readToday(TZ_B);
  const expB = nearToday(TZ_B);
  t('㉒ 角上署名那颗日期按**浏览器本地钟**印（不是 UTC）：两个相差 25 小时的时区，「今天」必须印成不同的两天',
    todayA !== todayB && expA.includes(todayA) && expB.includes(todayB),
    `${TZ_A}(UTC+14) ⇒ ${todayA}（该是 ${expA.join('／')}）｜`
    + `${TZ_B}(UTC−11) ⇒ ${todayB}（该是 ${expB.join('／')}）`
    + `｜UTC 今天 = ${dateIn('UTC')}`
    + (todayA === todayB ? '　★ 两边印成同一天 ⇒ 这格印的是 UTC 那版' : ''));

  // ================================================================ ㉓–㉚ 级别对照（卡 card-01961644-68f，L-9）
  // ★ 怎么摆才不是替身（这一族的全部摆法都在这几行里）：
  //   ① 样本里**一个合成框都没有** ⇒ 自己合成五个（`lvBox`，见上），X0/X1 全落在最后 200 根里、
  //      `?last=200` 一定看得见；DD/GG 取真 bars 的低/高 ⇒ 一定不会被"纵坐标出屏"跳过。
  //   ② `/api/levels` 跟 `/api/chart` 只有**同下标**这一条契约（`levels.units[i]` 对 `trend.units[i]`）
  //      ⇒ 两份载荷的**条数与次序**都得对得上：`ALL5` 的顺序就是屏上那五个框的顺序。
  //      ★ 这里**不许**给 levels 那几条编 `X0` 之类的字段（第一版编过，七格全绿而线上全瞎）。
  //   ③ 时区钉成 UTC：起点／第一个中枢那两个 `MM-DD` 是拿浏览器本地钟印的，不钉死就是在量机器的钟。
  const U_A = lvBox(4860, 4880, 3), U_B = lvBox(4890, 4910, 3), U_C = lvBox(4920, 4940, 3),
        U_D = lvBox(4950, 4970, 3), U_E = lvBox(4980, 5000, 3);
  // 五档摆成这样（share 的档数就是 L-9 分三档的依据）：
  //   A mismatch：share 2 档            ⇒ 「1 小时图上不一样」
  //   B mismatch：share 1 档 ＋ gap 40 ⇒ 「中间一段空着」
  //   C mismatch：share 0 档 ＋ gap 100⇒ 「1 小时图没有中枢」
  //   D match / E partial              ⇒ **一个字都不出**（L-9：match 是整个落在同一个中枢里，
  //                                        partial 只落在图头/图尾那两截、不算分歧）
  const LVM = [
    [U_A, 'mismatch', [{ i: 1, pct: 40 }, { i: 2, pct: 45 }], { pre: 15, gap: 0, post: 0 }],
    [U_B, 'mismatch', [{ i: 2, pct: 60 }],                     { pre: 0, gap: 40, post: 0 }],
    [U_C, 'mismatch', [],                                      { pre: 0, gap: 100, post: 0 }],
    [U_D, 'match',    [{ i: 3, pct: 100 }],                    { pre: 0, gap: 0, post: 0 }],
    [U_E, 'partial',  [],                                      { pre: 0, gap: 0, post: 100 }],
  ];
  // ★★ 这一份的**字段形状照着实拍载荷写**（Bram 线上 ZEC 15m 抓回来的那一条）：
  //   `{"status":"unmeasured","share":[],"outside":null}` —— 一条就三样，**没有 `X0`／`X1`／id**。
  //   第一版这里写过 `X0: u.X0`（照 spec 的"按 box start 对齐"想当然），于是七格全绿、线上一个标都不出。
  //   左边那个 `u` 现在**只用来排次序**（下标就是身份，见 layers.js `lvAligned`）。
  const lvUnits = (rows) => rows.map(([, status, share, outside]) => ({ status, share, outside }));
  const LV_START_DIFF = { status: 'differs',
    finest: { price: 191.35, t: Date.UTC(2026, 2, 8) / 1000 },
    here:   { price: 205.07, t: Date.UTC(2026, 2, 29) / 1000 },
    first_center_t: Date.UTC(2026, 2, 29) / 1000 };
  const ALL5 = [U_A, U_B, U_C, U_D, U_E];
  // 「高一级」默认关着 ⇒ 合成框不画、标也没地方挂。这一族一律先把它点开（页面里点，跟用户一模一样）。
  const openLv = async (ctx, q) => {
    const p = await open(ctx, q);
    await p.evaluate(() => { const c = document.querySelector('button.chip[data-key="up"]');
      if (c && c.getAttribute('aria-pressed') !== 'true') c.click(); });
    await sleep(500);
    return p;
  };
  // 每一枚标都钉在某个框的**右沿**（x1−6）⇒ 拿锚点去认领："这个框被标了没有"。
  //   ★ 认领时把「升级」那两字滤掉（它钉在**左沿** x0+6，是这一层的另一批字，不是级别对照的字）。
  const anchorsOf = async (p, units) => {
    const m = {};
    for (const u of units) m[u.X0] = await tagAnchor(p, u.X1);
    return m;
  };
  const lvAt = (probe, anchors, X0) => probe.labels.filter((l) =>
    l.tx !== '升级' && anchors[X0] !== null && anchors[X0] !== undefined && Math.abs(l.x1 - anchors[X0]) <= 1.5);

  // ㉓ 三档 mismatch（＋三档短标都 ≤8 字）＋ 锚点真在框右沿
  //   ★ 字数：brief 那条「≤8 字」是**约数**，三档的**原话**才是判据（`1 小时图上不一样` 数是 9 个字符）——
  //     这一格锁的是**原话**；字数只用来挡"跑飞的长句"，不是拿来裁掉一个字的。
  scen({ tick: 0.1, units: ALL5, levels: { ref_tf: '1h', start: LV_START_DIFF, units: lvUnits(LVM) } });
  const lctx = await newCtx({ viewport: { width: 1280, height: 800 }, timezoneId: 'UTC' });
  const lp = await openLv(lctx, '?symbol=ZECUSDT&tf=1h&last=200');
  const lv1 = await lvProbe(lp);
  const anc = await anchorsOf(lp, ALL5);
  const tA = lvAt(lv1, anc, U_A.X0), tB = lvAt(lv1, anc, U_B.X0), tC = lvAt(lv1, anc, U_C.X0);
  t('㉓ 三档 mismatch 各有各的一句话（照原话），且钉在**框右沿** x1−6（右对齐、不夹回视口）',
    lv1.boxes.length === 5 && tA.length === 1 && tA[0].tx === '1 小时图上不一样' && tA[0].tx.length <= 10
      && tB.length === 1 && tB[0].tx === '中间一段空着' && tB[0].tx.length <= 10
      && tC.length === 1 && tC[0].tx === '1 小时图没有中枢' && tC[0].tx.length <= 10
      && tA[0].x0 < tA[0].x1 && anc[U_A.X0] !== null && Math.abs(tA[0].x1 - anc[U_A.X0]) <= 1.5,
    `屏上 ${lv1.boxes.length} 个合成框｜A⇒「${tA.map((l) => l.tx).join('') || '（没标）'}」（锚距 ${tA[0] ? Math.abs(tA[0].x1 - anc[U_A.X0]).toFixed(2) : '?'} px）`
    + `｜B⇒「${tB.map((l) => l.tx).join('') || '（没标）'}」｜C⇒「${tC.map((l) => l.tx).join('') || '（没标）'}」`);

  // ㉔ match／partial **不出字**（L-9）—— 而且必须在**同一份载荷里**跟三档 mismatch 一起量：
  //    整层没画（比如「高一级」关了）也是"没字"，那种绿是假的。⇒ 先认领 A 有字，才认 D／E 的"没字"。
  const tD = lvAt(lv1, anc, U_D.X0), tE = lvAt(lv1, anc, U_E.X0);
  t('㉔ match／partial **不出字**（L-9）—— 同一份载荷里 mismatch 照旧出字，所以这不是"整层没画"',
    tA.length === 1 && tD.length === 0 && tE.length === 0,
    `A（mismatch）标了 ${tA.length} 枚｜D（match）标了 ${tD.length} 枚｜E（partial）标了 ${tE.length} 枚`
    + `（D/E 要 0；A 要 ≥1，否则这一格量的是"整层没画"）`);

  // ㉕ 开关的**从属关系**：`lv` 与 `up` 与过（shownOf）⇒「高一级」关着时它按灰、也没地方挂字
  const chipOf = () => lp.evaluate(() => {
    const g = (k) => { const c = document.querySelector(`button.chip[data-key="${k}"]`);
      return c ? { on: c.getAttribute('aria-pressed') === 'true', dis: !!c.disabled } : null; };
    return { up: g('up'), lv: g('lv') };
  });
  const tap = (k) => lp.evaluate((k) => { const c = document.querySelector(`button.chip[data-key="${k}"]`); if (c) c.click(); }, k);
  await tap('lv'); await sleep(400); const lvOff = await lvProbe(lp);
  await tap('lv'); await sleep(400);
  await tap('up'); await sleep(400); const upOff = await lvProbe(lp); const csOff = await chipOf();
  await tap('up'); await sleep(400); const lv2 = await lvProbe(lp); const csOn = await chipOf();
  const lvCount = (pr) => ALL5.reduce((n, u) => n + lvAt(pr, anc, u.X0).length, 0);
  t('㉕ 「级别对照」那颗芯片关掉 ⇒ 标全没（框还在）；「高一级」关掉 ⇒ 标也没（lv 与 up 与过），且它按灰',
    lvCount(lv1) === 3 && lvOff.boxes.length === 5 && lvCount(lvOff) === 0
      && upOff.boxes.length === 0 && lvCount(upOff) === 0 && csOff.up.on === false && csOff.lv.dis === true
      && csOn.up.on === true && csOn.lv.dis === false && lvCount(lv2) === 3,
    `开＝${lvCount(lv1)} 枚｜关 lv⇒${lvCount(lvOff)} 枚（框仍有 ${lvOff.boxes.length} 个）`
    + `｜关 up⇒标 ${lvCount(upOff)} 枚、框 ${upOff.boxes.length} 个，lv 芯片 disabled=${csOff.lv.dis}`
    + `｜开回来⇒${lvCount(lv2)} 枚（lv disabled=${csOn.lv.dis}）`);

  // ㉖ 起点那句话（L-7）：`differs` ⇒ 报事实的三截（起点／图头那一刀「会变」／本图第一个中枢）；
  //    ★ **不许有裁决** —— 后台的 `differs` 只证明"两刀不一样"、不证明"为什么"，写死一句"这不是分歧"
  //      必然在另一种来源（换窗口）上说错（Nova 14:09Z，card-6e338490）。
  const head1 = lv1.head || '';
  t('㉖ 起点那句话（L-7）：`differs` ⇒ 起点按细图算 ＋「会变」＋ 本图第一个中枢；**不下"算不算分歧"的裁决**',
    head1.includes('起点按 15 分钟图算在 03-08（') && head1.includes('），以细图为准')
      && head1.includes('这是15 分钟图的图头那一刀') && head1.includes('窗口一变会跟着挪（「会变」）')
      && head1.includes('本图第一个中枢 03-29 开始')
      && !head1.includes('这不是级别分歧'),
    `那一行话＝「${head1}」`);
  await lp.screenshot({ path: path.join(OUT, 'level-link.png'), clip: { x: 0, y: 0, width: 1280, height: 400 } });
  await lp.close();
  await lctx.close();

  // ㉗ `levels: null`（接口没有这一层）⇒ **一个标都不画、一个字都不说**（fail-closed），
  //    而且浮层那点内容**不占流** —— `#chart` 的高度跟 ㉑ 那页（那一行话老长）**一模一样**。
  scen({ tick: 0.1, units: ALL5, levels: null });
  const nctx = await newCtx({ viewport: { width: 1280, height: 800 }, timezoneId: 'UTC' });
  const np = await openLv(nctx, '?symbol=ZECUSDT&tf=1h&last=200');
  const null1 = await lvProbe(np);
  const nullLv = null1.labels.filter((l) => l.tx !== '升级').length;
  t('㉗ `levels: null`（这一层不存在）⇒ 不画标、不说话；且浮层**不占流**（#chart 高度跟有那一行话时一致）',
    null1.boxes.length === 5 && nullLv === 0 && !(null1.head || '').trim() && null1.headOn === false
      && Math.abs(null1.chartH - lv1.chartH) < 0.6,
    `框 ${null1.boxes.length} 个（还画着）｜非「升级」的标 ${nullLv} 枚｜那一行话「${null1.head || ''}」（on=${null1.headOn}）`
    + `｜#chart 高 ${null1.chartH.toFixed(1)} vs 有那一行话时 ${lv1.chartH.toFixed(1)}`);
  await np.close();
  await nctx.close();

  // ㉘ `unmeasured` ⇒ 覆盖率那句**老老实实说"没比成"**，读不出"对得上"；而且不给它画标
  scen({ tick: 0.1, units: [U_A, U_B],
         levels: { ref_tf: '1h', start: null,
                   units: lvUnits([[U_A, 'unmeasured', [], null], [U_B, 'unmeasured', [], null]]) } });
  const uctx = await newCtx({ viewport: { width: 1280, height: 800 }, timezoneId: 'UTC' });
  const up2 = await openLv(uctx, '?symbol=ZECUSDT&tf=1h&last=200');
  const un1 = await lvProbe(up2);
  const unLv = un1.labels.filter((l) => l.tx !== '升级').length;
  t('㉘ `unmeasured`（对照图没缓存）⇒ 覆盖率老实说「没比成」，读不出"对得上"；且不给它画标',
    un1.boxes.length === 2 && unLv === 0 && /2 个框/.test(un1.head || '')
      && /0 个比过/.test(un1.head || '') && /2 个没比成/.test(un1.head || '')
      && !/对得上|一样/.test(un1.head || ''),
    `那一行话＝「${un1.head || ''}」｜非「升级」的标 ${unLv} 枚`);
  await up2.close();
  await uctx.close();

  // ㉙ `start.status: 'same'` ⇒ **一个字都不说**（后台 `start_link`：一样＝不标；见 app.js `levelsStartText`）
  scen({ tick: 0.1, units: [U_D],
         levels: { ref_tf: '1h', start: { status: 'same', finest: { price: 205.07, t: Date.UTC(2026, 2, 29) / 1000 },
                   here: { price: 205.07, t: Date.UTC(2026, 2, 29) / 1000 }, first_center_t: Date.UTC(2026, 2, 29) / 1000 },
                   units: lvUnits([[U_D, 'match', [{ i: 3, pct: 100 }], { pre: 0, gap: 0, post: 0 }]]) } });
  const smctx = await newCtx({ viewport: { width: 1280, height: 800 }, timezoneId: 'UTC' });
  const smp = await openLv(smctx, '?symbol=ZECUSDT&tf=1h&last=200');
  const same1 = await lvProbe(smp);
  t('㉙ 起点 `same`（后台判"一样"）⇒ 一个字都不说 —— 在"一样"上贴一句话＝凭空捏一个分歧出来',
    same1.boxes.length === 1 && !(same1.head || '').trim() && same1.headOn === false,
    `那一行话「${same1.head || ''}」（要空）｜on=${same1.headOn}｜框 ${same1.boxes.length} 个`);
  await smp.close();
  await smctx.close();

  // ㉚ 对齐闸（card-01961644-68f）：`levels.units` 跟框**只有"同下标"这一条契约**（没有身份字段）
  //    ⇒ 载荷回显的**周期／档位／条数**只要有一条对不上，就**一个标都不画**（保守那一边）。
  //    ★ 两种错法各开一页，量的是同一件事：**框照画**（5 个 ⇒ 证明不是"整层没画"）、**字一个都没有**。
  //      a) **档位**对不上 —— 这是"旧快照"那条路：往左补数据之后 span 变了，两份载荷的框数往往还一样，
  //         条数那道闸拦不住它，只有回显的 span 拦得住。
  //      b) **条数**对不上 —— 后台少算/多算一个框 ⇒ 同下标**整体错位**，比"不标"坏得多（错位的标一样是"有字的"）。
  //    ★ 正对照就在 ㉓：同一份五个框、回显对得上 ⇒ 三枚标。所以这两格量的是"闸"，不是"整层坏了"。
  const ALIGN_CASES = [
    ['㉚a 档位对不上', '回了一份旧档的载荷（`span: 4`，屏上这一份是 1）', { span: 4 }],
    ['㉚b 条数对不上', '只回了 4 条（屏上 5 个框）', { units: lvUnits(LVM.slice(0, 4)) }],
  ];
  for (const [cell, name, patch] of ALIGN_CASES) {
    scen({ tick: 0.1, units: ALL5,
           levels: Object.assign({ ref_tf: '1h', start: null, units: lvUnits(LVM) }, patch) });
    const actx = await newCtx({ viewport: { width: 1280, height: 800 }, timezoneId: 'UTC' });
    const ap = await openLv(actx, '?symbol=ZECUSDT&tf=1h&last=200');
    const apr = await lvProbe(ap);
    const aanc = await anchorsOf(ap, ALL5);
    const onScreen = ALL5.filter((u) => aanc[u.X0] != null).length;   // 锚点在屏上的框数（0 枚标要是因为"看不见"就白量了）
    const anyTag = ALL5.reduce((k, u) => k + lvAt(apr, aanc, u.X0).length, 0);
    t(`${cell} 对齐闸：${name} ⇒ 一个标都不画（但框照画 —— 这不是"整层没画"）`,
      apr.boxes.length === 5 && onScreen === 5 && anyTag === 0,
      `框 ${apr.boxes.length} 个（要 5）｜锚点在屏上的框 ${onScreen}/5｜这一层出的标 ${anyTag} 枚（要 0）`);
    await ap.close();
    await actx.close();
  }

  await b.close();
  console.log(`\n${ok.length}/${ok.length + bad.length} 绿`
    + (errors.length ? `　★ 页面报错 ${errors.length} 条：\n   ` + errors.slice(0, 5).join('\n   ') : ''));
  if (bad.length) { console.log('红的：'); for (const x of bad) console.log('  ✗ ' + x); }
  console.log('截图 →', OUT);
  process.exit(bad.length || errors.length ? 1 : 0);
})().catch((e) => { console.error('工装自己炸了：', e); process.exit(3); });
