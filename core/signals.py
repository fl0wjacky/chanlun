# -*- coding: utf-8 -*-
"""三类买卖点（第 20 / 21 / 24 课），按某一层中枢判：线段中枢（默认，正规）或类中枢（笔构成，对照）。

    第一类（一买 / 一卖）—— 趋势背驰（第 21 / 24 课）：
        下跌趋势 = 相邻中枢「下跌延续」（第 20 课中心定理二①）。设最后一个中枢为 B：
        A 段 = 进入 B 之前最后一段向下走势，C 段 = 离开 B、创出 B 的波动范围新低（< DD）的那一段。
        C 段力度 < A 段力度 × 比例 → 背驰，一买在 C 段的终点。
        力度：MACD 柱面积（第 24 课「向下看绿柱子」，默认）或价格斜率（|Δ价| / K 线根数）。
        前提③（第 53 课）：B 的中枢级别要比 A、C 里的都大，否则 A、B、C 会连成一个更大的中枢 ——
        用上一层中枢是否把 A、B、C **整段**包住来判（check_premise3），**默认开**（2026-10-02 小栋拍板）。
        确认：背驰后回拉进最后一个中枢（高点 ≥ ZD），第 18 / 72 课「趋势结束的标志就是形成该级别的背驰后
        对最后一个中枢的回拉」；回拉之前先跌破 C 段低点 → 背驰失败，不算。一卖镜像。
    第二类（二买 / 二卖）—— 第 21 课「第一买点出现后的第二段次级别走势低点就构成第二类买点」：
        确认的一买之后，反弹段之后的那一段回调的终点。跌破一买低点也算，标为「弱」（第 54 / 101 课）。
    第三类（三买 / 三卖）—— 第 20 课定义，与引擎的中枢终结同一口径（center.find_centers）：
        离开段从中枢区间里出发，回试段整段在 ZG 之上（ZD 之下）；三买在回试段的终点。

    确认 vs 待确认：点所在的那一段已经走完（后面又出了一段）才算确认；还在走的记为待确认
    （confirmed=False），之后可能被改掉或消失。线段层只用已完成线段算中枢，所以待确认只来自最后那条未完成线段。

返回 [dict(kind="一买"…, bar=原始K线下标, price, confirmed, weak, level, center=中枢序号), ...]，按 bar 排序。
"""
from .center import find_centers
from .extend import build_hierarchy


def macd_lines(bars, fast=12, slow=26, sig=9):
    """MACD 的两条线：返回 (DIF, DEA)。DIF = 快慢 EMA 之差（白线），DEA = DIF 的 EMA（黄线）。

    EMA 用第一根收盘价起算（Pine 版照此手写，不用 ta.ema 的 SMA 起算，两边逐根一致）。
    macd_hist 就是从这两条线相减得来的 —— 拆出来是为了『B 段回抽 0 轴』那条需要**分别**看两条线。
    """
    dif, dea = [], []
    ef = es = None
    d = 0.0
    for n, b in enumerate(bars):
        c = b["c"]
        if n == 0:
            ef = es = c
            d = 0.0
        else:
            ef += (c - ef) * 2 / (fast + 1)
            es += (c - es) * 2 / (slow + 1)
            d += (ef - es - d) * 2 / (sig + 1)
        dif.append(ef - es)
        dea.append(d)
    return dif, dea


def macd_hist(bars, fast=12, slow=26, sig=9):
    """MACD 柱 = DIF − DEA（与 TradingView 内置 MACD 的 histogram 同义；不乘 2，面积比不受影响）。"""
    dif, dea = macd_lines(bars, fast, slow, sig)
    return [x - y for x, y in zip(dif, dea)]


