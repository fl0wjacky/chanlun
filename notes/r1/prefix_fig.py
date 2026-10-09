# 前缀连锁图：同一份 K 线截到第 N1、N2… 根各跑一遍引擎，一格一格往下排，看「尾笔改了 → 线段撤 → 分界撤」怎么传下来。
#   python prefix_fig.py --root <仓> --file zec15.json --at 3000,3060,3100 [--base core.trend.SAME_LEVEL=True …] --from 03-05 --to 03-20 --out x.png
#   --json <K 线 json> --tick <精度>：快照不在 data/ 里的时候直接喂 K 线（Bram 导出来的那一截）。
#   每一格跟上一格比：上一格有、这一格没了的笔／线段／刀画红色虚影（＝被撤掉的），这一格新出来的加粗（粉笔、青线段、粗白刀）。
#   开关只在进程里翻（setattr），仓里的默认值一个字不动。
import sys, os, json, argparse, importlib, math, datetime as DT
ap = argparse.ArgumentParser()
ap.add_argument('--root', required=True); ap.add_argument('--base', action='append', default=[])
ap.add_argument('--file'); ap.add_argument('--json'); ap.add_argument('--tick', type=float)
ap.add_argument('--at', required=True, help='逗号分隔的 K 线根数（前缀长度），从小到大')
ap.add_argument('--from', dest='frm'); ap.add_argument('--to'); ap.add_argument('--out', required=True)
ap.add_argument('--base-label', default=None, help='表头里口径那一截的简称（开关全名太长会冲出右边）'); ap.add_argument('--pen', default='old'); ap.add_argument('--title', default='前缀连锁图'); ap.add_argument('--note', default='')
a = ap.parse_args()
out = os.path.abspath(a.out); jpath = os.path.abspath(a.json) if a.json else None
sys.path[:0] = [a.root]; os.chdir(a.root)
from core.analyze import analyze
import core.trend as TR
from PIL import Image, ImageDraw, ImageFont

def parse(f):
    k, v = f.split('=', 1); mod, attr = k.rsplit('.', 1)
    return importlib.import_module(mod), attr, {'True': True, 'False': False}.get(v, v)
for m, at, v in map(parse, a.base): setattr(m, at, v)

if jpath:
    bars, tick = json.load(open(jpath, encoding='utf-8')), a.tick
else:
    from config import data, tick_of
    bars, tick = json.load(open(data(a.file), encoding='utf-8')), tick_of(a.file)
AT = [int(x) for x in a.at.split(',')]
assert AT == sorted(AT) and AT[-1] <= len(bars), f'--at 要从小到大、不超过 {len(bars)} 根'

def run(n):
    r = analyze(bars[:n], tick=tick, pen=a.pen); t = TR.trend_v3(r)
    return dict(n=n,
                pens={(p['i0'], p['i1'], p['p0'], p['p1']) for p in r['pens']},
                segs={(s['i0'], s['i1'], s['p0'], s['p1']) for s in r['segs']},
                live={(s['i0'], s['i1']) for s in r['segs'] if s.get('live')},
                bounds={(b['bar'], b['kind'], b['price']) for b in t['bounds']},
                pending={(b['bar'], b['kind']) for b in t.get('pending', []) if isinstance(b, dict) and 'bar' in b})
R = [run(n) for n in AT]

utc = lambda i: DT.datetime.fromtimestamp(bars[i]['t'] / 1e3, DT.timezone.utc)
def ix(s):
    if s is None: return None
    y = utc(0).year; d = DT.datetime.strptime(f'{y}-{s}', '%Y-%m-%d').replace(tzinfo=DT.timezone.utc).timestamp() * 1e3
    return next((i for i, b in enumerate(bars) if b['t'] >= d), len(bars) - 1)
b0 = ix(a.frm) if a.frm else max(0, AT[0] - 400)
b1 = min(ix(a.to) if a.to else AT[-1] + 20, len(bars) - 1)
lo = min(bars[i]['l'] for i in range(b0, b1 + 1)); hi = max(bars[i]['h'] for i in range(b0, b1 + 1))
LL, LH = math.log(lo) - 0.02, math.log(hi) + 0.02

