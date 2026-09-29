# -*- coding: utf-8 -*-
"""TradingView 截图（uploads/photo_26B0F906.png，AAPL 永续 4H，CHANLUN 3.0）的像素标定。

chart_annotate / chart_signals 共用 —— 两张图对同一个中枢、同一个点必须给出同一个价格和日期，
所以价格、日期一律由这里的标定从像素现算，不在脚本里手写数字。
"""
import datetime

# ---- 价格标定：y=335 像素对应 330.0，14.367 像素 / 1 美元 ----
_Y0, _P0, _PX_PER_USD = 335, 330.0, 14.367


def P(y):
    """像素 y → 价格"""
    return _P0 - (y - _Y0) / _PX_PER_USD


def Ypx(p):
    """价格 → 像素 y"""
    return _Y0 - (p - _P0) * _PX_PER_USD


# ---- 时间标定：x=270 像素对应 8 月 1 日，33.9 像素 / 天 ----
_X0, _D0, _PX_PER_DAY = 270, datetime.date(2026, 8, 1), 33.9


def datestr(x):
    """像素 x → 「8月27日」（按天取整：落在当天之内都算当天）"""
    dd = _D0 + datetime.timedelta(days=(x - _X0) / _PX_PER_DAY)
    return "%d月%d日" % (dd.month, dd.day)


# ---- 中枢框（像素实测）；ZG / ZD 用 P(yt) / P(yb) 现算 ----
#   kind: blue = 可用本级别三笔重叠复算；orange / red = 级别未定（本级别笔回算对不上）
#   live: 截图里仍在延续、未终结 → 按画法约定整框虚线
CENTERS = {
    "③": dict(x0=187,  x1=675,  yt=208.5, yb=484.5, kind="orange", live=False),
    "④": dict(x0=259,  x1=597,  yt=595,   yb=737.5, kind="red",    live=False),
    "⑤": dict(x0=731,  x1=998,  yt=651,   yb=686.5, kind="blue",   live=False),
    "②": dict(x0=1142, x1=1625, yt=543.5, yb=574.5, kind="blue",   live=False),
    "①": dict(x0=1682, x1=2182, yt=245.5, yb=285.5, kind="blue",   live=True),
}


def ZG(n):
    return P(CENTERS[n]["yt"])


def ZD(n):
    return P(CENTERS[n]["yb"])
