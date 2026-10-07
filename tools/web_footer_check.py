#!/usr/bin/env python3
"""图脚「买卖点」那段的一把尺（第三把，配 web_theme_sync.py）。

为什么单独立一把：2026-10-03 联调发现 `web/app.js` 那段买卖点文字是**逐个信号列出来**的，
长度跟着**信号数**涨。仓里的样本只有 4~17 个信号（最长 50 字符）＝看着像一句归纳，
所以配色尺、并排图、Atlas 的复核三把尺全是绿的 —— 真到了 Bram 后台的实时源
（ZECUSDT 15m，20160 根）一次 66 个信号 ⇒「类中枢层」那一层列表 **197 字符**，390px 视口下
量出来 **1549.6px**（按本尺子的保守每字宽算是 1598px），而图脚那一格只有 **362px**；
连标签整段 256 字符 ⇒ **整块图脚 8 行**。归并之后每层各一行（实测 170.3 / 245.6px）。
**样本比线上小两个数量级，尺子就量不到** —— 这条尺子拿一份**实时规模**的样本来量。

判据（主语和宽度都写死，不然同一句规则两个结果 —— Atlas 2026-10-03 提的）：
  **每个层级（线段中枢层 / 类中枢层）那一段「标签 ＋ 列表」整句，在 390px 视口的图脚那一格
  （宽 362px、字号 10px）里必须放得下一行。** 不是「整条图脚一行」—— 整条还带着根数/笔数/
  精度/数据源，在手机上本来就是四行，那个当不成判据。
  ★ 量的是**整句**（标签一起），不是只量列表再扣字数 —— 2026-10-03 Nova 定：
    这样以后标签改名也不会漏算（标签是**从 app.js 的模板里读**的，不是在这儿再抄一份）。
    ★ 只量列表会**假绿**：列表刚好 44 字时整句是 50 字 ≈ 406px > 362px，其实要换行。
      尺 ⑤ 那格探针专门钉这件事（旧尺必须假绿、新尺必须红）。

宽度怎么来的（都是**量**的，不是估的；量法：在真页面上用同字体的 span 量 getBoundingClientRect）：
  390px 视口 → 图脚那格 clientWidth = **362px**，字号 10px / 行高 15px。
  同一批文字里最费的每字宽 = **8.11px**（`线段中枢层 三买×7·一卖·二卖·三卖×4` 21 字 170.3px）。
  362 ÷ 8.11 = 44.6 ⇒ **预算 44 字符（对整句）**。取最费的每字宽是故意的：这是上界，宁可提前叫。
  ★ 这是**字符预算**，不是像素量 —— 仓里没有浏览器，真量像素得把 playwright 塞进仓，那是另一个决定。
    44 字 ≈357px（放得下）；实测「六种全齐＋待确认」那种 49 字整句＝356px —— 只差 6px 就换行，
    所以 44 这条线会把那种边缘情形叫红。**知道它偏保守，是保守，不是准。**

第二件（2026-10-03 线上逮到之后加的）：图脚**末尾那格「数据源」不许是空的、也不许说假话**。
  `web/app.js` 的模板原先印 `${state.source}`，而 `state.source` 从声明（`''`）起**从没被赋过值** ——
  `load()` 把出处挂在**返回对象**上（`'api'` ／ `'样本 x.json'`），`draw()` 只存了 `state.data`。
  真源和离线两条路都印不出出处 ⇒ 线上图脚末尾常年挂着一个光杆「｜ 数据源」。
  ★ 这格当时是**绿着漏过去的**：本尺子上一条判据量的是「标签＋列表」的宽度，**空字段不在判据里**。

  ★★ 第一版的补法（给 `draw()` 补一行把 `d.source` 写回 `state.source`）**自己又带了一个洞**，
     Atlas 2026-10-03 挑出来的：本尺子当时是**把「赋值那一行」和「模板」两块抠出来自己拼**，
     固定「先赋值、后 renderMeta」—— **量的是尺子造出来的顺序，不是 `draw()` 里真实的顺序**。
     把 `renderMeta(d)` 挪到赋值之前（真页面上会印**上一次** load 的出处），尺子照样绿。
     ⇒ 现在的修法是**把那个中间变量整个删掉**：模板直接读传进来的 `d`（`d.source` / `d.stale`），
       没有顺序可以错，尺子也不用再造替身。这块叫「判据量了替身」，跟「判据漏了一半」是两族。
  ★ 判据四格（都**真跑** `renderMeta`，不读代码）：真源（不 stale）⇒「币安实时」／ 真源 stale ⇒「币安缓存」
     ／ 离线样本 ⇒「样本 x.json」原样 ／ 出处字段缺 ⇒「未知」（空着是看不出来，未知是看得出来的不知道）。
     「币安缓存」那一态不是洁癖：stale 为真时角上同时挂着「★ 旧数据（本轮拉取失败）」，
     图脚要是还说「实时」，同一屏上两句话就打架了。

第三件（2026-10-04，卡 card-84091d2d-c97）：图脚多了一格「背驰看法」——
  `+ measureText(d)` 插在「数据源」前面，写的是**当前画的那份**是哪种力度比较（面积/斜率/黄白线/峰值）。
  ★★ 跟「数据源」那格同一个坑位：**认的必须是 `d.measure`（后台那份响应里的回显）**，
     不是用户点的那颗、也不是前端那张代号→人话的表。用户点的那颗可能没换成（后台 400/503），
     屏幕上到底画的是哪种，只有回的那份说了算。探针 ⑫ 钉的就是这个（写死缺省 ⇒ 必须红）。
  ★ 三条支路各有判据：四种名字（回显说话）／**后台新加的第五种原样印代号**（不吞，Nova 10-04 定的
     「宁可难看也不藏」）／**没有这个字段就不出现这一格**（旧后台、离线样本 —— 不知道的事不编）。
     所以这格「切不到」**不是错**，跟「数据源」那格必须有个值不一样，两把切法分开写。

跑法：
  python3 tools/web_footer_check.py            # 主跑：拿实时规模的样本量 ＋ 数据源/背驰看法/中枢切法那三格
  python3 tools/web_footer_check.py --selftest # 探针：十七格都得变红（尺子自己先证明会红）
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = os.path.join(ROOT, "web", "app.js")
FIX = os.path.join(ROOT, "web", "fixtures", "signals_zec15m_live.json")

BEGIN = "// >>> SIG_TIER_TEXT"
END = "// <<< SIG_TIER_TEXT"
# 图脚末尾那格「数据源」：**只抠模板这一块**真跑（2026-10-03 线上逮到的洞）。
# ★ 这里**没有**第二块要拼 —— 早先那版还抠「给 state.source 赋值」的一行拼在前面，
#   那等于尺子自己造了个顺序去量（Atlas 挑出来的假绿）。模板直接读 d，就没得拼。
MBEGIN, MEND = "// >>> RENDER_META", "// <<< RENDER_META"
SRC_RE = re.compile(r"｜\s*数据源\s*(.*)$")

LINE_PX = 362.0        # 390px 视口下图脚那格的 clientWidth（量出来的）
PX_PER_CHAR = 8.11     # 实测最费的每字宽（见文件头）
BUDGET = int(LINE_PX // PX_PER_CHAR)   # 44 —— 对「标签＋列表」整句

# 模板里那两个层级标签：`买卖点 线段中枢层 ${sigTierText(…)} · 类中枢层 ${sigTierText(…)}`
LABEL_RE = re.compile(r"([^\s`|+]{2,8}层\s*)\$\{sigTierText\(")


def block(path=JS, begin=BEGIN, end=END):
    """把带标记的那一段从 app.js 里抠出来。抠不到 ⇒ 直接报错，不许静默跳过。"""
    src = open(path, encoding="utf-8").read()
    a = src.find(begin)
    b = src.find(end)
    if a < 0 or b < 0 or b < a:
        raise SystemExit("✗ 在 %s 里找不到 %s / %s 标记 —— 抠不到被测量，尺子不猜" %
                         (os.path.relpath(path, ROOT), begin, end))
    # 从标记**那一行的行尾**开始切：标记行后面还跟着说明文字，带上它会变成 JS 语法错
    return src[src.index("\n", a) + 1:b]


def labels(path=JS):
    """两个层级标签**从 app.js 的模板里读**，不在这儿再抄一份 —— 改名自动跟，且不会再出现
    「尺子里的副本跟页面上不一致」那种 bug（配色那条就是这么栽的）。读不到 ⇒ 报错。"""
    src = open(path, encoding="utf-8").read()
    found = LABEL_RE.findall(src)
    if len(found) != 2:
        raise SystemExit("✗ 从 %s 里读到 %d 个 `${sigTierText(` 前面的层级标签（要 2 个）—— "
                         "模板改了就得改这把尺子，不许静默少算一层" % (os.path.relpath(path, ROOT), len(found)))
    return found


def run(js, fixture):
    """把抠出来的 JS 段丢给 node 跑，喂 fixture，收每层那段列表文字。"""
    harness = js + """
