import sys, math, json, gzip, datetime as D; sys.path[:0]=['.','tools']
from PIL import Image, ImageDraw, ImageFont
import config
from core.analyze import analyze
from core import trend as T
from core.signals import signals
from trend_check import load
name, out = sys.argv[1], sys.argv[2]
if name.startswith("data/"):
    bars = load(name); tk = config.tick_of(name.split("/")[-1]); title = name + " 冻结夹具"
else:
    bars = json.loads(gzip.open('/tmp/live15.json.gz').read())[name]["bars"]; tk = config.tick_of("zec_.json"); title = "线上 " + name + "（10-07 快照）"
r = analyze(bars, tick=tk)
T._XZD_SECOND = False; A = T.trend_v3(r, reading="A")
T._XZD_SECOND = True;  Bv = T.trend_v3(r, reading="A")
sig = [s for s in signals(r) if s["kind"] in ("一买", "二买", "三买", "一卖", "二卖", "三卖")]
ts = lambda i: D.datetime.fromtimestamp(bars[i]["t"]/1000, D.timezone.utc).strftime('%m-%d %H:%M')
ix = lambda s: next(i for i, b in enumerate(bars) if D.datetime.fromtimestamp(b["t"]/1000, D.timezone.utc).strftime('%m-%d') >= s)
b0, b1 = ix("07-12"), ix("09-06") - 1
font = ImageFont.truetype(config._pick_font(), 15); fsm = ImageFont.truetype(config._pick_font(), 12)
W, PH, ML, MR, MT = 1800, 520, 70, 20, 34
img = Image.new("RGB", (W, PH * 2 + 40), "white"); d = ImageDraw.Draw(img)
seg = bars[b0:b1 + 1]; lo = min(b["l"] for b in seg); hi = max(b["h"] for b in seg); pad = (hi - lo) * .06; lo -= pad; hi += pad
def label(x, y, t, c):
    w = d.textlength(t, font=fsm); d.rectangle([x - 2, y - 1, x + w + 2, y + 14], fill="white"); d.text((x, y), t, fill=c, font=fsm)
def panel(k, v, tag, extra):
    y0 = k * (PH + 20); X = lambda i: ML + (i - b0) * (W - ML - MR) / (b1 - b0); Y = lambda p: y0 + MT + (hi - p) * (PH - MT - 30) / (hi - lo)
    p = math.ceil(lo / 50) * 50
    while p <= hi: d.line([(ML, Y(p)), (W - MR, Y(p))], fill=(225, 225, 225)); d.text((4, Y(p) - 7), "%g" % p, fill=(90, 90, 90), font=fsm); p += 50
    d.text((ML, y0 + 6), "%s · %s～%s UTC · 6 根 · %s" % (title, ts(b0), ts(b1), tag), fill="black", font=font)
    for i in range(b0, b1 + 1):
        b = bars[i]; c = (200, 60, 60) if b["c"] >= b["o"] else (40, 150, 90); d.line([(X(i), Y(b["h"])), (X(i), Y(b["l"]))], fill=c)
    for bd in v["bounds"]:
        if not b0 <= bd["bar"] <= b1: continue
        x = X(bd["bar"])
        for yy in range(int(y0 + MT), int(y0 + PH - 30), 8): d.line([(x, yy), (x, yy + 4)], fill=(120, 40, 160), width=2)
        label(x + 6, y0 + MT + 2, "分界 %s %.2f（%s）" % (bd["kind"], bd["price"], bd.get("death", "")), (120, 40, 160))
    for s in sig:
        if not b0 <= s["bar"] <= b1: continue
        x, y = X(s["bar"]), Y(s["price"]); c = (40, 110, 200)
        d.polygon([(x, y + 4), (x - 6, y + 14), (x + 6, y + 14)] if "买" in s["kind"] else [(x, y - 4), (x - 6, y - 14), (x + 6, y - 14)], fill=c)
        label(x + 8, y + (8 if "买" in s["kind"] else -24), s["kind"] + " %.2f" % s["price"], c)
    if extra:
        for s in v.get("xzd_seconds", []):
            if not b0 <= s["bar"] <= b1: continue
            x, y = X(s["bar"]), Y(s["price"])
            d.ellipse([x - 16, y - 16, x + 16, y + 16], outline=(230, 120, 0), width=3)
            kb = s.get("known_bar")
            label(x - 40, y + 30, "★ 新加：%s %.2f @%s（%s%s）" % (s["kind"], s["price"], ts(s["bar"]), s["why"],
                  "，%s 才知道" % ts(kb) if kb is not None else ""), (230, 120, 0))      # 往下错开，别压三买的标签
panel(0, A, "改前（main：小转大没有二类点）", False)
panel(1, Bv, "改后（M29：小转大那一刀之后紧接的第二段终点出二买，L53；放走势层 xzd_seconds）", True)
d.text((ML, PH * 2 + 24), "蓝三角＝信号层买卖点（这一批段级没有变化）；紫虚线＝走势分界；橙圈＝新加的小转大二买", fill=(60, 60, 60), font=fsm)
img.save(out); print("ok", name, [(s["price"], ts(s["bar"])) for s in Bv["xzd_seconds"]])
