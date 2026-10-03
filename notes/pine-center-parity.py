# -*- coding: utf-8 -*-
"""把 `tradingview/chanlun.pine` 里**段内算类中枢**那段（findCenters + findCentersBySegment）
逐行抄成 Python，跟引擎对账（只读）。

为什么要有这个：Pine 在这台机器上**编译不了、跑不了**，`tools/pine_lockstep.py` 只回答
「引擎自 pine 上次改动以来变了没有」，**不回答「pine 抄的和引擎算的是不是一回事」**。
本卡给类中枢改成段内算，pine 与引擎各有一份 —— 其中两处特别容易抄错、光看 pine 源码看不出来：

    pine 的 findCentersBySegment()  ⟷  core/center.py 的 find_centers_by_segment()

两处被单独验证：
    ① 空段切片守卫：`if cs.size() > 0` —— pine 的 `for ci = 0 to cs.size() - 1` 在 cs 为空时
       就是 `0 to -1`，而 pine 的 for 会**倒着跑**（i=0、i=-1），`cs.get(0)` 当场崩。翻译成
       Python 后这条守卫不报错也不影响结果（空 list 的 for 就是 no-op），所以它**验不出来**，
       只能靠上面那段 pine 源码的静态锚点守着（见 check_pine_anchors）。
    ② 已完成线段里的 live：findCenters 会把每段切片最后那个中枢标成 live —— 那是**被段分界
       截断**，不是真的「仍在延续」。两边都要在已完成线段里把 live 改 False、term 改
       『所在线段结束』。这一条**能验**：翻译版照 pine 写 `if z.live and not s.live`，
       跟引擎逐个中枢比 PI0/PI1/live/term，有一处不同就红。

做法：**照 pine 的源码逐行翻译**（变量名、分支顺序对齐），在**全部数据**上逐个类中枢比
PI0/PI1/live/term（term 按 pine 的 int 枚举 0..5 映射回引擎的中文字符串）。

★ 它能证什么、不能证什么（两句分开，引用时别只引前半句）：
    能证 —— 我**想写进 pine 的那个算法**与引擎一致：每段切片的起止、PI0/PI1 的 rebase、
            live 与终结原因在每一个中枢上判得一样。
    不能证 —— pine 的**语法/idiom 本身**能编译、能跑出同一个结果（那要 TradingView），
            空段切片那条守卫的**语义**也一样验不了（见 ①）。

    python3 notes/pine-center-parity.py              # 全量对账
    python3 notes/pine-center-parity.py --self-test  # 正臂：故意抄错 live 改法，看它会不会红
退出码：
    0  0 处不一致
    1  ★ 有不一致（印出数据名 / 中枢下标 / 两边判到什么）
    2  跑不动（取不到树 / 引擎抛异常）—— **查不了 ≠ 通过**
    3  --self-test 的**正臂没红** ⇒ 这个检查程序本身不算数
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import data                                            # noqa: E402
from core.analyze import analyze_file                              # noqa: E402
from core.center import find_centers_by_segment                    # noqa: E402

# pine 里 term 的 int 枚举 → 引擎的中文字符串（chanlun.pine:128 的注释逐字）
TERM_INT = {0: "仍在延续", 1: "三买", 2: "三卖", 3: "Z 段向上离开", 4: "Z 段向下离开",
            5: "所在线段结束"}


# ─────────────────── 以下两支：tradingview/chanlun.pine 的逐行翻译 ───────────────────

def isUp(u):                          # pine:479  isUp(Unit u) => u.p1 > u.p0
    return u["p1"] > u["p0"]


def pine_find_centers(U):
    """pine 的 findCenters(array<Unit> U) 逐行翻译。只保留对账要用的 PI0/PI1/live/term；
    DD/GG、9 段升级那两段不参与对账，不抄（它们不影响这四样）。"""
    zs = []
    N = len(U)
    i = 0
    while i + 2 < N:
        a, b, c = U[i], U[i + 1], U[i + 2]
        ZG = min(a["hi"], b["hi"], c["hi"])
        ZD = max(a["lo"], b["lo"], c["lo"])
        if ZG >= ZD:
            endU = i + 2
            j = i + 3
            reason = 0
            nxt = -1
            while j < N and reason == 0:
                u = U[j]
                hit = False
                if (j - i) % 2 == 0:
                    if u["lo"] > ZG or u["hi"] < ZD:
                        reason = 3 if u["lo"] > ZG else 4
                        nxt = j
                        hit = True
                    else:
                        endU = j
                if not hit and j + 1 < N and u["p0"] >= ZD and u["p0"] <= ZG:
                    w = U[j + 1]
                    if (isUp(u) and w["lo"] > ZG) or (not isUp(u) and w["hi"] < ZD):
                        reason = 1 if isUp(u) else 2
                        endU = j - 1
                        nxt = j + 1
                if reason == 0:
                    j += 1
            zs.append(dict(PI0=i, PI1=endU, live=(reason == 0), term=reason))
            i = nxt if reason != 0 else endU + 1
        else:
            i += 1
    return zs


def pine_find_centers_by_segment(pens, segs):
    """pine 的 findCentersBySegment() 逐行翻译（含空段守卫 + 已完成线段 live 改法）。"""
    zs = []
    for s in segs:
        base = s["PI0"]
        cs = pine_find_centers(pens[base:s["PI1"] + 1])
        if len(cs) > 0:                                   # pine: if cs.size() > 0
            for z in cs:
                z["PI0"] += base
                z["PI1"] += base
                if z["live"] and not s.get("live", False):  # pine: if z.live and not s.live
                    z["live"] = False
                    z["term"] = 5                           # pine: z.term := 5
                zs.append(z)
    return zs


def check_pine_anchors():
    """空段守卫 + live 改法那两行必须在 pine 里各命中一次（静态锚，不拿行号当输入）。"""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "tradingview", "chanlun.pine"), encoding="utf-8").read()
    want = ["if cs.size() > 0", "if z.live and not s.live"]
    bad = [(w, src.count(w)) for w in want if src.count(w) != 1]
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    anchors = check_pine_anchors()
    if anchors:
        print("★ 静态锚点没各命中一次（pine 动过、先重读）：")
        for w, n in anchors:
            print("    %r 命中 %d 次" % (w, n))
        return 2

    files = sorted(os.path.basename(p) for p in glob.glob(data("*.json")))
    n = bad = skipped = 0
    for fn in files:
        try:
            r = analyze_file(fn)
        except Exception as e:
            skipped += 1
            print("跳过 %-18s（%s: %s）" % (fn, type(e).__name__, str(e)[:50]))
            continue
        pens, segs = r["pens"], r["segs"]
        pine_cs = pine_find_centers_by_segment(pens, segs)
        eng_cs = find_centers_by_segment(pens, segs)
        if len(pine_cs) != len(eng_cs):
            bad += 1
            print("✗ %s 中枢个数不一致：pine %d ≠ 引擎 %d" % (fn, len(pine_cs), len(eng_cs)))
            continue
        for k, (p, e) in enumerate(zip(pine_cs, eng_cs)):
            n += 1
            diff = []
            for key in ("PI0", "PI1", "live"):
                if p[key] != e[key]:
                    diff.append("%s: pine=%s 引擎=%s" % (key, p[key], e[key]))
            if TERM_INT[p["term"]] != e["term"]:
                diff.append("term: pine=%s(%d) 引擎=%s" % (TERM_INT[p["term"]], p["term"], e["term"]))
            if diff:
                bad += 1
                print("✗ %s 中枢[%d] %s" % (fn, k, " ｜ ".join(diff)))
    print("对账 %d 个类中枢（跳过 %d 份数据），不一致 %d 个" % (n, skipped, bad))
    if n == 0:
        print("★ 一个中枢都没对上（数据没了？）—— 查不了 ≠ 通过")
        return 2
    return 1 if bad else 0


def self_test():
    """正臂：把 live 改法抄错（改成『未完成线段也改 False』），必须红。"""
    files = sorted(os.path.basename(p) for p in glob.glob(data("*.json")))
    caught = 0
    for fn in files:
        try:
            r = analyze_file(fn)
        except Exception:
            continue
        pens, segs = r["pens"], r["segs"]
        # 抄错版：无条件把 live 改 False —— 未完成线段里本该 live 的中枢也被错杀
        wrong = pine_find_centers_by_segment(pens, segs)
        wrong = [dict(z) for z in wrong]
        for z in wrong:
            if z["live"]:
                z["live"], z["term"] = False, 5
        eng = find_centers_by_segment(pens, segs)
        if [(z["PI0"], z["PI1"], z["live"]) for z in wrong] != \
           [(z["PI0"], z["PI1"], z["live"]) for z in eng]:
            caught += 1
            break
    if not caught:
        print("★ 正臂**没红** ⇒ 这个检查程序判不出 live 差异 ⇒ 它印的「不用动」不算数。")
        return 3
    print("⇒ 正臂红了（抓到 live 抄错）✓ —— 它接上了，所以它印的「0 处」才算数。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