const fs = require('fs');
const d = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));   // argv[1] 是脚本自己
process.stdout.write(JSON.stringify({
  seg: sigTierText(d.signals.seg || []),
  pen: sigTierText(d.signals.pen || []),
  n_seg: (d.signals.seg || []).length,
  n_pen: (d.signals.pen || []).length,
  nbars: d.nbars,
}));
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(harness)
        tmp = f.name
    try:
        p = subprocess.run(["node", tmp, fixture], capture_output=True, text=True, timeout=60)
    finally:
        os.unlink(tmp)
    if p.returncode != 0:
        raise SystemExit("✗ node 跑不起来：\n" + p.stderr.strip())
    return json.loads(p.stdout)


def judge(got, labs, budget=BUDGET):
    """→ [(层级, 信号数, 整句, 字符数, ≈px, 过没过)]。整句 ＝ 标签 ＋ 列表。"""
    rows = []
    for (tier, nsig), lab in zip((("seg", got["n_seg"]), ("pen", got["n_pen"])), labs):
        line = lab + got[tier]
        n = len(line)
        rows.append((lab.strip(), nsig, line, n, n * PX_PER_CHAR, n <= budget))
    return rows


def measure(path=JS, fixture=FIX, quiet=False):
    d = json.load(open(fixture, encoding="utf-8"))
    labs = labels(path)
    got = run(block(path), fixture)
    rows = judge(got, labs)
    bad = [r for r in rows if not r[5]]
    if quiet:
        return rows, not bad
    print("  样本：%s（%s 根，%s 个信号：线段中枢层 %d ＋ 类中枢层 %d）"
          % (d.get("_source", os.path.relpath(fixture, ROOT)), got["nbars"], got["n_seg"] + got["n_pen"],
             got["n_seg"], got["n_pen"]))
    print("  预算：每个层级「标签＋列表」整句 ≤ %d 字符（390px 视口 / 图脚格 %gpx / 最费每字 %gpx）\n"
          % (BUDGET, LINE_PX, PX_PER_CHAR))
    print("  %-12s %6s %6s %9s %6s  %s" % ("层级", "信号数", "整句字", "列表字", "≈px", "判定"))
    for lab, nsig, line, n, px, ok in rows:
        print("  %-12s %6d %6d %6d %9.0f  %s"
              % (lab, nsig, n, n - len(lab) - 1, px, "✓ 一行" if ok else "✗ 放不下（要 %.2f 行）" % (px / LINE_PX)))
    print()
    for (lab, _n, line, _c, _p, _ok) in rows:
        print("  %s：%s" % (lab, line))
    print()
    return rows, not bad


