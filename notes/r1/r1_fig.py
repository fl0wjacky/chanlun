# R-1 前后图（同级别／非同级别分解）—— 通用：同一棵树、同一份 K 线，跑两遍引擎，第二遍只翻一个开关。
#   python r1_fig.py --root <仓> --flag core.trend._D28=False --rank            # data/ 10 份逐张数「段、刀」变化
#   python r1_fig.py --root <仓> --flag <模块.常量=值> --file zec15.json --out x.png [--from 03-10 --to 04-06]
#   开关只在进程里翻（setattr），仓里的默认值一个字不动。上格＝现行（非同级别），下格＝翻了开关之后。
import sys, os, json, argparse, importlib, math, datetime as DT
ap = argparse.ArgumentParser()
ap.add_argument('--root', required=True); ap.add_argument('--flag', action='append', default=[])
ap.add_argument('--kw-b', action='append', default=[], help='下格给 trend_v3 的关键字参数，比如 alternate=False（D-0 交替开关不是模块常量）')
ap.add_argument('--base-label', default=None, help='表头里底座那一截的简称（开关全名太长会冲出右边）')
ap.add_argument('--mark', action='append', default=[], help='下格圈一个点："MM-DD HH:MM|价|说明"（S-13 非极值端点那张用来圈笔内真正的极值）')
ap.add_argument('--base', action='append', default=[], help='上下两格都翻的开关（比如上格要 S9 当底座）')
ap.add_argument('--file'); ap.add_argument('--out'); ap.add_argument('--rank', action='store_true')
ap.add_argument('--from', dest='frm'); ap.add_argument('--to')
ap.add_argument('--label-a', default='现行：非同级别分解'); ap.add_argument('--label-b', default='同级别分解（开关）')
ap.add_argument('--title', default='前后图'); ap.add_argument('--note', default='', help='图注再加一行（写在画法说明下面）'); ap.add_argument('--pen', default='old'); ap.add_argument('--pen-b', default=None, help='下格换一种笔（old/new），B-10 老笔新笔用')
a = ap.parse_args()
sys.path[:0] = [a.root]; os.chdir(a.root)
import config
from core.analyze import analyze_file
import core.trend as TR

def parse(f):
    k, v = f.split('=', 1); mod, attr = k.rsplit('.', 1)
    return importlib.import_module(mod), attr, {'True': True, 'False': False}.get(v, v if not v.replace('.', '').lstrip('-').isdigit() else float(v) if '.' in v else int(v))
FLAGS = [parse(f) for f in a.flag]
BASE = [parse(f) for f in a.base]
KWB = {k: {'True': True, 'False': False}.get(v, v) for k, v in (x.split('=', 1) for x in a.kw_b)}
if not FLAGS and not a.pen_b and not KWB: sys.exit('至少给一个 --flag 或 --pen-b')

def run(fn, flipped):
    saved = [(m, at, getattr(m, at)) for m, at, _ in BASE + FLAGS]
    try:
        for m, at, v in BASE: setattr(m, at, v)
        if flipped:
            for m, at, v in FLAGS: setattr(m, at, v)
        r = analyze_file(fn, pen=(a.pen_b or a.pen) if flipped else a.pen); t = TR.trend_v3(r, **(KWB if flipped else {}))
    finally:
        for m, at, v in saved: setattr(m, at, v)
    return dict(bars=r['bars'] if 'bars' in r else None, r=r,
                pens=[(p['i0'], p['i1'], p['p0'], p['p1']) for p in r['pens']],
                segs=[(s['i0'], s['i1'], s['p0'], s['p1']) for s in r['segs'] if not s.get('live')],
                live=[(s['i0'], s['i1'], s['p0'], s['p1']) for s in r['segs'] if s.get('live')],
                bounds=[(b['bar'], b['kind'], b['price'], b.get('death')) for b in t['bounds']],
                moved=[(m['from_bar'], m['to_bar'], m['kind']) for m in t.get('moved', [])],
                retr=sorted(__import__('collections').Counter((x['bar'], x['kind'], x['price']) for x in t.get('retracted', [])).items()),
                tsegs=[(s['i0'], s['i1'], s['type'], bool(s.get('head')), bool(s.get('upgraded'))) for s in t['segments']],
                zs=[(z.get('X0', z.get('x0')), z.get('X1', z.get('x1')), z['ZD'], z['ZG']) for z in t['seg_centers'] if 'ZD' in z])

