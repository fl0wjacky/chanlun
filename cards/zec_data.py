# -*- coding: utf-8 -*-
"""c06 / c07 共用的实证数据：ZEC 永续（`tools/fetch_klines.py ZECUSDT …` 拉到当前），出图时现算。

数据一刷新，卡上的数字跟着变 —— 所以卡片只调这里的函数，不手抄数字；
tools/verify_c06_c07.py 另写一遍逐项比对，并核对卡上的定性结论还成立。
"""
import json, datetime
from functools import lru_cache
from collections import Counter
from config import data
from core import analyze, analyze_file

FILES = {"15m": "zec15.json", "1h": "zec_1h.json", "2h": "zec_2h.json", "4h": "zec_4h.json"}


@lru_cache(None)
def run(tf):
    return analyze_file(FILES[tf])


def done_segs(tf):
    return [s for s in run(tf)["segs"] if not s.get("live")]


def date_range(tf="15m"):
    b = run(tf)["bars"]
    f = lambda ms: datetime.datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%d")
    return "%s – %s" % (f(b[0]["t"]), f(b[-1]["t"]))


def pair_stats(zs):
    """相邻中枢关系计数：dict(n=对数, 趋势=, 扩展=, 同一中枢=)。"""
    c = Counter(z["kind"] for z in zs[1:])
    return dict(n=sum(c.values()), 趋势=c["趋势"], 扩展=c["扩展"], 同一中枢=c["同一中枢"])


def _span(tf, z, units):
    B = run(tf)["bars"]
    return B[units[z["PI0"]]["i0"]]["t"], B[units[z["PI1"]]["i1"]]["t"]


def _meet(ta, za, tb, zb):
    """宽松匹配：起止时间有交叠，且中枢区间有交叠。"""
    return ta[0] <= tb[1] and tb[0] <= ta[1] and za["ZD"] <= zb["ZG"] and zb["ZD"] <= za["ZG"]


def cross(tf_hi):
    """15 分钟线段中枢（路径 A）vs 高一档周期的类中枢（路径 B）。

    返回 dict(A=个数, B=个数, A_hit=A 中能在 B 里找到对应的个数, B_hit=反之)。
    """
    A, Ad = run("15m")["seg_centers"], done_segs("15m")
    Bz, P = run(tf_hi)["centers"], run(tf_hi)["pens"]
    ta = [(_span("15m", a, Ad), a) for a in A]
    tb = [(_span(tf_hi, b, P), b) for b in Bz]
    return dict(A=len(A), B=len(Bz),
                A_hit=sum(any(_meet(s, a, t, b) for t, b in tb) for s, a in ta),
                B_hit=sum(any(_meet(s, a, t, b) for s, a in ta) for t, b in tb))