# 「数据源」那格的最小载荷：只喂 renderMeta 真的会读到的字段
# （别的字段它不读 —— 喂多了反而看不见「读了却没接线」这种事）
PAYLOAD = {
    "symbol": "ZECUSDT", "name": "ZEC/USDT 永续", "tf": "15m", "nbars": 20160,
    "pens": [{"i0": 0, "p0": 1, "i1": 1, "p1": 2}],
    "centers": [{"ZD": 1, "ZG": 2}], "seg_centers": [{"ZD": 1, "ZG": 2}],
    "segs": [{"live": False}, {"live": False}, {"live": True}],
    "meta": {"tick": 0.01, "pen_rule": "old"},
    "signals": {"seg": [{"kind": "三买", "confirmed": True}],
                "pen": [{"kind": "一买", "confirmed": True}]},
    "source": "api",
}


def footer_text(payload, path=JS, block_js=None):
    """把 SIG_TIER_TEXT ＋ RENDER_META 两块拼成一个小模块，配**假 DOM** 真跑一遍 `renderMeta`，
    收它写进 `#meta` 的那整句话。`block_js` 给探针用：拿一版**被改过**的模板替进去。

    ★ 这里**不拼 draw()、也不经任何中间变量**：模板直接读传进来的 d（`d.source` / `d.stale`）。
      早先那版先拼「给 state.source 赋值」那一行 —— 那是**尺子自己造了一个顺序**，量的是替身
      （把 renderMeta(d) 挪到赋值之前，真页面会印上一次 load 的出处，尺子照样绿）。
    ★ 假 DOM 里**故意不定义 `state`**：模板要是回头去读 `state.xxx`，这里当场 ReferenceError ⇒ 直接红。
      探针 ⑨ 钉的就是这个形状 —— 当初那个洞正是「模板读了一个没人赋值的 state 字段」。"""
    js = (block(path) + "\n" + (block(path, MBEGIN, MEND) if block_js is None else block_js) + """
const out = {};
const el = (id) => ({ set textContent(v) { out[id] = v; }, get textContent() { return out[id] || ''; },
                      set className(v) {}, set title(v) {} });
const d = JSON.parse(process.argv[2]);
renderMeta(d);
process.stdout.write(JSON.stringify({ meta: out.meta }));
""")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js)
        tmp = f.name
    try:
        p = subprocess.run(["node", tmp, json.dumps(payload)], capture_output=True, text=True, timeout=60)
    finally:
        os.unlink(tmp)
    if p.returncode != 0:
        raise SystemExit("✗ 「数据源」那格跑不起来：\n" + p.stderr.strip())
    return json.loads(p.stdout)["meta"]


def source_of(meta):
    """从整句图脚里切出「｜ 数据源」后面那截。切不到 ⇒ 报错，不许当成空字符串糊过去。"""
    m = SRC_RE.search(meta)
    if not m:
        raise SystemExit("✗ 图脚里找不到「｜ 数据源」那一段 —— 模板改了就得改这把尺子")
    return m.group(1).strip()


