#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""演示 · 第二轮 1：线段起点『开头三笔必须有公共重叠』（card-dc942cad-46f）。

原文（引文照口径：『』＝我的话，「」＝原文逐字，↵＝原文硬折行）：
  · L65:50-51「线段有一个最基本的前提，就是线段的前三笔，必须有重叠的部分，这个前提在前面可能没有特别强调，这里必须特别强调一次。线段至↵少有三笔，但并不是连续的三笔就一定构成线段，这三笔必须有重叠的部分。」
  · L77:69-70「由此可见，线段中包含笔的数目，都是单数的。而且，线段开始的那三笔，必须有重合，开始三笔没有重合的，是↵构不成线段的。」

这个演示回答五件事，缺一条结论就不算数：
  ④ **阳性对照（先做）**：同一台仪器去比一对『已知不同』的提交，它必须红 ——
     否则『改后没变』有两个解释：真的没变，或者这台仪器根本没接上；
  ① **改前/改后**：`data/` 每份数据的引擎输出哈希（逐位比，不比路径）；
  ② 真实数据上，六份的笔数／段数／开头无重叠数（改前 vs 改后）；
  ③ 随机行情：改前最短的反例长什么样，改后还在不在；
  ③b 换 **6 族**生成器再问一次『段界之后会不会也出现』 —— 一族样本答不了『不可能』；
  ⑤ **判据形状**的两条读数：证明『不能简化成只查相邻两笔』，并**更正**本卡初版那句
     『不是两两重叠』（理由是错的，见 `_opening_overlaps` docstring 的更正）。

用法：
    python3 docs/audit/round2-seg-start-demo.py                 # 对照 origin/main
    python3 docs/audit/round2-seg-start-demo.py --ref <sha>