# ---- 『B 段回抽 0 轴附近』这条必要条件：口径 ----
# ★ 原文只给了「附近」两个字，**下面四个量全是我们发明的**，一律不许挂课号（见 README「0 轴回抽」）。
ZA_STAT = "mean|DIF| 与 mean|DEA|（B 中枢窗口内，两条线到 0 的平均距离）"
ZA_WINDOW = "B 中枢的 K 线跨度：起 = 构成它的第一段的起点 i0，止 = 最后一段的终点 i1"
ZA_REF = "该点的 A 段内 max|DIF|（除价格尺度，才可跨品种 / 级别比）"
ZA_THRESHOLD = 0.30


def zero_axis(points, r, level="seg", fast=12, slow=26, sig=9, threshold=ZA_THRESHOLD):
    """量『B 段把 MACD 黄白线回抽 0 轴附近』这条必要条件。**只量，不改买卖点判定。**

    原文（两条都是**答疑**里的话，不是正文）：
      第 25 课答疑「用 MACD 判断背驰首先要有黄白线对 0 轴的回拉，这个都没有，
                     在该级别就不存在什么背驰」
      第 27 课答疑「如果 B 段不是回抽 0 轴附近，就根本不满足条件」
    第 24 课正文说的是「B 这个中枢**一般会**把 MACD 的黄白线…回拉到 0 轴附近」—— 那是弱说法。
    （**这条引文折叠了 OCR 叠字** —— 源页逐字是「B 这个中枢枢一般会把…回拉到 0 轴轴附近」，照抄去 grep 会不中；
    块里的 `**` 是后加的着重、`…` 省掉了原文的括注 `(也就是 DIFF 和 DEA)`。标注口径同 README『引号口径』那条。）
    强说法出自上面两条答疑。

    **口径（阈值的数是我们发明的）**：见 ZA_STAT / ZA_WINDOW / ZA_REF / ZA_THRESHOLD。
    为什么不用 `min|DIF|`（"两条线最近贴到过 0 多近"）：DIF 在反转处必然穿 0 ⇒ 它**几乎恒为 0、
    没有分辨力**（实测 7 个一买一卖里 4 个 < 0.005，其余最大 0.249）⇒ 分母再大也分不出来。
    mean 在同样这 7 个上的读数是 0.205 ~ 0.610，分得开。

    返回一买 / 一卖逐条读数：dict(kind, bar, center, win, r_dif, r_dea, r, ok)。
    r = max(r_dif, r_dea) —— 两条线**都要**回抽，所以取差的那个；r ≤ threshold 记 ok。
    """
    dif, dea = macd_lines(r["bars"], fast, slow, sig)
    AU, Z = _units(r, level)[0], _units(r, level)[2]
    out = []
    for s in points:
        if s["kind"] not in ("一买", "一卖"):
            continue
        B = Z[s["center"] - 1]
        if B["PI1"] >= len(AU) or B["PI0"] < 0:
            continue
        lo, hi = AU[B["PI0"]]["i0"], AU[B["PI1"]]["i1"]
        if hi <= lo:
            continue
        a = next((q for q in range(B["PI0"] - 1, -1, -1)
                  if (AU[q]["p1"] < AU[q]["p0"]) == s["kind"].endswith("买")), None)
        if a is None:
            continue
        ref = max(abs(x) for x in dif[AU[a]["i0"]:AU[a]["i1"] + 1])
        if ref <= 0:
            continue
        w = hi - lo + 1
        r_dif = sum(abs(x) for x in dif[lo:hi + 1]) / w / ref
        r_dea = sum(abs(x) for x in dea[lo:hi + 1]) / w / ref
        rr = max(r_dif, r_dea)
        out.append(dict(kind=s["kind"], bar=s["bar"], center=s["center"], win=hi - lo,
                        r_dif=r_dif, r_dea=r_dea, r=rr, ok=rr <= threshold))
    return out


def _units(r, level):
    """(全部单位含未完成的, 构成中枢的单位, 中枢)。单位统一带 i0/i1/p0/p1/hi/lo。"""
    if level == "seg":
        segs = r["segs"]
        done = [s for s in segs if not s.get("live")]
        return segs, done, r["seg_centers"]
    return r["pens"], r["pens"], r["centers"]


