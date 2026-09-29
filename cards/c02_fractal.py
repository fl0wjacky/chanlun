#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""概念卡 02 分型"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cards.base import *

W, H = 1400, 1720                    # 卡片尺寸；模块常量，各段函数直接用
OUTNAME = "c02_分型.png"

def column(d, x0, w, no, tag, verdict, vcol, bars, arrows, pmin, pmax, hl):
    """hl: ('top', i) 或 ('bot', i) 或 None —— 标出分型中心并画虚线"""
    d.rounded_rectangle([x0, 200, x0+w, 690], 18, fill=CARD, outline=LINE, width=2)
    d.text((x0+18, 216), no, font=F(30), fill=(78,86,104))
    d.text((x0+62, 220), tag, font=f_p, fill=TX)
    d.rounded_rectangle([x0+18, 268, x0+w-18, 306], 10, fill=vcol+(46,), outline=vcol, width=2)
    d.text((x0+(w-d.textlength(verdict, font=f_n))/2, 272), verdict, font=f_n, fill=vcol)
    m = Mini(d, x0+30, 326, x0+w-30, 600, pmin, pmax)
    X = lambda i: m.X(i, 3); Y = m.Y
    for i, bb in enumerate(bars):
        o,h,l,c = bb; col=(38,166,154) if c>=o else (239,83,80)
        d.line([X(i),Y(h),X(i),Y(l)],fill=col,width=4)
        d.rectangle([X(i)-26,Y(max(o,c)),X(i)+26,Y(min(o,c))],fill=col)
        lab = ["第1根","第2根","第3根"][i]
        d.text((X(i)-d.textlength(lab, font=f_t)/2, 612), lab, font=f_t, fill=MU)
    for k, r in enumerate(arrows):
        cx = (X(k)+X(k+1))/2
        (tri_up if r=="u" else tri_dn)(d, cx, 650, GR if r=="u" else RD)
    if hl:
        kind, i = hl
        v = bars[i][1] if kind=="top" else bars[i][2]
        col = RD if kind=="top" else GR
        dash(d, x0+34, x0+w-34, Y(v), col, 3)
        d.ellipse([X(i)-8, Y(v)-8, X(i)+8, Y(v)+8], fill=col)
        lbl = ("高点最高" if kind=="top" else "低点最低")
        ty = Y(v)-40 if kind=="top" else Y(v)+12
        d.text((x0+(w-d.textlength(lbl,font=f_n))/2, ty), lbl, font=f_n, fill=col)
    return m


def draw_title(d):
    """页眉：编号 + 名称 + 一句话（本卡自带，不走 newcard）"""
    d.text((56,34), "02", font=F(38), fill=(70,78,96))
    d.text((132,24), "分型（顶分型 / 底分型）", font=F(58), fill=TX)
    d.text((136,104), "三根连续的标准化K线，只有 4 种相对关系；其中 2 种构成分型", font=F(28), fill=MU)
    d.line([56,168,W-56,168], fill=LINE, width=2)


def draw_cases(d):
    """四种相对关系：四列小图"""
    # 编号按第 62 课的完全分类：一 上升K线、二 顶分型、三 下降K线、四 底分型
    # 数据（① ② 共用前两根；③ ④ 共用前两根）
    A1=(98.0,99.0,97.5,98.6); B1=(98.6,101.0,98.2,100.6)
    C1=(100.6,103.0,100.2,102.6)      # ① 继续上移
    C2=(100.6,100.8,97.9,99.0)        # ② 掉头 → 顶分型
    A3=(102.6,103.0,100.2,100.6); B3=C2
    C3=(99.0,101.0,98.2,100.6)        # ④ 掉头 → 底分型
    C4=(99.0,99.4,97.0,97.6)          # ③ 继续下移

    CW, GAP, X0 = 310, 16, 56
    cols = [
        ("①", "上移 + 上移", "上升K线（非分型）", MU, [A1,B1,C1], ["u","u"], None),
        ("②", "上移 + 下移", "顶分型 ✓", RD,          [A1,B1,C2], ["u","d"], ("top", 1)),
        ("③", "下移 + 下移", "下降K线（非分型）", MU, [A3,B3,C4], ["d","d"], None),
        ("④", "下移 + 上移", "底分型 ✓", GR,          [A3,B3,C3], ["d","u"], ("bot", 1)),
    ]
    for k,(no,tag,vv,vc,bars,arr,hl) in enumerate(cols):
        column(d, X0 + k*(CW+GAP), CW, no, tag, vv, vc, bars, arr, 96, 104, hl)


