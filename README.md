# chanlun_mag — 缠论结构分析与概念卡

把《教你炒股票》里"包含处理 → 分型 → 笔 → 线段 → 中枢 → 扩展"这条链实现成可跑、可自检的代码，
并用它做两件事：**分析真实行情**（和闭源指标对账）、**画概念卡**（一张卡讲一个概念）。

---

## 目录结构

```
chanlun_mag/
├── config.py                ★ 路径 / 字体 / 产物目录（脚本一律从这里取，不要硬编码）
├── core/                    ★ 引擎：K线标准化 → 分型 → 笔 → 线段 → 中枢 → 扩展
│   ├── kline.py             standardize() / fractals() / 两个自检函数（第 65 课）
│   ├── pen.py               build_pens()
│   ├── segment.py           build_segments()（第 67 课定义 + 第 71 课分界点规则，唯一口径）/ verify_by_definition()
│   ├── center.py            find_centers()、classify_pair()（第 17 / 20 / 22 课）
│   ├── extend.py            build_hierarchy() —— 扩展合成大级别中枢（第 49 / 52 课）
│   └── analyze.py           analyze() —— 对外唯一入口：笔、笔中枢、线段、线段中枢一次给全
├── render/                  出图：真实数据图 + 截图标注
│   ├── style.py             字体 / 配色 / 坐标映射 / 虚线 / 三角（公共层）
│   ├── chart_levels.py      双级别对照图（4H vs 30m）
│   ├── chart_nested.py      级别递归实证图：笔中枢 → 扩展合成 → 上一级中枢
│   ├── chart_zec_segments.py ZEC 15 分钟概览：笔、线段、线段中枢（画最后 16 条线段）
│   ├── chart_zec_full.py    ZEC 15 分钟全量高清图 · 按月分面板（每月纵轴各自缩放，细节最满）
│   ├── chart_full_smooth.py 全量顺滑版 · 任意标的 / 周期（全程一根对数价格轴，不拼接、不变形）
│   ├── chart_zec_full_smooth.py 上面那个的 ZEC 15 分钟预设
│   ├── full_common.py       全量图 / 概览共用的画法：结构层 / 标签避让 / 图例 / 价格刻度
│   ├── shot_calib.py        截图的像素 ↔ 价格 / 日期标定（两个截图脚本共用，数字一律由它现算）
│   ├── chart_annotate.py    在 TradingView 截图上标笔与中枢（需截图）
│   └── chart_signals.py     在截图上标三类买卖点（需截图）
├── cards/                   概念卡（一卡一概念）
│   ├── base.py              页眉 / 页脚 / 要点 / 简笔图元 / section · callout · lchip
│   ├── c01_containment.py   01 包含处理
│   ├── c02_fractal.py       02 分型
│   ├── c03_pen.py … c09_buypoints.py
│   ├── c04plus_featureseq.py / c04c_fourcases.py / c04d_twoways.py   线段补充卡 04b / 04c / 04d
│   ├── model_dissent.py     框架卡：共识 → 分歧 → 证实 / 证伪
│   ├── level_recursion.py   框架卡：级别与递归
│   └── build_all.py         逐张调用各卡 build()，单张存盘 + 拼成一张长图
├── tools/
│   ├── selfcheck.py         ★ 跑全部不变量检查
│   ├── fetch_klines.py      拉币安永续 K 线（无参数 = AAPL 卡片数据；`ZECUSDT 15m --days 210 --out zec15.json` = 拉到当前）
│   ├── extract_chart_pens.py 从截图里提取笔折线顶点（需截图）
│   ├── fetch_chanlun108.py  ★ 抓《教你炒股票》108 课全文到本地（--reparse：不联网，从 raw/ 重新提取）
│   ├── find_original.py     ★ 在本地全文里检索（带上下文）
│   ├── term_stats.py        术语词频统计（生成 docs/术语别名表.md 的数字）
│   ├── verify_c03.py / verify_c05.py  卡片示意数据的引擎回算
│   ├── verify_c06_c07.py    c06 / c07 / chart_nested / 框架卡上实测数字的引擎回算（对不上即非零退出）
│   ├── check_*.py           笔的连续性 / 端点落位 / 同类相遇 的专项验证
│   ├── ab_segment.py        线段：旧整序列口径 vs 现行口径 的稳定性对照（扰动一根K线）
│   ├── calibrate_*.py       线段层与中枢稳定性的校准实验（第 83 课）
│   ├── offset_sensitivity.py 起点不同，笔与线段是否一致
│   └── build_pdf.py         把概念卡拼成手机版 PDF
├── docs/术语别名表.md       原文一词多写对照（检索前先看）
├── data/                    K 线与提取结果（可重新生成，别手改）
│   ├── aaplusdt_*.json      AAPL 永续 2026-07-26 – 09-27（c01–c05、框架卡、chart_levels / nested）
│   ├── zec15.json / zec_{1h,2h,4h}.json  ZEC 永续约 210 天、拉到当前（c06 / c07 实证、ZEC 线段图）
│   └── btc_4h.json          BTC 永续 4 小时，2025-10-01 起拉到当前（BTC 全景顺滑版）
├── out/                     本机产物目录（自动创建，可随时删）
└── archive/
    ├── chanlun108/          ★《教你炒股票》108 课全文（本地副本）
    │   ├── raw/             原始页
    │   ├── text/            每课正文纯文本
    │   ├── 全文.txt         合并版（检索用）
    │   └── 目录.txt         序号 + 标题
    ├── oneoff/              一次性修补脚本
    └── debug_crops/         调试截图
```

