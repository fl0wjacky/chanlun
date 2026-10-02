# -*- coding: utf-8 -*-
"""线段：把「笔」当成「K线」，把「分型」的方法再用一遍。

对应《教你炒股票》第 67 课（划分标准）、第 77 课（硬要求）、第 83 课（为什么要线段）。

核心（第 67 课原文）：
    向上笔开始的线段写作 S1 X1 S2 X2 S3 X3 …
    「以向上笔开始的线段，可以用笔的序列表示：S1X1S2X2S3X3…SnXn。容易证明，↵任何 Si 与 Si+1 之间，一定有重合区间。而考察序列 X1X2…Xn，该序列中，Xi 与 Xi+1 之间并不一定有重合区间，因此，这序列更能代表线段↵的性质。」
    → X1X2…Xn 叫「以向上笔开始线段的特征序列」；S1S2…Sn 反之。
    「关於特征序列，把每一元素看成是一 K 线，那么，如同一般 K 线图中找分型的方法，也存在所谓的包含关系，也可以对此进↵行非包含处理。经过非包含处理的特征序列，成为标准特征序列。」
    → 向上笔开始的线段只考察【顶分型】；向下笔开始的只考察【底分型】。

线段结束的两种情况（第 67 课）：
    第一种：分型的第一、第二元素之间【没有缺口】→ 线段在该分型的高/低点结束。
    第二种：之间【有缺口】→ 还必须「从该顶分型最高点开始的↵向下一笔开始的序列的特征序列，出现底分型」，才在该高点处结束。
            （原文补充：第二个序列中的分型不再分第一二种情况，「只要有分型就可以」。）

第 65／77 课的一条必要条件（2026-10-02 补实现）：
    · L65:50-51「线段有一个最基本的前提，就是线段的前三笔，必须有重叠的部分，这个前提在前面可能没有特别强调，这里必须特别强调一次。线段至↵少有三笔，但并不是连续的三笔就一定构成线段，这三笔必须有重叠的部分。」
    · L77:69-70「由此可见，线段中包含笔的数目，都是单数的。而且，线段开始的那三笔，必须有重合，开始三笔没有重合的，是↵构不成线段的。」
    ⇒ 起点处三笔要有**公共**重叠区间（判三笔的交集，别简化成只查相邻两笔），见 _opening_overlaps()。

第 71 课补的两条（本实现据此把 67 / 71 合并为一个算法）：
    ·「线段的划分，都是可以当下完成的……假设某转折点是两线段的分界点，然后对此用线段划分的
      两种情况去考察」→ 逐个假设分界点 V，第一个满足的就是终点。
    · 分界点前后那两个元素「是不存在包含关系的」；分界点之后的元素「是可以应用包含关系的」。
      旧 v67 在整条特征序列上做包含，会跨过分界点合并 —— 与这句不符，已停用
      （保留为 build_segments_whole_seq，仅供对照）。

对外：
    build_segments()            唯一口径（build_segments_v71 是它的别名，兼容旧调用）
    check_segments()            不变量（笔数单数、首尾相接、方向交替、开头三笔有公共重叠）
    verify_by_definition()      独立复核：逐段按原文定义重算终点，并确认它是第一个满足的分界点
    nonextreme_endpoints()      诊断：终点不是段内极值的线段（原文未要求，只报数）
"""

from .kline import fractals


def _dir(pen):
    return "up" if pen["p1"] > pen["p0"] else "down"


def _features(pens, i0, seg_dir):
    """特征序列：与线段方向相反的笔，看成 K 线。返回 [(原始笔序号, {h,l,i}), ...]"""
    out = []
    for k in range(i0, len(pens)):
        if _dir(pens[k]) != seg_dir:
            out.append((k, dict(h=pens[k]["hi"], l=pens[k]["lo"], i=k)))
    return out


