#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""概念卡 06 走势类型"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cards.base import *
from cards import zec_data as zec

W, H = 1400, 2100                    # 卡片尺寸；模块常量，各段函数直接用
OUTNAME = "c06_走势类型.png"


def zigpanel(d, x0, y0, w, h, title, boxes, path, pmin, pmax, note, col=BL):
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], 16, fill=CARD, outline=LINE, width=2)
    d.text((x0 + 18, y0 + 10), title, font=f_p, fill=TX)
    m = Mini(d, x0 + 30, y0 + 60, x0 + w - 30, y0 + h - 62, pmin, pmax)
    n = len(path) - 1
    X = lambda i: x0 + 50 + i / n * (w - 100)
    polyline(d, [(X(i), m.Y(p)) for i, p in enumerate(path)], col, 6)
    for (a, b, lo, hi) in boxes:
        d.rectangle([X(a), m.Y(hi), X(b), m.Y(lo)], fill=col + (44,), outline=col, width=3)
    d.text((x0 + 18, y0 + h - 38), note, font=f_t, fill=MU)


def draw_two_kinds(d):
    """A 只有两类"""
    section(d, 200, 792, "只有两类，数中枢就知道")
    d.text((500, 226), "第 17 课：任何级别的所有走势，都能分解成趋势与盘整两类", font=f_n, fill=MU)

    zigpanel(d, 76, 286, 614, 330, "盘整 · 只包含一个中枢",
             [(0, 4, 101, 108)], [110, 100, 108, 101, 107, 96],
             94, 112, "走势里只找到 1 个中枢 → 盘整（横着走）")
    zigpanel(d, 710, 286, 614, 330, "趋势 · 两个以上依次同向的中枢",
             [(0, 5, 101, 108), (6, 10, 113, 118)],
             [110, 100, 108, 101, 107, 102, 118, 112, 120, 113, 119],
             96, 124, "找到 2 个中枢、一个比一个高 → 上涨", col=GR)

    d.rounded_rectangle([76, 634, W - 76, 770], 14, fill=(BL[0], BL[1], BL[2], 26), outline=BL, width=2)
    d.text((100, 646), "原文定义", font=f_n, fill=LB)
    d.text((100, 682), "盘整：某完成的走势类型 只包含一个 走势中枢。", font=f_t, fill=TX)
    d.text((100, 710), "趋势：至少包含两个以上 依次同向 的走势中枢 —— 该中枢方向向上就称为上涨，向下就称为下跌。", font=f_t, fill=TX)
    d.text((100, 738), "补充（第 17 课）：任何走势都至少含一个中枢 —— 上+下+上 或 下+上+下 都必然产生一个中枢。",
           font=f_t, fill=MU)


def draw_theorems(d):
    """B 四条原理与定理"""
    section(d, 808, 1240, "四条原理与定理（第 17 课）")
    d.text((560, 834), "这四条是同一天给出的，构成后面的操作基石", font=f_n, fill=MU)
    rows = [
        ("基本原理一", "任何级别的任何走势类型 终要完成", "＝ 走势终完美", AM),
        ("基本原理二", "任何级别任何完成的走势类型，必然 包含一个以上的中枢", "走势里一定有中枢", BL),
        ("分解定理一", "任何走势 = 同级别盘整、下跌、上涨三种走势类型的连接", "两两相接，不重叠不断层", GR),
        ("分解定理二", "任何走势类型，都至少由 三段以上次级别走势类型 构成", "所以最短的结构也得三段", CY),
    ]
    yy = 880
    for k, v, note, c in rows:
        d.rounded_rectangle([80, yy, 260, yy + 56], 10, fill=c + (46,), outline=c, width=2)
        tw = d.textlength(k, font=f_n)
        d.text((80 + (180 - tw) / 2, yy + 14), k, font=f_n, fill=c)
        d.text((286, yy + 6), v, font=f_n, fill=TX)
        d.text((286, yy + 34), note, font=f_t, fill=MU)
        yy += 78


