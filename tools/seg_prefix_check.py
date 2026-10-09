#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""线段「已确认段只增不撤」检查：每份 K 线样本，笔序列逐笔加长，build_segments 的已确认段必须只往后长、不撤销。

    python3 tools/seg_prefix_check.py             # data/ 下全部样本，撤销数必须为 0（rc=0）
    python3 tools/seg_prefix_check.py --fuzz 4000 # 随机 4000 组逐笔加长（先不进 predeploy，见 fuzz()）
    python3 tools/seg_prefix_check.py --self-test # 反向验证：喂一个故意会撤销的划段函数，必须报出来（rc=0 ＝ 报出来了）
    python3 tools/seg_prefix_check.py --bars      # K 线前缀档：跟线上一样按 K 线往后长、尾笔不定稿；撤销数必须正好是 BAR_EXPECT

为什么要它（card-753bd03a，Nova 10-06 定为合并条件）：
  · Pine 的 ③ 逐根续扫（chanlun.pine::zSegStep）押的就是这条 —— 已确认段一旦被后来的笔撤销，逐根版就跟整段版不一样；
  · L78 待定改判第一版把「反向线段走完」界在它最后一笔（应为被确认那一笔），其余检查全绿，
    只有这条在 zec15 第 836 笔报了一次撤销 —— 那一版还据此误报了 1h 的分界变化。
main 0760562 上全部样本撤销 0。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from core.analyze import analyze                              # noqa: E402
from core.segment import build_segments                       # noqa: E402
from trend_check import load, kline_files                     # noqa: E402
from config import tick_of                                    # noqa: E402


def revocations(pens, build=build_segments):
    """→ [(第几笔加进来时, 被撤销的段 (PI0, PI1))]"""
    out, prev = [], []
    for n in range(3, len(pens) + 1):
        cur = [(s["PI0"], s["PI1"]) for s in build(pens[:n]) if not s.get("live")]
        if cur[:len(prev)] != prev:
            k = next((t for t, (a, b) in enumerate(zip(prev, cur)) if a != b), len(cur))
            out.append((n, prev[k]))
        prev = cur
    return out


def _confirmed(build, pens):
    return [(s["PI0"], s["PI1"]) for s in build(pens) if not s.get("live")]


def revocations_range(pens, lo, hi, build=build_segments):
    """revocations 的一段：只看第 lo..hi−1 笔加进来时。起点那一份「上一个前缀」现算（lo>3 时是 pens[:lo−1]），
    所以把 [3, len+1) 切成几段各跑一遍再按序拼起来，跟 revocations 整串跑**逐条相同**（自检 ③ 钉这一条）。"""
    out = []
    prev = _confirmed(build, pens[:lo - 1]) if lo > 3 else []
    for n in range(lo, hi):
        cur = _confirmed(build, pens[:n])
        if cur[:len(prev)] != prev:
            k = next((t for t, (a, b) in enumerate(zip(prev, cur)) if a != b), len(cur))
            out.append((n, prev[k]))
        prev = cur
    return out


def cuts(n_pens, parts):
    """把前缀 [3, n_pens] 切成 parts 段，**按工作量切**。实测第 n 个前缀划一遍的工夫约 ∝ n²（不是 n：按 n² 累计切的 4 片，
    zec15 实测 37／61／82／91 秒），累计 ∝ n³ ⇒ 按 n³ 等分。"""
    lo, hi = 3, n_pens + 1
    if parts <= 1 or hi - lo < 2 * parts:
        return [(lo, hi)]
    edges = [lo] + [int(round((lo ** 3 + (hi ** 3 - lo ** 3) * k / parts) ** (1 / 3))) for k in range(1, parts)] + [hi]
    edges = sorted(set(edges))
    return list(zip(edges, edges[1:]))


def _job(args):
    pens, lo, hi = args
    return revocations_range(pens, lo, hi)


JOBS = int(os.environ.get("SEG_PREFIX_JOBS", "4"))   # 子进程数；1 ＝ 跟原来一样整串跑（对拍用）


