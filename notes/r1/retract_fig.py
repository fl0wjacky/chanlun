# Q-6「已撤回」示意图（Nova 10-09 11:41）：同一份 K 线截到前 N1、N2 根各跑一遍引擎，上下两格。
#   这不是排错图，是**给小栋看的画法提案**：照网站的画法画（实心点＝确认、空心点＝待确认），
#   只在下格加一样新东西 —— 上一格确认过、这一格没了的刀，原位置留**淡色叉**，旁边写「已撤回：笔回头改了」。
#   python retract_fig.py --root <引擎仓> --json <K 线 json> --tick 0.01 --at 8745,8746 --from-bar 5900 --out x.png
#   口径（同级别正式口径、锁关、D-2⁗＋D-4′＋D2-5 档 3）在下面写死；开关只在进程里翻，仓里一个字不动。
import sys, os, json, argparse, math, datetime as DT
ap = argparse.ArgumentParser()
ap.add_argument('--root', required=True); ap.add_argument('--json', required=True); ap.add_argument('--tick', type=float, required=True)
ap.add_argument('--at', required=True); ap.add_argument('--from-bar', type=int, required=True); ap.add_argument('--out', required=True)
ap.add_argument('--title', default='Q-6 A「撤的时候老实标出来」示意'); ap.add_argument('--note', default='')
a = ap.parse_args()
out, jpath = os.path.abspath(a.out), os.path.abspath(a.json)
sys.path[:0] = [a.root]; os.chdir(a.root)
import config
from core.analyze import analyze
import core.trend as TR, core.pen as PEN
from render.style import BG, TX, MU
from PIL import Image, ImageDraw, ImageFont
for k, v in dict(SAME_LEVEL=True, SAME_LEVEL_D2=True, SAME_LEVEL_D6='fallback', SL_FIRST_EXEMPT=True, SAME_LEVEL_DEATH=True, D25_FILL=3).items(): setattr(TR, k, v)
PEN.PEN_FINAL_LOCK = False

bars = json.load(open(jpath, encoding='utf-8'))
N1, N2 = [int(x) for x in a.at.split(',')]
utc = lambda i: DT.datetime.fromtimestamp(bars[i]['t'] / 1000, DT.timezone.utc)
def run(n):
    r = analyze(bars[:n], tick=a.tick); t = TR.trend_v3(r)
    return dict(n=n, pens=[(p['i0'], p['i1'], p['p0'], p['p1']) for p in r['pens']],
                segs=[(s['i0'], s['i1'], s['p0'], s['p1']) for s in r['segs']],
                bounds={(b['bar'], b['kind']): (b['price'], b.get('state'), b.get('death')) for b in t['bounds']})
A, B = run(N1), run(N2)
gone = {k: v for k, v in A['bounds'].items() if k not in B['bounds'] and v[1] == 'confirmed'}            # 确认过又没了 ⇒ 已撤回
back = {k for k, v in B['bounds'].items() if k in A['bounds'] and A['bounds'][k][1] == 'confirmed' and v[1] == 'pending'}   # 确认过又回待确认
for k, v in sorted(gone.items()): print('撤回', k, f'{utc(k[0]):%m-%d %H:%M}', v)
for k in sorted(back): print('回待确认', k, f'{utc(k[0]):%m-%d %H:%M}', B['bounds'][k])

b0, b1 = a.from_bar, N2 - 1
font = lambda s: ImageFont.truetype(config._pick_font(), s)
F, Fs, Fb = font(20), font(15), font(17)
W, PH, ML, MR = 2000, 540, 80, 150
NOTE_H = 96 if a.note else 64
im = Image.new('RGB', (W, 70 + 2 * (PH + 26) + NOTE_H), BG); d = ImageDraw.Draw(im)
win = bars[b0:b1 + 1]; lo = min(x['l'] for x in win) * 0.985; hi = max(x['h'] for x in win) * 1.015
LL, LH = math.log(lo), math.log(hi)
d.text((ML, 14), a.title, fill=TX, font=F)
d.text((ML, 42), f'快照 AAPL 15m · 同级别正式口径、锁关 · 上格截到第 {N1} 根（{utc(N1 - 1):%m-%d %H:%M}），下格多走一根（{utc(N2 - 1):%m-%d %H:%M}）', fill=MU, font=Fs)
RED = (255, 96, 96)