---

## 常用入口

```bash
# —— 原文检索：先用本地，本地没有再联网 ——
python3 tools/find_original.py --toc                 # 列 108 课目录
python3 tools/find_original.py --lesson 20           # 读第 20 课全文
python3 tools/find_original.py 中枢的延伸 -n 5        # 关键词 + 上下文
python3 tools/find_original.py 线段必须 三笔          # 多关键词（全部命中）

python3 tools/selfcheck.py                 # 先跑这个，确认引擎没坏
for f in tools/verify_*.py; do python3 "$f" > /dev/null || echo "✗ $f"; done   # 卡上数字是否过期
python3 tools/fetch_klines.py              # 重新拉 AAPL 卡片数据
for iv in 1h 2h 4h; do python3 tools/fetch_klines.py ZECUSDT $iv --days 210 --out zec_$iv.json; done
python3 tools/fetch_klines.py ZECUSDT 15m --days 210 --out zec15.json   # 刷新 ZEC 到当前（c06 / c07 跟着变）
python3 tools/fetch_klines.py BTCUSDT 4h --start 2025-10-01 --out btc_4h.json
python3 render/chart_full_smooth.py btc_4h.json --name "BTC/USDT 永续" --tf "4 小时" --px 8 --ph 2400   # BTC 全景顺滑版
python3 tools/extract_chart_pens.py        # 截图 → 笔顶点
python3 render/chart_levels.py             # 出双级别对照图
python3 cards/c05_center.py                # 出某一张概念卡
python3 cards/build_all.py                 # 出全部 12 张概念卡 + 合集长图
python3 tools/build_pdf.py                 # 概念卡合集 PDF（先跑上一行）
```

产物落在 `config.OUT`（见下节）。

---

## 运行环境（全部由 `config.py` 决定）

| 项 | 默认取值 | 覆盖用环境变量 |
|---|---|---|
| 产物目录 `OUT` | `/var/minis/attachments` 存在就用它（Minis 沙箱，方便贴进对话）；否则项目下 `out/` | `CHANLUN_OUT` |
| 中文字体 `FONT` | 依次找 Droid Sans Fallback（Linux）→ Arial Unicode（macOS）→ STHeiti / Hiragino → Noto CJK | `CHANLUN_FONT` |
| 截图目录 `UPLOADS` | `/var/minis/attachments/uploads`，否则项目下 `uploads/` | `CHANLUN_UPLOADS` |

