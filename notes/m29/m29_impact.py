# M29 影响面：25 份（data/ 10 份 K 线 + 线上 10-07 冻结快照 15 张），段级二买/二卖分三类：
#  ① 不创新低（weak=False）——照 L57 照样是二类，不变；
#  ② 创新低 + 盘整背驰（代理）——照 L57 照样是二类，只是去掉『弱』；
#  ③ 创新低 + 无盘整背驰（代理）——照 L57 不是二类，会被拿掉。
# 盘整背驰的代理：s2（二买那段）对 C（一买那段）用 signals 的 _diverges（同一把 MACD 面积尺）。
# 不是 D2-5 的正式判法（D2-5 还没做），只给上下界之间的一个点估计。用法：在仓根跑 python3 <本文件> <快照.gz>
import sys,os,json,gzip
ROOT=os.getcwd();sys.path[:0]=[ROOT,ROOT+'/tools']
import importlib; S=importlib.import_module("core.signals")
from core.analyze import analyze, analyze_file
from config import tick_of
DATA=["aaplusdt_1h.json","aaplusdt_2h.json","aaplusdt_30m.json","aaplusdt_4h.json","btc_4h.json",
      "zec15.json","zec30_cut.json","zec_1h.json","zec_2h.json","zec_4h.json"]
syms={"ZECUSDT":"zec","BTCUSDT":"btc","AAPLUSDT":"aaplusdt"}
charts=[(f,analyze_file(f)) for f in DATA]
snap=json.loads(gzip.open(sys.argv[1]).read())
charts+=[(k,analyze(snap[k]["bars"],tick=tick_of(syms[k.split()[0]]+"_.json"))) for k in sorted(snap)]
tot={"①":0,"②":0,"③":0}; nf=0; rows=[]
for name,r in charts:
    sig=S.signals(r,level="seg")
    AU,U,Z=S._units(r,"seg")
    hist=S.series_for(r["bars"],"macd",12,26,9)
    for s in sig:
        if s["kind"] in ("一买","一卖") and s["confirmed"]: nf+=1
        if s["kind"] not in ("二买","二卖"): continue
        down=s["kind"]=="二买"; q=s["unit"]; C=AU[q-2]; s2=AU[q]
        if not s["weak"]: cat="①"
        else: cat="②" if S._diverges(C,s2,down,hist,"macd",1.0) else "③"
        tot[cat]+=1
        rows.append((name,s["kind"],r["bars"][s["bar"]].get("t",s["bar"]),round(s["price"],4),round(C["p1"],4),cat,s["confirmed"]))
for x in rows: print(*x,sep="\t")
print("合计",len(charts),"份；确认的一买/一卖",nf,"；二类",sum(tot.values()),tot)
