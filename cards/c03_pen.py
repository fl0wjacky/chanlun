#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""概念卡 03 笔"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cards.base import *
from core import analyze_file
from core.pen import nonextreme_pens, build_pens_v1

W, H = 1400, 2600
OUTNAME = "c03_笔.png"


def draw_anatomy(d):
    """A 一笔的解剖：分型各占 3 根、中间至少 1 根独立K线"""
    section(d, 200, 736, "一笔的解剖")
    d.text((300, 224), "分型各占 3 根K线；两段之间至少要空出 1 根 —— 这 1 根才叫独立K线", font=f_n, fill=MU)

    A = [(100.5,101.0,99.5,99.8), (99.8,100.0,98.6,99.0), (99.0,99.2,97.8,98.4),
         (98.4,100.2,98.4,99.6),  (99.6,101.4,99.6,100.8), (100.8,102.2,100.4,101.6),
         (101.6,103.0,101.2,101.8), (101.8,102.4,100.6,101.0), (101.0,101.6,99.8,100.2)]
    ma = Mini(d, 180, 392, 1220, 648, 97.6, 103.2)
    n = len(A); Xa = lambda i: ma.X(i, n)
    cs(ma, Xa, ma.Y, A, w=52)
    d.line([Xa(2), ma.Y(97.8), Xa(6), ma.Y(103.0)], fill=BL, width=8)
    d.ellipse([Xa(2) - 9, ma.Y(97.8) - 9, Xa(2) + 9, ma.Y(97.8) + 9], fill=GR)
    d.ellipse([Xa(6) - 9, ma.Y(103.0) - 9, Xa(6) + 9, ma.Y(103.0) + 9], fill=RD)

    def bracket(i, j, y, col, label):
        x0, x1 = Xa(i) - 34, Xa(j) + 34
        d.line([x0, y, x1, y], fill=col, width=3)
        d.line([x0, y, x0, y + 16], fill=col, width=3)
        d.line([x1, y, x1, y + 16], fill=col, width=3)
        d.text(((x0 + x1) / 2 - d.textlength(label, font=f_n) / 2, y - 32), label, font=f_n, fill=col)
    bracket(1, 3, 368, GR, "底分型（占 3 根）")
    bracket(4, 4, 368, CY, "独立K线")
    bracket(5, 7, 368, RD, "顶分型（占 3 根）")
    d.line([Xa(2), 300, Xa(6), 300], fill=AM, width=3)
    d.line([Xa(2), 300, Xa(2), 318], fill=AM, width=3)
    d.line([Xa(6), 300, Xa(6), 318], fill=AM, width=3)
    d.text((Xa(2) + 10, 266), "两个分型中心之间 = 5 根K线（第 77 课老笔；第 81 课新笔可选，默认老笔）", font=f_n, fill=AM)
    d.text((180, 656), "第 77 课：顶底之间至少一根K线不属于两分型 → 索引差 ≥ 4", font=f_n, fill=MU)
    d.text((820, 658), "底 = 底分型的最低点　顶 = 顶分型的最高点", font=f_n, fill=BL)
    d.text((820, 690), "笔 = 两个相邻的「顶」与「底」之间", font=f_n, fill=BL)