- 依赖：`Pillow`、`numpy`（提取截图）、`reportlab`（仅 `build_pdf.py`）。
- 截图 `photo_26B0F906.png` 不在项目里；`chart_annotate` / `chart_signals` /
  `extract_chart_pens` 要先把它放进 `UPLOADS` 才能跑。
- **字体不同，字宽就不同**：macOS 默认用 Arial Unicode —— 中文和 ✓ ✗ ₁₂₃ 都有，字宽与黑体相差 <1%，
  但基线比黑体低约 4px。STHeiti / 冬青黑缺 ✓ ✗ ₁₂₃（显示成方框），只作后备。
  要与 Minis 沙箱逐像素一致，把 `DroidSansFallbackFull.ttf` 放进项目，用 `CHANLUN_FONT` 指过去。

---

## 引擎不变量（selfcheck 会逐条验证）

| 不变量 | 为什么重要 |
|---|---|
| 标准化序列里相邻两根**不存在包含关系** | 这是"标准化做完了"的定义 |
| 相邻两根的**高点不相等、低点也不相等** | 上一条的等价形式；一旦出现就是标准化有 bug |
| 分型的**类型严格交替** | 顶、底、顶、底…… 位置可以不连续，但类型不会连排 |
| 顶分型「4 条件」版 == 「只看高点」版 | 验证"低点也最高是自动的"这条推论 |
| 底分型「4 条件」版 == 「只看低点」版 | 同上 |
| 中枢区间 = 前三段的 [max 低, min 高]，且 ZG > ZD | 三段确实重叠才有中枢（笔中枢、线段中枢同一套检查） |
| 相邻中枢不重叠、关系标签可重算；终点是 Z 段、内部 Z 段都与区间重叠、已终结的其后 Z 段完全离开 | `check_centers()`（中心定理一） |
| 线段：笔数单数、首尾相接、方向交替；按原文定义独立复核 | `check_segments()` / `verify_by_definition()` |

---

## 记忆要点（踩过的坑）

- **只用最高价、最低价**，开盘收盘不参与任何计算（第 65 课）。
- **方向由「标准化序列的最后两根」决定**，不是看被合并的那两根。
- **合并后的东西是一个区间，没有实体和影线**。
- **分型判定必须在标准化序列上做**，不能拿原始K线图数。
- **中枢的延续 / 终结按第 20 课中心定理一**：Z 段的 [dn,gn] 与 [ZD,ZG] 重叠就延续；第一个完全离开的 Z 段
  出现，中枢终于最后一个仍重叠的 Z 段，两者之间那段是连接段，下一个中枢从离开的 Z 段找起。
  旧版用「第三类买卖点」判终结，只看终点、不看出发位置，会把「先涨破 ZG、再从上方穿过整个中枢跌破 ZD」
  误判成三卖（2026-09-29 在 BTC 4h 线段中枢上发现，已改）。三类买卖点本身的定义不变。
- 参数 `min_gap=4`（整笔至少跨 5 根K线）是"传统笔"口径，选定后不要改。

---

## 工作纪律（吃过的亏）

1. **要用原文，先查本地全文**，没有再联网 —— 源站是单页应用，随机会返回目录页，
   判断办法是看 `<title>` 里有没有「第N课」。
   - **源站文本自带重字噪声**（「如果果」「顶顶分型」，约 30 课、2000+ 处，原始页里就有）。
     `find_original.py` 已对两边都「压重字」再匹配；整句仍搜不到时改用 2–4 字短词组合，
     **搜不到 ≠ 原文没有**。引用进卡片时用去掉重字的干净原句。
   - 提取曾把公式里裸的「<」当成标签吃掉（第 20 课中心定理二 ③④ 被截），已修；
     以后改 `to_text()` 后跑 `fetch_chanlun108.py --reparse`，不必重新联网。
2. 每个说法都要能拿引擎回算验证（见 `tools/verify_*.py`）。改引擎或换数据后，跑一遍全部 verify；
   卡上改了数字，同步改 verify 脚本开头的「卡片标称」。