def data_source_check(quiet=False):
    """判据：图脚末尾那格**必须印出真实的出处，而且不许说假话**。四格：
      真源（不 stale）⇒「币安实时」／ 真源 stale ⇒「币安缓存」／ 离线样本 ⇒「样本 x.json」原样
      ／ 出处字段缺 ⇒「未知」。

    ★ 报红的时候只印**实际印出来的值**，不印预设的原因 —— 早先那版把「接线摘掉」的失败信息
      写死成「印出来是空的」，可实测印的是别的，写死的解释把人往错处带（Atlas 2026-10-03 指出的）。"""
    live = source_of(footer_text(PAYLOAD))
    st = source_of(footer_text(dict(PAYLOAD, stale=True)))
    off = source_of(footer_text(dict(PAYLOAD, source="样本 zec_15m.json")))
    unk = source_of(footer_text({k: v for k, v in PAYLOAD.items() if k != "source"}))
    got = (live, st, off, unk)
    want = ("币安实时", "币安缓存", "样本 zec_15m.json", "未知")
    ok = got == want
    if not quiet:
        for name, g, w in zip(("真源（不 stale）", "真源 stale", "离线样本", "出处字段缺"), got, want):
            print("  数据源那格：%-14s ⇒ %-22r（要 %r）" % (name, g, w))
    return got, ok


# 「背驰看法」那格（card-84091d2d-c97，2026-10-04 加）：跟「数据源」那格同一套规矩 ——
# 模板认的是 **d.measure（后台的回显）**，不是用户点的那颗、也不是前端的名单。
MEAS_RE = re.compile(r"｜\s*背驰看法\s*(\S+)")


def measure_cell(meta):
    """从整句图脚里切出「｜ 背驰看法」后面那个名字。切不到 ⇒ None。
    ★ 跟 source_of 不一样：**切不到不是错**。没有这个字段（旧后台／离线样本）时这一格本来就
      不该出现，所以「不出现」是要判成的那个态；而「数据源」那格是必须总有个值。
      两边口径不同就写两把切法，别为省事合成一把（合成那把会把「该不该出现」这件事吞掉）。"""
    m = MEAS_RE.search(meta)
    return m.group(1).strip() if m else None


def measure_check(quiet=False):
    """判据：图脚那格＝**它自己给的那份回显**，四态。

    黄白线（回显 lines）／面积（回显 macd）／后台新加的第五种**原样印代号**（不吞，Nova 定的
    「宁可难看也不藏」）／没有这个字段 ⇒ **整格不出现**（不知道的事不编）。
    另加一验：新格子插在「数据源」那格前面，不许把它挤坏。

    ★ 报红只印实际印出来的值，不印预设的原因（跟 data_source_check 同一条规矩）。"""
    got = (measure_cell(footer_text(dict(PAYLOAD, measure="lines"))),
           measure_cell(footer_text(dict(PAYLOAD, measure="macd"))),
           measure_cell(footer_text(dict(PAYLOAD, measure="zigzag"))),
           measure_cell(footer_text(PAYLOAD)))
    want = ("黄白线", "面积", "zigzag", None)
    src_got = source_of(footer_text(dict(PAYLOAD, measure="lines")))
    src_ok = src_got == "币安实时"
    ok = got == want and src_ok
    if not quiet:
        for name, g, w in zip(("回显 lines", "回显 macd", "名单外的第五种（原样印）", "没有这个字段（旧后台/样本）"), got, want):
            print("  背驰看法那格：%-28s ⇒ %-10r（要 %r）" % (name, g, w))
        print("  背驰看法那格：%-28s ⇒ %r（要 '币安实时'）" % ("它后面那格「数据源」", src_got))
    return got, src_got, ok


