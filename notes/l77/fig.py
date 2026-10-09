# L77 第二支前后图：main（左上）vs land-b5（下），同一窗口、同一把尺。用法：python fig.py <main树> <b5树> <data/zec_1h.json|快照 ZECUSDT 1h> <输出.png>
import sys, json, gzip, subprocess, datetime as D
from PIL import Image, ImageDraw, ImageFont
main_root, b5_root, name, out = sys.argv[1:5]
CODE = r'''
import sys, json, gzip; root=sys.argv[1]; name=sys.argv[2]; sys.path[:0]=[root, root+"/tools"]
from core.analyze import analyze
from trend_check import load
import config
if name.startswith("data/"):
    bars=load(root+"/"+name); tk=config.tick_of(name.split("/")[-1])
else:
    bars=[dict(t=x["t"],o=x["o"],h=x["h"],l=x["l"],c=x["c"]) for x in json.loads(gzip.open("/tmp/live15.json.gz").read())[name]["bars"]]; tk=config.tick_of("zecusdt_.json")
r=analyze(bars,tick=tk)
print(json.dumps(dict(bars=bars, pens=[(p["i0"],p["i1"],p["p0"],p["p1"]) for p in r["pens"]],
    segs=[(s["PI0"],s["PI1"],s["i0"],s["i1"],s["p0"],s["p1"],s.get("case"),bool(s.get("live"))) for s in r["segs"]])))
'''
def run(root):
    py = "/Users/agent/.cumora/agents/bram-9d29/workspace/deploy-chanlun-venv/bin/python"
    o = subprocess.run([py, "-c", CODE, root, name], capture_output=True, text=True, cwd=root)
    return json.loads(o.stdout.strip().splitlines()[-1])
A, B = run(main_root), run(b5_root)
bars = A["bars"]
ts = lambda i: D.datetime.fromtimestamp(bars[i]["t"]/1000, D.timezone.utc)
ix = lambda s: next(i for i in range(len(bars)) if ts(i).strftime("%m-%d") >= s)
b0, b1 = ix("03-10"), ix("04-06") - 1
sa = {tuple(s[:2]) for s in A["segs"]}; sb = {tuple(s[:2]) for s in B["segs"]}
sys.path[:0] = [main_root]; import config
font = ImageFont.truetype(config._pick_font(), 16); fsm = ImageFont.truetype(config._pick_font(), 13)
W, PH, ML, MR, MT = 1700, 470, 70, 20, 40
img = Image.new("RGB", (W, PH * 2 + 100), "white"); d = ImageDraw.Draw(img)
seg = bars[b0:b1 + 1]; lo = min(b["l"] for b in seg); hi = max(b["h"] for b in seg); pad = (hi - lo) * .07; lo -= pad; hi += pad
title = ("data/zec_1h.json（冻结夹具）" if name.startswith("data/") else "线上 ZECUSDT 1h（10-07 快照）") + "　L77 第二支：前 main 3bb4de4 ／ 后 land-b5"
d.text((ML, 6), title, fill="black", font=font)
def panel(k, R, tag, other):
    y0 = 34 + k * (PH + 18)
    pi = Image.new("RGB", (W, PH), "white"); q = ImageDraw.Draw(pi)       # 每格一张小图，贴回去 ⇒ 超出窗口的自然裁掉，不串到另一格
    X = lambda i: ML + (i - b0) * (W - ML - MR) / (b1 - b0); Y = lambda p: MT + (hi - p) * (PH - MT - 26) / (hi - lo)
    clampy = lambda y: max(MT, min(PH - 40, y))
    for i in range(b0, b1 + 1):
        b = bars[i]
        q.line([X(i), Y(b["h"]), X(i), Y(b["l"])], fill="#ccc")
    for (i0, i1, p0, p1) in R["pens"]:
        if i1 < b0 or i0 > b1: continue
        q.line([X(i0), Y(p0), X(i1), Y(p1)], fill="#999", width=1)
    for (P0, P1, i0, i1, p0, p1, case, live) in R["segs"]:
        if i1 < b0 or i0 > b1: continue
        changed = (P0, P1) not in other
        col = ("#e07b00" if case == 4 else "#1f5fd1") if changed else "#555"
        q.line([X(i0), Y(p0), X(i1), Y(p1)], fill=col, width=4 if changed else 2)
        if changed:
            lab = "%s→%s%s" % (p0, p1, "（L77 合段）" if case == 4 else "")
            ly = clampy(Y(p1) - 18)
            if abs(ly + 7 - Y(205.6)) < 12:               # 别压在 V 的红线上（Iris 00:24）：往上挪开
                ly = Y(205.6) - 28
            q.text((max(ML + 4, X(i0) + 4), ly), lab, fill=col, font=fsm)
    q.line([ML, Y(205.6), W - MR, Y(205.6)], fill="#d22", width=2)
    # 画框外的一律刷白（笔、段的线不许越出框：左边 y 轴、顶上，Iris 00:22）
    top, bot = MT - 8, PH - 18
    q.rectangle([0, 0, ML - 1, PH], fill="white"); q.rectangle([W - MR + 1, 0, W, PH], fill="white")
    q.rectangle([0, 0, W, top - 1], fill="white"); q.rectangle([0, bot + 1, W, PH], fill="white")
    q.rectangle([ML, top, W - MR, bot], outline="#bbb")
    q.text((ML + 6, 8), tag, fill="black", font=font)
    q.text((W - MR - 110, Y(205.6) + 3), "V = 205.6", fill="#d22", font=fsm)
    for i in range(b0, b1 + 1, 24 * 3):
        q.text((X(i) - 20, PH - 16), ts(i).strftime("%m-%d"), fill="#666", font=fsm)
    step = 30
    p = (int(lo // step) + 1) * step
    while p < hi:                                         # 刻度取整数（Iris 00:22）
        q.text((8, Y(p) - 7), str(p), fill="#666", font=fsm)
        q.line([ML - 4, Y(p), ML, Y(p)], fill="#999")
        p += step
    img.paste(pi, (0, y0))
panel(0, A, "前：main 3bb4de4（旧规则：L78 ① 型「旧段延续」，跌到 205.07 那一下算在这一段里，205.6→257.84）", sb)
panel(1, B, "后：land-b5（L77 第二支：X＋A＋R 合成 205.6→247.61，之后转头创新低到 205.07 是下一段；走势分界不变）", sa)
d.text((ML, 34 + 2 * (PH + 18) + 4), "图注：合段 ＝ 第一笔 X ＋ 走势 A ＋ 反弹 R，收在反弹终点（L77）；段内最高点 289.31 是 X 的终点。原文允许线段终点不是段内极值（L70:34）。", fill="#333", font=fsm)
img.save(out)
print("saved", out)
