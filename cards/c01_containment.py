#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""概念卡 01 包含处理"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cards.base import *

W, H = 1400, 2080                    # 卡片尺寸；模块常量，各段函数直接用
OUTNAME = "c01_包含处理.png"

def cell(d, x0, x1, yt_title, y0, y1, yl, title, pmin, pmax,
         b1, b2, b3, merged, lines, accent):
    d.text((x0+2, yt_title), title, font=f_n, fill=accent)
    m = Mini(d, x0+30, y0, x1-36, y1, pmin, pmax)
    n = 6
    X = lambda i: m.X(i, n); Y = m.Y
    H1, L1 = b1[1], b1[2]; H2, L2 = b2[1], b2[2]; H3, L3 = b3[1], b3[2]
    # 虚线：第1根灰 / 第2根橙 / 第3根青
    dash(d, X(0)-40, X(2)+64, Y(H1), GY, 3); dash(d, X(0)-40, X(2)+64, Y(L1), GY, 3)
    for v in (H2, L2): dash(d, X(1)-62, X(2)+64, Y(v), AM, 3)
    for v in (H3, L3): dash(d, X(1)-62, X(2)+64, Y(v), CY, 3)
    # 三根K线（连续：前收 = 后开）
    for i, bb in ((0, b1), (1, b2), (2, b3)):
        o,h,l,c = bb
        col = (38,166,154) if c >= o else (239,83,80)
        d.line([X(i), Y(h), X(i), Y(l)], fill=col, width=4)
        d.rectangle([X(i)-23, Y(max(o,c)), X(i)+23, Y(min(o,c))], fill=col)
    # 连续性标记
    d.ellipse([X(0)+34, Y(b1[3])-6, X(0)+46, Y(b1[3])+6], outline=GR, width=2)
    d.ellipse([X(1)-12, Y(b2[0])-6, X(1), Y(b2[0])+6], outline=GR, width=2)
    d.ellipse([X(1)+34, Y(b2[3])-6, X(1)+46, Y(b2[3])+6], outline=GR, width=2)
    d.ellipse([X(2)-12, Y(b3[0])-6, X(2), Y(b3[0])+6], outline=GR, width=2)
    d.ellipse([X(0)-7, Y(H1)-7, X(0)+7, Y(H1)+7], fill=GY)
    d.ellipse([X(1)-7, Y(H2)-7, X(1)+7, Y(H2)+7], fill=AM)
    d.ellipse([X(2)-7, Y(H3)-7, X(2)+7, Y(H3)+7], fill=CY)
    # 合并箭头 + 结果
    ax = X(3); ay = (Y(pmin)+Y(pmax))//2
    d.line([ax-26, ay, ax+22, ay], fill=accent, width=5)
    d.polygon([(ax+32, ay), (ax+16, ay-11), (ax+16, ay+11)], fill=accent)
    rx0, rx1 = X(4)-46, X(5)+46
    d.rectangle([rx0, Y(merged[0]), rx1, Y(merged[1])], fill=accent+(58,), outline=accent, width=4)
    d.line([rx0-40, Y(merged[0]), rx1+16, Y(merged[0])], fill=accent, width=2)
    d.line([rx0-40, Y(merged[1]), rx1+16, Y(merged[1])], fill=accent, width=2)
    t1="上界 %g"%merged[0]; t2="下界 %g"%merged[1]
    d.text(((rx0+rx1)/2 - d.textlength(t1,font=f_b)/2, Y(merged[0])-44), t1, font=f_b, fill=accent)
    d.text(((rx0+rx1)/2 - d.textlength(t2,font=f_b)/2, Y(merged[1])-38), t2, font=f_b, fill=accent)
    for k,(txt,col) in enumerate(lines):
        d.text((x0+2, yl + k*32), txt, font=f_t, fill=col)
    # 图例：三根颜色
    lx = x0+2; ly = yl + 3*32
    for nm,col in (("第1根",GY),("第2根",AM),("第3根",CY)):
        d.rectangle([lx, ly+8, lx+22, ly+24], fill=col)
        d.text((lx+28, ly+5), nm, font=f_t, fill=MU); lx += 118


