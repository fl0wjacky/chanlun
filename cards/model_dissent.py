#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""框架卡一：共识 → 分歧 → 证实 / 证伪（机会模型）"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json, datetime
from collections import Counter
from config import out, data
from core import analyze, analyze_file
from render.style import *

f_t, f_s, f_b, f_m, f_n = F(50), F(30), F(34), F(27), F(24)

W, H = 1400, 2200                    # 卡片尺寸；模块常量，各段函数直接用


def box(d, x0, x1, y0, y1, col):
    """中枢 / 共识区：同色半透明底 + 描边"""
    d.rounded_rectangle([x0, y0, x1, y1], 10, fill=col + (46,), outline=col, width=3)


def draw_title(d):
    """标题 + 署名"""
    d.text((60, 44), "缠论的机会模型", font=f_t, fill=TX)
    d.text((62, 112), "共识 → 分歧 → 证实 / 证伪（作者解读，非原文术语）", font=f_s, fill=MU)
    r = "冲浪者 · 2026-09-26"
    d.text((W - d.textlength(r, font=f_n) - 60, 60), r, font=f_n, fill=(110, 118, 136))


def draw_diagram(d):
    """示意图：共识区 → 分歧段 → 回试证实 / 证伪"""
    d.rounded_rectangle([50, 180, W - 50, 900], 22, fill=CARD, outline=LINE, width=2)
    ax0, ax1 = 120, W - 120
    # 中枢区间按第 20 课公式：ZG = 三段高点里最低的，ZD = 三段低点里最高的（屏幕上 y 越小价越高）
    ZG = 632                                   # 中枢① 的 ZG：高点 y=622/632/612 里最低的那个

    box(d, 140, 420, 632, 690, BL)                # 中枢① / 共识区① = [ZD, ZG]
    box(d, 770, 1170, 404, 452, BL)               # 中枢② / 共识区②
    d.text((150, 574), "共识区①  中枢", font=f_m, fill=(200, 215, 255))
    d.text((880, 340), "共识区②  中枢", font=f_m, fill=(200, 215, 255))

    # ZG 线
    x = ax0
    while x < ax1:
        d.line([x, ZG, min(x + 16, ax1), ZG], fill=BL + (230,), width=3); x += 26
    d.text((ax1 - 200, ZG - 38), "ZG（中枢上沿）", font=f_n, fill=BL)

    # 价格折线
    path = [(140,690),(188,622),(232,704),(282,632),(332,700),(396,612),
            (462,516),(520,668),                          # 回试① 跌破 ZG ✗
            (626,462),(680,556),                          # 回试② 站住 ✓
            (770,404),(818,452),(872,398),(930,462),(986,392),(1044,458),(1102,398),
            (1170,388)]
    for i in range(len(path) - 1):
        d.line([path[i], path[i+1]], fill=(255, 255, 255, 220), width=4)

    # 分歧段标注
    d.line([396, 760, 396, 786], fill=AM, width=3)
    d.line([770, 760, 770, 786], fill=AM, width=3)
    d.line([396, 786, 770, 786], fill=AM, width=3)
    d.text((452, 742), "分歧段（缝隙）", font=f_m, fill=AM)

    # 回试点标记
    d.ellipse([520-15, 668-15, 520+15, 668+15], fill=BG, outline=RD, width=5)
    d.text((520, 668), "×", font=F(26), fill=RD, anchor="mm")
    d.text((540, 690), "① 回试跌回 ZG 以内 → 中枢延伸，不是机会", font=f_m, fill=RD)
    d.ellipse([680-15, 556-15, 680+15, 556+15], fill=BG, outline=GR, width=5)
    d.text((680, 556), "✓", font=F(26), fill=GR, anchor="mm")
    d.text((700, 516), "② 回试不破 ZG → 三买成立，缝隙才被追认", font=f_m, fill=GR)

    d.text((140, 826), "中枢 = 多空达成共识的区间　　分歧 = 有人不同意，把价格拉开　　机会 = 分歧被证实的那一刻",
           font=f_n, fill=MU)