def wolf_below(bars, fast=12, slow=26, sig=9):
    """防狼术（均线.md 六.7，第七章 T13，Nova 10-08 定：独立开关、默认关、**不是判据**）：MACD 黄白线在 0 轴下的区间。
    → [(i0, i1)]：从 i0 那根起「在下面」，到 i1 那根「站住」为止（i1 不含；还没站住 ⇒ i1 = None）。

    『编者口径』（Nova 09:02／09:03）：DIF、DEA **两条都 < 0** 才进入『在下面』；**两条都 > 0** 才算『站住』；
    一上一下、或正好等于 0 ⇒ **维持原状态**（带滞后，防来回跳）。开头还没有过一次两条同号 ⇒ 状态未定，不算在下面。
    只给前端画一层提示；**不进任何结构判定、买卖点、背驰**（那些都不 import 这个函数）。"""
    dif, dea = macd_lines(bars, fast, slow, sig)
    out, below, i0 = [], False, None
    for i, (a, b) in enumerate(zip(dif, dea)):
        if not below and a < 0 and b < 0:
            below, i0 = True, i
        elif below and a > 0 and b > 0:
            below = False
            out.append((i0, i))
    if below:
        out.append((i0, None))
    return out


# 力度比较的四种看法（单选；docs/spec/背驰.md 第六节，Nova 2026-10-04 定）：
#   macd  柱子面积（默认）· slope 斜率 · lines 黄白线不创新高低 · peak 柱子一波峰值
#   macd_or_lines  面积**或**黄白线，一条成立就算（spec 六.3，小栋 10-04 ②A）；两条都成立的点打 std=True
MEASURES = ("macd", "slope", "lines", "peak", "macd_or_lines")
OR_PARTS = ("macd", "lines")                 # macd_or_lines 由哪两半组成；两半各自原样走单选的判法
# 哪几种是 108 课原文给的判法（小栋 10-04 ①A）：斜率（价差÷根数）是早期自己加的，原文没有，留着但要标明。
MEASURE_ORIG = {"macd": True, "slope": False, "lines": True, "peak": True, "macd_or_lines": True}
# 量是原文的、但单独拿来用超出了原文的那几种（背驰.md 六.3 末段，第七章 T16，Nova 10-08 定「不改类型、另挂说明」）。
#   跟斜率的「非原文」分开：斜率是**量本身**不是原文的（MEASURE_ORIG False）；峰值的量是原文的（L15:177-178），只是单用超出原文。
MEASURE_NOTE = {"peak": "单用超出原文：峰值这个量是原文的（第 15 课），但原文只在 1 分钟急促上升时允许单看柱子，其他情况要配合黄白线"}


def series_for(bars, measure, fast=12, slow=26, sig=9):
    """力度那一步要读的序列：lines 读 (DIF, DEA) 两条线，其余读 MACD 柱（slope 不读，照旧给柱）。
    macd_or_lines 两样都要：给 {"macd": 柱, "lines": (DIF, DEA)}。"""
    if measure not in MEASURES:
        raise ValueError("measure 只认 %s，给的是 %r" % ("/".join(MEASURES), measure))
    if measure == "macd_or_lines":
        return {m: series_for(bars, m, fast, slow, sig) for m in OR_PARTS}
    return macd_lines(bars, fast, slow, sig) if measure == "lines" else macd_hist(bars, fast, slow, sig)


def strength(u, hist, measure="macd"):
    """一段走势的力度：MACD 柱面积（只算与该段同向的柱子）、斜率，或柱子峰值。

    peak：段内与该段同向的柱子里绝对值最大的那根（＝段内最高的山顶；不管「一波」怎么切都一样，
    见 spec 背驰.md 六.2(b)）。段内一根同向柱子都没有 ⇒ 0。
    lines 不是一个数，不走这里（见 lines_extreme / _diverges）。"""
    up = u["p1"] > u["p0"]
    if measure == "slope":
        return abs(u["p1"] - u["p0"]) / max(1, u["i1"] - u["i0"])
    seg = hist[u["i0"]:u["i1"] + 1]
    if measure == "peak":
        return max([h for h in seg if h > 0], default=0) if up else -min([h for h in seg if h < 0], default=0)
    return sum(h for h in seg if h > 0) if up else -sum(h for h in seg if h < 0)


