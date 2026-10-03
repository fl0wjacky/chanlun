# web/ —— chanlun.surfers.cc 的前端

小栋 2026-10-03 定：这个站**公开可看**（后台是 Bram 那张卡 `card-29a45ab6-0ac`）。这一层只做**看**：
取数、画图、开关。没有任何写入口。

## 怎么跑

这一层就是一个静态目录：起一个**只监听回环**的静态服务指向 `web/`，打开对应地址并带上 `?symbol=&tf=`
（不带就是默认的 BTCUSDT / 4h）。后台没起时前端自动退回仓里的样本，所以离线也能看、也能截图对账。

两条纪律（都踩过，所以单独立着）：
- **服务只许绑回环**：`python3 -m http.server` 这类工具**默认绑全网卡**，照默认起就是把这层直接露在网络里
  —— 起之前显式绑回环地址，起来后自己核一眼监听的是哪个地址（`lsof -nP -iTCP:<port>`）。
- **部署口径不写进仓**：在哪台机器、什么端口、进程怎么常驻、日志放哪，都不属于这个目录要记的事
  （小栋 2026-10-03 定：部署细节不进仓库）。这里只写「这一层是怎么工作的」。

URL 参数（都可分享 / 可截图复现同一段）：

| 参数 | 作用 |
|---|---|
| `symbol` / `tf` | 白名单外的值**不认**，退回默认（BTCUSDT / 4h）—— 跟后台卡的白名单口径一致 |
| `last=N` | 只看最后 N 根（手机上看得清一点） |
| `at=N&span=M` | 看第 N 根前后 M 根：验收截图就是靠它把网页和 Python 出图对准同一段 |

正式跑由后台那一个进程把静态页一起送出来（同源 ⇒ 前端请求 `/api/chart?symbol=&tf=` 直接命中，
不用配 CORS、也不用写死地址）。

## 数据形状（前后台之间唯一的契约）

一份 JSON，字段就这些 —— 形状的**可执行定义**是 `tools/make_web_fixture.py`，改形状就改它、重烤样本：

| 字段 | 内容 |
|---|---|
| `symbol` / `tf` / `name` | 标的、周期、显示名 |
| `updated` | 最后一根 K 线的开盘时间（UTC，`…Z`）——角落那格显示的就是它 |
| `closed` | 最后一根是否已收盘；`false` 时图上给那根加虚线框并标「未收盘」 |
| `stale` / `fetched_at` | 后台那层才有的两个：拉币安的时刻、以及「这轮没拉到、回的是上一次的结果」。`stale` 为真时角上那格标「★ 旧数据」。**没有这两个字段（样本就没有）也照样跑**，当成不是旧数据；想看那格长什么样：`tools/make_web_fixture.py <file> --stale` |
| `bars[]` | `{t(ms), o, h, l, c}` |
| `pens[]` | `{i0,p0,i1,p1}`（K 线下标 + 价） |
| `segs[]` | `{i0,p0,i1,p1,dir,PI0,PI1,hi,lo,live?}`；`live` 的那条画到迄今的极值 |
| `centers[]` / `seg_centers[]` | `{PI0,PI1,ZD,ZG,live,up[{ZD,ZG,up}]}`；横跨区要靠 `PI0/PI1` 回查宿主（笔 / **已完成**线段） |
| `signals` | `{seg[], pen[]}`，元素 `{kind,bar,price,confirmed,weak}` —— **引擎算好送过来** |
| `big[]` | 相邻两中枢「扩展」合出来的高一级类中枢（`core/extend.py` `build_hierarchy`，`nmerge>1` 才是真合成）。`members` 是成员在 `centers[]` 里的 `PI0`。**前端现在不画这一层**（Python 出图 `chart_full_smooth.py` 也只画 `up`、不画 `big`），带上是为了把数据给全；要画是产品决定 |
| `meta` | `{tick, pen_rule, min_gap}` 口径，只读展示 |

★ 前端**不判信号**、不重算结构：判据只许有一处（`core/signals.py`），前端画两处必然分家。

★ `big` 与中枢里内嵌的 `up[{ZD,ZG,up}]` **不是一回事**：`up` 是**一个**中枢自己延伸满 9 段升上去的
（第 33 课，`center.upgrades`），前端画的「↑高N级」就是它；`big` 是**相邻两个**中枢合出来的。别混。

## 画法从哪儿来

不是这里定的，是从两处搬的，改的时候要一起改：

- **颜色 / 线宽 / 填充 → `render/style.py` 的 `CHART`**（`web/theme.js` 抄一份，出处写在每一行右边）
- **几何与虚实 → `render/full_common.py`**：`box_split` 的三档（规则 B：前三里夹着未走完的那笔 ⇒ 整框虚线；
  已结束 ⇒ 整框实线；仍在延续 ⇒ 前三那截实线、延续那截虚线）、`draw_signals` 的三角尺寸与偏移、
  `draw_labels` 的「先到先得、最多往上挪 12 行」、未完成线段画到迄今极值、未收盘那根的虚线框
- **线宽 → `tradingview/chanlun.pine` 的输入默认值**（笔 1 / 段 2）。**不**按 Python 那张 17592 px 的位图
  等比缩 —— 按那个缩到屏幕上只剩零点几像素，等于没有线；pine 的取值本来就是给小栋在真机上看的选择。

**开关默认值也照 TradingView**：笔 / 线段 / 线段中枢 → 开；**类中枢、高一级、买卖点 → 关**（卡面点名的一条）。
买卖点在 TradingView 那边是六个独立开关（一买…三卖）全默认关；这里收成一个主开关 + 六个筛选，
主开关默认关 —— 六个独立开关同时默认关，用户打开「买卖点」会看到一个空面板，那不是一致，那是个坑。

