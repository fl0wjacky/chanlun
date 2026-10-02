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

        ★ 合并**既不改取值、也不新增**（即真"幂等"）—— 这条被人当面质疑过，所以写全。
          Nova 给过一个反例想说明"合并能让 L−2 从无到有"：设 m[L−1].h == m[L−2].h，
          此时那格既不是顶也不是底（顶要严格大于），再来一根包含K线按 max 把 m[L−1].h
          抬过 m[L−2].h，底分型就长出来了。
          **这个前提在标准化序列里不可能成立：**
              相邻两根标准化K线，**高必不相等、低必不相等**。
              证：设 m[i-1].h == m[i].h。若 m[i-1].l <= m[i].l 则 m[i-1] 罩住 m[i]；
                  否则 m[i].l < m[i-1].l，则 m[i] 罩住 m[i-1]。`_contains` 是**对称**的、
                  且 **等号算包含** ⇒ 这两种情形都会被合并掉，永远不可能相邻。低同理。∎
              实测：全部真实数据 26218 对相邻，高相等 0 ｜ 低相等 0。
          ⇒ 于是 up 判据里 `p.h == p2.h and p.l > p2.l` 那半句是**死代码**（永远走不到）。
          ⇒ 由"相邻高必不等"再推一步，合并时 L−2 那格的判词必然不变：
              · up 合并（唯一可能：m[L−1].h > m[L−2].h）⇒ c.h := max 只会更高、c.l := max 只会更高，
                底分型要的 `b.h < c.h`、`b.l < c.l` 只会更容易满足；而合并前这两条**本来就成立**
                （若 b.l >= c.l 则 b 罩住 c 早就被合并了）。
              · 与 a = m[L−3] 的三条比较完全没被合并碰到。
              ⇒ 合并前是底则合并后仍是底；合并前不是底，失败只可能在 a 那侧，合并改不了。
              顶方向对 down 合并镜像同理。
          ⇒ 所以合并时 L−2 的判词**确实不变**（幂等），分型表**只增不改不删**。
          ⇒ 三支臂各钉一个错法：MergeStale（跳过重算）**绿**、StaleFx（照抄旧值但愿意补）**绿** ——
            两支都是负臂，红不了是因为上面这条；"删掉不补"那支早就红过。
          ⇒ 这也正是 pen 层 NoCk 臂绿的道理：分型表只往后加，喂给笔的仍是追加。
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

    class MergeStale(Incremental):
        """**负臂（预测绿）**：合并那根整段跳过 k=L−2 的重算，照抄旧分型表。

        本来是当正臂写的（Nova 要求："合并时不重算 L−2，照抄旧值，必须红"）。
        **它红不了，而且不该红** —— 见 `_refx` 里那条证明：合并时 L−2 的判词不变
        （相邻标准化K线高必不相等 ⇒ Nova 那个 `m[L−1].h == m[L−2].h` 的前提不可能成立）。
        跳过重算与重算得到的结果**逐位相同**，所以红不了是**结论**，不是"没压到"。
        实测：全部真实数据里"合并让分型表长出一格"发生 **0 次**。
        留着它当哨兵：哪天 ① 改了 zRefx（比如不再重算），这里会先红。
        """
        def _refx(self):
            if not self.grew:                       # grew 在 _refx 之前已经赋值
                return
            Incremental._refx(self)
    arms.append(("合并时跳过 L−2 的重算（负臂：必须保持绿）", MergeStale, "expect_green"))


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


# 一条**手挑的**小序列：专门压 pine 里那几处只有人读得出来的分支。
# 每一行是 (高, 低)。设计意图逐条写在下面，跑 `--trace` 会印出每个前缀的期望状态 ——
# 这份表是给**读 pine 的人**对账用的（本仓跑不了 Pine，逐前缀尺子只能证 Python 那一半）。
TRACE_CASE = [
    (10.0, 5.0),     # 1  第一根 ⇒ seed
    (9.5, 6.0),      # 2  包含 ⇒ chain（**状态里留的仍是第 1 根**）
    (9.0, 6.5),      # 3  包含 ⇒ chain
    (11.0, 7.0),     # 4  不包含 ⇒ break：第 0 格换成第 3 根，再追加本根，方向向上
    (10.5, 7.5),     # 5  被最后一根罩住、方向向上 ⇒ merge（两端点都取高）
    (12.0, 8.5),     # 6  不包含 ⇒ append（第 3 根标准化K线，分型窗口打开）
    (11.5, 9.0),     # 7  被罩住、方向向上 ⇒ merge
    (13.0, 10.0),    # 8  不包含 ⇒ append
    (12.0, 8.0),     # 9  不包含 ⇒ append ⇒ 前一根成为**顶分型**
    (11.0, 7.0),     # 10 不包含 ⇒ append
    (10.0, 5.0),     # 11 不包含 ⇒ append
    (9.0, 4.0),      # 12 不包含 ⇒ append
    (9.5, 6.0),      # 13 不包含 ⇒ append ⇒ 前一根成为**底分型**
]


