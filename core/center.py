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
    因为笔的方向在标准化序列上严格交替，Z 段就是『覆盖区间里索引与第一笔
    同奇偶的笔』，即第 1、3、5… 段，不需要另行判断方向。

终结：**第三类买卖点为主，中心定理一兜底**，按段逐个往后看，谁先出现算谁。
    ① 第三类买卖点（第 20 课定义；第 38 课「第三类买卖点，和中枢延伸的结束是一回事情」；
       第 18 / 72 课「盘整结束的标志就是第三类买卖点」）：
       某一段**从中枢区间里出发**（起点在 [ZD, ZG] 内）向上（下）离开，下一段回试（回抽）
       整段都在 ZG 之上（ZD 之下）→ 当下判定中枢终结。
       中枢终于离开段的前一段；离开段是连接段（第 49 课：前中枢 + 连接段 + 后中枢；
       第 54 课答疑：连接段「当然要和趋势本身是同向的」），不属于任何中枢；
       下一个中枢从回试那一段找起。
       『从中枢里出发』是关键：先涨破 ZG、再从上方一路穿过整个中枢跌破 ZD 的那一段，
       起点不在区间里，不是三卖（v0 的误判，BTC 4h 上见过）。
    ② 中心定理一（第 20 课）兜底：「若有 Zn，使得 dn>ZG 或 gn<ZD，则必然产生高级别的走势中枢，
       或趋势，及中枢延续」—— 出现第一个整段在区间之外的 Z 段，中枢终于**最后一个仍重叠的
       Z 段**，其间那一段是连接段，下一个中枢从离开的 Z 段找起。
       （v1 只用这一条，会把离开段算进前中枢，把前中枢的 GG / DD 撑大，连接段反向的中枢对
       永远判不成趋势。）
    · 两者都没出现 → 仍在延续（live）。

可信度 `status`（每个中枢都带「已确认」/「暂定」两档之一）：
    后到的 K 线会**改写末尾的中枢** —— 这不是缺陷，是『走势没走完』的必然结果。
    审计（`docs/audit/engine-vs-spec_中枢走势组.md` §3）把改写分了三档：
        A 档 仍在延续：边界每加一笔就往后长（X1/PI1/npens/nZ/DD/GG 都动）
        B 档 会**倒退**：终结判据要等回抽段出现，回抽段还在走时 `live=False` 会被撤销、
             边界回缩、ZG/ZD/F1 被重画
        C 档 下一层跟着动：`big` 的合并、`seg_centers` 的条数、乃至中枢**个数**
    实测（`notes/round2-tail-stability.py`，六份 data/ 砍尾）：砍掉末尾最多 233 根
    K 线时，改写最远到『末尾第 4 个』；砍到 89 根以内则**不越出末尾 1 个**。
    据此取**保守**的一刀：
        暂定   = 仍在延续，**或**它是末尾中枢，**或**它与末尾中枢相邻
        已确认 = 其余（live=False 且后面至少还有两个中枢）
    ★ 这是**按实测改写半径给的档，不是保证**：`已确认` 的中枢在已有数据下没被改写过，
    不构成『以后也不会被改写』的证明。要更强的保证得等数据把这一条钉死。
"""


def _range(pens, PI0, PI1):
    """中枢的波动范围 [DD, GG]（第 20 课）。

    只统计 **Z 走势段** —— 与中枢形成方向一致的那几段（A、C、E…）。
    因为笔的方向在标准化序列上严格交替，Z 段就是『覆盖区间里索引与
    第一笔同奇偶的笔』，也就是第 1、3、5… 段，不需要另行判断方向。
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


