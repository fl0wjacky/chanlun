#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对账：/api/chart 吐出来的结构 ≡ render/chart_full_smooth.py 对同一份 K 线算出来的结构（逐个、逐字段）。

    python3 web/check_parity.py          # 仓里 9 份基准数据，走真 HTTP（含 gzip），rc=0 才算过
    python3 web/check_parity.py --self-test   # 三条变异必须各自红，否则这把尺不算数

参照侧照抄 chart_full_smooth.render() 的取数口径：analyze(bars, tick=tick_of(fn))；
买卖点照抄 render/full_common.draw_signals：signals(r, 层, CHART["sig_measure"])，两层。
服务侧：把 server.fetch 换成「返回这份文件的 K 线」，起一个临时端口（回环），真发 GET。
服务侧的形状来自 tools/make_web_fixture.shape（前端离线样本也是它烤的）—— 这里不信它，照渲染器重算一遍比。
比较不做 JSON 往返的「两边都洗一遍」—— 参照是引擎原值，服务侧是解码后的 JSON：
tuple 当 list 比、浮点逐位相等，big 的 members 按 PI0 列表比。
"""
import contextlib
import glob
import gzip
import json
import os
import re
import sys
import threading
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import server                                           # noqa: E402
import make_web_fixture as mwf                          # noqa: E402  （server 已把 tools/ 放上 sys.path）
from config import data, tick_of                        # noqa: E402
from core.analyze import analyze                        # noqa: E402
from core.signals import signals                        # noqa: E402
from render.style import CHART                          # noqa: E402

PREFIX = {"zec": "ZECUSDT", "btc": "BTCUSDT", "aaplusdt": "AAPLUSDT"}
TF_OF = {"15": "15m", "15m": "15m", "30m": "30m", "1h": "1h", "2h": "2h", "4h": "4h"}


def dataset(fn):
    """data/ 文件名 → (symbol, tf)；对不上就 None（不在本对账范围）。"""
    stem = fn[:-5]
    for p, sym in PREFIX.items():
        if stem.startswith(p):
            rest = stem[len(p):].lstrip("_")
            if rest in TF_OF:
                return sym, TF_OF[rest]
    return None


def norm(v):
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [norm(x) for x in v]
    return v


def reference(bars, fn):
    r = analyze(bars, tick=tick_of(fn))
    big = []
    for b in r["big"]:
        b = dict(b)
        if "members" in b:
            b["members"] = [m["PI0"] for m in b["members"]]
        big.append(b)
    return norm(dict(
        bars=r["bars"],
        pens=r["pens"], segs=r["segs"], centers=r["centers"], seg_centers=r["seg_centers"], big=big,
        signals=dict(pen=signals(r, "pen", CHART["sig_measure"]), seg=signals(r, "seg", CHART["sig_measure"])),
        tick=r["tick"], pen_rule=r["pen_rule"],
    ))


def flat(got):
    """服务侧 → 跟 reference 同一套键：tick / pen_rule 在 meta 里。"""
    m = got.get("meta") or {}
    return dict(got, tick=m.get("tick"), pen_rule=m.get("pen_rule"))


@contextlib.contextmanager
def running(bars_by_key):
    """起一个临时服务；fetch 换成查表（只认白名单里的 key），DAYS 放大到不截任何一根。"""
    saved = (server.fetch, server.DAYS)
    server.fetch = lambda s, t, a, b: list(bars_by_key[(s, t)])
    server.DAYS = 100000
    for slot in server.SLOTS.values():
        slot.__init__()
    srv = server.make_server(0)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        yield srv.server_address[1]
    finally:
        srv.shutdown()
        srv.server_close()
        server.fetch, server.DAYS = saved


def get(port, symbol, tf):
    req = urllib.request.Request("http://127.0.0.1:%d/api/chart?symbol=%s&tf=%s" % (port, symbol, tf),
                                 headers={"Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
    return json.loads(body)


def compare(ref, got):
    """→ 差异列表（每条一行）。逐结构、逐个、逐字段。"""
    diffs = []
    for key in ("tick", "pen_rule"):
        if ref[key] != got.get(key):
            diffs.append("%s: 参照=%r 服务=%r" % (key, ref[key], got.get(key)))
    groups = [(k, ref[k], got.get(k)) for k in ("bars", "pens", "segs", "centers", "seg_centers", "big")]
    groups += [("signals." + lv, ref["signals"][lv], (got.get("signals") or {}).get(lv)) for lv in ("pen", "seg")]
    for name, a, b in groups:
        if b is None:
            diffs.append("%s: 服务侧缺这一项" % name)
            continue
        if len(a) != len(b):
            diffs.append("%s: 个数 参照 %d ≠ 服务 %d" % (name, len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                keys = sorted(set(x) | set(y)) if isinstance(x, dict) and isinstance(y, dict) else ["(整条)"]
                bad = [k for k in keys if not isinstance(x, dict) or x.get(k) != y.get(k)]
                diffs.append("%s[%d]: 字段 %s 不同" % (name, i, ",".join(bad[:6])))
                break                                      # 每组只报第一处，别刷屏
    return diffs


def run(quiet=False):
    files = sorted(os.path.basename(p) for p in glob.glob(data("*.json")))
    cases = [(fn, dataset(fn)) for fn in files]
    cases = [(fn, k) for fn, k in cases if k]
    bars_by_key = {k: json.load(open(data(fn), encoding="utf-8")) for fn, k in cases}
    if len(bars_by_key) != len(cases):
        print("★ 两份数据落在同一个（品种, 周期）上，对账会互相覆盖 —— 查不了 ≠ 通过")
        return 2, 0
    total = bad = 0
    with running(bars_by_key) as port:
        for fn, (sym, tf) in cases:
            ref = reference(bars_by_key[(sym, tf)], fn)
            try:
                got = get(port, sym, tf)
                d = compare(ref, flat(got))
                if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", str(got.get("fetched_at"))) or got.get("stale") is not False:
                    d.append("fetched_at / stale 不对：%r / %r" % (got.get("fetched_at"), got.get("stale")))
            except Exception as e:                         # 服务侧回非 200 / 回不来：算不一致，不算「跳过」
                d = ["服务侧没回结构（%s）" % type(e).__name__]
            n = sum(len(ref[k]) for k in ("pens", "segs", "centers", "seg_centers", "big")) + \
                len(ref["signals"]["pen"]) + len(ref["signals"]["seg"])
            total += n
            bad += bool(d)
            if not quiet:
                print("%s %-18s %s %-3s  结构 %5d 个%s" % ("✗" if d else "✓", fn, sym, tf, n,
                                                         "" if not d else "  ← " + " ｜ ".join(d[:4])))
    if not quiet:
        print("对账 %d 份数据、%d 个结构（另逐根比 K 线），不一致 %d 份" % (len(cases), total, bad))
    if not cases:
        print("★ 一份数据都没对上 —— 查不了 ≠ 通过")
        return 2, 0
    return (1 if bad else 0), bad


def self_test():
    """服务侧三种「看起来能跑、其实算错」：精度错、背驰度量错、一个类中枢的 ZG 差一跳 —— 对账必须各自红。"""
    arms = []

    def arm_tick():
        saved = dict(server.SYMBOLS)
        server.SYMBOLS["ZECUSDT"] = "btc"                 # ZEC 用了 BTC 的精度 0.1
        try:
            return run(quiet=True)[1]
        finally:
            server.SYMBOLS.clear()
            server.SYMBOLS.update(saved)
    arms.append(("ZEC 精度错成 0.1", arm_tick))

    def arm_measure():
        real = mwf.signals
        mwf.signals = lambda r, lv, measure="macd", **k: real(r, lv, "slope", **k)
        try:
            return run(quiet=True)[1]
        finally:
            mwf.signals = real
    arms.append(("背驰度量 macd→slope", arm_measure))

    def arm_drop():
        real = mwf.analyze

        def lossy(*a, **k):                               # 悄悄错一个数，不让下游崩（崩了是另一种脸）
            r = real(*a, **k)
            if r["centers"]:
                r["centers"][-1]["ZG"] += r["tick"] or 0.01
            return r
        mwf.analyze = lossy
        try:
            return run(quiet=True)[1]
        finally:
            mwf.analyze = real
    arms.append(("最后一个类中枢 ZG 差一跳", arm_drop))

    miss = 0
    for name, f in arms:
        n = f()
        print("%s 变异 %-20s ⇒ %d 份不一致" % ("✓" if n else "✗", name, n))
        miss += 0 if n else 1
    assert mwf.analyze is analyze and mwf.signals is signals   # 变异都还原了
    return 3 if miss else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(run()[0])
