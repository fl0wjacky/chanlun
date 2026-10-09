"""D2-7 撤哪一头：几个选项各跑一遍，跟现行比刀变了几把。只在本脚本里换 find_bounds（不改仓里文件）。
选项（D2-7 触发时：上一刀 prev 到新刀之间没有中枢）：
  O0 现行：撤 prev，新刀不切，这一对拉黑。
  O1 撤被越过的那头：新刀跟 prev 前面那把 pp 同向且更极端（pp 已被越过）⇒ prev、pp 都撤，新刀顶替 pp（再核一遍新刀跟 pp 之前那把之间有中枢，没有就退回 O0）；不满足 ⇒ 同 O0。
  O2 两头都撤、重新找：撤 prev，也撤 pp（不管有没有被越过），want 回到 pp 的方向，同一步重新找。
J18_DATA=<目录> [J18_FILES=..] OPTS=O1,O2 python3 d27opts.py   （在仓根目录跑；60c72a4、40935c0 上都跑过）"""
import os, sys, json, inspect, textwrap, datetime as d
sys.path[:0] = ['.', 'tools']
import core.trend as T
from core.analyze import analyze
from config import tick_of
DATA = os.environ.get("J18_DATA", "data")
FILES = os.environ["J18_FILES"].split(",") if os.environ.get("J18_FILES") else sorted(f for f in os.listdir(DATA) if f.endswith(".json") and f not in ("annot_pens.json", "mag_klines.json", "m15_sub.json"))
OPTS = os.environ.get("OPTS", "O1,O2").split(",")
ts = lambda t: d.datetime.utcfromtimestamp(t / 1000).strftime('%Y-%m-%d %H:%M')
SRC = textwrap.dedent(inspect.getsource(T.find_bounds))
OLD = """                if not [q for q in zz if q["PI0"] >= lo and q["PI1"] <= j]:
                    ks.pop()
                    prev = bounds.pop()"""
assert OLD in SRC
NEW = """                if not [q for q in zz if q["PI0"] >= lo and q["PI1"] <= j]:
                    if _OPT != "O0" and len(bounds) >= 2:
                        pp = bounds[-2]
                        more = (done[j]["p1"] > pp["price"]) if typ == "H" else (done[j]["p1"] < pp["price"])
                        if pp["kind"] == typ and (more or _OPT == "O2"):
                            lo2 = ks[-3] if len(ks) >= 3 else 0
                            ok2 = True
                            if _OPT == "O1" and len(ks) >= 3:
                                zz2 = _sl_centers_with_cuts(done[:t + 1], ks[:-2] + [j + 1])
                                ok2 = bool([q for q in zz2 if q["PI0"] >= lo2 and q["PI1"] <= j])
                            if ok2:
                                for _ in range(2):
                                    ks.pop(); gone = bounds.pop()
                                    retracted.append(dict(bar=gone["bar"], kind=gone["kind"], price=gone["price"], pullback_end_bar=gone["pullback_end_bar"],
                                                          retracted_bar=done[t]["i1"], blocked_bar=done[j]["i1"], blocked_kind=typ, opt=_OPT))
                                if _OPT == "O2":
                                    want = typ
                                    break
                                ks.append(j + 1)
                                bounds.append(dict(rule="D2-2", line_seg=j, bar=done[j]["i1"], kind=typ, price=done[j]["p1"], pullback_line_seg=t,
                                                   pullback_end_bar=done[t]["i1"], ZD=z["ZD"], ZG=z["ZG"], ref_X0=z["X0"]))
                                want = None if not alternate else ("L" if typ == "H" else "H")
                                break
                    ks.pop()
                    prev = bounds.pop()"""
g = dict(vars(T)); g["_OPT"] = "O0"
exec(compile(SRC.replace(OLD, NEW), "fb_variant", "exec"), g)
VAR = g["find_bounds"]; ORIG = T.find_bounds

def run(bars, fn, opt):
    if opt == "O0":
        T.find_bounds = ORIG
    else:
        g["_OPT"] = opt; T.find_bounds = VAR
    try:
        v = T.trend_v3(analyze(bars, tick=tick_of(fn)))
    finally:
        T.find_bounds = ORIG
    return v

def d2t1(v):
    n = 0
    for b in v["bounds"]:
        if b["rule"] == "D2-2" and b.get("state") == "confirmed":
            s = next((s for s in v["segments"] if s["i0"] == b["bar"]), None)
            n += bool(s and ((b["kind"] == "H" and s["type"] == "上涨") or (b["kind"] == "L" and s["type"] == "下跌")))
    return n

tot = {o: [0, 0, 0] for o in OPTS}
for fn in FILES:
    raw = json.load(open(os.path.join(DATA, fn))); raw = raw["bars"] if isinstance(raw, dict) else raw
    bars = [dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"]) for b in raw]
    v0 = run(bars, fn, "O0")
    k0 = {(b["bar"], b["kind"], b["rule"]) for b in v0["bounds"]}
    line = "%s：现行 刀 %d、D2-T1 %d" % (fn, len(k0), d2t1(v0))
    for o in OPTS:
        v = run(bars, fn, o)
        k = {(b["bar"], b["kind"], b["rule"]) for b in v["bounds"]}
        add, rem = k - k0, k0 - k
        tot[o][0] += len(add); tot[o][1] += len(rem); tot[o][2] += d2t1(v)
        line += " ｜ %s 加 %d 去 %d、D2-T1 %d" % (o, len(add), len(rem), d2t1(v))
        for x in sorted(add | rem):
            print("    %s %s %s %s %.2f %s" % (o, "+" if x in add else "−", ts(bars[x[0]]["t"]), x[1], next(b["price"] for b in (v["bounds"] if x in add else v0["bounds"]) if (b["bar"], b["kind"], b["rule"]) == x), x[2]), flush=True)
    print(line, flush=True)
print("合计：" + " ｜ ".join("%s 加 %d 去 %d、D2-T1 %d" % (o, *tot[o]) for o in OPTS))