# 「中枢切法」那格（card-e346ede6-996，2026-10-05 加）：跟「背驰看法」那格**同一套规矩** ——
# 认的是 **d.cut（后台的回显）**，不是用户点的那颗、也不是 /api/meta 给的那份名单。
# ★ 一处**故意不一样**，钉在探针 ⑰：**缺省那一档也要印**（缺省 **2026-10-06 起是「走势分段」**，
#   见 `web/app.js` 的 `DEFAULT_CUT = 'trend'`）。这是一张图的记录 ——
#   「延伸」「走势分段」两张对照图就靠这一格分开；要是"只在换了才印"，切换前那张图上
#   没有任何一处说得出它是哪种切法（那就成了两张长得一样、含义不同的图）。
#
# ★★ 这一格**换过一次尺**（2026-10-07，card-22888623-1a7，Atlas 查的账）：缺省 10-06 从 turn
#    改成 trend 时（`dac61cb`）**只改了后台和 app.js，忘了改这把尺** —— 于是这格一直拿
#    「回显 turn ⇒『按转折切』」当期望，对着一个**后台已经不回的档位**报警。
#    代码是好的，是尺旧了。现在按后台的实情重钉：
#      · 回显 `trend` ⇒「走势分段」——**这才是今天的缺省那一档**；
#      · 回显 `turn`  ⇒ 字面 `'turn'`。**这条不是"另一种档位"，是一条绊线** ——
#        `web/server.py` 的 `CUT_ALIAS = {"turn": "trend"}` 把老链接当 trend 收、**回显 trend**，
#        而 `CUT_NAME` 里**故意不给 turn 留名字**（`app.js`:2185-2188 写着为什么：留了反而会印出
#        一个后台已经不用的档位）。所以 turn 今天走的是「名单外的新名字**原样印**」那条路
#        —— 跟 zigzag 同一条规矩。哪天有人把 turn 的中文名加回 `CUT_NAME`，这条就红：
#        那等于**把 `dac61cb` 撤销了**，该有人看一眼。
#    ⚠️ 教训（写在这儿，别再踩）：**探针里引用的字面量，跟它一起过期**。⑭⑮⑰ 当时钉的都是
#       「按转折切」——这个词前台已经印不出来了，于是 ⑭⑮ 变成**空过**（拿一个谁都印不出的词
#       当"不相等"的另一边，永远成立），⑰ 也探错了档。⑰ 自己那句注释（"字面量得跟
#       `DEFAULT_CUT` 一起翻"）写的就是这件事 —— 上一趟没照做。改尺时**先搜一遍这个文件里
#       所有跟被改档位有关的字面量**，别只看判据那几行。
CUT_RE = re.compile(r"｜\s*中枢切法\s*(\S+)")


def cut_cell(meta):
    """从整句图脚里切出「｜ 中枢切法」后面那个名字。切不到 ⇒ None（跟 measure_cell 同一条：
    **切不到不是错** —— 没有这个字段时这一格本来就不该出现）。"""
    m = CUT_RE.search(meta)
    return m.group(1).strip() if m else None


def cut_check(quiet=False):
    """判据：图脚那格＝**它自己给的那份回显**，五态（跟 measure_check 同形）。

    回显 trend ⇒「走势分段」（**这是今天的缺省那一档，也印**）／回显 extend ⇒「延伸」（也印）
    ／回显 turn ⇒ **原样的 'turn'**（后台当 trend 收、不回 turn，所以这条走"名单外原样印"那条路；
    见上面那段：这是一条绊线，不是第二种档位）／后台新加的名字 ⇒ **原样印**（不吞）
    ／没有这个字段 ⇒ **整格不出现**（旧后台、离线样本：不知道的事不编）。
    另加一验：这一格插在「数据源」前面，不许把它挤坏。"""
    got = (cut_cell(footer_text(dict(PAYLOAD, cut="trend"))),
           cut_cell(footer_text(dict(PAYLOAD, cut="extend"))),
           cut_cell(footer_text(dict(PAYLOAD, cut="turn"))),
           cut_cell(footer_text(dict(PAYLOAD, cut="zigzag"))),
           cut_cell(footer_text(PAYLOAD)))
    want = ("走势分段", "延伸", "turn", "zigzag", None)
    src_got = source_of(footer_text(dict(PAYLOAD, cut="trend")))
    src_ok = src_got == "币安实时"
    ok = got == want and src_ok
    if not quiet:
        for name, g, w in zip(("回显 trend（现缺省）", "回显 extend（另一档，也印）",
                              "回显 turn（后台已不收 ⇒ 原样印，绊线）",
                              "名单外的新名字（原样印）", "没有这个字段（旧后台/样本）"), got, want):
            print("  中枢切法那格：%-38s ⇒ %-10r（要 %r）" % (name, g, w))
        print("  中枢切法那格：%-38s ⇒ %r（要 '币安实时'）" % ("它后面那格「数据源」", src_got))
    return got, src_got, ok


def mutate(js, old, new):
    """探针里改源码用。**改动必须真落到抠出来的那段上** —— 落不上就抛，不许白捡一个红：
    Atlas 2026-10-03 那格探针就是这么假红的（他删的是标记块里那一行，块因为空了才红，
    红得不是地方 —— 「红的原因」也得核）。"""
    if old not in js:
        raise SystemExit("探针改不动：抠出来的模板里没有 %r" % old)
    return js.replace(old, new)


def node_eval(js):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js)
        tmp = f.name
    try:
        p = subprocess.run(["node", tmp], capture_output=True, text=True, timeout=60)
    finally:
        os.unlink(tmp)
    if p.returncode != 0:
        raise SystemExit(p.stderr.strip())
    return json.loads(p.stdout)


