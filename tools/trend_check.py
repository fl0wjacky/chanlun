#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""走势分界 v3（core/trend.py，docs/spec/走势分段.md v3）的检查＋探针。rc=0 才算过。

    python3 tools/trend_check.py              # 基线 + 不变量 + 不看未来
    python3 tools/trend_check.py --self-test  # spec §四 的探针（拿掉一条规则，结果必须变）

  ① 基线（spec §三）：zec15 五个分界（bar、高低、确立那一根）＋ 531.91 撤回一次；zec30 五个；btc_4h／zec_1h／aaplusdt_30m 各一个；
  ② 不变量（data/ 下每份 K 线）：一高一低交替（D2-3）；刀落在同向线段的终点上（D2-1）；确立晚于刀（L88:19-21）；
     相邻两刀之间至少一个中枢（D2-7）；没有框跨过分界（D4-1）；走势首尾相接盖满整张图；每个框的 seg 指对了段；
  ③ 367.77（zec15 bar 11314）不是分界、落在框里（D4-4）；
  ④ 不看未来：每个分界从『最早能确立』那一根截断起就在，之后再截都不变（实时确立比回抽段终点晚，印出来）。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from core.analyze import analyze                              # noqa: E402
import core.trend as T                                        # noqa: E402
import re                                                     # noqa: E402

# 线上用哪种 D3 读法以 web/server.py 的 TREND_READING 为准（不 import server，免得起它那一摊）；这里的格子都按它跑
_m = re.search(r'^TREND_READING = "([AB])"', open(os.path.join(ROOT, "web", "server.py"), encoding="utf-8").read(), re.M)
READING = _m.group(1) if _m else None

# spec §三（agent/atlas/spec-v3 22e0570 起）：(bar, 高低, 确立那一根)
BASE = {
    # D2-0（card-acbe5855，10-06）整层用标准化后的线段：zec15 多出 3699 H（394.0）、4575 L（299.56）—— 段 23 的真高点在下一段段内，
    #   以前候选是端点那个次高点、P3 又按区间判它「被过了」，卡到 7558 才确立；其余 5 刀不变。
    "zec15.json": [(490, "L", None), (3699, "H", None), (4575, "L", None), (7558, "H", None), (9043, "L", None),
                   (12906, "H", None), (14215, "L", None)],
    "zec30_cut.json": [(134, "L", None), (3476, "H", None), (4219, "L", None), (6150, "H", None), (6805, "L", None)],
}
BASE_PRICE = {"btc_4h.json": [("H", 97932.1)], "zec_1h.json": [("L", 205.07)], "aaplusdt_30m.json": [("L", 300.50)],
              # D2-0 先后（Nova 06:44Z）：中间接点先挪到不动、图头最后挪 ⇒ zec_2h 第一刀 191.35；图头先挪会卡住接点 1，变成 205.07
              "zec_2h.json": [("L", 191.35)]}
