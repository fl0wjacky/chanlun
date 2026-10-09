# R6 B 对 A 的前后图（Atlas 10-09 20:46，card-8fea72e0-772）：同一个窗口上下两格，上＝B（现行），下＝A（_R6_B=False）。
#   数全从 l43_dump.py 打的 json 来（--set '_R6_B=False' 出 A），图上不读数。
#   分界：D2（「分界」）实心点＋价和时间；S5（「盘整相连」）空心圈、不写字（一年 1h 的窗口里有二十来把，写字就糊了）。
#   python r6_fig.py --root <引擎仓> --file btc_1h_iris.json --a B.json --b A.json --from 2024-02-01 --to 2025-02-01 \
#       --box-b 60800,71888,2024-02-23,2024-03-27,'A 的参照中枢' --mark-b 2024-08-05,48888,'…' --out x.png
import sys, os, json, argparse, math, datetime as DT
ap = argparse.ArgumentParser()
ap.add_argument('--root', required=True); ap.add_argument('--file', required=True)
ap.add_argument('--a', required=True); ap.add_argument('--b', required=True)
ap.add_argument('--ta', required=True); ap.add_argument('--tb', required=True)
ap.add_argument('--from', dest='frm', required=True); ap.add_argument('--to', required=True)
ap.add_argument('--box-b', default=''); ap.add_argument('--legend2', default=''); ap.add_argument('--mark-b', default='')
ap.add_argument('--title', default=''); ap.add_argument('--note', default=''); ap.add_argument('--out', required=True)
a = ap.parse_args(); out = os.path.abspath(a.out)
A = json.load(open(a.a)); B = json.load(open(a.b))
sys.path[:0] = [a.root]; os.chdir(a.root)
import config
from render.style import BG, TX, MU
from PIL import Image, ImageDraw, ImageFont
bars = json.load(open(config.data(a.file), encoding='utf-8'))
utc = lambda i: DT.datetime.fromtimestamp(bars[i]['t'] / 1000, DT.timezone.utc)
day = lambda s: DT.datetime.strptime(s, '%Y-%m-%d').replace(tzinfo=DT.timezone.utc)
pick = lambda s: next(i for i in range(len(bars)) if utc(i) >= day(s))
b0, b1 = pick(a.frm), pick(a.to)
font = lambda s: ImageFont.truetype(config._pick_font(), s)
F, Fs, Fb = font(22), font(15), font(17)
W, PH, ML, MR = 2000, 600, 80, 40
NOTE_H = 110
im = Image.new('RGB', (W, 74 + 2 * (PH + 26) + NOTE_H), BG); d = ImageDraw.Draw(im)
win = bars[b0:b1 + 1]; lo = min(x['l'] for x in win) * 0.95; hi = max(x['h'] for x in win) * 1.03
LL, LH = math.log(lo), math.log(hi)
d.text((ML, 12), a.title, fill=TX, font=F)
d.text((ML, 44), f'同一个窗口、同一把尺（对数轴）· {utc(b0):%Y-%m-%d} → {utc(b1):%Y-%m-%d} · 1 小时 K 线', fill=MU, font=Fs)
GOLD, RED, GRN, GRY, AMB, WARN = (196, 137, 1), (230, 92, 92), (70, 175, 120), (150, 156, 170), (255, 190, 60), (255, 80, 80)
TC = {'上涨': RED, '下跌': GRN, '盘整': GRY, '无中枢': GRY}

