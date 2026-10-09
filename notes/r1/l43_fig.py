# J18（L43）前后图：同一个窗口上下两格，上＝落地支，下＝改了 S5 的那支。数全从 l43_dump.py 打的 json 来，图上不读数。
#   python l43_fig.py --root <引擎仓(取K线)> --file zec15.json --a before.json --b after.json --ta '上：…' --tb '下：…' --from 08-24 --to 09-21 --out x.png
import sys, os, json, argparse, math, datetime as DT
ap = argparse.ArgumentParser()
ap.add_argument('--root', required=True); ap.add_argument('--file', required=True)
ap.add_argument('--a', required=True); ap.add_argument('--b'); ap.add_argument('--ta', required=True); ap.add_argument('--tb', default='')
ap.add_argument('--from', dest='frm', required=True); ap.add_argument('--to', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--title', default=''); ap.add_argument('--note', default='')
a = ap.parse_args(); out = os.path.abspath(a.out)
A = json.load(open(a.a)); B = json.load(open(a.b)) if a.b else None
sys.path[:0] = [a.root]; os.chdir(a.root)
import config
from render.style import BG, TX, MU
from PIL import Image, ImageDraw, ImageFont
bars = json.load(open(config.data(a.file), encoding='utf-8'))
utc = lambda i: DT.datetime.fromtimestamp(bars[i]['t'] / 1000, DT.timezone.utc)
Y0 = utc(0).year
pick = lambda s: next(i for i in range(len(bars)) if utc(i) >= DT.datetime.strptime(f'{Y0}-{s}', '%Y-%m-%d').replace(tzinfo=DT.timezone.utc))
b0, b1 = pick(a.frm), pick(a.to)
font = lambda s: ImageFont.truetype(config._pick_font(), s)
F, Fs, Fb = font(22), font(15), font(17)
W, PH, ML, MR = 2000, 560, 80, 60
panels = [p for p in (A, B) if p]
NOTE_H = 100
im = Image.new('RGB', (W, 74 + len(panels) * (PH + 26) + NOTE_H), BG); d = ImageDraw.Draw(im)
win = bars[b0:b1 + 1]; lo = min(x['l'] for x in win) * 0.96; hi = max(x['h'] for x in win) * 1.02
LL, LH = math.log(lo), math.log(hi)
d.text((ML, 12), a.title, fill=TX, font=F)
d.text((ML, 44), f'同一个窗口、同一把尺（对数轴）· {utc(b0):%m-%d} → {utc(b1):%m-%d} · 线段画标准化那一套', fill=MU, font=Fs)
GOLD, RED, GRN, GRY, WARN, AMB = (196, 137, 1), (230, 92, 92), (70, 175, 120), (150, 156, 170), (255, 80, 80), (255, 190, 60)
RULE = {'S5': '盘整相连'}                                  # 刀名跟决策页一个叫法（Nova 18:58：小栋不认识 S5；D2 各条一律叫「转折分界」，Nova 18:59）
TC = {'上涨': RED, '下跌': GRN, '盘整': GRY, '无中枢': GRY}

def dashed(q, x0, y0, x1, y1, col, width, on=8, off=6):
    L = max(1e-6, math.hypot(x1 - x0, y1 - y0)); k = 0
    while k * (on + off) < L:
        t0, t1 = k * (on + off) / L, min(1, (k * (on + off) + on) / L)
        q.line([x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0, x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1], fill=col, width=width); k += 1

def panel(k, D, tag):
    y0 = 74 + k * (PH + 26); top, bot = 64, PH - 26
    p = Image.new('RGB', (W, PH), BG); q = ImageDraw.Draw(p, 'RGBA')
    X = lambda i: ML + (i - b0) * (W - ML - MR) / max(1, b1 - b0)
    Y = lambda v: top + (LH - math.log(v)) / (LH - LL) * (bot - top)
    segs = D['segs']
    for z in D['centers']:                                   # 中枢框，颜色跟它所在那段走势的类型
        if z['i1'] < b0 or z['i0'] > b1: continue
        c = TC[segs[z['seg']]['type']]
        q.rectangle([X(max(z['i0'], b0)), Y(z['ZG']), X(min(z['i1'], b1)), Y(z['ZD'])], fill=c + (40,), outline=c + (170,), width=2)
    late = []                                              # 代价那两种框的字，最后画，免得被 K 线和线段压住
    cz = [[z for z in D['centers'] if z['seg'] == j] for j in range(len(segs))]
    for j, kk in D.get('l20', []):                           # P 的代价：同一段趋势里叠着的那对中枢，红粗框＋字
        z1, z2 = cz[j][kk - 1], cz[j][kk]
        if z2['i1'] < b0 or z1['i0'] > b1: continue
        xa, xb = X(max(z1['i0'], b0)), X(min(z2['i1'], b1)); ya, yb = Y(max(z1['ZG'], z2['ZG'])), Y(min(z1['ZD'], z2['ZD']))
        q.rectangle([xa - 4, ya - 4, xb + 4, yb + 4], outline=WARN + (230,), width=3)
        t = f'同一段{segs[j]["type"]}里两个中枢叠着 —— 第 20 课原文不允许'
        late.append(((xa, ya - 30), t, WARN))
    for j in D.get('s4', []):                                 # Z 的代价：S4′（单中枢那截后面的 S5 接缝不叠），琥珀 —— 犯的是我们对 L38 的窄读，不是原文明令（Atlas 18:54）
        z1, z2 = cz[j - 1][-1], cz[j][0]
        if z2['i1'] < b0 or z1['i0'] > b1: continue
        xa, xb = X(max(z1['i0'], b0)), X(min(z2['i1'], b1)); ya, yb = Y(max(z1['ZG'], z2['ZG'])), Y(min(z1['ZD'], z2['ZD']))
        q.rectangle([xa - 4, ya - 4, xb + 4, yb + 4], outline=AMB + (230,), width=3)
        t = f'{segs[j - 1]["type"]}接{segs[j]["type"]}、中枢不叠 —— 违背我们自己的一条规矩（第 38 课读窄了），原文没禁'
        late.append(((xa, ya - 30), t, AMB))
    for i in range(b0, b1 + 1):
        b = bars[i]; q.line([X(i), Y(b['h']), X(i), Y(b['l'])], fill=(120, 126, 140, 140))
    for s in D['std']:
        if s['i1'] < b0 or s['i0'] > b1: continue
        q.line([X(s['i0']), Y(s['p0']), X(s['i1']), Y(s['p1'])], fill=GOLD + (200,), width=2)
    for j, s in enumerate(segs):                              # 顶上一条带：每段走势一种颜色＋类型字
        if s['i1'] < b0 or s['i0'] > b1: continue
        xa, xb = X(max(s['i0'], b0)), X(min(s['i1'], b1)); c = TC[s['type']]
        q.rectangle([xa + 1, 34, xb - 1, 56], fill=c + (70,), outline=c + (200,))
        t = f"{s['type']}（{s['n']} 个中枢）" if xb - xa > 150 else s['type']
        if xb - xa > 40: q.text((xa + 6, 36), t, fill=TX, font=Fs)
    placed = []
    for bd in D['bounds']:                                    # 分界：竖虚线＋规则、价、时间
        i = bd['bar']
        if i < b0 or i > b1: continue
        j = next((j for j, s in enumerate(segs) if s['i0'] == i), None)
        bad = j in D['bad']
        col = WARN if bad else MU
        dashed(q, X(i), 34, X(i), bot, col + (220,), 3 if bad else 1)
        ty = min(bot - 56, max(64, Y(bd['price']) + (14 if bd['kind'] == 'L' else -40)))
        st = '待确认' if bd['state'] == 'pending' else '已确认' if bd['state'] == 'confirmed' else ''
        t = f"{('转折分界' if bd['rule'].startswith('D2') else RULE.get(bd['rule'], bd['rule']))} {bd['price']:g} · {utc(i):%m-%d %H:%M} {st}"
        if bad: t += f"\n{segs[j - 1]['type']}接{segs[j]['type']} —— 第 43 课原文不允许"
        tw = q.multiline_textbbox((0, 0), t, font=Fb)[2]
        tx = X(i) + 8 if X(i) + 8 + tw < W - MR else X(i) - 8 - tw     # 靠右边出框 ⇒ 字放到线左边
        bb = q.multiline_textbbox((tx, ty), t, font=Fb)
        while any(bb[0] < o[2] and o[0] < bb[2] and bb[1] < o[3] and o[1] < bb[3] for o in placed):   # 跟已放的字撞了 ⇒ 往上挪一行
            ty -= bb[3] - bb[1] + 6; bb = q.multiline_textbbox((tx, ty), t, font=Fb)
        placed.append(bb); q.rectangle(bb, fill=BG + (230,))
        q.multiline_text((tx, ty), t, fill=WARN if bad else TX, font=Fb)
    for xy, t, c in late:
        bb = q.textbbox(xy, t, font=Fb); q.rectangle(bb, fill=BG + (240,)); q.text(xy, t, fill=c, font=Fb)
    q.rectangle([0, 0, ML - 1, PH], fill=BG); q.rectangle([W - MR + 1, 0, W, PH], fill=BG); q.rectangle([0, bot + 1, W, PH], fill=BG)
    q.rectangle([ML, 34, W - MR, bot], outline=(60, 66, 80))
    q.text((ML + 2, 4), tag, fill=TX, font=F)
    days = [i for i in range(b0, b1 + 1) if i == b0 or utc(i).date() != utc(i - 1).date()]
    step = max(1, math.ceil(len(days) / 14))
    for i in days[::step]: q.text((min(W - MR - 48, X(i) - 24), bot + 4), f'{utc(i):%m-%d}', fill=MU, font=Fs)
    for v in sorted({float(f'{lo * (hi / lo) ** (j / 6):.3g}') for j in range(1, 6)}):
        q.text((6, Y(v) - 8), f'{v:g}', fill=MU, font=Fs); q.line([ML - 5, Y(v), ML, Y(v)], fill=MU)
    im.paste(p, (0, y0))

panel(0, A, a.ta)
if B: panel(1, B, a.tb)
yb = 74 + len(panels) * (PH + 26) + 4
d.text((ML, yb), '画法：顶上色带＝走势段（红＝上涨，绿＝下跌，灰＝盘整），框＝同级别中枢，颜色跟所在那段；金线＝标准化线段；竖虚线＝分界（红粗＝两边同向趋势相连）；红框＝同一段趋势里叠着的中枢；琥珀框＝违背我们自己规矩的地方（只有一个中枢的盘整，跟后面的中枢不叠）。', fill=MU, font=Fs)
if a.note: d.multiline_text((ML, yb + 28), a.note, fill=TX, font=Fs)
im.save(out); print('saved', out, im.size)