def diff(A, B):
    sa, sb = set(A['segs']), set(B['segs']); ba, bb = {x[:2] for x in A['bounds']}, {x[:2] for x in B['bounds']}
    pa, pb = set(A['pens']), set(B['pens'])
    return dict(pen_only_a=len(pa - pb), pen_only_b=len(pb - pa), seg_only_a=len(sa - sb), seg_only_b=len(sb - sa), bnd_only_a=len(ba - bb), bnd_only_b=len(bb - ba),
                type_changed=sum(1 for x, y in zip(A['tsegs'], B['tsegs']) if x[2] != y[2]) + abs(len(A['tsegs']) - len(B['tsegs'])))

DATA = sorted(f for f in os.listdir('data') if f.endswith('.json'))
if a.rank:
    rows = []
    for fn in DATA:
        try: A, B = run(fn, False), run(fn, True)
        except Exception as e: print(f'{fn:20s} 跳过：{type(e).__name__} {e}'); continue
        d = diff(A, B); score = d['seg_only_a'] + d['seg_only_b'] + 5 * (d['bnd_only_a'] + d['bnd_only_b'])
        rows.append((score, fn, d))
    for score, fn, d in sorted(rows, reverse=True):
        print(f'{fn:20s} 分 {score:4d}　笔 −{d["pen_only_a"]}/+{d["pen_only_b"]}　段 −{d["seg_only_a"]}/+{d["seg_only_b"]}　刀 −{d["bnd_only_a"]}/+{d["bnd_only_b"]}　段型变 {d["type_changed"]}')
    sys.exit(0)

# ---- 出图 ----
from PIL import Image, ImageDraw, ImageFont
from render.style import CHART, BG, TX, MU
import json as _j
A, B = run(a.file, False), run(a.file, True)
bars = _j.load(open(config.data(a.file), encoding='utf-8'))
utc = lambda i: DT.datetime.fromtimestamp(bars[i]['t'] / 1000, DT.timezone.utc)
def ix(s):
    for i in range(len(bars)):
        if utc(i).strftime('%m-%d') >= s: return i
    return len(bars) - 1
if a.frm: b0, b1 = ix(a.frm), (ix(a.to) if a.to else len(bars) - 1)
else:  # 自动：包住所有变了的刀和段，两边各留 15%
    ch = [x[0] for x in set(A['bounds']) ^ set(B['bounds'])] + [i for s in set(A['segs']) ^ set(B['segs']) for i in s[:2]]
    if not ch: sys.exit('两边一刀一段都没变：这个开关在这张图上不起作用')
    lo_i, hi_i = min(ch), max(ch); pad = max(400, (hi_i - lo_i) * 0.25)   # 只变一刀时也要看得见前后各一段
    b0, b1 = max(0, int(lo_i - pad)), min(len(bars) - 1, int(hi_i + pad))
font = lambda s: ImageFont.truetype(config._pick_font(), s)
F, Fs = font(20), font(15)
W, PH, ML, MR = 2000, 560, 80, 20
im = Image.new('RGB', (W, 90 + 2 * (PH + 30) + (70 if a.note else 40)), BG); d = ImageDraw.Draw(im)
win = bars[b0:b1 + 1]; lo = min(x['l'] for x in win) * 0.985; hi = max(x['h'] for x in win) * 1.015
LL, LH = math.log(lo), math.log(hi)
nm = lambda fs: ' '.join(f.rsplit('.', 1)[-1] if '=True' in f else f.split('.')[-1] for f in fs)   # 只留常量名：上下两格的名字已经写在格子左上角，表头再写一遍会冲出右边
d.text((ML, 14), f'{a.file} · {a.title}' + (f' · 底座 {a.base_label or nm(a.base)}' if a.base else '') + f' · 下格加 {" ".join([nm(a.flag)] + [f"{k}={v}" for k, v in KWB.items()]).strip() or ("笔 " + a.pen + " → " + a.pen_b)}', fill=TX, font=F)
dd = diff(A, B)
d.text((ML, 48), f'窗口 {utc(b0):%Y-%m-%d} → {utc(b1):%Y-%m-%d}（UTC）｜整张：笔 上独有 {dd["pen_only_a"]} / 下独有 {dd["pen_only_b"]}，线段 上独有 {dd["seg_only_a"]} / 下独有 {dd["seg_only_b"]}，分界刀 上独有 {dd["bnd_only_a"]} / 下独有 {dd["bnd_only_b"]}，段型变 {dd["type_changed"]}｜加粗＝只在这一格有',
       fill=MU, font=Fs)