def main():
    """★ 10-08 起按前缀区间切片、多进程跑（card-b71b1600-253）：zec15 1581 笔一张整串要 258 秒（平方级），整门 306 秒里的大头。
    切片跟整串**逐条相同**（revocations_range 的文档；SEG_PREFIX_JOBS=1 就是原来的整串跑，两种跑法的输出逐字节对拍过）。"""
    items = [(fn, analyze(load(os.path.join(ROOT, "data", fn)), tick=tick_of(fn))["pens"]) for fn in kline_files()]
    for fn in ("aaplusdt_1h_headdir.json", "zecusdt_4h_headext.json"):   # 图头那两条修法的线上夹具（card-24dd71cb／card-2783fa1f）
        bars = json.load(open(os.path.join(HERE, "fixtures", fn)))
        items.append(("fixtures/" + fn, analyze([dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"]) for b in bars], tick=tick_of(fn))["pens"]))
    fz = json.load(open(os.path.join(HERE, "fixtures", "headfuzz_pens.json")))["seeds"]   # 直接是笔（Atlas 的随机反例）
    items += [("fixtures/headfuzz_pens.json seed %s" % sd, pens) for sd, pens in fz.items()]
    # 每张按工作量切成若干片（大图多切，小图一片），所有片进同一个进程池 ⇒ 长的那张不会拖住别的
    total = sum(len(p) ** 3 for _, p in items) or 1
    tasks = []
    for k, (name, pens) in enumerate(items):
        parts = max(1, round(JOBS * 8 * len(pens) ** 3 / total)) if JOBS > 1 else 1   # 切细（每路约 8 片）：片数少了尾巴不齐，实测 2 片/路只快一倍
        tasks += [(k, lo, hi) for lo, hi in cuts(len(pens), parts)]
    tasks.sort(key=lambda t: -(t[2] ** 3 - t[1] ** 3))        # 大片先发
    if JOBS > 1:
        import concurrent.futures as cf
        with cf.ProcessPoolExecutor(max_workers=JOBS) as ex:
            res = list(ex.map(_job, [(items[k][1], lo, hi) for k, lo, hi in tasks]))
    else:
        res = [_job((items[k][1], lo, hi)) for k, lo, hi in tasks]
    got = {}
    for (k, lo, _), rv in zip(tasks, res):
        got.setdefault(k, []).append((lo, rv))
    bad = 0
    for k, (name, pens) in enumerate(items):
        rv = [x for _, part in sorted(got.get(k, [])) for x in part]
        bad += len(rv)
        print("%s %s %d 笔 撤销 %d %s" % ("✓" if not rv else "✗", name, len(pens), len(rv), rv[:2] if rv else ""))
    print("全部通过（已确认段只增不撤）" if not bad else "%d 处撤销" % bad)
    return 1 if bad else 0


def self_test():
    """反向验证：一个「笔数是 7 的倍数时把最后一个已确认段扔掉」的划段函数 ⇒ 必须报撤销。"""
    def flaky(pens):
        segs = build_segments(pens)
        done = [s for s in segs if not s.get("live")]
        return done[:-1] if done and len(pens) % 7 == 0 else segs
    fn = "zec_1h.json"
    pens = analyze(load(os.path.join(ROOT, "data", fn)), tick=tick_of(fn))["pens"]
    rv = revocations(pens, flaky)
    print("%s 故意撤销的划段函数（%s）⇒ 报出 %d 处" % ("✓" if rv else "✗", fn, len(rv)))
    # 图头那一条拿掉 cutoff（判 ① 型等到反向段确认）⇒ Atlas 的两组随机反例必须报撤回（card-2783fa1f-da8）
    import core.segment as SG
    fz_all = json.load(open(os.path.join(HERE, "fixtures", "headfuzz_pens.json")))["seeds"]
    fz = {sd: p for sd, p in fz_all.items() if sd in ("1525", "4772")}
    SG.HEAD_EXT_CUTOFF = False
    try:
        rv2 = {sd: len(revocations(p)) for sd, p in fz.items()}
    finally:
        SG.HEAD_EXT_CUTOFF = True
    ok2 = all(rv2.values())
    print("%s 图头那一条不设 cutoff ⇒ 随机反例撤回 %s" % ("✓" if ok2 else "✗", rv2))
    # 图头挪位踩暂定刀（card-6dd83a22-a76）：关掉 HEAD_DIR_NO_TENT ⇒ 1754／2068 必须报撤回
    SG.HEAD_DIR_NO_TENT = False
    try:
        rv3 = {sd: len(revocations(fz_all[sd])) for sd in ("1754", "2068")}
    finally:
        SG.HEAD_DIR_NO_TENT = True
    ok4 = all(rv3.values())
    print("%s 图头挪位不避暂定刀 ⇒ 随机反例撤回 %s" % ("✓" if ok4 else "✗", rv3))
    # ③ 切片拼起来 ≡ 整串（10-08 起主跑是切片并行的）：拿会撤销的 flaky 比，撤销点得一条不差 —— 切错一格（起点那份
    #    「上一个前缀」取成 pens[:lo] 之类）就会多报或漏报衔接处那一条
    whole = revocations(pens, flaky)
    ok3 = all([x for lo, hi in cuts(len(pens), parts) for x in revocations_range(pens, lo, hi, flaky)] == whole
              for parts in (2, 3, 5, 9))
    print("%s 切片拼起来 ≡ 整串（%s，切 2/3/5/9 片，整串报 %d 处）" % ("✓" if ok3 else "✗", fn, len(whole)))
    # ⑤ K 线前缀档有牙（card-eafabf4b-a60）：data/zec15 第 6200～6649 根这一截，K 线前缀档必须报撤销（尾笔改了，
    #    已确认的 6445～6472 那段被撤）；同一截拿定稿的笔走上面那档，必须 0 处 —— 关掉这一档就照不出来
    fn5 = "zec15.json"
    sl = load(os.path.join(ROOT, "data", fn5))[6200:6650]
    t5 = tick_of(fn5)
    cs = bar_cuts(sl, t5)
    rv5 = bar_revocations_range(sl, t5, (cs[0] - 1, cs))
    rv5p = revocations(_pens_of_bars(sl, t5))
    ok5 = bool(rv5) and not rv5p
    print("%s K 线前缀档：zec15 那一截报 %d 处 %s；同一截定稿笔那档 %d 处" % ("✓" if ok5 else "✗", len(rv5), rv5[:1], len(rv5p)))
    # ⑤′ 切片拼起来 ≡ 整串（K 线前缀档也是切片并行的）
    whole5 = bar_revocations_range(sl, t5, (0, cs))
    pieces = [x for a, b in ((0, len(cs) // 3), (len(cs) // 3, 2 * len(cs) // 3), (2 * len(cs) // 3, len(cs)))
              for x in bar_revocations_range(sl, t5, (cs[a - 1] if a else 0, cs[a:b]))]
    ok6 = pieces == whole5 and bool(whole5)
    print("%s K 线前缀档切 3 片拼起来 ≡ 整串（整串报 %d 处）" % ("✓" if ok6 else "✗", len(whole5)))
    return 0 if rv and ok2 and ok3 and ok4 and ok5 and ok6 else 3


# ---------------------------------------------------------------- K 线前缀档（card-eafabf4b-a60，Nova 10-09 03:34）
# 上面那档拿**定稿的笔**逐笔加长，每一步喂的笔都是最终的；线上是按 **K 线**往后长，最后一两笔还会被后来的 K 线改（笔.md C9，
# 小栋 10-07 选 A「当下的判断可以改」）。10-09 量过：线段层确认一段时会用到这种还没定的尾笔，尾笔一改，已确认的段就撤了 ——
# 定稿那档从来不喂没定的尾笔，所以照不出来。这一档每张图在「每一笔终点的后一根」取 K 线前缀，整个重算笔和线段再比。
# 「已确认」跟上面那档同一个口径：不是 live 的段。段用 K 线下标 (i0, i1) 认，不用笔号（尾笔一改，笔号会挪）。
BAR_EXPECT = 4                         # data/ 下 10 份的撤销数（main 0293c1f）：aaplusdt_30m 2、zec15 1、zec30_cut 1。
#   已知现状、先冻住（跟 FUZZ_EXPECT 一个意思）：修法要先跟 spec 对（card-eafabf4b-a60 第 2 条），定了、改了再改这个数。
#   数一变就红：多了是新撤销，少了是有人改了线段层或笔层，得说清楚。


def _pens_of_bars(bars, tick):
    from core.pen import build_pens, MIN_GAP_DEFAULT
    import importlib
    A = importlib.import_module("core.analyze")    # core 包把 analyze 这个名字换成了函数，模块得这样拿
    std = A.standardize(A.quantize(bars, tick))
    return build_pens(A.fractals(std), std, "old", MIN_GAP_DEFAULT)[0]


def _confirmed_bars(pens, build=build_segments):
    return [(pens[s["PI0"]]["i0"], pens[s["PI1"]]["i1"]) for s in build(pens) if not s.get("live")]


def bar_revocations_range(bars, tick, cuts_, build=build_segments, pens_of=None):
    """K 线前缀 cuts_[0], cuts_[1], … 逐个重算 → [(前缀长度, 被撤销的段 (i0, i1))]。起点那份「上一个前缀」现算（跟 revocations_range 同理），
    所以把整串 cuts 切成几片各跑一遍再按序拼，跟整串跑逐条相同。"""
    pens_of = pens_of or _pens_of_bars
    out = []
    prev = _confirmed_bars(pens_of(bars[:cuts_[0]], tick), build) if cuts_[0] else []
    for c in cuts_[1]:
        cur = _confirmed_bars(pens_of(bars[:c], tick), build)
        if cur[:len(prev)] != prev:
            k = next((t for t, (a, b) in enumerate(zip(prev, cur)) if a != b), len(cur))
            out.append((c, prev[k]))
        prev = cur
    return out


def bar_cuts(bars, tick):
    """取前缀的地方：最终那份笔的每个终点后一根，加上整份。"""
    return sorted({p["i1"] + 1 for p in _pens_of_bars(bars, tick)} | {len(bars)})


def _bar_job(args):
    fn, start, cs = args
    bars = load(os.path.join(ROOT, "data", fn))
    return bar_revocations_range(bars, tick_of(fn), (start, cs))


def bars_main():
    """--bars：data/ 下全部样本按 K 线前缀逐笔重算。每个前缀要整个重划一遍线段（约 ∝ 前缀长度），zec15 一张串着跑约 390 秒，
    所以每张按工作量（前缀长度平方累计）切片、多进程跑，跟主跑同一个 JOBS。"""
    items = []
    for fn in kline_files():
        bars = load(os.path.join(ROOT, "data", fn))
        items.append((fn, bar_cuts(bars, tick_of(fn))))
    total = sum(sum(c * c for c in cs) for _, cs in items) or 1
    tasks = []
    for k, (fn, cs) in enumerate(items):
        w = sum(c * c for c in cs)
        parts = max(1, round(JOBS * 8 * w / total)) if JOBS > 1 else 1
        step, acc, lo = w / parts, 0, 0
        for i, c in enumerate(cs):
            acc += c * c
            if acc >= step * (len([t for t in tasks if t[0] == k]) + 1) or i == len(cs) - 1:
                tasks.append((k, lo, i + 1))
                lo = i + 1
    tasks.sort(key=lambda t: -sum(c * c for c in items[t[0]][1][t[1]:t[2]]))
    args = [(items[k][0], items[k][1][lo - 1] if lo else 0, items[k][1][lo:hi]) for k, lo, hi in tasks]
    if JOBS > 1:
        import concurrent.futures as cf
        with cf.ProcessPoolExecutor(max_workers=JOBS) as ex:
            res = list(ex.map(_bar_job, args))
    else:
        res = [_bar_job(a) for a in args]
    got = {}
    for (k, lo, _), rv in zip(tasks, res):
        got.setdefault(k, []).append((lo, rv))
    n = 0
    for k, (fn, cs) in enumerate(items):
        rv = [x for _, part in sorted(got.get(k, [])) for x in part]
        n += len(rv)
        print("%s %s %d 个前缀 撤销 %d %s" % ("·" if not rv else "!", fn, len(cs), len(rv), rv[:3] if rv else ""))
    ok = n == BAR_EXPECT
    print("%s K 线前缀档：撤销 %d 处，期望 %d（BAR_EXPECT，已知现状）" % ("✓" if ok else "✗", n, BAR_EXPECT))
    return 0 if ok else 1


def fuzz_pens(sd):
    """随机笔（Atlas／Bram 10-08 那个生成器，card-c784a101-791）：起价 100、涨跌交替，每笔幅度取自 {0.3,0.6,1,1.5,2.5,4}，
    长度取自 {30,50,80}。跟 tools/fixtures/l77_pens.json、headfuzz 不是一个分布，所以三处各留各的。"""
    import random
    rng = random.Random(sd)
    n = rng.choice([30, 50, 80])
    P, p, up = [], 100.0, rng.random() < .5
    for k in range(n):
        d = rng.choice([0.3, 0.6, 1, 1.5, 2.5, 4]) * (1 if up else -1)
        q = round(p + d, 2)
        P.append(dict(p0=p, p1=q, hi=max(p, q), lo=min(p, q), i0=k * 5, i1=k * 5 + 5, dir="up" if up else "down"))
        p, up = q, not up
    return P


FUZZ_EXPECT = 18                       # 随机 4000 组的撤销组数（B 之后）。Nova 10-08 23:07 定；小栋 10-09 选 B（追平不算新高），18 是已知现状


def fuzz(n_seeds):
    """--fuzz N（Nova 10-08 21:49）：随机 N 组笔逐笔加长查撤销。10-08 land-b4c 上 4000 组有 20 组撤销（card-6dd83a22-a76）；
    B（图头挪位不踩暂定刀，HEAD_DIR_NO_TENT）进第五批以后剩 **18** 组，根在「追平算不算新高」。小栋 10-09 00:26 选 B（不算，维持严格），这 18 组是已知现状。
    ⇒ 期望值冻成 FUZZ_EXPECT（只对 N=4000 判）：撤销组数**正好**等于它才绿 —— 谁动了线段层，这个数一变就红（多了是新撤销，
    少了是有人顺手改了判定、得说清楚）。先不进 predeploy（4000 组单跑约 30 秒、4 路）；原先写的「甲定了、改成 0 以后再接」作废（小栋选 B），接不接门 Nova 另定。"""
    import concurrent.futures as cf
    with cf.ProcessPoolExecutor(max_workers=JOBS) as ex:
        res = list(ex.map(_fuzz_one, range(n_seeds), chunksize=50))
    bad = [(sd, rv[0]) for sd, rv in enumerate(res) if rv]
    for sd, first in bad[:20]:
        print("✗ seed %d：第 %d 笔加进来时撤了 %s" % (sd, first[0], first[1]))
    print("随机 %d 组：%d 组撤销%s" % (n_seeds, len(bad), "" if len(bad) <= 20 else "（只列前 20 组）"))
    if n_seeds == 4000:
        ok = len(bad) == FUZZ_EXPECT
        print("%s 期望 %d 组（FUZZ_EXPECT），实际 %d 组" % ("✓" if ok else "✗", FUZZ_EXPECT, len(bad)))
        return 0 if ok else 1
    return 1 if bad else 0


def _fuzz_one(sd):
    return revocations(fuzz_pens(sd))


if __name__ == "__main__":
    if "--fuzz" in sys.argv:
        sys.exit(fuzz(int(sys.argv[sys.argv.index("--fuzz") + 1])))
    if "--bars" in sys.argv:
        sys.exit(bars_main())
    sys.exit(self_test() if "--self-test" in sys.argv else main())
