# -*- coding: utf-8 -*-
"""**对账器**，不是判据 —— 把"某句话里的口径"翻成参数，跑出来对上／对不上。

用法（四个旋钮各给一个值，跑法就是这一行）：
    python3 tools/quotes_recount.py --tree 05f3e24 --min-len 6 --face literal \
        --dedup raw --v1ref skip
    python3 tools/quotes_recount.py --tree 05f3e24 --min-len 1 --face whole \
        --dedup norm --v1ref keep --json

它**故意不回答**「哪个才对」。它只回答一件事：**你写下的那句口径，跑出来是几**。
判据在 `tools/quotes_census.py`（那支的三箱与 rc 才是门）；这一支的存在理由是
"口径写成散文，两个人就实现成两条" —— 把散文翻成参数，分歧就变成**可跑的**，
而不是两段各说各话的回忆。

四个旋钮（就是这一支的全部输入，多一个都没有）：
    --tree    <sha|.>    哪棵树（sha 走 `git archive | tar -x` 到临时目录，跑完删）
    --min-len <n>        配对的**长度下限**（按 `norm()` 后的字数算，n=1 表示无下限）
    --face    whole|literal
                         whole   = 整篇正则在源码上扫（引文跨相邻字面量时中间夹 `",\\n"`）
                         literal = 逐字面量扫（拼接的引文被切断 ⇒ 那条判不到）
    --dedup   raw|norm   去重键：配对原文逐字，还是 `verify_quotes.norm(配对)`
    --v1ref   skip|keep  `tools/v1_ref` 跳不跳（其余 SKIP 一律跳：.git/archive/out/__pycache__）

退出：0 跑完 · 2 语料不在（**查不了 ≠ 通过**）
"""
import argparse, io, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_quotes as V                                   # noqa: E402  口径单一来源

CELLS = ("cards", "core", "render", "tools")
Q = re.compile(r"「([^「」]{1,400}?)」|『([^『』]{1,400}?)』", re.S)


def tree_dir(sha):
    """sha → 临时工作树。`.` 表示就地。"""
    if sha in (".", "", None):
        return None
    d = tempfile.mkdtemp(prefix="recount-")
    p = subprocess.run("git archive %s | tar -x -C %s" % (sha, d),
                       shell=True, cwd=V.ROOT)
    if p.returncode:
        shutil.rmtree(d, ignore_errors=True)
        raise SystemExit("取不到那棵树：%s" % sha)
    return d


def count(base, cell, a):
    n = 0
    keys = set()
    if not os.path.isdir(os.path.join(base, cell)):
        return 0, 0
    for root, _d, files in os.walk(os.path.join(base, cell)):
        if a.v1ref == "skip" and "v1_ref" in root:
            continue
        if any(("/%s" % s.split("/")[-1]) in root or root.endswith(s)
               for s in V.SKIP if s.split("/")[-1] != "v1_ref" or a.v1ref == "skip"):
            continue
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            t = io.open(os.path.join(root, f), encoding="utf-8").read()
            texts = [t] if a.face == "whole" else literal_bodies(t)
            for body in texts:
                for m in Q.finditer(body):
                    q = m.group(1) or m.group(2)
                    if len(V.norm(q)) < a.min_len:
                        continue
                    n += 1
                    keys.add(q if a.dedup == "raw" else V.norm(q))
    return n, len(keys)


LIT = re.compile(
    r"(?:[rbfuRBFU]{0,2})(?:"
    r'"""(?:[^"\\]|\\.|"(?!""))*"""'
    r"|'''(?:[^'\\]|\\.|'(?!''))*'''"
    r'|"(?:[^"\\\n]|\\.)*"'
    r"|'(?:[^'\\\n]|\\.)*'" r")")


def literal_bodies(text):
    import ast
    out = []
    for m in LIT.finditer(text):
        try:
            v = ast.literal_eval(m.group(0))
        except Exception:
            continue
        if isinstance(v, str):
            out.append(v)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", default=".")
    ap.add_argument("--min-len", type=int, default=6)
    ap.add_argument("--face", choices=("whole", "literal"), default="whole")
    ap.add_argument("--dedup", choices=("raw", "norm"), default="norm")
    ap.add_argument("--v1ref", choices=("skip", "keep"), default="skip")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    docs = V.load()
    if docs is None:
        print("语料不在 ⇒ 什么都没查（exit=2）。先跑 tools/fetch_chanlun108.py")
        return 2

    d = tree_dir(a.tree)
    base = d or V.ROOT
    try:
        print("量法   口径参数：tree=%s · min-len(norm后)=%d · face=%s · dedup=%s · v1_ref=%s"
              % (a.tree, a.min_len, a.face, a.dedup, a.v1ref))
        print("对象   %s" % base)
        print("语料   sha256:%s" % V.fingerprint(docs)[0])
        print()
        tot = [0, 0]
        for cell in CELLS:
            n, k = count(base, cell, a)
            tot[0] += n
            tot[1] += k
            print("  %-8s %4d 处 / %4d 条" % (cell, n, k))
        c = os.path.join(base, "config.py")
        if os.path.isfile(c) and a.face == "whole":
            t = io.open(c, encoding="utf-8").read()
            n = sum(1 for m in Q.finditer(t) if len(V.norm(m.group(1) or m.group(2))) >= a.min_len)
            print("  %-8s %4d 处" % ("config.py", n))
        print("  %-8s %4d 处 / %4d 条  ← 卡面那四格是 331 / 302" % ("合计", tot[0], tot[1]))
        print()
        print("★ 这一支不判对错，只把口径跑成数。判据看 tools/quotes_census.py 的三箱。")
    finally:
        if d:
            shutil.rmtree(d, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
