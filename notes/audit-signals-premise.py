# -*- coding: utf-8 -*-
"""引擎对说明书（买卖点/背驰/均线）· 背驰 §五 四条件的**回验器**。—— 只读，不动 core/ 任何一行。

对 `core/signals.py` 报出的每个一买/一卖，用**它自己的取段规则**取回 A、B、C，然后问三件事：

  P3  有没有一个**更高一层**的中枢把 A、B、C 整段包住？
      （原文 `L53:91`：B 的中枢级别要比 A、C 里的都大，**否则 A、B、C 就连成一个大的趋势或大的中枢**）
      —— 真被包住 ⇒ 原文说这里不是趋势背驰 ⇒ 程序**多报**的候补。
      另记 B 自己的 `up`（9 段升级）非空没有 —— 有则 B 同时是高一级别中枢，P3 大致成立。

  P4  A 开始之前、**同一层**里有没有已经结束的中枢？
      （原文 `L53:91-92`：A 段之前一定是和 B 同级别或更大级别的一个中枢）

  ZA  「B 段回抽 0 轴附近」（默认关的那条检查）：r 是多少、开着会不会挡下来。

用法：在仓根跑 `python3 notes/audit-signals-premise.py`
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.analyze import analyze_file            # noqa: E402
from core.signals import _units, signals, zero_axis, ZA_THRESHOLD   # noqa: E402

FILES = ["zec15.json", "zec_1h.json", "zec_4h.json", "btc_4h.json",
         "aaplusdt_4h.json", "aaplusdt_30m.json"]


def seg_of(r, level, s):
    """按 signals() 的规则取回 A、C（同一段函数照抄，不改信号本身）。"""
    AU, U, Z = _units(r, level)
    k = s["center"] - 1
    B = Z[k]
    buy = s["kind"].endswith("买")
    same = (lambda u: u["p1"] < u["p0"]) if buy else (lambda u: u["p1"] > u["p0"])
    a = next((q for q in range(B["PI0"] - 1, -1, -1) if same(AU[q])), None)
    c = next((q for q in (B["PI1"] + 1, B["PI1"] + 2) if q < len(AU) and same(AU[q])), None)
    return AU, Z, k, B, a, c


def probe(r, level, s):
    AU, Z, k, B, a, c = seg_of(r, level, s)
    if a is None or c is None:
        return None
    A, C = AU[a], AU[c]
    lo = min(A["lo"], B["DD"], C["lo"])
    hi = max(A["hi"], B["GG"], C["hi"])
    higher = r["seg_centers"] if level == "pen" else r["big"]
    strict = [H for H in higher if H["ZD"] <= lo and H["ZG"] >= hi]          # 全在【区间】里
    loose = [H for H in higher if H["DD"] <= lo and H["GG"] >= hi]           # 全在【波动范围】里
    prior = [z for z in Z[:k] if z["X1"] <= A["i0"]]                         # A 之前已结束的同层中枢
    return dict(s=s, A=A, B=B, C=C, lo=lo, hi=hi, strict=strict, loose=loose,
                prior=prior, b_up=bool(B.get("up")), a=a, c=c, k=k)


def main():
    print("== 背驰 §五 四条件 · 回验（core/signals.py，提交 335e3a3）==")
    print("原文坐标：L53:89-94（干净重述）· L24:20-24（首述）\n")
    tot = dict(points=0, p3_strict=0, p3_loose=0, p4_none=0, za_off=0)
    for lv in ("seg", "pen"):
        for fn in FILES:
            r = analyze_file(fn)
            sig = signals(r, lv, "macd")
            pts = [s for s in sig if s["kind"] in ("一买", "一卖")]
            za = {(x["kind"], x["bar"]): x for x in zero_axis(pts, r, lv)}
            rows = []
            for s in pts:
                p = probe(r, lv, s)
                if p is None:
                    continue
                tot["points"] += 1
                x = za.get((s["kind"], s["bar"]))
                if x is not None and not x["ok"]:
                    tot["za_off"] += 1
                if p["strict"]:
                    tot["p3_strict"] += 1
                if p["loose"]:
                    tot["p3_loose"] += 1
                if not p["prior"]:
                    tot["p4_none"] += 1
                flag = ""
                if p["loose"]:
                    H = p["loose"][0]
                    flag = "P3↯ 被更高层中枢包住 [%s] %.4f~%.4f" % (
                        "升级" if H.get("up") else "扩展", H["ZD"], H["ZG"])
                elif not p["prior"]:
                    flag = "P4↯ A 之前无同层中枢"
                rows.append("  %-4s %-3s @bar%-5d A[%d→%d] C[%d→%d] B=[%.4f,%.4f] up=%s %s%s"
                            % (fn.replace(".json", ""), lv, s["bar"], p["A"]["i0"], p["A"]["i1"],
                               p["C"]["i0"], p["C"]["i1"], p["B"]["ZD"], p["B"]["ZG"],
                               "有" if p["b_up"] else "无", flag,
                               "" if x is None or x["ok"] else "  ZA r=%.3f>%.2f" % (x["r"], ZA_THRESHOLD)))
            if rows:
                print("[%s / %s] 一买一卖 %d 个" % (fn.replace(".json", ""), lv, len(pts)))
                for line in rows:
                    print(line)
                print("")
    print("== 合计 ==")
    print("一买/一卖 %d 个 · 被更高一层中枢【整段】包住（区间口径）%d 个 ·（波动范围口径）%d 个"
          % (tot["points"], tot["p3_strict"], tot["p3_loose"]))
    print("A 之前找不到同层中枢 %d 个 · 0 轴那条开着会挡下 %d 个（阈值 %.2f）"
          % (tot["p4_none"], tot["za_off"], ZA_THRESHOLD))


if __name__ == "__main__":
    main()
