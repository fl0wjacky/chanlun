#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中枢切分（core/cut.py，docs/spec/中枢切分.md）的检查＋探针。rc=0 才算过。

    python3 tools/cut_check.py [bars.json]     # 不给就用 data/zec15.json

逐条核：
  ① 形状：cuts 按 cut_bar 升序、cut_bar 都是已完成线段端点、status ∈ pending/done/void、boxes 只在 pending 有且全带 provisional；
  ② 规则 4：没有 done 的刀 ⇒ seg_centers 跟不切那份逐字段相同（待定照回旧框）；
  ③ 规则 5：每一刀的 status 按「切点后头三段已完成线段重叠」独立重算一遍，必须对上；
  ④ 规则 6：只动线段中枢 —— 笔、线段、类中枢、两层买卖点不变（cut_centers 不改 r）；
  探针 A（规格第三节第 4 条）：把『头三段重叠』改成『头一段走完就算』⇒ 切成数必须变；
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
    #    端点里，三买取最低、三卖取最高（一样极取后一个）—— 10-05 改的「往回落到前一走势结束点」。
    pens, bars = r["pens"], r["bars"]
    end_list = sorted(ends)
    want, prev = set(), end_list[0]
    for g in sorted(sig, key=lambda g: g["bar"]):
        if not g["confirmed"] or g["kind"] not in C.TURN_KINDS:
            continue
        if g["kind"] in ("一买", "一卖"):
            e = min(end_list, key=lambda x: (abs(x - g["bar"]), -x))
        else:
            leave = [p for p in pens if p["i1"] == pens[g["unit"]]["i0"]][0]
            win = [x for x in end_list if prev < x <= leave["i0"]]
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

    real = C._status
    C._status = lambda done_, k: "done" if k + 1 <= len(done_) else "pending"     # 头一段走完就算
    try:
        _, cuts_a = C.cut_centers(r, sig)
    finally:
        C._status = real
    n0, na = sum(c["status"] == "done" for c in cuts), sum(c["status"] == "done" for c in cuts_a)
    cell("探针 A：『头一段走完就算』⇒ 切成数变", n0 != na, "%d → %d" % (n0, na))

    seg_sig = S.signals(r, "seg", "macd")
    _, cuts_b = C.cut_centers(r, seg_sig, units=r["segs"])
    targets = [z for z in r["seg_centers"] if round(z["ZD"], 2) in (405.90, 523.24)]
    hit = {(z["X0"], z["X1"]): [c["cut_bar"] for c in cuts_b if z["X0"] < c["cut_bar"] < z["X1"]] for z in targets}
    # 10-05 往回落以后，线段层的三卖也会往回落到最高点上 ⇒ 规格原先「线段层认、两个框都切不开」不再成立。
    # 现在守的是还成立的那一半：最低点那个框（405.9–423）在线段层仍切不开（线段层在那儿没有能往回落到低点的三买）。
    low_box = [v for (x0, x1), v in hit.items() if any(round(z["ZD"], 2) == 405.90 and z["X0"] == x0 for z in targets)]
    cell("探针 B：线段层认 ⇒ 最低点那个框切不开（最高点那个现在能被线段层三卖往回切到，见卡）",
         bool(low_box) and not low_box[0], "（目标框 %d 个；各框里线段层的刀 %s）" % (len(targets), hit))
    print(("全部通过" + ("（%s 未执行）" % "、".join(skipped) if skipped else "")) if not bad else "%d 格不过" % len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
