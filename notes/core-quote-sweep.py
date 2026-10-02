# -*- coding: utf-8 -*-
"""core/*.py 的「」块**逐块取证**：哪些是原文引文、哪些只是程序自己的标签（只读，不动任何文件）。

★ 档位**不自己实现**：直接 import `notes/concepts-pipeline/checkquotes.py` 的 `hits()`，
  用它那把尺本身判档 —— 换一套实现就是换一个母体，(那两边的数就再也不能并读了)。

为什么不能按读数批量处理：`checkquotes --min 4` 的『都不中 N 块』只说明**这一块在语料里捞不到**，
**不说为什么**。捞不到至少有三种因，处置完全不同：

  ① **标签** —— 程序自己的术语／不变量名／自检名，本来就不是引文 ⇒ 该改成『』（＝换引号）；
  ② **真引文漂移** —— 是引文，但被清理过／改过字／掐过尾 ⇒ **该报的错**，要照原文改回去
     （改『』等于把该报的错洗绿 —— 见 `memory/downgrade-needs-per-block-evidence.md`）；
  ③ **跨课拼装／换字** —— 两处原文接起来、或个别字被替换 ⇒ 也是①之外的另一种，要分开写。

本脚本给的是**逐块的证据**（判 ①/②/③ 要靠人读上下文，脚本只把材料摆齐）：
    · 尺自己的档位（strict / deco / ellipsis / norm / punct / miss）；
    · **最长前缀**落在哪一课、缺的尾巴是什么（差 1–2 字＋同课 ⇒ 更像漂移；头一个字就对不上 ⇒ 更像标签）；
    · **代码味**正则命中（`bars[b]`／`b-1`／`==`／`_x`）—— 语料里不可能有这些，命中即铁定不是引文。

用法：
    python3 notes/core-quote-sweep.py core/center.py core/signals.py core/pen.py core/extend.py core/preprocess.py
    python3 notes/core-quote-sweep.py 'core/*.py' --all     # 连命中的也列（默认只列不中/待看的）
"""
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── 尺：直接借 checkquotes.py 的 hits()（同母体） ─────────────────────────────
_spec = importlib.util.spec_from_file_location(
    "checkquotes_ruler", ROOT / "notes/concepts-pipeline/checkquotes.py")
CQ = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CQ)

LESSONS = {}
for p in sorted((ROOT / "archive/chanlun108/text").glob("lesson-*.txt")):
    LESSONS[int(p.stem.split("-")[1])] = p.read_text(encoding="utf-8").replace("\r", "").replace("\n", "")
FOLDED = {k: CQ.fold(v) for k, v in LESSONS.items()}
LOSSY = {k: CQ.lo(v) for k, v in LESSONS.items()}
NWS = {k: re.sub(r"\s+", "", v) for k, v in FOLDED.items()}

def dedup(s):
    """折叠**同字重复**（源页噪声的主要形态：`想想了想`、`的的`、`中枢枢`、`0 轴轴`）。

    ★ 只折叠 CJK 单字的重叠（`[一-鿿]`），K／数字／ASCII 不动 —— `KK`、`00` 可能是有意的。
    ★ 这是**筛查**不是证明：折叠会缩短查串，短串难免巧合命中；命中只说明『像是一条带噪声的引文』，
      最终判还是要人看上下文。语料侧也要一起折叠，否则噪声在两边不同形态时还是对不上。
    另带一处已知改字：`於 → 于`（`pen.py:14` 自己声明过这处清理）。
    """
    return re.sub(r"([一-鿿])\1+", r"\1", s).replace("於", "于")


def dedup_hit(q):
    """折叠噪声后，**按省略号切片逐段按序**在语料里找 —— 块里有 `…`（省掉了原文中段）时也能判。

    ★ 只折叠不够：`signals.py:71` 把 L24 的 `(也就是 DIFF 和 DEA)` 用 `…` 省掉了，
      整块折叠后照样不中 —— 那是**省略**挡的，不是噪声挡的，得切片找。
    """
    frags = [f for f in re.split(r"[…⋯]|\.{2,}", WS.sub("", CQ.fold(q))) if len(f) >= 3]
    if not frags:
        return None
    for n, t in DEDUP_CORPUS.items():
        pos = 0
        for f in frags:
            d = dedup(f)
            p = t.find(d, pos)
            if p < 0:
                break
            pos = p + len(d)
        else:
            return n
    return None


DEDUP_CORPUS = {k: dedup(v) for k, v in NWS.items()}

