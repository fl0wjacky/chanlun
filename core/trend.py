"""走势分界 v3 —— docs/spec/走势分段.md（v3）D2、D4、D3，card-51571a5f-dc2 / card-e416aa21-0f6。

本级别 ＝ 线段中枢，次级别 ＝ 已完成线段（D5）。从左往右一段一段推，第 t 步只用 done[:t+1]：

  D2-1  候选死点：上一个分界 b 之后、到 done[t-2] 为止，同向线段终点里最高（H）／最低（L）的那个，一样极取后一个。
        图头还不知道方向 ⇒ 先看 H 再看 L，谁先确立算谁。
  D2-2  确立：参照中枢 Z ＝ 本段走势里（从 b 起切开重算）X0 不晚于 H 那一根的最后一个中枢；
        离开段 done[t-1] 终点 < Z.ZD 且回抽段 done[t]（向上）终点 < Z.ZD，且 H 之后价格没再过 H（P3，按段内 hi／lo）
        ⇒ 在 done[t] 走完时确立，刀落在 H。L 反过来（> Z.ZG）。
  D2-3  分界一高一低交替。
  D2-4  确立以后从 H 起整段重算中枢（_centers_with_cuts，按刀分组）。
  D2-6  没确立的就是中阴；最后一段还在长。
  D2-7  新刀 b' 让 b→b' 那一段一个中枢都没有 ⇒ b' 不立、b 撤回，回到 b 之前那段走势接着走（图头那一段不查）。
  D4    线段中枢的框只在确立的分界处断开（同一套中枢既画框又判分界）。
  D3    同一段走势里连续扩展的中枢合成一个高一级中枢（DD 取小、GG 取大）。读法 A：有合成中枢就整段升一级、
        只数合成出来的；读法 B：合成中枢留在本级别跟别的一起数（L17:255 后半句）。等小栋定，默认 A（spec 现写法）。

D2-5 死点类型（趋势背驰／盘整背驰／小转大）只标注、不决定刀，另一步做。
"""
from .center import find_centers, classify_relations


