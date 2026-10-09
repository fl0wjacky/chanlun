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
    每个中枢的 z["up"]：延伸满 9 段时同时构成的高一级别中枢（满 27 段再升一级），见 center.upgrades
    r["tick"] / r["pen_rule"]   这次用的精度 / 成笔标准（口径一旦选定要一路保持）

第 83 课：「由线段构成最小中枢，则不存在这个问题」—— 正规的最小中枢是线段中枢；
第 91 课：「笔是不能构成中枢的」。笔层那个只是「类中枢」，留着作对照，因为短数据上线段太少。
"""
import json

from .kline import standardize, fractals, quantize
from .pen import build_pens, MIN_GAP_DEFAULT
from .center import find_centers, find_centers_by_segment
from .extend import build_hierarchy
from .segment import build_segments


# S-13 甲（#19，读法-S13；Q-6b 待小栋选）：线段只用定稿的笔来划——笔列表里只有最后一笔没定稿（P1，L77:51-52），
#   所以划线段时把最后一笔去掉。锁关（小栋 10-09 ①B）下单开这个：25 张线段确认后撤 12→8，确认中位晚十几根。默认关。
#   开了以后最后一笔不进任何线段（图尾本来就允许有不进线段的笔）。
SEG_FINAL_PENS = False


def analyze(bars, tick=None, pen="old", min_gap=None):
    """tick：价格精度（None = 原样）；pen："old" 老笔（默认，第 77 课）/ "new" 新笔（第 81 课）。"""
    std = standardize(quantize(bars, tick))
    fx = fractals(std)
    min_gap = MIN_GAP_DEFAULT if min_gap is None else min_gap
    pens, seq = build_pens(fx, std, pen, min_gap)
    segs = build_segments(pens[:-1] if SEG_FINAL_PENS and len(pens) > 1 else pens)
    centers = find_centers_by_segment(pens, segs)
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
            " ｜ 笔 %d ｜ 类中枢 %d（满 9 段升级 %d）｜ 大级别类中枢 %d ｜ 线段 %d ｜ 线段中枢 %d（升级 %d）｜ 精度 %s ｜ %s笔"
            % (len(r["bars"]), len(r["std"]), len(r["fx"]),
               sum(1 for f in r["fx"] if f["type"] == "top"),
               sum(1 for f in r["fx"] if f["type"] == "bot"),
               len(r["pens"]), len(r["centers"]), sum(bool(z["up"]) for z in r["centers"]), len(r["big"]),
               sum(not s.get("live") for s in r["segs"]), len(r["seg_centers"]),
               sum(bool(z["up"]) for z in r["seg_centers"]),
               r["tick"], "老" if r["pen_rule"] == "old" else "新"))
