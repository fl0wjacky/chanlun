#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中枢切分（core/cut.py，docs/spec/中枢切分.md）的检查＋探针。rc=0 才算过。

    python3 tools/cut_check.py [bars.json]     # 不给就用 data/zec15.json
    python3 tools/cut_check.py --self-test     # ⑨ 的反向验证：造跨刀的框，必须报出来

逐条核：
  ① 形状：cuts 按 cut_bar 升序、cut_bar 都是已完成线段端点、status ∈ pending/done/void、boxes 只在 pending 有且全带 provisional；
  ② 规则 4：没有 done 的刀 ⇒ seg_centers 跟不切那份逐字段相同（待定照回旧框）；
  ③ 规则 5：每一刀的 status 按「切点后头三段已完成线段重叠」独立重算一遍，必须对上；
  ④ 规则 6：只动线段中枢 —— 笔、线段、类中枢、两层买卖点不变（cut_centers 不改 r）；
  探针 A（规格第三节第 4 条）：把『头三段重叠』改成『头一段走完就算』⇒ 切成数必须变；
  探针 C：三类往回落不分高低点（只收同类端点之前的样子）⇒ zec15 上刀位置必须变（19164 那把回来）；
  探针 B：转折点改在线段层认 ⇒ 最低点那个框（405.9–423）必须切不开（10-05 往回落以后最高点那个能被线段层三卖切到）。旧注：『线段层认出的刀里没有一刀
         落在 405.9–423 / 523.24–549.65 两个框的内部』。