def draw_title(d):
    """页眉：编号 + 名称 + 一句话（本卡自带，不走 newcard）"""
    d.text((56,34), "01", font=F(38), fill=(70,78,96))
    d.text((132,24), "包含处理（K线标准化）", font=F(58), fill=TX)
    d.text((136,104), "四种情形都画上「定方向的那根」；示意图约定：前一根收盘 = 后一根开盘", font=F(28), fill=MU)
    d.line([56,168,W-56,168], fill=LINE, width=2)


def draw_scope(d):
    """A 口径：只看最高价与最低价"""
    d.rounded_rectangle([56, 196, W-56, 592], 20, fill=PANEL, outline=LINE, width=2)
    d.rounded_rectangle([80, 214, 470, 264], 10, fill=(GR[0],GR[1],GR[2],46))
    d.text((100, 222), "口径：只看最高价与最低价", font=f_p, fill=GR)
    ma = Mini(d, 100, 300, 660, 545, 94, 106)
    x=300; o,h,l,c = 97.0,105.0,95.5,100.5
    d.line([x,ma.Y(h),x,ma.Y(l)],fill=(38,166,154),width=5)
    d.rectangle([x-38,ma.Y(max(o,c)),x+38,ma.Y(min(o,c))],fill=(38,166,154))
    d.line([x-90,ma.Y(h),x+120,ma.Y(h)],fill=GR,width=2)
    d.line([x-90,ma.Y(l),x+120,ma.Y(l)],fill=GR,width=2)
    d.text((x+130,ma.Y(h)-14), "最高价 105　✓ 参与计算", font=f_n, fill=GR)
    d.text((x+130,ma.Y(l)-14), "最低价 95.5　✓ 参与计算", font=f_n, fill=GR)
    d.line([x-90,ma.Y(o),x+120,ma.Y(o)],fill=DIM,width=2)
    d.line([x-90,ma.Y(c),x+120,ma.Y(c)],fill=DIM,width=2)
    d.text((x+130,ma.Y(o)-14), "开盘价 97　× 不参与", font=f_n, fill=DIM)
    d.text((x+130,ma.Y(c)-14), "收盘价 100.5　× 不参与", font=f_n, fill=DIM)
    d.text((100, 270), "一根普通K线上的四个价", font=f_n, fill=MU)
    d.text((100, 548), "第 65 课：「用[di,gi]记号第 i 根 K 线的最低和最高构成的区间」；第 62 课：「这里不分阳线阴线，只看 K 线高低点」。", font=f_n, fill=TX)


def draw_up(d):
    """B 向上过程：情形 A / B"""
    d.rounded_rectangle([56, 612, W-56, 1134], 20, fill=PANEL, outline=LINE, width=2)
    d.rounded_rectangle([80, 630, 320, 680], 10, fill=(AM[0],AM[1],AM[2],46))
    d.text((102, 638), "向上过程", font=f_p, fill=AM)
    d.text((344, 638), "口诀：向上全取大（高取 max，低也取 max）", font=f_n, fill=AM)
    A1=(95.2,98.0,95.0,97.0); A2=(97.0,102.0,96.0,100.0); A3=(100.0,100.5,96.5,97.5)
    B1=(95.2,98.0,95.0,97.0); B2=(97.0,100.0,96.5,99.0);  B3=(99.0,102.0,95.5,96.5)
    cell(d, 76, 690, 684, 710, 990, 994, "情形 A：第 2 根包住第 3 根（先大后小）",
         94, 103, A1, A2, A3, (102, 96.5),
         [("方向：第2根(102/96) 高于 第1根(98/95) → 向上", GY),
          ("包含：第2根(96~102) 完整罩住 第3根(96.5~100.5)", AM),
          ("合并：高 max(102,100.5)=102　低 max(96,96.5)=96.5", AM)], AM)
    cell(d, 710, 1324, 684, 710, 990, 994, "情形 B：第 3 根包住第 2 根（先小后大）",
         94, 103, B1, B2, B3, (102, 96.5),
         [("方向：第2根(100/96.5) 高于 第1根(98/95) → 向上", GY),
          ("包含：第3根(95.5~102) 完整罩住 第2根(96.5~100)", AM),
          ("合并：高 max(100,102)=102　低 max(96.5,95.5)=96.5", AM)], AM)


