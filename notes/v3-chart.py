"""v3 改前／改后对照图（只读，不改引擎）。用法：python3 notes/v3-chart.py zec15.json out.svg
上半：改前 ＝ 现在线上 turn（笔层出刀）的线段中枢框和刀。
下半：改后 ＝ notes/v3-proto.py 的分界；走势背景上涨绿、下跌红（小栋 10-05 13:27Z）；
      中阴（极值 → 确立那一根）画斜线；框用 v3 分界重算的那一套。"""
import sys, io, runpy, contextlib, datetime as D, importlib
fn, out = sys.argv[1], sys.argv[2]
sys.argv = ['v3-proto.py', fn]
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path('notes/v3-proto.py')
B, done, ks, bnd, r = g['B'], g['done'], g['ks'], g['bnd'], g['r']
C = importlib.import_module('core.cut'); S = importlib.import_module('core.signals')
cur_turn, cuts_turn = C.cut_centers(r, S.signals(r, 'pen', 'macd'))
zs_v3 = C._centers_with_cuts(done, ks)
N = len(B)
ts = lambda i: D.datetime.utcfromtimestamp(B[i]['t'] / 1000).strftime('%m-%d')

W, PH, ML, MR, MT, GAP = 1600, 380, 70, 20, 56, 70
H = MT + PH * 2 + GAP + 70
lo = min(b['l'] for b in B); hi = max(b['h'] for b in B)
X = lambda i: ML + (W - ML - MR) * i / (N - 1)
def Y(p, top): return top + PH - (PH - 44) * (p - lo) / (hi - lo) - 30

GREEN, RED, INK, MUTED, GRID = '#2e9e5b', '#d64545', '#1f2328', '#6e7781', '#e6e8eb'
o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="PingFang SC, Hiragino Sans GB, sans-serif">' % (W, H),
     '<defs><pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
     '<line x1="0" y1="0" x2="0" y2="8" stroke="#8c959f" stroke-width="2"/></pattern></defs>',
     '<rect width="100%" height="100%" fill="#ffffff"/>']
name = {'zec15.json': 'ZEC 15m', 'zec30_cut.json': 'ZEC 30m'}.get(fn, fn)
o.append('<text x="%d" y="28" font-size="20" fill="%s" font-weight="600">%s · 走势分段 改前／改后（夹具 data/%s，引擎 main e494d90）</text>' % (ML, INK, name, fn))

