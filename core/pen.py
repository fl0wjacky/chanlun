# -*- coding: utf-8 -*-
"""笔：把标准化序列切成一节一节。

对应第 77 课（划笔三步骤、唯一性证明）、第 81 课正文（**新笔的定义**），以及第 66 / 70 / 71 课答疑的同一句话：
    「顶和底，当然一定是那一笔的最高最低，如果不是，那里面一定不只一笔。」

新笔的定义**就在第 81 课正文里**（`archive/chanlun108/text/lesson-081.txt:106-111`）。
    ⚠️ **这段引文直接 grep 会 0 命中 —— 不是笔误，是语料噪声**：108 课里 105 课带
    『相邻同字重复一次』的噪声，第 81 课这 6 行几乎每个词都有；另有两处增字。噪声**来自源页**，
    不是我们抓取的锅（`archive/chanlun108/raw/lesson-081.html` 里就写着「笔的的成立条件」，
    而干净的『笔的成立条件』在 raw 里搜不到 —— 抓取只去了标签）。
    原文首行逐字：「本 ID 想想了想，计算了一下下能量力度，觉得得以后可以把笔的的成立条件略微放放松一下」。
    其余噪声：107 行「顶分型型」，109 行「顶足顶分型」「不包括低括这两 K 线」，以及「分别属於」（原文用「於」）。
    下面是**折叠叠字、去掉那两处增字、於→于**之后的可读版 —— **意思忠实，但不是逐字原文**：
    「本 ID 想了想，计算了一下能量力度，觉得以后可以把笔的成立条件略微放松一下，就是一笔必须满足以下两个条件：
      1、顶分型与底分型经过包含处理后，不允许共用 K 线，也就是不能有一 K 线分别属于顶分型与底分型，
         这条条件和原来是一样的，这一点绝对不能放松，因为这样，才能保证足够的能量力度；
      2、在满足 1 的前提下，顶分型中最高 K 线和底分型的最低 K 线之间(不包括这两 K 线)，
         不考虑包含关系，至少有 3 根(包括 3 根)以上 K 线。」
    下面 "new" 那两条就是这两条的代码化。第 81 课同一篇的答疑（2007-09-19）里说
    「**请去昨天晚上帖子里看**」「最新给了一个新的笔的定义」，那份"昨天晚上的帖子"**就是这个文件里的正文**；
    ⚠️ 正文本身**没有日期戳**，所以别用日期串去找它（本文件早先一版正是这么找的，于是得出了
    "新笔的定义不在 108 课里"这个**错误**结论 —— 一份没有日期戳的帖子不会让日期串计数命中）。
    rule="old" 同样有原文支持：缠师在同一条答疑里说「**本 ID 自己一直用老标准**」；
    "new" 的用途也是他原话：「那主要是为了**不同软件间可以减少不同**」。

两种成笔标准（rule）：
    "old"  老笔（第 77 课，缠师自己一直用的）：顶、底分型之间至少有一根不属于两个分型的K线
           → 在标准化序列上 k 相差 ≥ 4（min_gap）。
    "new"  新笔（第 81 课正文，理由是不同软件结果少打架；定义原文见上）：
           ① 包含处理后顶、底分型不共用K线 → k 相差 ≥ 3；
           ② 顶分型最高那根与底分型最低那根**原始**K线之间（不含这两根）至少 3 根 → i 相差 ≥ 4。
    「隔够」之外，每一笔还要满足：**两个端点就是这一笔（标准化序列上）的最高点和最低点**。

划法（第 77 课步骤 + 唯一性证明里的取舍）：
    · 同类分型接连出现：更极端的替换前一个（步骤二）；
    · 反类分型：隔够、且它是从上一端点到它为止的极值 → 成笔；
      隔够但不是极值（中间夹着一个挨得太近、却更极端的反类分型）→ 这一笔还没完成，不收；
    · 挨得太近、却比前前个端点更极端的反类分型，记为「待定」。之后若上一端点被同类更极端的分型
      替换，上一笔就包不住它了 → 回头修正：作废上一笔，把前一端点换成这个待定分型（唯一性证明里
      说的是**底那一侧**，原文：「一个底不经过一个顶后就有一个更低的底，这是最典型的笔没完成的情况」
      （第 77 课）；顶那一侧是它的镜像 —— 原话里**没有**『一个顶不经过一个底』这句，别加引号当引文用）；
    · 替换后仍有端点不是极值 → 再往回找更早的同类端点，找到能同时包住两头的就合成一笔。
极少数剧烈的扩张震荡（顶一个比一个高、底一个比一个低，又挨得太近）两道修正都救不回来，
nonextreme_pens() 会把它们报出来（v2 实测：5 组数据合计个位数）。
"""