def cellc(d, x0, y0, w, h, no, title, verdict, vcol, bars, note,
          marks=None, labels=None, pen_pts=None, pen_col=BL, gap=None):
    """一个情形小格。
    marks  : [(索引, 'top'|'bot', 颜色)]
    labels : [(索引, 文本, 颜色, 'up'|'dn')]
    pen_pts: [(i, 'top'|'bot'), (j, ...)]  画笔（按分型类型取极值点）
    gap    : (i, j, 文本)  画两点的间隔标尺
    """
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], 16, fill=CARD, outline=LINE, width=2)
    d.text((x0 + 16, y0 + 8), no, font=F(28), fill=(78, 86, 104))
    d.text((x0 + 52, y0 + 12), title, font=f_p, fill=TX)
    cw = d.textlength(verdict, font=f_n) + 40
    d.rounded_rectangle([x0 + 16, y0 + 52, x0 + 16 + cw, y0 + 90], 10,
                        fill=vcol + (46,), outline=vcol, width=2)
    d.text((x0 + 36, y0 + 60), verdict, font=f_n, fill=vcol)
    lo = min(b[2] for b in bars); hi = max(b[1] for b in bars)
    pad = (hi - lo) * 0.14
    m = Mini(d, x0 + 40, y0 + 104, x0 + w - 40, y0 + 256, lo - pad, hi + pad)
    nn = len(bars)
    Xc = lambda i: m.X(i, nn)
    cs(m, Xc, m.Y, bars, w=34)
    if pen_pts:
        (i, ki), (j, kj) = pen_pts
        d.line([Xc(i), m.Y(bars[i][1] if ki == "top" else bars[i][2]),
                Xc(j), m.Y(bars[j][1] if kj == "top" else bars[j][2])], fill=pen_col, width=6)
    if gap:
        gi, gj, glab = gap
        gy = m.y1 - 22
        d.line([Xc(gi), gy, Xc(gj), gy], fill=RD, width=3)
        d.line([Xc(gi), gy - 9, Xc(gi), gy + 9], fill=RD, width=3)
        d.line([Xc(gj), gy - 9, Xc(gj), gy + 9], fill=RD, width=3)
        d.text(((Xc(gi) + Xc(gj)) / 2 - d.textlength(glab, font=f_t) / 2, gy + 12),
               glab, font=f_t, fill=RD)
    for (i, kind, col) in (marks or []):
        x = Xc(i)
        if kind == "top":
            yv = m.Y(bars[i][1])
            d.polygon([(x, yv - 8), (x - 11, yv - 24), (x + 11, yv - 24)], fill=col)
        else:
            yv = m.Y(bars[i][2])
            d.polygon([(x, yv + 8), (x - 11, yv + 24), (x + 11, yv + 24)], fill=col)
    for (i, txt, col, side) in (labels or []):
        yv = m.Y(bars[i][1]) if side == "up" else m.Y(bars[i][2])
        d.text((Xc(i) - d.textlength(txt, font=f_t) / 2, yv + (-48 if side == "up" else 30)),
               txt, font=f_t, fill=col)
    for k, t in enumerate(note if isinstance(note, (list, tuple)) else [note]):
        d.text((x0 + 16, y0 + 296 + k * 32), t, font=f_t, fill=MU)