def load(path):
    raw = json.load(open(path))
    raw = raw["bars"] if isinstance(raw, dict) else raw
    return [dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"]) for b in raw]


def kline_files():
    """data/ 下所有「K 线数组」样本（每条有 t/o/h/l/c）；别的 JSON（标注、子图样本）跳过。"""
    out = []
    for fn in sorted(os.listdir(os.path.join(ROOT, "data"))):
        if not fn.endswith(".json") or fn.endswith("_tmp.json"):
            continue
        try:
            raw = json.load(open(os.path.join(ROOT, "data", fn)))
        except ValueError:
            continue
        if isinstance(raw, list) and raw and isinstance(raw[0], dict) and {"t", "o", "h", "l", "c"} <= set(raw[0]):
            out.append(fn)
    return out


# spec D3（小栋 10-05 定 B）：升级中枢留在本级别一起数。下面是**冻结夹具 data/zec15.json** 的段类型（下标 0 起），
# 不是线上：线上窗口在滚，段数和中枢合法都会变（10-06 线上第 1 段 4 个中枢合成一个 n=4 ⇒ 本级别只剩一个 ⇒ 盘整，也对）。
# 夹具里第 1 段（bar 490–7558）4 个中枢只合了 2 个 ⇒ 本级别 3 个 ⇒「上涨」；第 5 段同理。A 读法下两段都是「升级·盘整」。
# D2-0（10-06）以后 zec15 是 8 段：多切出 3699／4575 两刀，原先第 1 段（490–7558，读法 B「上涨」）被切成三段，各自中枢不够两个以上
#   不重叠 ⇒ 都是盘整；原先第 5 段（14215 起）照旧「上涨」。
TYPES = {"zec15.json": ["盘整", "盘整", "盘整", "盘整", "盘整", "盘整", "下跌", "上涨"]}
# ★ 10-07 D3 改 A（card-0374e640-127，一A二A）：读法 A、合成框按高一级 3+3+3 重算（D3-2 推广口径 (iii)）、
#   最后一个中枢还在走不合成（D3-4）。zec15 八段（「·升」＝含合成出来的高一级中枢、整段升一级读）：
TYPES = {"zec15.json": ["盘整", "盘整·升", "盘整", "上涨", "盘整", "盘整·升", "下跌", "盘整·升"]}
# ★ D6-4（10-07 09:16Z，先限方向判段型）：第 3 段从「盘整」变「上涨」（限方向找出两个依次上移的中枢）。
FIX_D2STD = os.path.join(ROOT, "tools", "fixtures", "zec1m_d2std.json")
# card-eecdfd08：ZEC 永续 1m 一段（04-08 前后），旧程序在这里把同一对 (308.24 L, 394.0 H) 确立又撤回 13 次
FIX_RETRACT = os.path.join(ROOT, "tools", "fixtures", "zec1m_retract_loop.json")   # Atlas 10-06：ZEC 永续 1m，04-29 317.74 真低点在向上线段段内
RETRACT = {"zec15.json": [(15295, "H")], "zec30_cut.json": []}
_R = {}


def run(fn, bars=None, **kw):
    from config import tick_of
    key = (fn, len(bars) if bars else None)
    if key not in _R:
        _R[key] = analyze(bars or load(os.path.join(ROOT, "data", fn)), tick=tick_of(fn))
    kw.setdefault("reading", READING)
    return _R[key], T.trend_v3(_R[key], **kw)


def baseline():
    bad = []
    for fn, want in BASE.items():
        _, v = run(fn)
        got = [(b["bar"], b["kind"]) for b in v["bounds"]]
        if got != [(b, k) for b, k, _ in want]:
            bad.append("%s 分界 %s ≠ %s" % (fn, got, [(b, k) for b, k, _ in want]))
        rg = [(x["bar"], x["kind"]) for x in v["retracted"]]
        if rg != RETRACT[fn]:
            bad.append("%s 撤回 %s ≠ %s" % (fn, rg, RETRACT[fn]))
    for fn, want in BASE_PRICE.items():
        _, v = run(fn)
        got = [(b["kind"], round(b["price"], 2)) for b in v["bounds"]]
        if got != want:
            bad.append("%s 分界 %s ≠ %s" % (fn, got, want))
    return bad


def invariants(fn):
    r, v = run(fn)
    bad = []
    done = T._done(r)                                # 走势层看的是标准化后的线段（D2-0）
    # ★ 独立核 D2-0（不调引擎那份 _standardize）：按定义查 —— 首尾相接、方向交替、每段端点就是自己区间里的最高／最低
    bars = r["bars"]
    for a_, b_ in zip(done, done[1:]):
        if a_["i1"] != b_["i0"] or a_["dir"] == b_["dir"] or a_["i0"] >= a_["i1"]:
            bad.append("标准化后不首尾相接或不交替 %d/%d" % (a_["i1"], b_["i0"]))
    for k, s_ in enumerate(done):
        hi = max(bars[i]["h"] for i in range(s_["i0"], s_["i1"] + 1))
        lo = min(bars[i]["l"] for i in range(s_["i0"], s_["i1"] + 1))
        up_ = s_["dir"] == "up"
        if (s_["p0"], s_["p1"]) != ((lo, hi) if up_ else (hi, lo)):
            bad.append("%s 标准化后段 %d 端点不是段内极值" % (fn, k))
    ends = {s["i1"]: s for s in done}
    bs = v["bounds"]
    for a, b in zip(bs, bs[1:]):
        if a["kind"] == b["kind"]:
            bad.append("不交替 %d/%d" % (a["bar"], b["bar"]))
    for b in bs:
        s = ends.get(b["bar"])
        if s is None or (s["p1"] > s["p0"]) != (b["kind"] == "H"):
            bad.append("刀 %d 不在同向线段终点" % b["bar"])
        if b["pullback_end_bar"] <= b["bar"]:
            bad.append("刀 %d 回抽段终点不晚于刀" % b["bar"])
    for a, b in zip(bs, bs[1:]):                 # D2-7：两刀之间至少一个中枢
        if not [z for z in v["seg_centers"] if a["bar"] <= z["X0"] and z["X1"] <= b["bar"]]:
            bad.append("%d→%d 之间没有中枢" % (a["bar"], b["bar"]))
    for b in bs:                                 # D4-1：框不跨分界
        for z in v["seg_centers"]:
            if z["X0"] < b["bar"] < z["X1"]:
                bad.append("框 %d–%d 跨过分界 %d" % (z["X0"], z["X1"], b["bar"]))
    seg = v["segments"]
    for z in v["seg_centers"]:                    # 每个框的 seg 指的那段走势真的装得下它（前端靠它编字母）
        g = z.get("seg")
        if g is None or not (0 <= g < len(seg)) or not (seg[g]["i0"] <= z["X0"] and z["X1"] <= seg[g]["i1"]):
            bad.append("框 %d–%d 的 seg=%r 不对" % (z["X0"], z["X1"], g))
    for b in bs:                                  # 对外 seg 只指走势段号：bounds 不许带同名键（用 line_seg）
        if "seg" in b:
            bad.append("bounds 带了 seg 键（该叫 line_seg）")
        elif not any(s["i0"] == b["bar"] for s in seg[1:]):
            bad.append("分界 %d 不是某一段走势的起点" % b["bar"])
    # ★ L24:84-85（card-40f4ce13）：上涨走势里的框只认下上下（首段向下），下跌里只认上下上。独立按定义查：
    #   看框首段 done[PI0] 的 dir，不看引擎里那两遍怎么走。豁免：图头那段不查；前一段是反向走势 ⇒ 段内第一个框不查（L45:122-124）。
    #   只管本级别的上涨／下跌：升级·上涨／下跌（含合成框）不查，豁免里的「前一段反向」也只认本级别（Nova 10-07 08:00Z）。
    for g, sg in enumerate(seg):
        if g == 0 or sg["type"] not in ("上涨", "下跌") or sg["upgraded"]:
            continue
        want = "down" if sg["type"] == "上涨" else "up"
        zz = sorted((z for z in v["seg_centers"] if z.get("seg") == g), key=lambda z: z["X0"])
        if zz and not seg[g - 1]["upgraded"] and seg[g - 1]["type"] == ("下跌" if sg["type"] == "上涨" else "上涨"):
            zz = zz[1:]
        for z in zz:
            if done[z["PI0"]]["dir"] != want:
                bad.append("%s段 %d 里的框 %d–%d 首段向%s（L24:85 要向%s）" % (
                    sg["type"], g, z["X0"], z["X1"], "上" if want == "down" else "下", "下" if want == "down" else "上"))
    # ★ D3-2／D3-4（card-0374e640-127）独立按定义查每个合成框：不调 _regroup，从框盖住的线段直接算 ——
    #   线段数 ≥9 且 9＋3k；头三组（各 3 条线段，区间取最低～最高）的 [max 低, min 高] 就是 ZD／ZG 且有重叠；
    #   之后每组都跟 [ZD, ZG] 有重叠；DD／GG＝各组最低／最高。它所在那条扩展链的最后一个中枢不许还在走。
    for u in v["units"]:
        cov = [k for k, x in enumerate(done) if x["i0"] >= u["X0"] and x["i1"] <= u["X1"]]
        if len(cov) < 9 or (len(cov) - 9) % 3 or cov != list(range(cov[0], cov[0] + len(cov))):
            bad.append("合成框 %d–%d 盖住 %d 条线段（要 9＋3k）" % (u["X0"], u["X1"], len(cov)))
            continue
        gs = [(min(done[q]["lo"] for q in cov[m:m + 3]), max(done[q]["hi"] for q in cov[m:m + 3])) for m in range(0, len(cov), 3)]
        zd, zg = max(x[0] for x in gs[:3]), min(x[1] for x in gs[:3])
        if zd > zg or u.get("ZD") != zd or u.get("ZG") != zg or any(x[0] > zg or x[1] < zd for x in gs[3:]) \
                or (u["DD"], u["GG"]) != (min(x[0] for x in gs), max(x[1] for x in gs)):
            bad.append("合成框 %d–%d 区间不是按 3+3+3 算的（%s～%s）" % (u["X0"], u["X1"], u["DD"], u["GG"]))
        zz = sorted((z for z in v["seg_centers"] if z["seg"] == u["seg"]), key=lambda z: z["X0"])
        k0 = next((k for k, z in enumerate(zz) if z["X0"] == u["X0"]), None)
        if k0 is not None:
            k1 = k0
            while k1 + 1 < len(zz) and zz[k1 + 1]["kind"] == "扩展":
                k1 += 1
            if zz[k1]["live"]:
                bad.append("合成框 %d–%d 所在扩展链的最后一个中枢还在走（D3-4 不该合成）" % (u["X0"], u["X1"]))
    if sum(s["n_centers_level"] for s in seg) != len(v["seg_centers"]):
        bad.append("各段 n_centers_level 之和 ≠ seg_centers 个数")
    if seg[0]["i0"] != 0 or seg[-1]["i1"] != len(r["bars"]) - 1 or any(
            a["i1"] != b["i0"] for a, b in zip(seg, seg[1:])):
        bad.append("走势没有首尾相接盖满")
    return bad


def first_seen(fn, k, want, bars, lo):
    """第 k 个分界最早在哪一根截断时就有了（二分；之后一直在，见 no_future 的复查）。"""
    hi = len(bars) - 1

    def ok(t):
        _, v = run(fn, bars[:t + 1])
        return [(x["bar"], x["kind"]) for x in v["bounds"]][:k + 1] == want
    if not ok(hi):
        return None
    while lo < hi:
        mid = (lo + hi) // 2
        if ok(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


def no_future(fn="zec15.json"):
    """不看未来：每个分界在它『最早能确立』的那一根截断重跑就在，此后再截（＋1 天、＋1 周、＋1 月）都还在、不变。
    ★ 最早能确立 ≠ spec 表里的『确立』列（那是回抽段的终点）：线段要等后面的 K 线才算走完，所以实时会晚一截，这里一并印出来。"""
    bars = load(os.path.join(ROOT, "data", fn))
    _, full = run(fn)
    bad, lags = [], []
    for k, b in enumerate(full["bounds"]):
        want = [(x["bar"], x["kind"]) for x in full["bounds"][:k + 1]]
        seen = first_seen(fn, k, want, bars, b["pullback_end_bar"])
        if seen is None:
            bad.append("%d 截到图尾都没有" % b["bar"])
            continue
        lags.append(seen - b["pullback_end_bar"])
        for extra in (96, 672, 2880):            # 15m：1 天、1 周、1 月
            t = seen + extra
            if t >= len(bars):
                break
            _, v = run(fn, bars[:t + 1])
            if [(x["bar"], x["kind"]) for x in v["bounds"]][:k + 1] != want:
                bad.append("%d 在 %d 出现、%d 又变了" % (b["bar"], seen, t))
    print("    实时比回抽段终点晚：%s 根" % lags)
    return bad


def main():
    bad = []

    def cell(name, items):
        print("%s %s %s" % ("✓" if not items else "✗", name, items[:3] if items else ""))
        bad.extend(items)

    cell("① 基线（spec §三）", baseline())
    files = kline_files()
    inv = []
    for fn in files:
        inv += ["%s %s" % (fn, x) for x in invariants(fn)]
    cell("② 不变量（%d 份样本）" % len(files), inv)
    r, v = run("zec15.json")
    in_box = [z for z in v["seg_centers"] if z["X0"] < 11314 < z["X1"]]
    cell("③ 367.77（bar 11314）不是分界、落在框里",
         [] if 11314 not in [b["bar"] for b in v["bounds"]] and in_box else ["11314 是分界或不在框里"])
    tys = [s["type"] + ("·升" if s["upgraded"] else "") for s in v["segments"]]
    cell("⑤ 段类型按线上读法 A（spec D3-3，server.TREND_READING）", [] if v["reading"] == "A" and tys == TYPES["zec15.json"]
         else ["读法 %s 段类型 %s" % (v["reading"], tys)])
    cell("⑥ 每个分界是两邻分界之间的极值（直接从 K 线算，不经线段）", extreme_between())
    cell("⑦ D2-0 夹具 zec1m_d2std：04-29 那个 317.74 L 要确立（候选卡死就没有）", d2std_fixture())
    cell("⑧ 同一对 (b, b′) 被 D2-7 去掉最多一次（编者口径；含 zec1m_retract_loop 夹具）", retract_once())
    cell("④ 不看未来（zec15：最早能确立那一根起，之后一直在、不变）", no_future())
    print("全部通过" if not bad else "%d 处不过" % len(bad))
    return 1 if bad else 0


def extreme_between():
    """H 是它前后两个分界之间的最高价、L 是最低价（D2-1 候选＝到当时为止的极值，D2-2 价格没再过它）—— 直接从 K 线算，不经线段，
    所以能逮住「真极值在段内、候选卡在端点次高点」（D2-0 补的就是这个；关掉标准化 ⇒ zec_2h 367.77 那刀报出来）。第一刀不查。"""
    bad = []
    for fn in kline_files():
        r, v = run(fn)
        bars, bs = r["bars"], v["bounds"]
        for k, b in enumerate(bs):
            if k == 0:
                continue                                 # 图头那一刀两头都开（D2-1），更极端的点若前面没中枢就永远确立不了（D2-2 第 1 步）⇒ 不适用
            a = bs[k - 1]["bar"]
            z = bs[k + 1]["bar"] if k + 1 < len(bs) else len(bars) - 1
            seg = bars[a:z + 1]
            ext = max(x["h"] for x in seg) if b["kind"] == "H" else min(x["l"] for x in seg)
            if ext != b["price"]:
                bad.append("%s 刀 %d %s %.2f 不是两邻分界之间的极值 %.2f" % (fn, b["bar"], b["kind"], b["price"], ext))
    return bad


def _fixture(path=None, **kw):
    from config import tick_of
    bars = [dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"]) for b in json.load(open(path or FIX_D2STD))]
    return T.trend_v3(analyze(bars, tick=tick_of("zecusdt_1m.json")), reading=READING, **kw)


def d2std_fixture():
    v = _fixture()
    return [] if ("L", 317.74) in [(b["kind"], round(b["price"], 2)) for b in v["bounds"]] else \
        ["没有 317.74 L：%s" % [(b["kind"], round(b["price"], 2)) for b in v["bounds"]]]


def retract_once():
    """D2-7 编者口径（card-eecdfd08）：同一对 (b, b′) 最多撤回一次 —— 那一组里有没有中枢只看 done[b..b′]，结论不会变。"""
    import collections
    bad = []
    for name, v in [(fn, run(fn)[1]) for fn in kline_files()] + [("zec1m_retract_loop", _fixture(FIX_RETRACT))]:
        c = collections.Counter((x["bar"], x["blocked_bar"]) for x in v["retracted"])
        bad += ["%s 同一对 %s 撤回 %d 次" % (name, k, n) for k, n in c.items() if n > 1]
    return bad


def self_test():
    """spec §四：P1 不重算 ⇒ zec15 3 个；P2 不交替 ⇒ 撤回 20；P5 不查空段 ⇒ 7 个。各自必须变。"""
    _, base = run("zec15.json")
    arms = [("P1 拿掉 D2-4（不重算中枢）", dict(regroup=False), lambda v: len(v["bounds"]) != len(base["bounds"])),
            ("P2 拿掉 D2-3（不交替）", dict(alternate=False), lambda v: len(v["retracted"]) != len(base["retracted"])),
            ("P5 拿掉 D2-7（空段照切）", dict(check_empty=False), lambda v: len(v["bounds"]) != len(base["bounds"])),
]
    miss = 0
    # P3（「H 之后价格不再过 H」，按段内 hi／lo）。card-753bd03a（L78 待定改判）以后 zec_1h 第 8 段拆开了，原来那颗牙
    # （zec_1h 不交替 1 刀 1 撤 ↔ 0 刀 3 撤）没了；现在默认规则下 zec15 就咬得到：留着 5 刀，拿掉 7 刀。
    # P3 在标准化以后是推论（看区间＝看端点，spec D2-0），拿掉它默认规则下不会变 —— 所以这颗牙放在**不标准化**那条路上量，
    #   守的是「P3 这一条代码本身还在干活」。
    _, a3 = run("zec15.json", standardize=False)
    _, b3 = run("zec15.json", standardize=False, no_exceed=False)
    ok = len(b3["bounds"]) != len(a3["bounds"])
    print("%s P3 拿掉「H 之后不再过 H」（zec15、不标准化）⇒ 分界 %d、撤回 %d（留着 %d、%d）" % (
        "✓" if ok else "✗", len(b3["bounds"]), len(b3["retracted"]), len(a3["bounds"]), len(a3["retracted"])))
    miss += not ok
    # D2-0 的两颗牙：拿掉标准化 ⇒ 夹具上 317.74 L 没了；zec15 分界数也变
    vf = _fixture(standardize=False)
    ok = ("L", 317.74) not in [(b["kind"], round(b["price"], 2)) for b in vf["bounds"]]
    print("%s D2-0 拿掉标准化（zec1m_d2std）⇒ 317.74 L %s" % ("✓" if ok else "✗", "没了" if ok else "还在"))
    miss += not ok
    real = T._done                                       # ⑥ 的牙：关掉标准化 ⇒ 「分界是两邻之间的极值」必须报出来
    T._done = lambda r, standardize=True: real(r, False)
    _R.clear()
    try:
        e6 = extreme_between()
    finally:
        T._done = real
        _R.clear()
    print("%s ⑥ 关掉标准化 ⇒ 报出 %d 处（例 %s）" % ("✓" if e6 else "✗", len(e6), e6[:1]))
    miss += not e6
    T._HEAD_FIRST = True                                 # D2-0 先后反过来（先挪图头）⇒ zec_2h 第一刀必须变
    _R.clear()
    try:
        _, hf = run("zec_2h.json")
    finally:
        T._HEAD_FIRST = False
        _R.clear()
    ok = [(b["kind"], round(b["price"], 2)) for b in hf["bounds"]][:1] != [("L", 191.35)]
    print("%s D2-0 先挪图头 ⇒ zec_2h 第一刀 %s（应为 191.35）" % ("✓" if ok else "✗", [(b["kind"], round(b["price"], 2)) for b in hf["bounds"]][:1]))
    miss += not ok
    T._BLOCK_RETRACTED = False                           # 编者口径拿掉 ⇒ ⑧ 必须在 retract_loop 夹具上报出来
    try:
        e8 = retract_once()
    finally:
        T._BLOCK_RETRACTED = True
    print("%s D2-7 编者口径拿掉 ⇒ 报出 %d 处（例 %s）" % ("✓" if e8 else "✗", len(e8), e8[:1]))
    miss += not e8
    T._MOVE_ENDS = False                                 # 图头起点／末段终点不挪 ⇒ 不变量里「段端点＝段内极值」必须报出来
    _R.clear()
    try:
        ends = [x for fn in kline_files() for x in invariants(fn) if "端点不是段内极值" in x]
    finally:
        T._MOVE_ENDS = True
        _R.clear()
    print("%s D2-0 图头／末段不挪 ⇒ 报出 %d 处（例 %s）" % ("✓" if ends else "✗", len(ends), ends[:1]))
    miss += not ends
    _, s0 = run("zec15.json", standardize=False)
    ok = len(s0["bounds"]) != len(base["bounds"])
    print("%s D2-0 拿掉标准化（zec15）⇒ 分界 %d（原样 %d）" % ("✓" if ok else "✗", len(s0["bounds"]), len(base["bounds"])))
    miss += not ok
    # D4-1 的反向验证（原 cut_check --self-test 挪来）：重算中枢时不按刀分组 ⇒ ② 必须报出跨分界的框
    real = T._centers_with_cuts
    T._centers_with_cuts = lambda done, ks: real(done, [])
    T._DIR_RULE = False                          # 方向规则那一遍是按组重找的，不关掉它探针就碰不到画出来的框
    _R.clear()
    try:
        cross = [x for x in invariants("zec15.json") if "跨过分界" in x]
    finally:
        T._centers_with_cuts = real
        T._DIR_RULE = True
        _R.clear()
    ok = bool(cross)
    print("%s D4 拿掉「按刀分组」⇒ ② 报出跨分界的框 %d 个（例 %s）" % ("✓" if ok else "✗", len(cross), cross[:1]))
    miss += not ok
    # L24:84-85 的反向验证（card-40f4ce13）：拿掉方向限制 ⇒ 不变量必须报出「上涨段里首段向上的框」
    T._DIR_RULE = False
    _R.clear()
    try:
        dirv = [x for fn in ("zec15.json", "zec30_cut.json", "zec_1h.json")
                for x in invariants(fn) if "L24:85" in x]
    finally:
        T._DIR_RULE = True
        _R.clear()
    print("%s L24:85 拿掉中枢方向限制 ⇒ 报出 %d 个框（例 %s）" % ("✓" if dirv else "✗", len(dirv), dirv[:1]))
    miss += not dirv
    # D3-3 读法的反向验证。★ D3-2（3+3+3 重算）＋ D6-4（先限方向）以后，data/、tools/fixtures、线上 15 张**没有一份**
    #   读法 A／B 段型不同（10-07 实测），真数据咬不到了 ⇒ 造一段：一对扩展中枢（合成成一个单元）＋ 它上方一个不重叠的中枢。
    #   读法 A 只数合成单元 ⇒ 升级·盘整；读法 B 合成单元跟本级别中枢一起数 ⇒ 上涨。classify 不给 done ⇒ 走拼 DD／GG 那条，只为够到读法分支。
    zz = [dict(DD=10, GG=20, ZD=12, ZG=18, X0=0, X1=10, kind="—"), dict(DD=15, GG=25, ZD=16, ZG=22, X0=11, X1=20, kind="扩展"),
          dict(DD=40, GG=50, ZD=42, ZG=48, X0=21, X1=30, kind="趋势")]
    ka, kb = T.classify(zz, "A"), T.classify(zz, "B")
    ok = ka == ("盘整", True) and kb == ("上涨", True)
    print("%s D3 读法 A／B（造的一段）⇒ A %s ／ B %s" % ("✓" if ok else "✗", ka, kb))
    miss += not ok
    # D6 只管本级别（card-0374e640-127，Nova 08:00Z）—— 造出来的牙：把 zec15 第 6 段（本级别下跌、D6 会限它的方向）
    #   第一遍段型硬改成「升级·下跌」。规则对 ⇒ 这段的框跟不限方向时一样；拿掉这条（_D6_BASE_ONLY=False）⇒ 照样被限、框不一样。
    real_cls = T.classify
    def fake(zz, reading="A", done=None):
        k, up = real_cls(zz, reading, done)
        return (k, True) if zz and zz[0]["PI0"] >= fake.lo and zz[0]["PI0"] < fake.hi and k == "下跌" else (k, up)
    r15, v15 = run("zec15.json")
    b6 = v15["segments"][6]
    dn = T._done(r15)
    fake.lo = next(k for k, x in enumerate(dn) if x["i0"] >= b6["i0"])
    fake.hi = next((k for k, x in enumerate(dn) if x["i0"] >= b6["i1"]), len(dn))
    box6 = lambda v: sorted((z["X0"], z["X1"]) for z in v["seg_centers"] if z["seg"] == 6)
    T.classify = fake
    try:
        on = box6(T.trend_v3(r15, reading=READING))
        T._DIR_RULE = False
        free = box6(T.trend_v3(r15, reading=READING))
        T._DIR_RULE = True
        T._D6_BASE_ONLY = False
        off = box6(T.trend_v3(r15, reading=READING))
    finally:
        T.classify, T._DIR_RULE, T._D6_BASE_ONLY = real_cls, True, True
    ok = on == free and off != free
    print("%s D6 只管本级别：第 6 段假装成升级·下跌 ⇒ 框跟不限时%s；拿掉这条 ⇒ %s" % ("✓" if ok else "✗",
          "一样" if on == free else "不一样（该一样）", "被限了（该这样）" if off != free else "没被限（牙没咬到）"))
    miss += not ok
    # D3-2／D3-4 的反向验证（card-0374e640-127）：各拧回旧写法，不变量必须报
    for flag, fn, name in (("_D3_REGROUP", "zec15.json", "合成框退回拼 DD／GG"), ("_D3_LIVE_TAIL", "zec30_cut.json", "最后一个中枢还在走也合成")):
        setattr(T, flag, False)
        try:
            hits = [x for x in invariants(fn) if "合成框" in x]
        finally:
            setattr(T, flag, True)
        print("%s D3 %s ⇒ 报出 %d 处（例 %s）" % ("✓" if hits else "✗", name, len(hits), hits[:1]))
        miss += not hits
    for name, kw, changed in arms:
        _, v = run("zec15.json", **kw)
        ok = changed(v)
        print("%s %s ⇒ 分界 %d、撤回 %d（原样 %d、%d）" % ("✓" if ok else "✗", name, len(v["bounds"]),
              len(v["retracted"]), len(base["bounds"]), len(base["retracted"])))
        miss += not ok
    return 3 if miss else 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