"""
import argparse, json, os, random, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pine_lockstep as pl                                       # noqa: E402  （复用它的取树与哈希）

# ★ 正臂锚：这对提交之间引擎被重写过（笔极值／特征序列包含／三买卖终结／扩展合并），输出**必须**不同。
#   没有它，『改后没变』证明不了任何事。
SELFTEST_OLD, SELFTEST_NEW = "430e074", "67d1bd1"

STATS = r'''
import json, os, sys
tree = sys.argv[1]
sys.path.insert(0, tree)
import core
from core.segment import build_segments, check_segments
out = {}
d = os.path.join(tree, "data")
for f in sorted(os.listdir(d)):
    if not f.endswith(".json"): continue
    try:
        bars = json.load(open(os.path.join(d, f), encoding="utf-8"))
        if isinstance(bars, dict):
            bars = bars.get("bars") or bars.get("klines") or bars
        r = core.analyze(bars)
        pens = r["pens"]
        segs = build_segments(pens)
        bad = [b for b in check_segments(segs, pens) if b[0] == "开头三笔无公共重叠"]
        out[f] = dict(pens=len(pens), segs=len(segs), bad_open=len(bad),
                      bad_all=len(check_segments(segs, pens)))
    except Exception as e:
        out[f] = "跑不动:%s" % type(e).__name__
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False)
'''


def segstats(tree):
    """在 tree 里跑一遍引擎，回收每份数据的笔数／段数／开头无重叠数。"""
    fd, tmp = pl.tempfile.mkstemp(suffix=".json"); os.close(fd)
    p = subprocess.run([sys.executable, "-c", STATS, tree, tmp], capture_output=True, text=True)
    if p.returncode:
        print("★ 引擎在 %s 上跑不动 ⇒ 查不了（**不是「通过」**）：\n%s" % (tree, p.stderr.strip()[-600:]))
        raise SystemExit(2)
    return json.load(open(tmp, encoding="utf-8"))


# ---------------------------------------------------------------- 随机行情
RAND_SNIPPET = r'''
import json, random, sys
tree = sys.argv[1]
sys.path.insert(0, tree)
from core import analyze
from core.segment import build_segments, check_segments
def gen(rng, n=120):
    bars, price = [], 100.0
    for t in range(n):
        o = price
        h = o * (1 + abs(rng.gauss(0, 0.02))); l = o * (1 - abs(rng.gauss(0, 0.02)))
        bars.append(dict(t=t, o=o, h=h, l=l, c=rng.uniform(l, h))); price = bars[-1]["c"]
    return bars
def bad(pens, i):
    p3 = pens[i:i+3]
    return len(p3) == 3 and max(x["lo"] for x in p3) >= min(x["hi"] for x in p3)
rng = random.Random(20261002)
n_seg = n_bad = n_head = n_mid = 0
shotest = None
# ★ 阴性对照：新增一条判据很容易顺手把别的判据撞坏（往后挪一笔 → 相接断了／奇偶翻了）。
#   所以不能只看『新判据 0 违规』，还要把 check_segments 的**整张单子**收上来。
kinds = {}
for _ in range(3000):
    r = analyze(gen(rng)); pens = r["pens"]
    segs = build_segments(pens)
    for b in check_segments(segs, pens):
        kinds[b[0]] = kinds.get(b[0], 0) + 1
    for s in segs:
        n_seg += 1
        if bad(pens, s["PI0"]):
            n_bad += 1
            # ★ 分『序列开头』与『段界之后』两格 —— 决定这条判据该挂在哪儿
            if s["PI0"] == 0: n_head += 1
            else: n_mid += 1
            w = s["PI1"] - s["PI0"] + 1
            if shotest is None or w < shotest[0]:
                shotest = (w, s["PI0"], s["PI1"],
                           [(round(p["lo"], 4), round(p["hi"], 4)) for p in pens[s["PI0"]:s["PI0"]+3]])
json.dump(dict(segs=n_seg, bad=n_bad, head=n_head, mid=n_mid, shortest=shotest, kinds=kinds),
          open(sys.argv[2], "w"), ensure_ascii=False)
'''


# 『段界之后会不会也出现』—— 只用一族生成器答不了『不可能』，换 6 族再问一次。
FAM_SNIPPET = r'''
import json, random, sys
tree = sys.argv[1]
sys.path.insert(0, tree)
from core import analyze
from core.segment import build_segments
def bad(pens, i):
    p3 = pens[i:i+3]
    return len(p3) == 3 and max(x["lo"] for x in p3) >= min(x["hi"] for x in p3)
def walk(rng, n, sig, drift=0.0):
    bars, price = [], 100.0
    for t in range(n):
        o = price
        h = o * (1 + abs(rng.gauss(0, sig))); l = o * (1 - abs(rng.gauss(0, sig)))
        c = rng.uniform(l, h) if drift == 0 else min(h, max(l, o * (1 + drift)))
        bars.append(dict(t=t, o=o, h=h, l=l, c=c)); price = c
    return bars
def contain(rng, n):
    bars, price = [], 100.0
    for t in range(n):
        w = rng.uniform(0.005, 0.06)
        o = price; c = price * (1 + rng.gauss(0, 0.005))
        hi, lo = max(o, c), min(o, c)
        bars.append(dict(t=t, o=o, h=hi*(1+w), l=lo*(1-w), c=c)); price = c
    return bars
FAMS = [("walk", lambda r: walk(r, 120, 0.02)),
        ("wild", lambda r: walk(r, 120, 0.08)),
        ("trend", lambda r: walk(r, 120, 0.012, 0.004)),
        ("contain", lambda r: contain(r, 120)),
        ("tiny40", lambda r: walk(r, 40, 0.02)),
        ("big400", lambda r: walk(r, 400, 0.02))]
out = {}
for name, g in FAMS:
    rng = random.Random(20261002); seg = head = mid = 0
    for _ in range(300):
        r = analyze(g(rng)); pens = r["pens"]
        for s in build_segments(pens):
            seg += 1
            if bad(pens, s["PI0"]):
                if s["PI0"] == 0: head += 1
                else: mid += 1
    out[name] = dict(segs=seg, bad=head+mid, head=head, mid=mid)
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False)
'''


def famscan(tree):
    fd, tmp = pl.tempfile.mkstemp(suffix=".json"); os.close(fd)
    p = subprocess.run([sys.executable, "-c", FAM_SNIPPET, tree, tmp], capture_output=True, text=True)
    if p.returncode:
        print("★ 6 族扫描在 %s 上跑不动 ⇒ 查不了：\n%s" % (tree, p.stderr.strip()[-600:]))
        raise SystemExit(2)
    return json.load(open(tmp, encoding="utf-8"))


def randscan(tree):
    fd, tmp = pl.tempfile.mkstemp(suffix=".json"); os.close(fd)
    p = subprocess.run([sys.executable, "-c", RAND_SNIPPET, tree, tmp], capture_output=True, text=True)
    if p.returncode:
        print("★ 随机段在 %s 上跑不动 ⇒ 查不了：\n%s" % (tree, p.stderr.strip()[-600:]))
        raise SystemExit(2)
    return json.load(open(tmp, encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="origin/main")
    a = ap.parse_args()

    print("=" * 78)
    print("④ 阳性对照（先做）—— 这台仪器去比一对已知不同的提交，它必须红")
    print("=" * 78)
    rc = pl.compare(SELFTEST_OLD, SELFTEST_NEW, "自证·旧", "自证·新")
    if rc == 0:
        print("★ 正臂**没红** ⇒ 仪器判不出差异 ⇒ 下面所有「没变」都不算数。")
        return 3
    print("⇒ 正臂红了 ✓ —— 仪器接上了，下面印的「没变」才算数。\n")

    print("=" * 78)
    print("① 改前/改后 · data/ 每份数据的引擎输出哈希（%s → 工作区）" % a.ref)
    print("=" * 78)
    A = pl.ref_tree(a.ref)                                       # 取 ref 的树 → 跑引擎 → 哈希
    B = pl.outputs(ROOT)                                         # 工作区（未提交的改动也看得到）
    keys = sorted(set(A) | set(B))
    diff = [(k, A.get(k), B.get(k)) for k in keys if A.get(k) != B.get(k)]
    for k in keys:
        mark = "  " if A.get(k) == B.get(k) else "★ "
        print("   %s%-24s %-20s %s" % (mark, k, A.get(k), B.get(k)))
    print("   ⇒ %d 份数据 · %d 份不同" % (len(keys), len(diff)))
    print("   ⇒ %s\n" % ("输出**逐位相同** ⇒ 真实数据结果不变" if not diff
                         else "★ 输出变了 —— 与『真实数据结果不变』的验收不符"))

    print("=" * 78)
    print("② 线段读数 · 改前 vs 改后")
    print("=" * 78)
    sa, sb = segstats(pl.materialize(a.ref)), segstats(ROOT)
    print("   %-24s %-28s %s" % ("数据", "改前 笔/段/开头无重叠", "改后"))
    tot = [0, 0, 0, 0, 0, 0]
    for k in sorted(sa):
        x, y = sa[k], sb[k]
        if isinstance(x, str) or isinstance(y, str):
            print("   %-24s %s" % (k, x if isinstance(x, str) else y))
            continue
        print("   %-24s %4d /%4d /%4d            %4d /%4d /%4d"
              % (k, x["pens"], x["segs"], x["bad_open"], y["pens"], y["segs"], y["bad_open"]))
        tot = [tot[0] + x["pens"], tot[1] + x["segs"], tot[2] + x["bad_open"],
               tot[3] + y["pens"], tot[4] + y["segs"], tot[5] + y["bad_open"]]
    print("   %-24s %4d /%4d /%4d            %4d /%4d /%4d" % ("合计", *tot))
    print()

    print("=" * 78)
    print("③ 随机行情 3000 组 · 改前 vs 改后")
    print("=" * 78)
    ref = pl.materialize(a.ref)
    ra, rb = randscan(ref), randscan(ROOT)
    print("   改前：段 %d ｜ 开头三笔无公共重叠 **%d**（序列开头 %d ／ **段界之后 %d**）"
          % (ra["segs"], ra["bad"], ra["head"], ra["mid"]))
    if ra["shortest"]:
        w, i0, i1, rngs = ra["shortest"]
        print("         改前最短的反例：段笔 %d 根（PI0=%d..%d），三笔区间 %s" % (w, i0, i1, rngs))
        print("         公共区间 = [%.4f, %.4f] ⇒ 空" % (max(x[0] for x in rngs), min(x[1] for x in rngs)))
    print("   改后：段 %d ｜ 开头三笔无公共重叠 **%d**" % (rb["segs"], rb["bad"]))
    print("   ⇒ %s" % ("反例被消掉" if rb["bad"] == 0 else "★ 还有反例没消掉"))
    print()
    print("   阴性对照 · 同一批随机段上 check_segments 的**整张单子**（只看新判据会把别的撞坏看不出来）：")
    for tag, r in (("改前", ra), ("改后", rb)):
        print("     %s：%s" % (tag, r["kinds"] or "无任何违规"))
    print("   ⇒ %s" % ("除新判据外，其余判据的违规单子**逐项相同** ⇒ 没撞坏别的"
                       if {k: v for k, v in ra["kinds"].items() if k != "开头三笔无公共重叠"} == rb["kinds"]
                       else "★ 别的判据的违规数变了 ⇒ 往下查"))

    print()
    print("=" * 78)
    print("③b 换 6 族生成器 × 300 组 · 『段界之后』到底会不会出现？（只问改前那棵树）")
    print("=" * 78)
    print("   只用一族答不了『不可能』，所以换族重问。**段界之后只要有一例**，")
    print("   这条判据就不能只挂在序列开头。")
    fa = famscan(ref)
    print("   %-9s %7s %7s %7s %s" % ("族", "段", "无重叠", "序列开头", "段界之后"))
    th = tm = 0
    for name in fa:
        d = fa[name]
        print("   %-9s %7d %7d %7d %7d" % (name, d["segs"], d["bad"], d["head"], d["mid"]))
        th += d["head"]; tm += d["mid"]
    print("   %-9s %7s %7s %7d %7d" % ("合计", "", "", th, tm))
    print("   ⇒ 段界之后 %s" % ("**0 例** ⇒ 判据落在起点处成立" if tm == 0
                                else "★ %d 例 ⇒ 注释里那句『只在开头触发』不成立，得改代码" % tm))

    print()
    print("=" * 78)
    print("⑤ 判据形状 · 两条读数（更正初版那句『不是两两重叠』）")
    print("=" * 78)
    print("   1 维区间上，三对两两相交 ⟺ 三笔有公共段（Helly 数＝2）。")
    print("   所以真正会漏的不是『两两』，而是**只看相邻两对**。")
    print("   下面两个都是随机区间上的计数，**随分布变**，都不当发生率用。")
    rng = random.Random(20261002)
    N = 200000
    pw_bad = adj_bad = 0
    for _ in range(N):
        iv = []
        for _ in range(3):
            a = rng.uniform(0, 100)
            iv.append((a, a + rng.uniform(0.001, 40)))
        A, B, C = iv
        common = max(x[0] for x in iv) < min(x[1] for x in iv)
        pw = (max(A[0], B[0]) < min(A[1], B[1])) and (max(B[0], C[0]) < min(B[1], C[1])) \
            and (max(A[0], C[0]) < min(A[1], C[1]))
        adj = (max(A[0], B[0]) < min(A[1], B[1])) and (max(B[0], C[0]) < min(B[1], C[1]))
        if pw and not common:
            pw_bad += 1
        if adj and not common:
            adj_bad += 1
    print("   %d 组 · 种子 20261002（区间长 0.001~40，起点 0~100）" % N)
    print("   两两（三对全查）相交但无公共段：%d 例（%.4f%%）" % (pw_bad, 100.0 * pw_bad / N))
    print("   只查相邻两对  相交但无公共段：%d 例（%.4f%%）" % (adj_bad, 100.0 * adj_bad / N))
    print("   ⇒ %s" % ("两两 ⟺ 公共（Helly 成立），要拦的是『别简化』" if pw_bad == 0
                       else "★ 出现反例 ⇒ Helly 那条不成立，往下查"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