def _feature_std(elems, up):
    """特征序列的非包含处理（第 67 课「标准特征序列」）。

    与 K 线的 standardize 只差开头：K 线开头互相包含时还定不出方向，只能丢掉；
    特征序列属于一条有方向的线段，开头就按**这条线段的方向**合并（向上段取高高、向下段取低低），
    之后照常按『最后两根』定方向。丢掉开头会漏掉元素（第 66 / 71 / 78 课要求这里必须合并）。
    elems: [{h, l, i}, ...]；返回同样结构，i 取合并组里最后一个元素的。
    """
    m = []
    for e in elems:
        if m and ((m[-1]["h"] >= e["h"] and m[-1]["l"] <= e["l"]) or (e["h"] >= m[-1]["h"] and e["l"] <= m[-1]["l"])):
            a = m[-1]
            go_up = up if len(m) < 2 else (a["h"] > m[-2]["h"])
            pick = max if go_up else min
            m[-1] = dict(h=pick(a["h"], e["h"]), l=pick(a["l"], e["l"]), i=e["i"], ih=e["i"], il=e["i"])
        else:
            m.append(dict(h=e["h"], l=e["l"], i=e["i"], ih=e["i"], il=e["i"]))
    return m


def _fractals_of(pens, i0, seg_dir, want):
    """在特征序列的标准形式上找分型。返回 [(hit, std, feats), ...]（按位置排序）"""
    feats = _features(pens, i0, seg_dir)
    if len(feats) < 3:
        return [], None, None
    std = _feature_std([f[1] for f in feats], seg_dir == "up")
    fx = fractals(std)
    return [f for f in fx if f["type"] == want], std, feats


def _end_pen_of(hit, std, feats):
    """分型中间元素 → 原始笔序号 → 线段端点笔（该反向笔之前的那根同向笔）"""
    return feats[std[hit["k"]]["i"]][0] - 1


def _has_gap(hit, std):
    """分型的第一、第二元素之间是否有缺口"""
    kk = hit["k"]
    if kk < 1:
        return False
    a, b = std[kk - 1], std[kk]
    return (a["l"] > b["h"]) or (a["h"] < b["l"])


def _reverse_scan(pens, end_pen, seg_dir):
    """第二种情况的确认：从端点之后的反向序列里，能不能找到分型。返回 (确认与否, 破位笔序号)。

    破位笔 = 价格重新越过端点的那一笔（None = 到数据末尾都没越过）。
    未确认时：有破位 → 第 78 课「没有形成第二特征序列的分型又直接新高或新低了……加起来只能算是
    一个线段」，原线段延续；无破位 → 当下待定。

    ★ 关键是给「该序列」加一个边界：只看**价格还没重新越过端点之前**的那一段。
      否则一路看到数据末尾，几乎总能找到一个分型，确认条件就等于没做
      （v2 实测：加不加这条，结果完全一样）。
    端点被越过后，说明价格又创了新极值，原来那个候选位置已经不成立了。
    """
    pivot = pens[end_pen]["p1"]
    rev_dir = "down" if seg_dir == "up" else "up"
    want2 = "bot" if rev_dir == "down" else "top"
    # 截取：从 end_pen+1 起，到价格重新越过 pivot 为止
    tail, brk = [], None
    for j in range(end_pen + 1, len(pens)):
        p = pens[j]
        if (seg_dir == "up" and p["hi"] > pivot) or (seg_dir != "up" and p["lo"] < pivot):
            brk = j                             # 高点被向上 / 低点被向下突破即止
            break
        tail.append(p)
    if len(tail) < 3:
        return False, brk
    hits, _, _ = _fractals_of(tail, 0, rev_dir, want2)
    return len(hits) > 0, brk


def _reverse_confirms(pens, end_pen, seg_dir):
    """只要『确认与否』（旧整序列口径在用）。"""
    return _reverse_scan(pens, end_pen, seg_dir)[0]


