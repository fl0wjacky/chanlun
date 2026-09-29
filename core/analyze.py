# -*- coding: utf-8 -*-
"""引擎对外入口：喂进原始K线，拿回全套结构。

    from core.analyze import analyze, analyze_file
    r = analyze_file("aaplusdt_4h.json")          # 从 data/ 读，精度按 config.TICK
    r = analyze(bars, tick=0.01, pen="old")      # 直接喂K线
    r["std"]    标准化序列（按精度取整之后）
    r["fx"]     分型
    r["pens"]   笔
    r["seq"]    笔端点序列
    r["centers"]类中枢（由笔构成；第 64 课「线段以下是没有中枢的，所以说是类中枢」）
    r["big"]    由「扩展」合成出来的更大级别中枢
    r["segs"]   线段（最后一条可能是未完成的，带 live=True）
    r["seg_centers"] 线段中枢 —— 只用**已完成**的线段算（未完成段的高低点还会变）
    r["tick"] / r["pen_rule"]   这次用的精度 / 成笔标准（口径一旦选定要一路保持）

第 83 课：「由线段构成最小中枢，则不存在这个问题」—— 正规的最小中枢是线段中枢；
第 91 课：「笔是不能构成中枢的」。笔层那个只是「类中枢」，留着作对照，因为短数据上线段太少。
"""
import json

from .kline import standardize, fractals, quantize
from .pen import build_pens
from .center import find_centers
from .extend import build_hierarchy
from .segment import build_segments


def analyze(bars, tick=None, pen="old", min_gap=4):
    """tick：价格精度（None = 原样）；pen："old" 老笔（默认，第 77 课）/ "new" 新笔（第 81 课）。"""
    std = standardize(quantize(bars, tick))
    fx = fractals(std)
    pens, seq = build_pens(fx, std, pen, min_gap)
    centers = find_centers(pens)
    segs = build_segments(pens)
    return dict(bars=bars, std=std, fx=fx, pens=pens, seq=seq,
                centers=centers, big=build_hierarchy(centers, pens),
                segs=segs, seg_centers=find_centers([s for s in segs if not s.get("live")]),
                tick=tick, pen_rule=pen, min_gap=min_gap)


def analyze_file(fn, pen="old", **kw):
    """读 data/<fn>，按 config.TICK 里给这个标的写明的精度分析。"""
    from config import data, tick_of
    bars = json.load(open(data(fn), encoding="utf-8"))
    return analyze(bars, tick=kw.pop("tick", tick_of(fn)), pen=pen, **kw)


def summarize(r):
    return ("原始 %d 根 → 标准化 %d 根 ｜ 分型 %d（顶 %d / 底 %d）"
            " ｜ 笔 %d ｜ 类中枢 %d ｜ 大级别类中枢 %d ｜ 线段 %d ｜ 线段中枢 %d ｜ 精度 %s ｜ %s笔"
            % (len(r["bars"]), len(r["std"]), len(r["fx"]),
               sum(1 for f in r["fx"] if f["type"] == "top"),
               sum(1 for f in r["fx"] if f["type"] == "bot"),
               len(r["pens"]), len(r["centers"]), len(r["big"]),
               sum(not s.get("live") for s in r["segs"]), len(r["seg_centers"]),
               r["tick"], "老" if r["pen_rule"] == "old" else "新"))
