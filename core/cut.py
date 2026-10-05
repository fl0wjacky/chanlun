"""线段中枢在转折点切开（可切换画法，默认不变）—— docs/spec/中枢切分.md，card-e346ede6-996。

只改**线段中枢的画法**：笔、线段、类中枢、两层买卖点一律不动；线段层买卖点仍按**不切**的
r["seg_centers"] 算（规则 6，否则成环）。

  规则 1  转折点在**笔层**认（L29:3「站在次级别图形中」）——笔层买卖点不读线段中枢，没有循环。
  规则 2  笔层已确认的 一买/一卖 ⇒ 切在极值那根（C 段终点）；三买/三卖 ⇒ **往回**落到上一刀以来（到离开笔起点为止）
          最低（三买）/最高（三卖）的线段端点 —— 前一个走势的结束点（10-05 改）。
          二买/二卖不当转折点。
  规则 3  切点落到最近的**已完成**线段端点上（一样近取后一个）。
  规则 4  切点前后各自从头 find_centers；切点之后整段重新划分。
  规则 5  切点之后已完成线段的头三段：有重叠 ⇒ done（在第三段完成时立住）；不重叠 ⇒ void；
          不满三段 ⇒ pending。
  待定画法：seg_centers 里 pending 的刀照回旧框（不切），done 的刀切；预览要的框放在
          cuts[i]["boxes"]（带 provisional=True），前端开关决定画哪个。
"""
from .center import find_centers, classify_relations

TURN_KINDS = ("一买", "一卖", "三买", "三卖")


def _turn_bar(g, pens):
    """一类点：极值那根（C 段终点）；三类点：离开笔（回试笔的前一笔）的起点 —— 三类的切点不在这里，见 _backdate。"""
    if g["kind"] in ("一买", "一卖"):
        return g["bar"]
    return pens[g["unit"] - 1]["i0"]


def _backdate(kind, leave_bar, prev_k, ends, bars):
    """规则 2（10-05 改，L38:104 / L52:90 / L88:19-21）：三类点**往回**落到前一个走势的结束点。
    窗口 = 上一刀之后（没有就从图头）到离开笔起点（含）的已完成线段端点；三买取最低、三卖取最高，一样极取后一个。
    窗口里一个端点都没有 ⇒ None（这一刀不切）。"""
    cand = [k for k in range(prev_k + 1, len(ends)) if ends[k] <= leave_bar]
    if not cand:
        return None
    if kind == "三买":
        return min(cand, key=lambda k: (bars[ends[k]]["l"], -k))
    return min(cand, key=lambda k: (-bars[ends[k]]["h"], -k))


def _snap(bar, ends):
    """规则 3：落到最近的已完成线段端点（ends 升序）；一样近取后一个。返回端点在 ends 里的下标。"""
    best = None
    for k, e in enumerate(ends):
        d = abs(e - bar)
        if best is None or d < best[0] or (d == best[0] and e > ends[best[1]]):
            best = (d, k)
    return best[1]


def _status(done, k):
    """规则 5：从第 k 段（切点后的第一段）起，已完成线段的头三段。"""
    if k + 3 > len(done):
        return "pending"
    a, b, c = done[k:k + 3]
    return "done" if min(a["hi"], b["hi"], c["hi"]) >= max(a["lo"], b["lo"], c["lo"]) else "void"


def _centers_with_cuts(done, ks):
    """规则 4：按切点下标 ks（段序号，升序）把已完成线段分组，各组从头 find_centers，PI 加回全局下标。
    组被切点截断的最后一个中枢 live 改 False、终结写『转折点切开』（跟段内类中枢『所在线段结束』同一个道理）。"""
    out, bounds = [], [0] + list(ks) + [len(done)]
    for gi in range(len(bounds) - 1):
        lo, hi = bounds[gi], bounds[gi + 1]
        last_group = gi == len(bounds) - 2
        for z in find_centers(done[lo:hi]):
            z["PI0"] += lo
            z["PI1"] += lo
            z["seg"] = gi                                # 只用来让 classify_relations 在切点处不接续
            if z["live"] and not last_group:
                z["live"], z["term"] = False, "转折点切开"
            out.append(z)
    out = classify_relations(out)
    for z in out:
        z.pop("seg", None)                               # 线段中枢的对外形状不多一个键
    return out


def cut_centers(r, pen_signals, units=None):
    """→ (seg_centers 当前状态, cuts)。pen_signals = signals(r, "pen", measure) —— 跟着请求的看法走。
    units：买卖点的 unit 下标指向的那一层（默认笔；探针「改在线段层认」时传 r["segs"]）。"""
    done = [s for s in r["segs"] if not s.get("live")]
    if not done:
        return r["seg_centers"], []
    ends = [done[0]["i0"]] + [s["i1"] for s in done]     # 端点 ends[k] = 第 k 段的起点（k == len(done) 是最后一段终点）
    pens = r["pens"] if units is None else units
    cuts, prev_k = {}, 0                                 # prev_k：上一刀落在哪个端点（0 ＝ 图头）
    for g in sorted(pen_signals, key=lambda g: g["bar"]):
        if not g["confirmed"] or g["kind"] not in TURN_KINDS:
            continue
        if g["kind"] in ("一买", "一卖"):
            k = _snap(_turn_bar(g, pens), ends)
        else:
            k = _backdate(g["kind"], _turn_bar(g, pens), prev_k, ends, r["bars"])
            if k is None:
                continue
        if k == 0:
            continue                                     # 切在第一段起点上 ＝ 没切
        prev_k = max(prev_k, k)
        c = cuts.setdefault(k, dict(level="seg", cut_bar=ends[k], by="笔·" + g["kind"], signal_bar=g["bar"], n=0))
        c["n"] += 1
    ks = sorted(cuts)
    for k in ks:
        cuts[k]["status"] = _status(done, k)
    k_done = [k for k in ks if cuts[k]["status"] == "done"]
    k_pend = [k for k in ks if cuts[k]["status"] == "pending"]
    current = _centers_with_cuts(done, k_done)
    if k_pend:
        preview = _centers_with_cuts(done, sorted(k_done + k_pend))
        for k in k_pend:
            nxt = min([j for j in ks if j > k] + [len(done)])
            prv = max([j for j in k_done + k_pend if j < k] + [0])
            boxes = [dict(z, provisional=True) for z in preview if prv <= z["PI0"] < nxt]
            cuts[k]["boxes"] = boxes
    return current, [cuts[k] for k in ks]
