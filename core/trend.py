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
        只数合成出来的；读法 B：合成中枢留在本级别跟别的一起数（L17:255 后半句）。小栋 10-07 定 A（card-0374e640-127；走势分段.md 六之三）。

D2-5 死点类型（趋势背驰／盘整背驰／小转大／盘整·未见背驰／比不了；D2-8 补刀单列）：确立的分界上标 death＋death_why，只标注、不决定刀（_death_types，第四批 ①）。
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


_R6_B = True                                     # 只给 trend_check --self-test 的探针关：参照中枢退回读法 A（只取起点不晚于 H 的）
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
    zs = (_sl_centers_with_cuts if (SAME_LEVEL and SAME_LEVEL_D2) else _centers_with_cuts)(done[:t + 1], ks)
    # D2-2 第 1 步（R6＝B，小栋 10-08）：两类候选取最后一个 —— ① 起点不晚于 H；② 起点在 H 之后、最后一条线段不晚于 S[t-2]（离开段之前已走完）
    ref = [z for z in zs if z["PI0"] >= lo and (z["X0"] <= done[j]["i1"] or (_R6_B and z["PI1"] <= t - 2))]
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
                zz = (_sl_centers_with_cuts if (SAME_LEVEL and SAME_LEVEL_D2) else _centers_with_cuts)(done[:t + 1], ks + [j + 1])
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
            bounds.append(dict(rule="D2-2", line_seg=j, bar=done[j]["i1"], kind=typ, price=done[j]["p1"], pullback_line_seg=t,
                               pullback_end_bar=done[t]["i1"], ZD=z["ZD"], ZG=z["ZG"], ref_X0=z["X0"]))
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


def _layer(done, ks, bounds_, reading, n):
    """分界定了以后的那一层：中枢（D6-4 先限方向）、段型（D3）、合成框 → (segments, units_out, centers_out)。"""
    zs = _centers_with_cuts(done, ks)
    edges = [0] + ks + [len(done)]
    # ★ L24:84-85（card-40f4ce13）：上涨走势里的中枢只认下上下、下跌里只认上下上（D6）。
    #   ★ D4「同一套中枢既画框又判分界」在上涨／下跌段里不成立：分界和 bounds[].ZD／ZG 用不限方向的，画框用限方向的。
    # ★ D6-4（2026-10-07 09:16Z Nova 改，card-66a0fd73-b30；spec bd5872b）：段型**先按方向判**。
    #   图头以外每段：照这段的方向（从低点起 ⇒ 首段须向下；从高点起 ⇒ 首段须向上）限方向找中枢，豁免照 D6-2
    #   （前一段的最终段型是本级别反向趋势 ⇒ 段内第一个框不限）。这组中枢按 D3 判得出**同方向的本级别趋势**
    #   （上涨／下跌、不是升级段）⇒ 段型就是它、画框也用它；判不出 ⇒ 改用不限方向的中枢按 D3 判（盘整／升级·…）。
    #   为什么：先不限方向定段型，从极值出发的那一笔（连接段 a）会被吞成第一个中枢的首段，趋势被遮成盘整，D6 就不再限了。
    #   不打转：分界只用不限方向那一套（find_bounds），每段最多试两次、从左到右、不回头。
    bks = {b["line_seg"] + 1: b["kind"] for b in bounds_}
    grouped, final_kind = [], []
    for g, (a, b) in enumerate(zip(edges, edges[1:])):
        last = g == len(edges) - 2
        free = [z for z in zs if a <= z["PI0"] < b]
        pick = None
        if _DIR_RULE and g and bks.get(a) in ("L", "H"):
            want = "上涨" if bks[a] == "L" else "下跌"
            opp = "下跌" if want == "上涨" else "上涨"
            prev = final_kind[g - 1]
            cz = _group_centers(done, a, b, g, last, start_dir="down" if want == "上涨" else "up",
                                free_first=(prev[0] == opp and not prev[1]))
            cz = classify_relations(cz)
            k, up = classify(cz, reading, done)
            if k == want and not (_D6_BASE_ONLY and up):
                pick = cz
        if pick is None:
            pick = [dict(z, seg=g) for z in free]
        grouped += pick
        final_kind.append(classify(classify_relations([dict(z) for z in pick]), reading, done))
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