def lines_extreme(u, lines):
    """一段里两条线各自的极值：向下段取 (min DIF, min DEA)，向上段取 (max DIF, max DEA)。
    窗口就是该段自己的 [i0, i1]，不往后延（spec 背驰.md 六.1(a)）。"""
    dif, dea = lines
    pick = max if u["p1"] > u["p0"] else min
    return pick(dif[u["i0"]:u["i1"] + 1]), pick(dea[u["i0"]:u["i1"] + 1])


def _diverges(A, C, want_down, data, measure, ratio):
    """C 对 A 背驰没有（signals 用这一份）。
    · macd / slope / peak：C 的力度 < A 的力度 × ratio（严格 <；macd/slope 就是原来那一行，默认逐位不变）；
    · lines：两条线都不创新低（向下：C 的 min ≥ A 的 min，两条线都要）/ 不创新高（向上：≤）。
      持平算「不创新」（spec 六.1(b)）。ratio 对 lines 不适用（它比的不是大小，是创不创新）。
    · macd_or_lines：上面 macd 那条 **或** lines 那条，两半各自原样（spec 六.3(a)），不另发明比法。"""
    if measure == "macd_or_lines":
        return any(_diverges(A, C, want_down, data[m], m, ratio) for m in OR_PARTS)
    if measure == "lines":
        c, a = lines_extreme(C, data), lines_extreme(A, data)
        return all((x >= y) if want_down else (x <= y) for x, y in zip(c, a))
    return strength(C, data, measure) < strength(A, data, measure) * ratio


def _higher_centers(r, level):
    """本层的**上一层**中枢列表：笔层看线段中枢，线段层看**线段中枢自己**的扩展合成。

    ★ 线段层**不能**用 r["big"]：那两个是**同一级**的东西 —— r["seg_centers"] 是『线段当中枢』，
    r["big"] 是『类中枢（笔中枢）扩展合成』，两个都是线段级（`extend.py` 第 54 课那条：三个
    1 分钟中枢当成线段，重叠出的是 5 分钟中枢）。拿同级的来查『上一层有没有中枢包住』，是
    拿错了一级 ⇒ 线段层要再往上合成一次，即 build_hierarchy(seg_centers, 已完成线段)。

    ★ 线段层还要**只取真合成过的**（nmerge > 1）：build_hierarchy() 的返回值是**混级**的 ——
    合成出来的（level=2、nmerge>1）和**没合成、原样浅拷贝进来的单中枢**（nmerge=1、level 保持
    本级别）混在同一个列表里（`extend.py:59` 自己写着『不合的原样留下（nmerge=1）』）。浅拷贝那条
    **跟 B 是同一级**，拿它当『上一层的中枢』＝又犯一次『拿同级当上一层』的错。全仓已有的口径就是
    只认合成过的：`render/chart_nested.py:47`、`cards/c05_center.py:218` 都只取 nmerge>1 ——
    这里跟上，判据与画图/卡片读同一半。**笔层不滤**：seg_centers 是原始中枢（身上没有 nmerge
    这个键），它本来就是笔的上一层。
    """
    if level == "pen":
        return r["seg_centers"]
    if not r["seg_centers"]:
        return []
    done = [s for s in r["segs"] if not s.get("live")]
    return [c for c in build_hierarchy(r["seg_centers"], done) if c.get("nmerge", 1) > 1]


