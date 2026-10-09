# -*- coding: utf-8 -*-
"""级别联动（docs/spec/级别联动.md §四 第 1／3／4 项，card-6e338490）：只给数据，文案归前端。

纯函数，不碰缓存、不碰币安：server.py 从缓存里取出各周期的「视图」交进来。
没量到一律写 "unmeasured"，**不许**默认成对得上（Nova 10-06：没量到不算绿）。

视图 view = {"t": [每根 K 线的开盘毫秒], "step": 一根 K 线的毫秒, "bounds": trend.bounds, "centers": seg_centers,
"units": trend.units}（bounds 用 bar／price，centers 与 units 用 X0／X1，都是本图 K 线下标）。
★ 时间区间一律取 [第一根开盘, 最后一根开盘 + 一根)：不加那一根，1h 中枢的尾巴少算 1 小时，
  正好落在里面的 15m 框会算成 99.x% ⇒ 被误判成对不上。
"""

REF_MULT = 4      # 第 3 项的对照周期 = 本图周期 × REF_MULT（spec L-8，编者口径，依 L33:21-26 的 15→60 那套安排）
MATCH_PCT = 100   # 合成框落在对照图「主要那个中枢」里的时间占比 < 它 ⇒ mismatch（编者口径）。
                  # 照 spec §二 2 的实例：63%、72% 都算「对不上」，只有 100% 算对得上 ⇒ 100。
                  # （我先提的 50 跟这几个实例矛盾，已报 Nova／Atlas；要调就拿线上 15 张图的分布再定）


def finest_tf(tfs):
    """配置里最细的周期 —— 只在这里定（以后加 5m／1m 自动跟，Nova 10-06）。tfs: {名字: 毫秒}。"""
    return min(tfs, key=tfs.get)


def ref_tf(tf, tfs):
    """本图的对照周期（L-8：× REF_MULT）；配置里没有那个周期（2h、4h）⇒ None ⇒ 第 3 项全 unmeasured。"""
    want = tfs[tf] * REF_MULT
    return next((k for k, v in tfs.items() if v == want), None)


def _span(view, x0, x1):
    t = view["t"]
    return t[x0], t[x1] + view["step"]


def start_link(here, finest, step_ms):
    """第 4 项（L-7，起点以细图为准）。本图就是最细那张 ⇒ None（不标）。
    status：same（一样，不标）／differs（真分歧）／window（数据窗口造成的，印「图里没有更早的数据」，不算分歧）／
    unmeasured（最细那张缓存里没有，或两张图有一张没有分界）。"""
    if finest is None:
        return {"status": "unmeasured", "finest": None, "here": None, "first_center_t": None}
    first_c = here["centers"][0] if here["centers"] else None
    out = {"status": "unmeasured",
           "finest": None, "here": None,
           "first_center_t": here["t"][first_c["X0"]] if first_c else None}
    if not finest["bounds"] or not here["bounds"]:
        return out
    fb, hb = finest["bounds"][0], here["bounds"][0]
    out["finest"] = {"price": fb["price"], "t": finest["t"][fb["bar"]]}
    out["here"] = {"price": hb["price"], "t": here["t"][hb["bar"]]}
    if out["finest"]["t"] < here["t"][0] or out["here"]["t"] < finest["t"][0]:
        out["status"] = "window"          # 有一张图根本没有那一段数据：图头差别是窗口造成的
    elif fb["price"] == hb["price"] and abs(out["finest"]["t"] - out["here"]["t"]) < step_ms:
        out["status"] = "same"
    else:
        out["status"] = "differs"
    return out


def units_part(here, ref, same_level):
    """/api/levels 里第 3 项那一块 → {"units_applicable": bool, "units": [...]}。
    同级别下本级不合成框（T2：trend.units 为空），第 3 项**不适用**（Nova 10-09 13:09 选 (b)；spec 级别联动 §四 第 3 项，
    依据 L38:35「该级别以上级别，根本不考虑」）：明说 units_applicable=false，不给一个看上去像「没有框」的空列表。
    文案归前端（「级别对照」按灰、悬停写原因）。"""
    if same_level:
        return {"units_applicable": False, "units": []}
    return {"units_applicable": True, "units": unit_links(here, ref)}


def unit_links(here, ref):
    """第 3 项：本图每个合成框（trend.units，同下标）落在对照图哪几个线段中枢里、按时间算的占比。
    status 四种（Nova 10-06，spec L-9）：match（整个框在一个中枢里）／partial（只有 pre 或 post 落在外面，
    没有 gap、没跨两个中枢 —— 部分未比，不算分歧）／mismatch（有 gap 或跨两个中枢）／
    unmeasured（对照图没有：缓存里没有／本图最粗，或对照图的 K 线没盖住这个框）。"""
    out = []
    for u in here["units"]:
        if ref is None:
            out.append({"status": "unmeasured", "share": [], "outside": None})
            continue
        t0, t1 = _span(here, u["X0"], u["X1"])
        if t0 < ref["t"][0] or t1 > ref["t"][-1] + ref["step"]:
            out.append({"status": "unmeasured", "share": [], "outside": None})
            continue
        share, top = [], 0.0
        spans = [_span(ref, c["X0"], c["X1"]) for c in ref["centers"]]
        out_ms = {"pre": 0, "gap": 0, "post": 0}       # 框里不在任何对照中枢里的时间：在第一个之前／两个之间／最后一个之后
        if spans:                                       # （Iris 10-06：27% 那个框大半段是「1h 上还没有中枢」，不是对不上）
            first, last = min(a for a, _ in spans), max(b for _, b in spans)
            out_ms["pre"] = max(0, min(t1, first) - t0)
            out_ms["post"] = max(0, t1 - max(t0, last))
            inside = sum(max(0, min(t1, b) - max(t0, a)) for a, b in spans)   # 线段中枢按时间不重叠
            out_ms["gap"] = max(0, (t1 - t0) - inside - out_ms["pre"] - out_ms["post"])
        else:
            out_ms["pre"] = t1 - t0                     # 对照图一个中枢都没有：整个框都算「还没有」
        for i, c in enumerate(ref["centers"], 1):
            c0, c1 = _span(ref, c["X0"], c["X1"])
            frac = max(0, min(t1, c1) - max(t0, c0)) / (t1 - t0)   # t1 > t0：区间至少一根宽
            if frac > 0:
                top = max(top, frac)
                if round(100 * frac) > 0:                           # 印给人看的取整（不印 0%）；判定用 frac 本身
                    share.append({"i": i, "pct": round(100 * frac)})
        hit = sum(1 for a, b in spans if min(t1, b) > max(t0, a))   # 框碰到几个对照中枢
        if 100 * top >= MATCH_PCT:
            st = "match"
        elif out_ms["gap"] == 0 and hit <= 1 and (out_ms["pre"] or out_ms["post"]):
            st = "partial"        # 落在外面的只有对照图第一个中枢之前／最后一个之后：部分未比，不算分歧（Nova 10-06，L-9）
        else:
            st = "mismatch"       # 夹在两个中枢之间、或跨了两个中枢
        out.append({"status": st, "share": share,
                    "outside": {k: round(100 * v / (t1 - t0)) for k, v in out_ms.items()}})
    return out
