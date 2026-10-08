"""R6 前后对比图：上＝读法 A（_R6_B=False），下＝读法 B。蜡烛＋线段中枢框＋分界竖虚线＋价格＋网格。
用法（在 wt 根目录）：python r6_ab.py <K线json或快照key> <bar0> <bar1> <out.png> [--snap path]"""
import sys, os, json, gzip
sys.path[:0] = [os.getcwd(), os.getcwd() + "/tools"]
from PIL import Image, ImageDraw, ImageFont
import config
from core.analyze import analyze
import core.trend as T
from trend_check import load

src, b0, b1, outp = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
if "--snap" in sys.argv:
    snap = json.loads(gzip.open(sys.argv[sys.argv.index("--snap") + 1]).read())
    bars = snap[src]["bars"]; tick = config.tick_of({"ZECUSDT": "zec", "BTCUSDT": "btc"}[src.split()[0]] + "_.json"); title = src
else:
    bars = load(src); tick = config.tick_of(os.path.basename(src)); title = os.path.basename(src)
r = analyze(bars, tick=tick)
B = r["bars"]
vs = {}
for flag in (False, True):
    T._R6_B = flag
    vs[flag] = T.trend_v3(r, reading="A")
T._R6_B = True
font = ImageFont.truetype(config._pick_font(), 15)
fsm = ImageFont.truetype(config._pick_font(), 12)
W, PH, ML, MR, MT = 1800, 520, 70, 20, 34
img = Image.new("RGB", (W, PH * 2 + 20), "white"); d = ImageDraw.Draw(img)
seg = B[b0:b1 + 1]
lo, hi = min(b["l"] for b in seg), max(b["h"] for b in seg); pad = (hi - lo) * 0.06; lo -= pad; hi += pad
def panel(k, v, label):
    y0 = k * (PH + 20)
    X = lambda i: ML + (i - b0) * (W - ML - MR) / max(1, b1 - b0)
    Y = lambda p: y0 + MT + (hi - p) * (PH - MT - 30) / (hi - lo)
    # 网格＋价格轴
    import math
    step = 10 ** math.floor(math.log10((hi - lo) / 6)); step *= 2 if (hi - lo) / step > 12 else 1
    p = math.ceil(lo / step) * step
    while p <= hi:
        d.line([(ML, Y(p)), (W - MR, Y(p))], fill=(225, 225, 225)); d.text((4, Y(p) - 7), ("%g" % p), fill=(90, 90, 90), font=fsm); p += step
    d.text((ML, y0 + 6), "%s  bar %d–%d  %s" % (title, b0, b1, label), fill="black", font=font)
    # 框
    for z in v["seg_centers"]:
        if z["X1"] < b0 or z["X0"] > b1: continue
        d.rectangle([X(max(z["X0"], b0)), Y(z["ZG"]), X(min(z["X1"], b1)), Y(z["ZD"])], outline=(40, 110, 200), width=2)
        d.text((X(max(z["X0"], b0)) + 3, Y(z["ZG"]) - 15), "%.2f–%.2f" % (z["ZD"], z["ZG"]), fill=(40, 110, 200), font=fsm)
    # 蜡烛
    cw = max(1, (W - ML - MR) / max(1, b1 - b0) * 0.6)
    for i in range(b0, b1 + 1):
        b = B[i]; x = X(i); up = b["c"] >= b["o"]; col = (200, 60, 60) if up else (40, 150, 90)
        d.line([(x, Y(b["h"])), (x, Y(b["l"]))], fill=col)
        if cw > 1.5: d.rectangle([x - cw / 2, Y(max(b["o"], b["c"])), x + cw / 2, Y(min(b["o"], b["c"]))], fill=col)
    # 分界
    for bd in v["bounds"]:
        if not b0 <= bd["bar"] <= b1: continue
        x, y = X(bd["bar"]), Y(bd["price"])
        for yy in range(int(y0 + MT), int(y0 + PH - 30), 8): d.line([(x, yy), (x, yy + 4)], fill=(120, 40, 160), width=2)
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(120, 40, 160))
        d.text((x + 6, y + (-20 if bd["kind"] == "H" else 6)), "%s %.2f @%d（回抽段终点 %d）" % (bd["kind"], bd["price"], bd["bar"], bd["pullback_end_bar"]), fill=(120, 40, 160), font=fsm)
    d.text((ML, y0 + PH - 24), "分界：%s" % ", ".join("%s %.2f@%d" % (b["kind"], b["price"], b["bar"]) for b in v["bounds"] if b0 <= b["bar"] <= b1), fill="black", font=fsm)
panel(0, vs[False], "读法 A（改前：只认起点不晚于 H 的中枢）")
panel(1, vs[True], "读法 B（改后：再加 H 之后、离开段之前已走完的中枢，取最近）")
img.save(outp); print(outp)