def draw_evidence(d):
    """C 实证：相邻中枢之间，扩展多还是趋势多（ZEC 线段中枢为主，类中枢对照；出图时现算）"""
    from tools.v1_ref import center_v1
    r = zec.run("15m")
    seg, pen = zec.pair_stats(r["seg_centers"]), zec.pair_stats(r["centers"])
    done = [s for s in r["segs"] if not s.get("live")]    # 同一批笔、线段，只换回 v1 的中枢终结口径
    seg1, pen1 = zec.pair_stats(center_v1.find_centers(done)), zec.pair_stats(center_v1.find_centers(r["pens"]))
    more = seg["扩展"] > seg["趋势"]
    section(d, 1268, 1700, "一个实证：扩展多还是趋势多", GR)
    d.text((560, 1294), "相邻中枢之间：扩展仍多于趋势，但差距比 v1 小" if more else "相邻中枢之间：这段数据里趋势不少于扩展",
           font=f_n, fill=MU)
    d.text((86, 1344), "数据：ZECUSDT 永续 15 分钟，%s（UTC），%d 根K线；本项目引擎，出图时现算"
           % (zec.date_range("15m"), len(r["bars"])), font=f_t, fill=MU)

    cols = [(86, "口径"), (400, "中枢"), (530, "相邻对数"), (700, "趋势（新生）"), (900, "扩展"),
            (1030, "同一中枢"), (1180, "趋势占比")]
    for x, t in cols:
        d.text((x, 1386), t, font=f_t, fill=MU)
    yy = 1424
    for name, zs, st, col in (("线段中枢（主）", r["seg_centers"], seg, TX), ("类中枢（对照）", r["centers"], pen, MU)):
        vals = [name, str(len(zs)), str(st["n"]), str(st["趋势"]), str(st["扩展"]), str(st["同一中枢"]),
                "%d%%" % round(100 * st["趋势"] / st["n"])]
        for (x, _), v, c in zip(cols, vals, (col, MU, MU, GR, AM, MU, AM)):
            d.text((x, yy), v, font=f_n, fill=c)
        yy += 38
    d.line([86, yy + 4, W - 86, yy + 4], fill=LINE, width=2)
    rat = lambda st: st["扩展"] / max(st["趋势"], 1)
    d.text((86, yy + 20), "★ 线段中枢 %d 对：趋势 %d、扩展 %d，扩展约是趋势的 %.1f 倍；类中枢是 %.1f 倍"
           % (seg["n"], seg["趋势"], seg["扩展"], rat(seg), rat(pen)), font=f_n, fill=AM)
    d.text((86, yy + 56), "　 同一批笔和线段，换回 v1 的终结口径：线段中枢趋势 %d / 扩展 %d（%.1f 倍），类中枢 %d / %d（%.1f 倍）"
           % (seg1["趋势"], seg1["扩展"], rat(seg1), pen1["趋势"], pen1["扩展"], rat(pen1)), font=f_t, fill=TX)
    d.text((86, yy + 86), "　 v1 只用中心定理一，把冲出中枢的离开段算进前中枢，撑大了它的波动范围 —— 差距有一部分是引擎造成的。",
           font=f_t, fill=MU)
    d.text((86, yy + 116), "　 第 21 课：「A、中枢扩张导致一个更大级别的中枢；B、中枢新生，就会形成一个上涨的趋势」",
           font=f_t, fill=TX)
    d.text((86, yy + 146), "　 原文只列两种可能、没说孰多孰少；线段中枢只有 %d 对，样本偏薄，只能说，在这段数据上扩展仍多。"
           % seg["n"], font=f_t, fill=MU)


def trap():
    """页脚陷阱：按现算结果措辞。"""
    seg = zec.pair_stats(zec.run("15m")["seg_centers"])
    share = round(100 * seg["扩展"] / seg["n"])
    if seg["扩展"] > seg["趋势"]:
        return "以为趋势常见 —— 这段数据上相邻线段中枢 %d%% 是扩展；但 v1 引擎曾把这个差距放大过" % share
    return "以为扩展或趋势哪个天然更常见 —— 这段数据里相邻线段中枢扩展只占 %d%%，要看数据说话" % share


def draw_buhuan(d):
    """D 不患"""
    callout(d, 1728, 1918, RD, 22)
    d.text((86, 1742), "★ 当下的两难：延续还是改变？（第 17 课）", font=f_p, fill=RD)
    d.text((86, 1782), "「在任何一个走势的当下，无论前面是盘整还是趋势，都有一个两难的问题：究竟是继续延续还是改变。」",
           font=f_t, fill=TX)
    d.text((86, 1812), "「……这样的问题在当下的层次上永远是“不患”的，无位次的。」"
                       "（后文：在「走势都能分解成趋势与盘整」之下，又可以位次）", font=f_t, fill=TX)
    d.text((86, 1842), "「任何宣称自己能解决这个两难问题的，就如同在地球上宣称自己不受地球引力影响一样无效」",
           font=f_t, fill=MU)
    d.text((86, 1872), "所以操作靠的不是预测会不会延续，而是等它走完 —— 这也是一买和二买的出处。",
           font=f_t, fill=AM)


def build():
    """画整张卡，返回 PIL Image。"""
    set_size(W, H)
    im, d = newcard("06", "走势类型", "任何走势都能分解成趋势与盘整两类 —— 而分辨它们只需要数中枢",
                    panel=False)
    draw_two_kinds(d)
    draw_theorems(d)
    draw_evidence(d)
    draw_buhuan(d)
    foot(d, "第 17 课《走势终完美》（定义 + 四条原理定理）；第 21 课（三买后的两种情况）",
         trap())
    return im


def main():
    build().save(OUT + OUTNAME)
    print("06")




# --- cardfit 失败分支声明（见 tools/cardfit.py 的 failure_modes()）--------------------------
# **这张卡是 13 张里唯一真的存在一条走不到的分支的卡**（实测，见 card-8b15761f-779）：
# `more = seg["扩展"] > seg["趋势"]` 在这段数据上恒为 True ⇒ 那句 else 正文从来没被画过。
def _cardfit_inject_trend_not_more():
    """把 扩展>趋势 这个判断翻成不成立，逼出那句 else 正文。

    **只翻关系、不改量级**：同一批计数值对调（趋势 4 / 扩展 14 → 14 / 4），位数不变 ⇒
    量的还是这张卡的排版，不是我另外编的一组数。`n = 趋势 + 扩展`，对调不影响它。

    签名对的是工具的约定：**本函数不接参数，返回 `install(mod) -> restore`**
    （跟 `model_dissent._cardfit_inject_mismatch(n)` 同形；多接一个 `mod` 会在 restore 那步 TypeError）。
    """
    def install(mod):
        orig = mod.zec.pair_stats

        def swapped(zs):
            d = orig(zs)
            if d["扩展"] > d["趋势"]:
                d = dict(d, 趋势=d["扩展"], 扩展=d["趋势"])
            return d

        def restore():
            mod.zec.pair_stats = orig

        mod.zec.pair_stats = swapped
        return restore
    return install


# 注意列表里放的是**调用结果**（`install`），不是函数本身 —— 工具会执行 `install(mod)`。
CARDFIT_FAILURES = [("趋势不少于扩展（真数据走不到的那支）", _cardfit_inject_trend_not_more())]

if __name__ == "__main__":
    main()
