# -*- coding: utf-8 -*-
"""中枢：连续三笔的重叠区间，以及它形成之后的三种运动。

对应《教你炒股票》：
    第 17 课   定义
    第 20 课   公式、中心定理一（延续的判据）、中心定理二（扩展/趋势的判据）
    第 22 课   三种运动：延续、扩展、新生
    第 49/52 课 扩展出来的大中枢怎么构成、区间怎么算

    中枢区间  [ZD, ZG] = [max(低₁,低₂,低₃), min(高₁,高₂,高₃)]
    波动范围  [DD, GG] = [min(dn), max(gn)]，n 遍历与中枢同向的「Z 走势段」

三种运动（第 22 课）：
    延续  后续 Z 段的 [dn, gn] 仍与 [ZD, ZG] 重叠 → 还是同一个中枢，框继续长（中心定理一）
    扩展  与另一个同级别中枢的波动范围重叠   → 合成更大级别中枢
    新生  另起一个同级别中枢，两者范围不碰   → 构成趋势

关于 Z 走势段（第 20 课）：
    构成中枢的三段里，A、C 与中枢形成方向一致，叫 Z 走势段（Z1、Z2…）。
    中枢区间 [ZD, ZG] 只用 Z1、Z2 —— 成立时定死；
    波动范围 [DD, GG] 要遍历全部 Z 段（含延伸期间新增的）—— 随延伸更新。
    因为笔的方向在标准化序列上严格交替，Z 段就是「覆盖区间里索引与第一笔
    同奇偶的笔」，即第 1、3、5… 段，不需要另行判断方向。

延续 / 终结：按**中心定理一**（第 20 课）逐个看 Z 段 ——
    「走势中枢的延伸等价於任意区间[dn，gn]与[ZD，ZG]有重叠。换言之，若有 Zn，使得 dn>ZG 或 gn<ZD，
      则必然产生高级别的走势中枢，或趋势，及中枢延续。」
    · Z 段仍与 [ZD, ZG] 重叠 → 延续，中枢终点推到这个 Z 段；
    · 出现第一个完全在区间之外的 Z 段（dn>ZG 或 gn<ZD）→ 中枢终结于**最后一个仍重叠的 Z 段**；
      两者之间那一段是连接段（第 49 课：前中枢 + 连接段 + 后中枢），下一个中枢从离开的 Z 段找起；
    · 数据走完都没出现离开的 Z 段 → 仍在延续（live）。
    旧版用「第三类买卖点」判终结，只看终点、不看出发位置，会把「先涨破 ZG、再从上方一路穿过
    整个中枢跌破 ZD」误判成三卖（BTC 4h 2026 线段中枢1 就是这样）。三类买卖点的定义不变，
    只是不再拿它判中枢终结。
"""


def _range(pens, PI0, PI1):
    """中枢的波动范围 [DD, GG]（第 20 课）。

    只统计 **Z 走势段** —— 与中枢形成方向一致的那几段（A、C、E…）。
    因为笔的方向在标准化序列上严格交替，Z 段就是「覆盖区间里索引与
    第一笔同奇偶的笔」，也就是第 1、3、5… 段，不需要另行判断方向。
    """
    Z = pens[PI0:PI1 + 1:2]
    return min(p["lo"] for p in Z), max(p["hi"] for p in Z)


def _range_all(pens, PI0, PI1):
    """旧口径：覆盖区间内全部笔的极值（保留用于对比）。"""
    seg = pens[PI0:PI1 + 1]
    return min(p["lo"] for p in seg), max(p["hi"] for p in seg)


def classify_pair(A, B):
    """按第 20 课中心定理二，判定前后两个同级别中枢的关系。

    ① 后 GG < 前 DD          → 下跌及其延续          （趋势）
    ② 后 DD > 前 GG          → 上涨及其延续          （趋势）
    ③ 后 ZG < 前 ZD 且 后 GG ≥ 前 DD → 形成高级别中枢（扩展·向下）
    ④ 后 ZD > 前 ZG 且 后 DD ≤ 前 GG → 形成高级别中枢（扩展·向上）
    """
    if B["GG"] < A["DD"]:
        return "下跌延续", "趋势"
    if B["DD"] > A["GG"]:
        return "上涨延续", "趋势"
    if B["ZG"] < A["ZD"] and B["GG"] >= A["DD"]:
        return "扩展·向下", "扩展"
    if B["ZD"] > A["ZG"] and B["DD"] <= A["GG"]:
        return "扩展·向上", "扩展"
    return "区间重叠", "同一中枢"