def check_premise3(higher, B, lo, hi, strict=True):
    """前提③：A、B、C 是不是其实同处一个**更大级别**的中枢里（第 53 课 L53:91）。

    原文：「B 的中枢级别比 A、C 里的中枢级别都要大，否则 A、B、C 就连成一个大的趋势或大的
    中枢了。」—— 这里判的就是那个「否则」：上一层有没有一个中枢把 A、B、C **整段**包住。

    strict=True  用中枢区间 [ZD, ZG] —— 原文「在一个大的中枢里」的字面读法（默认）
    strict=False 用波动范围 [DD, GG] —— 更宽，挡下的更多
    B 自己带 9 段升级（z["up"] 非空）时直接算成立：那本来就是『B 是高一级别中枢』。
    """
    if B.get("up"):
        return dict(hit=False, center=None, why="B 自带 9 段升级，本身就是高一级别中枢")
    for H in higher:
        if (H["ZD"] <= lo and H["ZG"] >= hi) if strict else (H["DD"] <= lo and H["GG"] >= hi):
            return dict(hit=True, center=H,
                        why="上一层中枢 [%.4f, %.4f] 把 A、B、C 整段包住" % (H["ZD"], H["ZG"]))
    return dict(hit=False, center=None, why="上一层没有中枢把 A、B、C 整段包住")


def beichi(AU, Z, k, kind, diverge_fn, hist, measure="macd", ratio=1.0,
           higher=(), premise3=True, p3_strict=True):
    """**背驰判法这一块**：取 A/B/C 段 → 判力度 → 判回拉 → 查前提③④。

    signals() 与 check_signals() 都调它 —— 这两处原先各写了一遍取段规则，改判法要改两处，
    改漏一处自检就会拿旧规则去核新判据。现在结构只有这一份。

    力度比较由调用方**注入** diverge_fn(A, C, want_down, hist, measure, ratio)：signals 传 _diverges()，
    check_signals 传 _diverges_by_definition() —— 『收成一块』收的是结构，力度那支的
    独立性靠注入保住（见 _strength_by_definition 的说明）。注入的是**整个比较**而不只是力度数：
    lines 那种看法不是一个数，比较方向写在哪一份里，就只有那一份管得着它。
    hist：力度要读的序列（series_for 给的；lines 是 (DIF, DEA)，其余是 MACD 柱）。

    返回 dict(emit, blocks, why, a, c, A, B, C, ok, p3, p4)：
      emit    True = 该发这个点
      blocks  挡下它的**全部**理由（按判的先后排），空列表 ⇒ emit=True
              'A/C 段找不到' | '没创新低' | '没背驰' | '前提③' | '回拉失败'
      ok      回拉：True 已回拉进中枢 / False 回拉前先破了 C 的极值 / None 还没走到
      p3      前提③ 的证据（hit=真被上一层中枢包住）
      p4      A 之前、同层里已经结束的中枢（前提④ 的证据；六份数据上 11/11 都非空）
    """
    want_down = kind.endswith("买")
    B = Z[k]
    same = (lambda u: u["p1"] < u["p0"]) if want_down else (lambda u: u["p1"] > u["p0"])
    a = next((q for q in range(B["PI0"] - 1, -1, -1) if same(AU[q])), None)                   # A 段
    c = next((q for q in (B["PI1"] + 1, B["PI1"] + 2) if q < len(AU) and same(AU[q])), None)  # C 段
    if a is None or c is None:
        return dict(emit=False, blocks=["A/C 段找不到"], why="A/C 段找不到",
                    a=a, c=c, A=None, B=B, C=None, ok=None, p3=None, p4=[])
    A, C = AU[a], AU[c]
    lo, hi = min(A["lo"], B["DD"], C["lo"]), max(A["hi"], B["GG"], C["hi"])
    p3 = check_premise3(higher, B, lo, hi, p3_strict)
    p4 = [z for z in Z[:k] if z["X1"] <= A["i0"]]

    blocks = []
    if not ((C["lo"] < B["DD"]) if want_down else (C["hi"] > B["GG"])):
        blocks.append("没创新低")                      # 没创新低（新高）：不是离开段
    elif not diverge_fn(A, C, want_down, hist, measure, ratio):
        blocks.append("没背驰")
    if premise3 and p3["hit"]:
        blocks.append("前提③")
    ok = None                                          # 背驰后：先回拉进中枢，还是先破 C 的极值
    for q in range(c + 1, len(AU)):
        u = AU[q]
        if (u["lo"] < C["p1"]) if want_down else (u["hi"] > C["p1"]):
            ok = False; break
        if (u["hi"] >= B["ZD"]) if want_down else (u["lo"] <= B["ZG"]):
            ok = True; break
    if ok is False:
        blocks.append("回拉失败")
    return dict(emit=not blocks, blocks=blocks, why=(blocks[0] if blocks else ""),
                a=a, c=c, A=A, B=B, C=C, ok=ok, p3=p3, p4=p4)


