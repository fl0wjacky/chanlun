"""总纲④ 给小栋那页的三张图（只读，不带站名路径）。用法：python figs.py <输出目录>"""
import sys, os, json, gzip, datetime as D
sys.path[:0] = [os.getcwd(), "tools"]
from PIL import Image, ImageDraw, ImageFont
from core.analyze import analyze
import core.trend as T
import config
from config import tick_of
OUT = sys.argv[1]
F = ImageFont.truetype(config._pick_font(), 17); FS = ImageFont.truetype(config._pick_font(), 13)
BG, GRID, TXT, MUT = (24, 26, 32), (44, 47, 56), (225, 228, 235), (130, 135, 150)
RAW, STD, BOUND, BOX, RED = (150, 155, 170), (240, 170, 40), (90, 180, 255), (240, 170, 40), (240, 80, 80)
snap = json.loads(gzip.open(os.environ["LIVE15"]).read())

def ts(bars, i): return D.datetime.fromtimestamp(bars[i]["t"] / 1000, D.timezone.utc).strftime("%Y-%m-%d %H:%M")

class Panel:
    def __init__(s, img, box, bars, i0, i1, title):
        s.d = ImageDraw.Draw(img); s.x0, s.y0, s.x1, s.y1 = box; s.bars, s.i0, s.i1 = bars, i0, i1
        lo = min(b["l"] for b in bars[i0:i1 + 1]); hi = max(b["h"] for b in bars[i0:i1 + 1]); pad = (hi - lo) * .06
        s.lo, s.hi = lo - pad, hi + pad
        s.d.rectangle(box, outline=GRID)
        for k in range(5):
            p = s.lo + (s.hi - s.lo) * k / 4; y = s.Y(p)
            s.d.line([(s.x0, y), (s.x1, y)], fill=GRID); s.d.text((s.x1 + 4, y - 7), "%.2f" % p, font=FS, fill=MUT)
        s.d.text((s.x0, s.y0 - 26), title, font=F, fill=TXT)
        s.d.text((s.x0, s.y1 + 4), ts(bars, i0), font=FS, fill=MUT)
        s.d.text((s.x1 - 120, s.y1 + 4), ts(bars, i1), font=FS, fill=MUT)
        step = max(1, (i1 - i0) // 1400)
        for i in range(i0, i1 + 1, step):
            seg = bars[i:i + step]; x = s.X(i)
            s.d.line([(x, s.Y(max(b["h"] for b in seg))), (x, s.Y(min(b["l"] for b in seg)))], fill=(70, 74, 86))
    def X(s, i): return s.x0 + (i - s.i0) * (s.x1 - s.x0) / max(1, s.i1 - s.i0)
    def Y(s, p): return s.y1 - (p - s.lo) * (s.y1 - s.y0) / (s.hi - s.lo)
    def poly(s, segs, col, w):
        for a, b, pa, pb in segs:
            if b < s.i0 or a > s.i1: continue
            s.d.line([(s.X(a), s.Y(pa)), (s.X(b), s.Y(pb))], fill=col, width=w)
    def vline(s, i, col, label, dy=0):
        if s.i0 <= i <= s.i1:
            x = s.X(i)
            for y in range(int(s.y0), int(s.y1), 8): s.d.line([(x, y), (x, y + 4)], fill=col, width=2)
            s.d.text((x + 4, s.y0 + 4 + dy), label, font=FS, fill=col)
    def box(s, a, b, lo, hi, col, label=""):
        s.d.rectangle([s.X(a), s.Y(hi), s.X(b), s.Y(lo)], outline=col, width=2)
        if label: s.d.text((s.X(a) + 2, s.Y(hi) - 16), label, font=FS, fill=col)

def run(bars, tk, n=None):
    r = analyze(bars[:n] if n else bars, tick=tick_of(tk)); return r, T.trend_v3(r), T.find_bounds(r)["done"]

def stdsegs(done): return [(d["i0"], d["i1"], d["p0"], d["p1"]) for d in done]

# ① AAPL 15m H 345.38：撤回前、撤回后
bars = snap["AAPLUSDT 15m"]["bars"]; tk = "aaplusdt_.json"
rF, vF, _ = run(bars, tk)
R = vF["retracted"][0]; B = R["bar"]
grid = sorted({p["i1"] + 1 for p in rF["pens"] if R["pullback_end_bar"] <= p["i1"] <= R["retracted_bar"] + 600})
has = lambda n: any(b["bar"] == B for b in run(bars, tk, n)[1]["bounds"])
# 逐根找：确立＝第一次出现的前缀，撤回＝其后第一次消失的前缀（先按笔粗找，再在区间里逐根）
g1 = next(n for n in grid if has(n)); lo = max(0, g1 - 400)
t1 = next(n for n in range(lo, g1 + 1) if has(n))
g2 = next(n for n in grid if n > g1 and not has(n)); gp = max(n for n in grid if n < g2)
t2 = next(n for n in range(gp, g2 + 1) if not has(n)); k2 = t2 - 1
lo_i, hi_i = max(0, B - 2500), min(len(bars) - 1, t2 + 600)
img = Image.new("RGB", (1700, 1060), BG); d = ImageDraw.Draw(img)
d.text((20, 12), "① 已确认的分界又被撤回（D2-7）· AAPLUSDT 15m · H 345.38（10-07 快照）", font=F, fill=TXT)
for row, (n, tag) in enumerate(((k2, "撤回前：看到第 %d 根 K 线（%s）为止，H 345.38 是已确立的分界" % (k2 - 1, ts(bars, k2 - 1))),
                                  (t2, "撤回后：多看到第 %d 根 K 线（%s），H 345.38 被撤回" % (t2 - 1, ts(bars, t2 - 1))))):
    r, v, done = run(bars, tk, n)
    P = Panel(img, (60, 80 + row * 500, 1600, 520 + row * 500), bars, lo_i, hi_i, tag)
    d.rectangle([P.X(n), P.y0 + 1, P.x1 - 1, P.y1 - 1], fill=(30, 32, 38))
    d.text((P.X(n) + 6, P.y1 - 22), "还没走出来", font=FS, fill=MUT)
    P.poly(stdsegs(done), STD, 2)
    for b in v["bounds"]: P.vline(b["bar"], BOUND, "%s %.2f" % (b["kind"], b["price"]))
    if row == 0: P.vline(t1 - 1, (110, 210, 120), "确立于 %s（这根收出来时）" % ts(bars, t1 - 1), dy=40)
    x = P.X(n - 1); d.line([(x, P.y0), (x, P.y1)], fill=RED, width=3)
    d.text((x - 6, P.y0 + 60), "当下（%s）" % ts(bars, n - 1), font=FS, fill=RED, anchor="ra")
img.save(os.path.join(OUT, "zg4-1-retract.png"))
print("① 确立首见前缀", t1, ts(bars, t1 - 1), "撤回前最后", k2, "撤回于", t2, ts(bars, t2 - 1))

# ② zec_4h：原始线段 vs 标准化线段
bars = json.load(open("data/zec_4h.json")); r, v, done = run(bars, "zec_4h.json")
raw = [(s["i0"], s["i1"], s["p0"], s["p1"]) for s in r["segs"]]
img = Image.new("RGB", (1700, 620), BG); d = ImageDraw.Draw(img)
d.text((20, 12), "② 两套线段 · data/zec_4h：灰＝图上画的原始线段，橙＝分走势用的标准化线段（D2-0）", font=F, fill=TXT)
P = Panel(img, (60, 80, 1600, 560), bars, 0, min(len(bars) - 1, 900), "前 900 根；端点不同的段：%d / %d" % (
    len({(a, b) for a, b, _, _ in stdsegs([x for x in done if not x.get('live')])} - {(a, b) for a, b, _, _ in raw}), len([x for x in done if not x.get('live')])))
P.poly(raw, RAW, 3); P.poly(stdsegs(done), STD, 2)
for b in v["bounds"]: P.vline(b["bar"], BOUND, "%s %.2f" % (b["kind"], b["price"]))
img.save(os.path.join(OUT, "zg4-2-twosets.png"))

# ③ AAPL 15m 段 4：一段盘整里 7 个中枢
bars = snap["AAPLUSDT 15m"]["bars"]; r, v, done = run(bars, "aaplusdt_.json")
g = 4; sg = v["segments"][g]; zz = [z for z in v["seg_centers"] if z["seg"] == g]
img = Image.new("RGB", (1700, 620), BG); d = ImageDraw.Draw(img)
d.text((20, 12), "③ 一段盘整里 %d 个本级别中枢 · AAPLUSDT 15m 第 %d 段（%s 盘整，没升级）" % (len(zz), g, "中间段"), font=F, fill=TXT)
P = Panel(img, (60, 80, 1600, 560), bars, max(0, sg["i0"] - 300), min(len(bars) - 1, sg["i1"] + 300),
          "%s → %s；框＝ZD～ZG，编号后是跟前一个的关系" % (ts(bars, sg["i0"]), ts(bars, sg["i1"])))
P.poly(stdsegs(done), STD, 2)
for k, z in enumerate(zz): P.box(z["X0"], z["X1"], z["ZD"], z["ZG"], BOX, "%d %s" % (k + 1, z.get("rel")))
for b in v["bounds"]: P.vline(b["bar"], BOUND, "%s %.2f" % (b["kind"], b["price"]))
img.save(os.path.join(OUT, "zg4-3-centers.png"))
print("③", [(z["X0"], z["X1"], z["ZD"], z["ZG"], z.get("rel")) for z in zz])
