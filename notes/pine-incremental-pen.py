# -*- coding: utf-8 -*-
"""第②步（笔逐根）的尺子：**逐前缀**比「增量版笔」与 `core/pen.py` 的批量版。

和 ① 那份（pine-incremental-parity.py）同一条规矩：不比全长，比**每一根前缀**。
全长相等是弱条件 —— 中间某根错、最后一根凑回来照样过。

## 增量版的形状（第②步）

**pine 里跑的是 `Guarded`** —— 无检查点的 O(1) 守卫版；全量验收默认 `--impl Guarded`。
`IncPens`（检查点版）留作对照臂：两者同解，但它每根复制整份快照（seq 能到上千），
正是这张卡要干掉的那种写法，**不进 pine**。

`build_pens` 只有一个状态：`(seq, pend)`。它对分型表逐个 `feed`。`feed` 会**往回改**
（`fix_start`：`seq[:] = seq[:j+1] + [P]`，j 可以到 0），也会重喂一段旧分型。所以
「加一个新分型只动尾巴」**不是**代码看起来那样 —— 我先量过才敢写
（notes/pen-reach-probe.py：回溯中位 1、p99 2、最大 5）。**但那个 5 是量出来的，不是上限**，
所以正确性**不押在它上面**：守卫三条，任一条对不上就走第 3 条**从空整段重算**。

    守卫 1  长度没变、尾分型签名也没变      ⇒ 无事可做
    守卫 2  长了一格 **且旧尾巴签名没变**    ⇒ 只喂新那一个（O(1) 摊还）
    守卫 3  其余（缩了 / 跳变 / 旧尾巴被改） ⇒ 从空重算，不在旧状态上猜

守卫 2 里那次签名比较是**必须的**，不是保险：只比长度的话，「旧尾巴被改 + 又长一格」
长度照样对得上，可被改的那一格得重喂。`done == 0` 时没有旧尾巴可比（m 必为 1）。

`IncPens` 的检查点形状（仅供对照）：喂最后一个分型**之前**的 (seq, pend) 快照，
恢复后顺序重喂；分型表缩了不止一格 ⇒ 从空重算。回溯深度只决定代价，不决定对不对。

## 这份尺子不证什么

它证「这份 Python 增量实现 == `core/pen.py` 的批量实现」。它**证不了** pine 里那段
跟这份 Python 逐行相同 —— 本仓没有 Pine 运行时，那一步只能靠人读。

用法：
    python3 notes/pine-incremental-pen.py                 # 全部数据 × 每个前缀（不抽稀）
    python3 notes/pine-incremental-pen.py --self-test     # 正臂：改坏必须红
    python3 notes/pine-incremental-pen.py --max-bars 800  # 只跑前 N 根（调着用）
退出码：0 全同 ｜ 1 有分歧 ｜ 2 跑不动 ｜ 3 --self-test 的正臂没红
"""
import argparse
import importlib.util
import io
import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from core.kline import standardize, fractals, quantize      # noqa: E402
from core.pen import build_pens                             # noqa: E402

SKIP = ("annot", "mag", "sub")                              # data/ 里不是K线序列的几份


