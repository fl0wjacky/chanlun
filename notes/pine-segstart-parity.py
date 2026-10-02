# -*- coding: utf-8 -*-
"""把 `tradingview/chanlun.pine` 里**新加的那段**（线段起点三笔重叠守卫）逐行抄成 Python，
跟引擎对账（只读，不改 core/）。

为什么要有这个：Pine 在这台机器上**编译不了、跑不了**，而 `tools/pine_lockstep.py` 只回答
「引擎自 pine 上次改动以来变了没有」，**不回答「pine 和引擎算的是不是一回事」**。
这条守卫又特别刁：**真实行情上根本不触发**（段界由特征序列分型确认、本身已含重叠），
所以 lockstep 那 12 份数据**对它完全瞎** —— 移植得对不对，lockstep 一个字都不会说。

    pine 的 openingOverlaps() + 循环头守卫  ⟷  core/segment.py 的 _opening_overlaps() + build_segments()

做法：**照 pine 的源码逐行翻译**（`math.max` 套 `math.max` 就是三笔取交，`i += 1` + `continue`
就是「只前进一笔」），然后在**随机行情**上（真实行情打不出来，见上）比两边。

── ★ 它能证什么 / 不能证什么（两句分开，引用时别只引前半句）──────────────────
能证 —— 我**想写进 pine 的那个算法**与引擎一致：谓词在**每一笔位置**上判得一样，
        且「不满足就前进一笔」的跳过语义，与引擎实际产出的线段起点一致。
不能证 —— pine 的**语法/idiom 本身**能编译、能跑出同一个结果（那要 TradingView）。
        **我的翻译错了，这个脚本也会跟着一起错** —— 它比的是"我的翻译 vs 引擎"，
        不是"pine 运行时 vs 引擎"。有 TradingView 环境的人请优先真跑一遍。

用法：
    python3 notes/pine-segstart-parity.py              # 随机族 + 六份真实数据
    python3 notes/pine-segstart-parity.py --self-test  # 正臂：故意抄错，看它会不会红
退出码：
    0  0 处不一致
    1  ★ 有不一致（印出族名 / 种子 / 笔序号）
    2  跑不动 —— 引擎侧没有这条守卫（= 这一支还没合 Atlas 的 core 改动）**查不了 ≠ 通过**
    3  --self-test 的**正臂没红** ⇒ 这个检查程序本身不算数
    4  ★ 文件头那四个坐标锚点解不出来（改名／搬走／不再唯一）—— 报告里的指针失效
"""
import argparse
import hashlib
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.segment as S                                               # noqa: E402