def upgrades(units, PI0, PI1):
    """9 段升级（第 32 / 33 课；算法见第 64 课答疑「用结合律。例如原来九段的，三个三段结合起来看」）。

    中枢从形成起共 n 段次级别走势（含形成的三段）：
      n ≥ 9  → 同时构成高一级别中枢：前 9 段按 3+3+3 结成三段，各取高低点，重叠即其区间；
      n ≥ 27 → 再高一级：前 27 段按 9+9+9 结成三段，同法；以此类推（3^(m+1) 段升 m 级）。
    本级别照样是一个中枢（第 17 课答疑「一万年在一个区间里，那还是一个中枢」），两层都保留。
    返回 [{up, ZD, ZG, groups}, ...]，up = 升几级；不够 9 段返回 []。
    """
    n, out, m = PI1 - PI0 + 1, [], 1
    while 3 ** (m + 1) <= n:
        g = 3 ** m
        groups = [(min(u["lo"] for u in units[PI0 + t * g:PI0 + (t + 1) * g]),
                   max(u["hi"] for u in units[PI0 + t * g:PI0 + (t + 1) * g])) for t in range(3)]
        out.append(dict(up=m, ZD=max(x[0] for x in groups), ZG=min(x[1] for x in groups), groups=groups))
        m += 1
    return out


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
        if ZG >= ZD:                                  # 三段确有公共重叠 → 成立（第 54 课：重叠成「一个价位」也算）
            end, j, reason, nxt = i + 2, i + 3, None, None
            while j < N:
                u = pens[j]
                if (j - i) % 2 == 0:                  # ② 中心定理一：Z 段整段在区间外 → 终结
                    if u["lo"] > ZG or u["hi"] < ZD:
                        reason = "Z 段向上离开" if u["lo"] > ZG else "Z 段向下离开"
                        nxt = j                       # 下一个中枢从离开的 Z 段找起
                        break
                    end = j                           # 仍重叠 → 延续到这个 Z 段
                if j + 1 < N and ZD <= u["p0"] <= ZG:  # ① 第三类买卖点：从区间里出发离开、回试不回来
                    w = pens[j + 1]
                    if (u["p1"] > u["p0"] and w["lo"] > ZG) or (u["p1"] < u["p0"] and w["hi"] < ZD):
                        reason = "三买" if u["p1"] > u["p0"] else "三卖"
                        end, nxt = j - 1, j + 1       # 中枢终于离开段之前；离开段 = 连接段
                        break
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
                up=upgrades(pens, i, end),            # 9 段升级：延伸满 9 段，同时是高一级别中枢
            )
            zs.append(z)
            # 终结时：end 与 nxt 之间是连接段，不属于任何中枢（第 49 课：前中枢 + 连接段 + 后中枢）
            i = nxt if reason else end + 1
        else:
            i += 1

    return classify_relations(zs)


def classify_relations(zs):
    """给中枢列表补上『与前一个中枢的关系』（趋势 / 扩展 / 同一中枢）和『可信度档』。"""
    n = len(zs)
    for k, z in enumerate(zs):
        if k == 0:
            z["rel"], z["kind"] = "—", "—"
        else:
            z["rel"], z["kind"] = classify_pair(zs[k - 1], z)
        # 暂定 / 已确认（见模块 docstring「可信度」）：末尾一个 + 相邻那个都会跟着末尾动
        if z["live"]:
            z["status"], z["status_note"] = "暂定", "仍在延续"
        elif k == n - 1:
            z["status"], z["status_note"] = "暂定", "末尾中枢（终结可能被撤销）"
        elif k == n - 2:
            z["status"], z["status_note"] = "暂定", "与末尾相邻（末尾一动它跟着动）"
        else:
            z["status"], z["status_note"] = "已确认", "—"
    return zs


def find_centers_by_segment(pens, segs):
    """类中枢改段内算：按线段把笔切开，每段内各自 find_centers —— 类中枢不跨线段。

    依据（L65:145-146 / L57:21）：类中枢用来「确认笔与线段的结束」，每一条线段就是
    次级别走势类型，跨段的重叠归线段中枢，所以类中枢不该横跨线段分界。
    每条线段（含未完成那条 live）里的笔单独跑 find_centers，得到的 PI0/PI1 是段内下标，
    加回段起点 rebase 成全局笔下标；段与段之间的分界处不接续、不合并。
    『与前一个中枢的关系』和『可信度档』最后全局重算（关系是「两个中枢之间」的，
    可信度档看的是整份数据的末尾，都不是中枢本身跨段）。
    """
    out = []
    for s in segs:
        base = s["PI0"]
        for z in find_centers(pens[base:s["PI1"] + 1]):
            z["PI0"] += base
            z["PI1"] += base
            out.append(z)
    return classify_relations(out)


