"""走势分界 v3 —— docs/spec/走势分段.md（v3）D2、D4、D3，card-51571a5f-dc2 / card-e416aa21-0f6。

本级别 ＝ 线段中枢，次级别 ＝ 已完成线段（D5）。从左往右一段一段推，第 t 步只用 done[:t+1]：

  D2-1  候选死点：上一个分界 b 之后、到 done[t-2] 为止，同向线段终点里最高（H）／最低（L）的那个，一样极取后一个。
        图头还不知道方向 ⇒ 先看 H 再看 L，谁先确立算谁。
  D2-2  确立：参照中枢 Z ＝ 本段走势里（从 b 起切开重算）X0 不晚于 H 那一根的最后一个中枢；
        离开段 done[t-1] 终点 < Z.ZD 且回抽段 done[t]（向上）终点 < Z.ZD，且 H 之后价格没再过 H（P3，按段内 hi／lo）
        ⇒ 在 done[t] 走完时确立，刀落在 H。L 反过来（> Z.ZG）。
  D2-3  分界一高一低交替。
  D2-4  确立以后从 H 起整段重算中枢（core.cut._centers_with_cuts，按刀分组）。
  D2-6  没确立的就是中阴；最后一段还在长。
  D2-7  新刀 b' 让 b→b' 那一段一个中枢都没有 ⇒ b' 不立、b 撤回，回到 b 之前那段走势接着走（图头那一段不查）。
  D4    线段中枢的框只在确立的分界处断开（同一套中枢既画框又判分界）。
  D3    同一段走势里连续扩展的中枢合成一个高一级中枢（DD 取小、GG 取大）。读法 A：有合成中枢就整段升一级、
        只数合成出来的；读法 B：合成中枢留在本级别跟别的一起数（L17:255 后半句）。等小栋定，默认 A（spec 现写法）。

D2-5 死点类型（趋势背驰／盘整背驰／小转大）只标注、不决定刀，另一步做。
"""
from .cut import _centers_with_cuts


def _done(r):
    return [s for s in r["segs"] if not s.get("live")]


def _is_up(s):
    return s["p1"] > s["p0"]


def _try_confirm(done, t, ks, typ, lo, no_exceed=True):
    """第 t 步、方向 typ（'H'/'L'）能不能确立 → (j, Z) 或 None。j ＝ 死点所在线段（刀落在 done[j]['i1']）。"""
    cand = range(lo, t - 1)                      # 到 t-2 为止：后面要留离开段、回抽段
    if not cand:
        return None
    if typ == "H":
        j = max(cand, key=lambda k: (done[k]["p1"], k))
    else:
        j = max(cand, key=lambda k: (-done[k]["p1"], k))
    if _is_up(done[j]) != (typ == "H"):          # 极值得是同向线段的终点
        return None
    # D2-2（P3，Nova 10-05 16:42 定成条件）：H 之后价格没再过 H（L 反过来）。线段端点不一定是段内极值（L78:50-51），
    # 所以这条推不出来、要单写：看 j 之后每条线段的 hi／lo，不只看端点
    after = done[j + 1:t + 1]
    if no_exceed and after and (max(a["hi"] for a in after) > done[j]["p1"] if typ == "H"
                                else min(a["lo"] for a in after) < done[j]["p1"]):
        return None
    zs = _centers_with_cuts(done[:t + 1], ks)
    ref = [z for z in zs if z["PI0"] >= lo and z["X0"] <= done[j]["i1"]]
    if not ref:
        return None                              # 本段走势里还没有中枢 ⇒ 一直中阴（D2-6）
    z = ref[-1]
    leave, back = done[t - 1], done[t]
    if typ == "H":
        ok = leave["p1"] < z["ZD"] and back["p1"] < z["ZD"] and _is_up(back)
    else:
        ok = leave["p1"] > z["ZG"] and back["p1"] > z["ZG"] and not _is_up(back)
    return (j, z) if ok else None


def find_bounds(r, regroup=True, alternate=True, check_empty=True, no_exceed=True):
    """→ dict(bounds, retracted)。四个开关是 spec §四 的探针 P1／P2／P5／P3（默认全开 ＝ 规则本身）。
    bounds：[dict(line_seg=j, bar, kind 'H'/'L', price, pullback_line_seg=t, pullback_end_bar, ZD, ZG)]，按时间升序；
      ★ line_seg／pullback_line_seg 是**已完成线段**的下标（不是走势段号）—— 对外 `seg` 只指 segments[] 下标（Iris 10-05 17:51）；
    retracted：[dict(bar, kind, price, pullback_end_bar, retracted_bar, blocked_bar, blocked_kind)]（D2-7）。
    ★ pullback_end_bar ＝ 回抽段 S[t] 的终点那一根，**不是**实时能确立的那一根：线段要等后面的 K 线才算走完，
      实时确立更晚（tools/trend_check.py ④ 量出来 zec15 晚 61～184 根）。前端斜线画「极值到回抽段终点」，不标「确立」。"""
    done = _done(r)
    ks, bounds, retracted = [], [], []           # ks：切点段号（新组起点 ＝ j+1）
    want = None                                  # 下一个分界要 'H' 还是 'L'（None ＝ 两头都开）
    for t in range(2, len(done)):
        lo = ks[-1] if ks else 0
        for typ in ("H", "L"):
            if want and typ != want:
                continue
            hit = _try_confirm(done, t, ks if regroup else [], typ, lo, no_exceed)
            if hit is None:
                continue
            j, z = hit
            if ks and check_empty:               # D2-7：上一刀 → 这一刀之间得有中枢
                zz = _centers_with_cuts(done[:t + 1], ks + [j + 1])
                if not [q for q in zz if q["PI0"] >= lo and q["PI1"] <= j]:
                    ks.pop()
                    prev = bounds.pop()
                    retracted.append(dict(bar=prev["bar"], kind=prev["kind"], price=prev["price"],
                                          pullback_end_bar=prev["pullback_end_bar"], retracted_bar=done[t]["i1"],
                                          blocked_bar=done[j]["i1"], blocked_kind=typ))
                    want = prev["kind"]
                    break
            ks.append(j + 1)
            bounds.append(dict(line_seg=j, bar=done[j]["i1"], kind=typ, price=done[j]["p1"], pullback_line_seg=t,
                               pullback_end_bar=done[t]["i1"], ZD=z["ZD"], ZG=z["ZG"]))
            want = None if not alternate else ("L" if typ == "H" else "H")
            break
    return dict(bounds=bounds, retracted=retracted, ks=ks, done=done, want=want)