def draw_rules(d):
    """口诀：四句话记住"""
    y = 930
    d.rounded_rectangle([50, y, W - 50, y + 454], 22, fill=CARD, outline=LINE, width=2)
    d.text((86, y + 26), "四句话记住", font=f_s, fill=AM)
    rules = [("中枢是共识", "多空都认的价位区间"),
             ("缝隙是分歧", "有人不同意，把价格拉出去"),
             ("机会在被证实回不去的那一下", "不在缝隙中段追，在回试不破 ZG 的那一下"),
             ("缝隙是结果，不是原因", "先有回试通过，才追认这是缝隙")]
    yy = y + 90
    for i, (a, b) in enumerate(rules):
        d.ellipse([86, yy + 6, 86 + 44, yy + 50], fill=(BL + (235,)))
        d.text((86 + 22, yy + 28), str(i + 1), font=f_b, fill=(255, 255, 255), anchor="mm")
        d.text((150, yy), a, font=f_b, fill=TX)
        d.text((150, yy + 46), b, font=f_n, fill=MU)
        yy += 88


def gap_rows_and_z():
    """引擎现算：4 小时类中枢里，每次向上离开 ZG 之后的第一次回试。

    返回 (rows, Z)，其中 rows = [(日期, 中枢序号, 中枢, 离开冲高, 回试低点, 判定)]；
    判定 = 三买 / 贯穿（从区间另一侧整段穿过）/ 假缝隙 / ZD 下方。
    出图时现算 —— 换数据或改引擎，卡片自动跟着变，不会过期。

    一并返回 Z 是给 cross_check() 用的：那张表的期望值必须来自被测物之外，
    而 Z 里的 term 由 core/center.py 独立算出（见 cross_check 的说明）。
    """
    r = analyze_file("aaplusdt_4h.json")
    P, B, Z = r["pens"], r["bars"], r["centers"]
    rows = []
    for n, z in enumerate(Z):
        nxt = Z[n + 1]["PI0"] if n + 1 < len(Z) else len(P)
        for j in range(z["PI0"], min(nxt + 1, len(P) - 1)):
            up, dn = P[j], P[j + 1]
            if up["p1"] > up["p0"] and up["p1"] > z["ZG"] and dn["p1"] < dn["p0"]:
                if dn["p1"] > z["ZG"]:                # 回试整段在 ZG 之上：离开段须从区间里出发才算三买（第 20 / 38 课）
                    v = "三买" if z["ZD"] <= up["p0"] <= z["ZG"] else "贯穿"
                else:
                    v = "ZD 下方" if dn["p1"] < z["ZD"] else "假缝隙"
                t = datetime.datetime.utcfromtimestamp(B[dn["i1"]]["t"] / 1000)
                rows.append(("%d月%d日" % (t.month, t.day), n + 1, z, up["p1"], dn["p1"], v))
    return rows, Z


def gap_rows():
    """兼容旧调用（tools/verify_c06_c07.py:95 按 6 元组解包）：只要 rows。"""
    return gap_rows_and_z()[0]


def seg_fallback_count():
    """线段中枢层的兜底（中心定理一）结束还有多少个 —— 给脚注当例子。

    类中枢改段内算以后，本卡数据（aaplusdt_4h）里那个由中心定理一兜底判终结的类中枢
    在线段边界就结束了（term='所在线段结束'），脚注里原来的「贯穿」实例没了。但线段
    中枢层仍按老规则兜底：这里从 ZEC 15m 现算，换数据或改引擎自动跟着变，不会过期。
    """
    r = analyze_file("zec15.json")
    return sum(1 for z in r.get("seg_centers", [])
               if z["term"] in ("Z 段向上离开", "Z 段向下离开"))


