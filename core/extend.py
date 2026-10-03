# -*- coding: utf-8 -*-
"""把「扩展」真正算出来 —— 合成一个更大级别的中枢。

原文依据：
    第 49 课  两个次级别中枢 ＋ 连接两个次级别的段 = 三个次级别走势类型
    第 30 课  「5 分钟扩展成 30 分钟的，那第一个 5 分钟就是第一段」
              → 第一段 = 前中枢整体，第二段 = 连接段，第三段 = 后中枢整体
    第 54 课  算例：三个 1 分钟中枢「当成线段……高低点就是这线段的端点」，
              重叠出「该 5 分钟中枢的区间是[d2，g5]」
              → 每一段按它的高低点（中枢取波动范围 [DD, GG]）参与，区间 = [max(三段低点), min(三段高点)]
    第 52 课  「A+B+C=(A+B+C)，而后者符合更大的中枢定义」；答疑「中枢延伸的情况，只看前三段的区间，
              后面都是震荡」→ 大中枢的区间由**前三段定死**，之后接上来的中枢只算震荡，不改区间
    第 52 课  「中枢扩展不能预先说是某级别的，因为扩展可以不断延续下去」→ 链式：后面的中枢只要还碰到
              大中枢区间（中心定理一，高一级别上看），就继续算进来
    第 17 / 42 / 43 课  趋势里的中枢「之间是不会有任何重叠的」→ 相邻两中枢只要不是「趋势」
              （扩展，或区间直接重叠），就要合成大中枢

    级别：由本级别中枢合成出来的，一律是高一级别（level = 成员级别 + 1）；链再长也不再往上加 ——
    单个中枢延伸满 9 段的『9 段升级』是另一回事，见 center.upgrades。
"""


def _span(z):
    return z["DD"], z["GG"]


def big_interval(spans):
    """三段（各自的 [低, 高]）重叠出的大中枢区间 [ZD, ZG]（第 20 课公式，第 54 课算例）。"""
    return max(s[0] for s in spans), min(s[1] for s in spans)


def merge_extended(A, B, pens):
    """前中枢 A + 连接段 + 后中枢 B 三段重叠 → 大中枢（区间由这三段定死）。"""
    conn = pens[A["PI1"] + 1: B["PI0"]]          # 连接段（前中枢终点与后中枢起点之间的那一两段）
    s1, s3 = _span(A), _span(B)
    s2 = (min(p["lo"] for p in conn), max(p["hi"] for p in conn)) if conn else s3
    spans = [s1, s2, s3]
    ZD, ZG = big_interval(spans)
    return dict(
        ZD=ZD, ZG=ZG, valid=(ZG >= ZD),
        DD=min(s[0] for s in spans), GG=max(s[1] for s in spans),
        spans=spans, nconn=len(conn),
        PI0=A["PI0"], PI1=B["PI1"],
        X0=A["X0"], X1=B["X1"], X2=B["X1"],
        level=A.get("level", 1) + 1,
        members=[A, B],
        live=B.get("live", False),               # 链尾成员仍在延续 → 合成体也未完成（画虚线）
    )


def _absorb(big, C):
    """C 的波动范围仍碰到大中枢区间 → 算作震荡接进来：区间不变，只扩波动范围、终点和成员。"""
    lo, hi = _span(C)
    big.update(DD=min(big["DD"], lo), GG=max(big["GG"], hi), PI1=C["PI1"], X1=C["X1"], X2=C["X1"],
               members=big["members"] + [C], live=C.get("live", False))