def check_centers(zs, units, stops=None):
    """自检中枢（类中枢、线段中枢通用），不调用 find_centers 的逻辑，按定义逐条重验。返回违规列表（应为空）。

    zs    : find_centers() 的输出
    units : 构成中枢的那一层（笔列表，或已完成的线段列表）
    stops : 可选，段内算时的「硬分界」笔下标（每条线段末笔下标 +1）。给了它，
            终结方式的扫描只看本段内（到下一个分界为止），分界之后的走势不算
            —— 段内算里「仍在延续」是**被分界截断**，不是真的后面还有事。
    """
    bound_of = (lambda i: next((s for s in stops if s > i), len(units))) if stops else (lambda i: len(units))

    def outside(u, z):                           # 整段在区间外：+1 上方 / -1 下方 / 0 有重叠
        return 1 if u["lo"] > z["ZG"] else (-1 if u["hi"] < z["ZD"] else 0)

    def leave3(q, z):                             # 第 q 段从区间里出发离开、下一段不回来 → +1 三买 / -1 三卖 / 0
        if q + 1 >= len(units):
            return 0
        u, w = units[q], units[q + 1]
        if not (z["ZD"] <= u["p0"] <= z["ZG"]):
            return 0
        d = 1 if u["p1"] > u["p0"] else -1
        return d if outside(w, z) == d else 0

    bad = []
    n_z = len(zs)                                # ★ 别叫 n：下面 9 段升级那一支会把它覆写成段数
    for k, z in enumerate(zs):
        # 可信度档：只在带这个键的输出上重验（v1 参考实现不带）
        if "status" in z:
            want = "已确认" if (not z["live"] and k <= n_z - 3) else "暂定"
            if z["status"] != want:
                bad.append(("可信度档标错：应为 %s，实为 %s" % (want, z["status"]), k))
        i, j = z["PI0"], z["PI1"]
        if not (0 <= i and i + 2 <= j < len(units)):
            bad.append(("覆盖不足三段或序号越界", k)); continue
        a, b, c = units[i], units[i + 1], units[i + 2]
        if (z["ZG"], z["ZD"]) != (min(a["hi"], b["hi"], c["hi"]), max(a["lo"], b["lo"], c["lo"])):
            bad.append(("区间与前三段重算不符（第 20 课公式）", k))
        if not (z["ZG"] >= z["ZD"]):
            bad.append(("ZG<ZD（三段没有公共重叠）", k))
        if not (z["DD"] <= z["ZD"] and z["GG"] >= z["ZG"]):
            bad.append(("波动范围未包住中枢区间", k))
        if z["nZ"] != (z["npens"] + 1) // 2 or z["npens"] != j - i + 1:
            bad.append(("段数计数不符", k))
        if any(outside(units[q], z) for q in range(i, j + 1, 2)):
            bad.append(("中枢内有 Z 段已整段在区间外（中心定理一）", k))
        # 终结方式：从 i+3 起按段看，第一个事件必须就是标注的那个
        bound = bound_of(i)
        ev = None
        for q in range(i + 3, bound):
            if (q - i) % 2 == 0 and outside(units[q], z):
                ev = ("Z 段向上离开" if outside(units[q], z) > 0 else "Z 段向下离开", q - 2, q); break
            if q + 1 < bound:                        # 三买/三卖：离开段和回试段都得在本段内
                d = leave3(q, z)
                if d:
                    ev = ("三买" if d > 0 else "三卖", q - 1, q + 1); break
        if ev is None:
            if not z["live"]:
                bad.append(("标为已终结，但其后既无第三类买卖点也无离开的 Z 段", k))
        else:
            if z["live"] or z["term"] != ev[0]:
                bad.append(("终结方式标错：应为 %s" % ev[0], k))
            if j != ev[1]:
                bad.append(("终点不对：%s 时应终于第 %d 段" % (ev[0], ev[1]), k))
            if k + 1 < len(zs) and zs[k + 1]["PI0"] < ev[2]:
                bad.append(("下一个中枢起点早于连接段之后", k))
        # 9 段升级：另写一遍（按组号累加，不调用 upgrades）
        n, want, g = j - i + 1, [], 3
        while 3 * g <= n:
            lo = [min(units[q]["lo"] for q in range(i + t * g, i + t * g + g)) for t in range(3)]
            hi = [max(units[q]["hi"] for q in range(i + t * g, i + t * g + g)) for t in range(3)]
            want.append((len(want) + 1, max(lo), min(hi)))
            g *= 3
        if [(u["up"], u["ZD"], u["ZG"]) for u in z.get("up", [])] != want:
            bad.append(("9 段升级不符（满 9 段升一级、27 段升两级，区间按三组重叠）", k))
        if k > 0:
            if i <= zs[k - 1]["PI1"]:
                bad.append(("与前一个中枢重叠或乱序", k))
            if (z["rel"], z["kind"]) != classify_pair(zs[k - 1], z):
                bad.append(("与前一个中枢的关系标错", k))
    return bad
