#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""『逐根增量』与『一次性批量』的**逐前缀**等价检查（第①步：K线包含 + 分型）。

要回答的唯一问题：**把 chanlun.pine 从 barstate.islast 一次性重算改成逐根增量之后，
在第 k 根K线上，增量版的结果与批量版在 [0..k] 上跑出来的结果是不是逐字节相同？**

★ 为什么这个检查是这件事的正确尺子：
  卡的验收是「9 份真实数据＋随机行情上 0 不一致」。原先那个『不一致』量的是引擎 vs pine 的
  口径差；本卡改的是**算法形态**（批量 → 增量），所以真正要证的是**逐根等价**——
  在**每一根前缀**上都相等，而不只是全长上相等。全长相等是弱条件：一个"只在中间某根错、
  最后一根又凑回来"的实现照样过。逐前缀相等才能把它摁住。

★★ 射程（别把绿当更多的东西）：
  证的是『这份 Python 增量实现 == core/kline.py 的批量实现』。
  它**证不了** pine 里那段增量代码跟这份 Python 逐行相同 —— 那要靠人读（本仓没有 Pine 运行时）。
  pine 侧的对齐见同目录 `notes/pine-p3-parity.py` 的同一套做法：把 pine 的算法逐行抄成 Python。

用法：
    python3 notes/pine-incremental-parity.py              # 数据集 + 随机，全部
    python3 notes/pine-incremental-parity.py --self-test  # 正臂自证（见下）
    python3 notes/pine-incremental-parity.py --random 400 # 随机序列条数
退出码：
    0  全部前缀逐位相同
    1  ★ 有分歧（印出数据名 / 第几根 / 首个不同的标准化K线）
    2  跑不动（数据缺 / 引擎抛异常）—— **查不了 ≠ 通过**
    3  --self-test 的**正臂没红** ⇒ 这个检查程序本身不算数
