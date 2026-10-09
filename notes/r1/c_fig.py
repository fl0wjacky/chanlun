# 合并页那道题的图（Nova 10-09 15:08）：同一个窗口、同一根 K 线时刻，上下两格只差「最后几条线段算没定」——
#   上 A：最后一条标准化线段画虚线，其余实线（＝已确认）；前一刻已确认、这一刻没了的那条 ⇒ 淡红虚线＋叉「线段已撤回」。
#   下 C：最后两条画虚线；同一处那条前一刻还是虚线（没确认过），变长了也不算撤回 ⇒ 没有叉。
#   线段一律画标准化那套（trend._done，D-3 C 以后网站画的就是它）。数全从引擎打出来，图上不读数。
#   python c_fig.py --root <引擎仓> --file zec30_cut.json --at 1882,1895 --from-bar 1600 --out x.png
import sys, os, json, argparse, math, datetime as DT
ap = argparse.ArgumentParser()
ap.add_argument('--root', required=True); ap.add_argument('--file', required=True)
ap.add_argument('--at', required=True); ap.add_argument('--from-bar', type=int, required=True); ap.add_argument('--out', required=True)
ap.add_argument('--title', default='最后一条算没定（A）还是最后两条算没定（C）'); ap.add_argument('--note', default='')
ap.add_argument('--plain', action='store_true', help='给小栋看的版本：表头不放文件名、K 线根数（引擎号由 --note 自己决定写不写）')
a = ap.parse_args()
out = os.path.abspath(a.out)
sys.path[:0] = [a.root]; os.chdir(a.root)
import config
from core.analyze import analyze
import core.trend as TR
from render.style import BG, TX, MU
from PIL import Image, ImageDraw, ImageFont

bars = json.load(open(config.data(a.file), encoding='utf-8')); tick = config.tick_of(a.file)
N0, N1 = [int(x) for x in a.at.split(',')]
utc = lambda i: DT.datetime.fromtimestamp(bars[i]['t'] / 1000, DT.timezone.utc)
def run(n):
    r = analyze(bars[:n], tick=tick)
    return dict(n=n, pens=[(p['i0'], p['i1'], p['p0'], p['p1']) for p in r['pens']],
                std=[(s['i0'], s['i1'], s['p0'], s['p1'], s['dir']) for s in TR._done(r)])
P0, P1 = run(N0), run(N1)
keys1 = {(s[0], s[1], s[4]) for s in P1['std']}
gone = {k: [s for s in P0['std'][:-k] if (s[0], s[1], s[4]) not in keys1] for k in (1, 2)}   # 前一刻「已确认」里、这一刻不在了的
for k, g in gone.items():
    print(('A' if k == 1 else 'C'), '撤回', [f'{utc(s[0]):%m-%d %H:%M} {s[2]:g} → {utc(s[1]):%m-%d %H:%M} {s[3]:g}' for s in g])

b0, b1 = a.from_bar, N1 - 1
font = lambda s: ImageFont.truetype(config._pick_font(), s)
F, Fs, Fb = font(20), font(15), font(17)
W, PH, ML, MR = 2000, 540, 80, 150
NOTE_H = 96 if a.note else 64
im = Image.new('RGB', (W, 70 + 2 * (PH + 26) + NOTE_H), BG); d = ImageDraw.Draw(im)
win = bars[b0:b1 + 1]; lo = min(x['l'] for x in win) * 0.97; hi = max(x['h'] for x in win) * 1.015
LL, LH = math.log(lo), math.log(hi)
d.text((ML, 14), a.title, fill=TX, font=F)
d.text((ML, 42), (f'线段画标准化那一套 · 两格都是 {utc(N1 - 1):%m-%d %H:%M} 这一刻；前一刻是 {utc(N0 - 1):%m-%d %H:%M}' if a.plain else
                 f'{a.file} · 线段画标准化那一套 · 两格都是第 {N1} 根（{utc(N1 - 1):%m-%d %H:%M}）这一刻；前一刻是第 {N0} 根（{utc(N0 - 1):%m-%d %H:%M}）'), fill=MU, font=Fs)
GOLD, RED, AMB = (196, 137, 1), (255, 96, 96), (255, 190, 60)

