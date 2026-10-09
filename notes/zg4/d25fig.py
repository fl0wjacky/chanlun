"""D2-5 档 3 前后对照：data/zec30_cut，刀 L@6805，档 0 标「比不了」无二类 ↔ 档 3 改判、多一个小转大二买。定稿口径＋锁。不带站名。"""
import sys, os, json, datetime as D
sys.path[:0] = [os.getcwd(), "tools"]
from PIL import Image, ImageDraw, ImageFont
from core.analyze import analyze
import core.trend as T, core.pen as PEN
import config
from config import tick_of
T.SAME_LEVEL = T.SAME_LEVEL_D2 = True; T.SAME_LEVEL_D6 = "fallback"; T.SL_FIRST_EXEMPT = True; T.SAME_LEVEL_DEATH = True; PEN.PEN_FINAL_LOCK = True
F = ImageFont.truetype(config._pick_font(), 17); FS = ImageFont.truetype(config._pick_font(), 13)
bars = json.load(open("data/zec30_cut.json")); r = analyze(bars, tick=tick_of("zec30_cut.json"))
I0, I1, CUT = 6560, 7120, 6805
W, H, PADL, PADR, PANEL = 1400, 380, 20, 90, 30
ts = lambda i: D.datetime.fromtimestamp(bars[i]["t"] / 1000, D.timezone.utc).strftime("%Y-%m-%d %H:%M")
img = Image.new("RGB", (W, 2 * H + 40), (18, 20, 26)); d = ImageDraw.Draw(img)
lo = min(b["l"] for b in bars[I0:I1]); hi = max(b["h"] for b in bars[I0:I1])
for row, fill in enumerate((0, 3)):
    T.D25_FILL = fill; v = T.trend_v3(r); T.D25_FILL = 0
    y0, y1 = row * H + 40 + PANEL, row * H + H - 10
    X = lambda i: PADL + (i - I0) * (W - PADL - PADR) / (I1 - I0)
    Y = lambda p: y1 - (p - lo) * (y1 - y0) / (hi - lo)
    for i in range(I0, I1):
        b = bars[i]; c = (220, 80, 80) if b["c"] < b["o"] else (80, 190, 120)
        d.line([(X(i), Y(b["h"])), (X(i), Y(b["l"]))], fill=c)
    for p in r["pens"]:
        if p["i1"] >= I0 and p["i0"] <= I1:
            d.line([(X(max(p["i0"], I0)), Y(p["p0"] if p["i0"] >= I0 else p["p1"])), (X(min(p["i1"], I1)), Y(p["p1"]))], fill=(140, 140, 160))
    for z in v["seg_centers"]:
        if z["X1"] >= I0 and z["X0"] <= I1:
            d.rectangle([X(max(z["X0"], I0)), Y(z["ZG"]), X(min(z["X1"], I1)), Y(z["ZD"])], outline=(200, 170, 60))
    for b in v["bounds"]:
        if I0 <= b["bar"] <= I1:
            x = X(b["bar"]); d.line([(x, y0), (x, y1)], fill=(230, 230, 230) if b["rule"] == "D2-2" else (110, 110, 120))
            if b["rule"] == "D2-2":
                d.text((x + 4, y0 + 2), "%s %s" % (b.get("death"), "" if b.get("state") == "confirmed" else "（待确认）"), font=FS, fill=(240, 240, 240))
    for x2 in v.get("xzd_seconds", []):
        if I0 <= x2["bar"] <= I1:
            xx, yy = X(x2["bar"]), Y(x2["price"])
            d.polygon([(xx, yy + 4), (xx - 7, yy + 16), (xx + 7, yy + 16)], fill=(80, 200, 255))
            d.text((xx + 9, yy + 4), "%s %s" % (x2["kind"], x2["price"]), font=FS, fill=(80, 200, 255))
    cut = next(b for b in v["bounds"] if b["bar"] == CUT)
    d.text((PADL, row * H + 40), "%s：刀 L@%d（%s）死因 = %s　｜　%s" % ("D2-5 档 0（现行）" if fill == 0 else "D2-5 档 3（-1→-2→-3）",
           CUT, ts(CUT), cut.get("death"), cut.get("death_why")), font=F, fill=(235, 235, 235))
d.text((PADL, 8), "data/zec30_cut · 30m · %s ～ %s · 同级别定稿口径＋笔锁 · 刀和走势段两格逐项相同，只差标注和二类" % (ts(I0), ts(I1 - 1)), font=F, fill=(200, 200, 210))
out = sys.argv[1]; img.save(out); print(out)