def build_segments_whole_seq(pens, min_pens=3):
    """【旧口径，已停用】整条特征序列先做包含处理再找分型（旧 v67）。

    问题：包含处理会跨过假设的分界点合并前后元素，违反第 71 课「在这假设的转折点前后
    那两元素，是不存在包含关系的」。只留作对照（tools/ab_segment.py）。
    """
    segs, i, n = [], 0, len(pens)
    while i + min_pens - 1 < n:
        seg_dir = _dir(pens[i])
        want = "top" if seg_dir == "up" else "bot"
        hits, std, feats = _fractals_of(pens, i + 1, seg_dir, want)
        if not hits:
            break
        chosen = None
        for hit in hits:                        # 逐个尝试，不是取第一个就收工
            ep = _end_pen_of(hit, std, feats)
            if ep <= i:
                continue
            if ep - i + 1 < min_pens:
                continue
            if not _has_gap(hit, std):          # 第一种情况：直接采用
                chosen = (hit, ep, 1); break
            if _reverse_confirms(pens, ep, seg_dir):   # 第二种情况：反向确认
                chosen = (hit, ep, 2); break
        if chosen is None:
            break
        hit, end_pen, case = chosen
        segs.append(dict(
            PI0=i, PI1=end_pen,
            i0=pens[i]["i0"], i1=pens[end_pen]["i1"],
            p0=pens[i]["p0"], p1=pens[end_pen]["p1"],
            dir=seg_dir, npens=end_pen - i + 1, case=case,
            hi=max(pens[k]["hi"] for k in range(i, end_pen + 1)),
            lo=min(pens[k]["lo"] for k in range(i, end_pen + 1)),
        ))
        i = end_pen + 1

    # 尾部剩余 ≥3 笔：还没被确认 → 未完成线段
    if n - i >= 3:
        seg_dir = _dir(pens[i])
        segs.append(dict(
            PI0=i, PI1=n - 1,
            i0=pens[i]["i0"], i1=pens[n - 1]["i1"],
            p0=pens[i]["p0"], p1=pens[n - 1]["p1"],
            dir=seg_dir, npens=n - i, case=0, live=True,
            hi=max(p["hi"] for p in pens[i:]),
            lo=min(p["lo"] for p in pens[i:]),
        ))
    return segs


def _opening_overlaps(pens, i):
    """起点处三笔是否有**公共**重叠区间。

    原文（L65:50-51／L77:69-70）：线段开始的那三笔必须有重合的部分。
    ★ 判的是**三笔的公共区间**（三笔各自的 [lo, hi] 交集非空）—— 别简化成『只查相邻两笔』。
      ★ 2026-10-02 更正（@bram-9d29 指出，复跑后确认）：本 docstring 初版写的是『不是两两重叠』，
        **那个理由是错的** —— 1 维区间上三对两两相交 ⟺ 有公共段（Helly 数＝2；
        20 万组随机区间实测『两两都相交但无公共段』0 例）。真正会漏的是**只看相邻两对**：
        相邻都相交而三笔无公共段，同一次实测 3.63%（随分布变，不当发生率用）。
        判据本身没动，改的只是「为什么不能简化」这句理由。
    ★ 边界取严格 < ：公共区间退化成一个点不算「有重叠的部分」。
    """
    p3 = pens[i:i + 3]
    if len(p3) < 3:
        return False                       # 不足三笔 ⇒ 构不成线段起点
    return max(p["lo"] for p in p3) < min(p["hi"] for p in p3)


def check_segments(segs, pens):
    """自检线段的不变量。返回违规列表。"""
    bad = []
    for k, s in enumerate(segs):
        if s["npens"] < 3:
            bad.append(("笔数 < 3", k, s["npens"]))
        if not _opening_overlaps(pens, s["PI0"]):       # L65:50-51／L77:69-70
            bad.append(("开头三笔无公共重叠", k, s["PI0"]))
        if s["npens"] % 2 == 0 and not s.get("live"):
            bad.append(("笔数不是单数", k, s["npens"]))
        if k > 0:
            if s["PI0"] != segs[k - 1]["PI1"] + 1:
                bad.append(("与上一段不相接", k))
            if s["dir"] == segs[k - 1]["dir"]:
                bad.append(("两端方向相同", k))
    return bad


