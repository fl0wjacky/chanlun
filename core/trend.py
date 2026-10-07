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


def _group_centers(done, lo, hi, gi, last_group, start_dir=None, free_first=False):
    """一组（两刀之间）的中枢：从头 find_centers，PI 加回全局下标；被切点截断的最后一个中枢 live 改 False、
    终结写『转折点切开』（跟段内类中枢『所在线段结束』同一个道理）。带 seg＝组号，给 classify_relations 在切点处不接续。"""
    out = []
    for z in find_centers(done[lo:hi], start_dir=start_dir, free_first=free_first):
        z["PI0"] += lo
        z["PI1"] += lo
        z["seg"] = gi
        if z["live"] and not last_group:
            z["live"], z["term"] = False, "转折点切开"
        out.append(z)
    return out


def _centers_with_cuts(done, ks):
    """D2-4（原 core/cut.py 规则 4，笔层出刀退役后挪到这里）：按切点下标 ks（段序号，升序）把已完成线段分组，各组从头 find_centers。"""
    bounds = [0] + list(ks) + [len(done)]
    out = []
    for gi in range(len(bounds) - 1):
        out += _group_centers(done, bounds[gi], bounds[gi + 1], gi, gi == len(bounds) - 2)
    out = classify_relations(out)
    for z in out:
        z.pop("seg", None)                               # 线段中枢的对外形状不多一个键
    return out


_HEAD_FIRST = False                               # 只给 trend_check --self-test 的探针开：先挪图头／末段再挪中间
_BLOCK_RETRACTED = True                           # 只给 trend_check --self-test 的探针关：D2-7 去掉过的那一对照旧反复确立／撤回
_MOVE_ENDS = True                                 # 只给 trend_check --self-test 的探针关：图头起点／末段终点不挪
_DIR_RULE = True                                  # 只给 trend_check --self-test 的探针关：L24:84-85 中枢方向不限（card-40f4ce13）


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


_D3_REGROUP = True                               # 只给 trend_check --self-test 的探针关：合成框退回拼 DD／GG（旧 D3-2）
_D6_BASE_ONLY = True                             # 只给 trend_check --self-test 的探针关：升级·上涨／下跌的段也套 D6 方向限制
_D3_LIVE_TAIL = True                             # 只给 trend_check --self-test 的探针关：最后一个中枢还在走也照样合成（D3-4）


def _regroup(done, a, b):
    """D3-2（二A，小栋 10-07；推广口径 (iii) 编者口径，Nova 10-07 07:12Z）：已完成线段 done[a..b] 按高一级重新找中枢。
    头 9 段按 3+3+3 分三组（每组＝3 条线段，区间取那 3 条的最低～最高），ZD＝三组低点的最大值、ZG＝三组高点的最小值（中枢公式 L20:47）；
    之后每 3 段一组、跟 [ZD, ZG] 有重叠就算延伸（只扩 DD／GG），碰到第一组没重叠、或者剩下不足 3 段就停。
    → dict(ZD, ZG, DD, GG, a, e)（e＝用到的最后一条线段），或 None：不足 9 段（L32:118-120）／头 9 段三组无重叠 ⇒ 构不成。"""
    if b - a + 1 < 9:
        return None
    grp = lambda k: (min(done[q]["lo"] for q in range(k, k + 3)), max(done[q]["hi"] for q in range(k, k + 3)))
    g = [grp(a + 3 * m) for m in range(3)]
    zd, zg = max(x[0] for x in g), min(x[1] for x in g)
    if zd > zg:
        return None
    e = a + 8
    while e + 3 <= b:
        lo, hi = grp(e + 1)
        if lo > zg or hi < zd:
            break
        g.append((lo, hi))
        e += 3
    return dict(ZD=zd, ZG=zg, DD=min(x[0] for x in g), GG=max(x[1] for x in g), a=a, e=e)