_DEATH = True                                     # 只给 trend_check --self-test 的探针关：分界不标死点类型（D2-5）
_DEATH_MATCH_CHECK = True                         # 只给 trend_check --self-test 的探针关：一买一卖跟刀 bar 对不上时不报


def _death_types(r, done, bounds, segments, centers):
    """D2-5（第四批 ①，Nova 10-08 14:09；口径照 agent/atlas/d25-a 169d63b，Nova 14:32 审过）：每个确立的分界标 death＋death_why，
    只标注、不动刀。D2-8 补的刀不进分类，标「D2-8 补刀」（靠中枢排布切的，不是背驰、也不是反方向三类点确立的）。
    其余按顺序取第一个成立的：
      ① 趋势背驰：引擎现有的一卖（H）／一买（L）正好落在这一刀（signals 线段级、默认看法 MACD 面积）；
      ② 盘整背驰：C＝刀所在线段；Z＝**C 离开的那个中枢**（C 之前最后一个走完的本级别中枢，C 不在它的成段里）；
         A＝进入 Z 的那条线段（Z 第一段之前紧挨着的那一条，L24 的 A、B、C）；C 比 A 创了更高（低）的点、C 的面积 < A 的面积；
      ①② 都比不了（找不到 Z／找不到 A／进入段跟 C 反向）⇒「比不了」，单独一类；没有一买一卖只说明 ① 不成立，照样接着比 ②；
      ①② 真比过、都不成立 ⇒ 前一段是本级别趋势（上涨／下跌、不是升级段）标「小转大」（L43：a+A+b+B+c），否则标「盘整·未见背驰」。
    centers：分界确立以后按刀切开重算的线段中枢（seg_centers）。原地写进 bounds，返回 bounds。"""
    from .signals import signals, macd_hist, _panzheng
    sig1 = [s for s in signals(r) if s["kind"] in ("一买", "一卖")]
    first = {(s["bar"], s["kind"]) for s in sig1}
    hist = macd_hist(r["bars"])
    pre = {sg["i1"]: sg for sg in segments}                # 刀 ⇒ 刀前那一段走势
    for b in bounds:
        if b.get("rule") == "D2-8":
            b["death"], b["death_why"] = "D2-8 补刀", "不分类（中枢排布切出来的）"
            continue
        if b.get("rule") == "S5":                      # 同级别：盘整接盘整的接缝（L38:19-20），不是背驰、也不是三类点确立的，不分类
            b["death"], b["death_why"] = "盘整相连", "不分类（同级别两个盘整的连接，L38:20；S12）"
            continue
        up = b["kind"] == "H"
        kind1 = "一卖" if up else "一买"
        if (b["bar"], kind1) in first:
            b["death"], b["death_why"] = "趋势背驰", kind1
            continue
        j = b["line_seg"]
        C = done[j]
        # ★ 一买／一卖落在刀所在的那条线段里、bar 却跟刀对不上（signals 用原始线段、分界用 D2-0 标准化后的线段，端点可能挪过）：
        #   不许悄悄降到 ②，挂 death_warn，trend_check 当违规报（Atlas 10-08 15:18 提，Nova 15:42 派）。分类照常往下走。
        if _DEATH_MATCH_CHECK:
            near = [x for x in sig1 if x["kind"] == kind1 and C["i0"] <= x["bar"] <= C["i1"]]
            if near:
                b["death_warn"] = "%s 在 bar %d，落在刀所在线段里，跟刀 bar %d 对不上" % (kind1, near[0]["bar"], b["bar"])
        zs = [z for z in centers if z["PI1"] < j]
        fill = ""                                      # D2-5 补位（读法-D2-5，Nova 06:43 定优先级 -1→-2→-3→-4）
        if not zs:
            # -3：找不到 Z，但 C 跟往前两条三段重叠 ⇒ 拿 C 跟往前第二条比
            if D25_FILL >= 3 and j >= 2 and max(done[q]["lo"] for q in (j - 2, j - 1, j)) <= min(done[q]["hi"] for q in (j - 2, j - 1, j)):
                A, fill = done[j - 2], "（-3 补位：无 Z，C 与前两条重叠，比 C 往前第二条）"
            else:
                b["death"], b["death_why"] = "比不了", "找不到 Z"
                continue
        else:
            z = zs[-1]
            k0 = z["PI0"]
            A = done[k0 - 1] if k0 > 0 else None
            if A is None or _is_up(A) != up:
                # -2：进入段反向或找不到 ⇒ C 往前第二条（必跟 C 同向），条件是它属于 Z
                if D25_FILL >= 2 and j >= 2 and z["PI0"] <= j - 2 <= z["PI1"]:
                    A, fill = done[j - 2], "（-2 补位：进入段%s，比 C 往前第二条 Ai／Ai+2）" % ("反向" if A is not None else "找不到")
                else:
                    b["death"], b["death_why"] = "比不了", ("进入段反向" if A is not None else "找不到 A")
                    continue
        newx = (C["p1"] > A["p1"]) if up else (C["p1"] < A["p1"])
        if _panzheng(A, C, not up, hist):              # 盘整背驰的判法跟 M29 共用一份（signals._panzheng）
            b["death"], b["death_why"] = "盘整背驰", "C 创新%s、面积小于 A" % ("高" if up else "低") + fill
            continue
        why = ("C 没创新%s" % ("高" if up else "低") if not newx else "C 面积不小于 A") + fill
        sg = pre.get(b["bar"])
        trend = sg is not None and sg["type"] in ("上涨", "下跌") and not sg["upgraded"]
        b["death"], b["death_why"] = ("小转大" if trend else "盘整·未见背驰"), why + ("" if trend else "；前一段是%s" % (
            (sg["type"] + ("·升" if sg["upgraded"] else "")) if sg else "？"))
    return bounds


