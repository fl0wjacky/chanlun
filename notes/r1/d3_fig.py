# D-3 选 C「还可能被合并的那一截画虚线」示意图（Nova 10-09 11:51）：同一份 K 线截到前 N1、N2 根各跑一遍引擎，上下两格。
#   图上只画**标准化线段**（C：图上跟分界用同一套）。最后一条已完成的标准化线段画虚线 —— 它的终点还可能往后挪
#   （后面的线段走完以后，标准化会把端点挪到真正的极值、或者把相邻的并成一条）。下格是多走几根以后：那一条的终点真的挪了，
#   原来的终点留一个空心圈、箭头指到新的终点；挪完它变实线，新的最后一条接着画虚线。
#   python d3_fig.py --root <引擎仓> --file aaplusdt_1h.json --at 1248,1257 --from-bar 800 --out x.png
#   口径：同级别正式口径（跟分界那套一致）；开关只在进程里翻，仓里一个字不动。线段层本身不受这些开关影响。
import sys, os, json, argparse, math, datetime as DT
ap = argparse.ArgumentParser()
ap.add_argument('--root', required=True); ap.add_argument('--file', required=True)
ap.add_argument('--at', required=True); ap.add_argument('--from-bar', type=int, required=True); ap.add_argument('--out', required=True)
ap.add_argument('--title', default='D-3 选 C「后面还可能并进来的那一截画虚线」示意'); ap.add_argument('--note', default='')
a = ap.parse_args()
out = os.path.abspath(a.out)
sys.path[:0] = [a.root]; os.chdir(a.root)
import config
from core.analyze import analyze
import core.trend as TR
from render.style import BG, TX, MU
from PIL import Image, ImageDraw, ImageFont
for k, v in dict(SAME_LEVEL=True, SAME_LEVEL_D2=True, SAME_LEVEL_D6='fallback', SL_FIRST_EXEMPT=True, SAME_LEVEL_DEATH=True, D25_FILL=3).items(): setattr(TR, k, v)

bars = json.load(open(config.data(a.file), encoding='utf-8')); tick = config.tick_of(a.file)
N1, N2 = [int(x) for x in a.at.split(',')]
utc = lambda i: DT.datetime.fromtimestamp(bars[i]['t'] / 1000, DT.timezone.utc)
def run(n):
    r = analyze(bars[:n], tick=tick)
    std = [(s['i0'], s['i1'], s['p0'], s['p1']) for s in TR._done(r)]
    live = [(s['i0'], s['i1'], s['p0'], s['p1']) for s in r['segs'] if s.get('live')]
    return dict(n=n, pens=[(p['i0'], p['i1'], p['p0'], p['p1']) for p in r['pens']], std=std, live=live)
A, B = run(N1), run(N2)
moved = [s for s in A['std'] if s not in B['std']]
for s in moved:
    nw = next((t for t in B['std'] if t[0] == s[0]), None)
    print('挪了', f'{utc(s[0]):%m-%d %H:%M} {s[2]:g} → {utc(s[1]):%m-%d %H:%M} {s[3]:g}', '⇒', nw and f'终点 {utc(nw[1]):%m-%d %H:%M} {nw[3]:g}')

b0, b1 = a.from_bar, N2 - 1
font = lambda s: ImageFont.truetype(config._pick_font(), s)
F, Fs, Fb = font(20), font(15), font(17)
W, PH, ML, MR = 2000, 540, 80, 150
NOTE_H = 96 if a.note else 64
im = Image.new('RGB', (W, 70 + 2 * (PH + 26) + NOTE_H), BG); d = ImageDraw.Draw(im)
win = bars[b0:b1 + 1]; lo = min(x['l'] for x in win) * 0.985; hi = max(x['h'] for x in win) * 1.015
LL, LH = math.log(lo), math.log(hi)
d.text((ML, 14), a.title, fill=TX, font=F)
d.text((ML, 42), f'{a.file} · 图上只画标准化线段（＝分界用的那一套）· 上格截到第 {N1} 根（{utc(N1 - 1):%m-%d %H:%M}），下格截到第 {N2} 根（{utc(N2 - 1):%m-%d %H:%M}）', fill=MU, font=Fs)
GOLD, AMB = (196, 137, 1), (255, 190, 60)

