# -*- coding: utf-8 -*-
"""证明：这次改动**只动了注释与文档串** —— 去掉注释与文档串后，代码 token 流逐字相同。

用法：
    python3 notes/code-token-same.py <base-rev> core/center.py core/signals.py ...

三层证据，一层比一层硬：

  ① **token 流**：`tokenize` 剥掉 COMMENT，`ast` 认出**真文档串**（module/class/func 的第一条
     字符串语句）也剥掉，剩下的 `(类型, 原文)` 序列**前后逐条相同**（条数也相同）。
     ⇒ 机器读的那部分没被碰过。
  ② **字符级审计**：对每个文件做**位置级** diff（`difflib.SequenceMatcher` 按字符），
     规定：**单字符**替换只准是 `「→『` / `」→』`；**多字符**替换只准出现在事先点名的那两行
     （`core/pen.py:201`、`core/signals.py:71-73`）—— 越界即炸。
     ⇒ 也顺便证伪「有人偷偷全局替换」（pine 那卡的坑）。
  ③ **活字符串**：`ast` 数「含「／『的**非**文档串字符串」」（＝raise/print 这类用户看得见的文案）
     改前改后都是 0。

★ 为什么不能只交 ①：文档串也是用户读得到的正文（`help()`、Sphinx）。①保证程序行为不变，
  ②保证改动**看得见地**落在注释/文档串里、且没有顺手改别处；两条要一起交。
"""
import ast
import difflib
import io
import re
import subprocess
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DROP = (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
        tokenize.DEDENT, tokenize.ENDMARKER, tokenize.ENCODING)
# 允许多字符替换的行（本次两处特例；其余一律只准单字符引号替换）
BIG_EDIT_LINES = {"core/pen.py": (201, 201), "core/signals.py": (71, 73)}
QUOTE_MAP = {"「": "『", "」": "』"}


def docstring_spans(src):
    """真文档串的 (起行, 起列, 止行, 止列) —— 只有「某个 body 的第一条语句」才算。"""
    out = []
    tree = ast.parse(src)
    SCOPE = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    # ★ 只认这四种作用域的 body：`ast.Lambda` / `ast.IfExp` **也有 `body` 字段**，
    #   但那是表达式不是语句表（`lambda: "x"` 的 body 是 Constant）—— 第一版在这里炸过。
    for node in ast.walk(tree):
        if not isinstance(node, SCOPE):
            continue
        body = node.body
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                and isinstance(first.value.value, str):
            v = first.value
            out.append((v.lineno, v.col_offset, v.end_lineno, v.end_col_offset))
    return out


def codetokens(src):
    """(去掉注释与文档串的 token 流, 留下的活字符串清单)。"""
    ds = docstring_spans(src)
    toks, live = [], []
    for t in tokenize.generate_tokens(io.StringIO(src).readline):
        if t.type in DROP:
            continue
        if t.type == tokenize.STRING:
            (r0, c0), (r1, c1) = t.start, t.end
            if any(r0 == a and c0 == b and r1 == c and c1 == d for a, b, c, d in ds):
                continue
            live.append((r0, t.string))
        toks.append((t.type, t.string))
    return toks, live


def char_audit(path, old, new):
    """位置级 diff：返回 (违规清单, 已登记的多字符改动清单)（违规为空＝过）。"""
    bad, big = [], []
    ol = old.split("\n")
    sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        o, n = old[i1:i2], new[j1:j2]
        ln = old.count("\n", 0, i1) + 1
        if tag == "replace" and len(o) == 1 and len(n) == 1 and QUOTE_MAP.get(o) == n:
            continue
        rng = BIG_EDIT_LINES.get(path)
        if rng and rng[0] <= ln <= rng[1]:
            big.append((ln, o, n))
            continue
        bad.append((ln, tag, o, n))
    return bad, big, ol


def main(argv):
    rev = argv[1]
    ok_all = True
    for path in argv[2:]:
        old = subprocess.run(["git", "show", "%s:%s" % (rev, path)],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout
        new = (ROOT / path).read_text(encoding="utf-8")
        print("=" * 78)
        print("%s  ← %s" % (path, rev))
        if old == new:
            print("  （无差异）")
            continue
        to, lo_ = codetokens(old)
        tn, ln_ = codetokens(new)
        same = to == tn
        print("  ① 去注释/文档串后 token：%d → %d，逐条%s" %
              (len(to), len(tn), "相同 ✓" if same else "**不同 ✗**"))
        if not same:
            ok_all = False
            for k, (a, b) in enumerate(zip(to, tn)):
                if a != b:
                    print("     第一处不同 #%d：%r ≠ %r" % (k, a, b))
                    break
        live_q = [(r, s) for r, s in ln_ if "「" in s or "『" in s]
        print("  ③ 活字符串（非文档串）里含「／『：%d 处 %s" % (len(live_q), "✓" if not live_q else "**✗**"))
        if live_q:
            ok_all = False
            print("     %r" % live_q[:3])
        bad, big, ol = char_audit(path, old, new)
        nq = sum(1 for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes()
                 if tag == "replace" and len(old[i1:i2]) == 1 and QUOTE_MAP.get(old[i1:i2]) == new[j1:j2])
        print("  ② 字符级：引号单字符替换 %d 处%s" %
              (nq, "" if not bad else "；**越界 %d 处 ✗**" % len(bad)))
        for ln, o, n in big:
            print("     已登记的多字符改动 :%-4d %r → %r" % (ln, o, n))
        for ln, tag, o, n in bad:
            ok_all = False
            print("     :%-4d %s  %r → %r" % (ln, tag, o[:60], n[:60]))
    print("=" * 78)
    print("**全部通过 ✓**" if ok_all else "**有不过的项 ✗**")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