def dashed(q, x0, y0, x1, y1, col, width, on=12, off=8):
    L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(L // (on + off)))
    for k in range(n + 1):
        t0, t1 = k * (on + off) / L, min(1, (k * (on + off) + on) / L)
        if t0 >= 1: break
        q.line([x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0, x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1], fill=col, width=width)

def panel(k, nopen, tag):
    y0 = 70 + k * (PH + 26); top, bot = 30, PH - 26
    p = Image.new('RGB', (W, PH), BG); q = ImageDraw.Draw(p, 'RGBA')
    X = lambda i: ML + (i - b0) * (W - ML - MR) / max(1, b1 - b0)
    Y = lambda v: top + (LH - math.log(v)) / (LH - LL) * (bot - top)
    for i in range(b0, N1):
        b = bars[i]; q.line([X(i), Y(b['h']), X(i), Y(b['l'])], fill=(120, 126, 140, 150))
    for s in P1['pens']:
        if s[1] < b0: continue
        q.line([X(max(s[0], b0)), Y(s[2]) if s[0] >= b0 else Y(s[2] + (s[3] - s[2]) * (b0 - s[0]) / (s[1] - s[0])), X(s[1]), Y(s[3])], fill=(122, 137, 166, 160), width=1)
    std = [s for s in P1['std'] if s[1] >= b0]
    for j, s in enumerate(std):
        p0 = s[2] if s[0] >= b0 else s[2] + (s[3] - s[2]) * (b0 - s[0]) / (s[1] - s[0])   # 起点在窗口左边外 ⇒ 在左沿上按比例插值，别拿原起点的价硬画（斜率会错）
        x0, y0_, x1, y1 = X(max(s[0], b0)), Y(p0), X(s[1]), Y(s[3])
        if j >= len(std) - nopen: dashed(q, x0, y0_, x1, y1, GOLD, 3)
        else: q.line([x0, y0_, x1, y1], fill=GOLD, width=3)
    L = std[-1]
    lab = '终点还可能挪'
    q.text((X(L[1]) - 40, Y(L[3]) + (14 if L[4] == 'down' else -34)), lab, fill=GOLD, font=Fs)
    for s in gone[nopen]:                                       # 撤回：原位置淡红虚线＋终点一个叉＋字（跟网站 ③b 同一画法）
        x0, y0_, x1, y1 = X(s[0]), Y(s[2]), X(s[1]), Y(s[3])
        dashed(q, x0, y0_, x1, y1, RED + (120,), 2, on=4, off=4)
        q.line([x1 - 10, y1 - 10, x1 + 10, y1 + 10], fill=RED + (170,), width=3); q.line([x1 - 10, y1 + 10, x1 + 10, y1 - 10], fill=RED + (170,), width=3)
        t = f'线段已撤回：笔回头改了（{s[3]:g}，{utc(s[1]):%m-%d %H:%M}）'
        bb = q.textbbox((x1 + 14, y1 + 12), t, font=Fb); q.rectangle(bb, fill=BG + (230,)); q.text((x1 + 14, y1 + 12), t, fill=RED, font=Fb)
    if not gone[nopen]:                                         # C 那格：同一处写一句「这里没有叉」，读图的人不用自己找
        for s in gone[1]:
            x1, y1 = X(s[1]), Y(s[3])
            q.ellipse([x1 - 12, y1 - 12, x1 + 12, y1 + 12], outline=AMB, width=2)
            t = f'同一处：那时它还是虚线（没定），变长了不算撤回'
            bb = q.textbbox((x1 + 16, y1 + 12), t, font=Fb); q.rectangle(bb, fill=BG + (230,)); q.text((x1 + 16, y1 + 12), t, fill=AMB, font=Fb)
    q.rectangle([0, 0, ML - 1, PH], fill=BG); q.rectangle([0, 0, W, top - 1], fill=BG); q.rectangle([0, bot + 1, W, PH], fill=BG)
    q.rectangle([ML, top, W - MR, bot], outline=(60, 66, 80))
    q.text((ML + 6, 4), tag, fill=TX, font=F)
    # 刻度：每天的第一根 K 线标一次日期（原来按「窗口十等分」打，十分之一不到一天时同一个日期会出现两次 —— Nova 15:13 看出来的）
    days = [i for i in range(b0, b1 + 1) if i == b0 or utc(i).date() != utc(i - 1).date()]
    step = max(1, math.ceil(len(days) / 12))
    for i in days[::step]: q.text((min(W - MR - 48, X(i) - 24), bot + 4), f'{utc(i):%m-%d}', fill=MU, font=Fs)
    for v in sorted({float(f'{lo * (hi / lo) ** (j / 6):.3g}') for j in range(1, 6)}):
        q.text((6, Y(v) - 8), f'{v:g}', fill=MU, font=Fs); q.line([ML - 5, Y(v), ML, Y(v)], fill=MU)
    im.paste(p, (0, y0))

panel(0, 1, '上：A —— 只有最后一条算没定（虚线）')
panel(1, 2, '下：C —— 最后两条都算没定（虚线）')
yb = 70 + 2 * (PH + 26) + 4
d.text((ML, yb), '画法：笔灰细线；标准化线段金色，实线＝已确认，虚线＝还可能挪；淡红虚线＋叉＝已确认的线段被撤了；琥珀圈＝C 那一格里同一个位置。对数轴，两格同一把尺。', fill=MU, font=Fs)
if a.note: d.text((ML, yb + 30), '注：' + a.note, fill=TX, font=Fs)
im.save(out); print('saved', out, im.size)
