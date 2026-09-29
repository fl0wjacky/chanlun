# -*- coding: utf-8 -*-
"""引擎对外入口：喂进原始K线，拿回全套结构。

    from core.analyze import analyze
    r = analyze(bars)
    r["std"]    标准化序列
    r["fx"]     分型
    r["pens"]   笔
    r["seq"]    笔端点序列
    r["centers"]笔中枢
    r["big"]    由「扩展」合成出来的更大级别中枢
    r["segs"]   线段（最后一条可能是未完成的，带 live=True）
    r["seg_centers"] 线段中枢 —— 只用**已完成**的线段算（未完成段的高低点还会变）

第 83 课：「由线段构成最小中枢，则不存在这个问题」—— 正规的最小中枢是线段中枢；
笔中枢留着是因为短数据上线段太少，统计撑不起来（见 README）。
"""

from .kline import standardize, fractals
from .pen import build_pens
from .center import find_centers
from .extend import build_hierarchy
from .segment import build_segments


def analyze(bars, min_gap=4):
    std = standardize(bars)
    fx = fractals(std)
    pens, seq = build_pens(fx, min_gap)
    centers = find_centers(pens)
    segs = build_segments(pens)
    return dict(bars=bars, std=std, fx=fx, pens=pens, seq=seq,
                centers=centers, big=build_hierarchy(centers, pens),
                segs=segs, seg_centers=find_centers([s for s in segs if not s.get("live")]),
                min_gap=min_gap)


def summarize(r):
    return ("原始 %d 根 → 标准化 %d 根 ｜ 分型 %d（顶 %d / 底 %d）"
            " ｜ 笔 %d ｜ 笔中枢 %d ｜ 大级别中枢 %d ｜ 线段 %d ｜ 线段中枢 %d"
            % (len(r["bars"]), len(r["std"]), len(r["fx"]),
               sum(1 for f in r["fx"] if f["type"] == "top"),
               sum(1 for f in r["fx"] if f["type"] == "bot"),
               len(r["pens"]), len(r["centers"]), len(r["big"]),
               sum(not s.get("live") for s in r["segs"]), len(r["seg_centers"])))