"""
import copy
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.analyze import analyze                              # noqa: E402
import core.signals                                           # noqa: E402,F401
import core.cut as C                                          # noqa: E402
S = sys.modules["core.signals"]


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


def span_violations(files=None, measure="macd", strict=True):
    """card-e634f6e9-bb5：cut=turn 下，**任何框都不许跨过已切成（done）的切点** —— 框跟走势分段对得上。
    跨 = 框的成员线段里，有一段在切点之前、有一段在切点之后（X0 < cut_bar < X1）。
    ★ 不等号必须**严格**：切点正好压在框沿上（cut_bar == X0 或 == X1）是故意允许的那一档（框在刀处相接，
      前端 cut-edge f3f063e 就是为它写的）。收紧成 <= 会把这一档在真数据上全报成红（--self-test 第二条量这个）。
    X0/X1 跟前端画框用的是同一条式子（web/layers.js：host[PI0].i0 .. host[PI1].i1），所以这里守的是屏幕上画出来的框。
    pending / void 的刀不算：待定时旧框照画是规则页定的（L88:14），作废的刀本来就不切。
    返回 [(文件, cut_bar, 切点的 by, 框 X0, 框 X1)]，应为空。"""
    from config import tick_of
    bad = []
    for fn in files or kline_files():
        r = analyze(load(os.path.join(ROOT, "data", fn)), tick=tick_of(fn))
        cur, cuts = C.cut_centers(r, S.signals(r, "pen", measure))
        for c in cuts:
            if c["status"] != "done":
                continue
            for z in cur:
                inside = (z["X0"] < c["cut_bar"] < z["X1"]) if strict else (z["X0"] <= c["cut_bar"] <= z["X1"])
                if inside:
                    bad.append((fn, c["cut_bar"], c["by"], z["X0"], z["X1"]))
        # 预览框（cuts[i].boxes，provisional）是「待定的刀也切了」那一版：它们不许跨过任何 done 或 pending 的刀
        live_cuts = [c["cut_bar"] for c in cuts if c["status"] in ("done", "pending")]
        for c in cuts:
            for z in c.get("boxes", []):
                for x in live_cuts:
                    if z["X0"] < x < z["X1"]:
                        bad.append((fn + "（预览框）", x, c["by"], z["X0"], z["X1"]))
    return bad


def span_self_test():
    """反向验证：把「切成的刀要分组」拿掉（_centers_with_cuts 忽略切点），框必然跨刀 ⇒ 必须报出来。"""
    real = C._centers_with_cuts
    C._centers_with_cuts = lambda done, ks: real(done, [])
    try:
        n = len(span_violations())
    finally:
        C._centers_with_cuts = real
    print("%s 变异「切成的刀不分组」⇒ 跨刀的框 %d 个" % ("✓" if n else "✗", n))
    m = len(span_violations(strict=False))
    print("%s 收紧成 <=（框沿也算跨）⇒ 真数据上报 %d 个 —— 证明「压在框沿」这一档真实存在，不等号必须严格"
          % ("✓" if m else "✗", m))
    # 第三条（Atlas 核 d4fd3c3 时自己加的那一刀，收进来）：预览框不按待定的刀分组 ⇒ 预览框跨刀，必须报出来。
    #  样本里预览框很少（10 份里只有 1 个待定刀带预览框），所以这一条薄，但它是这一支唯一的牙。
    src = open(C.__file__, encoding="utf-8").read()
    if "preview = _centers_with_cuts(done, sorted(k_done + k_pend))" not in src:
        print("✗ 第三条找不到预览那一行，变异没打上 ⇒ 不算数")
        return 3
    real_cc = C.cut_centers
    ns = {}
    exec(compile(src.replace("preview = _centers_with_cuts(done, sorted(k_done + k_pend))",
                             "preview = _centers_with_cuts(done, k_done)"), C.__file__, "exec"), C.__dict__, ns)
    C.cut_centers = ns["cut_centers"]
    try:
        p = len(span_violations())
    finally:
        C.cut_centers = real_cc
    print("%s 变异「预览框不按待定的刀分组」⇒ 跨刀的预览框 %d 个" % ("✓" if p else "✗", p))
    return 0 if n and m and p else 3


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "zec15.json")
    r = analyze(load(path), tick=0.01)
    before = copy.deepcopy(r)
    sig = S.signals(r, "pen", "macd")
    cur, cuts = C.cut_centers(r, sig)
    done = [s for s in r["segs"] if not s.get("live")]
    ends = {done[0]["i0"]} | {s["i1"] for s in done}
    bad, skipped = [], []

    def cell(name, ok, note=""):
        print("%s %s %s" % ("✓" if ok else "✗", name, note))
        if not ok:
            bad.append(name)

    shape_ok = (all(a["cut_bar"] < b["cut_bar"] for a, b in zip(cuts, cuts[1:]))
                and all(c["cut_bar"] in ends and c["status"] in ("pending", "done", "void") and c["level"] == "seg"
                        for c in cuts)
                and all(("boxes" in c) == (c["status"] == "pending") for c in cuts)
                and all(z.get("provisional") is True for c in cuts for z in c.get("boxes", [])))
    cell("① 形状（升序、落在线段端点、status 三选一、boxes 只在 pending 且带 provisional）", shape_ok, "%d 刀" % len(cuts))

    nodone = [dict(c, status="pending") for c in cuts]
    k_none = C._centers_with_cuts(done, [])
    cell("② 一刀不切时重建出来的 ＝ 原 seg_centers（待定照回旧框的前提）", [(z["PI0"], z["PI1"], z["ZD"], z["ZG"]) for z in k_none]
         == [(z["PI0"], z["PI1"], z["ZD"], z["ZG"]) for z in r["seg_centers"]], "（%d 刀全当待定）" % len(nodone))

    pos = {s["i0"]: k for k, s in enumerate(done)}
    mism = []
    for c in cuts:
        k = pos.get(c["cut_bar"], len(done))
        tri = done[k:k + 3]
        want = "pending" if len(tri) < 3 else ("done" if min(x["hi"] for x in tri) >= max(x["lo"] for x in tri) else "void")
        if want != c["status"]:
            mism.append((c["cut_bar"], c["status"], want))
    cell("③ 规则 5 独立重算", not mism, "不符 %s" % mism[:3])

    same = all(r[k] == before[k] for k in ("pens", "segs", "centers", "seg_centers"))
    cell("④ 只动线段中枢（r 原样、买卖点不变）", same and S.signals(r, "pen", "macd") == sig
         and S.signals(r, "seg", "macd") == S.signals(before, "seg", "macd"))

    # ⑤ 规则 2/3 独立重算切点（不调 _turn_bar / _snap / _backdate）：
    #    一类＝极值那根落最近端点；三类＝离开笔（终点正好是回试笔起点的那笔）起点之前、上一刀之后的
    #    **同类**端点里，三买取最低、三卖取最高（一样极取后一个）—— 10-05 改的「往回落到前一走势结束点」。
    pens, bars = r["pens"], r["bars"]
    end_list = sorted(ends)
    want, prev = set(), end_list[0]
    fin = [x for x in r["segs"] if not x.get("live")]
    lows = {x["i1"] for x in fin if x["dir"] == "down"} | {x["i0"] for x in fin if x["dir"] == "up"}
    for g in sorted(sig, key=lambda g: g["bar"]):
        if not g["confirmed"] or g["kind"] not in C.TURN_KINDS:
            continue
        if g["kind"] in ("一买", "一卖"):
            e = min(end_list, key=lambda x: (abs(x - g["bar"]), -x))
        else:
            leave = [p for p in pens if p["i1"] == pens[g["unit"]]["i0"]][0]
            # 只收同类端点（Nova 10-05 12:47）：低点＝向下线段的终点或向上线段的起点，高点反过来
            want_low = g["kind"] == "三买"
            win = [x for x in end_list if prev < x <= leave["i0"] and (x in lows) == want_low]
            if not win:
                continue
            if g["kind"] == "三买":
                e = sorted(win, key=lambda x: (bars[x]["l"], -x))[0]
            else:
                e = sorted(win, key=lambda x: (-bars[x]["h"], -x))[0]
        if e != end_list[0]:
            want.add(e)
            prev = max(prev, e)
    got = {c["cut_bar"] for c in cuts}
    cell("⑤ 切点位置独立重算（一类＝极值、三类＝往回取上一刀以来的最低/最高端点）", got == want,
         "多 %s 少 %s" % (sorted(got - want)[:3], sorted(want - got)[:3]))

    # ⑥ 规则 4：被切点截断的组，最后那个框不许还标「仍在延续」—— 只有全图最后一个框可以是 live
    lives = [k for k, z in enumerate(cur) if z["live"]]
    cell("⑥ 只有最后一个框可以是 live（组尾被截断的标『转折点切开』）", all(k == len(cur) - 1 for k in lives)
         and any(z["term"] == "转折点切开" for z in cur), "live 的下标 %s" % lives)

    # ⑦ 钉死（规格第三节第 1 条）：data/zec15.json 上那两个横跨的框，各被谁切、切在哪根
    # 10-05 往回落以后：最低点 367.77（11314）、最高点 588.8（12906）都成了切成的刀
    PIN = {(10811, 11859): [(11097, "笔·三卖", "void"), (11314, "笔·三买", "done")],
           (12632, 13528): [(12906, "笔·一卖", "done"), (13273, "笔·三卖", "done"), (13403, "笔·三卖", "done")]}
    if os.path.basename(path) == "zec15.json":
        pin_bad = []
        for (x0, x1), exp in PIN.items():
            have = [(c["cut_bar"], c["by"], c["status"]) for c in cuts if x0 <= c["cut_bar"] <= x1]
            if have != exp:
                pin_bad.append(((x0, x1), have))
        lo_hi_in = [(z["X0"], z["X1"]) for z in cur for x in (11314, 12906) if z["X0"] < x < z["X1"]]
        cell("⑦ 钉死 zec15 那两个框的切点（谁切、切在哪根、状态），且两个极值不在任何框里面", not pin_bad and not lo_hi_in,
             "不符 %s · 极值仍在框内 %s" % (pin_bad[:1], lo_hi_in))
    else:
        skipped.append("⑦")
        print("· ⑦ 未执行（只钉 data/zec15.json；这份是 %s）—— 不算绿" % os.path.basename(path))

    # ⑧ 验收格（Nova 10-05）：线上 ZEC 30m 那份（存成 data/zec30_cut.json）上，最低点 367.77（5354）、最高点 588.8（6150）
    #    都是切成的刀，且都不在任何切后的框里面 —— 朋友说的「上下两个转折不能在同一个框里」。
    r30 = analyze(load(os.path.join(ROOT, "data", "zec30_cut.json")), tick=0.01)
    cur30, cuts30 = C.cut_centers(r30, S.signals(r30, "pen", "macd"))
    st = {c["cut_bar"]: c["status"] for c in cuts30}
    inside30 = [(x, z["X0"], z["X1"]) for x in (5354, 6150) for z in cur30 if z["X0"] < x < z["X1"]]
    cell("⑧ ZEC 30m：5354、6150 两个极值都切成，且不在任何框里面", st.get(5354) == "done" and st.get(6150) == "done"
         and not inside30, "状态 5354=%s 6150=%s · 仍在框内 %s" % (st.get(5354), st.get(6150), inside30))

    # ⑨ 框不跨已切成的切点（card-e634f6e9-bb5）：data/ 下所有 K 线样本都跑
    sv = span_violations()
    cell("⑨ 所有样本（%d 份）：没有框跨过已切成的切点" % len(kline_files()), not sv, "跨刀 %s" % sv[:3])

    real = C._status
    C._status = lambda done_, k: "done" if k + 1 <= len(done_) else "pending"     # 头一段走完就算
    try:
        _, cuts_a = C.cut_centers(r, sig)
    finally:
        C._status = real
    n0, na = sum(c["status"] == "done" for c in cuts), sum(c["status"] == "done" for c in cuts_a)
    cell("探针 A：『头一段走完就算』⇒ 切成数变", n0 != na, "%d → %d" % (n0, na))

    class _AnyKind:                                       # 变异：三类往回落不分高低点（10-05 12:47 之前的样子）
        def __eq__(self, other):
            return True
    real_low = C._is_low
    C._is_low = lambda done_, k: _AnyKind()
    try:
        _, cuts_c = C.cut_centers(r, sig)
    finally:
        C._is_low = real_low
    diff_c = sorted({c["cut_bar"] for c in cuts_c} ^ {c["cut_bar"] for c in cuts})
    cell("探针 C：三类往回落不分高低点 ⇒ 刀位置变（⑤ 得跟着红）", bool(diff_c), "差 %s" % diff_c[:5])

    seg_sig = S.signals(r, "seg", "macd")
    _, cuts_b = C.cut_centers(r, seg_sig, units=r["segs"])
    targets = [z for z in r["seg_centers"] if round(z["ZD"], 2) in (405.90, 523.24)]
    hit = {(z["X0"], z["X1"]): [c["cut_bar"] for c in cuts_b if z["X0"] < c["cut_bar"] < z["X1"]] for z in targets}
    # 10-05 往回落以后，线段层的三卖也会往回落到最高点上 ⇒ 规格原先「线段层认、两个框都切不开」不再成立。
    # 现在守的是还成立的那一半：最低点那个框（405.9–423）在线段层仍切不开（线段层在那儿没有能往回落到低点的三买）。
    low_box = [v for (x0, x1), v in hit.items() if any(round(z["ZD"], 2) == 405.90 and z["X0"] == x0 for z in targets)]
    if not low_box:
        skipped.append("探针 B")
        print("· 探针 B 未执行（这份数据里没有 405.9–423 那个框）—— 不算绿")
    else:
        cell("探针 B：线段层认 ⇒ 最低点那个框切不开（最高点那个现在能被线段层三卖往回切到，见卡）",
             not low_box[0], "（目标框 %d 个；各框里线段层的刀 %s）" % (len(targets), hit))
    print(("全部通过" + ("（%s 未执行）" % "、".join(skipped) if skipped else "")) if not bad else "%d 格不过" % len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(span_self_test() if "--self-test" in sys.argv else main())