def dashed(q, x0, y0, x1, y1, col, width, on=12, off=8):
    L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(L // (on + off)))
    for k in range(n + 1):
        t0, t1 = k * (on + off) / L, min(1, (k * (on + off) + on) / L)
        if t0 >= 1: break
        q.line([x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0, x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1], fill=col, width=width)

def panel(k, R, tag):
    y0 = 70 + k * (PH + 26); top, bot = 30, PH - 26
    p = Image.new('RGB', (W, PH), BG); q = ImageDraw.Draw(p, 'RGBA')
    X = lambda i: ML + (i - b0) * (W - ML - MR) / max(1, b1 - b0)
    Y = lambda v: top + (LH - math.log(v)) / (LH - LL) * (bot - top)
    clip = lambda s: (X(max(s[0], b0)), Y(s[2] if s[0] >= b0 else s[2] + (s[3] - s[2]) * (b0 - s[0]) / (s[1] - s[0])), X(s[1]), Y(s[3]))
    for i in range(b0, R['n']):
        b = bars[i]; q.line([X(i), Y(b['h']), X(i), Y(b['l'])], fill=(120, 126, 140, 150))
    for s in R['pens']:
        if s[1] < b0: continue
        q.line(clip(s), fill=(122, 137, 166, 170), width=1)
    std = [s for s in R['std'] if s[1] >= b0]
    for s in std[:-1]:
        q.line(clip(s), fill=GOLD, width=3)
        q.ellipse([X(s[1]) - 4, Y(s[3]) - 4, X(s[1]) + 4, Y(s[3]) + 4], fill=GOLD)
    if std:                                                     # 提案：最后一条已完成的标准化线段画虚线
        s = std[-1]; x0, y0_, x1, y1 = clip(s)
        dashed(q, x0, y0_, x1, y1, GOLD, 3)
        q.ellipse([x1 - 6, y1 - 6, x1 + 6, y1 + 6], outline=GOLD, width=2, fill=BG)
        txt = f'虚线：这一条的终点还可能往后挪（{utc(s[1]):%m-%d %H:%M} {s[3]:g}）'
        lx, ly = x1 + 12, min(bot - 24, max(top + 2, y1 + (10 if s[3] < s[2] else -30)))
        bb = q.textbbox((lx, ly), txt, font=Fb); q.rectangle(bb, fill=BG + (230,)); q.text((lx, ly), txt, fill=GOLD, font=Fb)
    for s in R['live']:                                         # 还在走的那一段：细点线（网站现在就这么画，不是提案）
        if s[1] < b0: continue
        dashed(q, *clip(s), (196, 137, 1, 120), 1, on=3, off=5)
    if k == 1:                                                  # 下格：上一格那条虚线的终点挪到哪了
        for s in moved:
            nw = next((t for t in B['std'] if t[0] == s[0]), None)
            if not nw: continue
            xa, ya, xb, yb = X(s[1]), Y(s[3]), X(nw[1]), Y(nw[3])
            q.ellipse([xa - 9, ya - 9, xa + 9, ya + 9], outline=AMB, width=2)
            q.line([xa, ya, xb, yb], fill=AMB, width=2)
            q.polygon([(xb, yb), (xb - 9 if xb > xa else xb + 9, yb - 5), (xb - 9 if xb > xa else xb + 9, yb + 5)], fill=AMB)
            txt = f'终点挪了：{utc(s[1]):%m-%d %H:%M} {s[3]:g} → {utc(nw[1]):%m-%d %H:%M} {nw[3]:g}（起点不动），挪完变实线'
            lx, ly = xa - 20, min(bot - 24, ya + 26)
            bb = q.textbbox((lx, ly), txt, font=Fb); q.rectangle(bb, fill=BG + (230,)); q.text((lx, ly), txt, fill=AMB, font=Fb)
    xn = X(R['n'] - 1)
    q.line([xn, top, xn, bot], fill=AMB + (120,), width=1)
    q.text((xn + 6 if W - MR - xn > 120 or xn > W - MR - 2 else xn - 106, top + 4), f'此刻\n{utc(R["n"] - 1):%m-%d %H:%M}', fill=AMB, font=Fs)   # 此刻线离右框太近时字写在线左边，别横跨框线
    q.rectangle([0, 0, ML - 1, PH], fill=BG); q.rectangle([0, 0, W, top - 1], fill=BG); q.rectangle([0, bot + 1, W, PH], fill=BG)
    q.rectangle([ML, top, W - MR, bot], outline=(60, 66, 80))
    q.text((ML + 6, 4), tag, fill=TX, font=F)
    short = (bars[b1]['t'] - bars[b0]['t']) / 10 < 86400e3 * 1.5   # 刻度间隔不到一天半就带上时分（跟 r1_fig 同一条），免得一排两个同样的日期
    for i in range(b0, b1 + 1, max(1, (b1 - b0) // 10)): q.text((min(W - MR - (80 if short else 48), X(i) - (40 if short else 24)), bot + 4), f'{utc(i):%m-%d %H:%M}' if short else f'{utc(i):%m-%d}', fill=MU, font=Fs)
    for v in sorted({float(f'{lo * (hi / lo) ** (j / 6):.3g}') for j in range(1, 6)}):
        q.text((6, Y(v) - 8), f'{v:g}', fill=MU, font=Fs); q.line([ML - 5, Y(v), ML, Y(v)], fill=MU)
    im.paste(p, (0, y0))

panel(0, A, f'上：截到第 {N1} 根 —— 最后一条线段画虚线：它还没定死')
panel(1, B, f'下：截到第 {N2} 根 —— 后面一段走完，虚线那条的终点往后挪了')
yb = 70 + 2 * (PH + 26) + 4
d.text((ML, yb), '画法：笔灰细线；标准化线段金色，实线＝定了，虚线＝终点还可能往后挪（提案）；细点线＝还在走的那一段（网站现在就这么画）；琥珀圈→箭头＝终点挪到哪；琥珀竖线＝此刻。对数轴，两格同一把尺。', fill=MU, font=Fs)
if a.note: d.text((ML, yb + 30), '注：' + a.note, fill=TX, font=Fs)
im.save(out); print('saved', out, im.size)
