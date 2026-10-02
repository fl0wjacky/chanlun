# -*- coding: utf-8 -*-
"""把 `tradingview/chanlun.pine` 里**新写的规则 B 判据**逐行抄成 Python，跟引擎对账（只读）。

为什么要有这个：Pine 在这台机器上**编译不了、跑不了**，`tools/pine_lockstep.py` 只回答
「引擎自 pine 上次改动以来变了没有」，**不回答「pine 和引擎判的是不是一回事」**。中枢框的
虚实规则 B（2026-10-02 小栋定）是这一轮新写进 pine 的**判断**，本地必须有尺：

    pine :993 / :995（类中枢）· :1011- :1013（线段中枢）的 wholeDash / split / xm
        ⟷  render/full_common.py 的 box_split()（Python 侧已成图、小栋看过的那一支）

做法：**照 pine 的源码逐行翻译**（变量名、分支顺序对齐），在**全部数据**上逐个中枢比对
「整框虚线 / 整框实线 / 拆两截」三档，并检查分界落点。

★ 两边都有「框短到装不下分界就退回整框」的守卫，**守卫也必须纳入状态再比**：
    pine `split = … and xm > x0 and xm < x1`；引擎 `frame()` 的 `x0 < int(xm) < x1`。
  实测到过案子（zec_4h 一个 live 类中枢，成员正好 3 个 ⇒ 分界正好落在框右边）：两边**都**退回
  整框实线 —— 语义上也对，「延续那一截」是空的，没东西可虚。这种退化单独计数、不算不一致。

★ 它能证什么、不能证什么：
    能证 —— pine 里那几行判据与引擎一致（含两层「没走完的那一员」口径不同这件事、含上面那条守卫）。
    不能证 —— pine 的语法/idiom 能编译（那要 TradingView），也不能证画出来的**样子**对
              （Pine 的 box 四条边一起画，拆两截会多一条竖边，见 chanlun.pine 的注释）。
              `xc()` 那 9990 根的回画钳位也没建模：钳到同一根上时两边同样降级成整框实线，
              但引擎侧没有这个钳位 —— 只影响 9990 根以前、TV 上本来就画不出的框。

    python3 notes/pine-ruleb-parity.py
退出码：0 = 逐中枢判档一致；1 = 有不一致（印出数据名 / 层 / 下标 / 两边判到什么）。
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import data                                              # noqa: E402
from core.analyze import analyze_file                                # noqa: E402


# ─────────────────── 以下两支：tradingview/chanlun.pine 的逐行翻译 ───────────────────

def pineRule(z, host, hasPen, np_):
    """pine 调用点 + drawCenter 头两行的翻译。→ (整框虚线?, 拆两截?, 分界在 host 里的下标)。

    pine  :993  hasUnf = np - 1 < z.PI0 + 3          （笔层；线段层传 false）
    pine  :995  xm = host.get(math.min(z.PI0 + 2, np - 1)).i1
    pine  :911  wholeDash = hasUnfinished
    pine  :912  split = not wholeDash and z.live and xm > x0 and xm < x1
    """
    if hasPen:
        hasUnfinished = (np_ - 1) < z["PI0"] + 3
    else:
        hasUnfinished = False                        # 线段层没有「没走完的那一员」
    wholeDash = hasUnfinished
    jm = min(z["PI0"] + 2, len(host) - 1)
    split = (not wholeDash) and z["live"]
    return wholeDash, split, jm


def engineRule(z, host, uj):
    """render/full_common.py 的 box_split()：→ (分界 K 线下标 或 None, 整框是否实线)。"""
    j0 = z["PI0"]
    if uj is not None and j0 <= uj < min(j0 + 3, len(host)):
        return None, False                           # ① 前三里夹着没走完的 ⇒ 整框虚线
    if not z["live"]:
        return None, True                            # ② 已结束 ⇒ 整框实线
    return host[min(j0 + 2, len(host) - 1)]["i1"], True   # ③ 仍在延续 ⇒ 拆两截


def main():
    files = sorted(os.path.basename(p) for p in glob.glob(data("*.json")))
    n = bad = skipped = degraded = 0
    # ★ 量程自查：两支函数是我一个人抄的，**两坨代码互相同意**本身不构成证据 ——
    #   三档必须**都在数据里出现过**，这次对账才覆盖到了规则 B 的全部三支。
    seen = {"整框虚线": 0, "整框实线": 0, "拆两截": 0}
    for fn in files:
        try:
            r = analyze_file(fn)
        except Exception as e:                       # config.TICK 没写精度的那几份
            skipped += 1
            print("跳过 %-18s（%s: %s）" % (fn, type(e).__name__, str(e)[:50]))
            continue
        pens = r["pens"]
        done = [s for s in r["segs"] if not s.get("live")]
        layers = (("类中枢", r["centers"], pens, len(pens) - 1, True, len(pens)),
                  ("线段中枢", r["seg_centers"], done, None, False, 0))
        for name, cs, host, uj, hasPen, np_ in layers:
            for z in cs:
                n += 1
                a, b = host[z["PI0"]]["i0"], host[z["PI1"]]["i1"]      # ★ 都是 K 线下标
                wd, sp, jm = pineRule(z, host, hasPen, np_)
                xmBar, solid = engineRule(z, host, uj)
                # 两边的守卫：框短到装不下分界 ⇒ 各自退回整框（pine: xm>x0 and xm<x1；引擎: x0<xm<x1）
                if sp and not (a < host[jm]["i1"] < b):
                    sp = False
                    degraded += 1
                if xmBar is not None and not (a < xmBar < b):
                    xmBar, solid = None, True
                pineState = "整框虚线" if wd else ("拆两截" if sp else "整框实线")
                engState = ("整框虚线" if (xmBar is None and not solid)
                            else ("整框实线" if xmBar is None else "拆两截"))
                seen[engState] = seen.get(engState, 0) + 1
                if pineState != engState:
                    bad += 1
                    print("✗ %s %s PI0=%s PI1=%s live=%s ｜ pine=%s 引擎=%s"
                          % (fn, name, z["PI0"], z["PI1"], z["live"], pineState, engState))
    print("对账 %d 个中枢（跳过 %d 份数据），判档不一致 %d 个 ｜ 分界装不下、两边一起退回整框的 %d 个"
          % (n, skipped, bad, degraded))
    print("三档各出现几次：%s" % " ｜ ".join("%s %d" % (k, v) for k, v in seen.items()))
    if n == 0:
        print("★ 一个中枢都没对上（数据没了？）—— 查不了 ≠ 通过")
        return 1
    for k, v in seen.items():
        if v == 0:
            print("★ 量程不够：『%s』档在全部数据里一次都没出现 ⇒ 这次对账证不了它" % k)
            return 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
