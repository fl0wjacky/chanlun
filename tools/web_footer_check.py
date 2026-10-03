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

跑法：
  python3 tools/web_footer_check.py            # 主跑：拿实时规模的样本量
  python3 tools/web_footer_check.py --selftest # 探针：六格都得变红（尺子自己先证明会红）
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

LINE_PX = 362.0        # 390px 视口下图脚那格的 clientWidth（量出来的）
PX_PER_CHAR = 8.11     # 实测最费的每字宽（见文件头）
BUDGET = int(LINE_PX // PX_PER_CHAR)   # 44 —— 对「标签＋列表」整句

# 模板里那两个层级标签：`买卖点 线段中枢层 ${sigTierText(…)} · 类中枢层 ${sigTierText(…)}`
LABEL_RE = re.compile(r"([^\s`|+]{2,8}层\s*)\$\{sigTierText\(")


def block(path=JS):
    """把带标记的那一段从 app.js 里抠出来。抠不到 ⇒ 直接报错，不许静默跳过。"""
    src = open(path, encoding="utf-8").read()
    a = src.find(BEGIN)
    b = src.find(END)
    if a < 0 or b < 0 or b < a:
        raise SystemExit("✗ 在 %s 里找不到 %s / %s 标记 —— 抠不到被测量，尺子不猜" %
                         (os.path.relpath(path, ROOT), BEGIN, END))
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
    """六格探针：每一格都必须变红。尺子先证明自己会红，绿才算数。"""
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
    except SystemExit as e:
        print(str(e))
        sys.exit(1)
    if ok:
        print("✓ 两个层级都在一行内（%s）" % os.path.relpath(JS, ROOT))
        sys.exit(0)
    print("✗ 有一段放不下一行 —— 图脚在手机上是几行糊在一起的字（见上面的 ≈px）")
    sys.exit(1)