def build_pens(fx, std, rule="old", min_gap=4):
    """fx: fractals() 的输出；std: standardize() 的输出。返回 (笔列表, 笔端点序列)。"""
    if rule not in ("old", "new"):
        raise ValueError("rule 只能是 'old'（老笔）或 'new'（新笔）")

    def far(a, b):
        if rule == "old":
            return b["k"] - a["k"] >= min_gap
        return b["k"] - a["k"] >= 3 and abs(b["i"] - a["i"]) >= 4

    def beyond(f, g):                        # 同类分型：f 比 g 更极端
        return f["price"] > g["price"] if f["type"] == "top" else f["price"] < g["price"]

    # 区间最高 / 最低：线段树，单次 O(log n)。原来是每次切片现扫 max/min —— fix_start 往回找端点时
    # 每一步都扫 [e.k, g.k]，修不成的时候一路扫到头 ⇒ 整体平方级（ZEC 15m：2 万根 0.25s、4 万根 1.2s）。
    # 判据一字不改：仍是「f 的价 ≥ 区间最高 h」/「≤ 区间最低 l」，只是区间最值换了算法。
    n_std = len(std)
    size = 1
    while size < max(n_std, 1):
        size *= 2
    tmax = [float("-inf")] * (2 * size)
    tmin = [float("inf")] * (2 * size)
    for i, x in enumerate(std):
        tmax[size + i], tmin[size + i] = x["h"], x["l"]
    for i in range(size - 1, 0, -1):
        tmax[i] = max(tmax[2 * i], tmax[2 * i + 1])
        tmin[i] = min(tmin[2 * i], tmin[2 * i + 1])

    def span_ext(k0, k1, top):
        """std[k0:k1+1] 的最高 h（top）/ 最低 l。切片语义照旧：k1 越界就截到末尾，空区间照旧报 ValueError。"""
        k1 = min(k1, n_std - 1)
        if k0 < 0 or k0 > k1:
            raise ValueError("区间为空：[%d, %d]" % (k0, k1))
        t, best = (tmax, float("-inf")) if top else (tmin, float("inf"))
        pick = max if top else min
        lo, hi = k0 + size, k1 + size + 1
        while lo < hi:
            if lo & 1:
                best = pick(best, t[lo])
                lo += 1
            if hi & 1:
                hi -= 1
                best = pick(best, t[hi])
            lo >>= 1
            hi >>= 1
        return best

    def extreme(f, k0, k1):                  # f 是不是标准化序列 [k0, k1] 上的最高（顶）/ 最低（底）
        return f["price"] >= span_ext(k0, k1, True) if f["type"] == "top" \
            else f["price"] <= span_ext(k0, k1, False)

    seq, pend = [], None
    fx_by_k = [None] * len(std)
    for f in fx:
        fx_by_k[f["k"]] = f

    def pen_ok(a, b):
        return far(a, b) and extreme(a, a["k"], b["k"]) and extreme(b, a["k"], b["k"])

    def fix_start():
        """最后一笔 a→g 的起点若不是极值（笔内有个更极端的同类点 P），往回修，两种修法取保留端点多的：
        · 让 P 自己当端点：找更早的、与 g 同类的端点 e，使 e→P、P→g 都成笔；
        · 合并：找更早的、与 a 同类的端点 e，使 e→g 一笔两头都包得住。"""
        if len(seq) < 2:
            return
        a, g = seq[-2], seq[-1]
        if extreme(a, a["k"], g["k"]):
            return
        inner = [f for f in fx_by_k[a["k"] + 1:g["k"]] if f and f["type"] == a["type"]]
        P = (max if a["type"] == "top" else min)(inner, key=lambda f: f["price"]) if inner else None
        nonlocal pend
        for j in range(len(seq) - 3, -1, -1):
            e = seq[j]
            if P is not None and e["type"] == g["type"] and e["k"] < P["k"] and pen_ok(e, P) and pen_ok(P, g):
                seq[:] = seq[:j + 1] + [P]         # P 当端点，其后的分型对着它重新看一遍（g 也在其中）
                pend = None
                for x in fx_by_k[P["k"] + 1:g["k"] + 1]:
                    if x:
                        feed(x)
                return
            if e["type"] == a["type"] and j <= len(seq) - 4 and pen_ok(e, g):
                seq[:] = seq[:j + 1] + [g]
                return

    def feed(f):
        nonlocal pend
        if not seq:
            seq.append(f)
            return
        last = seq[-1]
        if f["type"] == last["type"]:        # 步骤二：同类取更极端的
            if not beyond(f, last):
                return
            if pend is not None and (len(seq) < 3 or not beyond(last, seq[-3])):
                P, pend = pend, None         # 上一笔包不住待定分型 → 作废上一笔
                seq.pop()
                seq[-1] = P
                fix_start()
                for x in fx_by_k[P["k"] + 1:f["k"] + 1]:   # 端点换了，其后的分型要对着新端点重新看一遍
                    if x:
                        feed(x)
                return
            seq[-1] = f
            pend = None
            fix_start()
            return
        if far(last, f) and extreme(f, last["k"], f["k"]):
            seq.append(f)
            pend = None
            return
        if not far(last, f) and len(seq) >= 2 and beyond(f, seq[-2]) and (pend is None or beyond(f, pend)):
            pend = f

    for f in fx:
        feed(f)
    return _pens_of(seq), seq