def signals(r, level="seg", measure="macd", ratio=1.0, fast=12, slow=26, sig=9,
            premise3=True, p3_strict=True):
    """level: "seg" 线段中枢（默认）/ "pen" 类中枢；measure: MEASURES 五选一（默认 macd）；
    ratio: C < A × ratio 才算背驰（lines 不用 ratio）。

    premise3：前提③ **默认开**（小栋 2026-10-02 拍板 ①A）—— 用 check_premise3 挡掉
    『A、B、C 其实同处一个更大级别中枢』的点。p3_strict：③ 用中枢区间（默认）还是波动范围。
    """
    AU, U, Z = _units(r, level)
    hist = series_for(r["bars"], measure, fast, slow, sig)
    n_done = len(U)                                  # U 里的单位下标与 AU 一致（已完成的在前）
    last_live = (level == "seg" and len(AU) > n_done) or level == "pen"
    done_idx = lambda q: q < len(AU) - (1 if last_live else 0)   # 这一段已经走完（后面又出了一段）
    out = []

    def add(kind, q, k, weak=False):
        u = AU[q]
        out.append(dict(kind=kind, bar=u["i1"], price=u["p1"], confirmed=done_idx(q), weak=weak,
                        level=level, center=k + 1, unit=q))

    # ---- 第三类：与中枢终结同一口径 ----
    for k, z in enumerate(Z):
        if z["term"] in ("三买", "三卖"):
            add(z["term"], z["PI1"] + 2, k)
    if level == "seg" and Z and Z[-1]["live"] and len(AU) > n_done:   # 待确认：回试段就是那条未完成线段
        z, j = Z[-1], n_done - 1
        u, w = AU[j], AU[j + 1]
        if j >= z["PI0"] + 3 and z["ZD"] <= u["p0"] <= z["ZG"]:
            if u["p1"] > u["p0"] and w["lo"] > z["ZG"]:
                add("三买", j + 1, len(Z) - 1)
            elif u["p1"] < u["p0"] and w["hi"] < z["ZD"]:
                add("三卖", j + 1, len(Z) - 1)

    # ---- 第一类、第二类：判据全部收在 beichi() 一块里 ----
    higher = _higher_centers(r, level)
    for k in range(1, len(Z)):
        B = Z[k]
        for want_down, rel, k1, k2 in ((True, "下跌延续", "一买", "二买"), (False, "上涨延续", "一卖", "二卖")):
            if B["rel"] != rel:
                continue
            blk = beichi(AU, Z, k, k1, _diverges, hist, measure, ratio,
                         higher, premise3, p3_strict)
            if not blk["emit"]:
                continue
            C, c = AU[blk["c"]], blk["c"]
            confirmed = bool(blk["ok"]) and done_idx(c)
            pt = dict(kind=k1, bar=C["i1"], price=C["p1"], confirmed=confirmed, weak=False,
                      level=level, center=k + 1, unit=c)
            if measure == "macd_or_lines":                                # 「更标准」只打标记，不另出点（六.3(b)）
                pt["std"] = all(_diverges(blk["A"], C, want_down, hist[m], m, ratio) for m in OR_PARTS)
            out.append(pt)
            if confirmed and c + 2 < len(AU):                             # 第二类：一买后第二段次级别走势的终点
                s2 = AU[c + 2]
                weak = (s2["p1"] < C["p1"]) if want_down else (s2["p1"] > C["p1"])
                add(k2, c + 2, k, weak)
    out.sort(key=lambda s: (s["bar"], s["kind"]))
    return out