import config
F = ImageFont.truetype(config._pick_font(), 26); Fs = ImageFont.truetype(config._pick_font(), 20)   # 跟 r1_fig 同一支字体（仓里挑的那支，缺字形会被 fontcheck 抓）
BG, TX, MU = (18, 20, 26), (234, 238, 246), (140, 148, 166)
W, ML, MR, PH = 2000, 80, 20, 420
H = 90 + len(R) * (PH + 30) + 44 + 26 * max(1, len(a.note.split('|')) if a.note else 1)
im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
d.text((ML, 14), f'{a.file or os.path.basename(jpath)} · {a.title} · 口径 {a.base_label or (" ".join(f.rsplit(".", 1)[-1] for f in a.base) or "现行")}', fill=TX, font=F)
d.text((ML, 48), f'窗口 {utc(b0):%Y-%m-%d %H:%M} → {utc(b1):%Y-%m-%d %H:%M}（UTC）｜截到 ' + '、'.join(f'第 {n} 根' for n in AT), fill=MU, font=Fs)

def dash(q, x0, y0, x1, y1, fill, width=2, on=8, off=6):
    L = math.hypot(x1 - x0, y1 - y0) or 1; k = 0.0
    while k < L:
        e = min(L, k + on); q.line([x0 + (x1 - x0) * k / L, y0 + (y1 - y0) * k / L, x0 + (x1 - x0) * e / L, y0 + (y1 - y0) * e / L], fill=fill, width=width); k = e + off