def _case_at(pens, i, k, seg_dir):
    """第 71 课：假设 pens[k] 的终点 V 是分界点，按原文程序考察。

    返回 (case, at)：
      case 为 None 时，at 是下一个**允许考察**的候选笔序号的下限（None = 照常试下一个）；
      case 为 1 时，at 是『第一笔结束位置被突破』的那一笔 —— 新线段到这一笔才确立，
      它的终点不能早于此（None = 不受限）。

    ① E1 = V 之前旧线段的最后一个特征元素 —— 取旧线段特征序列（pens[i+1..k-1] 里的反向笔）
       做包含处理后的最后一根；
    ② E2 = 从 V 开始的第一笔 pens[k+1]。E1、E2 之间**不做包含处理**（原文：「是不存在包含关系的，
       因为，这两者已经被假设不是同一性质的东西」）；
    ③ E1、E2 **无缺口 = 第一种情况 = 转折点下来的第一笔就破坏了前线段**（第 71 课：最早破坏的
       一笔若不是第一笔，两者之间「肯定有缺口」，反之亦然）。此时这一笔「属於中间地带……
       即使出现似乎有特征序列的包含关系的走势，也不能算」—— 所以**不拿它做包含**，改按原文
       的两种最后结果判定：
         · 之后先破第一笔的**结束位置** →「新的线段显然成立，旧线段还是被破坏了」→ V 成立；
           新线段在破位那一笔才确立，此前方向未定，所以它的终点不得早于破位那一笔；
         · 先破第一笔的**开始位置**（即 V）→「旧线段依然延续，新线段没有出现」→ V 不成立；
         · 都还没破 → 当下待定，不确认。
       （第三笔直接破第一笔结束位置的，就是「新的线段一定形成」，同样落在第一条。）
       待定期间，走势都在第一笔的范围内 ——「这三笔就分不出是向上还是向下……定义不了什么特征
       序列」，所以其间的后续候选**不能拿来判定**：先破开始位置 → 从破位那一笔起再找；
       一直没破 → 停在待定，线段保持未完成。
    ④ E1、E2 **有缺口 = 第二种情况**：V 之后的元素（E2、pens[k+3]…）「是可以应用包含关系的」，
       合并方向与分型同向（顶取高高，底取低低），合完后的下一根是 E3；E1-E2-E3 必须构成顶（底）
       分型且 E2 的极值仍是 V，再加反向序列出现分型才确认（第 67 课）。
       反向序列没出分型之前同样是待定：先被新高 / 新低越过 V →「加起来只能算是一个线段」
       （第 78 课），从破位那一笔起再找；都没发生 → 其后候选一律不判。

    注：E1 与 E2 之间只比高点（顶）/ 低点（底），不要求四条件 —— 两者不做包含处理，
       四条件在『可能互相包含』时没有意义。
    本实现不强加『终点须为段内极值』（原文未写）；按上面规则，12 标的 15 分钟里仍有约 1%
    的线段终点不是段内极值，成因见 README 已知债务。
    """
    up = seg_dir == "up"
    feats = [f for f in _features(pens, i + 1, seg_dir) if f[0] < k]
    if not feats or k + 1 >= len(pens):
        return None, None
    E1 = _feature_std([f[1] for f in feats], up)[-1]
    V = pens[k]["p1"]
    E2 = dict(h=pens[k + 1]["hi"], l=pens[k + 1]["lo"])
    if (up and V <= E1["h"]) or (not up and V >= E1["l"]):
        return None, None                         # V 不高于（低于）前一特征元素，谈不上顶（底）
    gap = (E1["h"] < E2["l"]) if up else (E1["l"] > E2["h"])

    if not gap:                                   # ③ 第一种情况：第一笔在中间地带，看先破哪一头
        L = pens[k + 1]["p1"]                     # 第一笔的结束位置
        for r in range(k + 2, len(pens)):
            p = pens[r]
            if (up and p["hi"] > V) or (not up and p["lo"] < V):
                return None, r                    # 先破开始位置：旧线段延续，从 r 起再找
            if (up and p["lo"] < L) or (not up and p["hi"] > L):
                return 1, r                       # 先破结束位置：V 是终点，新段在 r 才确立
        return None, len(pens)                    # 都没破：待定，其后候选一律不判

    E3 = None                                     # ④ 第二种情况
    for j in range(k + 3, len(pens), 2):          # V 之后的同类元素，按分型方向做包含
        e = pens[j]
        if (E2["h"] >= e["hi"] and E2["l"] <= e["lo"]) or (e["hi"] >= E2["h"] and e["lo"] <= E2["l"]):
            E2 = dict(h=max(E2["h"], e["hi"]), l=max(E2["l"], e["lo"])) if up else \
                 dict(h=min(E2["h"], e["hi"]), l=min(E2["l"], e["lo"]))
            continue
        E3 = dict(h=e["hi"], l=e["lo"]); break
    if E3 is None:                                # 分型还没走出来：当下无法确认
        return None, None
    if up:
        if E2["h"] != V or not (E2["h"] > E3["h"] and E2["l"] > E3["l"]):
            return None, None
    else:
        if E2["l"] != V or not (E2["l"] < E3["l"] and E2["h"] < E3["h"]):
            return None, None
    ok, brk = _reverse_scan(pens, k, seg_dir)
    if ok:
        return 2, None
    return None, (brk if brk is not None else len(pens))   # 新高/新低 → 从破位处再找；否则待定


