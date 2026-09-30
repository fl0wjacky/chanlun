# -*- coding: utf-8 -*-
"""**器外第二条路径**：相邻性那一问的逐条清单。

不 import 器、不 import verify_quotes 的 Corpus —— 自己贪心、自己算空隙。
（第二份实现不许跑得比第一份野 ⇒ 先自证：逐格处数必须与器印的逐格处数逐位相同，
 不等就把结论吞掉、exit 9。）

跑法：
    python3 notes/adjacency_probe.py --commit 05f3e24 \
        --sidecar /tmp/speaker_axis_judged.tsv
"""
import argparse, io, os, re, shutil, subprocess, sys, tempfile, unicodedata

ELL = re.compile(u"…+")
PUNCT = re.compile(u"[，。、；：？！“”‘’（）《》〈〉「」『』—…·\\s\"'`,;:()\\[\\]{}.!?<>|/~@#$%^&*+=-]+")
FOLD = re.compile(u"(.)\\1+")
DISPLAY_NL = u"⏎"


def norm(s):
    """与器同名同义：去标点 + 折叠相邻同字。"""
    return FOLD.sub(r"\1", PUNCT.sub("", s))


def greedy_chain(blob, lo, hi, parts):
    """按原顺序贪心取最小递增落点（器外重写）。返回落点表或 None。"""
    cur, out = -1, []
    for p in parts:
        best = None
        i = blob.find(p, lo)
        while i >= 0 and i < hi:
            if i > cur:
                best = i
                break
            i = blob.find(p, i + 1)
        if best is None:
            return None
        cur = best
        out.append((best, best + len(p)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", required=True)
    ap.add_argument("--sidecar", required=True)
    ap.add_argument("--corpus-rel", default=os.path.join("archive", "chanlun108", "text"))
    a = ap.parse_args()

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tmp = tempfile.mkdtemp(prefix="adjprobe-")
    try:
        tar = subprocess.Popen(["git", "archive", a.commit], cwd=repo,
                               stdout=subprocess.PIPE)
        subprocess.check_call(["tar", "-x", "-C", tmp], stdin=tar.stdout)
        tar.wait()

        # ---- 语料：自己拼 108 课，自己记课界 ----
        # ★ 语料**不在 git 树里**（`archive/` 是 SKIP）⇒ 只能读工作目录那份，
        #   同器走的是同一个对象（语料指纹 cc27e258cdd52eab）。别去 git archive 里找。
        txt = os.path.join(repo, a.corpus_rel)
        docs = []
        for f in sorted(os.listdir(txt)):
            m = re.match(r"lesson-(\d+)\.txt$", f)
            if m:
                docs.append((int(m.group(1)),
                             io.open(os.path.join(txt, f), encoding="utf-8").read()))
        docs.sort()
        starts, ends, nums, parts = [], [], [], []
        pos = 0
        for n, body in docs:
            # ★★ 语料也必须 `norm()` 过 —— 器的 `Corpus(docs, V.norm)` 就是这么建的，
            #    而链上的零件是 `norm(段)`。**归一化只做在一侧 ⇒ 一个都找不到**（我这个 bug
            #    第一版就犯在这里：拿 norm 过的零件去 find 没归一化的语料 ⇒ 一片假红）。
            t = norm(body)
            starts.append(pos); ends.append(pos + len(t)); nums.append(n)
            parts.append(t); pos += len(t) + 1
        blob = "\n".join(parts)
        print(u"语料：%d 课 · blob %d 字（**norm 后**；器外自拼，不用 V.Corpus）" % (len(docs), len(blob)))

        # ---- 逐条 ----
        rows = []
        for line in io.open(a.sidecar, encoding="utf-8"):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            c = line.split("\t")
            if len(c) < 4:
                continue
            rows.append({"面": c[0], "引文": c[1], "判词": c[2], "坐标": c[3]})

        FIX = {u"cards/c06_trend.py:99": u"固件① 删32字",
               u"core/pen.py:201": u"固件② 插+段首删",
               u"core/segment.py:17": u"固件③ 插+压缩",
               u"core/segment.py:8": u"回归点 删8字"}
        # 固件① 不在旁档里（旁档里它是 (a)）；单独补进来
        EXTRA = [(u"cards/c06_trend.py:99", u"(a)",
                  u"A、中枢扩张导致一个更大级别的中枢；B、中枢新生，就会形成一个上涨的趋势")]

        print()
        print(u"%-26s %-9s %-6s %-7s %-9s %-11s %s"
              % (u"坐标", u"判词", u"含省略", u"能问到", u"chain_in",
                 u"语料空隙", u"相邻性判什么"))
        print(u"-" * 118)

        stats = {"chain_green_adj_red": 0, "chain_green_adj_green": 0,
                 "unreachable": 0, "chain_red": 0}

        def one(coord, verdict, q):
            q = q.replace(DISPLAY_NL, u"\n")
            has_ell = bool(ELL.search(q))
            segs = [s for s in ELL.split(q) if s.strip()]
            reach = has_ell and len(segs) > 1
            parts_n = [norm(s) for s in segs] if reach else []
            chain = None
            lands = None
            if reach and all(parts_n):
                for j in range(len(nums)):
                    lands = greedy_chain(blob, starts[j], ends[j], parts_n)
                    if lands:
                        break
                chain = u"绿" if lands else u"红"

            # 相邻性：连着两个零件的落点，**两侧空隙各自是什么**（@iris-64a1 的定义）
            #   语料那头空隙 = C[p+len(c1) : q]   ← 语料的文字，不是我挑的
            #   我们这头空隙 = Q[段1尾 : 段2头]   ← ★ 这一半才是判据的另一半
            # ★★ 只有"语料那头有字"判不了任何事 —— 那是一句**标了省略号的省略**的**常态**。
            #    要两侧一起看：「我们这头」空（只剩省略号）才是"标了"；语料那头空 = 省略号**虚设**。
            adj = u"—（没问）"
            gcorp = u""
            if lands and len(lands) > 1:
                gs = []
                ours_nonempty = False
                for k in range(len(lands) - 1):
                    pc = blob[lands[k][1]:lands[k + 1][0]]
                    # 我们这头：两段之间（引文里）夹的东西，**去掉省略号与标点后还剩什么**
                    m = ELL.search(q)
                    our_gap = u""
                    pos = 0
                    for si in range(k + 1):
                        pos = q.find(segs[si], pos) + len(segs[si])
                        e = ELL.search(q, pos)
                        if e:
                            our_gap = q[pos:e.start()]
                            pos = e.end()
                    if norm(our_gap):
                        ours_nonempty = True
                    gs.append((pc, our_gap))
                gcorp = u" / ".join(u"%d字(%s)" % (len(x[0]), x[0][:8]) for x in gs)
                corpus_has = any(x[0].strip() for x in gs)
                if ours_nonempty:
                    adj = u"★红：**我们这头**省略号外还有字，而它不是标点 ⇒ 插入"
                    stats["chain_green_adj_red"] += 1
                elif not corpus_has:
                    adj = u"★红：语料那头是**空的**(两段紧挨着) ⇒ 省略号**虚设**（没东西可省）"
                    stats["chain_green_adj_red"] += 1
                else:
                    adj = u"绿：我们这头只剩省略号、语料那头有字 ⇒ 标了的省略（可定位）"
                    stats["chain_green_adj_green"] += 1
            elif reach:
                stats["chain_red"] += 1
            else:
                stats["unreachable"] += 1

            tag = FIX.get(coord, u"")
            print(u"%-26s %-9s %-6s %-7s %-9s %-11s %s%s"
                  % (coord[:26], verdict, u"是" if has_ell else u"否",
                     u"是(%d段)" % len(segs) if reach else u"**否**",
                     chain or u"—", gcorp[:11], adj,
                     (u"   ← " + tag) if tag else u""))

        for coord, verdict, q in EXTRA:
            one(coord, verdict, q)
        for r in rows:
            if r["判词"] in (u"省略",) or r["判词"].startswith(u"配对伪影"):
                one(r["坐标"], r["判词"][:6], r["引文"])

        print()
        print(u"统计：能问到且 chain_in 绿、相邻性却判红 = %d ｜ 两边都绿 = %d ｜ "
              u"chain_in 直接红 = %d ｜ **根本问不到** = %d"
              % (stats["chain_green_adj_red"], stats["chain_green_adj_green"],
                 stats["chain_red"], stats["unreachable"]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