def pending(done, ks, want):
    """D2-6：当前这段走势的候选极值（还没确立）→ [dict(bar, kind, price)]。want 为 None（图头）时两头都给。"""
    lo = ks[-1] if ks else 0
    out = []
    for typ in ("H", "L"):
        if want and typ != want:
            continue
        segs = [k for k in range(lo, len(done)) if _is_up(done[k]) == (typ == "H")]
        if not segs:
            continue
        j = max(segs, key=lambda k: ((done[k]["p1"] if typ == "H" else -done[k]["p1"]), k))
        out.append(dict(bar=done[j]["i1"], kind=typ, price=done[j]["p1"]))
    return out


def _units(zz):
    """D3-2：同一段走势里连续扩展的中枢合成一个单元。"""
    units = []
    for i, z in enumerate(zz):
        if i and z["kind"] == "扩展":
            u = units[-1]
            units[-1] = dict(DD=min(u["DD"], z["DD"]), GG=max(u["GG"], z["GG"]), n=u["n"] + 1,
                             X0=u["X0"], X1=max(u["X1"], z["X1"]))
        else:
            units.append(dict(DD=z["DD"], GG=z["GG"], n=1, X0=z["X0"], X1=z["X1"]))
    return units


def _trend_of(units):
    """单元依次同向、波动区间互不重叠 ⇒ 上涨／下跌；否则 None。"""
    rel = {"上" if v["DD"] > u["GG"] else "下" if v["GG"] < u["DD"] else "叠" for u, v in zip(units, units[1:])}
    if rel == {"上"}:
        return "上涨"
    if rel == {"下"}:
        return "下跌"
    return None


def classify(zz, reading="A"):
    """D3-3：一段走势的类型 → (类型, 升级?)。reading ∈ A（整段升一级，只数合成中枢）/ B（合成中枢留在本级别一起数）。"""
    units = _units(zz)
    if not units:
        return "无中枢", False
    up = [u for u in units if u["n"] > 1]
    if up and reading == "A":
        if len(up) == 1:
            return "盘整", True
        return (_trend_of(up) or "盘整"), True
    if len(units) == 1:
        return "盘整", bool(up)
    return (_trend_of(units) or "盘整"), bool(up)


def trend_v3(r, reading="A", regroup=True, alternate=True, check_empty=True, no_exceed=True):
    """→ dict(seg_centers, bounds, retracted, pending, segments, units, reading)。
    seg_centers：按确立的分界切开重算的线段中枢（D4，前端画框就用它），每个带 seg（属于第几段走势，跟 segments 下标对齐）；
    segments：[dict(i0, i1, type, upgraded, head, live, n_centers_level)]，首尾相接盖满整张图；
      ★ n_centers_level 是**本级别**中枢个数，跟读法无关；读法 A 的升级段，字母挂在 units 上，个数不是它；
    units：D3 合成出来的高一级中枢（只列 n>1 的），带 seg，给前端画升级框；
    reading：这一跑用的 D3 读法（A／B），前端据此决定字母挂哪一级（spec §八 第 6 条）。"""
    res = find_bounds(r, regroup=regroup, alternate=alternate, check_empty=check_empty, no_exceed=no_exceed)
    done, ks = res["done"], res["ks"]
    n = len(r["bars"])
    if not done:
        return dict(seg_centers=[dict(z, seg=0) for z in r["seg_centers"]], bounds=[], retracted=[], pending=[],
                    units=[], reading=reading,
                    segments=[dict(i0=0, i1=n - 1, type="无中枢", upgraded=False, head=True, live=True,
                                   n_centers_level=0)])
    zs = _centers_with_cuts(done, ks)
    edges = [0] + ks + [len(done)]
    segments, units_out, centers_out = [], [], []
    for g, (a, b) in enumerate(zip(edges, edges[1:])):
        zz = [z for z in zs if a <= z["PI0"] < b]
        centers_out += [dict(z, seg=g) for z in zz]
        kind, upgraded = classify(zz, reading)
        last = g == len(edges) - 2
        segments.append(dict(i0=0 if g == 0 else done[a - 1]["i1"], i1=n - 1 if last else done[b - 1]["i1"],
                             type=kind, upgraded=upgraded, head=g == 0, live=last, n_centers_level=len(zz)))
        units_out += [dict(u, seg=g) for u in _units(zz) if u["n"] > 1]
    assert len(centers_out) == len(zs)                # 每个中枢恰好属于一段（PI0 落在组内）
    return dict(seg_centers=centers_out, bounds=res["bounds"], retracted=res["retracted"],
                pending=pending(done, ks, res["want"]), segments=segments, units=units_out, reading=reading)
