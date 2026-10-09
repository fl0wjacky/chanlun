#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T8：「已撤回」账本（web/withdrawn.py，Q-6 A）对实例。状态目录指到临时目录，不碰真的。

    python3 tools/withdrawn_check.py              # rc=0 全对 ／ 1 有一格不对
    python3 tools/withdrawn_check.py --self-test  # 反向臂：每条判据各拧坏一处，必须红；红不了 ⇒ rc=3

夹具 data/aaplusdt_15m_q6.json：AAPL 15m 前 8746 根（决策页 Q-6 那张图的那一刀）。
  ① 8745 → 8746 根：刚好记一条——D2 L 273.27（06-26 那一刀）；旁边 3 把 S5 只是回到待确认，不记；
  ② 前一步、后一步（8744 → 8745、8746 → 8747 换成 8746 → 8746 重算）：0 条；
  ③ 窗口左边切掉 500／1500／3000 根再多一根（线上每次刷新就是这样）：0 条——不比对齐点就会冒假撤回；
  ④ 找不到对齐点（上次的 D2 这次一把都没有）：刀这一类不记；
  ⑤ 账本：重开读得回、每张图最多 CAP 条、几个 span 同一条只给一次、窗口外的不给；
  ⑥ 服务端接线：ENABLED 关着一个字都不写；开着 ⇒ _cut_cc 算完 mbodies 里有 withdrawn。
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, os.path.join(ROOT, "web")]
import core                                     # noqa: E402
import core.trend as T                          # noqa: E402
from config import tick_of                      # noqa: E402
import decisions                                # noqa: E402
import withdrawn as W                           # noqa: E402

A = sys.modules["core.analyze"]                 # ★ 不能写 import core.analyze as A：拿到的是函数
FIX = os.path.join(ROOT, "data", "aaplusdt_15m_q6.json")
TICK = tick_of("aaplusdt_.json")
EVENT = dict(kind="d2", dir="L", price=273.27)
_memo = {}
CAP0 = W.CAP                                    # 方案定的 200；检查按它比，不按（可能被变异改掉的）W.CAP


def snap(bars):
    """→ (trend, segs, snapshot)。缓存只存引擎结果（慢：8.7k 根一次几十秒），snapshot 每次现算 ⇒ 变异臂动了 snapshot 也不用清缓存。"""
    key = (bars[0]["t"], bars[-1]["t"], len(bars))
    if key not in _memo:
        r = A.analyze(bars, tick=TICK)
        _memo[key] = (T.trend_v3(r), T._done(r))     # 线段跟服务端一样比 segs_std（图上画的那套标准化线段）
    v, segs = _memo[key]
    return v, segs, W.snapshot(bars, v, segs)


def step(old, new):
    """上次 old、这次 new（两份 K 线）→ 这一步新记的撤回。"""
    return W.diff(snap(old)[2][0], *snap(new)[2], new[-1]["t"])