def _units(zz, done=None):
    """D3-2：同一段走势里连续扩展的中枢（一条扩展链）合成一个高一级中枢 → 计数用的单元列表（按时间）。
    · 合成成功 ⇒ 一个单元：区间按 _regroup 重算（不拼 DD／GG）；n＝落在它用到的线段里的本级别中枢个数（≥2）。
      延伸停下以后链上剩下的中枢不并进框，照本级别各算一个单元（Nova 10-07 ③；读法 A 下段型只数合成单元，不受它们影响）。
    · 构不成（不足 9 段／头 9 段无重叠）、或链上最后一个中枢还在走（D3-4，L36:44-45）⇒ 链上每个中枢各算一个单元（n=1）。
    done 不给 ⇒ 旧写法（拼 DD／GG），只留给没有线段的调用方；探针 _D3_REGROUP=False 也走它。"""
    chains = []
    for i, z in enumerate(zz):
        if i and z["kind"] == "扩展":
            chains[-1].append(z)
        else:
            chains.append([z])
    one = lambda z: dict(DD=z["DD"], GG=z["GG"], n=1, X0=z["X0"], X1=z["X1"])
    units = []
    for ch in chains:
        if len(ch) == 1:
            units.append(one(ch[0]))
            continue
        if done is None or not _D3_REGROUP:
            units.append(dict(DD=min(z["DD"] for z in ch), GG=max(z["GG"] for z in ch), n=len(ch),
                              X0=ch[0]["X0"], X1=max(z["X1"] for z in ch)))
            continue
        hz = None if (_D3_LIVE_TAIL and ch[-1]["live"]) else _regroup(done, ch[0]["PI0"], ch[-1]["PI1"])
        if hz is None:
            units += [one(z) for z in ch]
            continue
        inside = [z for z in ch if z["PI0"] <= hz["e"]]
        units.append(dict(DD=hz["DD"], GG=hz["GG"], ZD=hz["ZD"], ZG=hz["ZG"], n=max(2, len(inside)),
                          X0=done[hz["a"]]["i0"], X1=done[hz["e"]]["i1"]))
        units += [one(z) for z in ch if z["PI0"] > hz["e"]]
    return units


def _trend_of(units):
    """单元依次同向、波动区间互不重叠 ⇒ 上涨／下跌；否则 None。"""
    rel = {"上" if v["DD"] > u["GG"] else "下" if v["GG"] < u["DD"] else "叠" for u, v in zip(units, units[1:])}
    if rel == {"上"}:
        return "上涨"
    if rel == {"下"}:
        return "下跌"
    return None


def classify(zz, reading="A", done=None):
    """D3-3：一段走势的类型 → (类型, 升级?)。reading ∈ A（整段升一级，只数合成中枢；小栋 10-07 07:04Z 定 A）/ B（合成中枢留在本级别一起数）。"""
    units = _units(zz, done)
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