def draw_rule(d):
    """判定条件：只需要两个数"""
    d.rounded_rectangle([56, 716, W-56, 1024], 20, fill=PANEL, outline=LINE, width=2)
    d.rounded_rectangle([80, 734, 470, 784], 10, fill=(AM[0],AM[1],AM[2],46))
    d.text((100, 742), "判定其实只需要两个数", font=f_p, fill=AM)
    d.text((80, 802), "因为「相邻两根永不包含」（上一步保证的），可以推出一个很强的结论：", font=f_n, fill=MU)
    d.text((80, 840), "若 第2根的高点 > 第1根的高点　→　必然有 第2根的低点 > 第1根的低点", font=f_p, fill=TX)
    d.text((80, 882), "证明：若低点不高于第1根（≤），第2根就罩住了第1根 = 包含 —— 与前提矛盾。", font=f_n, fill=(170,200,255))
    d.rounded_rectangle([80, 916, W-80, 1006], 12, fill=(RD[0],RD[1],RD[2],26), outline=RD, width=2)
    d.text((102, 924), "所以：顶分型 ＝ 只要看「中间那根的高点是不是最高」", font=f_p, fill=RD)
    d.text((102, 962), "　　　底分型 ＝ 只要看「中间那根的低点是不是最低」", font=f_p, fill=RD)


def draw_edges(d):
    """边界与误判：四个必须记住的边界"""
    d.rounded_rectangle([56, 1044, W-56, 1538], 20, fill=PANEL, outline=LINE, width=2)
    d.rounded_rectangle([80, 1062, 470, 1112], 10, fill=(GR[0],GR[1],GR[2],46))
    d.text((100, 1070), "四个必须记住的边界", font=f_p, fill=GR)
    items = [
        ("① 图上像山顶 ≠ 分型", "你在原始K线图上看到的一个尖顶，中间那根可能已经被合并掉了；判定必须在「标准化序列」上做。"),
        ("② 分型成立 ≠ 成笔",   ["分型只是一个转折点，能不能连成笔，还要看顶底之间是否有独立K线（第 62 课）。",
                                "本项目用旧笔口径：顶到底含两端 ≥5 根标准化K线；第 81 课另有放宽的新笔标准。"]),
        ("③ 分型「是不是」是二值的，强弱另说", ["分型成立与否只看高低点、没有中间态；强弱是另一层（第 82 课：看第三根",
                                "能否收回第二根区间的一半之上），不影响分型是否成立。"]),
        ("④ 相邻分型不能共用K线",   "第 77 课：任何相邻的分型之间必须满足结合律 —— 不能有些K线分属不同的分型。"),
    ]
    yy = 1146
    for a,b in items:
        d.text((80, yy), a, font=f_b, fill=TX)
        for k, ln in enumerate(b if isinstance(b, list) else [b]):
            d.text((80, yy+34+k*32), ln, font=f_n, fill=MU)
            yy += 32 if k else 0
        yy += 76


def draw_foot(d):
    """页脚：原文 + 陷阱（本卡配色与 base.foot 略有不同，保留原样）"""
    d.line([56, H-150, W-56, H-150], fill=LINE, width=2)
    d.text((56, H-136), "原文", font=F(22), fill=DIM)
    d.text((132, H-136), "第 62 课《分型、笔与线段》定义；第 65 课：「这种定义是唯一的，有统一答案的」", font=F(24), fill=(168,176,192))
    d.text((56, H-96), "陷阱", font=F(22), fill=DIM)
    d.text((132, H-96), "拿原始K线图直接数分型 —— 中间那根可能早被合并掉了，会多数或漏数", font=F(24), fill=AM)


def build():
    """画整张卡，返回 PIL Image。"""
    set_size(W, H)
    im = Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im,"RGBA")
    draw_title(d)
    draw_cases(d)
    draw_rule(d)
    draw_edges(d)
    draw_foot(d)
    return im


def main():
    im = build()
    im.save(OUT + OUTNAME)
    print("ok", im.size)


if __name__ == "__main__":
    main()