def selftest():
    """十格探针：每一格都必须变红。尺子先证明自己会红，绿才算数。"""
    cases = []
    old = ("const sigTierText = (s) => s.map((x) => `${x.kind}${x.confirmed ? '' : '?'}`)"
           ".join('·') || '无';")

    # ① 老写法（34b5739a 原来那一行）必须红 —— ★ Atlas 的做法更狠：他直接从 34b5739a 抠 L242 原文
    #    替进标记块跑主路径。这里重打一遍，只因 selftest 要能独立跑；口径以他那次为准。
    try:
        labs = labels()
        js = old + """
const fs=require('fs');const d=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
process.stdout.write(JSON.stringify({seg:sigTierText(d.signals.seg||[]),pen:sigTierText(d.signals.pen||[])}));"""
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(js)
            tmp = f.name
        p = subprocess.run(["node", tmp, FIX], capture_output=True, text=True, timeout=60)
        os.unlink(tmp)
        o = json.loads(p.stdout)
        red = any(len(lab + o[t]) > BUDGET for lab, t in zip(labs, ("seg", "pen")))
        cases.append(("① 老写法（逐个 join，34b5739a 原样）必须红", red))
    except Exception:
        cases.append(("① 老写法（逐个 join，34b5739a 原样）必须红", False))

    # ② 标记删掉 ⇒ 必须报错（不许静默跳过被测量）
    src = open(JS, encoding="utf-8").read().replace(BEGIN, "// (marker removed)")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(src)
        tmp = f.name
    try:
        block(tmp)
        cases.append(("② 标记被删掉 ⇒ 报错", False))
    except SystemExit:
        cases.append(("② 标记被删掉 ⇒ 报错", True))
    finally:
        os.unlink(tmp)

    # ③ 认不出的 kind 必须露面、待确认要分开算（注释里写了「不许静默吞掉」，就得有探针）
    try:
        got = node_eval(block() + """
process.stdout.write(JSON.stringify({t: sigTierText([
  {kind: '四买', confirmed: true}, {kind: '三卖', confirmed: true}, {kind: '三卖', confirmed: false}])}));""")
        t = got["t"]
        cases.append(("③ 认不出的 kind 没被吞、待确认单独计数（%s）" % t, "四买" in t and "三卖?" in t))
    except Exception:
        cases.append(("③ 认不出的 kind 没被吞、待确认单独计数", False))

    # ④ 极端输入（6 种 × 已确认/待确认 ＝ 12 项）必须红
    try:
        js = block() + """
process.stdout.write(JSON.stringify({t: sigTierText([
  {kind:'一买',confirmed:true},{kind:'一买',confirmed:false},
  {kind:'二买',confirmed:true},{kind:'二买',confirmed:false},
  {kind:'三买',confirmed:true},{kind:'三买',confirmed:false},
  {kind:'一卖',confirmed:true},{kind:'一卖',confirmed:false},
  {kind:'二卖',confirmed:true},{kind:'二卖',confirmed:false},
  {kind:'三卖',confirmed:true},{kind:'三卖',confirmed:false}])}));"""
        t = node_eval(js)["t"]
        cases.append(("④ 极端输入（12 项）必须红（%d 字）" % len(t), len(t) + max(len(l) for l in labels()) > BUDGET))
    except Exception:
        cases.append(("④ 极端输入（12 项）必须红", False))

    # ⑤ ★ 这一格是这次的假绿：列表**卡在旧预算里**（只量列表 ⇒ 绿），加上标签整句就超宽 ⇒ 必须红。
    #    两件都要成立：旧尺必须假绿（否则没复现），新尺必须红（否则没修上）。
    #    ★ 这格只是把「旧尺会绿」写成算式；**真凭据是拿 e3c6df2 里那份原件跑出来的**（2026-10-03）：
    #      把 `git show e3c6df2:tools/web_footer_check.py` 落成一个临时模块，喂一份「列表 41 字」的样本
    #      （6 种 × 已确认/待确认），**旧尺 rc=0 绿、新尺红** —— 假绿在原件上复现过，不是推的。
    #      那个临时模块不进仓（selftest 不该依赖 git 历史），所以算式留在这儿当常驻的钉子。
    try:
        js = block() + """
process.stdout.write(JSON.stringify({t: sigTierText([
  {kind:'一买',confirmed:true},{kind:'一买',confirmed:false},
  {kind:'二买',confirmed:true},{kind:'二买',confirmed:false},
  {kind:'三买',confirmed:true},{kind:'三买',confirmed:false},
  {kind:'一卖',confirmed:true},{kind:'一卖',confirmed:false},
  {kind:'二卖',confirmed:true},{kind:'二卖',confirmed:false},
  {kind:'三卖',confirmed:true},{kind:'三卖',confirmed:false}])}));"""
        t = node_eval(js)["t"]
        lab = max(labels(), key=len)
        old_green = len(t) <= BUDGET                       # 旧尺：只量列表
        new_red = len(lab + t) > BUDGET                    # 新尺：整句
        cases.append(("⑤ 边界：列表 %d 字（旧尺绿）＋标签＝%d 字（新尺红）"
                      % (len(t), len(lab + t)), old_green and new_red))
    except Exception:
        cases.append(("⑤ 边界那格（旧尺假绿、新尺必须红）", False))

    # ⑥ 标签改名/模板改样 ⇒ 必须报错，不许静默少算一层
    src = open(JS, encoding="utf-8").read().replace("类中枢层 ${sigTierText(", "类中枢 ${sigTierText(")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(src)
        tmp = f.name
    try:
        labels(tmp)
        cases.append(("⑥ 层级标签改名 ⇒ 报错", False))
    except SystemExit:
        cases.append(("⑥ 层级标签改名 ⇒ 报错", True))
    finally:
        os.unlink(tmp)

    # ⑦⑧⑨ 「数据源」那格的三格探针：拿**改过的模板**跑，看尺子的判据认不认得出来。
    #    ★ 先把「改得动吗」跟「改完跑出什么」分开：改不动是**探针自己坏了**，判 False（不许白捡一个红）。
    MB = block(JS, MBEGIN, MEND)

    def _mut(old, new):
        try:
            return mutate(MB, old, new)
        except SystemExit as e:
            cases.append(("（探针自身失效，不算红）%s" % e, False))
            return None

    def _run(bjs, payload):
        """跑一版被改过的模板，返回它印出来的数据源值；跑不起来返回 None。"""
        try:
            return source_of(footer_text(payload, block_js=bjs))
        except SystemExit:
            return None

    # ⑦ stale 那态塌成一态（Nova 点名的「两态各配一格」之一）⇒ stale 必须印不出「币安缓存」
    b = _mut("stale ? '币安缓存' : '币安实时'", "'币安实时'")
    if b is not None:
        got = _run(b, dict(PAYLOAD, stale=True))
        cases.append(("⑦ stale 两态塌成一态 ⇒ 印成 %r，判据必须不认" % got, got != "币安缓存"))

    # ⑧ 缺字段那态退回空（＝Atlas 指出的「光杆 ｜ 数据源」那个症状回来了）⇒ 必须印不出非空
    b = _mut("src || '未知'", "src || ''")
    if b is not None:
        got = _run(b, {k: v for k, v in PAYLOAD.items() if k != "source"})
        cases.append(("⑧ 缺字段退回空 ⇒ 印成 %r，判据必须不认" % got, not got))

    # ⑨ ★ 当初那个 bug 的形状：模板回头去读中间变量 `state.source`。
    #    假 DOM 里没有 `state` ⇒ 跑挂 ⇒ 判据不可能认（「中间变量」这条路就算被封死了）
    b = _mut("sourceLabel(d.source, d.stale)", "state.source")
    if b is not None:
        got = _run(b, PAYLOAD)
        cases.append(("⑨ 模板回头读 state.source ⇒ 印成 %r，判据必须不认" % got, got != "币安实时"))

    # ⑩ RENDER_META 标记被删 ⇒ 必须报错（不许静默跳过被测量，跟 ② 同一条规矩）
    src = open(JS, encoding="utf-8").read().replace(MBEGIN, "// (marker removed)")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(src)
        tmp = f.name
    try:
        block(tmp, MBEGIN, MEND)
        cases.append(("⑩ RENDER_META 标记被删掉 ⇒ 报错", False))
    except SystemExit:
        cases.append(("⑩ RENDER_META 标记被删掉 ⇒ 报错", True))
    finally:
        os.unlink(tmp)

    # ⑪–⑬ 「背驰看法」那格的三格探针（2026-10-04 加这一格时配的）。
    #    判据是「名字＝**d.measure 那份回显**」⇒ 三件事都得钉住：接线在不在、认不认回显、缺字段编不编。
    def _mrun(bjs, payload):
        try:
            return measure_cell(footer_text(payload, block_js=bjs))
        except SystemExit:
            return None

    # ⑪ 接线被摘掉（模板里不再调 measureText）⇒ 必须印不出名字
    b = _mut("+ measureText(d)", "+ ''")
    if b is not None:
        got = _mrun(b, dict(PAYLOAD, measure="lines"))
        cases.append(("⑪ 模板不再调 measureText ⇒ 印成 %r，判据必须不认" % got, got != "黄白线"))

    # ⑫ ★ 写死成缺省（不认回显）：回显说是 lines，格子却印「面积」⇒ 判据必须不认。
    #    这一格钉的是「以回显为准」—— 用户点的那颗、前端的名单，都不能当准。
    b = _mut("const m = d.measure;", "const m = 'macd';")
    if b is not None:
        got = _mrun(b, dict(PAYLOAD, measure="lines"))
        cases.append(("⑫ 写死缺省、不认回显 ⇒ 印成 %r，判据必须不认" % got, got != "黄白线"))

    # ⑬ 缺字段那态塌成一态：没有 measure 也硬印一个 ⇒ 必须印不出「不出现」（＝不许编）
    b = _mut("if (typeof m !== 'string' || !m) return '';", "if (false) return '';")
    if b is not None:
        got = _mrun(b, PAYLOAD)
        cases.append(("⑬ 缺字段也硬印 ⇒ 印成 %r，判据必须不认（要的是整格不出现）" % got, got is not None))

    # ⑭–⑰ 「中枢切法」那格的四格探针（2026-10-05 加这一格时配的）。
    #     判据是「名字＝**d.cut 那份回显**」⇒ 四件事都得钉住：接线在不在、认不认回显、缺字段编不编、
    #     **缺省那一态印不印**（这一条是本格特有的，见 CUT_RE 上面那段）。
    # ★★ 2026-10-07 跟着缺省一起翻的字面量：⑭⑮⑰ 原来钉的是「按转折切」／`cut="turn"`，
    #    缺省改 trend 之后那个词前台**印不出来**了 ⇒ ⑭⑮ 的「不相等」永远成立（空过），
    #    ⑰ 探的也不是缺省那一档。**探针引用的字面量跟判据一起过期**，改尺时全文件搜一遍。
    def _crun(bjs, payload):
        try:
            return cut_cell(footer_text(payload, block_js=bjs))
        except SystemExit:
            return None

    # ⑭ 接线被摘掉（模板里不再调 cutText）⇒ 必须印不出名字
    b = _mut("+ cutText(d)", "+ ''")
    if b is not None:
        got = _crun(b, dict(PAYLOAD, cut="trend"))
        cases.append(("⑭ 模板不再调 cutText ⇒ 印成 %r，判据必须不认" % got, got != "走势分段"))

    # ⑮ ★ 写死成某一档（不认回显）：回显说是 trend，格子却印「延伸」⇒ 判据必须不认
    b = _mut("const c = d.cut;", "const c = 'extend';")
    if b is not None:
        got = _crun(b, dict(PAYLOAD, cut="trend"))
        cases.append(("⑮ 写死缺省、不认回显 ⇒ 印成 %r，判据必须不认" % got, got != "走势分段"))

    # ⑯ 缺字段那态塌成一态：没有 cut 也硬印一个 ⇒ 判据必须不认
    b = _mut("if (typeof c !== 'string' || !c) return '';", "if (false) return '';")
    if b is not None:
        got = _crun(b, PAYLOAD)
        cases.append(("⑯ 缺字段也硬印 ⇒ 印成 %r，判据必须不认（要的是整格不出现）" % got, got is not None))

    # ⑰ ★ 本格特有的那一条：**只在不等于缺省时才印**（"少印一格是省事"的写法）⇒ 缺省那档必须印不出来。
    #   ★★ 探的既然是**缺省那一档**，这个字面量就得跟 `web/app.js` 的 `DEFAULT_CUT` 一起翻
    #      （**2026-10-06 起缺省＝trend／「走势分段」**）。拿 extend 当"缺省"来探的话，在 trend
    #      当缺省的世界里它照样红得挺像样，其实探的是**另一档** —— "缺省被吞掉"这件事就没人钉了。
    b = _mut("const c = d.cut;", "const c = d.cut === 'trend' ? '' : d.cut;")
    if b is not None:
        got = _crun(b, dict(PAYLOAD, cut="trend"))
        # 这一格的"红"是**那一格消失**（判据要的是「走势分段」四个字都在）—— 跟 ⑯ 正好相反：
        # ⑯ 是"不该有的却在"，这一格是"该在的却没了"。两个方向都得钉住。
        cases.append(("⑰ 缺省那档不印（走势分段时整格消失）⇒ 印成 %r，判据必须不认" % got, got != "走势分段"))

    print("探针（每一格都必须红）：")
    for name, red in cases:
        print("  %s %s" % ("✓" if red else "✗ 没红", name))
    n_ok = sum(1 for _, r in cases if r)
    print("\n%s %d/%d 格探针都能变红" % ("✓" if n_ok == len(cases) else "✗", n_ok, len(cases)))
    return n_ok == len(cases)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    print("图脚「买卖点」段的宽度尺（390px 视口，量「标签＋列表」整句）\n")
    try:
        _, ok = measure()
        _ds, ds_ok = data_source_check()
        _mc, _ms, m_ok = measure_check()
        _cc, _cs, c_ok = cut_check()
    except SystemExit as e:
        print(str(e))
        sys.exit(1)
    if ok and ds_ok and m_ok and c_ok:
        print("✓ 两个层级都在一行内，且「数据源」「背驰看法」「中枢切法」三格印得出真实的值（%s）" % os.path.relpath(JS, ROOT))
        sys.exit(0)
    if not ok:
        print("✗ 有一段放不下一行 —— 图脚在手机上是几行糊在一起的字（见上面的 ≈px）")
    if not ds_ok:
        print("✗ 「数据源」那格印出来的值不对 —— 实际值印在上面每一行里，照那个看，别猜原因")
    if not m_ok:
        print("✗ 「背驰看法」那格印出来的值不对 —— 实际值印在上面每一行里，照那个看，别猜原因")
    if not c_ok:
        print("✗ 「中枢切法」那格印出来的值不对 —— 实际值印在上面每一行里，照那个看，别猜原因")
    sys.exit(1)