def price_line(top):
    step = max(1, N // 1400); pts = []
    for a in range(0, N, step):
        seg = B[a:a + step]
        i_hi = max(range(len(seg)), key=lambda k: seg[k]['h']); i_lo = min(range(len(seg)), key=lambda k: seg[k]['l'])
        for k in sorted({i_hi, i_lo}):
            p = seg[k]['h'] if k == i_hi else seg[k]['l']
            pts.append('%.1f,%.1f' % (X(a + k), Y(p, top)))
    o.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="1" opacity="0.85"/>' % (' '.join(pts), INK))

def axes(top, title):
    for f in (0, .25, .5, .75, 1):
        p = lo + (hi - lo) * f; y = Y(p, top)
        o.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s"/>' % (ML, W - MR, y, y, GRID))
        o.append('<text x="%d" y="%.1f" font-size="12" fill="%s" text-anchor="end">%.0f</text>' % (ML - 6, y + 4, MUTED, p))
    for i in range(0, N, N // 8):
        o.append('<text x="%.1f" y="%d" font-size="12" fill="%s" text-anchor="middle">%s</text>' % (X(i), top + PH + 16, MUTED, ts(i)))
    o.append('<text x="%d" y="%d" font-size="15" fill="%s" font-weight="600">%s</text>' % (ML, top - 8, INK, title))

def boxes(zs, top, color):
    for z in zs:
        x0, x1 = X(z['X0']), X(z['X1'])
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" stroke="%s" stroke-width="1.5"/>'
                 % (x0, Y(z['ZG'], top), max(1, x1 - x0), Y(z['ZD'], top) - Y(z['ZG'], top), color))

# ---- 改前 ----
top1 = MT + 20
done_cuts = [c for c in cuts_turn if c['status'] == 'done']
axes(top1, '改前：现在线上的样子（turn：笔层出刀，%d 把已定的刀，灰竖线；蓝框＝线段中枢）' % len(done_cuts))
for c in done_cuts:
    x = X(c['cut_bar']); o.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="#8c959f" stroke-width="1"/>' % (x, x, top1, top1 + PH))
boxes(cur_turn, top1, '#3b6fd4')
price_line(top1)

# ---- 改后 ----
top2 = top1 + PH + GAP
axes(top2, '改后：v3 原型（%d 个分界；绿＝上涨、红＝下跌；斜线＝中阴：极值已出、还没确立）' % len(bnd))
cutbars = [done[j]['i1'] for j, _, _, _ in bnd]
edges = [0] + cutbars + [N - 1]
for k in range(len(edges) - 1):
    a, b = edges[k], edges[k + 1]
    if k == 0:
        col, op = '#d0d7de', .35                                  # 图头：方向未定
    else:
        typ = bnd[k - 1][1]; col = GREEN if typ == 'L' else RED; op = .16 if k < len(edges) - 2 else .08
    o.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s" opacity="%.2f"/>' % (X(a), top2, X(b) - X(a), PH, col, op))
for j, typ, t, z in bnd:                                          # 中阴：极值那一根 → 确立那一根
    a, b = done[j]['i1'], done[t]['i1']
    o.append('<rect x="%.1f" y="%d" width="%.1f" height="12" fill="url(#hatch)"/>' % (X(a), top2 + PH - 12, X(b) - X(a)))
boxes(zs_v3, top2, '#3b6fd4')
price_line(top2)
for j, typ, t, z in bnd:
    s = done[j]; x, y = X(s['i1']), Y(s['p1'], top2)
    o.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="%s" stroke-width="1.5" stroke-dasharray="4 3"/>' % (x, x, top2, top2 + PH, INK))
    o.append('<circle cx="%.1f" cy="%.1f" r="4.5" fill="%s" stroke="#fff" stroke-width="2"/>' % (x, y, INK))
    dy = -10 if typ == 'H' else 20
    o.append('<text x="%.1f" y="%.1f" font-size="13" fill="%s" text-anchor="middle" font-weight="600" stroke="#fff" stroke-width="3" paint-order="stroke">%.2f</text>' % (x, y + dy, INK, s['p1']))
# 图尾：最后一个分界之后的极值，还没确立 ⇒ 中阴（候选，会换）
if bnd:
    jl, tl = bnd[-1][0], bnd[-1][1]
    want_up = tl == 'L'
    cand = [k for k in range(jl + 1, len(done)) if (done[k]['p1'] > done[k]['p0']) == want_up]
    if cand:
        k = (max if want_up else min)(cand, key=lambda q: (done[q]['p1'], q))
        x, y = X(done[k]['i1']), Y(done[k]['p1'], top2)
        o.append('<rect x="%.1f" y="%d" width="%.1f" height="12" fill="url(#hatch)"/>' % (x, top2 + PH - 12, X(N - 1) - x))
        o.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="%s" stroke-width="1.5" stroke-dasharray="2 4"/>' % (x, x, top2, top2 + PH, MUTED))
        o.append('<text x="%.1f" y="%.1f" font-size="13" fill="%s" text-anchor="end" stroke="#fff" stroke-width="3" paint-order="stroke">%.2f 待定（中阴：还没出反方向三类点）</text>' % (x - 8, y + 4, MUTED, done[k]['p1']))
o.append('<text x="%d" y="%d" font-size="12" fill="%s">最后一段（浅色）还在长：极值已出但没确立，标「待定」，后面价格再创新高它就换。图头（灰）方向未定。框：v3 按分界两边各自重算的线段中枢。脚本 notes/v3-chart.py。</text>' % (ML, H - 14, MUTED))
o.append('</svg>')
open(out, 'w').write('\n'.join(o))
print(out, 'bnd', [(round(done[j]['p1'], 2), typ) for j, typ, _, _ in bnd], 'turn done cuts', len(done_cuts))
