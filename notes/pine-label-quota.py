# -*- coding: utf-8 -*-
"""中枢标签撞不撞 pine 的配额线 —— 逐份数据重算一遍（只读）。

为什么要有这个：2026-10-02 小栋要「每一个中枢（类中枢、线段中枢、升级中枢）左上角都标 [ZD, ZG]」。
这一下**类中枢那族的标签需求从「只有满 9 段的升级标签」变成「每个中枢 1 个价签 + 升级另算」**，
而 pine 里中枢那两族一共只有 198 格标签（`CTR_LB_CAP`），还要再对半分给两类。
需求翻了近 7 倍，**原来的注释「实测合计才 26 个，根本撞不到线」当场失义** ——
所以这里把撞线与否算成数，别拿感觉顶。

照 pine 的判据抄（不是照感觉估）：

    盒子  每个中枢 1 + (拆两截 ? 1) + upZD.size()         上限 PC_BOX_CAP 378 / SC_BOX_CAP 120
    标签  每个中枢 1（价签）+ upZD.size()（每个升级框一个）  上限 PC_LB_SHARE / SC_LB_SHARE 各 99
    顺序  **倒序**（pine 的 `for k = arr.size() - 1 to 0`）：最新的先画，配额用完 break
          ⇒ 丢标签时丢的一定是**最老的那一头**（这正是小栋要的「保留最新的」）

★ 它能证什么、不能证什么：
    能证 —— 按 pine 的配额与顺序，各份数据上「谁被丢、丢几个」。
    不能证 —— TradingView 上的实际表现（只在 barstate.islast 画、x0Draw 窗口过滤没建模，
              所以这里是**全窗口**的保守上界：真实占用只会更少，不会更多）。
              也不能证 pine 能编译 —— 那要 TradingView。
    ★ 一处口径差，说在前面：升级框的个数，pine 数的是**它自己推的** `z.upZD`（chanlun.pine:681-698
      那一段现推的），这边数的是引擎给的 `z["up"]`。两边是同一个概念、但**不是同一段代码** ——
      本条脚本证不了它们永远相等（那要看两边各自的升级判定，不是这张尺的活）。数一下只为量级。

    python3 notes/pine-label-quota.py
退出码：0 = 算完（并印出有没有哪份撞线）；1 = 一份数据都没读到（查不了 ≠ 通过）。
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import data                                              # noqa: E402
from core.analyze import analyze_file                                # noqa: E402

# 与 tradingview/chanlun.pine 的常量逐字对应，改那边记得改这边
PC_BOX_CAP, SC_BOX_CAP = 378, 120
PC_LB_SHARE, SC_LB_SHARE = 99, 99


def split_of(z, host, hasPen, np_):
    """pine 的 wholeDash / split，含「框短到装不下分界就退回整框」那条守卫。"""
    whole = (np_ - 1) < z["PI0"] + 3 if hasPen else False     # 线段层没有「没走完的那一员」
    if whole:
        return False
    a, b = host[z["PI0"]]["i0"], host[z["PI1"]]["i1"]
    xm = host[min(z["PI0"] + 2, len(host) - 1)]["i1"]
    return z["live"] and a < xm < b


def count(cs, host, hasPen, np_, box_cap, lb_cap):
    """→ (画进几个中枢, 盒子占几格, 想要几个标签, 实得几个标签)。"""
    boxes = labels = drawn = 0
    for z in reversed(cs):                                     # ★ 倒序：pine 就是这个顺序
        nup = len(z.get("up") or [])                           # 引擎侧叫 up，pine 侧叫 upZD（见文件头那处口径差）
        cost = 1 + (1 if split_of(z, host, hasPen, np_) else 0) + nup
        if boxes + cost > box_cap:
            break
        boxes += cost
        drawn += 1
        labels = min(labels + 1 + nup, lb_cap)                 # 价签 + 每个升级框一个
    return drawn, boxes, sum(1 + len(z.get("up") or []) for z in cs), labels


def main():
    files = sorted(os.path.basename(p) for p in glob.glob(data("*.json")))
    seen = hit = 0
    for fn in files:
        try:
            r = analyze_file(fn)
        except Exception:                                      # config.TICK 没写精度的那几份
            continue
        seen += 1
        pens, done = r["pens"], [s for s in r["segs"] if not s.get("live")]
        for name, cs, host, hasPen, np_, bc, lc in (
                ("类中枢", r["centers"], pens, True, len(pens), PC_BOX_CAP, PC_LB_SHARE),
                ("线段中枢", r["seg_centers"], done, False, 0, SC_BOX_CAP, SC_LB_SHARE)):
            if not cs:
                continue
            drawn, boxes, want, got = count(cs, host, hasPen, np_, bc, lc)
            flag = ""
            if got < want:
                hit += 1
                flag = "  ← 撞线，丢的是最老的 %d 个" % (want - got)
            print("%-18s %-5s 中枢 %3d 个 → 画进 %3d；盒子 %3d/%d；标签 想要 %3d 实得 %3d%s"
                  % (fn, name, len(cs), drawn, boxes, bc, want, got, flag))
    if seen == 0:
        print("★ 一份数据都没读到 —— 查不了 ≠ 通过")
        return 1
    print("\n读了 %d 份数据；有 %d 处撞线（撞线时丢的都是最老的中枢，"
          "且线段中枢那 99 格是另算的、不会被类中枢吃掉）" % (seen, hit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