def panel(k, D, tag, box=None, mark=None):
    y0 = 74 + k * (PH + 26); top, bot = 64, PH - 26
    p = Image.new('RGB', (W, PH), BG); q = ImageDraw.Draw(p, 'RGBA')
    X = lambda i: ML + (i - b0) * (W - ML - MR) / max(1, b1 - b0)
    Y = lambda v: top + (LH - math.log(v)) / (LH - LL) * (bot - top)
    segs = D['segs']
    for z in D['centers']:
        if z['i1'] < b0 or z['i0'] > b1: continue
        c = TC[segs[z['seg']]['type']]
        q.rectangle([X(max(z['i0'], b0)), Y(z['ZG']), X(min(z['i1'], b1)), Y(z['ZD'])], fill=c + (34,), outline=c + (150,), width=1)
    for i in range(b0, b1 + 1):
        b = bars[i]; q.line([X(i), Y(b['h']), X(i), Y(b['l'])], fill=(120, 126, 140, 120))
    for s in D['std']:
        if s['i1'] < b0 or s['i0'] > b1: continue
        q.line([X(max(s['i0'], b0)), Y(s['p0']) if s['i0'] >= b0 else Y(s['p0'] + (s['p1'] - s['p0']) * (b0 - s['i0']) / (s['i1'] - s['i0'])),
                X(min(s['i1'], b1)), Y(s['p1']) if s['i1'] <= b1 else Y(s['p0'] + (s['p1'] - s['p0']) * (b1 - s['i0']) / (s['i1'] - s['i0']))],
               fill=GOLD + (200,), width=2)
    for j, s in enumerate(segs):                               # 顶上色带：走势段类型
        if s['i1'] < b0 or s['i0'] > b1: continue
        xa, xb = X(max(s['i0'], b0)), X(min(s['i1'], b1)); c = TC[s['type']]
        q.rectangle([xa + 1, 34, xb - 1, 56], fill=c + (70,), outline=c + (200,))
        if xb - xa > 46: q.text((xa + 4, 36), s['type'], fill=TX, font=Fs)
    late = []
    if box:                                                    # 指定的中枢框（A 的参照中枢）
        zd, zg, f0, f1, lab = box
        xa, xb = X(max(pick(f0), b0)), X(min(pick(f1), b1))
        q.rectangle([xa, Y(zg), xb, Y(zd)], outline=AMB + (240,), width=3)
        q.line([xa, Y(zd), X(b1), Y(zd)], fill=AMB + (150,), width=1)          # ZD 往右延一条细线：离开段要收在它下面才算确认
        late.append(((xa, Y(zg) - 26), f'{lab} [{zd:g}, {zg:g}]，框底 {zd:g} 往右延长', AMB))
    for bd in D['bounds']:
        i = bd['bar']
        if i < b0 or i > b1: continue
        j = next((j for j, s in enumerate(segs) if s['i0'] == i), None)
        x, y = X(i), Y(bd['price'])
        if bd['rule'] == 'S5':
            r = 6; q.ellipse([x - r, y - r, x + r, y + r], outline=(j in D['bad']) and WARN or TX, width=2)
        else:
            r = 8; q.ellipse([x - r, y - r, x + r, y + r], fill=TX, outline=BG, width=2)
            q.line([x, 34, x, bot], fill=TX + (90,), width=1)
            ty = y + 12 if bd['kind'] == 'L' else y - 34
            late.append(((x + 10, min(bot - 24, max(60, ty))), f"分界 {bd['price']:g} · {utc(i):%Y-%m-%d}", TX))
    if mark:                                                   # 指定的一根（48888 那根急跌底）
        md, mp, lab = mark
        i = min(range(pick(md), pick(md) + 24), key=lambda i: abs(bars[i]['l'] - mp))
        x, y = X(i), Y(bars[i]['l'])
        q.line([x, y + 8, x, y + 40], fill=AMB, width=2); q.polygon([(x - 6, y + 14), (x + 6, y + 14), (x, y + 6)], fill=AMB)
        late.append(((x + 10, y + 22), lab, AMB))
    placed = []
    for (xx, yy), t, c in late:
        bb = q.textbbox((xx, yy), t, font=Fb)
        if bb[2] > W - MR: xx -= bb[2] - (W - MR) + 4; bb = q.textbbox((xx, yy), t, font=Fb)
        while any(bb[0] < o[2] and o[0] < bb[2] and bb[1] < o[3] and o[1] < bb[3] for o in placed):
            yy += bb[3] - bb[1] + 6; bb = q.textbbox((xx, yy), t, font=Fb)
        placed.append(bb); q.rectangle(bb, fill=BG + (235,)); q.text((xx, yy), t, fill=c, font=Fb)
    q.rectangle([0, 0, ML - 1, PH], fill=BG); q.rectangle([W - MR + 1, 0, W, PH], fill=BG); q.rectangle([0, bot + 1, W, PH], fill=BG)
    q.rectangle([ML, 34, W - MR, bot], outline=(60, 66, 80))
    q.text((ML + 2, 4), tag, fill=TX, font=F)
    nseg = sum(1 for s in segs if b0 <= s['i0'] <= b1); nd2 = sum(1 for bd in D['bounds'] if b0 <= bd['bar'] <= b1 and bd['rule'] != 'S5')
    nall = sum(1 for bd in D['bounds'] if b0 <= bd['bar'] <= b1)
    t = f'实心点 {nd2} 个、全部分界 {nall} 把、走势 {nseg} 段'; tw = q.textbbox((0, 0), t, font=F)[2]   # 「分界」跟合并页一个数法＝全部的刀（Nova 20:55）
    q.text((W - MR - tw, 4), t, fill=TX, font=F)
    months = [i for i in range(b0, b1 + 1) if i == b0 or utc(i).month != utc(i - 1).month]
    for i in months: q.text((min(W - MR - 60, X(i) - 4), bot + 4), f'{utc(i):%Y-%m}', fill=MU, font=Fs)
    for v in sorted({float(f'{lo * (hi / lo) ** (j / 6):.3g}') for j in range(1, 6)}):
        q.text((6, Y(v) - 8), f'{v:g}', fill=MU, font=Fs); q.line([ML - 5, Y(v), ML, Y(v)], fill=MU)
    im.paste(p, (0, y0))

def parse_box(s):
    if not s: return None
    zd, zg, f0, f1, lab = s.split(',', 4); return float(zd), float(zg), f0, f1, lab
def parse_mark(s):
    if not s: return None
    dd, pp, lab = s.split(',', 2); return dd, float(pp), lab

panel(0, A, a.ta)
panel(1, B, a.tb, box=parse_box(a.box_b), mark=parse_mark(a.mark_b))
yb = 74 + 2 * (PH + 26) + 4
d.text((ML, yb), '画法：顶上色带＝走势段（红＝上涨，绿＝下跌，灰＝盘整）；框＝同级别中枢；金线＝线段；实心点＝走势转折处的分界（写价和日期）；空心圈也是分界（盘整相连）。', fill=MU, font=Fs)
if a.legend2: d.text((ML, yb + 24), a.legend2, fill=MU, font=Fs)
if a.note: d.multiline_text((ML, yb + 52), a.note, fill=TX, font=Fs)
im.save(out); print('saved', out, im.size)
