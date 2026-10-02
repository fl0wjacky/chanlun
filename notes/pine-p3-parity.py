# -*- coding: utf-8 -*-
"""把 `tradingview/chanlun.pine` 里**新加的那段**逐行抄成 Python，跟引擎对账（只读）。

为什么要有这个：Pine 在这台机器上**编译不了、跑不了**，而 `tools/pine_lockstep.py` 只回答
「引擎自 pine 上次改动以来变了没有」，**不回答「pine 和引擎算的是不是一回事」**。所以新写进
pine 的 `hierarchy()` / `p3Hit()` 没有任何本地验证 —— 这个脚本补的就是那一块：

    pine 里的 hierarchy()/p3Hit()  ⟷  core/signals.py 的 _higher_centers()/check_premise3()

做法：**照 pine 的源码逐行翻译**（变量名、分支顺序、连 `break` 的位置都对齐），然后对六份
数据 × seg/pen 的**每一个 (中枢 B, 方向) 候选**，比对两边算出的前提③结论。

★ 它能证什么、不能证什么：
    能证 —— 我**想写进 pine 的算法**与引擎一致（层级选对了、合并条件对了、区间对了）。
    不能证 —— pine 的**语法/idiom** 本身能编译（那要 TradingView）。这条限制写在报告里。

    python3 notes/pine-p3-parity.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.analyze import analyze_file                                   # noqa: E402
from core.signals import _units, _higher_centers, check_premise3        # noqa: E402

FILES = ["zec15.json", "zec_1h.json", "zec_4h.json", "btc_4h.json",
         "aaplusdt_4h.json", "aaplusdt_30m.json"]


# ─────────────────── 以下三支：tradingview/chanlun.pine 的逐行翻译 ───────────────────

def relOf(A, B):                       # pine: relOf(Ctr A, Ctr B)
    if B["GG"] < A["DD"]:
        return 1
    if B["DD"] > A["GG"]:
        return 2
    if B["ZG"] < A["ZD"] and B["GG"] >= A["DD"]:
        return 3
    if B["ZD"] > A["ZG"] and B["DD"] <= A["GG"]:
        return 4
    return 5


def hierarchy(zs, U):                  # pine: hierarchy(array<Ctr> zs, array<Unit> U)
    out = []
    k = 0
    while k < len(zs):
        A = zs[k]
        merge = False
        if k + 1 < len(zs):
            rl = relOf(A, zs[k + 1])
            merge = (not A.get("live")) and rl != 1 and rl != 2
        if merge:
            B = zs[k + 1]
            s2lo, s2hi = B["DD"], B["GG"]
            if B["PI0"] - 1 >= A["PI1"] + 1:
                s2lo = U[A["PI1"] + 1]["lo"]
                s2hi = U[A["PI1"] + 1]["hi"]
                t = A["PI1"] + 2
                while t <= B["PI0"] - 1:
                    s2lo = min(s2lo, U[t]["lo"])
                    s2hi = max(s2hi, U[t]["hi"])
                    t += 1
            ZD = max(A["DD"], max(s2lo, B["DD"]))
            ZG = min(A["GG"], min(s2hi, B["GG"]))
            DD = min(A["DD"], min(s2lo, B["DD"]))
            GG = max(A["GG"], max(s2hi, B["GG"]))
            PI1, live = B["PI1"], bool(B.get("live"))
            k += 2
            while k < len(zs) and ZG >= ZD and not live:
                Cn = zs[k]
                if Cn["DD"] > ZG or Cn["GG"] < ZD:
                    break
                DD = min(DD, Cn["DD"])
                GG = max(GG, Cn["GG"])
                PI1 = Cn["PI1"]
                live = bool(Cn.get("live"))
                k += 1
            out.append(dict(PI0=A["PI0"], PI1=PI1, ZD=ZD, ZG=ZG, DD=DD, GG=GG, live=live))
        else:
            out.append(dict(PI0=A["PI0"], PI1=A["PI1"], ZD=A["ZD"], ZG=A["ZG"],
                            DD=A["DD"], GG=A["GG"], live=bool(A.get("live"))))
            k += 1
    return out


def p3Hit(higher, B, lo, hi):          # pine: p3Hit(array<Ctr> higher, Ctr B, float lo, float hi)
    hit = False
    if len(B.get("up") or []) == 0:
        for H in higher:
            if H["ZD"] <= lo and H["ZG"] >= hi:
                hit = True
                break
    return hit


# ─────────────────────────────── 对账 ───────────────────────────────

def candidates(r, level):
    """遍历 pine 的 signalsOf 会走到的那批 (B, 方向) 候选，交出 (k, wantDown, lo, hi)。"""
    AU, _U, Z = _units(r, level)
    for k in range(1, len(Z)):
        B = Z[k]
        if B["rel"] not in ("下跌延续", "上涨延续"):
            continue
        want_down = B["rel"] == "下跌延续"
        same = (lambda u: u["p1"] < u["p0"]) if want_down else (lambda u: u["p1"] > u["p0"])
        a = next((q for q in range(B["PI0"] - 1, -1, -1) if same(AU[q])), None)
        c = next((q for q in (B["PI1"] + 1, B["PI1"] + 2) if q < len(AU) and same(AU[q])), None)
        if a is None or c is None:
            continue
        A, C = AU[a], AU[c]
        lo = min(A["lo"], B["DD"], C["lo"])
        hi = max(A["hi"], B["GG"], C["hi"])
        yield k, want_down, B, lo, hi


def main():
    n = bad = hits_pine = hits_eng = 0
    for level in ("pen", "seg"):
        for fn in FILES:
            r = analyze_file(fn)
            AU, _U, Z = _units(r, level)
            done = [s for s in r["segs"] if not s.get("live")]
            # pine 的两条 higher 来源（见 chanlun.pine 主流程 segLevel 那一段）
            pine_higher = r["seg_centers"] if level == "pen" else hierarchy(r["seg_centers"], done)
            eng_higher = _higher_centers(r, level)
            # 先把两支 higher 的几何逐条对上
            if len(pine_higher) != len(eng_higher):
                print("✗ %s|%s higher 条数不同：pine %d vs 引擎 %d"
                      % (fn, level, len(pine_higher), len(eng_higher)))
                bad += 1
            else:
                for i, (p, e) in enumerate(zip(pine_higher, eng_higher)):
                    if (round(p["ZD"], 9), round(p["ZG"], 9)) != (round(e["ZD"], 9), round(e["ZG"], 9)):
                        print("✗ %s|%s higher[%d] 区间不同：pine [%.4f,%.4f] vs 引擎 [%.4f,%.4f]"
                              % (fn, level, i, p["ZD"], p["ZG"], e["ZD"], e["ZG"]))
                        bad += 1
            for k, want_down, B, lo, hi in candidates(r, level):
                n += 1
                ph = p3Hit(pine_higher, B, lo, hi)
                eh = check_premise3(eng_higher, B, lo, hi, True)["hit"]
                hits_pine += ph
                hits_eng += eh
                if ph != eh:
                    bad += 1
                    print("✗ %s|%s B#%d %s：pine=%s 引擎=%s" %
                          (fn, level, k, "买" if want_down else "卖", ph, eh))
    print("候选 %d 个 · 前提③ 命中 pine %d / 引擎 %d · 不一致 %d" % (n, hits_pine, hits_eng, bad))
    print("⇒ %s" % ("Pine 里那段算法与引擎一致（语法能否编译不在此脚本范围内）" if bad == 0 else "★ 不一致，见上"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
