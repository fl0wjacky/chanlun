"""走势分段：在线段中枢这一级，把整张图切成一段接一段的走势类型 —— docs/spec/走势分段.md，card-51571a5f-dc2。

只在 core/cut.py 的刀上再筛一遍，不改任何一刀（spec 第三节）：
  规则 2  候选分界点 ＝ 已切成（done）的刀。
  规则 3  反复：找最左一个没有线段中枢的中间段，看它两头的两把刀 ——
          同类（都低／都高）⇒ 留更极端的那把（一样极留后一把）；一低一高 ⇒ 两把都去。
          每去一把刀，被隔开的线段合成一组、从头重找中枢（中枢切分.md 规则 4）。
  规则 4  段内 1 个中枢 ⇒ 盘整；≥2 个且两两都是同向「趋势」关系（classify_pair）⇒ 上涨／下跌；
          ≥2 个但有重叠 ⇒ 盘整（编者口径 A）。0 个（只会是图头或最后一段）⇒ 无中枢。
  规则 5  最后一段：还在长；它前面已有待定（pending）的刀 ⇒ 中阴（不拆，刀位置放在 pending_bars）。
          其余：已确认。
  规则 6  第一段从第 0 根开始，标 head=True（图头截断），照样分类。
"""
from .center import classify_pair
from .cut import _centers_with_cuts

LOW, HIGH = "低", "高"


def _end_kind(done, k):
    """端点 ends[k]（k ≥ 1）是高还是低：看结束在它上面的那条线段的方向。"""
    return HIGH if done[k - 1]["dir"] == "up" else LOW


def _groups(done, ks):
    """按刀 ks 分组重找中枢 → 每组的中枢列表（组内顺序）。"""
    bounds = [0] + list(ks) + [len(done)]
    zs = _centers_with_cuts(done, ks)
    return [[z for z in zs if bounds[g] <= z["PI0"] < bounds[g + 1]] for g in range(len(bounds) - 1)]


def merge_cuts(done, ks, bars, regroup=True):
    """规则 3 → 留下的刀（端点下标，升序）。regroup=False 是探针「去刀后不重算中枢」：一直用最初那次的分组计数。"""
    ks = sorted(ks)
    ends = [done[0]["i0"]] + [s["i1"] for s in done]
    first = None if regroup else [z for zs in _groups(done, ks) for z in zs]
    while True:
        if regroup:
            empty = [g for g, zs in enumerate(_groups(done, ks)) if 0 < g < len(ks) and not zs]
        else:                                            # 探针：中枢只用最初那次找的，刀去了也不重找
            empty = [g for g in range(1, len(ks))
                     if not any(ks[g - 1] <= z["PI0"] and z["PI1"] < ks[g] for z in first)]
        if not empty:
            return ks
        g = empty[0]
        a, b = ks[g - 1], ks[g]
        ka, kb = _end_kind(done, a), _end_kind(done, b)
        if ka != kb:
            drop = {a, b}
        elif ka == LOW:
            drop = {a if (bars[ends[b]]["l"] <= bars[ends[a]]["l"]) else b}
        else:
            drop = {a if (bars[ends[b]]["h"] >= bars[ends[a]]["h"]) else b}
        ks = [k for k in ks if k not in drop]


def _type(zs):
    if not zs:
        return "无中枢"
    if len(zs) == 1:
        return "盘整"
    rels = {classify_pair(a, b)[0] for a, b in zip(zs, zs[1:])}
    if rels == {"上涨延续"}:
        return "上涨"
    if rels == {"下跌延续"}:
        return "下跌"
    return "盘整"


def trend_segments(r, cuts, regroup=True, rule3=True):
    """r ＝ analyze() 的结果；cuts ＝ cut_centers(r, …)[1]。
    → [dict(i0, i1, type, status, head, n_centers, centers, start_kind, end_kind, pending_bars)]，首尾相接、盖满 [0, len(bars)-1]。
    rule3=False / regroup=False 是 spec 第五节的两个探针。"""
    bars = r["bars"]
    n = len(bars)
    done = [s for s in r["segs"] if not s.get("live")]
    if not done:
        return [dict(i0=0, i1=n - 1, type="无中枢", status="还在长", head=True, n_centers=0, centers=[],
                     start_kind=None, end_kind=None, pending_bars=[])] if n else []
    ends = [done[0]["i0"]] + [s["i1"] for s in done]
    k_of = {e: k for k, e in enumerate(ends)}
    ks = sorted(k_of[c["cut_bar"]] for c in cuts if c["status"] == "done")
    if rule3:
        ks = merge_cuts(done, ks, bars, regroup=regroup)
    groups = _groups(done, ks)
    last_cut = ends[ks[-1]] if ks else 0
    pend = sorted(c["cut_bar"] for c in cuts if c["status"] == "pending" and c["cut_bar"] > last_cut)
    out = []
    for g, zs in enumerate(groups):
        i0 = 0 if g == 0 else ends[ks[g - 1]]
        i1 = n - 1 if g == len(groups) - 1 else ends[ks[g]]
        lastg = g == len(groups) - 1
        out.append(dict(
            i0=i0, i1=i1, type=_type(zs),
            status=("中阴" if pend else "还在长") if lastg else "已确认",
            head=g == 0, n_centers=len(zs),
            centers=[(z["PI0"], z["PI1"]) for z in zs],
            start_kind=None if g == 0 else _end_kind(done, ks[g - 1]),
            end_kind=None if lastg else _end_kind(done, ks[g]),
            pending_bars=pend if lastg else []))
    return out
