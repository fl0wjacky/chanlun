# card-753bd03a：chanlun.pine 这次新写的 L78 部分逐行抄成 Python，跟引擎整段／逐根对账（Pine 本机跑不了）。
# 用法：python3 notes/pine-l78-parity.py [线上 /api/chart 载荷.json]。反向验证：把 caseAt 里 stop 改回 mEnd[s0]（最后一笔为界）⇒ zec15 红。
# Line-by-line Python transliteration of the NEW Pine code (chanlun.pine: reverseConfirmPen / caseAt(...memo) /
# firstSegFill / buildSegments / zSegStep continuation), checked against core.segment.build_segments.
# Reuses only the UNCHANGED helpers (featStd/hasFractal/reverseScan/openingOverlaps) from the engine.
import sys, os, json
sys.path[:0] = ['tools', '.']
from trend_check import load, kline_files
from core.analyze import analyze
from core.segment import build_segments, _feature_std, _reverse_scan, _opening_overlaps
from config import tick_of

isUp = lambda u: u["p1"] > u["p0"]

def featStd(eh, el, up):
    return [(x["h"], x["l"]) for x in _feature_std([dict(h=h, l=l, i=t) for t, (h, l) in enumerate(zip(eh, el))], up)]

def hasFractal(m, wantTop):
    for k in range(1, len(m) - 1):
        (h0, l0), (h1, l1), (h2, l2) = m[k - 1], m[k], m[k + 1]
        if (h1 > h0 and h1 > h2 and l1 > l0 and l1 > l2) if wantTop else (l1 < l0 and l1 < l2 and h1 < h0 and h1 < h2):
            return True
    return False

def contains(ah, al, bh, bl): return (ah >= bh and al <= bl) or (bh >= ah and bl <= al)

def reverseConfirmPen(P, endPen, segUp, e3):
    n = len(P); pivot = P[endPen]["p1"]; eh, el = [], []; ntail = 0; res = n; fin = False; j = endPen + 1
    while j < n and not fin:
        p = P[j]
        if (p["hi"] > pivot) if segUp else (p["lo"] < pivot):
            fin = True
        else:
            ntail += 1
            if isUp(p) == segUp: eh.append(p["hi"]); el.append(p["lo"])
            if ntail >= 3 and len(eh) >= 3 and hasFractal(featStd(eh, el, not segUp), not segUp):
                res = max(j, e3); fin = True
        j += 1
    return res

def caseAt(P, i, k, up, mEnd, mConf, mDir):
    n = len(P); cse = 0; at = -1
    eh = [P[j]["hi"] for j in range(i + 1, k) if isUp(P[j]) != up]
    el = [P[j]["lo"] for j in range(i + 1, k) if isUp(P[j]) != up]
    if eh and k + 1 < n:
        m = featStd(eh, el, up); e1h, e1l = m[-1]
        V = P[k]["p1"]; e2h, e2l = P[k + 1]["hi"], P[k + 1]["lo"]
        if not ((V <= e1h) if up else (V >= e1l)):
            gap = (e1h < e2l) if up else (e1l > e2h)
            if not gap:
                L = P[k + 1]["p1"]; s0 = k + 2
                okRev = s0 < n and mEnd[s0] >= 0 and mDir[s0] == (1 if up else -1)
                stop = mConf[s0] - 1 if okRev else n - 1
                at = n; r = k + 2; fin = False
                while r <= stop and not fin:
                    p = P[r]
                    if (p["hi"] > V) if up else (p["lo"] < V): at = r; fin = True
                    elif (p["lo"] < L) if up else (p["hi"] > L): cse = 1; at = r; fin = True
                    r += 1
                if not fin and okRev: cse = 1; at = mConf[s0]
            else:
                e3h = None; jj = k + 3
                while jj < n and e3h is None:
                    e = P[jj]
                    if contains(e2h, e2l, e["hi"], e["lo"]):
                        e2h = max(e2h, e["hi"]) if up else min(e2h, e["hi"]); e2l = max(e2l, e["lo"]) if up else min(e2l, e["lo"])
                    else:
                        e3h, e3l = e["hi"], e["lo"]
                    jj += 2
                if e3h is not None:
                    fracOk = (e2h == V and e2h > e3h and e2l > e3l) if up else (e2l == V and e2l < e3l and e2h < e3h)
                    if fracOk:
                        ok, brk = _reverse_scan(P, k, "up" if up else "down")
                        if ok:
                            cse = 2; at = reverseConfirmPen(P, k, up, jj - 2)
                        else:
                            at = brk if brk is not None else n
    return cse, at