def panel(k, R, other, tag):
    y0 = 70 + k * (PH + 26); top, bot = 30, PH - 26
    p = Image.new('RGB', (W, PH), BG); q = ImageDraw.Draw(p, 'RGBA')
    X = lambda i: ML + (i - b0) * (W - ML - MR) / max(1, b1 - b0)
    Y = lambda v: top + (LH - math.log(v)) / (LH - LL) * (bot - top)
    for i in range(b0, R['n']):
        b = bars[i]; q.line([X(i), Y(b['h']), X(i), Y(b['l'])], fill=(120, 126, 140, 150))
    othp = set(other['pens'])
    for s in R['pens']:
        i0, i1, p0, p1 = s
        if i1 < b0: continue
        mine = s not in othp                                     # 只在这一格有的笔：粉色加粗 —— 上格是要被改掉的那几笔，下格是改出来的（＝「笔回头改了」那一处）
        q.line([X(max(i0, b0)), Y(p0 if i0 >= b0 else p0 + (p1 - p0) * (b0 - i0) / (i1 - i0)), X(i1), Y(p1)], fill=(255, 120, 200, 235) if mine else (122, 137, 166, 200), width=3 if mine else 1)
    for (i0, i1, p0, p1) in R['segs']:
        if i1 < b0: continue
        q.line([X(max(i0, b0)), Y(p0 if i0 >= b0 else p0 + (p1 - p0) * (b0 - i0) / (i1 - i0)), X(i1), Y(p1)], fill=(196, 137, 1), width=2)
    def label(x, y, kind, txt, col):
        ly = min(bot - 22, max(top + 2, y + (-30 if kind == 'H' else 10)))
        bb = q.textbbox((x + 8, ly), txt, font=Fs); q.rectangle(bb, fill=BG + (220,)); q.text((x + 8, ly), txt, fill=col, font=Fs)
    for (bar, kind), (price, state, death) in sorted(R['bounds'].items()):
        if bar < b0: continue
        x, y = X(bar), Y(price)
        for yy in range(top, bot, 10): q.line([x, yy, x, yy + 5], fill=(234, 238, 246, 170), width=1)
        if state == 'pending':
            q.ellipse([x - 6, y - 6, x + 6, y + 6], outline=TX, width=2, fill=BG)
            txt = f'{price:g}（{"回到待确认" if k == 1 and (bar, kind) in back else "待确认"}）'
            label(x, y, kind, txt, (255, 190, 60) if k == 1 and (bar, kind) in back else MU)
        else:
            q.ellipse([x - 6, y - 6, x + 6, y + 6], fill=TX)
            label(x, y, kind, f'{price:g}', TX)
    if k == 1:                                                  # 提案的那一样：原位置淡色叉＋一句话
        for (bar, kind), (price, _, _) in gone.items():
            x, y = X(bar), Y(price)
            for yy in range(top, bot, 10): q.line([x, yy, x, yy + 5], fill=RED + (70,), width=1)
            q.line([x - 10, y - 10, x + 10, y + 10], fill=RED + (150,), width=3); q.line([x - 10, y + 10, x + 10, y - 10], fill=RED + (150,), width=3)
            txt = f'已撤回：笔回头改了（{price:g}，{utc(bar):%m-%d %H:%M}）'
            ly = min(bot - 24, y + 16); bb = q.textbbox((x + 14, ly), txt, font=Fb); q.rectangle(bb, fill=BG + (230,)); q.text((x + 14, ly), txt, fill=RED, font=Fb)
    xn = X(R['n'] - 1)                                          # 「此刻」：最右那根
    q.line([xn, top, xn, bot], fill=(255, 190, 60, 120), width=1)
    q.text((xn + 6, top + 4), f'此刻\n{utc(R["n"] - 1):%m-%d %H:%M}', fill=(255, 190, 60), font=Fs)
    q.rectangle([0, 0, ML - 1, PH], fill=BG); q.rectangle([0, 0, W, top - 1], fill=BG); q.rectangle([0, bot + 1, W, PH], fill=BG)
    q.rectangle([ML, top, W - MR, bot], outline=(60, 66, 80))
    q.text((ML + 6, 4), tag, fill=TX, font=F)
    for i in range(b0, b1 + 1, max(1, (b1 - b0) // 10)): q.text((min(W - MR - 48, X(i) - 24), bot + 4), f'{utc(i):%m-%d}', fill=MU, font=Fs)
    for v in sorted({float(f'{lo * (hi / lo) ** (j / 6):.3g}') for j in range(1, 6)}):
        q.text((6, Y(v) - 8), f'{v:g}', fill=MU, font=Fs); q.line([ML - 5, Y(v), ML, Y(v)], fill=MU)
    im.paste(p, (0, y0))

panel(0, A, B, f'上：截到第 {N1} 根 —— 这几刀都已确认（实心点）')
panel(1, B, A, f'下：再走一根（第 {N2} 根）—— 笔回头改了，一刀撤回、三刀回到待确认')
yb = 70 + 2 * (PH + 26) + 4
d.text((ML, yb), '画法：笔灰、线段金；只在这一格有的笔加粗粉（上格＝要被改掉的，下格＝改出来的）；分界白虚线，实心点＝已确认、空心点＝待确认；琥珀竖线＝此刻（最新那根）；红色淡叉＝已撤回（提案的新画法）。对数轴，两格同一把尺。', fill=MU, font=Fs)
if a.note: d.text((ML, yb + 30), '注：' + a.note, fill=TX, font=Fs)
im.save(out); print('saved', out, im.size)