D25_FILL = 3                                      # D2-5 补位（读法-D2-5，Atlas 27e714a，Nova 06:43 定优先级）：0＝现行（进入段反向即「比不了」）；
                                                  #   2＝加 -2（进入段反向／找不到 ⇒ 比 C 往前第二条，须属于 Z）；3＝再加 -3（找不到 Z 但 C 与前两条重叠）。只改标注


_XZD_SECOND = True                                # 只给自检反向臂关：小转大的刀不出二类


def _xzd_seconds(done, bounds, r=None):
    """L53「但在小级别转大级别的情况下，第二类买卖点就是最佳的，因为在这种情况下，没有该级别的第一类买卖点」（买卖点.md:106，第四批）。
    位置照 L53 正文「从高点一个次级别走势向下后接着一个次级别走势向上，如果不创新高或盘整背驰，都构成第二类卖点」：
    D2-5 标了小转大的 D2-2 刀，**刀之后紧接的两段**（done[j+1]、done[j+2]），第二段的终点不创新低（新高），或者创新了但对刀前那段
    （done[j]，三段的第一段，L27）有盘整背驰，才出二类；判法跟 M29 共用 signals._panzheng。
    ★ 不是 D2-2 确立用的那对离开段／回抽段：那一对可能隔得很远（ZEC 451.54：15m 隔 8 段、30m 隔 12 段），Bram 10-08 16:24 的前后图看出来的。
    ★ 放在走势层、单独一个键，**不进 core/signals.py**：J12（买卖点.md 八.5″）要 signals 不读分界。"""
    from .signals import _panzheng, macd_hist
    hist = macd_hist(r["bars"]) if r is not None else None
    out = []
    for b in bounds:
        if b.get("death") != "小转大" or b.get("rule") != "D2-2":
            continue
        j = b["line_seg"]
        if j + 2 >= len(done):
            continue                                   # 第二段还没走完
        A, s2 = done[j], done[j + 2]
        down = b["kind"] == "L"
        newx = (s2["p1"] < b["price"]) if down else (s2["p1"] > b["price"])
        if not newx:
            why = "小转大"
        elif hist is not None and _panzheng(A, s2, down, hist):
            why = "小转大·创新低＋盘整背驰" if down else "小转大·创新高＋盘整背驰"
        else:
            continue
        out.append(dict(kind="二买" if down else "二卖", bar=s2["i1"], price=s2["p1"], confirmed=True,
                        level="seg", why=why, from_bar=b["bar"]))   # weak 10-09 下线：创新低与否从 why 读（signals.newx）
    # ★ 不带 known_bar（Nova 10-08 16:41 指出 pullback_end_bar 也是事后才认出来的，实时还要晚一截）：
    #   这颗点「哪一根才知道」只能逐根截断重放才量得准（trend_check ④′），每次请求都重放太贵；回放／回测本来就是逐根截断，
    #   点会在刀实时确立的那一根自然出现，不需要这个字段。
    return out



