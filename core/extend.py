# -*- coding: utf-8 -*-
"""把「扩展」真正算出来 —— 合成一个更大级别的中枢。

原文依据：
    第 49 课  两个次级别中枢 ＋ 连接两个次级别的段（必含一个第三类买点）
              = 三个次级别走势类型
    第 30 课  「5 分钟扩展成 30 分钟的，那第一个 5 分钟就是第一段」
              → 第一段 = 前中枢整体，第二段 = 连接段，第三段 = 后中枢整体
    第 52 课  「其实就是 A+B+C=(A+B+C)，而后者符合更大的中枢定义」
              → 把三段合起来，按中枢定义重算区间
    第 52 课  「**中枢扩展不能预先说是某级别的，因为扩展可以不断延续下去**」
              → 所以合成是**链式**的：A、B 合完之后，还要继续拿它跟 C 比；
                 if 仍然是扩展，就继续合下去。不是两两配对。

    区间 = [max(三段各自的低点), min(三段各自的高点)]     （第 20 课中枢公式）

⚠️ 已知歧义（如实标注，不假装没有）：
   「段」的范围该取中枢**区间 [ZD,ZG]** 还是**波动范围 [DD,GG]**，原文未明写。
   本实现取 [DD,GG] —— 理由：一是 classify_pair 判定「扩展」的前提本来就是
   波动范围相交，取它必然得到非空结果；二是中枢作为一个走势类型，其「最高/最低」
   本来就应该含延伸段。若改用 [ZD,ZG]，会出现大量空区间。
"""


def merge_extended(A, B, pens):
    """把相邻两个判定为「扩展」的中枢，合成一个更大级别中枢。

    A / B : 中枢 dict（需要 ZD/ZG/DD/GG/PI0/PI1/X0/X1）
    pens  : 笔列表
    返回  大中枢 dict，或 None（连接段缺失时）
    """
    conn = pens[A["PI1"] + 1: B["PI0"]]          # 连接段（被跳过的「离开笔」）
    if not conn:
        lo2, hi2 = B["DD"], B["GG"]
    else:
        lo2 = min(p["lo"] for p in conn)
        hi2 = max(p["hi"] for p in conn)
    lo1, hi1 = A["DD"], A["GG"]                  # 第一段 = 前中枢整体
    lo3, hi3 = B["DD"], B["GG"]                  # 第三段 = 后中枢整体

    ZD2 = max(lo1, lo2, lo3)
    ZG2 = min(hi1, hi2, hi3)
    return dict(
        ZD=ZD2, ZG=ZG2, valid=(ZG2 > ZD2),
        DD=min(lo1, lo2, lo3), GG=max(hi1, hi2, hi3),
        spans=[(lo1, hi1), (lo2, hi2), (lo3, hi3)],
        nconn=len(conn),
        PI0=A["PI0"], PI1=B["PI1"],              # 继续往右延伸时要接着比
        X0=A["X0"], X1=B["X1"], X2=B["X1"],
        level=A.get("level", 1) + 1,
        members=A.get("members", [A]) + [B],
        live=B.get("live", False),               # 链尾成员仍在延续 → 合成体也未完成（画虚线）
    )


def build_hierarchy(zs, pens, from_scratch=True):
    """在全体中枢上跑一遍，把连续的「扩展」链合成更大级别的中枢。

    链式：A 与 B 是扩展 → 合成 A~；再拿 A~ 与 C 比，若仍是扩展就继续合
          （第 52 课：「扩展可以不断延续下去」）。
    """
    from .center import classify_pair
    out = []
    k = 0
    while k < len(zs):
        cur = dict(zs[k]); k += 1
        n = 1
        while k < len(zs):
            _, kind = classify_pair(cur, zs[k])
            if kind != "扩展":
                break
            nxt = merge_extended(cur, zs[k], pens)
            if nxt is None:
                break
            cur = nxt
            k += 1
            n += 1
        cur.setdefault("valid", cur["ZG"] > cur["ZD"])
        cur.setdefault("nmerge", n)
        out.append(cur)
    return out
