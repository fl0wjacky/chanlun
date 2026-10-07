"""用冻结快照（notes/snap/live15-1007.json.gz）出 D3+D6-4 前后表：旧＝快照里线上引擎那份，新＝本树引擎在同一份 K 线上。"""
import sys, json, os, gzip
ROOT = os.getcwd(); sys.path[:0] = [ROOT, ROOT + "/tools"]
from core.analyze import analyze
from core.trend import trend_v3
from config import tick_of
snap = json.loads(gzip.open(sys.argv[1]).read())
syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
ty = lambda x: x["type"] + ("·升" if x["upgraded"] else "")
tot = dict(seg=0, box_add=0, box_del=0, unit_add=0, unit_del=0, trend_lost=0, bounds_changed=0)
for key in sorted(snap):
    s, tf = key.split(); d = snap[key]
    v = trend_v3(analyze(d["bars"], tick=tick_of(syms[s] + "_.json")), reading="A")
    o = d["old_trend"]; oc = d["old_centers"]
    tot["bounds_changed"] += [b["bar"] for b in o["bounds"]] != [b["bar"] for b in v["bounds"]]
    rows = []
    for g, (so, sn) in enumerate(zip(o["segments"], v["segments"])):
        bo = sorted((round(z["ZD"], 2), round(z["ZG"], 2)) for z in oc if z["seg"] == g)
        bn = sorted((round(z["ZD"], 2), round(z["ZG"], 2)) for z in v["seg_centers"] if z["seg"] == g)
        uo = sorted((round(u["DD"], 2), round(u["GG"], 2)) for u in o["units"] if u["seg"] == g)
        un = sorted((round(u["DD"], 2), round(u["GG"], 2)) for u in v["units"] if u["seg"] == g)
        if ty(so) != ty(sn) or bo != bn or uo != un:
            rows.append("  段%d %s→%s 框-%s 框+%s 合成-%s 合成+%s" % (g, ty(so), ty(sn), [x for x in bo if x not in bn], [x for x in bn if x not in bo], [x for x in uo if x not in un], [x for x in un if x not in uo]))
            tot["seg"] += ty(so) != ty(sn); tot["box_del"] += len([x for x in bo if x not in bn]); tot["box_add"] += len([x for x in bn if x not in bo])
            tot["unit_del"] += len([x for x in uo if x not in un]); tot["unit_add"] += len([x for x in un if x not in uo])
            tot["trend_lost"] += so["type"] in ("上涨", "下跌") and sn["type"] not in ("上涨", "下跌")
    print("%s %s（数据 %s）变了 %d 段" % (s, tf, d["fetched_at"], len(rows)))
    for r_ in rows: print(r_)
print("合计", tot)
