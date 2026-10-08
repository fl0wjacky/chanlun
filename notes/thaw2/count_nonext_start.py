"""线段.md:313 计数（Atlas 10-08）：起点不是段内极值的线段有几个、_start_check 判成什么。
用法：python3 notes/thaw2/count_nonext_start.py [线上快照.json.gz]
口径：analyze() 默认参数的 r['segs']；去掉 live 段；极值取 seg 的 hi/lo（跟用笔的 hi/lo 算结果一样）；
图头段跟 check_segments 一样设 cutoff。data/ 只收「K 线数组」那几份（跟 trend_check.kline_files 同口径）。"""
import sys, os, json, gzip
sys.path[:0] = [".", "tools"]
from collections import Counter
from core.analyze import analyze
from core import segment as S
from config import tick_of

def count(r):
    c = Counter()
    for k, s in enumerate(r["segs"]):
        if s.get("live"):
            continue
        ext = s["lo"] if s["dir"] == "up" else s["hi"]
        if s["p0"] == ext:
            continue
        cut = None
        if k == 0:
            f0 = S._first_seg(r["pens"], s["PI0"])
            cut = f0["confirm"] if f0 is not None and f0["PI1"] == s["PI1"] else None
        c[S._start_check(s, r["pens"], cutoff=cut)] += 1
    return c

tot = Counter()
for f in sorted(os.listdir("data")):
    try:
        raw = json.load(open(os.path.join("data", f)))
    except ValueError:
        continue
    raw = raw["bars"] if isinstance(raw, dict) and "bars" in raw else raw
    if not (isinstance(raw, list) and raw and isinstance(raw[0], dict) and {"t", "o", "h", "l", "c"} <= set(raw[0])):
        continue
    c = count(analyze([dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"]) for b in raw], tick=tick_of(f)))
    tot += c
    print(f, dict(c))
print("data/ 合计", dict(tot), sum(tot.values()))
if len(sys.argv) > 1:
    snap = json.loads(gzip.open(sys.argv[1]).read())
    syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
    t2 = Counter()
    for key in sorted(snap):
        s, tf = key.split()
        t2 += count(analyze(snap[key]["bars"], tick=tick_of(syms[s] + "_.json")))
    print("线上快照 合计", dict(t2), sum(t2.values()))