def firstSegFill(P, frm, mEnd, mConf, mDir):
    n = len(P); s = n - 1
    while s >= frm:
        i = s
        while i + 2 < n and not _opening_overlaps(P, i): i += 1
        e = c = -1
        if i + 2 < n:
            up = isUp(P[i]); k = i + 2
            while k < n - 1 and e < 0:
                cse, at = caseAt(P, i, k, up, mEnd, mConf, mDir)
                if cse > 0: e = k; c = max(k + 1, at)
                else:
                    k += 2
                    if at >= 0:
                        while k < at: k += 2
            if e >= 0: mDir[s] = 1 if up else -1
        mEnd[s] = e; mConf[s] = c; s -= 1

def scan(P, i, born, segs, mEnd, mConf, mDir):
    n = len(P); stop = False
    while i + 2 < n and not stop:
        if not _opening_overlaps(P, i): i += 1; continue
        up = isUp(P[i]); k = i + 2
        while k < born: k += 2
        endPen = res = -1
        while k < n - 1 and endPen < 0:
            cse, at = caseAt(P, i, k, up, mEnd, mConf, mDir)
            if cse > 0: endPen = k; res = at if cse == 1 else 0
            else:
                k += 2
                if at >= 0:
                    while k < at: k += 2
        if endPen < 0: stop = True
        elif not segs and (P[endPen]['p1'] <= P[i]['p0'] if up else P[endPen]['p1'] >= P[i]['p0']): i += 1; born = 0   # 图头段方向（24dd）
        else: born = res; segs.append((i, endPen)); i = endPen + 1
    return i, born

def buildSegmentsPine(P):
    n = len(P); mEnd, mConf, mDir = [-1] * n, [-1] * n, [0] * n
    firstSegFill(P, 0, mEnd, mConf, mDir); segs = []; scan(P, 0, 0, segs, mEnd, mConf, mDir); return segs

def incrementalPine(P):
    segs, i, born = [], 0, 0
    for n in range(1, len(P) + 1):
        Q = P[:n]; mEnd, mConf, mDir = [-1] * n, [-1] * n, [0] * n
        firstSegFill(Q, i, mEnd, mConf, mDir)
        i, born = scan(Q, i, born, segs, mEnd, mConf, mDir)
    return segs

LIVE = sys.argv[1] if len(sys.argv) > 1 else None   # 可选：一份 /api/chart 载荷（线上永续），一起对账
sets = [(fn, load(os.path.join('data', fn)), tick_of(fn)) for fn in kline_files()] + \
       ([('live', [dict(t=b['t'], o=b['o'], h=b['h'], l=b['l'], c=b['c']) for b in json.load(open(LIVE))['bars']], tick_of('btcusdt_4h.json'))] if LIVE else []) + \
       [('aapl1h_headdir', [dict(t=b['t'], o=b['o'], h=b['h'], l=b['l'], c=b['c']) for b in json.load(open('tools/fixtures/aapl1h_headdir.json'))], tick_of('aaplusdt_1h.json'))]   # 图头段方向（24dd）只在这份上触发
bad = 0
for fn, bars, tk in sets:
    P = analyze(bars, tick=tk)["pens"]
    eng = [(s["PI0"], s["PI1"]) for s in build_segments(P) if not s.get("live")]
    full = buildSegmentsPine(P); inc = incrementalPine(P)
    ok = eng == full == inc; bad += not ok
    print("%s %s 段 %d  整段 %s  逐根 %s" % ("✓" if ok else "✗", fn, len(eng), full == eng, inc == eng))
print("全部一致" if not bad else "%d 份不一致" % bad)
sys.exit(1 if bad else 0)
