#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""线段「已确认段只增不撤」检查：每份 K 线样本，笔序列逐笔加长，build_segments 的已确认段必须只往后长、不撤销。

    python3 tools/seg_prefix_check.py             # data/ 下全部样本，撤销数必须为 0（rc=0）
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
    """把前缀 [3, n_pens] 切成 parts 段，**按工作量切**（第 n 个前缀要划 n 笔 ⇒ 工作量 ∝ n，累计 ∝ n²）。"""
    lo, hi = 3, n_pens + 1
    if parts <= 1 or hi - lo < 2 * parts:
        return [(lo, hi)]
    edges = [lo] + [int(round((lo * lo + (hi * hi - lo * lo) * k / parts) ** 0.5)) for k in range(1, parts)] + [hi]
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
    total = sum(len(p) ** 2 for _, p in items) or 1
    tasks = []
    for k, (name, pens) in enumerate(items):
        parts = max(1, round(JOBS * 2 * len(pens) ** 2 / total)) if JOBS > 1 else 1
        tasks += [(k, lo, hi) for lo, hi in cuts(len(pens), parts)]
    tasks.sort(key=lambda t: -(t[2] ** 2 - t[1] ** 2))        # 大片先发
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
    fz = json.load(open(os.path.join(HERE, "fixtures", "headfuzz_pens.json")))["seeds"]
    SG.HEAD_EXT_CUTOFF = False
    try:
        rv2 = {sd: len(revocations(p)) for sd, p in fz.items()}
    finally:
        SG.HEAD_EXT_CUTOFF = True
    ok2 = all(rv2.values())
    print("%s 图头那一条不设 cutoff ⇒ 随机反例撤回 %s" % ("✓" if ok2 else "✗", rv2))
    # ③ 切片拼起来 ≡ 整串（10-08 起主跑是切片并行的）：拿会撤销的 flaky 比，撤销点得一条不差 —— 切错一格（起点那份
    #    「上一个前缀」取成 pens[:lo] 之类）就会多报或漏报衔接处那一条
    whole = revocations(pens, flaky)
    ok3 = all([x for lo, hi in cuts(len(pens), parts) for x in revocations_range(pens, lo, hi, flaky)] == whole
              for parts in (2, 3, 5, 9))
    print("%s 切片拼起来 ≡ 整串（%s，切 2/3/5/9 片，整串报 %d 处）" % ("✓" if ok3 else "✗", fn, len(whole)))
    return 0 if rv and ok2 and ok3 else 3


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
