#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中枢形状（card-03ad1057-525 小栋问「上涨里怎么有涨跌涨框」；card-8368a083-082 B 档）：趋势段里的框，形状要跟段型相配——
上涨段里首段向下（下-上-下）、下跌段里首段向上（上-下-上）（答疑 L24:84-85、L31:145）。允许的例外只有两种：
  · 首中枢豁免（甲S-2，答疑 L45:122-123）：前一段是本级别反向趋势 ⇒ 这一组第一个框不限；
  · 图头那一组（前面没有刀，不限）。
其余反过来的框一个都不许有。

    python3 tools/shape_check.py              # rc=0 全对 ／ 1 有不对
    python3 tools/shape_check.py --self-test  # 反向臂：退回 fallback／S5 段不限／方向不定死，各自必须红；红不了 ⇒ rc=3

  ① 小栋两例（夹具 fixtures/shape/，线上 BTC 截的两段）：B 档下那个框没了；切回旧口径（fallback＋S5 不限）那个框必须在（夹具自己的牙）；
     btcusdt_4h_2022：2022-03-28 16:00 起的跌涨跌框 [37350.0, 40071.7]；btcusdt_15m_0930：2026-09-30 13:00 起的跌涨跌框 [83841.9, 85632.7]；
  ② data/ 下每份＋fixtures/shape/ 全部夹具：趋势段里反过来的框只许是上面两种例外。
  ③ SL_WAY_LOCK（甲S-6，Nova 10-10 13:34 定默认开）：夹具 aaplusdt_30m_lock 开着时「方向没定死」那两个框（07-13、07-29，
     从低点 D2 起头的那一段走成了下跌）归零、关着时在。
  夹具 aaplusdt_15m_s5 专给自检臂「S5 之后那截不限」当牙（07-24、08-03 两个跌涨跌框冒出来）。