def find_centers(pens):
    """pens: build_pens() 输出的笔列表。

    每个中枢返回区间 [ZD, ZG]、波动范围 [DD, GG]、覆盖的笔序号，
    以及它与**前一个**中枢的关系（趋势 / 扩展 / 同一中枢）。
    """
    zs, i = [], 0
    N = len(pens)
    while i + 2 < N:
        a, b, c = pens[i], pens[i + 1], pens[i + 2]
        ZG = min(a["hi"], b["hi"], c["hi"])
        ZD = max(a["lo"], b["lo"], c["lo"])
        if ZG > ZD:                                   # 三段确有公共重叠 → 成立
            end, j, reason = i + 2, i + 3, None
            while j < N:                              # 中心定理一：逐个看 Z 段（与第一段同向）
                if (j - i) % 2 == 0:
                    u = pens[j]
                    if u["lo"] > ZG or u["hi"] < ZD:  # dn>ZG 或 gn<ZD → 离开，中枢终结
                        reason = "Z 段向上离开" if u["lo"] > ZG else "Z 段向下离开"
                        break
                    end = j                           # 仍与 [ZD, ZG] 重叠 → 延续到这个 Z 段
                j += 1
            DD, GG = _range(pens, i, end)
            DD_all, GG_all = _range_all(pens, i, end)
            z = dict(
                X0=pens[i]["i0"], X1=pens[end]["i1"],
                F1=pens[i + 2]["i1"],                 # 成立段终点 = 第三笔终点
                ZG=ZG, ZD=ZD, DD=DD, GG=GG,
                DD_all=DD_all, GG_all=GG_all,
                nZ=len(pens[i:end + 1:2]),
                live=(reason is None),
                term=(reason if reason else "仍在延续"),
                npens=end - i + 1,
                PI0=i, PI1=end,
            )
            zs.append(z)
            # 终结时：最后一个仍重叠的 Z 段（end）与离开的 Z 段（j）之间那一段是「连接段」，
            # 不属于任何中枢（第 49 课：前中枢 + 连接段 + 后中枢）；下一个中枢从离开的 Z 段找起。
            i = j if reason else end + 1
        else:
            i += 1

    # 给每个中枢补上「与前一个中枢的关系」
    for k, z in enumerate(zs):
        if k == 0:
            z["rel"], z["kind"] = "—", "—"
        else:
            z["rel"], z["kind"] = classify_pair(zs[k - 1], z)
    return zs


def check_centers(zs, units):
    """自检中枢的不变量（笔中枢、线段中枢通用）。返回违规列表（应为空）。

    zs    : find_centers() 的输出
    units : 构成中枢的那一层（笔列表，或已完成的线段列表）
    """
    bad = []
    for k, z in enumerate(zs):
        i, j = z["PI0"], z["PI1"]
        if not (0 <= i and i + 2 <= j < len(units)):
            bad.append(("覆盖不足三段或序号越界", k)); continue
        a, b, c = units[i], units[i + 1], units[i + 2]
        if (z["ZG"], z["ZD"]) != (min(a["hi"], b["hi"], c["hi"]), max(a["lo"], b["lo"], c["lo"])):
            bad.append(("区间与前三段重算不符（第 20 课公式）", k))
        if not (z["ZG"] > z["ZD"]):
            bad.append(("ZG<=ZD", k))
        if not (z["DD"] <= z["ZD"] and z["GG"] >= z["ZG"]):
            bad.append(("波动范围未包住中枢区间", k))
        if z["nZ"] != (z["npens"] + 1) // 2 or z["npens"] != j - i + 1:
            bad.append(("段数计数不符", k))
        if (j - i) % 2:
            bad.append(("终点不是 Z 段（中心定理一：终于最后一个仍重叠的 Z 段）", k))
        if any(units[q]["lo"] > z["ZG"] or units[q]["hi"] < z["ZD"] for q in range(i, j + 1, 2)):
            bad.append(("中枢内有 Z 段已离开区间", k))
        nxt = j + 2                               # 已终结的：紧随其后的那个 Z 段必须完全在区间外
        if not z["live"] and not (nxt < len(units) and
                                  (units[nxt]["lo"] > z["ZG"] or units[nxt]["hi"] < z["ZD"])):
            bad.append(("已终结，但其后的 Z 段并未离开区间", k))
        if k > 0:
            if i <= zs[k - 1]["PI1"]:
                bad.append(("与前一个中枢重叠或乱序", k))
            if (z["rel"], z["kind"]) != classify_pair(zs[k - 1], z):
                bad.append(("与前一个中枢的关系标错", k))
    return bad