"""
import argparse
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from core.kline import _contains, fractals, standardize            # noqa: E402

# 数据目录里这几个不是行情序列（注释/语料/子集）
SKIP = ("annot", "mag", "sub")


def load_bars(fn):
    """读一份数据成 [{"h":..,"l":..}, ...]。"""
    d = json.load(open(os.path.join(ROOT, "data", fn)))
    raw = d if isinstance(d, list) else d.get("bars", d.get("klines"))
    return [{"h": b.get("h", b.get("high")), "l": b.get("l", b.get("low"))} for b in raw]


class Incremental:
    """逐根增量版：K线包含处理 + 分型。**状态全在这几个字段里**，不回头看历史。

    与 `core/kline.py` 的 `_standardize_span()` 逐步对应：
      · 未定方向（started=False）：原算法要"找第一对不包含的相邻K线"才开始；
        增量版只留上一根（prev）＋本段第一根（seg_first），够用 ——
        因为"是否包含"只取决于**相邻**两根。
      · 已定方向：新K线只与 m[-1] 比。**包含 ⇒ 替换 m[-1]（长度不变）；不包含 ⇒ 追加**。
        ⇒ 一次 push 的代价是 O(1)，且**不触碰 m[-2] 及更早**（这是增量的合法性来源）。
      · 分型：只有靠近末尾的三格可能变，所以每次 push 只重算末尾那几格。
    """

    def __init__(self):
        self.m = []                 # 标准化序列
        self.fx = []                # 分型（只保留 k < len(m)-2 的部分，最后一格每次重算）
        self.started = False
        self.prev = None            # 还没定方向时的上一根 (h, l, i)
        self.seg_first = None       # 本段第一根原始K线 (h, l, i) —— 整段互相包含时要用
        self.i = -1
        self.grew = True            # 本次 push 是否让标准化序列**变长**（追加）还是原地合并

    def push(self, h, l):
        self.i += 1
        i = self.i
        L0 = len(self.m)
        if not self.started:
            if self.seg_first is None:
                self.seg_first = (h, l, i)
            if self.prev is None:
                self.prev = (h, l, i)
                return
            if _contains(self.prev[0], self.prev[1], h, l):
                self.prev = (h, l, i)               # 还在互相包含，继续等
                return
            self.m = [dict(h=self.prev[0], l=self.prev[1], i=self.prev[2],
                           ih=self.prev[2], il=self.prev[2]),
                      dict(h=h, l=l, i=i, ih=i, il=i)]
            self.started = True
            self.grew = True
            self._refx()
            return

        p, p2 = self.m[-1], self.m[-2]
        up = p["h"] > p2["h"] or (p["h"] == p2["h"] and p["l"] > p2["l"])
        if _contains(p["h"], p["l"], h, l):
            if up:                                  # 向上：两个端点都取高
                self.m[-1] = dict(h=max(p["h"], h), l=max(p["l"], l), i=i,
                                  ih=i if h > p["h"] else p["ih"],
                                  il=i if l > p["l"] else p["il"])
            else:                                   # 向下：两个端点都取低
                self.m[-1] = dict(h=min(p["h"], h), l=min(p["l"], l), i=i,
                                  ih=i if h < p["h"] else p["ih"],
                                  il=i if l < p["l"] else p["il"])
        else:
            self.m.append(dict(h=h, l=l, i=i, ih=i, il=i))
        self.grew = len(self.m) > L0
        self._refx()

    def _refx(self):
        """只重算**最后一格**分型 —— 窗口宽度是量出来的，不是猜的。

        对长度 L 的标准化序列，合法分型位是 k ∈ [1, L-2]（k 要能取到 m[k+1]）。
        一次 push 只可能动到最后一格，两种情形各自推一遍：
          · 合并（长度不变）：只有 m[L-1] 被替换 ⇒ 唯一受影响的是 k=L-2（它用到 m[L-1]）。
          · 追加（长度 L→L+1）：老的 k=L0-3 及更早都只看 m[L0-3..L0-1]，m[L0-1] 没变；
            新出现的 k = 新L-2 就是最后一格。
        ⇒ 受影响集合 = {最后一格}，宽度 1。

        ★ 这个"1"是**测出来的**：`--self-test` 里有一支正臂把窗口收窄成"只到 L-3"
          （正好漏掉最后一格），它必须红；我一开始按"留 3 格余量"写，那支臂反而**不红** ——
          不是臂写坏了，是**那个余量本来就是多余的**。宁可供着的余量，是没被量过的边界。

        ★ 另一条也是测出来的（`--self-test` 的负臂 StaleFx）：**合并不会改最后一格分型的取值。**
          机制：合并只会把 m[-1] 沿**它已经走的方向**推得更远（up 由 m[-2]/m[-1] 定，合并期间不变），
          而分型只问"谁高谁低"，推得更远不翻转比较 ⇒ 取值不变。
          ⇒ 但**别据此省掉这次重算**：我试过"合并时把最后一格删掉、不补回来"，那是**真缺陷**
            （把 m[-1] 合并前后方向存在的那一格分型直接删没了），臂当场红。
          ⇒ 结论：合并时**重算**是对的写法（幂等、白做一点活）；合并时**删除**是错的。
            这条我特意写下来，因为它长得像一次"免费的优化"。
        """
        L = len(self.m)
        self.fx = [f for f in self.fx if f["k"] < L - 2]
        for k in range(max(1, L - 2), L - 1):
            a, b, c = self.m[k - 1], self.m[k], self.m[k + 1]
            if b["h"] > a["h"] and b["h"] > c["h"] and b["l"] > a["l"] and b["l"] > c["l"]:
                self.fx.append(dict(k=k, i=b["ih"], type="top", price=b["h"]))
            elif b["l"] < a["l"] and b["l"] < c["l"] and b["h"] < a["h"] and b["h"] < c["h"]:
                self.fx.append(dict(k=k, i=b["il"], type="bot", price=b["l"]))

    def snapshot(self):
        if self.started:
            return self.m, self.fx
        if self.seg_first is None:
            return [], []
        h, l, i0 = self.seg_first                     # 整段互相包含 ⇒ 塌成第一根
        return [dict(h=h, l=l, i=i0, ih=i0, il=i0)], []


def key_m(m):
    return [(x["h"], x["l"], x["i"], x["ih"], x["il"]) for x in m]


def key_fx(f):
    return [(x["k"], x["i"], x["type"], x["price"]) for x in f]


def check_series(bars, name, step=1, label="prefix"):
    """逐前缀比。step>1 时抽稀（大数据集用）。返回 (检查了几个前缀, 首个分歧 or None)。"""
    inc = Incremental()
    checked = 0
    for k in range(len(bars)):
        inc.push(bars[k]["h"], bars[k]["l"])
        if (k + 1) % step:
            continue
        checked += 1
        gm, gfx = inc.snapshot()
        bm = standardize(bars[:k + 1], None)
        bfx = fractals(bm)
        if key_m(gm) != key_m(bm) or key_fx(gfx) != key_fx(bfx):
            first = None
            for j in range(min(len(gm), len(bm))):
                if key_m(gm)[j] != key_m(bm)[j]:
                    first = (j, gm[j], bm[j])
                    break
            return checked, dict(name=name, k=k + 1, gm=len(gm), bm=len(bm),
                                 gfx=len(gfx), bfx=len(bfx), first=first,
                                 label=label)
    return checked, None


def rand_bars(rng, n, tick):
    """随机行情：**故意贴着一个价格网格走**，让"相等"频繁出现 ——
    缠论的包含关系吃等号（`>=` / `<=`），等号那一片正是最容易写错的地方。"""
    px = rng.uniform(10, 500)
    out = []
    for _ in range(n):
        px = max(tick, px + rng.choice((-2, -1, -1, 0, 0, 1, 1, 2)) * tick)
        h = px + rng.choice((0, 0, tick, tick, 2 * tick))
        l = px - rng.choice((0, 0, tick, tick, 2 * tick))
        out.append({"h": round(h, 6), "l": round(l, 6)})
    return out


def run_self_test():
    """正臂：把增量版**故意改坏**，检查程序必须红。改坏的两个方向各来一支。

    这一支是必须的：没有它，"全部相同"有两个解释 ——
    ① 真的相同 ② 这个检查程序根本没接上（比如两边跑的是同一份数据）。
    """
    arms = []

    class BadDir(Incremental):
        """方向判据写反（用 < 而不是 >）⇒ 合并时端点取错方向。"""
        def push(self, h, l):
            self.i += 1
            i = self.i
            if not self.started:
                if self.seg_first is None:
                    self.seg_first = (h, l, i)
                if self.prev is None:
                    self.prev = (h, l, i)
                    return
                if _contains(self.prev[0], self.prev[1], h, l):
                    self.prev = (h, l, i)
                    return
                self.m = [dict(h=self.prev[0], l=self.prev[1], i=self.prev[2],
                               ih=self.prev[2], il=self.prev[2]),
                          dict(h=h, l=l, i=i, ih=i, il=i)]
                self.started = True
                self._refx()
                return
            p, p2 = self.m[-1], self.m[-2]
            up = p["h"] < p2["h"] or (p["h"] == p2["h"] and p["l"] < p2["l"])   # ← 反了
            if _contains(p["h"], p["l"], h, l):
                if up:
                    self.m[-1] = dict(h=max(p["h"], h), l=max(p["l"], l), i=i,
                                      ih=i if h > p["h"] else p["ih"],
                                      il=i if l > p["l"] else p["il"])
                else:
                    self.m[-1] = dict(h=min(p["h"], h), l=min(p["l"], l), i=i,
                                      ih=i if h < p["h"] else p["ih"],
                                      il=i if l < p["l"] else p["il"])
            else:
                self.m.append(dict(h=h, l=l, i=i, ih=i, il=i))
            self._refx()
    arms.append(("方向判据写反", BadDir))

    class BadFx(Incremental):
        """分型窗口**差一格**：认定"只有 k ≤ L-3 需要重算"，漏掉最后一格。

        这才是真边界：合并替换 m[-1] 时受影响的恰好是 k=L-2 那一格，
        漏掉它 ⇒ 旧分型留着不走、新的进不来 ⇒ 分型表与批量版分叉。
        """
        def _refx(self):
            L = len(self.m)
            self.fx = [f for f in self.fx if f["k"] < L - 3]      # ← 差一格
            for k in range(max(1, L - 3), L - 2):                 # ← 差一格
                a, b, c = self.m[k - 1], self.m[k], self.m[k + 1]
                if b["h"] > a["h"] and b["h"] > c["h"] and b["l"] > a["l"] and b["l"] > c["l"]:
                    self.fx.append(dict(k=k, i=b["ih"], type="top", price=b["h"]))
                elif b["l"] < a["l"] and b["l"] < c["l"] and b["h"] < a["h"] and b["h"] < c["h"]:
                    self.fx.append(dict(k=k, i=b["il"], type="bot", price=b["l"]))
    arms.append(("分型窗口差一格（漏最后一格）", BadFx))

    class StaleFx(Incremental):
        """从不作废旧分型（只在末尾追加）⇒ 合并改掉旧分型时它赖着不走。"""
        def _refx(self):
            L = len(self.m)
            for k in range(max(1, L - 2), L - 1):
                a, b, c = self.m[k - 1], self.m[k], self.m[k + 1]
                if b["h"] > a["h"] and b["h"] > c["h"] and b["l"] > a["l"] and b["l"] > c["l"]:
                    nf = dict(k=k, i=b["ih"], type="top", price=b["h"])
                elif b["l"] < a["l"] and b["l"] < c["l"] and b["h"] < a["h"] and b["h"] < c["h"]:
                    nf = dict(k=k, i=b["il"], type="bot", price=b["l"])
                else:
                    nf = None
                if nf and not any(f["k"] == k for f in self.fx):
                    self.fx.append(nf)
    arms.append(("从不作废旧分型（负臂：必须保持绿）", StaleFx, "expect_green"))


    rng = random.Random(20261002)
    series = [rand_bars(rng, 300, t) for t in (1.0, 0.5, 0.1)]
    ok = True
    for arm in arms:
        name, cls = arm[0], arm[1]
        expect_green = len(arm) > 2 and arm[2] == "expect_green"
        red = False
        for s in series:
            inc = cls()
            for k in range(len(s)):
                inc.push(s[k]["h"], s[k]["l"])
                gm, gfx = inc.snapshot()
                bm = standardize(s[:k + 1], None)
                bfx = fractals(bm)
                if key_m(gm) != key_m(bm) or key_fx(gfx) != key_fx(bfx):
                    red = True
                    break
        mark = "✓ 当场红" if red else "· 绿（预测如此）" if expect_green else "✗ **没红**（这个检查程序不算数）"
        print("   正臂 %-24s ⇒ %s" % (name, mark))
        if not expect_green:
            ok = ok and red
        elif red:
            print("      ↑ 我预测它绿，它红了 ⇒ **我的推理有误**，`_refx` 必须在合并时也重算。")
            ok = False
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--random", type=int, default=300, help="随机序列条数")
    a = ap.parse_args()

    if a.self_test:
        print("--self-test：把增量版故意改坏，检查程序必须红")
        return 0 if run_self_test() else 3

    fails, total_checked, datasets = [], 0, 0

    print("── 真实数据 ──")
    files = [f for f in sorted(os.listdir(os.path.join(ROOT, "data")))
             if f.endswith(".json") and not any(x in f for x in SKIP)]
    for fn in files:
        try:
            bars = load_bars(fn)
        except Exception as e:                                   # noqa: BLE001
            print("  !! %-22s 读不动：%s" % (fn, e))
            return 2
        if not bars:
            continue
        datasets += 1
        step = 1 if len(bars) <= 3000 else 13                    # 大的抽稀，小的全跑
        checked, bad = check_series(bars, fn, step)
        total_checked += checked
        if bad:
            fails.append(bad)
            print("  ✗ %-22s %5d 根 ｜ 分歧 @第 %d 根 ｜ 标准化K线 %d vs %d ｜ 分型 %d vs %d"
                  % (fn, len(bars), bad["k"], bad["gm"], bad["bm"], bad["gfx"], bad["bfx"]))
            if bad["first"]:
                j, g, b = bad["first"]
                print("      首个不同的标准化K线 @%d：增量 %s ／ 批量 %s" % (j, g, b))
        else:
            print("  ✓ %-22s %5d 根 ｜ 查了 %5d 个前缀" % (fn, len(bars), checked))

    print("── 随机行情（每个前缀都查，等号密集）──")
    rng = random.Random(20261002)
    rand_checked = 0
    for t in range(a.random):
        tick = rng.choice((0.1, 0.25, 0.5, 1.0, 2.0))
        n = rng.randint(40, 500)
        bars = rand_bars(rng, n, tick)
        checked, bad = check_series(bars, "rand#%d(tick=%s,n=%d)" % (t, tick, n))
        rand_checked += checked
        if bad:
            fails.append(bad)
            if len(fails) == 1:
                print("  ✗ %s ｜ 分歧 @第 %d 根" % (bad["name"], bad["k"]))
                if bad["first"]:
                    j, g, b = bad["first"]
                    print("      首个不同的标准化K线 @%d：增量 %s ／ 批量 %s" % (j, g, b))
    total_checked += rand_checked
    print("  ✓ %d 条随机序列 ｜ 查了 %d 个前缀" % (a.random, rand_checked))

    print("\n真实数据 %d 份 ｜ 前缀合计查了 %d 个 ｜ 分歧 %d 处" % (datasets, total_checked, len(fails)))
    if fails:
        print("⇒ **不一致**：增量版与批量版不是逐前缀相同。")
        return 1
    print("⇒ 0 不一致：在第 k 根上，增量版与『拿 [0..k] 重跑一遍』逐位相同。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