例外的判法照 trend_check T4：前一段（终点＝这把 D2）是反向趋势 ⇒ 这组首框豁免。只读引擎输出，不挂引擎内部。
"""
import datetime
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.analyze import analyze  # noqa: E402
import core.trend as T  # noqa: E402
from config import tick_of  # noqa: E402

FIX = os.path.join(ROOT, "fixtures", "shape")
CASES = [("btcusdt_4h_2022.json", "2022-03-28 16:00", (37350.0, 40071.7)),
         ("btcusdt_15m_0930.json", "2026-09-30 13:00", (83841.9, 85632.7))]
OLD = dict(SAME_LEVEL_D6="fallback", SL_S5_SHAPE=False, SL_WAY_LOCK=False)


def _tick(path):
    """data/ 下按文件名查精度；夹具（fixtures/shape/<品种>_…）按品种。"""
    name = os.path.basename(path)
    if os.path.dirname(path) == FIX:
        return tick_of({"btcusdt": "btc_.json", "aaplusdt": "aaplusdt_.json", "zecusdt": "zec_.json"}[name.split("_")[0]])
    return tick_of(name)


def _ts(bars, i):
    return datetime.datetime.fromtimestamp(bars[i]["t"] / 1000, datetime.UTC).strftime("%Y-%m-%d %H:%M")


def odd_boxes(bars, tick):
    """→ [(起点时间, ZD, ZG, 例外类别或 None)]：趋势段里形状反过来的框。"""
    r = analyze(bars, tick=tick)
    v = T.trend_v3(r)
    done = T._done(r)
    segs = v["segments"]
    d2 = [b for b in v["bounds"] if b["rule"] == "D2-2"]
    edges = [0] + [b["line_seg"] + 1 for b in d2] + [len(done)]
    prev_type = {s["i1"]: s["type"] for s in segs}
    zz = sorted(v["seg_centers"], key=lambda z: z["PI0"])
    out = []
    for z in zz:
        sg = segs[z["seg"]]
        if sg["type"] not in ("上涨", "下跌"):
            continue
        up = done[z["PI0"]]["p1"] >= done[z["PI0"]]["p0"]
        if (sg["type"] == "上涨") != up:
            continue
        g = max(i for i, e in enumerate(edges[:-1]) if e <= z["PI0"])
        first = next(x for x in zz if edges[g] <= x["PI0"] < edges[g + 1]) is z
        why = None
        if g == 0:
            why = "图头"
        elif first and prev_type.get(d2[g - 1]["bar"]) == ("下跌" if d2[g - 1]["kind"] == "L" else "上涨"):
            why = "首中枢豁免"
        elif sg["i0"] == d2[g - 1]["bar"] and sg["type"] == ("下跌" if d2[g - 1]["kind"] == "L" else "上涨"):
            why = "方向没定死"                               # 低点刀起头那段走成了下跌（高点刀后走成上涨）：只给 ③ 认这一类用，② 照样算不许
        out.append((_ts(bars, z["X0"]), z["ZD"], z["ZG"], why))
    return out


def _with(flags, fn):
    saved = {k: getattr(T, k) for k in flags}
    try:
        for k, x in flags.items():
            setattr(T, k, x)
        return fn()
    finally:
        for k, x in saved.items():
            setattr(T, k, x)


def run(quiet=False, teeth=True):
    bad = []

    def chk(name, ok, got=""):
        if not quiet:
            print("%s %s %s" % ("✓" if ok else "✗", name, "" if ok else got))
        if not ok:
            bad.append(name)

    tick = tick_of("btc_.json")
    for fn, t0, zg in CASES:
        bars = json.load(open(os.path.join(FIX, fn)))
        now = odd_boxes(bars, tick)
        chk("① %s：%s 起那个反过来的框没了" % (fn, t0), not any(x[0] == t0 and (x[1], x[2]) == zg for x in now), now[:3])
        if teeth:
            old = _with(OLD, lambda: odd_boxes(bars, tick))
            chk("① %s：旧口径下那个框在（夹具的牙）" % fn, any(x[0] == t0 and (x[1], x[2]) == zg for x in old), old[:3])
    files = []
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "*.json"))):   # 只要 K 线数组（跟 trend_check.kline_files 同一个挑法）
        if p.endswith("_tmp.json"):
            continue
        try:
            raw = json.load(open(p))
        except ValueError:
            continue
        if isinstance(raw, list) and raw and isinstance(raw[0], dict) and {"t", "o", "h", "l", "c"} <= set(raw[0]):
            files.append(p)
    files += sorted(glob.glob(os.path.join(FIX, "*.json")))
    n_ok = 0
    for p in files:
        bars = json.load(open(p))
        name = os.path.basename(p)
        got = [x for x in odd_boxes(bars, _tick(p)) if x[3] not in ("首中枢豁免", "图头")]
        n_ok += not got
        if got:
            chk("② %s：趋势段里反过来的框只许豁免／图头" % name, False, got[:3])
    chk("② %d 份：趋势段里反过来的框只剩豁免／图头两种" % len(files), n_ok == len(files), "")
    if teeth:
        lk = os.path.join(FIX, "aaplusdt_30m_lock.json")
        bars = json.load(open(lk))
        got = _with(dict(SL_WAY_LOCK=True), lambda: [x for x in odd_boxes(bars, _tick(lk)) if x[3] not in ("首中枢豁免", "图头")])
        chk("③ SL_WAY_LOCK 开着：aaplusdt_30m_lock 里「方向没定死」那两个框归零（开关本身管用）", got == [], got[:3])
        got = _with(dict(SL_WAY_LOCK=False), lambda: [x for x in odd_boxes(bars, _tick(lk)) if x[3] == "方向没定死"])
        chk("③ SL_WAY_LOCK 关着：同一份夹具里那两个框在（夹具的牙）", len(got) == 2, got[:3])
    if not quiet:
        print("全部通过" if not bad else "%d 处不过" % len(bad))
    return len(bad)


def self_test():
    arms = [("退回 fallback（D6 凑不出就不限）", dict(SAME_LEVEL_D6="fallback")),
            ("S5 之后那截不限形状", dict(SL_S5_SHAPE=False)),
            ("限了形状的组方向不定死（甲S-6 关）", dict(SL_WAY_LOCK=False))]
    rc = 0
    for name, flags in arms:
        n = _with(flags, lambda: run(quiet=True, teeth=False))
        print("%s 变异「%s」⇒ 主跑 %d 处不过" % ("✓" if n else "✗", name, n))
        rc |= 0 if n else 3
    return rc


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv[1:] else (1 if run() else 0))