# ---------------------------------------------------------------- R-1 同级别分解（正式版开关，合并前最后一笔才翻默认；上线清单 docs/spec/同级别正式版-上线清单.md；docs/spec/读法-R1-分解方式.md S1～S6）
SAME_LEVEL = True                                # R-1 同级别分解：小栋 10-09 定 A→B（正式版，跟 ①D、S-13 一起上）。正式版取值 True；
                                                  #   现在默认关只为合并前 G1(a)「关掉跟 main 逐份同」，翻默认放合并前最后一笔
SAME_LEVEL_OVERLAP = "ZDZG"                       # S3 相邻中枢判重叠用 [ZD,ZG]（编者口径，上线清单 #2：只剩这一个可行）；DDGG 只留作量数对照
SAME_LEVEL_D6 = "fallback"                              # R-6 ③ 甲在同级别下（小栋 10-09 06:17 定）：正式版取值 "fallback"＝分界之后的组中枢首段须跟走势反向，
                                                  #   判不出同方向趋势就退回不限方向（D6-4）；"strict" 只留作量数对照；None＝不限方向（旧量数口径）
SL_FIRST_EXEMPT = True                           # 甲S-2（读法-R3R6 一·6，Atlas f3fac3c）：前一个走势段是本级别反向趋势 ⇒ 这一段第一个中枢不受限
                                                  #   （首中枢可以从同向那条起）。正式版取值 True。乙′（R6_YI_PRIME／R6_YI_FALLBACK）R-6 定甲以后删了，见 2ba3fbd
D2_ALTERNATE = True                               # D-0 分界一高一低交替（D2-3，小栋 10-09 06:36 定 A 保留）；只给出图／量数关：等同 trend_v3(alternate=False)
SAME_LEVEL_DEATH = True                          # 同级别下照标死点类型（D2-5 按三段中枢）、出小转大的二类（S11）、S5 标「盘整相连」（S12）。正式版取值 True
SAME_LEVEL_D2 = True                             # S9：D2 的参照中枢也换成同级别三段中枢（R-1＝B「完整同级别」）。正式版取值 True


def _sl_centers(done, a, b, first_up=None, first_free=False):
    """S1＋S2：done[a..b) 里从左往右找三段重叠，满三段即收、不延伸；下一个从这三段之后起，段不共用。
    first_up 给了（R-6 甲，D6）：中枢首段的方向必须是它（上涨段里 first_up=False，即下上下）。"""
    out, k = [], a
    while k + 2 < b:
        if first_up is not None and _is_up(done[k]) != first_up and not (first_free and not out):
            k += 1
            continue
        lo = max(done[q]["lo"] for q in range(k, k + 3))
        hi = min(done[q]["hi"] for q in range(k, k + 3))
        if lo <= hi:
            out.append(dict(PI0=k, PI1=k + 2, X0=done[k]["i0"], X1=done[k + 2]["i1"], ZD=lo, ZG=hi,
                            DD=min(done[q]["lo"] for q in range(k, k + 3)), GG=max(done[q]["hi"] for q in range(k, k + 3)),
                            nZ=3, live=False, kind="—", rel="—", status="已确认", status_note="—", term="—",
                            npens=None, F1=done[k + 1]["i1"]))
            k += 3
        else:
            k += 1
    return out


def _sl_rel(z1, z2):
    """S3：两个本级别中枢 → "叠"／"上"／"下"。区间照 SAME_LEVEL_OVERLAP。"""
    lo, hi = ("ZD", "ZG") if SAME_LEVEL_OVERLAP == "ZDZG" else ("DD", "GG")
    if z2[lo] > z1[hi]:
        return "上"
    if z2[hi] < z1[lo]:
        return "下"
    return "叠"


def _sl_centers_with_cuts(done, ks):
    """S9：同 _centers_with_cuts，但每组里找的是同级别三段中枢（S1＋S2）。"""
    edges = [0] + list(ks) + [len(done)]
    out = []
    for a, b in zip(edges, edges[1:]):
        out += _sl_centers(done, a, b)
    return out
