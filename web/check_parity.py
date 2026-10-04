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
import time
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
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))

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
    saved = (server.fetch, server.DAYS, server.start_prefetch)
    server.fetch = lambda s, t, a, b: list(bars_by_key[(s, t)])
    server.DAYS = 100000
    server.start_prefetch = lambda *a: None             # 对账只看被请求的那一档
    for slot in server.SLOTS.values():
        slot.reset()
    srv = server.make_server(0)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        yield srv.server_address[1]
    finally:
        srv.shutdown()
        srv.server_close()
        server.fetch, server.DAYS, server.start_prefetch = saved


def get(port, symbol, tf, span=None):
    req = urllib.request.Request("http://127.0.0.1:%d/api/chart?symbol=%s&tf=%s%s"
                                 % (port, symbol, tf, "&span=%d" % span if span else ""),
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


VIEW = 160                                               # 默认可视窗口（Nova 10-04：最近 160 根里结构必须逐项相同）


def run_span(quiet=False):
    """扩展档：每份数据往前接一份（时间前挪、价格缩 0.7）当「更长的历史」，假币安按请求的 [a, b] 截。
    ① span=2 对账：服务吐的结构 ≡ 引擎在**服务吐出来的那段 K 线**上整段重算的结构（证「整段重算、不拼接」）；
    ② span=1 对 span=2：最近 VIEW 根里结构逐项相同（span_measure.diff_pair，含买卖点），最右差异离右端 ≥ VIEW。"""
    from span_measure import diff_pair
    files = sorted(os.path.basename(p) for p in glob.glob(data("*.json")))
    cases = [(fn, dataset(fn)) for fn in files if dataset(fn)]
    longer = {}
    for fn, key in cases:
        b = json.load(open(data(fn), encoding="utf-8"))
        n, step = len(b), server.TFS[key[1]]
        longer[key] = [dict(x, t=x["t"] - n * step, o=x["o"] * .7, h=x["h"] * .7, l=x["l"] * .7, c=x["c"] * .7)
                       for x in b] + b
    saved = (server.fetch, server.start_prefetch)

    def fake(sym, tf, a, b_):
        src = longer[(sym, tf)]
        step = server.TFS[tf]
        shift = (int(time.time() * 1000) // step) * step - src[-1]["t"]
        return [dict(x, t=x["t"] + shift) for x in src if a <= x["t"] + shift <= b_]
    server.fetch, server.start_prefetch = fake, (lambda *a: None)
    for slot in server.SLOTS.values():
        slot.reset()
    srv = server.make_server(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port, bad, near = srv.server_address[1], 0, []
    try:
        for fn, (sym, tf) in cases:
            d1, d2 = get(port, sym, tf, 1), get(port, sym, tf, 2)
            ref = reference([dict(t=x["t"], o=x["o"], h=x["h"], l=x["l"], c=x["c"]) for x in d2["bars"]], fn)
            diffs = compare(ref, flat(d2))
            if d1.get("earliest"):
                # span=1 已经到最早（AAPL 这几份只有约 60 天）：span=2 必须是同一份、也标 earliest
                if not d2.get("earliest") or len(d2["bars"]) != len(d1["bars"]):
                    diffs.append("span=1 已 earliest，span=2 却不同（earliest=%s，%d vs %d 根）"
                                 % (d2.get("earliest"), len(d2["bars"]), len(d1["bars"])))
            elif len(d2["bars"]) <= len(d1["bars"]):
                diffs.append("span=2 没比 span=1 多出 K 线（%d vs %d），span=1 也没标 earliest"
                             % (len(d2["bars"]), len(d1["bars"])))
            p = diff_pair(d1, d2)
            r = p["rightmost_from_end"]
            if r is not None and r < VIEW:
                diffs.append("最近 %d 根里结构变了：最右一处离右端 %d 根 %s" % (VIEW, r, p["per_cat"]))
            near.append(r)
            bad += bool(diffs)
            if not quiet:
                print("%s %-18s %s %-3s span 1→2 根数 %5d→%5d%s · 对账%s · 最右差异离右端 %s 根%s"
                      % ("✗" if diffs else "✓", fn, sym, tf, len(d1["bars"]), len(d2["bars"]),
                         "（earliest）" if d1.get("earliest") else "",
                         "不一致" if any("对账" not in x and "最近" not in x and "多出" not in x for x in diffs) else "一致",
                         r, "  ← " + " ｜ ".join(diffs[:3]) if diffs else ""))
    finally:
        srv.shutdown()
        srv.server_close()
        server.fetch, server.start_prefetch = saved
    if not quiet:
        print("扩展档 %d 份：不过 %d 份 · 最右差异离右端最近 %s 根（门槛 %d）"
              % (len(cases), bad, min([x for x in near if x is not None], default=None), VIEW))
    return bad


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

    def arm_span_tail():
        """扩展档那一档动了最右的结构（最后一笔终点挪一跳）—— 对账和「最近 160 根相同」都必须红。"""
        real = server.build_payload

        def tail(bars, symbol, tf):
            d = real(bars, symbol, tf)
            if len(bars) > 5000 and d["pens"]:            # 只动 span=2 那份（假历史翻倍后才过 5000 根）
                d["pens"][-1]["p1"] += 1
            return d
        server.build_payload = tail
        try:
            return run_span(quiet=True)
        finally:
            server.build_payload = real
    arms.append(("扩展档最右一笔被改", arm_span_tail))

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
    rc = run()[0]
    rc = rc or (1 if run_span() else 0)
    sys.exit(rc)