def _strength_by_definition(u, hist, measure):
    """第 24 课的力度，**独立另写一份**——本函数存在的唯一理由就是它不调 strength()。

    为什么要抄一遍同样的公式：力度是背驰判据里唯一『算出来的量』，而 check_signals 原先
    只复核结构（点是不是段终点、方向、三类点的位置…），**没有一条看着力度**。
    实测：把 strength() 弄坏（斜率的 max(1, span) 换成 min，等长替换），ZEC 15m pen 的
    90 个买卖点里 12 个换了位置，而 check_signals 照样报 0——门一声不响。
    复核必须独立于被测实现，所以这里宁可重复一遍公式——和 check_centers『另写一遍、
    不调用 upgrades』是同一个写法。**改 strength 的公式时这里要一起改**，这是这份独立的代价。
    """
    if measure == "slope":
        span = u["i1"] - u["i0"]
        return abs(u["p1"] - u["p0"]) / (span if span > 1 else 1)      # 同 max(1, span)，写法不同
    seg = hist[u["i0"]:u["i1"] + 1]
    if measure == "peak":                                              # 同向柱子绝对值最大的一根，没有就 0
        best = 0
        for h in seg:
            if (h > 0) if u["p1"] > u["p0"] else (h < 0):
                best = max(best, abs(h))
        return best
    if u["p1"] > u["p0"]:
        return sum(h for h in seg if h > 0)
    return -sum(h for h in seg if h < 0)


def _diverges_by_definition(A, C, want_down, data, measure, ratio):
    """_diverges 的**独立另写**（check_signals 用）：lines 的比较方向在这里另写一遍，
    signals 那份写反了，复核才红得出来。macd_or_lines：两半各自用这里的另写版，再取「或」。"""
    if measure == "macd_or_lines":
        return (_diverges_by_definition(A, C, want_down, data["macd"], "macd", ratio)
                or _diverges_by_definition(A, C, want_down, data["lines"], "lines", ratio))
    if measure == "lines":
        dif, dea = data
        for line in (dif, dea):
            ca = sorted(line[C["i0"]:C["i1"] + 1])
            aa = sorted(line[A["i0"]:A["i1"] + 1])
            if want_down and ca[0] < aa[0]:                            # 向下：C 段这条线创了新低 ⇒ 不背驰
                return False
            if not want_down and ca[-1] > aa[-1]:                      # 向上：创了新高 ⇒ 不背驰
                return False
        return True
    return _strength_by_definition(C, data, measure) < _strength_by_definition(A, data, measure) * ratio


# beichi() 的挡下理由 → 自检报告的违规文字（两处措辞不必一样，但不许缺项）
_BLOCK_MSG = {
    "A/C 段找不到": "一类买卖点之前找不到同向的 A 段 / 之后找不到同向的 C 段",
    "没创新低": "一类买卖点的 C 段没创新低 / 新高",
    "没背驰": "背驰不成立：独立重算 C 段力度不小于 A 段 × 比例",
    "前提③": "前提③ 不成立：A、B、C 被上一层中枢整段包住，不构成更大级别",
    "回拉失败": "背驰后没先回拉进中枢，而是先破了 C 的极值",
}