def _sl_state(bars, bounds, two_sets, chosen):
    """①D（读法-①D，Nova 10-09 定）：同级别下每把刀标 state ＝ "pending"／"confirmed"，只看当前这一份 K 线，不记历史。
    D-2‴／D-2⁗：D2 刀 b（低点刀为例）——b 之后到当前最后一根的最高点 e（持平取最早那根），上界 ＝ min(e, 下一把 D2)。
          下一把 D2 **已确认** ⇒ 这一组封死（它不撤、线段层有锁＋甲不变），甲 fallback 不会再翻 ⇒ 实际选中那套（chosen）里
          有一个中枢整个落在 [b, 上界] 就确认（D-2⁗）；否则甲的两套中枢（限形状、不限形状，two_sets）里**各有**一个才确认（D-2‴），
          D6-4 往哪边翻都还在，不回翻。高点刀对称取最低点。b′ 只会落在 e 或更晚更极端的点上 ⇒ D2-7 撤不了 b。
          从右往左算：先定下一把的 state。
    D-4′：S5 刀确认 ⇔ 左右两把 D2 刀都已确认（右边那把待确认时会被撤，撤了 S5 就翻回去）。
    25 张前缀回放（定稿口径＋PEN_FINAL_LOCK）：确认后消失 D2 0／S5 0，确认回翻 D2 0／S5 0；D2 确认 84、S5 78（跟不防回翻时一样多），
    图尾待确认 0，延迟中位 0、最大 1564（只有 D-2‴ 时 78／70／图尾 6／最大 1159）。
    （试过作废的：只用 D-2′ 回翻 2／3；等最后一组 fallback 定、要求两套同一个中枢、F1 头 4 条定 a——见读法-①D 四之七。）"""
    n = len(bars)
    d2 = [b for b in bounds if b.get("rule") == "D2-2"]
    for i in range(len(d2) - 1, -1, -1):                    # 从右往左：D-2⁗ 要先知道下一把 D2 确认没有
        b = d2[i]
        hi = d2[i + 1]["bar"] if i + 1 < len(d2) else n      # 跟回放 dreplay3 同一判据：中枢也不越过下一把 D2 刀
        lo = b["bar"] + 1
        if lo >= n:
            b["state"] = "pending"
            continue
        key = (lambda q: bars[q]["h"]) if b["kind"] == "L" else (lambda q: -bars[q]["l"])
        e = max(range(lo, n), key=lambda q: (key(q), -q))
        sets = [chosen] if (i + 1 < len(d2) and d2[i + 1]["state"] == "confirmed") else two_sets   # D-2⁗
        ok = all(any(z["X0"] >= b["bar"] and z["X1"] <= min(hi, e) for z in zs) for zs in sets)
        b["state"] = "confirmed" if ok else "pending"
    for b in bounds:
        if b.get("rule") != "S5":
            continue
        left = [x for x in d2 if x["bar"] < b["bar"]]
        right = [x for x in d2 if x["bar"] > b["bar"]]
        b["state"] = "confirmed" if left and right and left[-1]["state"] == "confirmed" and right[0]["state"] == "confirmed" \
            else "pending"


# P（Nova 10-09 18:29，待小栋在合并页拍）：S5 的原文前提是「当成两个盘整的连接」（L38:19-21），而 L43:9 明说「不允许
#   上涨+上涨、下跌+下跌」。切完以后两边要是都判成同向趋势，这一刀的前提就不成立 ⇒ 不切，两截并成一段（只并同一个 D2 组里、
#   S5 接缝两边的；D2 分界两边不动）。并完再看下一个接缝，直到组里没有相邻的同向趋势。关掉 ⇒ 跟落地支 60c72a4 一字不差。
S5_NO_SAME_TREND = True