def build_hierarchy(zs, pens):
    """在全体同级别中枢上跑一遍，合成高一级别的中枢；不合的原样留下（nmerge=1）。

    类中枢带 `seg` 字段时，合成**只在同一段内**进行（段与段之间不接续、不合并）；
    线段中枢不带 `seg`（`None == None`），退回全局合成，行为与从前一致。"""
    from .center import classify_pair
    out, k = [], 0
    while k < len(zs):
        A = zs[k]
        if k + 1 < len(zs) and not A.get("live") \
                and A.get("seg") == zs[k + 1].get("seg") \
                and classify_pair(A, zs[k + 1])[1] != "趋势":
            big = merge_extended(A, zs[k + 1], pens)
            k += 2
            while k < len(zs) and big["valid"] and not big["live"]:
                if zs[k].get("seg") != A.get("seg"):   # 跨段：不接续，大中枢到此为止
                    break
                lo, hi = _span(zs[k])
                if lo > big["ZG"] or hi < big["ZD"]:   # 整段离开大中枢区间 → 大中枢到此为止
                    break
                _absorb(big, zs[k])
                k += 1
            big["nmerge"] = len(big["members"])
            out.append(big)
        else:
            out.append(dict(A, valid=A["ZG"] >= A["ZD"], nmerge=1, level=A.get("level", 1)))
            k += 1
    return out


def check_hierarchy(big, zs, pens):
    """自检合成结果。返回违规列表（应为空）。

    · 成员首尾相接、覆盖全部中枢、顺序不乱；
    · 区间 = 前三段（前中枢、连接段、后中枢）重算，之后的成员不改区间（第 52 课「只看前三段」）；
    · 合成的前两个成员不是「趋势」关系（第 17 / 42 / 43 课：有重叠就必然扩展）；
    · 类中枢（带 `seg`）合成**不跨段**：同一合成体的成员必须同段；
    · 接进来的成员都还碰到区间；没接进来的下一个中枢确实整段离开了（或它前面已经 live、或它跨了段）；
    · 级别：合成体 = 成员级别 + 1，不随链长增加。
    """
    from .center import classify_pair
    bad, seen = [], []
    for n, b in enumerate(big):
        ms = b.get("members", [b])
        seen += [m["PI0"] for m in ms]
        if b["nmerge"] != len(ms):
            bad.append(("nmerge 与成员数不符", n))
        if len(ms) == 1:
            continue
        if len({m.get("seg") for m in ms}) > 1:
            bad.append(("合成体成员跨了线段", n))
        A, B = ms[0], ms[1]
        if classify_pair(A, B)[1] == "趋势":
            bad.append(("前两个成员是趋势关系，不该合成", n))
        conn = pens[A["PI1"] + 1:B["PI0"]]
        spans = [(A["DD"], A["GG"]), (min(p["lo"] for p in conn), max(p["hi"] for p in conn)) if conn
                 else (B["DD"], B["GG"]), (B["DD"], B["GG"])]
        if (b["ZD"], b["ZG"]) != (max(x[0] for x in spans), min(x[1] for x in spans)):
            bad.append(("区间不是前三段重算的结果", n))
        for m in ms[2:]:
            if m["DD"] > b["ZG"] or m["GG"] < b["ZD"]:
                bad.append(("接进来的成员已整段离开区间", n))
        if b["level"] != A.get("level", 1) + 1:
            bad.append(("级别不是成员级别 + 1", n))
        lo, hi = min(m["DD"] for m in ms), max(m["GG"] for m in ms)
        if conn:                                  # 波动范围把连接段也算进去（merge_extended 的第 2 段）
            lo, hi = min(lo, spans[1][0]), max(hi, spans[1][1])
        if (b["PI0"], b["PI1"]) != (A["PI0"], ms[-1]["PI1"]) or b["DD"] != lo or b["GG"] != hi:
            bad.append(("覆盖范围 / 波动范围与成员不符", n))
        nxt = next((z for z in zs if z["PI0"] > ms[-1]["PI1"]), None)
        if nxt is not None and b["valid"] and not ms[-1].get("live") \
                and nxt.get("seg") == ms[-1].get("seg") \
                and not (nxt["DD"] > b["ZG"] or nxt["GG"] < b["ZD"]):
            bad.append(("下一个中枢仍碰到区间却没接进来", n))
    if seen != [z["PI0"] for z in zs]:
        bad.append(("合成结果没有恰好覆盖全部中枢（漏了、重了或乱序）", -1))
    return bad