def build_segments(pens, min_pens=3):
    """把笔聚合成线段 —— 第 67 课的定义 + 第 71 课的当下程序（逐个假设分界点）。

    原文：
      「线段的划分，都是可以当下完成的，无非是如下的程序：假设某转折点是两线段的分界点，
        然后对此用线段划分的两种情况去考察是否满足……」
      「特征序列的分型中，第一元素就是以该假设转折点前线段的最后一个特征元素，第二个元素，
        就是从这转折点开始的第一笔……如果这两者之间有缺口，那么就是第二种情况，否则就是第一种，
        **然后根据定义来考察就可以**。」

    两个元素只决定「是哪种情况」，不是判据本身 —— 仍要按第 67 课的定义确认分型（见 _case_at）。
    旧『两点法』漏了最后这一步：只要 E1、E2 不重叠就收，线段被切得过碎（30 分钟 72 段）。
    """
    segs, i, n = [], 0, len(pens)
    born = 0                                  # 本段方向确立的那一笔（上一段第一种情况确认时的破位笔）
    while i + min_pens - 1 < n:
        # ★ L65:50-51／L77:69-70：线段开始的那三笔必须有重合。没有公共重叠 ⇒ i 处**构不成线段**
        #   ⇒ 往后挪一笔再看（原文：「开始三笔没有重合的，是构不成线段的」）。
        #   实测这条只在**序列开头**触发：6 族生成器 2481 段随机 + 真实 201 段，段界之后 0 例
        #   —— 段界由特征序列分型确认，本身已含重叠，所以段界之后不需要它兜。
        #   ★★ 准确的说法（@bram-9d29 提出，本仓复跑对过）是「**谓词在段界上从不为假**」，
        #      不是「谓词从来不为假」：真实 9 份数据上谓词为假共 **222 处**（窗口放得下的口径；
        #      全 i 口径 240，多出的 18 是末尾两个位置——窗口不足三笔一律 False），
        #      只是循环**问不到**那些位置（只在头部与各段界问一次）。
        #      ⇒ 差别在于「改坏了会不会被发现」：按前一种说法改坏无所谓；按后一种，
        #        改坏正好落在没人问的地方，**lockstep 也照样绿**。
        #   ⇒ 挪过去的几笔都在头部，**没有上一段可并**，它们不构成任何线段（悬空前缀）。
        #   若哪天在 i>0 触发，check_segments 会以『与上一段不相接』报出来 ——
        #   那时才需要实现『并入上一段』那一支（注意并入 1 笔会把上一段笔数的奇偶翻掉，
        #   要保奇偶就得一次并 2 笔）。现在不写，因为写了就是没有样本能打的死代码。
        if not _opening_overlaps(pens, i):
            i += 1
            continue
        seg_dir = _dir(pens[i])
        found = None
        k = i + min_pens - 1                  # 候选终点笔（至少 3 笔，步长 2 保笔数为单数）
        while k < born:                       # 方向确立之前，本段不能结束
            k += 2
        while k < n - 1:
            case, resume = _case_at(pens, i, k, seg_dir)
            if case:
                found = (k, case, resume); break
            k += 2
            if resume is not None:                # 待定区间内的候选不判：跳到破位处之后的同向笔
                while k < resume:
                    k += 2
        if found is None:
            break
        end_pen, case, born = found
        born = born or 0
        segs.append(dict(
            PI0=i, PI1=end_pen,
            i0=pens[i]["i0"], i1=pens[end_pen]["i1"],
            p0=pens[i]["p0"], p1=pens[end_pen]["p1"],
            dir=seg_dir, npens=end_pen - i + 1, case=case,
            hi=max(pens[k]["hi"] for k in range(i, end_pen + 1)),
            lo=min(pens[k]["lo"] for k in range(i, end_pen + 1)),
        ))
        i = end_pen + 1

    if n - i >= 3:
        seg_dir = _dir(pens[i])
        segs.append(dict(
            PI0=i, PI1=n - 1,
            i0=pens[i]["i0"], i1=pens[n - 1]["i1"],
            p0=pens[i]["p0"], p1=pens[n - 1]["p1"],
            dir=seg_dir, npens=n - i, case=0, live=True,
            hi=max(p["hi"] for p in pens[i:]),
            lo=min(p["lo"] for p in pens[i:]),
        ))
    # ★ 尾部这里**不用**再查开头三笔：走到这一行只有两条路 ——
    #   ① 上面 break（found is None），此时 i 已过开头重叠的关；
    #   ② 循环条件退出，此时 n-i < min_pens，上面那个 if 本来就不成立。
    return segs