def _pens_of(seq):
    return [dict(
        i0=a["i"], i1=b["i"],                # 原始K线下标（画图用）
        x0=a["k"], x1=b["k"],                # 标准化序列下标（逻辑用）
        p0=a["price"], p1=b["price"],
        hi=max(a["price"], b["price"]),
        lo=min(a["price"], b["price"]),
    ) for a, b in zip(seq, seq[1:])]


def build_pens_v1(fx, min_gap=4):
    """【v1 口径，已停用】一遍扫过去、从不回头：同类取更极端，反类隔够就收。

    问题：隔得不够而被跳过的更极端分型，会被夹在后面那一笔的中间 —— 约 20–30% 的笔端点不是
    这一笔的极值（违反第 66 / 70 / 71 课答疑）。只留作对照。
    """
    seq = []
    for f in fx:
        if not seq:
            seq.append(f)
            continue
        last = seq[-1]
        if f["type"] == last["type"]:
            if (f["type"] == "top" and f["price"] > last["price"]) or \
               (f["type"] == "bot" and f["price"] < last["price"]):
                seq[-1] = f
        elif f["k"] - last["k"] >= min_gap:
            seq.append(f)
    return _pens_of(seq), seq


def nonextreme_pens(pens, std):
    """诊断：端点不是这一笔最高 / 最低的笔（标准化序列上量）。返回 [(笔序号, "起点"/"终点"), ...]。"""
    out = []
    for n, p in enumerate(pens):
        span = std[p["x0"]:p["x1"] + 1]
        hi, lo = max(x["h"] for x in span), min(x["l"] for x in span)
        up = p["p1"] > p["p0"]
        if (p["p0"] > lo) if up else (p["p0"] < hi):
            out.append((n, "起点"))
        if (p["p1"] < hi) if up else (p["p1"] > lo):
            out.append((n, "终点"))
    return out


def check_pens(pens, seq, std, rule="old", min_gap=4):
    """自检笔的不变量（不看极值，极值见 nonextreme_pens）。返回违规列表（应为空）。"""
    bad = []
    for n in range(len(seq) - 1):
        a, b = seq[n], seq[n + 1]
        if a["type"] == b["type"]:
            bad.append(("端点类型未交替", n))
        gap_ok = (b["k"] - a["k"] >= min_gap) if rule == "old" else \
                 (b["k"] - a["k"] >= 3 and abs(b["i"] - a["i"]) >= 4)
        if not gap_ok:
            bad.append(("两端点隔得不够（%s笔标准）" % ("老" if rule == "old" else "新"), n))
        top, bot = (a, b) if a["type"] == "top" else (b, a)
        if not std[top["k"]]["h"] > std[bot["k"]]["h"]:
            bad.append(("顶分型最高K线没有一部分高于底分型最低K线（第 77 课）", n))
        if n > 0 and pens[n]["i0"] != pens[n - 1]["i1"]:
            bad.append(("与上一笔不相接", n))
    return bad


def unsplit_violations(pens, fx, std, rule="old", min_gap=4):
    """独立复核（不调用 build_pens 的任何内部函数）：笔内不能再切出合法的三笔。

    第 77 课唯一性证明：两个候选端点之间不能再夹一个顶 —— 原文「在这两个底之间不可能还存在一个顶，↵否则这里就不是一笔了」。
    对每一笔 A→B，找笔内的一对分型 C（与 B 同类）、D（与 A 同类），若 A→C、C→D、D→B 三笔
    都隔得够、两头都是各自的极值（价格相等时终点须是第一次到达 —— 第 77 课「连续的底中最先一个」），
    说明这一笔被合并过头。返回 [(笔序号, C.k, D.k), ...]。
    """
    def ok(a, b):
        if a["type"] == b["type"]:
            return False
        if rule == "old":
            if b["k"] - a["k"] < min_gap:
                return False
        elif b["k"] - a["k"] < 3 or abs(b["i"] - a["i"]) < 4:
            return False
        span = std[a["k"]:b["k"] + 1]
        hi, lo = max(x["h"] for x in span), min(x["l"] for x in span)
        top, bot = (a, b) if a["type"] == "top" else (b, a)
        if not (top["price"] >= hi and bot["price"] <= lo):
            return False
        before = std[a["k"]:b["k"]]             # 终点要是笔内**第一次**到这个极值（第 77 课：相等的取最先一个）
        return all(x["h"] < b["price"] for x in before) if b["type"] == "top" else \
            all(x["l"] > b["price"] for x in before)

    by_k = {f["k"]: f for f in fx}
    bad = []
    for n, p in enumerate(pens):
        A, B = by_k.get(p["x0"]), by_k.get(p["x1"])
        if A is None or B is None:
            bad.append((n, None, None))
            continue
        inner = [f for f in fx if p["x0"] < f["k"] < p["x1"]]
        Cs = [c for c in inner if c["type"] == B["type"] and ok(A, c)]
        hit = next(((c["k"], d["k"]) for c in Cs for d in inner
                    if d["k"] > c["k"] and d["type"] == A["type"] and ok(c, d) and ok(d, B)), None)
        if hit:
            bad.append((n,) + hit)
    return bad