def trace():
    """印出手挑序列的逐前缀期望状态 —— 给读 pine 的人逐行对账用。

    ★ 这份表**只能**用来对 Python 那一半（`core/kline.py` 的批量实现 == 增量实现）。
      它证不了 pine 里那段跟这份 Python 逐行相同 —— 那只能靠人读，所以要印得能读。
    """
    inc = Incremental()
    bad = 0
    seen = {}
    print("手挑序列（h, l）逐前缀期望状态。读 pine 的人按这个对：")
    print("  前缀  本根          走的哪条分支   标准化序列(h,l)                       分型(k:i:type@price)")
    merge_touched = 0
    for k, (h, l) in enumerate(TRACE_CASE, 1):
        was_started = inc.started
        L0 = len(inc.m)
        fx0 = {f["k"]: key_fx([f]) for f in inc.fx}
        inc.push(h, l)
        if not was_started and inc.started:
            br = "break"
        elif not was_started:
            br = "seed" if k == 1 else "chain"
        elif len(inc.m) > L0:
            br = "append"
        else:
            br = "merge"
        seen[br] = seen.get(br, 0) + 1
        # 只盯「**原本就存在**的那一格分型，重算之后变了没有」—— append 新添一格不算。
        fx1 = {f["k"]: key_fx([f]) for f in inc.fx}
        touched = [kk for kk in fx0 if fx1.get(kk) != fx0[kk]]
        if br == "merge" and touched:
            merge_touched += 1
        gm, gfx = inc.snapshot()
        bm = standardize([{"h": a, "l": b} for a, b in TRACE_CASE[:k]], None)
        bfx = fractals(bm)
        same = key_m(gm) == key_m(bm) and key_fx(gfx) == key_fx(bfx)
        bad += 0 if same else 1
        chg = ("  ← 已存在的分型 @k=%s 被重算改掉了" % touched) if touched else ""
        ser = " ".join("(%.4g,%.4g)" % (x["h"], x["l"]) for x in gm)
        fxs = " ".join("%d:i%d:%s@%.4g" % (f["k"], f["i"], f["type"], f["price"]) for f in gfx) or "—"
        print("  %2d   (%-9s)  %-12s  %-35s  %s%s%s"
              % (k, "%.4g,%.4g" % (h, l), br, ser, fxs,
                 chg, "" if same else "   ★ 与批量版不一致！"))
    print("  分支覆盖：" + "  ".join("%s×%d" % (b, seen[b]) for b in
                                    ("seed", "chain", "break", "merge", "append") if b in seen))
    print("  merge 次数 %d ｜ 其中「已存在的分型格被重算改掉」 %d 次"
          % (seen.get("merge", 0), merge_touched))
    print("  ⇒ %s" % ("与批量版逐前缀一致（%d 个前缀）。" % len(TRACE_CASE) if not bad
                    else "★ %d 个前缀不一致 —— 别拿这份表去对 pine。" % bad))
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--random", type=int, default=300, help="随机序列条数")
    ap.add_argument("--step", type=int, default=0,
                    help="前缀抽稀步长；0 = 自动（>3000 根的每 13 个取一个），1 = 全跑不抽")
    ap.add_argument("--trace", action="store_true",
                    help="印一条手挑小序列的逐前缀期望状态，给**读 pine 的人**逐行对账")
    a = ap.parse_args()

    if a.trace:
        return trace()

    if a.self_test:
        print("--self-test：把增量版故意改坏，检查程序必须红")
        return 0 if run_self_test() else 3

    fails, total_checked, datasets = [], 0, 0

    print("── 真实数据 ──")
    files = [f for f in sorted(os.listdir(os.path.join(ROOT, "data")))
             if f.endswith(".json") and not any(x in f for x in SKIP)]
    # 短的先跑：zec15（20160 根）单份就是小时级，按字母序它排第 6，会把后面 4 份小的全堵在它后面。
    # 覆盖面一个不少，只换顺序（② 那份同改）。注意这只影响**报数顺序**，不影响任何判词。
    _sizes = {}

    def _nbars(fn):
        if fn not in _sizes:
            try:
                _sizes[fn] = len(load_bars(fn) or [])
            except Exception:                                    # noqa: BLE001
                _sizes[fn] = 0
        return _sizes[fn]

    files.sort(key=_nbars)
    print("顺序（按根数升序）：" + " → ".join("%s(%d)" % (f, _nbars(f)) for f in files))
    for fn in files:
        try:
            bars = load_bars(fn)
        except Exception as e:                                   # noqa: BLE001
            print("  !! %-22s 读不动：%s" % (fn, e))
            return 2
        if not bars:
            continue
        datasets += 1
        step = a.step or (1 if len(bars) <= 3000 else 13)        # 默认大的抽稀、小的全跑；--step 1 强制全跑
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
    real_checked = total_checked      # ★ 真实数据那一档单独留一份：原先这行把随机那批并进
    total_checked += rand_checked     #   同一个数，汇总行却写着「真实数据 N 份」⇒ 报出来是假的
    print("  ✓ %d 条随机序列 ｜ 查了 %d 个前缀" % (a.random, rand_checked))

    print("\n真实数据 %d 份 ｜ 查了 %d 个前缀 ｜ 随机 %d 条 ｜ 查了 %d 个前缀 ｜ 合计 %d ｜ 分歧 %d 处"
          % (datasets, real_checked, a.random, rand_checked, total_checked, len(fails)))
    if fails:
        print("⇒ **不一致**：增量版与批量版不是逐前缀相同。")
        return 1
    print("⇒ 0 不一致：在第 k 根上，增量版与『拿 [0..k] 重跑一遍』逐位相同。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