def run(quiet=False, server_arm=True):
    bars = json.load(open(FIX))
    bad = []

    def chk(name, ok, got=""):
        if not quiet:
            print("%s %s %s" % ("✓" if ok else "✗", name, "" if ok else got))
        if not ok:
            bad.append(name)

    if not T.SAME_LEVEL:
        chk("引擎默认是同级别（这张检查只对同级别有意义）", False, "SAME_LEVEL=False")
        return len(bad)
    ev = step(bars[:8745], bars[:8746])
    chk("① 8745 → 8746 刚好记一条：D2 L 273.27", len(ev) == 1 and all(ev[0].get(k) == v for k, v in EVENT.items()), ev)
    chk("② 前一步 8744 → 8745：0 条", step(bars[:8744], bars[:8745]) == [], step(bars[:8744], bars[:8745]))
    chk("② 同一份重算 8746 → 8746：0 条", step(bars[:8746], bars[:8746]) == [], "")
    for cut in (500, 1500, 3000):
        got = step(bars[:8700], bars[cut:8701])
        chk("③ 窗口左边切掉 %d 根、右边多一根：0 条" % cut, got == [], got[:3])
    old = snap(bars[:8745])[2][0]
    noanchor = dict(old, cuts=[[c[0] + 1, c[1], c[2], c[3]] if c[3] == "D2-2" else c for c in old["cuts"]])
    got = W.diff(noanchor, *snap(bars[:8746])[2], 0)
    chk("④ 找不到 D2 对齐点：刀一条都不记", not any(w["kind"] in ("d2", "s5") for w in got), got[:3])

    tmp = tempfile.mkdtemp()
    saved = decisions.STATE
    decisions.STATE = tmp
    try:
        key = ("AAPLUSDT", "15m", 1, 6)
        v0, s0, _ = snap(bars[:8745])
        v1, s1, _ = snap(bars[:8746])
        W.observe(key, bars[:8745], v0, s0)
        n1 = W.observe(key, bars[:8746], v1, s1)
        rec = json.load(open(W._path(key)))
        chk("⑤ 记下来、重开读得回", len(n1) == 1 and rec["withdrawn"] == n1 and rec["last"] == snap(bars[:8746])[2][0], rec["withdrawn"])
        W.observe(("AAPLUSDT", "15m", 4, 6), bars[:8745], v0, s0)
        W.observe(("AAPLUSDT", "15m", 4, 6), bars[:8746], v1, s1)
        vw = W.view("AAPLUSDT", "15m", 6, [1, 2, 4], bars[:8746], v1, s1)
        chk("⑤ 两个 span 都记到同一条 ⇒ 只给一次", len(vw) == 1, vw)
        late = bars[:8746]
        vw2 = W.view("AAPLUSDT", "15m", 6, [1, 4], [dict(b, t=b["t"] + 10 ** 12) for b in late], v1, s1)
        chk("⑤ 窗口外的不给", vw2 == [], vw2)
        # 造的条数用定死的 CAP0 + 50（不读 W.CAP：「不封顶」那条变异把它改成 10**9，照它造会造十亿条）
        fake = dict(last=rec["last"], withdrawn=[dict(n1[0], at=i) for i in range(CAP0 + 50)])
        W._save(key, fake)
        W.observe(key, bars[:8745], v0, s0)
        W.observe(key, bars[:8746], v1, s1)
        n = len(json.load(open(W._path(key)))["withdrawn"])
        chk("⑤ 一张图最多 %d 条" % CAP0, n == CAP0, n)

        if not server_arm:
            return len(bad)
        import server                           # noqa: E402
        shutil.rmtree(os.path.join(tmp, "withdrawn"), ignore_errors=True)
        slot = server.Slot(1)
        enabled = W.ENABLED
        try:
            for on in (False, True):
                W.ENABLED = on
                for b in (bars[:8745], bars[:8746]):
                    slot.bars, slot.mbodies = b, {}
                    server._cut_cc(slot, "AAPLUSDT", server.DEFAULT_PEN_MIN, "15m")
                wrote = os.path.isdir(os.path.join(tmp, "withdrawn"))
                got = slot.mbodies.get((server.WD_KEY, server.DEFAULT_PEN_MIN))
                if not on:
                    chk("⑥ ENABLED 关着：不写账本、不带 withdrawn", not wrote and got is None, (wrote, got))
                else:
                    chk("⑥ ENABLED 开着：_cut_cc 算完带 withdrawn（那一条）", wrote and got is not None and len(got) == 1, got)
        finally:
            W.ENABLED = enabled
    finally:
        decisions.STATE = saved
        shutil.rmtree(tmp, ignore_errors=True)
    if not quiet:
        print("全部通过" if not bad else "%d 处不过" % len(bad))
    return len(bad)


def self_test():
    real_anchor, real_diff, real_cap = W._anchor, W.diff, W.CAP
    arms = []

    def arm(name, setup, teardown):
        setup()
        try:
            n = run(quiet=True, server_arm=False)    # 变异都在账本模块里，服务端接线那格（⑥）不跟着拧，省四遍引擎
        finally:
            teardown()
        arms.append((name, n))

    def no_anchor():
        W._anchor = lambda old, new: float("-inf") if old else None
    arm("不比对齐点（从头比）", no_anchor, lambda: setattr(W, "_anchor", real_anchor))

    def pending_counts():
        def d(last, conf, seen, at):
            out = real_diff(last, conf, seen, at)
            now = {(c[0], c[1], c[2]) for c in conf["cuts"]}
            out += [dict(kind="s5", t=c[0], dir=c[1], price=c[2], at=at) for c in last["cuts"]
                    if c[3] != "D2-2" and (c[0], c[1], c[2]) in seen["cuts"] and (c[0], c[1], c[2]) not in now]
            return out
        W.diff = d
    arm("确认 → 待确认也记", pending_counts, lambda: setattr(W, "diff", real_diff))
    arm("不封顶", lambda: setattr(W, "CAP", 10 ** 9), lambda: setattr(W, "CAP", real_cap))

    real_snap = W.snapshot

    def by_index():
        def s(bars, trend, segs):
            off = bars[0]["t"]
            return real_snap([dict(b, t=i) for i, b in enumerate(bars)], trend, segs) if off else real_snap(bars, trend, segs)
        W.snapshot = s
    arm("键用下标不用开盘时间", by_index, lambda: setattr(W, "snapshot", real_snap))
    ok = all(n > 0 for _, n in arms)
    for name, n in arms:
        print("%s 变异「%s」⇒ 主跑 %d 处不过" % ("✓" if n > 0 else "✗", name, n))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv[1:] else (1 if run() else 0))
