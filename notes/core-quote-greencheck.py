# -*- coding: utf-8 -*-
"""「」绿块的**假绿筛查** + 每块**所在层**（注释／docstring／活代码）—— 只读，不动文件。

两件事，都是 `core-quote-sweep.py`（红块取证）不覆盖的那一半：

## ① 假绿：尺子报「原样逐字」不等于「这块是引文」
`card-8bd8ca52-373`（pine 引号排版）踩过：`「简化」`『趋势』两字常用词**碰巧是语料子串**，
尺子报绿 —— 可它们是散文用「」，一样要改『』。⇒ **分桶看是两类，看「是不是引文」是一类。**
本脚本给三条机器可判的嫌疑：
  · **字数**：4–6 字的块嫌疑最大（越长越不可能是巧合）；
  · **命中课 ∩ 引述课**：散文（块前后 3 行内）写了「第 N 课」，但块**只在别的课**命中 ⇒ ★对不上；
  · **命中课数**：同一块在很多课里都出现 ⇒ 常用语，不是某课的引文。

## ② 层：这块改得改不得
Python 有 AST/tokenize，pine 那套「改动必须落在注释里」在 .py 上有更硬的版本：
每个「」块所在位置是 COMMENT（注释）、STRING（字符串字面量 —— 多是 docstring）、还是**活代码**（其余的 token 流）。
★ 只有注释与 docstring 里的「」才是纯排版；**活代码里的（raise/print 的文案）改了就改了用户看得见的东西** ——
那张 pine 卡上 `:32` tooltip 就是这一类，留待人点头。

用法：python3 notes/core-quote-greencheck.py core/center.py core/signals.py core/extend.py
     python3 notes/core-quote-greencheck.py 'core/*.py' README.md
"""
import importlib.util
import io
import re
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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

TOK = re.compile("「([^「」]*)」")
# ★ 「第 17 / 42 / 43 课」—— 课号是个**列表**，别用重复捕获组（它只留最后一次：会漏掉 42，
#   本器第一版就是这么把 extend.py:15 报成「命中课对不上」的假警报的）。
LESSON_REF = re.compile(r"第\s*((?:\d+\s*[/、]\s*)*\d+)\s*课")
WS = re.compile(r"[\s↵]+")


def layers(path):
    """块起点 → 层。用 tokenize 的 COMMENT/STRING 区间判：注释 / 字符串 / 活代码。"""
    src = Path(path).read_text(encoding="utf-8")
    nl = [0]
    for i, ch in enumerate(src):
        if ch == "\n":
            nl.append(i)
    spans = []
    try:
        for t in tokenize.generate_tokens(io.StringIO(src).readline):
            if t.type in (tokenize.COMMENT, tokenize.STRING):
                (r0, c0), (r1, c1) = t.start, t.end
                spans.append((t.type, nl[r0 - 1] + c0, nl[r1 - 1] + c1))
    except (tokenize.TokenError, IndentationError) as e:      # 不闭嘴：报出来
        return None, "tokenize 失败：%s" % e
    return spans, None


def layer_of(spans, off):
    if spans is None:
        return "?"
    for ty, a, b in spans:
        if a <= off < b:
            return {tokenize.COMMENT: "注释", tokenize.STRING: "字符串"}[ty]
    return "★活代码"


def cited_lessons(text, off):
    """块前后各 3 行里提到的「第 N 课」。"""
    lines = text[:off].count("\n")
    all_lines = text.split("\n")
    seg = "\n".join(all_lines[max(0, lines - 6):lines + 6])
    out = set()
    for m in LESSON_REF.finditer(seg):
        out.update(int(x) for x in re.findall(r"\d+", m.group(1)))
    return out


def where_verbatim(q):
    """整块逐字命中的课号（strict 档的口径：fold 后原样）。"""
    fq = CQ.fold(q)
    return [n for n, t in FOLDED.items() if fq in t]


def main(argv):
    raw = [a for a in argv[1:] if not a.startswith("--")]
    files = [str(p) for a in raw for p in (sorted(ROOT.glob(a)) if "*" in a else [Path(ROOT / a)])]
    tally = {}
    for f in files:
        text = Path(f).read_text(encoding="utf-8")
        spans, err = layers(f) if f.endswith(".py") else (None, None)
        print("=" * 78)
        print("%s%s" % (f, ("   ⚠️ " + err) if err else ""))
        rows = [(text.count("\n", 0, m.start()) + 1, m.start(), m.group(1)) for m in TOK.finditer(text)]
        lay = {}
        for ln, off, q in rows:
            L = layer_of(spans, off) if f.endswith(".py") else "文本"
            lay[L] = lay.get(L, 0) + 1
        print("「」块 %d ｜ 层：%s" % (len(rows), " ｜ ".join("%s %d" % kv for kv in sorted(lay.items()))))
        for ln, off, q in rows:
            if len(WS.sub("", q)) < 4:
                continue                              # 与尺子的 ≥4 门槛同口径
            hit = where_verbatim(q)
            if not hit:
                continue                              # 红块归 sweep 那支管
            cited = cited_lessons(text, off)
            L = layer_of(spans, off) if spans else "文本"
            flag = []
            if cited and not (cited & set(hit)):
                flag.append("★命中课 %s 与引述的 %s 对不上" % (hit[:4], sorted(cited)))
            if len(hit) > 8:
                flag.append("命中 %d 课（常用语）" % len(hit))
            if len(WS.sub("", q)) <= 6:
                flag.append("短（%d 字）" % len(WS.sub("", q)))
            if L == "★活代码":
                flag.append("★活代码")
            if flag:
                print("  :%-4d [%s] %s ｜ %s" % (ln, L, " · ".join(flag), WS.sub("", q)[:52]))
            tally["绿"] = tally.get("绿", 0) + 1
            if flag:
                tally["嫌疑"] = tally.get("嫌疑", 0) + 1
    print("=" * 78)
    print("绿块 %d ｜ 其中带嫌疑标记 %d（嫌疑不是判词 —— 长句对不上课号常是**引述课号写错**，"
          "短块常是真·术语）" % (tally.get("绿", 0), tally.get("嫌疑", 0)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
