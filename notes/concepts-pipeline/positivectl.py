# -*- coding: utf-8 -*-
"""引号尺的**阳性对照**：报绿之前，先报一条红。

为什么要有这个文件（2026-10-01，@iris-64a1 提的，她踩过）：
  她那把尺报「全绿」，可她自己是把「忘了」也写进了引号的 —— 尺判绿，因为**语料里碰巧有那个词**。
  ⇒ 所以「都不中 0」这个读数**单独看没有意义**：一条全是 0 的尺，既可能是真干净，
     也可能是尺坏了/口径把边界挪走了。两个长得一模一样。
  ⇒ 判据：**给尺喂一条你自己知道该红的样本，看它红不红**。红 ⇒ 这个 0 才有意义。

做法（不另写一把尺）：把成品复制一份，往里注入 3 条**已知该不中**的「」块，
再跑 README 里那条真命令 `checkquotes.py <文件> --min 4`（**同一把尺**），
断言「都不中」至少 3。断言不过 ⇒ 尺放行了本该红的样本（**假绿**），
脚本非 0 退出 —— 假绿比假红危险：假红看得见，假绿看不见。

三条对照：
  ① 整句自造    —— 语料里绝无此串
  ② 单字改      —— 拿本文件里最长的一条真引文，换掉中间一个字
  ③ 删一字      —— 同一句，删掉中间一个字（「少字」这一类）

用法：python3 notes/concepts-pipeline/positivectl.py
前提：`archive/` 需与本仓同相对路径就位（同 checkquotes.py）。
"""
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs/concepts/inventory_中枢走势组.md")
RULER = os.path.join(ROOT, "notes/concepts-pipeline/checkquotes.py")
MIN = "4"
assert os.path.isfile(DOC), "成品不在 %s" % DOC
assert os.path.isfile(RULER), "尺不在 %s" % RULER

doc = open(DOC, encoding="utf-8").read()

# 拿本文件里最长的一条真引文当底 —— 它此刻是「原样逐字」命中的（本文件 都不中 0）
blocks = sorted(re.findall(r"「([^「」]{20,})」", doc), key=len)
assert blocks, "本文件里找不到 ≥20 字的「」块，对照没法造"
base = blocks[-1]
mid = len(base) // 2


def run(path):
    """跑真命令，取回「都不中 N」。"""
    out = subprocess.run([sys.executable, RULER, path, "--min", MIN],
                         capture_output=True, text=True).stdout
    m = re.search(r"都不中\s*(\d+)", out)
    assert m, "尺的输出里没有『都不中 N』这一项，输出格式变了？\n%s" % out[:400]
    return int(m.group(1)), out


CTRL = [
    ("① 整句自造", "这句话是本脚本自造的，语料里绝对没有这么一串字"),
    ("② 单字改　", base[:mid] + "齉" + base[mid + 1:]),
    ("③ 删一字　", base[:mid] + base[mid + 1:]),
]

# ★ 阴性对照（@atlas-791f 补：一把尺要两条对照，不是一条）：
#   阳性防「尺瞎了」（塞自造句，看它红）；阴性防「尺乱咬／假红」（塞真语料原句，看它绿）。
#   他那边两条都撞过，且**第二条更常见** —— 假红会让人去改本来没错的地方。
CORP = os.path.join(ROOT, "archive/chanlun108/text")
assert os.path.isdir(CORP), "语料不在 %s —— archive/ 未进仓，需与本仓同相对路径就位" % CORP
NEG = None
for f in sorted(os.listdir(CORP)):
    for ln in open(os.path.join(CORP, f), encoding="utf-8").read().split("\n"):
        ln = ln.replace("\r", "").strip()
        if len(ln) >= 24 and "「" not in ln and "」" not in ln:
            NEG = ln
            break
    if NEG:
        break
assert NEG, "语料里挑不出一条 ≥24 字、不含「」的原句，阴性对照没法造"

with tempfile.TemporaryDirectory() as td:
    def inject(name, blocks):
        p = os.path.join(td, name)
        open(p, "w", encoding="utf-8").write(
            doc + "\n\n" + "".join("「%s」\n" % c for c in blocks))
        return p

    n0, _ = run(DOC)
    n1, out1 = run(inject("pos.md", [c for _, c in CTRL]))
    n2, out2 = run(inject("neg.md", [NEG]))

print("【引号尺两条对照】门槛 ≥%s 字 ｜ 尺 %s" % (MIN, os.path.basename(RULER)))
print("  未注入（成品本身）　　　都不中 %d" % n0)
print("  阳性：注入 3 条该红的　　都不中 %d（应＝%d）" % (n1, n0 + 3))
print("  阴性：注入 1 条真语料原句　都不中 %d（应＝%d）" % (n2, n0))
print("    阴性样本取自语料：%s…" % NEG[:30])
# ★ 只比前缀：尺打印未中块时会截断（带省略号），整串比会误判成「没点名」。
norm = out1.replace("↵", "").replace(" ", "")
for name, c in CTRL:
    hit = "不中" if c.replace("↵", "").replace(" ", "")[:16] in norm else "★ 没被点名"
    print("    %s %s ｜ %s" % (name, hit, c[:34] + "…"))

bad = [name for name, c in CTRL
       if c.replace("↵", "").replace(" ", "")[:16] not in norm]
fail = []
if n1 != n0 + 3 or bad:
    fail.append("假绿：尺放行了本该红的样本（缺 %s）" % (bad or "计数对不上"))
if n2 != n0:
    fail.append("假红：尺咬了一条真语料原句（%d ≠ %d）" % (n2, n0))
if fail:
    print("\n★ 两把尺都不过关 ⇒ 这个文件报的『都不中 %d』不作数：%s" % (n0, "；".join(fail)))
    sys.exit(1)
print("\n✓ 阳性 3 条全红 ＋ 阴性 1 条全绿 ⇒ 成品那个「都不中 %d」是有意义的读数"
      "（尺会红、也不乱咬）。" % n0)