def _layer(done, ks, reading, n):
    """分界 ks 定了以后的那一层：中枢（含 D6 两遍）、段型（D3）、合成框 → (segments, units_out, centers_out, kinds0)。"""
    zs = _centers_with_cuts(done, ks)
    edges = [0] + ks + [len(done)]
    # ★ L24:84-85（card-40f4ce13，小栋 10-07 选 A）：「如果是向上的走势，里面的中枢一定是下-上-下的，向下的相反」。
    #   走势方向靠中枢判，中枢又要看走势方向 ⇒ 两遍、不回头（Atlas 10-07 spec 写法）：
    #   ① 分界（find_bounds）和每段的段型都用**不加限制**的中枢先算一遍，冻住；
    #   ② 只在第一遍判成上涨／下跌的段里按方向重找中枢（上涨段的框从向下那条起，下跌段反过来）。
    #      豁免（L45:122-124）：前一走势段（第一遍）是反向的 ⇒ 段内第一个框不限。图头那段不限（前面是什么不知道）；
    #   ③ 段型用第二遍的中枢重分一次 —— 不再回头改分界、不再重新决定限不限。
    #   ★ 所以 D4「同一套中枢既画框又判分界」在上涨／下跌段里不再成立：分界和 bounds[].ZD／ZG 用的是第一遍。
    kinds0 = [classify([z for z in zs if a <= z["PI0"] < b], reading, done) for a, b in zip(edges, edges[1:])]
    # ★ D6 只管**本级别**的上涨／下跌（Nova 10-07 08:00Z，card-0374e640-127）：含合成框的段（升级·上涨／下跌）
    #   不是本级别走势（D3-3 一A），不限方向；首中枢豁免里「前一段是反向趋势」也只认本级别的，升级·趋势不算。
    base = lambda k: kinds0[k][0] if (kinds0[k][0] in ("上涨", "下跌") and not (_D6_BASE_ONLY and kinds0[k][1])) else None
    if _DIR_RULE:
        grouped = []
        for g, (a, b) in enumerate(zip(edges, edges[1:])):
            last = g == len(edges) - 2
            if g and base(g):
                opp = "下跌" if base(g) == "上涨" else "上涨"
                grouped += _group_centers(done, a, b, g, last, start_dir="down" if base(g) == "上涨" else "up",
                                          free_first=base(g - 1) == opp)
            else:
                grouped += _group_centers(done, a, b, g, last)
        zs = classify_relations(grouped)
        for z in zs:
            z.pop("seg", None)
    segments, units_out, centers_out = [], [], []
    for g, (a, b) in enumerate(zip(edges, edges[1:])):
        zz = [z for z in zs if a <= z["PI0"] < b]
        centers_out += [dict(z, seg=g) for z in zz]
        kind, upgraded = classify(zz, reading, done)
        last = g == len(edges) - 2
        segments.append(dict(i0=0 if g == 0 else done[a - 1]["i1"], i1=n - 1 if last else done[b - 1]["i1"],
                             type=kind, upgraded=upgraded, head=g == 0, live=last, n_centers_level=len(zz)))
        units_out += [dict(u, seg=g) for u in _units(zz, done) if u["n"] > 1]
    assert len(centers_out) == len(zs)                # 每个中枢恰好属于一段（PI0 落在组内）
    return segments, units_out, centers_out


_D28 = True                                       # 只给 trend_check --self-test 的探针关：大盘整后接本级别趋势不切（D2-8）


def _d28_cuts(done, ks, segments, units, centers):
    """D2-8（card-22888623-1a7，小栋 08:45Z 要切，Nova 08:49Z 定落法 (b)）：一段里有合成出来的高一级中枢 U；
    U 后面先是还跟 U 重叠的本级别中枢（仍在大一级盘整里），再往后有一串 ≥2 个本级别中枢依次同向、互不重叠（按 DD～GG），
    而且这串第一个跟 U、也跟前面那些还在盘整里的中枢都不重叠 ⇒ 这串是一段本级别趋势，在中间补一刀，切成『升级·盘整』＋『趋势』。
    切点＝盘整最后一个中枢结束到趋势第一个中枢开始之间、逆着趋势方向的那个线段端点里最极端的（向上取最低，一样低取后一个）。
    确立＝趋势那串第二个中枢成立、跟第一个不重叠的那一刻（编者口径）；那以前这段照 D3-3 读。
    → [dict(j, kind, line_seg_confirm, U)]：j ＝ 切点所在的已完成线段下标（刀落在 done[j] 终点、新组从 j+1 起）。"""
    ov = lambda x, y: not (x["DD"] > y["GG"] or x["GG"] < y["DD"])
    out = []
    edges = [0] + ks + [len(done)]
    for g, (a, b) in enumerate(zip(edges, edges[1:])):
        us = [u for u in units if u["seg"] == g]
        if not us:
            continue                                  # 没有合成框的段不走这条（L29:39-41：盘整的中枢级别要更高）
        U = us[-1]
        zz = sorted((z for z in centers if z["seg"] == g and z["X0"] >= U["X1"]), key=lambda z: z["X0"])
        k = 0
        while k < len(zz) and ov(zz[k], U):
            k += 1
        pan, tr = zz[:k], zz[k:]
        if len(tr) < 2:
            continue
        up = tr[1]["DD"] > tr[0]["GG"]
        if not up and not tr[1]["GG"] < tr[0]["DD"]:
            continue                                  # 头两个就重叠：不是趋势
        run = [tr[0]]
        for z in tr[1:]:
            if (z["DD"] > run[-1]["GG"]) if up else (z["GG"] < run[-1]["DD"]):
                run.append(z)
            else:
                break
        if any(ov(run[0], x) for x in [U] + pan):
            continue
        x0 = pan[-1]["X1"] if pan else U["X1"]
        x1 = run[0]["X0"]
        cand = [q for q in range(a, b - 1) if x0 <= done[q]["i1"] <= x1 and (done[q]["dir"] == "down") == up]
        if not cand:
            continue
        j = min(cand, key=lambda q: (done[q]["p1"], -q)) if up else max(cand, key=lambda q: (done[q]["p1"], q))
        if not (a < j + 1 < b):
            continue
        out.append(dict(j=j, kind="L" if up else "H", confirm=run[1]["PI0"] + 2, U=U))
    return out


