# -*- coding: utf-8 -*-
"""card-ffffa2a9-043 演示：core/kline.py · preprocess.py · pen.py · segment.py

只跑现成代码、只打印，不修改 core/ 任何一行。仓库根直接跑：

    python3 docs/audit/engine-vs-spec_分型笔线段-demo.py

每一步对应 docs/audit/engine-vs-spec_分型笔线段.md 里的一行编号（D1…D5）。
"""
import glob
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))          # 仓库根，好让 `core` 能被 import

from core import kline as K
from core import pen as P
from core import segment as S

BAR = lambda h, l: dict(h=h, l=l)


def head(t):
    print("\n" + "=" * 72)
    print(t)
    print("=" * 72)


# ── D1 ───────────────────────────────────────────────────────────────────
# 「整段互相包含」时 standardize 取 bars[0]，不是包络、也不是任何一种合并
head("D1  开头互相包含：standardize 不合并，直接取第一根（A7）")
for bars in ([BAR(10, 5), BAR(12, 4)],
             [BAR(10, 5), BAR(12, 4), BAR(11, 6)]):
    out = K.standardize(bars)
    hi = max(b["h"] for b in bars)
    lo = min(b["l"] for b in bars)
    print("  输入            ", [(b["h"], b["l"]) for b in bars])
    print("  真实包络         h=%d l=%d" % (hi, lo))
    print("  standardize 输出 ", [(b["h"], b["l"]) for b in out])
    print("  ⇒ 输出的最高 %d ≠ 真实最高 %d ：这一根把 %d 那个高点丢了"
          % (out[0]["h"], hi, hi))
    print()

# ── D2 ───────────────────────────────────────────────────────────────────
# 方向判据里那个「高点相等」分支，在标准化序列上打不到
head("D2  kline.py:61 的 `p.h == p2.h` 分支：全库数据上不可达（A5）")
tot_pairs = tot_eq = 0
for path in sorted(glob.glob("data/*.json")):
    try:
        bars = json.load(open(path))
    except Exception:
        continue
    if not isinstance(bars, list) or not bars or "h" not in bars[0]:
        continue
    m = K.standardize(bars)
    eq = sum(1 for a, b in zip(m, m[1:]) if a["h"] == b["h"])
    tot_pairs += max(0, len(m) - 1)
    tot_eq += eq
    if eq:
        print("   ★ %s：%d 处相邻高点相等" % (path, eq))
print("  扫了 data/*.json：相邻标准化K线共 %d 对，高点相等 %d 对" % (tot_pairs, tot_eq))

rng = random.Random(20261002)
rand_eq = rand_bad = 0
for _ in range(20000):
    n = rng.randint(2, 12)
    bars = [BAR(rng.randint(1, 40), rng.randint(-40, 0)) for _ in range(n)]
    bars = [BAR(b["h"], min(b["l"], b["h"] - rng.randint(0, 3))) for b in bars]
    m = K.standardize(bars)
    rand_eq += sum(1 for a, b in zip(m, m[1:]) if a["h"] == b["h"])
    rand_bad += len(K.check_standardized(m))
print("  随机 20000 段：相邻高点相等 %d 对；check_standardized 违规 %d 次"
      % (rand_eq, rand_bad))
print("  ⇒ 该分支不可达；它一旦被走到，代码答『向下』，而 L65:16 原文说的是 gn>=gn-1 ⇒『向上』")

# ── D3 ───────────────────────────────────────────────────────────────────
# 同一个「开头定不出方向」，K线层与特征序列层给了两个不同答案
head("D3  同一个开头问题、两个答案（A7 ↔ C2）")
bars = [BAR(10, 5), BAR(12, 4), BAR(11, 6)]
print("  输入（三者互相包含）", [(b["h"], b["l"]) for b in bars])
print("  kline.standardize          →",
      [(b["h"], b["l"]) for b in K.standardize(bars)])
elems = [dict(h=b["h"], l=b["l"], i=i) for i, b in enumerate(bars)]
for up in (True, False):
    print("  segment._feature_std(up=%-5s) → %s"
          % (up, [(b["h"], b["l"]) for b in S._feature_std(elems, up)]))

# ── D4 ───────────────────────────────────────────────────────────────────
# 段内笔数与「开始三笔必须重合」：程序查了，说明书里没有
head("D4  说明书没写、程序在查的两条线段规则（C10 / C11，原文 L77:69）")
print("  程序里的两处：")
print("    core/segment.py:292   k = i + min_pens - 1 ; 之后每步 k += 2  ⇒ 步长 2 保笔数为单数")
print("    core/segment.py:186   if s['npens'] % 2 == 0 and not s.get('live'): 报违规")
print("  ⇒ 但 docs/spec/线段.md 全文没有『笔数单数』，也没有『开始三笔必须重合』。")

# ── D5 ───────────────────────────────────────────────────────────────────
# check_segments 的「笔数单数」在真实数据上是什么样
head("D5  真实数据上跑一遍：线段笔数的奇偶分布")
for path in ("data/zec15.json", "data/aaplusdt_30m.json", "data/zec_1h.json"):
    try:
        bars = json.load(open(path))
    except Exception:
        continue
    if not isinstance(bars, list) or not bars or "h" not in bars[0]:
        continue
    std = K.standardize(bars)
    fx = K.fractals(std)
    pens, seq = P.build_pens(fx, std, rule="old")
    segs = S.build_segments(pens)
    done = [s for s in segs if not s.get("live")]
    if not done:
        print("  %-24s 无已完成线段" % path)
        continue
    ev = sum(1 for s in done if s["npens"] % 2 == 0)
    print("  %-24s 已完成线段 %3d 条，笔数偶数 %d 条，check_segments 违规 %d 条，"
          "终点非极值 %d 条"
          % (path, len(done), ev, len(S.check_segments(segs, pens)),
             len(S.nonextreme_endpoints(segs))))

print()