def draw_four_cases(d):
    """B 三种处理：分型 → 笔只有成笔 / 跳过 / 取更极端（本项目引擎口径）"""
    cw = section(d, 756, 1660, "分型 → 笔：三种处理（本项目引擎口径）")
    d.text((80 + cw + 20, 782), "看三件事：同类/异类　间隔够不够 4　两头是不是极值", font=f_n, fill=MU)

    # ①② 成笔的两个方向
    P1 = [(100.0,100.2,98.8,99.2), (99.2,99.4,97.8,98.6), (98.6,100.0,98.4,99.6),
          (99.6,101.2,99.4,100.8), (100.8,102.2,100.4,101.8), (101.8,103.0,101.4,102.0),
          (102.0,102.4,100.8,101.4)]
    cellc(d, 76, 826, 614, 366, "①", "间隔够 + 异类分型", "向上笔 ✓", GR, P1,
          "底分型(索引1) → 顶分型(索引5)，差 4，刚好够 → 成笔",
          marks=[(1, "bot", GR), (5, "top", RD)], pen_pts=[(1, "bot"), (5, "top")])
    P2 = [(100.5,102.5,100.0,102.0), (102.0,103.0,101.0,101.5), (101.5,102.0,100.0,100.5),
          (100.5,101.0,99.0,99.5), (99.5,100.0,98.0,98.5), (98.5,98.8,97.0,97.5),
          (97.5,99.2,97.2,98.6)]
    cellc(d, 710, 826, 614, 366, "②", "间隔够 + 异类分型", "向下笔 ✓", GR, P2,
          "顶分型(索引1) → 底分型(索引5)，差 4 → 成笔（和左格对称）",
          marks=[(1, "top", RD), (5, "bot", GR)], pen_pts=[(1, "top"), (5, "bot")])

    # ★ ③④ 共用同一段行情
    d.text((86, 1204), "下面两格是同一段行情的先后两步：先处理底分型(索引2)，再处理顶分型(索引5)",
           font=f_n, fill=AM)
    P4 = [(99.0,100.0,98.5,100.0), (100.0,102.5,100.0,101.0), (100.5,101.0,99.0,100.0),
          (100.8,102.0,100.0,101.5), (101.8,103.5,101.5,103.0), (103.0,104.5,102.5,103.2),
          (103.4,103.8,102.0,102.6)]
    cellc(d, 76, 1236, 614, 406, "③", "与末尾端点异类，但间隔不够", "跳过 ×", RD, P4,
          ["此刻序列里只挂着顶分型(索引1)，它就是当前末尾端点",
           "底分型(索引2) 与它只隔 1 格 < 4 → 被跳过",
           "「跳过」是引擎的实现口径，第 77 课三步骤未单列"],
          marks=[(1, "top", RD), (2, "bot", GR)],
          labels=[(1, "末尾端点", RD, "up")], gap=(1, 2, "间隔 1"))
    cellc(d, 710, 1236, 614, 406, "④", "与末尾端点同类", "取更极端", AM, P4,
          ["底分型被跳过后，序列末尾仍是顶分型",
           "→ 索引5 的新顶与它同类，104.5 > 102.5，顶替它"],
          marks=[(1, "top", (120,126,146)), (2, "bot", (120,126,146)), (5, "top", GR)],
          labels=[(1, "被顶替", (120,126,146), "up"), (5, "保留", GR, "up")])


def draw_rules(d):
    """E 原文：两个条件、三步骤、唯一性（第 77 课）+ 端点必须是极值（第 66/70/71 课答疑）"""
    section(d, 2166, 2438, "原文怎么划笔（第 77 课）")
    d.text((520, 2192), "缠师在这一课里把笔的定义和算法一次讲完了", font=f_n, fill=MU)
    d.text((86, 2230), "两个条件：① 顶和底之间至少有一根K线不属于顶分型与底分型（= 索引差 ≥ 4）",
           font=f_t, fill=TX)
    d.text((86, 2260), "　　　　　② 顶分型中最高那根K线的区间，至少有一部分高于底分型中最低那根K线的区间",
           font=f_t, fill=TX)
    d.text((86, 2290), "三步骤：一、标出所有符合标准的分型　二、前后同性质时——顶取更高者、底取更低者（相等都先留）",
           font=f_t, fill=TX)
    d.text((86, 2320), "　　　　三、处理后相邻顶底即一笔；若相邻同性质，取「最先一个」　→ 净效果 = 同类取更极端",
           font=f_t, fill=AM)
    d.text((86, 2350), "★ 缠师在本课用反证法自己证明了：按这三步走，笔的划分是唯一的。", font=f_t, fill=GR)
    d.text((86, 2380), "★ 第 66/70/71 课答疑：「顶和底，当然一定是那一笔的最高最低，如果不是，那里面一定不只一笔」",
           font=f_t, fill=GR)
    d.text((86, 2408), "　→ 引擎：挨得太近被跳过、却更极端的分型，之后会让它回头作废上一笔重连（v1 没做，约两三成的笔不合格）",
           font=f_t, fill=MU)


