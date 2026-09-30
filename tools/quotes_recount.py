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

六个旋钮（就是这一支的全部输入，多一个都没有）：
    --tree    <sha|.>    哪棵树（sha 走 `git archive | tar -x` 到临时目录，跑完删）
    --min-len <n>        配对的**长度下限**（按 `norm()` 后的字数算，n=1 表示无下限）
    --face    whole|literal
                         whole   = 整篇正则在源码上扫（引文跨相邻字面量时中间夹 `",\\n"`）
                         literal = 逐字面量扫（拼接的引文被切断 ⇒ 那条判不到）
    --dedup   raw|norm   去重键：配对原文逐字，还是 `verify_quotes.norm(配对)`
    --v1ref   skip|keep  `tools/v1_ref` 跳不跳（其余 SKIP 一律跳：.git/archive/out/__pycache__）
    --unit    all|gone   ★ 单位（分母的定义）：
                         all  = **每一个**配对都进分母
                         gone = 只把「在 108 课原文里**找不到**」的配对算进去
    --ladder  norm|norm+ellipsis
                         ★ 阶梯（用哪档判据判"原文里有"）：
                         norm          = 整串规范化后查一次（卡面那套）
                         norm+ellipsis = 再加「逐段核（省）」那一档：含省略号的引文按
                                         `ELL` 切段、逐段规范化、要按原顺序落在同一课里
                                         （`V.split_ellipsis` + `Corpus.chain_in`）

★ `--ladder` 是再后补的，理由和 `--unit` 是同一件事的另一半：**Iris 拍的验收基准是
  「`norm` ＋ 逐段核（省）」= `68 / 50 / 179 / 14`，而在这格接线之前，那个数
  没有任何一条命令印得出来** —— 它只是 `tools/quotes_census.py` 文件头 `:147` 的一行字。
  **一个数只以散文形式存在 = 别人复现不出 = 判据不在公共面上。**
  接线后它是一条命令的输出：

    --unit gone --min-len 1 --face whole --dedup raw --v1ref keep --ladder norm
        ⇒ cards 78 · core 41 · render 16 · tools 182 · config 14 ⇒ **331 处 / 302 条**（卡面）
    --unit gone --min-len 1 --face whole --dedup raw --v1ref keep --ladder norm+ellipsis
        ⇒ cards 68 · core 34 · render 16 · tools 179 · config 14 ⇒ **311 处 / 283 条**
          （core+render = 50 ⇒ 就是验收基准那四格 `68/50/179/14`）

⇒ 报任何一格读数，**阶梯必须连"哪一档"一起报**：同一个旗标换一个值，
  四个桶全动（−10 / −7 / −3 / 0）。

★ `--unit` 是后补的，补的理由值得留着：**少了它，这支器就复现不了 `card-082d9aaa-cbb`
  那四格**。那四格数的**不是**全配对，是"找不到"的那些 —— 我先前把复跑命令写成
  `--min-len 1 --face whole --dedup raw --v1ref keep` 就发出去了，那一行跑出来是
  `577`，不是 `331`。**旋钮表里少了"分母是怎么定义的"这一格，等于没写口径。**

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


def found(q, a):
    """「原文里有」按 `--ladder` 判。

    norm           整串规范化后查一次（卡面那套：78 / 57 / 182 / 14）
    norm+ellipsis  再加「逐段核（省）」那一档 —— 含省略号的引文按 `ELL` 切段，
                   逐段规范化后要求**按原顺序**落在同一课里（`V.Corpus.chain_in`）。
                   ⇒ 这一档把"忠实省略的引用"和"真编造"分开，68 / 50 / 179 / 14。

    ★ 加 `--ladder` 的理由：Iris 拍的验收基准是 `norm + 逐段核（省）`，
      而在这支器加这一格之前，**`68/50/179/14` 没有任何一条命令印得出来** ——
      它只是 `quotes_census.py` 文件头 :147 的一行字。
      「一个数只以散文形式存在」= 别人复现不出 = 判据不在公共面上（见 memory/judgement-not-in-repo.md）。
      接线之后它是一条命令的输出，口径块里那一格就不再靠人手写。
    """
    corpus = a.corpus
    if corpus is None:
        return False                        # unit=all：不判"原文有没有"，这一档不参与
    if corpus.where(V.norm(q)):
        return True
    if a.ladder != "norm+ellipsis":
        return False
    segs, _kind = V.split_ellipsis(q)
    if not segs:
        return False
    parts = [V.norm(p) for p in segs]
    if not all(parts):
        return False
    return any(corpus.chain_in(parts, j) for j in range(len(corpus.nums)))


def count(base, cell, a):
    n = 0
    keys = set()
    if not os.path.isdir(os.path.join(base, cell)):
        return 0, 0
    corpus = a.corpus                     # None ⇒ unit=all，不建索引（省掉整趟扫描）
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
                    k = V.norm(q)
                    if len(k) < a.min_len:
                        continue
                    if found(q, a):
                        continue                  # 原文里有 ⇒ 不算「找不到」（按 --ladder）
                    n += 1
                    keys.add(q if a.dedup == "raw" else k)
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
    ap.add_argument("--unit", choices=("all", "gone"), default="all")
    ap.add_argument("--ladder", choices=("norm", "norm+ellipsis"), default="norm")
    a = ap.parse_args()

    docs = V.load()
    if docs is None:
        print("语料不在 ⇒ 什么都没查（exit=2）。先跑 tools/fetch_chanlun108.py")
        return 2
    # unit=gone 才建索引：它是"分母怎么定义"那一格，不是装饰。
    a.corpus = V.Corpus(docs, V.norm) if a.unit == "gone" else None

    d = tree_dir(a.tree)
    base = d or V.ROOT
    try:
        print("量法   口径参数：tree=%s · unit=%s · min-len(norm后)=%d · face=%s · "
              "dedup=%s · v1_ref=%s · ladder=%s"
              % (a.tree, a.unit, a.min_len, a.face, a.dedup, a.v1ref, a.ladder))
        print("对象   %s" % base)
        print("语料   sha256:%s" % V.fingerprint(docs)[0])
        print()
        tot = [0, 0]
        for cell in CELLS:
            n, k = count(base, cell, a)
            tot[0] += n
            tot[1] += k
            print("  %-8s %4d 处 / %4d 条" % (cell, n, k))
        # config.py 在仓根，不是一级目录 ⇒ 上面那轮走不到它。**它必须进合计**：
        # 卡面那四格是 cards / core+render / tools / **config.py**，
        # 331 = 78+57+182+14。先前这行只加前四桶 ⇒ 印 317，跟卡面差正好 14，
        # 而读到的人只会以为"对不上"。**合计行漏一个它自己刚印过的行 = 自证造不一致。**
        c = os.path.join(base, "config.py")
        if os.path.isfile(c) and a.face == "whole":
            t = io.open(c, encoding="utf-8").read()
            cn, ck = 0, set()
            for m in Q.finditer(t):
                q = m.group(1) or m.group(2)
                k = V.norm(q)
                if len(k) < a.min_len:
                    continue
                if found(q, a):
                    continue
                cn += 1
                ck.add(q if a.dedup == "raw" else k)
            print("  %-8s %4d 处 / %4d 条" % ("config.py", cn, len(ck)))
            tot[0] += cn
            tot[1] += len(ck)
        print("  %-8s %4d 处 / %4d 条  ← 卡面那四格是 331 / 302" % ("合计", tot[0], tot[1]))
        print()
        print("★ 这一支不判对错，只把口径跑成数。判据看 tools/quotes_census.py 的三箱。")
    finally:
        if d:
            shutil.rmtree(d, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