**虚线**：lightweight-charts 只给几种预设，给不了 Python 那边的 dash 长度（16/10、26/16…）。
所以虚线上守的是**实/虚二分与谁虚**，不追长度（`theme.js` 的 `DASH` 那段写了这个取舍）。

## 五把尺

```bash
python3 tools/web_theme_sync.py              # ① 色/线宽跟 style.py ＋ chanlun.pine 逐格比；不对就 rc=1
python3 tools/web_theme_sync.py --selftest   #    探针：改错一格必须变红（证明这把尺真会红）
python3 tools/web_footer_check.py            # ② 图脚「买卖点」那段在 390px 下放不放得下一行
python3 tools/web_footer_check.py --selftest #    探针：六格都得变红
python3 web/check_parity.py                  # ③ 结构与 Python 逐根对账（9 份数据 / 2707 个结构；要 PIL）
python3 tools/web_fmt_check.py               # ④ 价签数字 ≡ Python 的 `"%g" % round(v, 2)`（逐字相同）
python3 tools/web_fmt_check.py --selftest    #    探针：六格都得变红（含「取整交给 toFixed」那版）
python3 tools/web_fitbox_check.py            # ⑤ 文字落框：不出视口 / 有空格子就不许压 / 横不动 / 高不变
python3 tools/web_fitbox_check.py --selftest #    探针：八格都得变红（含 tag() 里「夹右边界」的顺序）
```

尺 ② 是 2026-10-03 联调补的：图脚那段买卖点文字原来是**逐个信号列出来**的，长度跟着**信号数**涨 ——
仓里的样本只有 4~17 个信号（最长 50 字符），看着就是一句归纳，配色尺和并排图全是绿的；换成后台的
实时源（ZECUSDT 15m，20160 根）一次 66 个信号 ⇒「类中枢层」那一层列表 197 字符 ≈ 1598px
（实测 1549.6px），图脚那一格只有 362px ⇒ 连标签整段在手机上糊成八行。
**样本比线上小两个数量级，尺子就量不到。** 所以这把尺量的是**实时规模**的样本
（`web/fixtures/signals_zec15m_live.json`），判据是「**每个层级**那段『标签＋列表』整句 ≤ 一行」——
主语和宽度都写死（390px 视口、图脚格 362px、字号 10px），不然同一句规则两个结果；
量的是**整句**不是光量列表，标签**从 `app.js` 的模板里读**（改名自动跟，抠不到就报错）——
只量列表会假绿：列表卡在 44 字时加上标签就是 47 字 ≈ 381px，其实要换行（尺 ⑤ 那格探针专钉这个）。

尺 ④ 钉的是**读数**，不是审美：中枢区间的上下沿就是判三买三卖的**价**，`1681.99` 显示成 `1682`
就"像破了"、其实没破。取整那一步**不能交给 `toFixed`/`toPrecision`** —— 它俩"正好一半就进位"，
Python 的 `round()`/`%g` 是"一半取偶"，`100000.5` 两边差 1；所以 `fmtG()` 自己把 20 位有效数字摊开、
判第 7 位起有没有过半。探针里有一格专门拿"取整交给 toFixed"的那版去撞（**必红**）。

尺 ⑤ 钉的是**落框**（价签和买卖点文字**共用**的那一份 `fitBox()`）：网页是视口，没有 Python 整幅图
顶上那 300px 边距，所以框要**夹两头**（上沿不得 < 0、下沿不得 > 画布高，都是**整框移、不改高**）、
撞上了要挪（跟 `draw_labels` 同一条：**判 12 个候选行**；上沿顶到 0 之后**往下试**）。
判四样：**落点逐坐标 / 不出视口 / 横不动**（锚点是那根 K 线，横着挪＝把标签从它的点上挪开，
所以左边刻意不夹）**/ 高不变**。它另抠出 `tag()` 配一个假 ctx 跑一格：**夹右边界必须在避让之前**，
否则推回来的框没人复查碰撞（Atlas 指出的一处老顺序）。

`web/theme.js` 是**唯一**写色值的地方：`style.css` 里除了 `:root` 那几个「JS 没跑起来时别白屏」的兜底，
一个色都不许写死（值由 app.js 灌进 CSS 变量；**连徽标边框那种「同色压到底色上」的值也在 JS 里算**）。
尺子会核 `:root` 的兜底跟 `theme.js` 是不是同一个色，也会在 `:root` 之外扫到裸色值就变红 ——
这条不是洁癖：`.badge.live` 里曾经写死过 `#ffbc3c`，而 `style.py` 的 `AM` 是 `#ffbe3c`，差 2，
当时尺子只读 `theme.js`，看不见。
`web/vendor/lightweight-charts/VERSION.txt` 里记着那个 js 的 sha256，尺子会核对 —— 图省事改库文件会当场变红。

## 目录

```
web/
  index.html   app.js      接线：取数 → 建图 → 开关 → 角上的时间
  style.css    layers.js   结构层：中枢框（拆两截）、价签、买卖点、未收盘那根
  theme.js     配色与线宽（唯一出处；出处写在每行右边）
  vendor/lightweight-charts/   TradingView 的 lightweight-charts 5.2.1（Apache-2.0，本地打包，不走 CDN）
  fixtures/    离线样本：btc_4h / zec_1h 由 tools/make_web_fixture.py 烤；另有一份
               signals_zec15m_live.json 是**从后台实时源存下来的图脚样本**（20160 根），
               只喂给尺 ② 用，不是给页面看的
```

**图例**不是装饰：每一项的样例直接取 `theme.js` 的色与线宽画出来 —— 图例和图上不一样，
图例就是唯一一处说假话的地方（Python 那边 `full_common.legend` 的注释记的是同一条账）。