def check_signals(sig, r, level="seg", measure="macd", ratio=1.0, check_zero_axis=False,
                  za_threshold=ZA_THRESHOLD, premise3=True, p3_strict=True):
    """独立复核（只用中枢与单位的原始字段，按定义另写一遍关键条件）。返回违规列表（应为空）。

    measure / ratio / premise3 / p3_strict 要跟产生 sig 的那次 signals() 调用一致，否则背驰
    那几条会误报或漏报（前两项一直如此，后两项随第二轮加上）。
    **MACD 参数（fast / slow / sig）也要一致** —— 本函数没有这三个形参，它按默认 12 / 26 / 9
    重算 hist（下面 `macd_hist(r["bars"])`），所以调用方若给 signals() 换过参数，复核量的就不是
    同一条线（今天仓里没有这样的调用点：`tools/selfcheck.py:81` 传的都是默认值）。

    一买 / 一卖这条**调 beichi() 同一块**（结构与 signals() 同一份），但注入的力度是
    _strength_by_definition() —— 独立另写一遍，才核得住 strength()。

    check_zero_axis：**默认 False**。开了才把『B 段回抽 0 轴附近』这条必要条件算进违规。
    默认关是拍过板的（2026-09-30 小栋）：这条的口径（统计量 / 窗口 / 阈值）**全是我们发明的数**，
    原文只给了"附近"两个字，而全库样本又少 ⇒ 先只当检查、不接进买卖点判定。口径见 ZA_* 常量。
    """
    AU, U, Z = _units(r, level)
    hist = series_for(r["bars"], measure) if measure != "slope" else None
    _za = ({(x["kind"], x["bar"]): x for x in zero_axis(sig, r, level, threshold=za_threshold)}
           if check_zero_axis else {})
    bad = []
    for s in sig:
        u = AU[s["unit"]]
        if (u["i1"], u["p1"]) != (s["bar"], s["price"]):
            bad.append(("点不在所属段的终点", s["kind"], s["bar"])); continue
        z = Z[s["center"] - 1]
        buy = s["kind"].endswith("买")
        if (u["p1"] < u["p0"]) != buy:
            bad.append(("买点不在向下段终点 / 卖点不在向上段终点", s["kind"], s["bar"]))
        if s["kind"] in ("三买", "三卖"):
            lv = AU[s["unit"] - 1]                                # 离开段
            if not (z["ZD"] <= lv["p0"] <= z["ZG"]):
                bad.append(("三类买卖点的离开段不是从中枢里出发", s["kind"], s["bar"]))
            if (u["lo"] <= z["ZG"]) if buy else (u["hi"] >= z["ZD"]):
                bad.append(("三类买卖点的回试段碰到了中枢区间", s["kind"], s["bar"]))
        if s["kind"] in ("一买", "一卖"):
            if z["rel"] != ("下跌延续" if buy else "上涨延续"):
                bad.append(("一类买卖点不在趋势的最后一个中枢之后", s["kind"], s["bar"]))
            if (u["lo"] >= z["DD"]) if buy else (u["hi"] <= z["GG"]):
                bad.append(("一类买卖点的 C 段没创新低 / 新高", s["kind"], s["bar"]))
            # 取段 / 力度 / 回拉 / 前提③ 全部调 beichi() 这一块（与 signals() 同一份结构），
            # 但力度注入独立实现 _strength_by_definition —— 这一条是力度那一支唯一的守卫。
            blk = beichi(AU, Z, s["center"] - 1, s["kind"], _diverges_by_definition, hist,
                         measure, ratio, _higher_centers(r, level), premise3, p3_strict)
            for b in blk["blocks"]:
                if b == "没创新低":
                    continue            # 上面那条结构检查（+ 三行前）已经报过同一个事实
                bad.append((_BLOCK_MSG.get(b, b), s["kind"], s["bar"]))
            x = _za.get((s["kind"], s["bar"]))
            if x is not None and not x["ok"]:
                bad.append(("B 段没把黄白线回抽 0 轴附近（r=%.3f > %.2f）" % (x["r"], za_threshold),
                            s["kind"], s["bar"]))
        if s["kind"] in ("二买", "二卖"):
            first = [t for t in sig if t["kind"] == ("一买" if buy else "一卖") and t["unit"] == s["unit"] - 2]
            if not first or not first[0]["confirmed"]:
                bad.append(("二类买卖点前面没有确认的一类买卖点", s["kind"], s["bar"]))
    return bad