def _sl_layer(done, ks, bounds_, n):
    """S3～S6：分界照 D2 定的组，每组里按同级别中枢再切：相邻两个中枢重叠，或者不重叠但方向跟这一截的趋势相反
    ⇒ 前一个中枢第三段的终点再切一刀（S5，盘整＋盘整）。每一截：0 个中枢＝无中枢，1 个＝盘整，≥2 个依次同向不重叠＝上涨／下跌。
    不升级、不合成（S6）。→ (segments, centers_out, extra_bounds)"""
    edges = [0] + list(ks) + [len(done)]
    pieces = []                                    # (起 done 下标, 止 done 下标（不含）, [中枢])
    extra = []
    bk = {x["line_seg"] + 1: x["kind"] for x in bounds_}
    two_sets = ([], [])                            # D-2‴：(限形状那套, 不限形状那套) 的中枢，没走 D6 的组两边都放同一份
    def kind_of(zz):
        return "无中枢" if not zz else "盘整" if len(zz) == 1 else ("上涨" if _sl_rel(zz[0], zz[1]) == "上" else "下跌")
    for g, (a, b) in enumerate(zip(edges, edges[1:])):
        zz = _sl_centers(done, a, b)
        exempt = False
        if SL_FIRST_EXEMPT and g and bk.get(a) in ("L", "H") and pieces:
            exempt = kind_of(pieces[-1][2]) == ("下跌" if bk[a] == "L" else "上涨")
        if SAME_LEVEL_D6 and g and bk.get(a) in ("L", "H"):
            want_up = bk[a] == "L"                       # 从低点起 ⇒ 上涨 ⇒ 中枢首段向下（下上下）
            zr = _sl_centers(done, a, b, first_up=not want_up, first_free=exempt)
            ok = len(zr) >= 2 and _sl_rel(zr[0], zr[1]) == ("上" if want_up else "下")
            two_sets[0].extend(zr); two_sets[1].extend(zz)
            if SAME_LEVEL_D6 == "strict" or ok:
                zz = zr
        else:
            two_sets[0].extend(zz); two_sets[1].extend(zz)
        start, cur, way = a, [], None
        for z in zz:
            if cur:
                r = _sl_rel(cur[-1], z)
                if r == "叠" or (way and r != way):
                    cut = cur[-1]["PI1"] + 1
                    pieces.append((start, cut, cur, g))
                    e = done[cut - 1]
                    extra.append(dict(rule="S5", line_seg=cut - 1, bar=e["i1"], kind="H" if e["p1"] >= e["p0"] else "L",
                                      price=e["p1"]))
                    start, cur, way = cut, [], None
                elif way is None:
                    way = r
            cur.append(z)
        pieces.append((start, b, cur, g))
    if S5_NO_SAME_TREND:
        pieces, extra = _merge_same_trend(pieces, extra, kind_of)
    segments, centers_out = [], []
    for g, (a, b, zz, _grp) in enumerate(pieces):
        last = g == len(pieces) - 1
        if not zz:
            kind = "无中枢"
        elif len(zz) == 1:
            kind = "盘整"
        else:
            kind = "上涨" if _sl_rel(zz[0], zz[1]) == "上" else "下跌"
        centers_out += [dict(z, seg=g) for z in zz]
        segments.append(dict(i0=0 if a == 0 else done[a - 1]["i1"], i1=n - 1 if last else done[b - 1]["i1"],
                             type=kind, upgraded=False, head=a == 0, live=last, n_centers_level=len(zz)))
    return segments, centers_out, extra, two_sets


def _merge_same_trend(pieces, extra, kind_of):
    """P：同一个 D2 组里，S5 接缝两边都是同向趋势（上涨+上涨／下跌+下跌）⇒ 去掉这一刀，两截并成一段；并完接着看，直到没有。
    pieces：[(起, 止, 中枢, 组号)]；extra：S5 刀（line_seg = 接缝前那条线段 = 前一截的止 − 1）。"""
    out = list(pieces)
    gone = set()
    k = 0
    while k + 1 < len(out):
        (a0, b0, z0, g0), (a1, b1, z1, g1) = out[k], out[k + 1]
        t0, t1 = kind_of(z0), kind_of(z1)
        if g0 == g1 and t0 == t1 and t0 in ("上涨", "下跌"):
            gone.add(b0 - 1)
            out[k:k + 2] = [(a0, b1, z0 + z1, g0)]
            continue                                  # 并完的这一截再跟下一截比
        k += 1
    return out, [x for x in extra if x["line_seg"] not in gone]