TOK = re.compile("「([^「」]*)」")
WS = re.compile(r"[\s↵]+")
CODEISH = re.compile(r"[\[\]{}<>]|::|\bdef\b|\breturn\b|\bNone\b|\bTrue\b|\bFalse\b|==|!=|_[a-z]")
# 只看的档（要人判的）：都不中 ＋ 仅标点归一；其余档是干净的
WATCH = ("miss", "punct", "norm")
TIER_CN = {"strict": "原样逐字", "deco": "剥装饰后", "ellipsis": "省略号按序",
           "norm": "仅空白归一", "punct": "仅标点归一", "miss": "都不中"}


def blocks(text):
    """抠「」块，带行号。★ 抽取规则与 `checkquotes.py` 逐字对齐：
    同一条正则、**在整篇文本上**跑（块可跨行）、门槛按**原始长度**。"""
    return [(text.count("\n", 0, m.start()) + 1, m.group(1)) for m in TOK.finditer(text)]


def divergence(q, k=3):
    """最长前缀 ＋ **语料里紧接其后写的是什么** —— 一眼分辨『差一两个字』还是『根本不是这句』。

    ★ 只报最长前缀落在哪一课是不够的：`pen.py:15` 的「本ID想」在 L22（`本ID想起N年前`）也命中，
      最长前缀同为 4 字，真正那一课却是 L81（`本ID想想了想，计算了一下下…`）。
      所以这里**把语料接下去的字一起印出来**（最多 k 课），读者自己看像不像。
    """
    qs = WS.sub("", CQ.fold(q))
    for cut in range(len(qs), 3, -1):
        cand = []
        for n, t in NWS.items():
            p = t.find(qs[:cut])
            if p >= 0:
                cand.append((n, t[p + cut:p + cut + 16]))
        if cand:
            return cut, cand[:k], qs[cut:]
    return 0, [], qs


def classify(path, min_len, show_all):
    print("=" * 78)
    print(path)
    text = Path(path).read_text(encoding="utf-8")
    rows = blocks(text)
    big = [(i, q) for i, q in rows if len(q) >= min_len]
    tally = {}
    print("「」块 %d ｜ ≥%d 字 %d" % (len(rows), min_len, len(big)))
    for ln, q in big:
        tier = CQ.hits(q, LESSONS, FOLDED, LOSSY, NWS, min_len)
        tally[tier] = tally.get(tier, 0) + 1
        if tier not in WATCH and not show_all:
            continue
        codeish = "★代码味" if CODEISH.search(q) else "        "
        print("  :%-4d [%s] %s ｜ %s" % (ln, TIER_CN[tier], codeish, WS.sub("", q)[:76]))
        if tier in WATCH:
            cut, cand, tail = divergence(q)
            if not cut:
                print("        最长前缀 0 字 —— 头一个字就对不上任何一课（多半是我们的标签，"
                      "少数是被改过头的引文，要看上下文）")
            else:
                print("        最长前缀 %d 字 ｜ 块里接着写「%s」" % (cut, tail[:22] or "（到此为止）"))
                for n, nxt in cand:
                    print("          语料 L%-3d 接着写「%s」" % (n, nxt or "（到此为止）"))
            dn = dedup_hit(q)
            if dn:
                print("        折叠噪声（＋省略号切片）后：**命中 L%d** —— ★真引文，被源页噪声/省略挡住的" % dn)
            else:
                print("        折叠噪声（＋省略号切片）后：仍不中 —— 至少不是这两样挡的")
    print("  档位：" + " ｜ ".join("%s %d" % (TIER_CN[k], tally.get(k, 0))
                                  for k in ("strict", "deco", "ellipsis", "norm", "punct", "miss")))
    return tally


def main(argv):
    show_all = "--all" in argv
    min_len = 4
    if "--min" in argv:
        min_len = int(argv[argv.index("--min") + 1])
    raw = [a for a in argv[1:] if not a.startswith("--")]
    files = [str(p) for a in raw for p in (sorted(ROOT.glob(a)) if "*" in a else [Path(a)])]
    tot = {}
    for f in files:
        for k, v in classify(f, min_len, show_all).items():
            tot[k] = tot.get(k, 0) + v
    print("=" * 78)
    print("合计：" + " ｜ ".join("%s %d" % (TIER_CN[k], tot.get(k, 0))
                                for k in ("strict", "deco", "ellipsis", "norm", "punct", "miss")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