for k, cur in enumerate(R):
    prev = R[k - 1] if k else None
    y0 = 90 + k * (PH + 30); top, bot = 28, PH - 26
    p = Image.new('RGB', (W, PH), BG); q = ImageDraw.Draw(p, 'RGBA')
    X = lambda i: ML + (i - b0) * (W - ML - MR) / max(1, b1 - b0)
    Y = lambda v: top + (LH - math.log(v)) / (LH - LL) * (bot - top)
    end = cur['n'] - 1
    for i in range(b0, min(b1, end) + 1):
        b = bars[i]; q.line([X(i), Y(b['h']), X(i), Y(b['l'])], fill=(120, 126, 140, 160))
    if b0 <= end <= b1: q.rectangle([X(end) + 1, top, W - MR, bot], fill=(255, 255, 255, 10))   # 还没走出来的那一截：淡底
    for (i0, i1, p0, p1) in (prev['pens'] - cur['pens'] if prev else ()):                    # 被撤掉的笔：红虚影
        dash(q, X(i0), Y(p0), X(i1), Y(p1), (255, 90, 90, 200), 2)
    for (i0, i1, p0, p1) in cur['pens']:
        new = prev is not None and (i0, i1, p0, p1) not in prev['pens']
        q.line([X(i0), Y(p0), X(i1), Y(p1)], fill=(255, 120, 200, 235) if new else (122, 137, 166, 200), width=3 if new else 1)
    for (i0, i1, p0, p1) in (prev['segs'] - cur['segs'] if prev else ()):                    # 被撤掉的线段：红虚影（粗）
        dash(q, X(i0), Y(p0), X(i1), Y(p1), (255, 70, 70, 230), 4, 14, 8)
    for s in cur['segs']:
        i0, i1, p0, p1 = s; new = prev is not None and s not in prev['segs']
        q.line([X(i0), Y(p0), X(i1), Y(p1)], fill=(80, 200, 255) if new else (196, 137, 1), width=5 if new else 2)
    for (bar, kind, price) in (prev['bounds'] - cur['bounds'] if prev else ()):              # 被撤掉的刀：红虚线＋叉
        x = X(bar)
        for yy in range(top, bot, 12): q.line([x, yy, x, yy + 6], fill=(255, 80, 80, 220), width=3)
        yv = Y(price); q.line([x - 9, yv - 9, x + 9, yv + 9], fill=(255, 80, 80), width=3); q.line([x - 9, yv + 9, x + 9, yv - 9], fill=(255, 80, 80), width=3)
        q.text((x + 8, min(bot - 22, max(top + 2, yv + (8 if kind == 'H' else -26)))), f'{price:g} 撤', fill=(255, 110, 110), font=Fs)
    for (bar, kind, price) in cur['bounds']:
        x = X(bar); new = prev is not None and (bar, kind, price) not in prev['bounds']
        for yy in range(top, bot, 10): q.line([x, yy, x, yy + 5], fill=(234, 238, 246, 255 if new else 150), width=3 if new else 1)
        q.ellipse([x - 5, Y(price) - 5, x + 5, Y(price) + 5], fill=TX)
        q.text((x + 6, min(bot - 22, max(top + 2, Y(price) + (-26 if kind == 'H' else 8)))), f'{price:g}', fill=TX if new else MU, font=Fs)
    q.rectangle([0, 0, ML - 1, PH], fill=BG); q.rectangle([W - MR + 1, 0, W, PH], fill=BG)
    q.rectangle([0, 0, W, top - 1], fill=BG); q.rectangle([0, bot + 1, W, PH], fill=BG)
    q.rectangle([ML, top, W - MR, bot], outline=(60, 66, 80))
    if b0 <= end <= b1:
        q.line([X(end), top, X(end), bot], fill=(255, 210, 90), width=2)
        q.text((X(end) + 6 if X(end) + 220 < W - MR else X(end) - 200, top + 4), f'截到第 {cur["n"]} 根', fill=(255, 210, 90), font=Fs)
    dl = ''
    if prev:
        # 不用 U+2212 减号：仓里那支 CJK 字体没有这个字形，会画成豆腐块（10-09 r1-fig 踩过）
        dl = (f' ｜ 跟上一格比：笔 撤 {len(prev["pens"] - cur["pens"])}／新 {len(cur["pens"] - prev["pens"])}，'
              f'线段 撤 {len(prev["segs"] - cur["segs"])}／新 {len(cur["segs"] - prev["segs"])}，刀 撤 {len(prev["bounds"] - cur["bounds"])}／新 {len(cur["bounds"] - prev["bounds"])}')
    q.text((ML + 6, 2), f'{"①②③④⑤⑥⑦⑧"[k]} 截到第 {cur["n"]} 根（{utc(end):%m-%d %H:%M}）{dl}', fill=TX, font=F)
    short = (bars[b1]['t'] - bars[b0]['t']) / 10 < 86400e3 * 1.5
    for i in range(b0, b1 + 1, max(1, (b1 - b0) // 10)):
        q.text((min(W - MR - (80 if short else 48), X(i) - (40 if short else 24)), bot + 4), f'{utc(i):%m-%d %H:%M}' if short else f'{utc(i):%m-%d}', fill=MU, font=Fs)
    for v in sorted({float(f'{lo * (hi / lo) ** (j / 6):.3g}') for j in range(1, 6)}):
        q.text((6, Y(v) - 8), f'{v:g}', fill=MU, font=Fs); q.line([ML - 5, Y(v), ML, Y(v)], fill=MU)
    im.paste(p, (0, y0))
yb = 90 + len(R) * (PH + 30) + 4
d.text((ML, yb), '画法：笔灰、线段金、分界白虚线；跟上一格比新出来的加粗（粉笔／青线段／粗白刀），上一格有、这一格没了的画红虚影（刀加红叉）。黄竖线＝截到哪一根，右边淡底＝还没走出来。对数轴。', fill=MU, font=Fs)
for j, line in enumerate(a.note.split('|') if a.note else []): d.text((ML, yb + 28 + 26 * j), ('注：' if j == 0 else '　　') + line, fill=TX, font=Fs)   # 图注用 | 分行
im.save(out); print('saved', out, im.size, [(x['n'], len(x['pens']), len(x['segs']), len(x['bounds'])) for x in R])