def cross_check(rows, Z):
    """拿引擎自己的中枢终结原因跟卡片的判定对账——**这只查漂移，不构成对原文的验证。**

    先说清它查不了什么，免得又被读成「验证」：
      本卡 L106-108 的谓词  up.p1>up.p0 且 dn.p1>ZG 且 ZD<=up.p0<=ZG
      center.py L120-125 的  u.p1>u.p0 且 w.lo>ZG 且 ZD<=u.p0<=ZG
    而向下笔恒有 lo == p1（在本数据 10/10 实测），所以 dn.p1>ZG 与 w.lo>ZG
    是**同一个条件**。两边是同一份原文规则的两次转写——和 upgrades()/check_centers()
    那种情形等同于同一算法被转写了两次。**原文读错了，两边一起错，这里查不出来。**

    它真正能查的是**管道**：谁跟谁配成一笔、三买记在哪个中枢上、本卡的扫描范围
    有没有漏掉引擎已判为三买的那一段。所以它是一条**漂移报警**——两处实现一旦
    分家就红。这有价值（内部不一致必须吼），但别把它当独立来源。

    真正的独立来源在引擎之外：data/annot_pens.json 是人工从截图标的笔。要让这张卡
    能验原文，得拿它当外部期望值——那是另一个活，本函数不做。

    依据是第 38 课原文「第三类买卖点，和中枢延伸的结束是一回事情」：三买 ⟺
    中枢终结原因就是三买。双向对，免得漏掉本卡漏判、引擎多判这两个方向。

    返回 (对上几个, 不一致的清单)。清单非空 = 两处实现已经分家。
    """
    bad, ok = [], 0
    for n, z in enumerate(Z, 1):
        mine = [r[5] for r in rows if r[1] == n]
        if not mine:
            continue
        card_buy, engine_buy = ("三买" in mine), (z["term"] == "三买")
        if card_buy == engine_buy:
            ok += 1
        else:
            bad.append((n, card_buy, z["term"], mine))
    return ok, bad


MISMATCH = []          # cross_check 的真失败清单；非空 → main() 以 1 退出（见文件末尾）