build_segments_v71 = build_segments          # 兼容旧调用：67 / 71 已合并为一个口径


def nonextreme_endpoints(segs):
    """诊断：终点不是段内极值的已完成线段（向上段终点 < 段内最高，或向下段终点 > 段内最低）。

    原文没有要求终点必须是极值，所以这里只报数、不算违规。
    """
    return [s for s in segs if not s.get("live") and
            ((s["dir"] == "up" and s["p1"] < s["hi"]) or (s["dir"] == "down" and s["p1"] > s["lo"]))]


def verify_by_definition(segs, pens):
    """独立复核：不调用 _case_at / _reverse_scan，按原文定义另写一遍，逐段重算。返回违规列表。

    对每条已完成线段 [PI0, PI1]，检查：
      ① 终点 V 处确实成立（第 67 课两种情况 + 第 71 课分界点包含规则与『第一笔中间地带』规则
         + 第 78 课第二种情况「直接新高或新低」则并为一段）；
      ② 段内更早、且不在待定区间里的候选都**不**成立（终点是第一个满足的）；
      ③ 终点不落在更早候选的待定区间里（第一种情况：先破第一笔哪一头之前；第二种情况：
         第二特征序列出分型或被新高新低越过之前）；
      ④ 上一段以第一种情况结束时，本段终点不早于『本段第一笔结束位置被突破』那一笔。
    与引擎共用的只有 fractals（K 线层已由 selfcheck 单独验证）；特征序列的非包含处理在这里另写一遍。
    """
    N = len(pens)

    def std_feats(xs, up):
        """非包含处理，另一种写法：先按线段方向把开头互相包含的并掉，再逐个按前两根定方向。"""
        out = []
        for x in xs:
            h, l = x["h"], x["l"]
            if out:
                ph, pl = out[-1]
                if (ph - h) * (pl - l) <= 0:          # 一方罩住另一方（含相等）
                    rising = up if len(out) == 1 else out[-1][0] > out[-2][0]
                    out[-1] = (max(ph, h), max(pl, l)) if rising else (min(ph, h), min(pl, l))
                    continue
            out.append((h, l))
        return [dict(h=h, l=l, ih=0, il=0) for h, l in out]

    def judge(i, k, up):
        """候选 k 的判决：("yes", None) / ("no", None) / ("wait", r) —— r 为待定区间终止处。"""
        if k + 1 >= N:
            return "no", None
        pre = [dict(h=pens[j]["hi"], l=pens[j]["lo"]) for j in range(i + 1, k, 2)]
        if not pre:
            return "no", None
        e1 = std_feats(pre, up)[-1]
        v, first = pens[k]["p1"], pens[k + 1]
        beyond_v = (lambda p: p["hi"] > v) if up else (lambda p: p["lo"] < v)
        if (up and not v > e1["h"]) or (not up and not v < e1["l"]):
            return "no", None
        no_gap = first["lo"] <= e1["h"] if up else first["hi"] >= e1["l"]
        if no_gap:                                # 第一种情况：第一笔在中间地带
            end = first["p1"]
            for r in range(k + 2, N):
                if beyond_v(pens[r]):
                    return "wait", r
                if (pens[r]["lo"] < end) if up else (pens[r]["hi"] > end):
                    return "yes", None
            return "wait", N
        # 第二种情况：V 之后的同类元素可以包含，找 E3
        mid, right, j = [first["hi"], first["lo"]], None, k + 3
        while j < N:
            h, l = pens[j]["hi"], pens[j]["lo"]
            if (mid[0] >= h and mid[1] <= l) or (h >= mid[0] and l <= mid[1]):
                pick = max if up else min
                mid = [pick(mid[0], h), pick(mid[1], l)]
                j += 2
                continue
            right = (h, l); break
        if right is None:
            return "no", None
        ok = (mid[0] == v and mid[0] > right[0] and mid[1] > right[1]) if up else \
             (mid[1] == v and mid[1] < right[1] and mid[0] < right[0])
        if not ok:
            return "no", None
        # 第二特征序列：从 V 起到价格重新越过 V 之前，反向线段的特征序列要出现分型
        tail, brk = [], N
        for r in range(k + 1, N):
            if beyond_v(pens[r]):
                brk = r; break
            tail.append(pens[r])
        feat = [dict(h=p["hi"], l=p["lo"]) for p in tail if (p["p1"] > p["p0"]) == up]
        want = "bot" if up else "top"
        if len(tail) >= 3 and len(feat) >= 3 and any(f["type"] == want for f in fractals(std_feats(feat, not up))):
            return "yes", None
        return "wait", brk

    bad = []
    for n, s in enumerate(segs):
        if s.get("live"):
            continue
        i, k, up = s["PI0"], s["PI1"], s["dir"] == "up"
        if judge(i, k, up)[0] != "yes":
            bad.append(("终点处不满足定义", n, k))
        skip = 0                                  # 方向确立前 / 待定区间：其间候选不判
        if n > 0 and segs[n - 1].get("case") == 1:
            end1 = pens[i]["p1"]                  # 本段第一笔的结束位置
            r = next((j for j in range(i + 1, N)
                      if ((pens[j]["hi"] > end1) if up else (pens[j]["lo"] < end1))), N)
            if k < r:
                bad.append(("本段在方向确立前就结束", n, r))
            skip = r
        for k2 in range(i + 2, k, 2):
            if k2 < skip:
                continue
            verdict, r = judge(i, k2, up)
            if verdict == "yes":
                bad.append(("更早的分界点已满足", n, k2)); break
            if verdict == "wait":
                if r > k:
                    bad.append(("终点落在更早候选的待定区间内", n, k2)); break
                skip = r
    return bad