def trend_v3(r, reading="A", regroup=True, alternate=True, check_empty=True, no_exceed=True, standardize=True):
    """→ dict(seg_centers, bounds, retracted, pending, segments, units, reading)。
    seg_centers：按确立的分界切开重算的线段中枢（D4，前端画框就用它），每个带 seg（属于第几段走势，跟 segments 下标对齐）；
    segments：[dict(i0, i1, type, upgraded, head, live, n_centers_level)]，首尾相接盖满整张图；
      ★ n_centers_level 是**本级别**中枢个数，跟读法无关；读法 A 的升级段，字母挂在 units 上，个数不是它；
    units：D3 合成出来的高一级中枢（只列 n>1 的），带 seg，给前端画升级框；
    reading：这一跑用的 D3 读法（A／B），前端据此决定字母挂哪一级（spec §八 第 6 条）。
    bounds 里 D2-8 补的那一刀带 via="D2-8"（不是 D2-2 的反方向三类点确立的；相邻同类型只许出现在它两侧）。"""
    res = find_bounds(r, regroup=regroup, alternate=alternate, check_empty=check_empty, no_exceed=no_exceed,
                      standardize=standardize)
    done, ks = res["done"], list(res["ks"])
    n = len(r["bars"])
    if not done:
        return dict(seg_centers=[dict(z, seg=0) for z in r["seg_centers"]], bounds=[], retracted=[], pending=[],
                    units=[], reading=reading,
                    segments=[dict(i0=0, i1=n - 1, type="无中枢", upgraded=False, head=True, live=True,
                                   n_centers_level=0)])
    segments, units_out, centers_out = _layer(done, ks, reading, n)
    bounds = list(res["bounds"])
    if _D28:
        cuts = _d28_cuts(done, ks, segments, units_out, centers_out)
        if cuts:                                      # 补刀以后整层重算一次，不再回头找第二轮（同 D6 的「不回头」）
            for c in cuts:
                j = c["j"]
                ks.append(j + 1)
                bounds.append(dict(line_seg=j, bar=done[j]["i1"], kind=c["kind"], price=done[j]["p1"],
                                   pullback_line_seg=c["confirm"], pullback_end_bar=done[min(c["confirm"], len(done) - 1)]["i1"],
                                   ZD=c["U"].get("ZD", c["U"]["DD"]), ZG=c["U"].get("ZG", c["U"]["GG"]), via="D2-8"))
            ks.sort()
            bounds.sort(key=lambda b: b["bar"])
            segments, units_out, centers_out = _layer(done, ks, reading, n)
    return dict(seg_centers=centers_out, bounds=bounds, retracted=res["retracted"],
                pending=pending(done, ks, res["want"]), segments=segments, units=units_out, reading=reading)