def _load_kline_incremental():
    """把 ① 那份里的 Incremental 借过来（文件名带连字符，不能直接 import）。"""
    p = os.path.join(HERE, "pine-incremental-parity.py")
    spec = importlib.util.spec_from_file_location("inc_kline", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Incremental


IncKline = _load_kline_incremental()


# ───────────────────────── 增量笔 ─────────────────────────
class IncPens:
    """`core/pen.py::build_pens` 的逐前缀增量版。状态 = (seq, pend) + 一个完整快照。

    与 `build_pens` 里那几个局部函数（far/beyond/extreme/pen_ok/fix_start/feed）
    逐行对应 —— 名字加下划线只是为了挂在类上。
    """

    def __init__(self, rule="old", min_gap=4):
        self.rule = rule
        self.min_gap = min_gap
        self.std = []
        self.fxk = []                 # 与 std 等长：k -> 分型 或 None
        self.seq = []
        self.pend = None
        self.ck = None                # (list(seq), pend) = state(len(fx)-1)
        self.ck_m = -1                # 快照对应「喂了几个分型」
        self.rebuilds = 0             # 从空重算了几次（代价指标，不是正确性）
        self.cklen = 0                # 快照里 seq 的长度合计（代价指标）

    # ---- core/pen.py 的局部函数，逐行搬过来 ----
    def _far(self, a, b):
        if self.rule == "old":
            return b["k"] - a["k"] >= self.min_gap
        return b["k"] - a["k"] >= 3 and abs(b["i"] - a["i"]) >= 4

    def _beyond(self, f, g):
        return f["price"] > g["price"] if f["type"] == "top" else f["price"] < g["price"]

    def _extreme(self, f, k0, k1):
        if f["type"] == "top":
            return f["price"] >= max(self.std[k]["h"] for k in range(k0, k1 + 1))
        return f["price"] <= min(self.std[k]["l"] for k in range(k0, k1 + 1))

    def _pen_ok(self, a, b):
        return self._far(a, b) and self._extreme(a, a["k"], b["k"]) and self._extreme(b, a["k"], b["k"])

    def _refeed(self, k0, k1):
        """端点换了 ⇒ 其后的分型要对着新端点重新看一遍。core/pen.py 里两处一模一样，这里合一。"""
        for k in range(k0, k1 + 1):
            x = self.fxk[k]
            if x:
                self._feed(x)

    def _fix_start(self):
        seq = self.seq
        if len(seq) < 2:
            return
        a, g = seq[-2], seq[-1]
        if self._extreme(a, a["k"], g["k"]):
            return
        inner = [self.fxk[k] for k in range(a["k"] + 1, g["k"])
                 if self.fxk[k] and self.fxk[k]["type"] == a["type"]]
        P = (max if a["type"] == "top" else min)(inner, key=lambda f: f["price"]) if inner else None
        for j in range(len(seq) - 3, -1, -1):
            e = seq[j]
            if P is not None and e["type"] == g["type"] and e["k"] < P["k"] \
                    and self._pen_ok(e, P) and self._pen_ok(P, g):
                seq[:] = seq[:j + 1] + [P]
                self.pend = None
                self._refeed(P["k"] + 1, g["k"])
                return
            if e["type"] == a["type"] and j <= len(seq) - 4 and self._pen_ok(e, g):
                seq[:] = seq[:j + 1] + [g]
                return

    def _feed(self, f):
        seq = self.seq
        if not seq:
            seq.append(f)
            return
        last = seq[-1]
        if f["type"] == last["type"]:
            if not self._beyond(f, last):
                return
            if self.pend is not None and (len(seq) < 3 or not self._beyond(last, seq[-3])):
                P = self.pend
                self.pend = None
                seq.pop()
                seq[-1] = P
                self._fix_start()
                self._refeed(P["k"] + 1, f["k"])
                return
            seq[-1] = f
            self.pend = None
            self._fix_start()
            return
        if self._far(last, f) and self._extreme(f, last["k"], f["k"]):
            seq.append(f)
            self.pend = None
            return
        if not self._far(last, f) and len(seq) >= 2 and self._beyond(f, seq[-2]) \
                and (self.pend is None or self._beyond(f, self.pend)):
            self.pend = f

    # ---- 快照 / 恢复 ----
    def _snapshot(self):
        return (list(self.seq), self.pend)

    def _restore(self, snap):
        self.seq = list(snap[0])
        self.pend = snap[1]

    def _rebuild_to(self, fx, t):
        """从空喂 fx[0..t-1]，并把结果存成快照。只在快照对不上任何前缀时用。"""
        self.rebuilds += 1
        self.seq, self.pend = [], None
        for i in range(t):
            self._feed(fx[i])
        self.ck = self._snapshot()
        self.ck_m = t
        self.cklen += len(self.ck[0])

    def update(self, std, fx):
        """把状态推进到「std + fx 这个前缀」。返回是否重算过。"""
        self.std = std
        self.fxk = [None] * len(std)
        for f in fx:
            self.fxk[f["k"]] = f
        m = len(fx)
        if m == 0:
            self.seq, self.pend, self.ck, self.ck_m = [], None, None, -1
            return False
        # ① 把快照对齐到「喂完前 m-1 个分型」
        if self.ck is None:
            self._rebuild_to(fx, m - 1)
        elif self.ck_m == m - 1:                     # 同长（最后一格被改）⇒ 快照不动
            pass
        elif self.ck_m == m - 2:                     # 长了一格 ⇒ 上一轮的 state 正是 state(m-1)
            self.ck = self._snapshot()
            self.ck_m = m - 1
        else:                                        # 缩了（或跳变）⇒ 快照不再对应任何前缀
            self._rebuild_to(fx, m - 1)
        # ② 从快照出发，重喂最后一个分型
        self._restore(self.ck)
        self._feed(fx[m - 1])
        return True

    def pens(self):
        return _pens_of(self.seq)

    def seqkey(self):
        return [(f["k"], f["i"], f["type"], f["price"]) for f in self.seq]


def _pens_of(seq):
    """与 core/pen.py::_pens_of 同义（只要参与比对的那几个字段）。"""
    out = []
    for t in range(len(seq) - 1):
        a, b = seq[t], seq[t + 1]
        out.append((a["i"], b["i"], a["k"], b["k"], a["price"], b["price"]))
    return out


class ShallowCk(IncPens):
    """**注意：这支红了，但红的不是"回溯深度"。**

    它把快照里的 seq 截成最后一格 —— 恢复之后笔的历史整个没了。所以它红是因为
    **状态被扔了**，跟 fix_start 要回溯多深毫无关系。留着只当"状态丢了当然要红"的哨兵，
    别拿它当"深度臂"用。
    """

    def _snapshot(self):
        return (list(self.seq)[-1:], self.pend)


class NoCk(IncPens):
    """**负臂（预测绿）**：完全没有检查点 —— 直接在上一轮的状态上喂新分型，从不回退。

    为什么它本来就该绿（不是"没压到"）：① 的 `zRefx` 只会**追加**分型。
        · `zH.size() = L` 单调不减，分型的 k ≤ L−2；
        · **新增**（L→L+1）：旧分型的 k ≤ (L+1)−3 < (L+1)−2 ⇒ pop 条件 `k ≥ L−2` 打不到 ⇒ 旧格不动；
        · **合并**（L 不变）：只重算 k = L−2 那一格，判词**确实不变**。理由不是"取 min 更保险"，
          而是**相邻标准化K线的高必不相等**（等号算包含 ⇒ 相等就被合并了，不可能相邻，
          实测 26218 对里 0 例），于是 up/down 合并只会把 m[L−1] 沿判词有利的方向推，
          而合并前那两条比较本来就成立。完整证明写在 ① 那份的 `Incremental._refx` 里。
    （Nova 提过一个反例：m[L−1].h == m[L−2].h 时那格不是分型，来根包含K线就"长出来"了。
      那个前提不可能成立 —— 高相等的相邻标准化K线会被合并掉。见 ① 的证明。）
    在真实 9 份 + 随机 60 条上量过：**52495 次 push，revised 0、shrank 0**。
    ⇒ 分型表没有"被改的前缀"，检查点永远不必回退。绿是结论，不是漏测。

    快照**照样留在设计里**：一次几十个整数、每个分型一次，代价可忽略；换来的好处是
    ② 不再依赖"① 只会追加"这条不变量 —— 以后谁改了 `zRefx`，这里不会静默坏掉。
    """

    def update(self, std, fx):
        self.std = std
        self.fxk = [None] * len(std)
        for f in fx:
            self.fxk[f["k"]] = f
        m = len(fx)
        if m == 0:
            self.seq, self.pend = [], None
            return False
        if not self.seq:
            self._feed(fx[0])
        else:
            self._feed(fx[m - 1])            # 直接在旧状态上喂，不回快照
        return True


def _sig(f):
    return (f["k"], f["i"], f["type"], f["price"])


class Guarded(IncPens):
    """**pine 里真打算跑的形状** —— 与 IncPens 同解，但把"每根复制整份快照"换成 O(1) 守卫。

    为什么必须换：pine 每根重放一次全历史（2 万根），每根 `array.copy(seq)`（seq 能到上千）
    就是 2000 万次拷贝 —— 那正是这张卡要干掉的那种"每根重算一遍"。

    守卫三条（按 ① 的不变量排的，但**正确性不押在它上面** —— 对不上就走第 3 条整段重算）：
        1) m == done 且最后一个分型没变（比对签名）  ⇒ 无事可做
        2) m == done + 1                            ⇒ 只喂新的那一个（O(1) 摊还）
        3) 其余（缩了 / 跳变 / 最后一格被改）        ⇒ 从空重算（不在旧状态上猜）
    """

    def __init__(self, rule="old", min_gap=4):
        IncPens.__init__(self, rule, min_gap)
        self.done = 0
        self.sig = None

    def update(self, std, fx):
        self.std = std
        self.fxk = [None] * len(std)
        for f in fx:
            self.fxk[f["k"]] = f
        m = len(fx)
        if m == 0:
            self.seq, self.pend, self.done, self.sig = [], None, 0, None
            return False
        if m == self.done and self.sig == _sig(fx[-1]):
            return False                                    # 守卫 1：分型表没变
        # 守卫 2：长了一格 **且旧尾巴没被动过** ⇒ 只喂新的那个。
        # ★ 光比长度不够：旧尾巴被改 + 又长一格，长度也对得上，但那格得重喂。
        #   `sig` 就是上一轮 fx[-1] 的签名，这一轮它是 fx[m-2]，比一下才敢只喂一个。
        #   done == 0 时没有旧尾巴可比，m 必为 1，直接喂 fx[0]。
        if m == self.done + 1 and (self.done == 0 or self.sig == _sig(fx[m - 2])):
            self._feed(fx[m - 1])
        else:
            self.rebuilds += 1
            self.seq, self.pend = [], None                  # 守卫 3：整段重算
            for i in range(m):
                self._feed(fx[i])
        self.done, self.sig = m, _sig(fx[-1])
        return True


class NoRefeed(IncPens):
    """正臂：**`fix_start` / 待定回退之后，不把那段旧分型对着新端点重看**。

    这才是 ② 真正会出的错：回溯中位 1、p99 2、最大 5（notes/pen-reach-probe.py），
    回退后的重喂就是把这段补回来的机制。掐掉它，深回溯处必然对不上 ⇒ 必须红。
    """

    def _refeed(self, k0, k1):
        pass


class NoFixStart(IncPens):
    """正臂：**从不调 `fix_start`** —— 端点不是极值也不回头修。必须红。"""

    def _fix_start(self):
        pass


# ───────────────────────── 比对 ─────────────────────────
def check_series(bars, name, tick=None, label="prefix", max_bars=None, rule="old",
                 cls=IncPens, stop_at_first=True):
    inc_k = IncKline()
    inc_p = cls(rule)
    checked, nbad = 0, 0
    if max_bars:
        bars = bars[:max_bars]
    for k in range(len(bars)):
        inc_k.push(bars[k]["h"], bars[k]["l"])
        std, fx = inc_k.snapshot()
        inc_p.update(std, fx)
        checked += 1
        bstd = standardize(quantize(bars[:k + 1], tick))
        bfx = fractals(bstd)
        bpens, bseq = build_pens(bfx, bstd, rule, 4)
        if inc_p.pens() != _pens_of(bseq) or inc_p.seqkey() != \
                [(f["k"], f["i"], f["type"], f["price"]) for f in bseq]:
            nbad += 1
            if stop_at_first:
                return checked, dict(name=name, k=k + 1, got=len(inc_p.pens()), want=len(bpens),
                                     gotseq=len(inc_p.seq), wantseq=len(bseq), label=label)
    return checked, (None if nbad == 0 else dict(name=name, nbad=nbad, label=label))


def rand_bars(rng, n, tick):
    # ★ 起点必须**落在 tick 格子上**：IncKline.push 存的是原价，批量参照那条路要过 quantize。
    # 起点随便取的话两条路看到的是不同的价格，会造出假的"分歧"（这个坑我自己踩过一次）。
    px = round(round(rng.uniform(10, 500) / tick) * tick, 10)
    out = []
    for _ in range(n):
        px = max(tick, px + rng.choice((-2, -1, -1, 0, 0, 1, 1, 2)) * tick)
        h = px + rng.choice((0, 0, tick, tick, 2 * tick))
        l = px - rng.choice((0, 0, tick, tick, 2 * tick))
        out.append({"h": round(h, 6), "l": round(l, 6)})
    return out


def load_real():
    """真实数据里最大的几份 —— 臂也要压真实行情，不只在随机序列上跑。"""
    out = []
    d = os.path.join(ROOT, "data")
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json") or any(x in fn for x in SKIP):
            continue
        try:
            bars = json.load(io.open(os.path.join(d, fn), encoding="utf-8"))
        except Exception:                                       # noqa: BLE001
            continue
        if isinstance(bars, dict):
            bars = bars.get("bars") or bars.get("klines") or bars
        if not bars:
            continue
        try:
            tick = tick_of_soft(fn)
        except Exception:                                       # noqa: BLE001
            tick = None
        out.append((fn, bars, tick))
    return out


def tick_of_soft(fn):
    try:
        from config import tick_of
        return tick_of(fn)
    except Exception:                                           # noqa: BLE001
        return None


def measure_append_only():
    """量「分型表只会追加」这条不变量 —— NoCk 预测绿的依据必须自己有数。"""
    KEYS = ("grew", "grew_on_merge", "same", "revised", "shrank")

    def scan(bars, tick):
        """口径写死，免得下一眼的人猜：
            grew            分型表长度 +1，且旧表是新表的**前缀**（= 纯追加）
            grew_on_merge   上面那种里，**标准化序列长度没涨**的那些（即"合并那一下长了一格"）
            same            长度不变且整表逐位相同
            revised         长度不变但内容变了，或长度 +1 而旧表不是前缀  ← 唯一要盯的数
            shrank          分型表变短（= pop 掉没补回来）
        """
        inc = IncKline()
        prev, stat = None, dict.fromkeys(KEYS, 0)
        for b in bars:
            inc.push(b["h"], b["l"])
            _m, fx = inc.snapshot()
            cur = [(f["k"], f["i"], f["type"], f["price"]) for f in fx]
            if prev is not None:
                if len(cur) == len(prev):
                    stat["same" if cur == prev else "revised"] += 1
                elif len(cur) == len(prev) + 1:
                    if cur[:len(prev)] == prev:
                        stat["grew"] += 1
                        if not inc.grew:                 # 标准化序列没涨 ⇒ 合并长出来的
                            stat["grew_on_merge"] += 1
                    else:
                        stat["revised"] += 1
                elif len(cur) < len(prev):
                    stat["shrank"] += 1
                else:
                    stat["grew"] += 1
            prev = cur
        return stat

    tot = dict.fromkeys(KEYS, 0)
    print("── 分型表：整表比长度、前缀比内容（真实数据，每个前缀）──")
    print("  %-22s %7s %14s %7s %8s %7s" % ("数据", "grew", "其中合并长的", "same", "revised", "shrank"))
    for fn, bars, tick in load_real():
        st = scan(bars, tick)
        for kk in tot:
            tot[kk] += st[kk]
        flag = "" if st["revised"] == 0 and st["shrank"] == 0 else "   ★ 有改动/有缩短"
        print("  %-22s %7d %14d %7d %8d %7d%s"
              % (fn, st["grew"], st["grew_on_merge"], st["same"], st["revised"], st["shrank"], flag))
    rng = random.Random(20261002)
    rst = dict.fromkeys(KEYS, 0)
    for _ in range(60):
        tick = rng.choice((0.1, 0.25, 0.5, 1.0, 2.0))
        st = scan(rand_bars(rng, rng.randint(40, 500), tick), tick)
        for kk in rst:
            rst[kk] += st[kk]
            tot[kk] += st[kk]
    print("  %-22s %7d %14d %7d %8d %7d"
          % ("随机 60 条", rst["grew"], rst["grew_on_merge"], rst["same"],
             rst["revised"], rst["shrank"]))
    print("\n  合计：push 之后 grew %d（其中「合并那一下长了一格」%d）｜ same %d ｜ revised %d ｜ shrank %d"
          % (tot["grew"], tot["grew_on_merge"], tot["same"], tot["revised"], tot["shrank"]))
    if tot["revised"] or tot["shrank"]:
        print("  ⇒ 分型表**会**被改/被删 ⇒ 检查点必须回退，NoCk 不再是负臂。")
        return 1
    print("  ⇒ revised 0 / shrank 0：分型表只增不改 ⇒ 检查点从不必回退（NoCk 绿是有理的）。")
    return 0


def run_self_test():
    """把增量版**故意改坏**，检查程序必须红。不红的正臂和没有臂同脸。"""
    arms = [
        ("O(1) 守卫版（pine 要跑的形状）", Guarded, True),   # 第②步真正要进 pine 的那个形状
        ("没有检查点（不回退）", NoCk, True),      # 负臂：见 NoCk 的 docstring（①只会追加）
        ("快照丢了 seq（状态被扔）", ShallowCk, False),
        ("fix_start 之后不重喂", NoRefeed, False),
        ("从不调 fix_start", NoFixStart, False),
    ]
    rng = random.Random(20261002)
    series = [("rand", rand_bars(rng, 600, t), t) for t in (1.0, 0.5, 0.1)]
    CAP = 1500          # 臂只为「该红的有没有红」，截 1500 根够覆盖实测的两个红点（362 / 530）
    for fn, bars, tick in load_real():
        series.append((fn, bars[:CAP], tick))
    print("--self-test：臂跑在 %d 条序列上（随机 3 × 600 根 + 真实 %d 份 × 前 %d 根，逐前缀）"
          % (len(series), len(series) - 3, CAP))
    ok = True
    for name, cls, expect_green in arms:
        red_where = None
        for nm, s, tick in series:
            checked, bad = check_series(s, nm, tick, cls=cls)
            if bad:
                red_where = "%s @第 %d 根" % (nm, bad["k"])
                break
        if red_where and not expect_green:
            mark = "✓ 当场红 · %s" % red_where
        elif red_where:
            mark = "✗ **意外红了** · %s（不变量被破了？）" % red_where
        elif expect_green:
            mark = "· 绿（预测如此）"
        else:
            mark = "✗ **没红**（这个检查程序或这批数据不算数）"
        print("   %-24s ⇒ %s" % (name, mark))
        if bool(red_where) == expect_green:          # 该红的红了 / 该绿的绿了
            ok = False
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--append-only", action="store_true",
                    help="量「分型表只增不改」这条不变量（NoCk 预测绿的依据）")
    ap.add_argument("--random", type=int, default=200)
    ap.add_argument("--max-bars", type=int, default=None)
    ap.add_argument("--arm", default=None, help="只跑某支臂：NoCk / NoRefeed / NoFixStart / ...")
    ap.add_argument("--impl", default="Guarded", choices=["Guarded", "IncPens"],
                    help="全量验收驱动哪个增量实现。默认 Guarded = **pine 里真跑的形状**；"
                         "IncPens = 检查点版（每根复制整份快照，慢十倍，且**不进 pine**）")
    ap.add_argument("--files", default="", help="配合 --arm：逗号分隔的文件名（data/ 下）")
    a = ap.parse_args()

    if a.self_test:
        print("--self-test：把增量笔故意改坏，检查程序必须红")
        return 0 if run_self_test() else 3
    if a.append_only:
        return measure_append_only()
    if a.arm:
        cls = {"NoCk": NoCk, "ShallowCk": ShallowCk, "NoRefeed": NoRefeed,
               "NoFixStart": NoFixStart, "IncPens": IncPens, "Guarded": Guarded}.get(a.arm)
        if cls is None:
            print("未知臂 %s" % a.arm, file=sys.stderr)
            return 2
        bad_total = 0
        t0 = time.time()
        for fn in a.files.split(","):
            bars = json.load(io.open(os.path.join(ROOT, "data", fn), encoding="utf-8"))
            if isinstance(bars, dict):
                bars = bars.get("bars") or bars.get("klines") or bars
            tick = tick_of_soft(fn)
            t1 = time.time()
            checked, bad = check_series(bars, fn, tick, cls=cls, max_bars=a.max_bars)
            if bad:
                bad_total += 1
                print("  ✗ %-14s 臂 %s 在第 %d 根就分开了 [%.1fs]"
                      % (fn, a.arm, bad["k"], time.time() - t1))
            else:
                print("  ✓ %-14s 臂 %s 全程 %d 个前缀都对上了 [%.1fs]"
                      % (fn, a.arm, checked, time.time() - t1))
        print("臂=%s ｜ %d 份 ｜ 分开 %d 处 ｜ 用时 %.0fs" % (a.arm, len(a.files.split(",")),
                                                          bad_total, time.time() - t0))
        return 1 if bad_total else 0

    from config import tick_of
    impl = {"Guarded": Guarded, "IncPens": IncPens}[a.impl]
    fails, total, datasets = [], 0, 0
    t0 = time.time()
    print("── 驱动实现：%s%s ──" % (a.impl, "（pine 里真跑的形状）" if a.impl == "Guarded" else
                                "（检查点版，不进 pine —— 慢十倍）"))
    print("── 真实数据（每个前缀都跑，不抽稀）──")
    files = [f for f in sorted(os.listdir(os.path.join(ROOT, "data")))
             if f.endswith(".json") and not any(x in f for x in SKIP)]

    def load(fn):
        b = json.load(io.open(os.path.join(ROOT, "data", fn), encoding="utf-8"))
        if isinstance(b, dict):
            b = b.get("bars") or b.get("klines") or b
        return b or []

    # 短的先跑。按字母序 zec15（20160 根）排第 6，单份要跑几小时，会把后面 4 份小的全堵在它后面；
    # 升序之后 8 份小的十几分钟就全出数，只有最大的那份长时间挂着。**覆盖面一个不少，只是换顺序。**
    cache = {fn: load(fn) for fn in files}
    files.sort(key=lambda fn: len(cache[fn]))
    print("顺序（按根数升序）：" + " → ".join("%s(%d)" % (f, len(cache[f])) for f in files))
    for fn in files:
        bars = cache[fn]
        if not bars:
            continue
        datasets += 1
        try:
            tick = tick_of(fn)
        except Exception:                                       # noqa: BLE001
            tick = None
        t1 = time.time()
        checked, bad = check_series(bars, fn, tick, max_bars=a.max_bars, cls=impl)
        total += checked
        if bad:
            fails.append(bad)
            print("  ✗ %-22s 分歧 @第 %d 根 ｜ 笔 %d vs %d ｜ 端点 %d vs %d   [%.1fs]"
                  % (fn, bad["k"], bad["got"], bad["want"], bad["gotseq"], bad["wantseq"],
                     time.time() - t1))
        else:
            print("  ✓ %-22s %5d 根 ｜ 查了 %5d 个前缀  [%.1fs]"
                  % (fn, len(bars), checked, time.time() - t1))

    print("── 随机行情（每个前缀都跑，等号密集）──")
    rng = random.Random(20261002)
    rand_checked = 0
    for t in range(a.random):
        tick = rng.choice((0.1, 0.25, 0.5, 1.0, 2.0))
        n = rng.randint(40, 500)
        bars = rand_bars(rng, n, tick)
        checked, bad = check_series(bars, "rand#%d" % t, tick, cls=impl)
        rand_checked += checked
        if bad:
            fails.append(bad)
            print("  ✗ 随机 #%d(tick=%s,n=%d) 分歧 @第 %d 根 ｜ 笔 %d vs %d"
                  % (t, tick, n, bad["k"], bad["got"], bad["want"]))
    print("  ✓ %d 条随机序列 ｜ 查了 %d 个前缀" % (a.random, rand_checked))

    print("\n驱动实现 %s ｜ 真实数据 %d 份 ｜ 前缀合计查了 %d 个 ｜ 分歧 %d 处 ｜ 用时 %.0fs"
          % (a.impl, datasets, total, len(fails), time.time() - t0))
    if fails:
        print("⇒ **不一致**：增量笔与批量笔不是逐前缀相同。")
        return 1
    print("⇒ 0 不一致：在第 k 根上，**%s** 与『拿 [0..k] 重跑一遍』逐位相同。" % a.impl)
    return 0


if __name__ == "__main__":
    sys.exit(main())