def trend_v3(r, reading="A", regroup=True, alternate=True, check_empty=True, no_exceed=True, standardize=True):
    """→ dict(seg_centers, bounds, retracted, pending, segments, units, reading)。
    seg_centers：按确立的分界切开重算的线段中枢（D4，前端画框就用它），每个带 seg（属于第几段走势，跟 segments 下标对齐）；
    segments：[dict(i0, i1, type, upgraded, head, live, n_centers_level)]，首尾相接盖满整张图；
      ★ n_centers_level 是**本级别**中枢个数，跟读法无关；读法 A 的升级段，字母挂在 units 上，个数不是它；
    units：D3 合成出来的高一级中枢（只列 n>1 的），带 seg，给前端画升级框；
    reading：这一跑用的 D3 读法（A／B），前端据此决定字母挂哪一级（spec §八 第 6 条）。"""
    alternate = alternate and D2_ALTERNATE
    res = find_bounds(r, regroup=regroup, alternate=alternate, check_empty=check_empty, no_exceed=no_exceed,
                      standardize=standardize)
    done, ks = res["done"], res["ks"]
    n = len(r["bars"])
    if not done:
        return dict(seg_centers=[dict(z, seg=0) for z in r["seg_centers"]], bounds=[], retracted=[], pending=[],
                    units=[], reading=reading,
                    segments=[dict(i0=0, i1=n - 1, type="无中枢", upgraded=False, head=True, live=True,
                                   n_centers_level=0)])
    bounds = list(res["bounds"])
    ks = list(ks)
    if SAME_LEVEL:                               # R-1 试验：同级别分解（默认关）。不升级、不补 D2-8、不标死点类型
        segments, centers_out, extra, two_sets = _sl_layer(done, ks, bounds, n)
        bounds = sorted(bounds + extra, key=lambda x: x["bar"])
        if _DEATH and SAME_LEVEL_DEATH:                  # 正式版：同级别下照标死点类型（D2-5 按三段中枢）、小转大的二类（S11）
            _death_types(r, done, bounds, segments, centers_out)
        _sl_state(r["bars"], bounds, two_sets, centers_out)
        return dict(seg_centers=centers_out, bounds=bounds, retracted=res["retracted"],
                    pending=pending(done, ks, res["want"]), segments=segments, units=[], reading="same_level",
                    xzd_seconds=_xzd_seconds(done, bounds, r) if (_DEATH and SAME_LEVEL_DEATH and _XZD_SECOND) else [],
                    moved=res.get("moved", []))
    segments, units_out, centers_out = _layer(done, ks, bounds, reading, n)
    if _D28:
        cuts = _d28_cuts(done, ks, segments, units_out, centers_out)
        if cuts:                                      # 补刀以后整层照 D4／D6-4 重算一次，不回头找第二轮
            ks2, b2 = list(ks), list(bounds)
            for c in cuts:
                j = c["j"]
                ks2.append(j + 1)
                b2.append(dict(line_seg=j, bar=done[j]["i1"], kind=c["kind"], price=done[j]["p1"],
                               pullback_line_seg=c["confirm"], pullback_end_bar=done[min(c["confirm"], len(done) - 1)]["i1"],
                               ZD=c["U"].get("ZD", c["U"]["DD"]), ZG=c["U"].get("ZG", c["U"]["GG"]), ref_X0=c["U"]["X0"], rule="D2-8"))
            ks2.sort()
            b2.sort(key=lambda x: x["bar"])
            s2, u2, c2 = _layer(done, ks2, b2, reading, n)
            # 自检兜底（Nova 09:15Z）：补刀以后那一截照 D6-4 重判，得是同方向的本级别趋势（不是升级段），否则不切
            ok = all(next(sg for sg in s2 if sg["i0"] == done[c["j"]]["i1"]) for c in cuts) and all(
                (lambda sg: sg["type"] == ("上涨" if c["kind"] == "L" else "下跌") and not sg["upgraded"])(
                    next(sg for sg in s2 if sg["i0"] == done[c["j"]]["i1"])) for c in cuts)
            if ok:
                ks, bounds, segments, units_out, centers_out = ks2, b2, s2, u2, c2
    if _DEATH:
        _death_types(r, done, bounds, segments, centers_out)
    return dict(seg_centers=centers_out, bounds=bounds, retracted=res["retracted"],
                pending=pending(done, ks, res["want"]), segments=segments, units=units_out, reading=reading,
                xzd_seconds=_xzd_seconds(done, bounds, r) if (_DEATH and _XZD_SECOND) else [])
