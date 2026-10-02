# -*- coding: utf-8 -*-
"""③ 的「笔序列同步」实测：三路守卫到底会不会漏掉**深处被回改**。

Nova 的挑战：pine 里那句「zSeq 只动最后两格」是错的 —— `fix_start` 会 `seq[:] = seq[:j+1] + [P]`，
j 可以一路降到 0（回改 5 笔都量到过），而已确认段的保护边界是 `endPen ≤ M-4`。回改一深，
尾巴签名（last-3）就可能**蒙混过关**：长度没缩、最后三格没变，可中间某一格已经变了。

这份尺子不猜，直接**把 pine 里 zSegStep 的三路守卫逐行搬成 Python**，喂给真实引擎的
增量笔序列（`Guarded`，已被 ② 证明逐前缀 == 批量），每根比对「守卫维护出来的 pens」跟
「拿整条 seq 重新摊平的 pens」是否逐格相同。守卫只要漏一次，这里当场红。

    守卫 1  纯追加：多一笔、旧尾巴签名不动            ⇒ push 一笔
    守卫 2  尾端点被换：笔数不变、e2 没变             ⇒ 只重推最后一笔
    守卫 3  其余（缩了 / 跳变 / 深处被改）            ⇒ 整段重算

三路守卫的正确性**全押在两件事上**：
    (A) 变化要么只动最后一格（e1），要么就整段缩水——「中间某格变了但长度没缩」不存在；
    (B) 守卫 2 里只查 `e2 == sig[1]` 就够——e3 变、e2 不变的中间态不存在。
这两条都不是代码保证，是**对 engine 行为的猜测**。本尺子量它到底成不成立。

用法：
    python3 notes/pen-sync-deepfix-probe.py                 # 全部数据 × 每个前缀
    python3 notes/pen-sync-deepfix-probe.py --max-bars 800  # 只跑前 N 根
退出码：0 守卫从未漏 ｜ 1 守卫漏过（有 bug）｜ 2 跑不动
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

# 把 ② 那份里的 Guarded（pine 真跑的形状）+ 数据加载借过来。
P = os.path.join(HERE, "pine-incremental-pen.py")
_spec = importlib.util.spec_from_file_location("incpen", P)
_incpen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_incpen)
Guarded = _incpen.Guarded
IncKline = _incpen.IncKline
load_real = _incpen.load_real
rand_bars = _incpen.rand_bars
tick_of_soft = _incpen.tick_of_soft

SKIP = ("annot", "mag", "sub")


def _k(f):
    return f["k"] if f is not None else -1


def _pen(a, b):
    return (a["i"], b["i"], a["k"], b["k"])


def _flatten(seq):
    return [_pen(seq[t], seq[t + 1]) for t in range(len(seq) - 1)]


class Sync3:
    """pine zSegStep 里「笔序列同步」三路的逐行 Python 版。只维护 pens 这一份状态。"""

    def __init__(self):
        self.pens = []
        self.sig = [-1, -1, -1]          # [e1, e2, e3] = 尾部三格端点签名（用 k 当身份）

    def apply(self, seq):
        M = len(seq)
        e1 = _k(seq[M - 1]) if M >= 1 else -1
        e2 = _k(seq[M - 2]) if M >= 2 else -1
        e3 = _k(seq[M - 3]) if M >= 3 else -1
        penCount = M - 1 if M >= 1 else 0
        branch = 0                       # 0 = 无事可做
        if penCount != len(self.pens) or e1 != self.sig[0] or e2 != self.sig[1] or e3 != self.sig[2]:
            if penCount == len(self.pens) + 1 and e2 == self.sig[0] and e3 == self.sig[1]:
                self.pens.append(_pen(seq[penCount - 1], seq[penCount]))          # 守卫 1
                branch = 1
            elif penCount == len(self.pens) and penCount > 0 and e2 == self.sig[1]:
                # 守卫 2（尾端点被换）：照 pine 修正，也整段重摊（换最后那根笔会翻动 openingOverlaps，
                # 段扫描会 stale —— 见 seg-sync-deepfix-probe.py）。本尺子只量「pens 漏没漏」，
                # 这里整段重摊与只重推最后一笔对 pens 的结果一样，但对段不一样。
                self.pens = _flatten(seq)
                branch = 2
            else:
                self.pens = _flatten(seq)                                         # 守卫 3
                branch = 3
            self.sig = [e1, e2, e3]
        return branch, list(self.pens)


def first_diff(a, b):
    if len(a) != len(b):
        return ("len", len(a), len(b))
    for t in range(len(a)):
        if a[t] != b[t]:
            return (t, a[t], b[t])
    return None


class DepthGuarded(Guarded):
    """在 `Guarded` 上叠一层：记录 `fix_start` 每次截断的**深度**（替换掉多少个端点）。

    深度 = 截断前 seq 长度 − (截断后保留的前缀 j+1 再加的那 1 个)。这就是「回改几笔」里的
    那个数 —— Nova 量到过 5。这里把每根的最大深度记下来，好确认「深处回改」确实被喂进了
    守卫、且确实被守卫 3（整段重算）接住了，而不是「这批数据里根本没发生」。
    """

    def __init__(self, rule="old", min_gap=4):
        Guarded.__init__(self, rule, min_gap)
        self.max_depth = 0
        self.deep_sites = []             # [(k, depth), ...] 深度 ≥ 3 的站点

    def _fix_start(self):
        seq = self.seq
        before = len(seq)
        # 深度 = 旧尾部被丢掉的端点个数（即 before − 1 − j，j 是保留到的下标）。
        # 在 _fix_start 里不好直接看 j，改在截断动作发生处量：这里包一层去算。
        # 直接重写，把 j 的扫描搬过来、只在截断那一刻记录深度。
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
                depth = before - (j + 2)                     # 保留 seq[:j+1] + [P]，丢 before-(j+2) 个
                self.max_depth = max(self.max_depth, depth)
                if depth >= 3:
                    self.deep_sites.append((self._bar, depth))
                seq[:] = seq[:j + 1] + [P]
                self.pend = None
                self._refeed(P["k"] + 1, g["k"])
                return
            if e["type"] == a["type"] and j <= len(seq) - 4 and self._pen_ok(e, g):
                depth = before - (j + 2)
                self.max_depth = max(self.max_depth, depth)
                if depth >= 3:
                    self.deep_sites.append((self._bar, depth))
                seq[:] = seq[:j + 1] + [g]
                return

    def update(self, std, fx):
        self._bar = len(fx)              # 当前喂到第几个分型（近似第几根，量深度够用）
        return Guarded.update(self, std, fx)


def probe(bars, tick, name, max_bars=None, rng=None):
    inc_k = IncKline()
    g = DepthGuarded("old", 4)
    sync = Sync3()
    if max_bars:
        bars = bars[:max_bars]

    stat = {"bars": 0, "branch1": 0, "branch2": 0, "branch3": 0, "noop": 0,
            "miss": 0, "miss_first": None, "branch2_wrong": 0, "branch2_wrong_first": None,
            "max_depth": 0, "deep_sites": []}

    for k in range(len(bars)):
        inc_k.push(bars[k]["h"], bars[k]["l"])
        std, fx = inc_k.snapshot()
        g.update(std, fx)               # 推进到第 k 根；g.seq 此刻 == zSeq
        seq = g.seq
        branch, got = sync.apply(seq)
        truth = _flatten(seq)
        stat["bars"] += 1
        if branch == 1:
            stat["branch1"] += 1
        elif branch == 2:
            stat["branch2"] += 1
        elif branch == 3:
            stat["branch3"] += 1
        else:
            stat["noop"] += 1

        d = first_diff(got, truth)
        if d is not None:
            if branch == 0:
                stat["miss"] += 1
                if stat["miss_first"] is None:
                    stat["miss_first"] = (k + 1, d, _k(seq[-1]) if seq else -1)
            elif branch == 2:
                stat["branch2_wrong"] += 1
                if stat["branch2_wrong_first"] is None:
                    stat["branch2_wrong_first"] = (k + 1, d, _k(seq[-1]) if seq else -1)
            else:
                # 守卫 1 或 3 里不该出差异；记个数，打印会当异常暴露
                stat["miss"] += 1
                if stat["miss_first"] is None:
                    stat["miss_first"] = (k + 1, d, "branch%d" % branch)
    stat["max_depth"] = g.max_depth
    stat["deep_sites"] = g.deep_sites
    return stat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-bars", type=int, default=None)
    ap.add_argument("--random", type=int, default=200)
    a = ap.parse_args()

    t0 = time.time()
    print("── ③ 笔序列同步：三路守卫会不会漏「深处回改」──")
    print("  口径：每根拿真实 `Guarded` 的 seq 喂守卫，比对「守卫维护的 pens」==「整条重摊平的 pens」。\n")
    tot = dict(bars=0, branch1=0, branch2=0, branch3=0, noop=0, miss=0, branch2_wrong=0)
    any_bad = False

    files = [f for f in sorted(os.listdir(os.path.join(ROOT, "data")))
             if f.endswith(".json") and not any(x in f for x in SKIP)]

    def load(fn):
        b = json.load(io.open(os.path.join(ROOT, "data", fn), encoding="utf-8"))
        if isinstance(b, dict):
            b = b.get("bars") or b.get("klines") or b
        return b or []

    cache = {fn: load(fn) for fn in files}
    files.sort(key=lambda fn: len(cache[fn]))
    for fn in files:
        bars = cache[fn]
        if not bars:
            continue
        try:
            tick = tick_of_soft(fn)
        except Exception:                       # noqa: BLE001
            tick = None
        st = probe(bars, tick, fn, max_bars=a.max_bars)
        for kk in tot:
            tot[kk] += st[kk]
        bad = st["miss"] or st["branch2_wrong"]
        any_bad |= bool(bad)
        flag = "" if not bad else "   ★★★ 守卫漏了"
        print("  %-20s 根 %6d | 追加%6d 换尾%4d 重算%4d 无事%6d | 漏%3d(其中守卫2错%3d) | 回改最深%2d%s"
              % (fn, st["bars"], st["branch1"], st["branch2"], st["branch3"], st["noop"],
                 st["miss"], st["branch2_wrong"], st["max_depth"], flag))
        if st["miss_first"]:
            print("        → 漏的首处：@第 %d 根，差异 %r" % (st["miss_first"][0], st["miss_first"][1]))
        if st["branch2_wrong_first"]:
            print("        → 守卫2错的首处：@第 %d 根，差异 %r" % (st["branch2_wrong_first"][0],
                                                                   st["branch2_wrong_first"][1]))
        if st["deep_sites"]:
            print("        → 深处回改(≥3)站点：%s" % ", ".join("@%d(深%d)" % s for s in st["deep_sites"][:6]))

    print("\n  ── 随机行情（压深处回改的稳健性）──")
    rng = random.Random(20261002)
    for t in range(a.random):
        tick = rng.choice((0.1, 0.25, 0.5, 1.0, 2.0))
        n = rng.randint(40, 500)
        bars = rand_bars(rng, n, tick)
        st = probe(bars, tick, "rand#%d" % t)
        for kk in ("bars", "branch1", "branch2", "branch3", "noop", "miss", "branch2_wrong"):
            tot[kk] += st[kk]
        if st["miss"] or st["branch2_wrong"]:
            any_bad = True
            print("  ✗ 随机 #%d 漏 %d / 守卫2错 %d" % (t, st["miss"], st["branch2_wrong"]))
    print("  ✓ %d 条随机序列跑完" % a.random)

    print("\n  合计：根 %d | 追加 %d | 换尾 %d | 重算 %d | 无事 %d | 漏 %d（守卫2错 %d）"
          % (tot["bars"], tot["branch1"], tot["branch2"], tot["branch3"], tot["noop"],
             tot["miss"], tot["branch2_wrong"]))
    if tot["miss"] or tot["branch2_wrong"]:
        print("  ⇒ **守卫漏了**：『中间某格变了但长度没缩 / 尾三格没变』真实存在，三路同步不安全。")
        return 1
    print("  ⇒ 全程 0 漏：三路守卫在真实数据上从未漏掉深处回改（但这是实测，不是上限证明）。")
    print("  用时 %.0fs" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
