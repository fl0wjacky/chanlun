# -*- coding: utf-8 -*-
"""core 五个文件的「」→『』**纯排版**改动（28 块，逐块点名，不按字符全局替换）。

清单与逐块证据：`notes/core-quote-sweep.md`（卡 `card-1a4cccd9-e66`）。
**只动这 28 块的引号**：块内文字一字不改，块外的字一字不改。

★ 为什么不是 `sed 's/「/『/g'`：那会把**真引文**（同文件里的「」）一起改掉 ——
  pine 那轮（`card-8bd8ca52-373`）的坑，这里同样适用。所以点名到 **(文件, 行, 块内文)**：
  同一行有两块时（`center.py:163`、`signals.py:139`）按块内文区分，对不上就**炸**，不猜。

用法：
    python3 notes/core-quote-typography.py            # 只报要改哪几块（dry-run）
    python3 notes/core-quote-typography.py --apply    # 真改
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOK = re.compile("「([^「」]*)」")
WS = re.compile(r"[\s↵]+")

# (文件, 行, 块内文去空白) —— 28 块，与清单 §① 一一对应
TARGETS = [
    ("core/center.py", 22, "覆盖区间里索引与第一笔同奇偶的笔"),
    ("core/center.py", 33, "从中枢里出发"),
    ("core/center.py", 43, "走势没走完"),
    ("core/center.py", 50, "末尾第 4 个"),
    ("core/center.py", 55, "以后也不会被改写"),
    ("core/center.py", 63, "覆盖区间里索引与第一笔同奇偶的笔"),
    ("core/center.py", 163, "与前一个中枢的关系"),
    ("core/center.py", 163, "可信度档"),
    ("core/signals.py", 31, "B 段回抽 0 轴"),
    ("core/signals.py", 56, "B 段回抽 0 轴附近"),
    ("core/signals.py", 65, "B 段把 MACD 黄白线回抽 0 轴附近"),
    ("core/signals.py", 131, "线段当中枢"),
    ("core/signals.py", 132, "类中枢（笔中枢）扩展合成"),
    ("core/signals.py", 133, "上一层有没有中枢包住"),
    ("core/signals.py", 138, "不合的原样留下（nmerge=1）"),
    ("core/signals.py", 139, "上一层的中枢"),
    ("core/signals.py", 139, "拿同级当上一层"),
    ("core/signals.py", 160, "B 是高一级别中枢"),
    ("core/signals.py", 179, "收成一块"),
    ("core/signals.py", 228, "A、B、C 其实同处一个更大级别中枢"),
    ("core/signals.py", 281, "算出来的量"),
    ("core/signals.py", 285, "另写一遍、不调用 upgrades"),
    ("core/signals.py", 320, "B 段回抽 0 轴附近"),
    ("core/pen.py", 9, "相邻同字重复一次"),
    ("core/pen.py", 11, "笔的成立条件"),
    ("core/pen.py", 42, "一个顶不经过一个底"),
    ("core/extend.py", 19, "9 段升级"),
    ("core/preprocess.py", 27, "两根K线之间是不是真的连续"),
]


def blocks(text):
    """(起始行, 起止偏移, 块内文) —— 与尺子同一条正则、同在整篇上跑（块可跨行）。"""
    out = []
    for m in TOK.finditer(text):
        out.append((text.count("\n", 0, m.start()) + 1, m.start(1) - 1, m.end(1) + 1, m.group(1)))
    return out


def main(argv):
    apply = "--apply" in argv
    by_file = {}
    for f, ln, body in TARGETS:
        by_file.setdefault(f, []).append((ln, WS.sub("", body)))

    total = 0
    for f, targets in by_file.items():
        p = ROOT / f
        text = p.read_text(encoding="utf-8")
        bl = blocks(text)
        edits = []
        for ln, want in targets:
            cand = [(a, b, t) for (s, a, b, t) in bl if s == ln and WS.sub("", t) == want]
            assert len(cand) == 1, "%s:%d 「%s」 命中 %d 块（应为 1）" % (f, ln, want, len(cand))
            a, b, t = cand[0]
            edits.append((a, b, t))
            print("  %-18s :%-4d 「%s」 → 『』" % (f, ln, WS.sub("", t)[:44]))
        # 从后往前换，偏移不串
        for a, b, t in sorted(edits, reverse=True):
            text = text[:a] + "『" + text[a + 1:b - 1] + "』" + text[b:]
        assert text.count("「") + len(edits) == (ROOT / f).read_text(encoding="utf-8").count("「"), \
            "%s 「 计数对不上 —— 有块被多改或少改" % f
        if apply:
            p.write_text(text, encoding="utf-8")
        total += len(edits)
    print("%s %d 块" % ("已改" if apply else "DRY-RUN：将改", total))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
