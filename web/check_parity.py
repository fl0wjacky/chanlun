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
    # 结构对账比的是引擎原样那份（不切）⇒ 显式要 cut=extend；默认（turn）那份另有 run_default 核
    req = urllib.request.Request("http://127.0.0.1:%d/api/chart?symbol=%s&tf=%s%s&cut=extend"
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


def get_path(port, path):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), headers={"Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
    return json.loads(body)


def run_macd(quiet=False):
    """副图 /api/macd：每份数据上 ① t 跟 /api/chart 的 bars 逐根同一份；② dif / dea / hist ≡ 引擎
    macd_lines(那一份 K 线, 12, 26, 9)、hist = dif − dea，逐个浮点相等；③ hist_def / params / 头部回显对；
    ④ 成交量：给夹具每根注入 v，/api/chart 的 bars[].v 原样带回。"""
    eng = sys.modules["core.signals"]                     # 模块对象（core/__init__ 把 signals 导成了函数）
    files = sorted(os.path.basename(p) for p in glob.glob(data("*.json")))
    cases = [(fn, dataset(fn)) for fn in files if dataset(fn)]
    bars_by_key = {}
    for fn, key in cases:
        b = json.load(open(data(fn), encoding="utf-8"))
        bars_by_key[key] = [dict(x, v=round(1000 + 7.5 * i, 2)) for i, x in enumerate(b)]   # 注入成交量
    bad = n = 0
    with running(bars_by_key) as port:
        for fn, (sym, tf) in cases:
            ch = get(port, sym, tf)
            mc = get_path(port, "/api/macd?symbol=%s&tf=%s" % (sym, tf))
            bars = [dict(t=x["t"], o=x["o"], h=x["h"], l=x["l"], c=x["c"]) for x in ch["bars"]]
            dif, dea = eng.macd_lines(bars, 12, 26, 9)
            hist_eng = eng.macd_hist(bars, 12, 26, 9)             # 背驰判断读的就是这一份柱子
            diffs = []
            if mc.get("t") != [x["t"] for x in ch["bars"]]:
                diffs.append("t 跟 /api/chart 的 bars 不是同一份")
            if mc.get("dif") != dif or mc.get("dea") != dea:
                diffs.append("dif/dea ≠ 引擎 macd_lines")
            if mc.get("hist") != hist_eng:
                diffs.append("hist ≠ 引擎 macd_hist（副图跟背驰判断不是同一份柱子）")
            if (mc.get("hist_def"), mc.get("params")) != ("dif-dea", [12, 26, 9]):
                diffs.append("约定字段不对：%r %r" % (mc.get("hist_def"), mc.get("params")))
            if not (mc.get("engine") == ch.get("engine") == server.ENGINE and re.fullmatch(r"[0-9a-f]{10}", ch["engine"])):
                diffs.append("引擎版本不对：chart %r macd %r 进程 %r" % (ch.get("engine"), mc.get("engine"), server.ENGINE))
            if any(mc.get(k) != ch.get(k) for k in ("span", "span_max", "earliest", "fetched_at")):
                diffs.append("头部回显跟 /api/chart 不一致")
            if [x.get("v") for x in ch["bars"]] != [x["v"] for x in bars_by_key[(sym, tf)]]:
                diffs.append("bars[].v 没原样带回")
            n += len(dif)
            bad += bool(diffs)
            if not quiet:
                print("%s %-18s %s %-3s 副图 %5d 根%s" % ("✗" if diffs else "✓", fn, sym, tf, len(dif),
                                                       "  ← " + " ｜ ".join(diffs) if diffs else ""))
    if not quiet:
        print("副图 MACD %d 份、%d 根：不一致 %d 份（逐根浮点相等）" % (len(cases), n, bad))
    return bad


def run_default(quiet=False):
    """默认切法（小栋 10-05 11:09Z：按转折切设成默认，card-21fbf426-889）：
    ① /api/meta 的 cut_default 是 turn、且在 cut_modes 里；② 不带 cut 的 /api/chart 回显 cut=turn、带 cuts；
    ③ 不带 cut 那份 ＝ 显式 cut=turn 那份（结构逐字段同）；④ 它的 seg_centers ＝ 引擎 cut_centers 在同一份 K 线上的结果；
    ⑤ 「延伸」还在：cut=extend 回显 extend、不带 cuts。"""
    import core.cut as _cut
    eng = sys.modules["core.signals"]
    files = sorted(os.path.basename(p) for p in glob.glob(data("*.json")))
    cases = [(fn, dataset(fn)) for fn in files if dataset(fn)]
    bars_by_key = {key: json.load(open(data(fn), encoding="utf-8")) for fn, key in cases}
    bad = 0
    with running(bars_by_key) as port:
        m = get_path(port, "/api/meta")
        if m.get("cut_default") != "turn" or "turn" not in (m.get("cut_modes") or []) or "extend" not in (m.get("cut_modes") or []):
            bad += 1
            if not quiet:
                print("✗ /api/meta cut_default=%r cut_modes=%r" % (m.get("cut_default"), m.get("cut_modes")))
        for fn, (sym, tf) in cases:
            dflt = get_path(port, "/api/chart?symbol=%s&tf=%s" % (sym, tf))
            turn = get_path(port, "/api/chart?symbol=%s&tf=%s&cut=turn" % (sym, tf))
            ext = get_path(port, "/api/chart?symbol=%s&tf=%s&cut=extend" % (sym, tf))
            bars = [dict(t=x["t"], o=x["o"], h=x["h"], l=x["l"], c=x["c"]) for x in dflt["bars"]]
            r = analyze(bars, tick=tick_of(fn))
            cur, cuts = _cut.cut_centers(r, eng.signals(r, "pen", "macd"))
            strip = lambda d: {k: v for k, v in d.items() if k not in ("fetched_at", "stale", "refreshing")}
            diffs = []
            if dflt.get("cut") != "turn" or "cuts" not in dflt:
                diffs.append("不带 cut 回显 %r、cuts %s" % (dflt.get("cut"), "有" if "cuts" in dflt else "没有"))
            if strip(dflt) != strip(turn):
                diffs.append("不带 cut ≠ cut=turn")
            if json.loads(json.dumps(server._clean(cur))) != dflt.get("seg_centers"):
                diffs.append("默认的 seg_centers ≠ 引擎 cut_centers")
            if ext.get("cut") != "extend" or "cuts" in ext:
                diffs.append("cut=extend 回显 %r" % ext.get("cut"))
            bad += bool(diffs)
            if not quiet:
                print("%s %-18s %s %-3s 默认切法%s" % ("✗" if diffs else "✓", fn, sym, tf,
                                                    "  ← " + " ｜ ".join(diffs) if diffs else " turn（刀 %d）" % len(cuts)))
    if not quiet:
        print("默认切法 %d 份：不一致 %d 份" % (len(cases), bad))
    return bad


def run_meta(quiet=False):
    """/api/meta：measures 仍是字符串列表（前端按字符串过滤，换成对象整组会消失）；measure_orig 跟 measures
    一一对应、全是布尔，且只有 slope 是 false（小栋 10-04 ①A：斜率不是 108 课原文的判法）。"""
    with running({}) as port:
        m = get_path(port, "/api/meta")
    ms, mo = m.get("measures"), m.get("measure_orig")
    diffs = [] if m.get("engine") == server.ENGINE else ["meta 的 engine %r ≠ 进程 %r" % (m.get("engine"), server.ENGINE)]
    if not (isinstance(ms, list) and ms and all(isinstance(x, str) for x in ms)):
        diffs.append("measures 不是字符串列表：%r" % (ms,))
    elif not isinstance(mo, dict) or sorted(mo) != sorted(ms) or any(type(v) is not bool for v in mo.values()):
        diffs.append("measure_orig 跟 measures 对不上或不是布尔：%r" % (mo,))
    elif [k for k in ms if not mo[k]] != ["slope"]:
        diffs.append("非原文的应当只有 slope，给的是 %r" % [k for k in ms if not mo[k]])
    if not quiet:
        print("%s /api/meta measures=%s measure_orig=%s%s" % ("✗" if diffs else "✓", ms, mo,
                                                             "  ← " + " ｜ ".join(diffs) if diffs else ""))
    return len(diffs)


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

    def arm_hist_x2():
        orig = server._macd_body

        def x2(slot, symbol, tf):
            d = json.loads(orig(slot, symbol, tf))
            d["hist"] = [2 * h for h in d["hist"]]
            return json.dumps(d, separators=(",", ":")).encode()
        server._macd_body = x2
        try:
            return run_macd(quiet=True)
        finally:
            server._macd_body = orig
    arms.append(("副图 hist 乘 2", arm_hist_x2))

    def arm_macd_other_bars():
        real = server.macd_lines
        server.macd_lines = lambda bars, *a: real(bars[1:] + bars[:1], *a)   # 喂的不是同一份（轮转一根）
        try:
            return run_macd(quiet=True)
        finally:
            server.macd_lines = real
    arms.append(("副图用的不是同一份 K 线", arm_macd_other_bars))

    def arm_hist_not_engine():
        """Atlas 10-04 的打法：引擎柱子改成 ×2（背驰用的那份变了），副图却自己减 DIF−DEA ⇒ 必须红。"""
        eng = sys.modules["core.signals"]
        real_mh, real_h = eng.macd_hist, server._hist
        eng.macd_hist = lambda bars, *a: [2 * h for h in real_mh(bars, *a)]
        server._hist = lambda bars: [x - y for x, y in zip(*eng.macd_lines(bars, *server.MACD_PARAMS))]
        try:
            return run_macd(quiet=True)
        finally:
            eng.macd_hist, server._hist = real_mh, real_h
    arms.append(("副图自己减柱子、引擎柱子 ×2", arm_hist_not_engine))

    def arm_meta_missing():
        real = server.MEASURES
        server.MEASURES = real + ("vol",)                 # 白名单多一种、原文表里没它 ⇒ 不许 500 了事、也不许漏标
        try:
            return run_meta(quiet=True)
        except Exception:
            return 1
        finally:
            server.MEASURES = real
    arms.append(("新看法没进原文表", arm_meta_missing))

    def arm_meta_all_orig():
        real = dict(server.MEASURE_ORIG)
        server.MEASURE_ORIG["slope"] = True
        try:
            return run_meta(quiet=True)
        finally:
            server.MEASURE_ORIG.clear()
            server.MEASURE_ORIG.update(real)
    arms.append(("斜率也标成原文", arm_meta_all_orig))

    def arm_engine_stale():
        """副图那份头部的引擎版本不跟着进程（比如缓存里留着旧值）⇒ 前端分不出换没换引擎，必须红。"""
        orig = server._macd_body

        def stale(slot, symbol, tf):
            d = json.loads(orig(slot, symbol, tf))
            d["engine"] = "0" * 10
            return json.dumps(d, separators=(",", ":")).encode()
        server._macd_body = stale
        try:
            return run_macd(quiet=True)
        finally:
            server._macd_body = orig
    arms.append(("副图头部引擎版本是旧的", arm_engine_stale))

    def arm_default_extend():
        real = server.DEFAULT_CUT
        server.DEFAULT_CUT = "extend"                      # 后台缺省退回延伸（前端改了、后台没跟上的那种）
        try:
            return run_default(quiet=True)
        finally:
            server.DEFAULT_CUT = real
    arms.append(("后台缺省仍是 extend", arm_default_extend))

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
    rc = rc or (1 if run_macd() else 0)
    rc = rc or (1 if run_meta() else 0)
    rc = rc or (1 if run_default() else 0)
    sys.exit(rc)