def draw_evidence(d):
    """实证：本引擎 4 小时类中枢，逐次核对缝隙"""
    rows, Z = gap_rows_and_z()
    y = 1414
    d.rounded_rectangle([50, y, W - 50, y + 762], 22, fill=CARD, outline=LINE, width=2)
    # 标题去掉用真实数据验证这个说法：下面那个✓不可能失败，说"验证"是给它安一个挣不到的出身。
    # 措辞用 Iris 那条的（按本引擎口径统计）。**不往标题里再塞对账说明**：那会让标题只剩
    # ~31px 余量（全角字≈30px，等于一个字的余量），换稍宽的 CJK 字体就溢出。对账只查漂移
    # 这句话下面那行脚注已经印了，标题不必重复。
    d.text((86, y + 24), "按本引擎口径统计：4 小时类中枢，每次向上离开后的回试", font=f_s, fill=AM)
    hd = ["日期（UTC）", "中枢", "离开冲高", "回试低点", "中枢区间 [ZD, ZG]", "判定"]
    xs = [86, 280, 400, 580, 760, 1080]
    # 96 → 80：这一块**整块**上提 16px。原因量出来的（`tools/cardfit.py` 全程没有 y，它够不着这一格）：
    #   面板里 y=1958…2152 每行都是 32px 步进、**墨迹间隔只剩 +2px**，整块本来就压满，动不了某一行；
    #   slack 只在顶部：标题墨迹底 1474 → 表头 1510，间隔 +36（别处全是 +2~+18）。
    # 三个口径都记下来，省下一个人再问一遍 —— 它们答的不是同一个问题：
    #   **真像素墨迹底**  问"看起来出不出框"，**bbox 底** 问"下一行还放不放得下"（含字体 descent 留白）。
    #   真 main：单行 y=2120 墨迹到 2151、面板底 2144 ⇒ 出框 +7（Noto +9）——**这一处不是回归，
    #   是原本就有的**，这里顺手清掉。上提前（本支第一次改）：墨迹 2181 / 面板 2176 ⇒ +5。
    #   上提后两支字体各量一遍（换字体是有余量的，这不是修辞）：
    #     Droid 97320619 墨迹 2165 / 面板 2176 ⇒ 余 +11
    #     Noto  2c76254f 墨迹 2167 / 面板 2176 ⇒ 余 +9
    yy = y + 80
    for i, h in enumerate(hd):
        d.text((xs[i], yy), h, font=f_n, fill=MU)
    d.line([86, yy + 38, W - 86, yy + 38], fill=LINE, width=2)
    yy += 56
    for t, n, z, hi, lo, v in rows:
        col = GR if v == "三买" else RD
        mark = {"三买": "✓ 三买", "假缝隙": "× 假缝隙", "ZD 下方": "× 跌到 ZD 下方", "贯穿": "× 贯穿，非三买"}[v]
        for x, txt in zip(xs[:5], [t, "中枢%d" % n, "%.2f" % hi, "%.2f" % lo, "[%.2f, %.2f]" % (z["ZD"], z["ZG"])]):
            d.text((x, yy), txt, font=f_n, fill=TX)
        d.text((xs[5], yy), mark, font=f_n, fill=col)
        yy += 40
    c = Counter(r[5] for r in rows)
    d.line([86, yy + 6, W - 86, yy + 6], fill=LINE, width=2)
    d.text((86, yy + 24), "%d 次向上离开后回试：成立 %d 次，跌回中枢 %d 次，跌到 ZD 下方 %d 次%s —— 不追缝隙中段。"
           % (len(rows), c["三买"], c["假缝隙"], c["ZD 下方"], "，贯穿 %d 次" % c["贯穿"] if c["贯穿"] else ""),
           font=f_m, fill=AM)
    d.text((86, yy + 72), "注：AAPLUSDT 永续 4 小时，07-26 – 09-27；类中枢（笔构成，第 83 课说稳定性差），出图时现算。",
           font=f_n, fill=MU)
    d.text((86, yy + 104), "　 三买按定义就是中枢终结（第 38 课「第三类买卖点，和中枢延伸的结束是一回事情」）：",
           font=f_n, fill=MU)
    d.text((86, yy + 136), "　 离开段从中枢里出发、回试整段不回到区间，当下就判中枢结束，离开段算连接段。", font=f_n, fill=MU)
    d.text((86, yy + 168),
           "　 类中枢改段内算后兜底退成『所在线段结束』，但线段中枢层仍有（ZEC 15m 有 %d 个以 Z 段离开结束）。"
           % seg_fallback_count(), font=f_n, fill=MU)
    yy0 = yy + 200
    d.text((86, yy0), "　 样本只有 %d 次，只作示意。" % len(rows), font=f_n, fill=MU)

    # 对账（本卡唯一会失败的地方）：期望值来自引擎自己的 term，而不是本文件把
    # 上面那个 v 再抄一遍 —— 那样两边同一个谓词，永远不会分歧。
    nok, MISMATCH[:] = cross_check(rows, Z)
    # 这一句原先是一行，宽 1546px、右边 1632 压在画布外 232px（tools/cardfit.py 量的）。
    # **不改口径、不砍字**：拆成两行，第一行仍是"判没判"，第二行是那句免责 ——
    # 免责是这句话的一半内容，砍掉它比让它出画布更糟。两行各 778 / 798px，都远在 1258px 内。
    if MISMATCH:
        # **列清单只列前 2 条，条数照旧全报**：这条正文的宽度是分家条数的函数，不是常数。
        # 实测（`tools/cardfit.py` 的注入，右边界 vs N，Droid 97320619 / Noto 2c76254f）：
        #   N=1 632.7 / 642.4   N=2 959.8 / 971.9   N=3 1262.8 / 1277.5（贴着 1344）
        #   N=4 1589.9 / 1607.1 **越界**   N=8 3032.8 / 3061.0 越界
        # 真实数据 8 行、全部分家就是 N=8 —— 那是够得着的，不是假想。贴边不算安全：
        # N=3 只剩 81px（≈2.7 个全角字），换稍宽的字体就翻。
        # 砍掉的只是**卡面上的明细**，`main()` 仍然把完整清单打到 stdout 并把退出码置 1 ⇒ 信息没丢。
        shown = MISMATCH[:2]
        d.text((86, yy0 + 34),
               "　 × 两处实现分家 %d 处：%s%s"
               % (len(MISMATCH),
                  "、".join("中枢%d(卡=%s/引擎=%s)" % (n, "三买" if cb else "非三买", t)
                            for n, cb, t, _ in shown),
                  "…" if len(MISMATCH) > len(shown) else ""),
               font=f_n, fill=RD)
        d.text((86, yy0 + 66), "　 —— 本卡与 core/center.py 的判定已经不一致，先查哪个错。",
               font=f_n, fill=RD)
    else:
        d.text((86, yy0 + 34),
               "　 ✓ 对账：%d 个有回试的中枢，本卡与 core/center.py 两处实现未分家。" % nok,
               font=f_n, fill=GR)
        d.text((86, yy0 + 66),
               "　 （谓词同源，原文若读错会一起错——这条只报漂移，不当独立验证。）",
               font=f_n, fill=GR)


