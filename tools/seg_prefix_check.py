#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""线段「已确认段只增不撤」检查：每份 K 线样本，笔序列逐笔加长，build_segments 的已确认段必须只往后长、不撤销。

    python3 tools/seg_prefix_check.py             # data/ 下全部样本，撤销数必须为 0（rc=0）
    python3 tools/seg_prefix_check.py --fuzz 4000 # 随机 4000 组逐笔加长（先不进 predeploy，见 fuzz()）
    python3 tools/seg_prefix_check.py --self-test # 反向验证：喂一个故意会撤销的划段函数，必须报出来（rc=0 ＝ 报出来了）

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
    return 0 if rv and ok2 and ok3 and ok4 else 3


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


FUZZ_EXPECT = 18                       # 随机 4000 组的撤销组数（B 之后；等甲）。Nova 10-08 23:07 定


def fuzz(n_seeds):
    """--fuzz N（Nova 10-08 21:49）：随机 N 组笔逐笔加长查撤销。10-08 land-b4c 上 4000 组有 20 组撤销（card-6dd83a22-a76）；
    B（图头挪位不踩暂定刀，HEAD_DIR_NO_TENT）进第五批以后剩 **18** 组，都等「追平算不算新高」（甲，上小栋那页）。
    ⇒ 期望值冻成 FUZZ_EXPECT（只对 N=4000 判）：撤销组数**正好**等于它才绿 —— 谁动了线段层，这个数一变就红（多了是新撤销，
    少了是有人顺手改了判定、得说清楚）。先不进 predeploy（4000 组单跑约 30 秒、4 路），甲定了、改成 0 以后再接。"""
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
    sys.exit(self_test() if "--self-test" in sys.argv else main())
