"""25 张：analyze 的 pens/segs + trend_v3（默认开关）整体 sha256 前 16，用来证明默认输出不变。"""
import sys, os, json, gzip, hashlib
sys.path[:0] = [os.getcwd(), "tools"]
from core.analyze import analyze
import core.trend as T
from config import tick_of
snap = json.loads(gzip.open(os.environ["LIVE15"]).read()); syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
it = [(snap[k]["bars"], syms[k.split()[0]] + "_.json") for k in sorted(snap)] + [(json.load(open("data/%s.json" % f)), f + ".json") for f in ["aaplusdt_1h", "aaplusdt_2h", "aaplusdt_30m", "aaplusdt_4h", "btc_4h", "zec15", "zec30_cut", "zec_1h", "zec_2h", "zec_4h"]]
h = hashlib.sha256()
for b, tk in it:
    r = analyze(b, tick=tick_of(tk)); v = T.trend_v3(r)
    h.update(json.dumps([r["pens"], r["segs"], v["bounds"], v["segments"]], sort_keys=True, default=str).encode())
print(h.hexdigest()[:16])