def build():
    """画整张卡，返回 PIL Image。"""
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im, "RGBA")
    draw_title(d)
    draw_diagram(d)
    draw_rules(d)
    draw_evidence(d)
    return im


def main():
    build().save(out("chanlun_model.png"))
    if MISMATCH:
        # 出图成功不等于卡是对的：判据和引擎的终结原因对不上时，这张卡不该被当成证据。
        print("model ok（图已出），但两处实现分家 %d 处：%s" % (len(MISMATCH), MISMATCH))
        return 1
    print("model ok，两处实现未分家")
    return 0


# ---- 交给 tools/cardfit.py 的失败分支注入 ------------------------------------
# 这张卡有一条**真实数据下永远走不到**的正文：`cross_check` 返空清单 ⇒ 那条
# 标签 × 两处实现分家 N 处：… 一次都画不出来，版式体检（tools/cardfit.py）也就一次都没量过它。
# 实测那一支比成功支**还宽 14px**（右边界 1646.3 vs 1632.0，画布只有 1400），而且**宽度是 N 的函数、
# 不是常数**：那串 `中枢1(卡=…/引擎=…)` 随分家条数线性变长（n=1/2/3 一行装得下，n≥4 起破边距）。
#
# 所以这里声明**怎么把那一支逼出来**，让 cardfit 现有的判据自己开口（判据一条没改）。
# 契约：`(模式名, 注入函数)`，注入函数(mod) -> 还原函数；装完后**必须真的改变画出来的字**，
# 没改变的话 cardfit 会报出注入未生效并计进退出码 —— **打歪的桩比不打更危险**，
# 它会让"这一支覆盖过了"变成新的代理量，而且长得跟真的一样。
# 注入写在卡这边而不是 cardfit 里：`cross_check` / `MISMATCH` 是**这张卡的内脏**，
# 工具一旦认识某张卡的内脏，加一张卡就得改工具，而工具是大家共用的热文件。


def _cardfit_inject_mismatch(n):
    """把 `cross_check` 打桩成会报 n 处分家。n 取值覆盖三种形状：
    装得下（1/2/3）、刚好过半（4）、**真实上界 8**（= `len(rows)`，全部分家）。

    **只改"有几条分家"，不改"它们说什么"** —— 那条正文的宽度由 `z["term"]` 决定，
    而这里的 term 从**真实 rows** 里取（有 `'三买'` 也有 `'Z 段向上离开'`，差 5 个字 ≈ 150px）。
    自己编一串假 term 去量，量的是我编的那串，不是这一支 —— 又一个代理量。"""
    def install(mod):
        orig = mod.cross_check

        def restore():
            mod.cross_check = orig
            mod.MISMATCH[:] = []      # build() 里是 `MISMATCH[:] = …` 原地改，不还原就留下一条脏清单

        def fake(rows, Z):
            # 形状照抄真实现：draw_evidence 解包 (n, cb, t, _)，四元组少一个当场 TypeError
            return 0, [(rows[i % len(rows)][1], i % 2 == 0,
                        rows[i % len(rows)][2]["term"], "三买") for i in range(n)]

        mod.cross_check = fake
        return restore
    return install


CARDFIT_FAILURES = [("分家 %d 处" % n, _cardfit_inject_mismatch(n)) for n in (1, 2, 3, 4, 8)]


if __name__ == "__main__":
    sys.exit(main())
