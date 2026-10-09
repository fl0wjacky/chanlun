#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L77 第二支（card-c784a101-791，b5-spec 第 3 步「② 坐实以后又越过 V」）：A 被一个反弹线段 R 破坏、之后越过 V ⇒ X＋A＋R 合成一段。

    python3 tools/l77_check.py              # rc=0 才算过
    python3 tools/l77_check.py --self-test  # 关掉 L77_MERGE（＝修之前的引擎）⇒ 主跑必须红（rc=0 ＝ 红了）

逐格：
  ① 夹具 tools/fixtures/l77_pens.json：1300 合成 15-25、1600 合成 4-10（各是向上 / 向下越过 V 的那一种）、1317 不合；三颗 check_segments 都是 0；
  ② 每个合段**逐笔加长时第一次出现的前缀长度**＝ 引擎算的合段时刻 max(R 确认, c＋1)：合段时刻是二分出来的，
     这一格拿整份逐笔加长去对 —— 两条不同的路算出同一个数，才说明「当下能知道」没算偏；
  ③ 随机 4000 组（同一个生成器）：check_segments 违规 0（修前 2 组）；
  ④ 独立复核 verify_by_definition 的 case 4 那一支：合段 0 处；终点前后挪 2 笔必须报；
  ⑤ 复核的结构条件有牙：反弹收成一笔（L77 第一支的形状）、A 收成一笔、R 头三笔没有公共重叠，三样标了合段都必须报。
