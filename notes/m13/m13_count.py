# M13：二、三类之间的中枢震荡买卖点有几个（只量不改）。口径：确认的二买（二卖）之后，同向单位（q+2, q+4…）的终点，
# 直到 ① 出现三买（三卖，signals 里 bar 更晚的第一颗）② 有单位破了一买低点（一卖高点）③ 已完成单位用完，为止；其间每个终点算一颗。
import sys,json,gzip,importlib
sys.path[:0]=['.','tools']
S=importlib.import_module('core.signals')
from core.analyze import analyze, analyze_file
from config import tick_of
DATA=["aaplusdt_1h.json","aaplusdt_2h.json","aaplusdt_30m.json","aaplusdt_4h.json","btc_4h.json","zec15.json","zec30_cut.json","zec_1h.json","zec_2h.json","zec_4h.json"]
syms={"ZECUSDT":"zec","BTCUSDT":"btc","AAPLUSDT":"aaplusdt"}
charts=[(f,analyze_file(f)) for f in DATA]
snap=json.loads(gzip.open(sys.argv[1]).read())
charts+=[(k,analyze(snap[k]["bars"],tick=tick_of(syms[k.split()[0]]+"_.json"))) for k in sorted(snap)]
for level in ("seg","pen"):
    n2=n_osc=0; rows=[]
    for name,r in charts:
        sig=S.signals(r,level=level); AU,U,Z=S._units(r,level)
        ndone=len(U) if level=="seg" else len(AU)-1
        for s in sig:
            if s["kind"] not in ("二买","二卖") or not s["confirmed"]: continue
            n2+=1; buy=s["kind"]=="二买"; q=s["unit"]; ext=AU[q-2]["p1"]
            third=[t["bar"] for t in sig if t["kind"]==("三买" if buy else "三卖") and t["bar"]>s["bar"]]
            stop_bar=min(third) if third else None; why="数据末"
            j=q+2; cnt=0
            while j<ndone:
                u=AU[j]
                if stop_bar is not None and u["i1"]>=stop_bar: why="到三类点"; break
                if (u["p1"]<ext) if buy else (u["p1"]>ext): why="破一类极值"; break
                cnt+=1; j+=2
            n_osc+=cnt
            if cnt: rows.append((name,s["kind"],round(s["price"],4),cnt,why))
    print(level,"确认的二类",n2,"→ 二三之间中枢震荡点",n_osc, rows[:12])