# ★ 坐标 = **锚点**，不存行号。理由（@iris-64a1 2026-10-02 复核时逮到我四个常数全漂了）：
#   存下来的行号是这张表里**唯一会漂**的一半，而它漂到的落点往往看着很合理
#   （函数头、注释、空行）—— 比明显错的更误人，因为它不提示你去怀疑。
#   锚串在每个文件里都唯一（四个各命中 1 次，现量；连去掉行首 ^ 也仍然唯一），
#   所以锚点足以定位。**行号改成运行期算出来再印**，就没有"存着的那一半"可以漂了。
COORD_ANCHORS = (
    ("PINE_PREDICATE", "tradingview/chanlun.pine",
     r"^openingOverlaps\(array<Unit> P, int i\) =>", "谓词函数"),
    ("PINE_GUARD", "tradingview/chanlun.pine",
     r"^\s*if not openingOverlaps\(P, i\)", "调用点：守卫 + i += 1 + continue"),
    ("ENGINE_GUARD", "core/segment.py",
     r"^def _opening_overlaps\(", "引擎侧的同名谓词"),
    ("ENGINE_LOOP", "core/segment.py",
     r"^\s*if not _opening_overlaps\(pens, i\):", "循环头守卫那三行"),
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def blob_sha(path):
    """git 的 blob 哈希 —— 和 `git rev-parse HEAD:<path>` 直接可比（不是纯 sha1(内容)）。"""
    data = open(path, "rb").read()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def check_coords():
    """把四个锚点解成当前的 (文件:行号)，顺便说清读的是哪份字节。

    返回 (解不到的 [(名, 为什么)], 解出来的 [(名, rel, 行号, 说明)], 读过的 [(rel, 行数, blob)])。
    锚点必须**恰好命中 1 次** —— 0 次是代码改名/搬走了，≥2 次是它不再能定位。
    ★ 为什么连 blob 一起返回：@iris-64a1 2026-10-02 —— **坐标必须带 sha**，
      否则「我量过」量的是哪棵树都说不清。我今晚两次报错的根都是这个（一次把旧树的数
      当成 main 的、一次 rc=2 实际测的是自己那条支）。所以"读了谁的字节"跟结论同排印出。
    """
    drift, resolved, stamps, cache, unreadable = [], [], [], {}, {}
    for rel in dict.fromkeys(c[1] for c in COORD_ANCHORS):
        path = os.path.join(_ROOT, rel)
        try:
            text = open(path, encoding="utf-8").read()
            cache[rel] = text.splitlines()
            stamps.append((rel, len(cache[rel]), blob_sha(path)[:12]))
        except OSError as e:
            cache[rel] = []
            unreadable[rel] = str(e)
            stamps.append((rel, -1, "读不到（%s）" % e))
    for name, rel, anchor, desc in COORD_ANCHORS:
        if rel in unreadable:
            # ★ 这一格单说：文件压根没读进来时，不许印「锚点找不到（改名了？搬走了？）」
            #   —— 那是在对我从没读到的内容下判断。@iris-64a1 2026-10-02 指出这一格我没跑。
            drift.append((name, "**读不到** %s（%s）—— 不是「锚点在不在里面」，是这份文件没读进来"
                          % (rel, unreadable[rel])))
            continue
        hits = [i for i, l in enumerate(cache[rel], 1) if re.search(anchor, l)]
        if len(hits) == 1:
            resolved.append((name, rel, hits[0], desc))
        elif not hits:
            drift.append((name, "锚点在这份 %s 里**一处都找不到**（改名了？搬走了？）" % rel))
        else:
            drift.append((name, "锚点不再唯一：%s 里命中 %d 次（%s）—— 定位不了"
                          % (rel, len(hits), "、".join(map(str, hits)))))
    return drift, resolved, stamps


# ───────────── 以下：tradingview/chanlun.pine 的逐行翻译（别改成语义等价的"更好的写法"）─────────────

def openingOverlaps(P, i):                  # pine: openingOverlaps(array<Unit> P, int i) =>
    ok = False                              # pine: bool ok = false
    if i + 2 < len(P):                      # pine: if i + 2 < P.size()
        lo = max(max(P[i]["lo"], P[i + 1]["lo"]), P[i + 2]["lo"])      # pine: math.max 套 math.max
        hi = min(min(P[i]["hi"], P[i + 1]["hi"]), P[i + 2]["hi"])      # pine: math.min 套 math.min
        ok = lo < hi                        # pine: ok := lo < hi
    return ok                               # pine: ok


def pineSkipHead(P):                        # pine: `if not openingOverlaps(P, i)` / `i += 1` / `continue`
    i = 0                                   # pine: i = 0（buildSegments 的循环变量）
    n = len(P)
    while i + 2 < n and not openingOverlaps(P, i):
        i += 1                              # pine: i += 1  —— **只前进一笔**，不是跳到下一处候选
    return i


def pinePredict(P):
    """pine 的循环头会跳到哪一笔开始，然后从那里照常走（引擎的段生成逻辑没被我抄，也不该抄）。"""
    j = pineSkipHead(P)
    if j + 2 >= len(P):
        return []
    orig = S._opening_overlaps
    S._opening_overlaps = lambda pens, i: True          # ← 关掉引擎的守卫 = 改前行为
    try:
        segs = S.build_segments(P[j:])
    finally:
        S._opening_overlaps = orig
    return [(s["PI0"] + j, s["PI1"] + j, s["dir"]) for s in segs]


# ─────────────────────────────── 随机行情 ───────────────────────────────
# ★ 种子写死，不提供 --seed：读数要能被别人复跑出同一个数。
SEEDS = [101, 202, 303, 404, 505]

DATAS = ["zec15.json", "zec_1h.json", "zec_4h.json", "btc_4h.json",
         "aaplusdt_4h.json", "aaplusdt_30m.json"]


def _zigzag(pts):
    """一串交替的极值点 → 笔（每笔 hi/lo = 两端点的 max/min，与引擎一致）。"""
    pens = []
    idx = 0
    for k in range(len(pts) - 1):
        p0, p1 = pts[k], pts[k + 1]
        if p0 == p1:
            continue
        pens.append(dict(i0=idx, i1=idx + 3, x0=idx, x1=idx + 3, p0=p0, p1=p1,
                         hi=max(p0, p1), lo=min(p0, p1)))
        idx += 3
    return pens


def gen_walk(rng, n, step_lo, step_hi, down_drift):
    """族 A／B：随机游走折线。down_drift > 1 ⇒ 下行笔更长 ⇒ 越来越不重叠（专门打守卫）。"""
    pts, price, up = [100.0], 100.0, True
    for _ in range(n):
        s = rng.uniform(step_lo, step_hi)
        price += s if up else -s * down_drift
        pts.append(round(price, 4))
        up = not up
    return _zigzag(pts)


def gen_adjacent_only(rng, n):
    """族 C：**相邻两笔各自重叠、三笔却没有公共段** —— 显式构造，
    让「三重取交」与「只查相邻」在这个族上**真的分得开**（随机游走里这个差别会淹没）。

    构造：上笔 [a, X]、下笔 [Y, X]、上笔 [Y, Z]，取 a > Y 且 Z ≤ a ⇒ max(a,Y)=a ≥ Z = 顶点
    ⇒ 公共段为空；而 [a,X]∩[Y,X]=[a,X]≠∅、[Y,X]∩[Y,Z]=[Y,Z]≠∅，相邻两组都重叠。
    """
    pts, k = [100.0], 0
    while k < n:
        a = pts[-1]
        X = a + rng.uniform(1.0, 4.0)                  # 上笔顶
        Y = a - rng.uniform(1.0, 4.0)                  # 回撤到 Y（低于 a）
        Z = rng.uniform(Y + 1e-6, a)                   # 再上到 Z ≤ a ⇒ 三笔无公共段
        pts += [round(X, 4), round(Y, 4), round(Z, 4)]
        k += 3
    return _zigzag(pts)


def mutate_skip(P, pred):
    i, n = 0, len(P)
    while i + 2 < n and not pred(P, i):
        i += 1
    return i


# 正臂用的三个"故意抄错"：每一个都该让脚本变红
MUTANTS = {
    "只查相邻两笔（漏三重）":
        lambda P, i: (i + 2 < len(P) and
                      P[i]["lo"] < P[i + 1]["hi"] and P[i + 1]["lo"] < P[i]["hi"] and
                      P[i + 1]["lo"] < P[i + 2]["hi"] and P[i + 2]["lo"] < P[i + 1]["hi"]),
    "边界写成 <=（非严格）":
        lambda P, i: (i + 2 < len(P) and
                      max(max(P[i]["lo"], P[i + 1]["lo"]), P[i + 2]["lo"]) <=
                      min(min(P[i]["hi"], P[i + 1]["hi"]), P[i + 2]["hi"])),
    "照 pine 抄但漏掉守卫（改前行为）":
        lambda P, i: True,
}


def run(verbose=True, mutate=None):
    total_i = total_pred = total_seg = 0
    worst = None
    for seed in SEEDS:
        rng = random.Random(seed)
        cases = [
            ("A 随机游走", gen_walk(rng, 60, 0.5, 5.0, 1.0)),
            ("B 下行加速（打守卫）", gen_walk(rng, 60, 0.5, 3.0, 1.8)),
            ("C 相邻重叠无公共段", gen_adjacent_only(rng, 60)),
        ]
        for name, pens in cases:
            if len(pens) < 6:
                continue
            pred = mutate or openingOverlaps
            n_i = len(pens) - 2
            pred_bad = sum(1 for i in range(n_i) if pred(pens, i) != S._opening_overlaps(pens, i))
            j = mutate_skip(pens, pred)
            want = []
            if j + 2 < len(pens):
                orig = S._opening_overlaps
                S._opening_overlaps = lambda p, i: True
                try:
                    want = [(s["PI0"] + j, s["PI1"] + j, s["dir"]) for s in S.build_segments(pens[j:])]
                finally:
                    S._opening_overlaps = orig
            got = [(s["PI0"], s["PI1"], s["dir"]) for s in S.build_segments(pens)]
            seg_bad = 0 if want == got else 1
            total_i += n_i
            total_pred += pred_bad
            total_seg += seg_bad
            if (pred_bad or seg_bad) and worst is None:
                worst = (seed, name)
            if verbose:
                print("  %-22s seed=%-4d 笔 %3d ｜ 查 %3d 处 ｜ 谓词不一致 %d ｜ 段不一致 %d%s"
                      % (name, seed, len(pens), n_i, pred_bad, seg_bad,
                         "   ← 第一处不一致" if worst == (seed, name) else ""))
    return total_i, total_pred, total_seg, worst


def run_real(verbose=True):
    try:
        from core.analyze import analyze_file
    except Exception as e:                                        # pragma: no cover
        print("  （真实数据这一层跳过：%s）" % e)
        return 0, 0, 0
    ti = tp = ts = 0
    for fn in DATAS:
        try:
            pens = analyze_file(fn)["pens"]
        except Exception as e:                                    # pragma: no cover
            print("  %-22s 读不了：%s" % (fn, e))
            continue
        if len(pens) < 6:
            continue
        n_i = len(pens) - 2
        pred_bad = sum(1 for i in range(n_i)
                       if openingOverlaps(pens, i) != S._opening_overlaps(pens, i))
        # 守卫在**整条**序列上会不会触发（不止头部）：这正是"真实行情打不出来"的那一栏
        hits = sum(1 for i in range(n_i) if not openingOverlaps(pens, i))
        head = pineSkipHead(pens)
        orig = S._opening_overlaps
        S._opening_overlaps = lambda p, i: True
        try:
            want = [(s["PI0"] + head, s["PI1"] + head, s["dir"])
                    for s in S.build_segments(pens[head:])] if head + 2 < len(pens) else []
        finally:
            S._opening_overlaps = orig
        got = [(s["PI0"], s["PI1"], s["dir"]) for s in S.build_segments(pens)]
        seg_bad = 0 if want == got else 1
        ti += n_i
        tp += pred_bad
        ts += seg_bad
        if verbose:
            print("  %-22s 笔 %4d ｜ 查 %4d 处 ｜ 守卫不满足 %d 处（头部跳过 %d 笔）"
                  " ｜ 谓词不一致 %d ｜ 段不一致 %d" % (fn, len(pens), n_i, hits, head, pred_bad, seg_bad))
    return ti, tp, ts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true", help="正臂：故意抄错，验证它会红")
    a = ap.parse_args()

    if not hasattr(S, "_opening_overlaps"):
        print("!! core/segment.py 里**没有** _opening_overlaps —— 这一支还没合 Atlas 的 core 改动。")
        print("   查不了 ≠ 通过：这个脚本要跟**带守卫的引擎**比。")
        return 2

    if a.self_test:
        print("正臂（故意抄错，每一支都**必须**变红）：")
        ok = True
        for name, mut in MUTANTS.items():
            _, p, s, _ = run(verbose=False, mutate=mut)
            red = (p + s) > 0
            print("  %-26s ⇒ 不一致 %d 处  %s" % (name, p + s, "✓ 红了" if red else "✗ **没红**"))
            ok = ok and red
        if not ok:
            print("!! 有正臂没红 ⇒ 这个检查程序没接上，它的 0 不算数。")
            return 3
        print("⇒ 三支正臂全红，检查程序是活的。")
        return 0

    drift, resolved, stamps = check_coords()
    if drift:
        print("!! 锚点解不出来 —— 这份报告的指针失效了：")
        for name, why in drift:
            print("   %-15s ⇒ %s" % (name, why))
        print("   ⇒ **不算绿**：读者会照这份报告去核对，却找不到指的那个东西。")
        for rel, n, sh in stamps:
            print("   （我读的是：%s %s）"
                  % (rel, ("%d 行 blob %s" % (n, sh)) if n >= 0 else sh))
        return 4

    d = {n: "%s:%d" % (rel, ln) for n, rel, ln, _ in resolved}
    print("照 pine %s ／ %s 逐行翻译，对 core/segment.py 的 %s ／ %s"
          % (d["PINE_PREDICATE"], d["PINE_GUARD"], d["ENGINE_GUARD"], d["ENGINE_LOOP"]))
    for rel, n, sh in stamps:
        print("   ★ 我读的是这份字节：%-28s %4s 行  blob %s" % (rel, n, sh))
    for _, rel, ln, desc in resolved:
        print("   · %s:%d —— %s" % (rel, ln, desc))
    print("\n【随机行情】（真实行情打不出这条守卫，所以必须有随机）")
    ti, tp, ts, worst = run()
    print("  小计：查 %d 处 ｜ 谓词不一致 %d ｜ 段不一致 %d" % (ti, tp, ts))
    if worst:
        print("  第一处不一致：seed=%d 族=%s" % worst)

    print("\n【六份真实数据】")
    ri, rp, rs = run_real()
    print("  小计：查 %d 处 ｜ 谓词不一致 %d ｜ 段不一致 %d" % (ri, rp, rs))

    bad = tp + ts + rp + rs
    print("\n不一致合计 = %d" % bad)
    if bad:
        print("⇒ 有分歧，逐条查（族名 + 种子在上面）。")
        return 1
    print("⇒ 0 不一致。**注意射程**：这只说明「我抄进 pine 的算法」与引擎一致，"
          "不说明 pine 能编译、能跑出同一结果（那要 TradingView）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