TYPE = {'上涨': (46, 158, 91), '下跌': (214, 69, 69)}
def panel(k, R, other, tag):
    y0 = 90 + k * (PH + 30); top, bot = 28, PH - 26
    p = Image.new('RGB', (W, PH), BG); q = ImageDraw.Draw(p, 'RGBA')
    X = lambda i: ML + (i - b0) * (W - ML - MR) / max(1, b1 - b0)
    Y = lambda v: top + (LH - math.log(v)) / (LH - LL) * (bot - top)
    for (i0, i1, ty, head, up) in R['tsegs']:                 # 走势背景：按段型（§八 1，10-08 起）
        if i1 < b0 or i0 > b1: continue
        c = (208, 215, 222) if (head or ty not in TYPE) else TYPE[ty]
        al = 20 if (head or ty not in TYPE) else 40
        q.rectangle([max(ML, X(i0)), top, min(W - MR, X(i1)), bot], fill=c + (al,))
    for i in range(b0, b1 + 1):
        b = bars[i]; q.line([X(i), Y(b['h']), X(i), Y(b['l'])], fill=(120, 126, 140, 160))
    for (x0, x1, zd, zg) in R['zs']:
        if x0 is None or x1 < b0 or x0 > b1: continue
        # 左右各内缩 3px：同级别下中枢满三段就收、前后两个框首尾相接，不缩的话两个框的边贴在一起，
        #   看着像一个框被分界刀从中间劈开（Nova 10-09 04:43 看到的就是这个错觉）。框里铺一层淡金，框和框之间露出一条缝。
        q.rectangle([X(x0) + 3, Y(zg), X(x1) - 3, Y(zd)], fill=(196, 137, 1, 28), outline=(196, 137, 1, 220), width=2)
    othp = set(other['pens'])
    for (i0, i1, p0, p1) in R['pens']:                          # 笔：灰；只在这一格有的笔用浅青加粗（B-10 老笔新笔要看这一层）
        if i1 < b0 or i0 > b1: continue
        mine = (i0, i1, p0, p1) not in othp
        q.line([X(i0), Y(p0), X(i1), Y(p1)], fill=(255, 120, 200, 235) if mine else (122, 137, 166, 200), width=3 if mine else 1)   # 粉：跟线段的青分开
    oth = set(other['segs']); othb = {x[:2] for x in other['bounds']}
    for s in R['segs'] + R['live']:
        i0, i1, p0, p1 = s
        if i1 < b0 or i0 > b1: continue
        mine = s not in oth and s in R['segs']
        q.line([X(i0), Y(p0), X(i1), Y(p1)], fill=(80, 200, 255) if mine else (196, 137, 1), width=5 if mine else 2)
    for (bar, kind, price, death) in R['bounds']:                # 价签夹在画框里：贴边的价签不许被框外刷底色刷掉
        if bar < b0 or bar > b1: continue
        mine = (bar, kind) not in othb; x = X(bar)
        for yy in range(top, bot, 10): q.line([x, yy, x, yy + 5], fill=(234, 238, 246, 255 if mine else 150), width=3 if mine else 1)
        q.ellipse([x - 5, Y(price) - 5, x + 5, Y(price) + 5], fill=TX)
        q.text((x + 6, min(bot - 22, max(top + 2, Y(price) + (-26 if kind == 'H' else 8)))), f'{price:g}' + (f' · {death}' if death else ''), fill=TX if mine else MU, font=Fs)
    for (fb, tb, kind) in R.get('moved', []):                  # 挪刀：橙色空心圈＝刀原来立的地方，箭头指到挪过去的地方
        if max(fb, tb) < b0 or min(fb, tb) > b1: continue
        px = lambda i: bars[i]['h'] if kind == 'H' else bars[i]['l']
        x0, y0_, x1, y1 = X(fb), Y(px(fb)), X(tb), Y(px(tb))
        q.line([x0, y0_, x1, y1], fill=(255, 150, 40, 230), width=2)
        q.ellipse([x0 - 8, y0_ - 8, x0 + 8, y0_ + 8], outline=(255, 150, 40), width=3)
        q.polygon([(x1, y1), (x1 - 9 if x1 > x0 else x1 + 9, y1 - 5), (x1 - 9 if x1 > x0 else x1 + 9, y1 + 5)], fill=(255, 150, 40))
        q.text((x0 - 14, y0_ + (14 if kind == 'L' else -34)), f'挪刀 {px(fb):g}', fill=(255, 150, 40), font=Fs)
    for ((bar, kind, price), n) in R.get('retr', []):              # 撤回：红叉＝这把刀立过又被撤掉，旁边写撤了几次（同一把刀可以立了撤、撤了又立）
        if bar < b0 or bar > b1: continue
        x, y = X(bar), Y(price)
        q.line([x - 9, y - 9, x + 9, y + 9], fill=(255, 80, 80), width=3); q.line([x - 9, y + 9, x + 9, y - 9], fill=(255, 80, 80), width=3)
        lx, ly = (x - 60 if x - 60 > ML + 2 else x + 12), min(bot - 22, max(top + 2, y + (30 if kind == 'H' else -48)))
        q.rectangle(q.textbbox((lx, ly), f'撤回×{n}', font=Fs), fill=BG + (230,))   # 垫一块底色：红字压在框边、刀点上会糊
        q.text((lx, ly), f'撤回×{n}', fill=(255, 110, 110), font=Fs)
    if k == 1:                                                    # --mark：只圈下格（翻了开关之后那一格）
        for mk in a.mark:
            ts, pv, lab = mk.split('|', 2); pv = float(pv)
            y = utc(0).year; t = DT.datetime.strptime(f'{y}-{ts}', '%Y-%m-%d %H:%M').replace(tzinfo=DT.timezone.utc).timestamp() * 1e3
            i = next((j for j, b in enumerate(bars) if b['t'] >= t), None)
            if i is None or i < b0 or i > b1: continue
            x, yv = X(i), Y(pv)
            q.ellipse([x - 13, yv - 13, x + 13, yv + 13], outline=(255, 150, 40), width=3)
            lx, ly = x + 18, min(bot - 24, max(top + 2, yv + 6))
            q.rectangle(q.textbbox((lx, ly), lab, font=Fs), fill=BG + (230,)); q.text((lx, ly), lab, fill=(255, 170, 70), font=Fs)
    # 画框外的一律刷回底色：框和线都不许越出画框（左右上下四边，ZD 低于窗口时框边会一路画到格外）
    q.rectangle([0, 0, ML - 1, PH], fill=BG); q.rectangle([W - MR + 1, 0, W, PH], fill=BG)
    q.rectangle([0, 0, W, top - 1], fill=BG); q.rectangle([0, bot + 1, W, PH], fill=BG)
    q.rectangle([ML, top, W - MR, bot], outline=(60, 66, 80))
    q.text((ML + 6, 4), tag, fill=TX, font=F)
    short = (bars[b1]['t'] - bars[b0]['t']) / 10 < 86400e3 * 1.5   # 刻度间隔不到一天半就带上时分（10 格），免得一排两个同样的日期（8 天窗口出过 05-07 05-07）
    # 最右一个刻度往里收，别被画布边切掉
    for i in range(b0, b1 + 1, max(1, (b1 - b0) // 10)): q.text((min(W - MR - (80 if short else 48), X(i) - (40 if short else 24)), bot + 4), f'{utc(i):%m-%d %H:%M}' if short else f'{utc(i):%m-%d}', fill=MU, font=Fs)
    for v in sorted({float(f'{lo * (hi / lo) ** (j / 6):.3g}') for j in range(1, 6)}):
        q.text((6, Y(v) - 8), f'{v:g}', fill=MU, font=Fs); q.line([ML - 5, Y(v), ML, Y(v)], fill=MU)
    im.paste(p, (0, y0))
panel(0, A, B, '上：' + a.label_a); panel(1, B, A, '下：' + a.label_b)
d.text((ML, 90 + 2 * (PH + 30) + 6), '画法：背景＝段型（绿涨／红跌／灰盘整）；笔灰、线段金，只在这一格有的笔加粗粉、线段加粗青；分界白虚线，只在这一格有的加粗；橙圈→箭头＝挪刀；红叉＝撤回（×n 次）；价旁写死点类型；对数轴，两格同一把尺。',
       fill=MU, font=Fs)
if a.note: d.text((ML, 90 + 2 * (PH + 30) + 34), '注：' + a.note, fill=TX, font=Fs)
im.save(a.out); print('saved', a.out, im.size, dd)