3. 文字宽度要量，不能凭感觉（卡片格宽固定，超了就裁字）。
4. 声称两个东西「相连」时，它们必须在同一张图上相连。
5. **批量替换要限定作用域** —— 按"行尾长相"匹配会误伤函数体内部（踩过一次）。
6. **卡片里的小图坐标一律自己加格子偏移** —— `zigp()` 只吃裸像素 x、不吃 Mini 的框，
   抄同一个 pts 到右边的格子里，折线会叠回左边的格子（踩过一次：卡片 08 的「盘整背驰」格）。

## 卡片脚本的结构

每张卡（`cards/c0*.py` 与两张框架卡）都是同一个形状：

```python
W, H = 1400, 2500                # 卡片尺寸（模块常量，各段函数直接用）
OUTNAME = "c03_笔.png"            # 输出文件名（main 与 build_all 共用）

def draw_anatomy(d): ...         # 一节一个 draw_*，docstring 写节标题
def build():                     # set_size(W, H) → newcard → 各节 → foot，返回 Image
def main():                      # build().save(OUT + OUTNAME)
if __name__ == "__main__": main()
```

- **import 不出图**，可以在别处 `from cards.c05_center import build` 单独复用。
- `build()` 里各节的**调用顺序就是叠放顺序**，调换可能让后画的盖住先画的。
- 实测数据**出图时由引擎现算**，不手抄数字：c06 / c07 走 `cards/zec_data.py`（ZEC 线段中枢为主、笔中枢对照），
  框架卡走 `model_dissent.gap_rows()` 等。刷新数据后跑 `verify_c06_c07.py`：它另算一遍比对，
  并核对卡上无条件写死的定性说法（「扩展占多数」「结构层级大致对应」）是否仍成立。
- 通用片段在 `cards/base.py`：`section()` 整宽分节面板 + 标题标签，`callout()` 整宽半透明强调框，
  `lchip()` 压在线上的带底色小标签。参数对不上（圆角、缩进、描边不同）的地方保留了原写法，
  不要为了用 helper 去改坐标。
- 新增一张卡：照上面的形状写，再在 `build_all.CARDS` 里加一行（模块名, PDF 目录标题）——
  长图和 PDF 的顺序、目录都只认这一处。

---

## 已知债务

- 本机（macOS）默认字体与原版不同，版式按 Arial Unicode 调过；换回 Droid 时需再目检一遍。
- **线段终点不是段内极值：已从 129 / 2272 降到 3 / 2050**（12 标的 15 分钟）。补的都是原文规则，没有硬加「终点须为极值」：
  · 第 71 课「第一笔属於中间地带」：第一笔不参与包含；先破其结束位置新段才成立、先破开始位置旧段延续；
  · 第 78 课：第二种情况未出第二特征序列分型之前是待定，先被新高 / 新低越过则「加起来只能算是一个线段」；
  · 两类待定期间，范围内的后续候选一律不判。
  剩下 3 段：2 段第一笔未破前段（第 71 课那段不管，按原文字面不处理）、1 段是数据开头第一段。selfcheck 只报数。
- c09 买点示意图里，一买之后的三笔会被引擎识别成一个新中枢；三买同时高于它和中枢②，判定不受影响，
  但图上「离开中枢② 后回试」的讲法与引擎口径不完全一致。

---

*署名约定：所有产出署名「冲浪者 · 日期」；卡片与图表底色统一用 `render.style.BG`。*
*画法约定：**未完成的笔 / 线段、仍在延续的中枢一律虚线**，已完成的用实线（`render.style.dashed_line` / `dashed_rect`）；
未完成线段的虚线画到迄今的极值（向上段最高、向下段最低）；最后一根未收盘的 K 线用虚线框标出；
虚线不再表示「中枢延伸段」。纯示意图（手编数据）不受此限。*
*配色约定：深底元素用 `style.py` 的主配色；画在浅色截图上的标注用 `SH_*`；
与 CHANLUN 3.0 指标原色对应的用 `IND_*`。脚本里不再写颜色字面量。*