"""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import core.segment as S                                 # noqa: E402
from core.segment import build_segments, check_segments  # noqa: E402

WANT = {"1300": [(15, 25)], "1600": [(4, 10)], "1317": []}


def gen(sd):
    """跟夹具同一个生成器（note 里写的那个）。"""
    rng = random.Random(sd)
    n = rng.choice([30, 50, 80])
    P, p, up = [], 100.0, None
    up = rng.random() < .5
    for k in range(n):
        d = rng.choice([0.3, 0.6, 1, 1.5, 2.5, 4]) * (1 if up else -1)
        q = round(p + d, 2)
        P.append(dict(p0=p, p1=q, hi=max(p, q), lo=min(p, q), i0=k * 5, i1=k * 5 + 5, dir="up" if up else "down"))
        p, up = q, not up
    return P


def merge_time(P, seg, segs):
    """引擎口径的合段时刻：max(R 确认的前缀长度, c＋1)。"""
    i = seg["PI0"]
    prev = next(t for t in segs if t["PI1"] == i - 1)
    A = S._first_seg(P, i + 1)
    R = S._first_seg(P, A["PI1"] + 1)
    up = prev["dir"] == "up"
    c = next(r for r in range(A["PI1"] + 1, len(P)) if S._beyond(P[r], prev["p1"], up, S.S10_TIE))
    return max(S._done_at(P, A["PI1"] + 1, R["PI1"], S.FEAT_STD_DEFAULT), c + 1)


def main(quiet=False):
    say = (lambda *a: None) if quiet else print
    bad = 0
    fx = json.load(open(os.path.join(HERE, "fixtures", "l77_pens.json")))["seeds"]
    for sd, P in fx.items():
        segs = build_segments(P)
        v = check_segments(segs, P, [])
        got = [(s["PI0"], s["PI1"]) for s in segs if s.get("case") == 4]
        ok = not v and got == WANT[sd]
        bad += not ok
        say("%s ① seed %s：合段 %s（应为 %s），违规 %d %s" % ("✓" if ok else "✗", sd, got, WANT[sd], len(v), v[:1] if v else ""))
        for s in [s for s in segs if s.get("case") == 4]:
            first = next((n for n in range(3, len(P) + 1)
                          if any(t["PI0"] == s["PI0"] and t["PI1"] == s["PI1"] and t.get("case") == 4 and not t.get("live")
                                 for t in build_segments(P[:n]))), None)
            t = merge_time(P, s, segs)
            ok2 = first == t
            bad += not ok2
            say("%s ② seed %s 合段 %d-%d：逐笔加长第一次出现在前缀 %s，引擎算的合段时刻 %s" % ("✓" if ok2 else "✗", sd, s["PI0"], s["PI1"], first, t))
    # ④ 独立复核 verify_by_definition 认得合段（它有一支专按 L77 原文的形状判 case 4，不调引擎）：正常 0 处；
    #    把合段终点往前、往后各挪 2 笔，都必须报「L77 合段不成立」—— 这一支不是摆设
    for sd, d in (("1300", -2), ("1600", 2)):
        P = fx[sd]
        segs = build_segments(P)
        v0 = S.verify_by_definition(segs, P)
        m = next((s for s in segs if s.get("case") == 4), None)
        if m is None:                             # 没有合段（关了 L77_MERGE）：这一格就是不过，不许崩
            bad += 1
            say("✗ ④ seed %s：没有合段可挪" % sd)
            continue
        m["PI1"] += d
        m["p1"] = P[m["PI1"]]["p1"]
        v1 = [x for x in S.verify_by_definition(segs, P) if x[0] == "L77 合段不成立"]
        ok4 = not v0 and bool(v1)
        bad += not ok4
        say("%s ④ seed %s：复核 %d 处；合段终点挪 %+d 笔 ⇒ 报 %d 处「L77 合段不成立」" % ("✓" if ok4 else "✗", sd, len(v0), d, len(v1)))
    # ⑤ 复核分得出 L77 第一支、第二支（Atlas 23:02）：把 1600 的反弹 R（8-10）收成一笔、合段照样标 case 4，
    #    这就是第一支 ⟪如果这个反弹只是一笔……走势A依然延续⟫ 的形状 —— 复核必须报「L77 合段不成立」
    P0 = fx["1600"]
    P1 = [dict(p) for p in P0]
    P1[8] = dict(P1[8], p1=P1[10]["p1"], hi=max(P1[8]["hi"], P1[10]["hi"]), lo=min(P1[8]["lo"], P1[10]["lo"]))
    del P1[9:11]
    segs0 = build_segments(P0)
    m0 = next((s for s in segs0 if s.get("case") == 4), None)
    if m0 is None:
        bad += 1
        say("✗ ⑤ seed 1600：没有合段可改")
    else:
        fake = [dict(s) for s in segs0 if s["PI1"] < m0["PI0"]] + [dict(m0, PI1=8, p1=P1[8]["p1"])]
        v5 = [x for x in S.verify_by_definition(fake, P1) if x[0] == "L77 合段不成立"]
        bad += not v5
        say("%s ⑤a 反弹收成一笔（第一支的形状）却标了合段 ⇒ 复核报 %d 处" % ("✓" if v5 else "✗", len(v5)))
        # ⑤b A 只有一笔：把 1600 的 A（5-7）收成一笔，合段终点跟着前移 2 笔
        P2 = [dict(p) for p in P0]
        P2[5] = dict(P2[5], p1=P2[7]["p1"], hi=max(P2[5]["hi"], P2[7]["hi"]), lo=min(P2[5]["lo"], P2[7]["lo"]))
        del P2[6:8]
        fake2 = [dict(s) for s in segs0 if s["PI1"] < m0["PI0"]] + [dict(m0, PI1=m0["PI1"] - 2, p1=P2[m0["PI1"] - 2]["p1"])]
        v5b = [x for x in S.verify_by_definition(fake2, P2) if x[0] == "L77 合段不成立"]
        bad += not v5b
        say("%s ⑤b A 收成一笔却标了合段 ⇒ 复核报 %d 处" % ("✓" if v5b else "✗", len(v5b)))
        # ⑤c R 三笔没有公共重叠（L65「有重叠部分的连续三笔」那一条）：把 R 第三笔整个挪到前两笔够不着的地方
        P3 = [dict(p) for p in P0]
        lo3 = max(P3[8]["hi"], P3[9]["hi"]) + 0.5
        P3[10] = dict(P3[10], p0=lo3, p1=lo3 + 1.0, lo=lo3, hi=lo3 + 1.0)
        v5c = [x for x in S.verify_by_definition([dict(s) for s in segs0 if s["PI1"] <= m0["PI1"]], P3) if x[0] == "L77 合段不成立"]
        bad += not v5c
        say("%s ⑤c R 头三笔没有公共重叠却标了合段 ⇒ 复核报 %d 处" % ("✓" if v5c else "✗", len(v5c)))
    hit = [sd for sd in range(4000) if check_segments(build_segments(gen(sd)), gen(sd), [])]
    bad += bool(hit)
    say("%s ③ 随机 4000 组违规 %d 组 %s" % ("✓" if not hit else "✗", len(hit), hit[:8]))
    say("全部通过" if not bad else "%d 格不过" % bad)
    return 1 if bad else 0


def self_test():
    S.L77_MERGE = False
    try:
        rc = main(quiet=True)
    finally:
        S.L77_MERGE = True
    print("%s 关掉 L77_MERGE（修之前的引擎）⇒ %s" % ("✓" if rc else "✗", "红" if rc else "没红（尺子没牙）"))
    return 0 if rc else 3


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