def _centers_with_cuts(done, ks):
    """D2-4（原 core/cut.py 规则 4，笔层出刀退役后挪到这里）：按切点下标 ks（段序号，升序）把已完成线段分组，各组从头 find_centers，PI 加回全局下标。
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


_HEAD_FIRST = False                               # 只给 trend_check --self-test 的探针开：先挪图头／末段再挪中间
_BLOCK_RETRACTED = True                           # 只给 trend_check --self-test 的探针关：D2-7 去掉过的那一对照旧反复确立／撤回
_MOVE_ENDS = True                                 # 只给 trend_check --self-test 的探针关：图头起点／末段终点不挪


def _standardize(done, bars):
    """D2-0（L78:50-51／L78:54，card-acbe5855）：已完成线段标准化成首尾相连的折线 —— 每条向上线段从段内最低开始、到最高结束，
    向下反过来。只改端点（价格与那一根），不改线段怎么划；hi／lo 按新区间重取。
    · 顶、底按线段自己的 dir 认，不按端点高低（线上 AAPL 1h 首段 dir=down、终点却比起点高，按端点认会造出零长度段）。
    · 每个接点挪到它左右两个接点之间（**不含**那两根）的极值上，顶取最高、底取最低；一轮挪完再来，直到不动 ——
      只挪一次不够（顶往后挪会带进下一段先跌的那一截，zec15 段 23 实测）；不含两邻是因为一根 K 线可能同时是最高和最低。
    · 图头起点只在 [第一段起点, 接点 1) 里挪，末段终点只在 (倒数第二个接点, 最后一段终点] 里挪（编者口径，Nova 06:30Z）。
    · 一样极取后一根（跟 D2-1「一样高取后一个」同口径）。"""
    if not done:
        return done
    n = len(done)
    piv = [done[0]["i0"]] + [s["i1"] for s in done]          # 第 k 个接点 ＝ done[k-1] 终点 ＝ done[k] 起点
    top = [done[0]["dir"] != "up"] + [s["dir"] == "up" for s in done]   # 接点 k 是顶 ⇔ 它前一段向上（图头起点反过来）
    lo0, hi_n = done[0]["i0"], done[-1]["i1"]

    def best(rng, k):
        return max(rng, key=(lambda i: (bars[i]["h"], i)) if top[k] else (lambda i: (-bars[i]["l"], i)))

    def move(k):
        if k == 0:
            rng = range(lo0, piv[1])
        elif k == n:
            rng = range(piv[n - 1] + 1, hi_n + 1)
        else:
            rng = range(piv[k - 1] + 1, piv[k + 1])
        if not rng:
            return False
        nb = best(rng, k)
        if nb == piv[k]:
            return False
        piv[k] = nb
        return True

    # 先后（编者口径，Nova 06:44Z 定 Atlas 的写法）：中间接点先挪到不动，图头起点、末段终点最后各挪一次。
    #   图头是被窗口截断的那一段，只能它迁就中间；先挪图头会把中间接点卡住（线上 AAPL 1h：起点先跳到 274.33，
    #   接点 1 只能在它后面找，真低点 245.99 就够不着了）。图头在 [起点, 接点1) 里挪、挪不过接点 1，所以挪完中间也不会再动。
    ends = (0, n) if _MOVE_ENDS else ()
    if _HEAD_FIRST:                                       # 只给探针：反过来先挪图头／末段
        for k in ends:
            move(k)
    for _ in range(len(piv) + 1):                         # 每轮至少定住一个；上限给死
        if not any([move(k) for k in range(1, n)]):
            break
    if not _HEAD_FIRST:
        for k in ends:
            move(k)
    out = []
    for k, s in enumerate(done):
        i0, i1 = piv[k], piv[k + 1]
        out.append(dict(s, i0=i0, i1=i1,
                        p0=bars[i0]["h"] if top[k] else bars[i0]["l"],
                        p1=bars[i1]["h"] if top[k + 1] else bars[i1]["l"],
                        hi=max(bars[i]["h"] for i in range(i0, i1 + 1)), lo=min(bars[i]["l"] for i in range(i0, i1 + 1))))
    return out


def _done(r, standardize=True):
    done = [s for s in r["segs"] if not s.get("live")]
    return _standardize(done, r["bars"]) if standardize and "bars" in r else done


def _is_up(s):
    return s["dir"] == "up"                      # 按线段自己的方向，不按端点高低（spec D2-0；线段层偶有终点不高于起点的坏段，card-24dd71cb-003）


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


def find_bounds(r, regroup=True, alternate=True, check_empty=True, no_exceed=True, standardize=True):
    """→ dict(bounds, retracted)。四个开关是 spec §四 的探针 P1／P2／P5／P3（默认全开 ＝ 规则本身）。
    bounds：[dict(line_seg=j, bar, kind 'H'/'L', price, pullback_line_seg=t, pullback_end_bar, ZD, ZG)]，按时间升序；
      ★ line_seg／pullback_line_seg 是**已完成线段**的下标（不是走势段号）—— 对外 `seg` 只指 segments[] 下标（Iris 10-05 17:51）；
    retracted：[dict(bar, kind, price, pullback_end_bar, retracted_bar, blocked_bar, blocked_kind)]（D2-7）。
    ★ pullback_end_bar ＝ 回抽段 S[t] 的终点那一根，**不是**实时能确立的那一根：线段要等后面的 K 线才算走完，
      实时确立更晚（tools/trend_check.py ④ 量出来 zec15 晚 61～184 根）。前端斜线画「极值到回抽段终点」，不标「确立」。"""
    done = _done(r, standardize)
    ks, bounds, retracted = [], [], []           # ks：切点段号（新组起点 ＝ j+1）
    want = None                                  # 下一个分界要 'H' 还是 'L'（None ＝ 两头都开）
    blocked = {}                                 # (kind, line_seg of b) → line_seg of b′：D2-7 去掉过的那一对（编者口径，card-eecdfd08）
    for t in range(2, len(done)):
        lo = ks[-1] if ks else 0
        for typ in ("H", "L"):
            if want and typ != want:
                continue
            hit = _try_confirm(done, t, ks if regroup else [], typ, lo, no_exceed)
            if hit is None:
                continue
            j, z = hit
            # 『同一对 (b, b′) 被 D2-7 去掉以后，b 不再确立，直到 b 或 b′ 被新的极值换掉』（编者口径，Nova 10-06）。
            #   D2-7 只看 done[b..b′] 这一组里有没有中枢，同一对的结论不会变（1m 实测同一对判了 40 次、40 次都没有）；
            #   b 换了 ⇒ j 不同、不在表里；b′ 换了 ⇒ 下面那个反向候选不是它了，放行。
            if _BLOCK_RETRACTED and (typ, j) in blocked and j + 1 < t - 1:
                opp = range(j + 1, t - 1)
                k2 = max(opp, key=(lambda k: (-done[k]["p1"], k)) if typ == "H" else (lambda k: (done[k]["p1"], k)))
                if k2 == blocked[(typ, j)]:
                    continue
            if ks and check_empty:               # D2-7：上一刀 → 这一刀之间得有中枢
                zz = _centers_with_cuts(done[:t + 1], ks + [j + 1])
                if not [q for q in zz if q["PI0"] >= lo and q["PI1"] <= j]:
                    ks.pop()
                    prev = bounds.pop()
                    blocked[(prev["kind"], prev["line_seg"])] = j
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


def trend_v3(r, reading="A", regroup=True, alternate=True, check_empty=True, no_exceed=True, standardize=True):
    """→ dict(seg_centers, bounds, retracted, pending, segments, units, reading)。
    seg_centers：按确立的分界切开重算的线段中枢（D4，前端画框就用它），每个带 seg（属于第几段走势，跟 segments 下标对齐）；
    segments：[dict(i0, i1, type, upgraded, head, live, n_centers_level)]，首尾相接盖满整张图；
      ★ n_centers_level 是**本级别**中枢个数，跟读法无关；读法 A 的升级段，字母挂在 units 上，个数不是它；
    units：D3 合成出来的高一级中枢（只列 n>1 的），带 seg，给前端画升级框；
    reading：这一跑用的 D3 读法（A／B），前端据此决定字母挂哪一级（spec §八 第 6 条）。"""
    res = find_bounds(r, regroup=regroup, alternate=alternate, check_empty=check_empty, no_exceed=no_exceed,
                      standardize=standardize)
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