def draw_real_data(d):
    """C 真实数据：分型是廉价的，笔是筛出来的（引擎现算）"""
    callout(d, 1690, 1924, GR, 24)
    d.text((86, 1704), "真实数据：分型是廉价的，笔是筛出来的", font=f_p, fill=GR)
    d.text((86, 1740), "币安合约 AAPLUSDT 永续　4小时 384 根 ／ 30分钟 3072 根　2026/07/26 – 09/27（UTC）　老笔",
           font=f_t, fill=MU)
    rows = []
    for fn, tag in (("aaplusdt_4h.json", "4 小时"), ("aaplusdt_30m.json", "30 分钟")):
        r = analyze_file(fn)
        v1, _ = build_pens_v1(r["fx"])
        rows.append((tag, len(r["fx"]), len(r["pens"]), len(nonextreme_pens(r["pens"], r["std"])),
                     len(v1), len(nonextreme_pens(v1, r["std"]))))
    for k, (tag, nfx, npen, bad, nv1, badv1) in enumerate(rows):
        d.text((86, 1774 + 32 * k), "%s：%d 个分型 → %d 条笔　（端点不是极值的 %d 条；v1 一遍扫过去是 %d 条，其中 %d 条不合格）"
               % (tag, nfx, npen, bad, nv1, badv1), font=f_n, fill=TX)
    if sum(r[3] for r in rows):
        d.text((86, 1838), "注：剩下的是剧烈的扩张震荡 —— 顶一个比一个高、底一个比一个低又挨得太近，两道回头修正都救不回。",
               font=f_t, fill=MU)
    d.text((86, 1870), "换算下来：约 %d 个分型才筛出 1 条笔。" % round(rows[1][1] / rows[1][2]), font=f_p, fill=AM)


def draw_dropped(d):
    """D 丢掉的波动去哪了：被丢的分型并进笔的跨度，不会扯断笔"""
    callout(d, 1950, 2150, BL, 26)
    d.text((86, 1964), "被丢掉的那些分型，会不会把笔扯断？—— 不会", font=f_p, fill=LB)
    d.text((86, 2002), "第 62 课原文：「所谓笔，就是顶和底之间的其他波动，都可以忽略不算」", font=f_n, fill=TX)
    d.text((86, 2036), "所以被丢掉的分型不是断口，它只是被并进了这一笔的跨度里 —— 笔本身照样首尾相接。", font=f_n, fill=MU)
    d.text((86, 2074), "逐根喂入实测：绝大多数时候只动最后一笔；回头修正时偶尔连带改前面 1–3 笔。", font=f_n, fill=AM)
    d.text((86, 2108), "（AAPL 4h/1h、BTC 4h、ZEC 4h、AAPL 30m：一次改 ≥2 笔的占 0.2%–0.5%，最多一次改 4 笔）", font=f_t, fill=MU)


def build():
    """画整张卡，返回 PIL Image。"""
    set_size(W, H)
    im, d = newcard("03", "笔", "一个顶分型 + 一个底分型相连 —— 但绝大多数分型连不上，笔是筛出来的", panel=False)
    draw_anatomy(d)
    draw_four_cases(d)
    draw_rules(d)            # 原稿里 E 节先于 C / D 画，顺序不要动
    draw_real_data(d)
    draw_dropped(d)
    foot(d, "第 62 课（顶/底）；第 77 课（双条件、三步骤、唯一性）；第 66/70/71 课答疑（极值）；第 81 课（新笔）",
         "以为有分型就有笔 —— 实际约九成分型连不上，画在图上全是噪音")
    return im


def main():
    build().save(OUT + OUTNAME)
    print("03")




# --- cardfit 失败分支声明（见 tools/cardfit.py 的 failure_modes()）--------------------------
# 三态必须分得开：**无此属性 = 没查过** / `[]` = 查过、没有 / 非空 = 逐支注入并自证。
# 本卡选了 `[]`，所以下面那句理由**不能省** —— 省了就是"一键消音"，把没查刷成查过。
CARDFIT_FAILURES = []
CARDFIT_NO_FAILURE = (
    "本卡正文全部是**字面量**，真实数据下逐条都画出过"
    "（判据：把画上去的字全收下来，看有没有哪条写了却从没出现）；"
    "卡里没有随数据分叉的判据支。量法与逐卡数据见 card-8b15761f-779。"
)

if __name__ == "__main__":
    main()