def draw_down(d):
    """C 向下过程：情形 C / D"""
    d.rounded_rectangle([56, 1150, W-56, 1674], 20, fill=PANEL, outline=LINE, width=2)
    d.rounded_rectangle([80, 1168, 320, 1218], 10, fill=(BL[0],BL[1],BL[2],56))
    d.text((102, 1176), "向下过程", font=f_p, fill=LB)
    d.text((344, 1176), "口诀：向下全取小（高取 min，低也取 min）", font=f_n, fill=LB)
    C1=(105.0,106.0,104.0,104.4); C2=(104.4,105.0,102.0,102.5); C3=(102.5,104.6,102.4,104.0)
    D1=(105.0,106.0,104.0,104.4); D2=(104.4,104.6,102.4,102.6); D3=(102.6,105.0,102.0,104.4)
    cell(d, 76, 690, 1222, 1248, 1528, 1532, "情形 C：第 2 根包住第 3 根（先大后小）",
         101.5, 106.5, C1, C2, C3, (104.6, 102.0),
         [("方向：第2根(105/102) 低于 第1根(106/104) → 向下", GY),
          ("包含：第2根(102~105) 完整罩住 第3根(102.4~104.6)", LB),
          ("合并：高 min(105,104.6)=104.6　低 min(102,102.4)=102.0", LB)], LB)
    cell(d, 710, 1324, 1222, 1248, 1528, 1532, "情形 D：第 3 根包住第 2 根（先小后大）",
         101.5, 106.5, D1, D2, D3, (104.6, 102.0),
         [("方向：第2根(104.6/102.4) 低于 第1根(106/104) → 向下", GY),
          ("包含：第3根(102~105) 完整罩住 第2根(102.4~104.6)", LB),
          ("合并：高 min(104.6,105)=104.6　低 min(102.4,102)=102.0", LB)], LB)


def draw_conclusion(d):
    """D 结论：谁包谁不影响结果"""
    callout(d, 1688, 1912, GR, 26)
    d.text((86, 1706), "★ 谁包谁，不影响结果；连续性只影响画图，不影响计算", font=f_p, fill=GR)
    d.text((86, 1750), "A、B 两根长得不一样、包的方向也相反，合并出来都是「高 102 / 低 96.5」；C、D 同理。", font=f_n, fill=TX)
    d.text((86, 1786), "公式只读四个数（两根各自的高与低）+ 一个方向，不关心谁罩住谁。", font=f_n, fill=TX)
    d.text((86, 1822), "方向由「被合并的前一根（第n根）」与「它前面那根（第n-1根）」比较决定，而不是被合并的两根互相比。", font=f_n, fill=TX)
    # 这行原来 1622px、从 x=86 一路画到 x=1708（**出画布 308px，出 56px 边距线 364px**）——
    # 是我写的，当时没量。改短到 1190px（Droid 97320619 / Noto 2c76254f 都 ≤1191，余 ~67px）。
    # 量法见 tools/cardfit.py（把 ImageDraw.text 包起来，量每一处真画上去的字）。
    d.text((86, 1858), "示意图按 7×24 连市画；股票有跳空时这条不成立，但跳空不改变「谁包谁」——只要求断点先处理（页脚陷阱②）。", font=f_n, fill=CY)


def draw_foot(d):
    """页脚：原文 + 陷阱（本卡配色与 base.foot 略有不同，保留原样）"""
    d.line([56, H-150, W-56, H-150], fill=LINE, width=2)
    d.text((56, H-136), "原文", font=F(22), fill=DIM)
    d.text((132, H-136), "第 65 课《再说说分型、笔、线段》", font=F(24), fill=(168,176,192))
    d.text((56, H-96), "陷阱", font=F(22), fill=DIM)
    d.text((132, H-96), "① 方向看「第n根 vs 第n-1根」，不是看被合并的两根彼此；漏掉第n-1根，方向就无从判断", font=F(24), fill=AM)
    d.text((132, H-56), "② A股/港股必须先 core.preprocess（前复权 + 会话/停牌/除权断点），否则 gap 会跨市场合并", font=F(24), fill=AM)


def build():
    """画整张卡，返回 PIL Image。"""
    set_size(W, H)
    im = Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im,"RGBA")
    draw_title(d)
    draw_scope(d)
    draw_up(d)
    draw_down(d)
    draw_conclusion(d)
    draw_foot(d)
    return im


def main():
    im = build()
    im.save(OUT + OUTNAME)
    print("ok", im.size)


if __name__ == "__main__":
    main()
