#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""压测 / 乱参数 / 币安挂掉：都不出错、不多拉币安、不漏本机信息。

    python3 web/check_abuse.py        # rc=0 才算过；不碰真币安（fetch 换成计数的假货，带 0.3 秒延迟）

逐格：
  ⓪ 预热按顺序每格拉 1 次（同时在拉的峰值 = 1），预热后访问不再拉；
  ① 绑定地址是 127.0.0.1（不是 0.0.0.0）；
  ② 同一（品种, 周期）并发 100 次 ⇒ 全 200、拉币安 1 次；
  ③ 15 个（品种, 周期）各并发 10 次 ⇒ 拉 15 次（每格 1 次，不多不少）；
  ④ 乱参数 / 白名单外 / 路径穿越 / 写方法 ⇒ 全 4xx、拉币安 0 次、响应里没有路径 / 堆栈；
  ⑤ 刷新期内再并发 100 次 ⇒ 拉 0 次；
  ⑥ 过了刷新期、币安挂了 ⇒ 先回旧缓存（refreshing=true），后台失败后回上次结果（stale=true），只试 1 次；
  ⑦ 一次都没成功过的格 + 币安挂了 ⇒ 503 固定措辞、并发 100 次只试 1 次；
  ⑧ 币安恢复 ⇒ 过了重试间隔，先回旧的、后台拉成后回到 stale=false / refreshing=false；
  ⑨ 币安慢 5 秒 ⇒ 过期请求仍 <100ms 回旧缓存，币安只被调 1 次（stale-while-revalidate）。
"""
import concurrent.futures as cf
import gzip
import http.client
import json
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import server                                           # noqa: E402

ROOT = os.path.dirname(HERE)
# 'File \\"' 是 JSON 里转义过的堆栈行：堆栈被塞进 JSON 字段时，裸的 'File "' 匹配不到
LEAKS = [ROOT, os.path.expanduser("~"), "Traceback", 'File "', 'File \\"', "/Users/", "/home/", ".py"]

_B = json.load(open(os.path.join(ROOT, "data", "zec_4h.json"), encoding="utf-8"))
# 假币安的「全部历史」：zec_4h 往前接 3 份（时间往前挪、价格缩一点），共约 840 天（4h 计）——
# 够 span 1/2/4 往左补、span 8 撞到「没有更早的了」（earliest）。
_N = len(_B)
BARS = []
for _c in range(3, -1, -1):
    _f = 0.7 ** _c
    BARS += [dict(b, t=b["t"] - _c * _N * 14400_000, o=b["o"] * _f, h=b["h"] * _f, l=b["l"] * _f, c=b["c"] * _f)
             for b in _B]
calls = {"n": 0, "down": False, "inflight": 0, "peak": 0, "delay": 0.3}
lock = threading.Lock()


def fake_fetch(symbol, tf, a, b):
    with lock:
        calls["n"] += 1
        calls["last"] = (a, b)
        calls["inflight"] += 1
        calls["peak"] = max(calls["peak"], calls["inflight"])
    try:
        time.sleep(calls["delay"])                       # 模拟慢的币安，让并发真的撞在一起（⑨ 调成 5 秒）
    finally:
        with lock:
            calls["inflight"] -= 1
    if calls["down"]:
        raise OSError("connect refused (假币安挂了) /secret/path")
    step = server.TFS[tf]
    t0 = BARS[-1]["t"]
    # 时间戳挪到「现在」附近，免得被 DAYS 窗口截掉；**按请求的 [a, b] 截**（像真币安一样，往左补只给缺的那段）
    shift = (int(time.time() * 1000) // step) * step - t0
    return [dict(x, t=x["t"] + shift) for x in BARS if a <= x["t"] + shift <= b]


def req(port, method, path):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    try:
        c.putrequest(method, path, skip_accept_encoding=True)
        c.putheader("Accept-Encoding", "gzip")
        c.endheaders()
        r = c.getresponse()
        body = r.read()
        if r.getheader("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        return r.status, body
    finally:
        c.close()


def burst(port, n, method, path):
    with cf.ThreadPoolExecutor(max_workers=n) as ex:
        return list(ex.map(lambda _: req(port, method, path), range(n)))


def main():
    calls.update(n=0, down=False, inflight=0, peak=0, delay=0.3)   # 每一跑从同一个起点开始（自测会连跑多臂）
    server.fetch = fake_fetch
    # 「收盘后还没拉过就算 due」那条（_close_due）在这里关掉：这把尺用真钟、假 K 线跟着真钟对齐，跑这 40 秒里要是
    #   碰上一个真的 15 分钟收盘，那一格会合法地多拉一次，⑤「刷新期内拉 0 次」这类格子就成了看运气的尺。
    #   收盘那条由 web/check_closedue.py 在假钟上专门量（含「每格每根最多多拉 1 次」）。
    server._close_due = lambda *a: False
    server.tick_fetch = lambda symbol, tf: fake_fetch(symbol, tf, 0, 1 << 62)[-2:]   # 跳价：一次调用＝一个请求
    real_prefetch = server.start_prefetch
    server.start_prefetch = lambda *a: None              # 老格子（⓪–⑨）量的是单档的拉取次数：先把预拉关掉，⑪ 再专门测它
    BASE = [k for k in server.SLOTS if k[2] == 1]
    srv = server.make_server(0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    bad = []

    def cell(name, ok, note=""):
        print("%s %-44s %s" % ("✓" if ok else "✗", name, note))
        if not ok:
            bad.append(name)

    def leaks(body):
        s = body.decode("utf-8", "replace")
        return [w for w in LEAKS if w in s]

    # ①
    try:
        server.make_server(0, "0.0.0.0")
        refused = False
    except SystemExit:
        refused = True
    cell("① 默认绑回环、给 0.0.0.0 拒绝起服务", srv.server_address[0] == "127.0.0.1" and refused,
         "%s · 0.0.0.0 %s" % (srv.server_address, "被拒" if refused else "**起来了**"))

    # ⓪ 预热：每格拉 1 次、同一时刻最多 1 个在拉（顺序，不并发）；预热完再访问任一格拉 0 次
    calls["n"] = calls["peak"] = 0
    server.prewarm()
    pre_n, pre_peak = calls["n"], calls["peak"]
    calls["n"] = 0
    burst(port, 30, "GET", "/api/chart?symbol=AAPLUSDT&tf=30m")
    cell("⓪ 预热：每格 1 次、顺序拉、预热后访问拉 0 次",
         pre_n == len(BASE) and pre_peak == 1 and calls["n"] == 0,
         "预热拉=%d（应 %d）同时在拉峰值=%d 之后拉=%d" % (pre_n, len(BASE), pre_peak, calls["n"]))
    for sl in server.SLOTS.values():                     # 清回冷态，后面各格照原样量 ——
        sl.reset()                                       # ★ reset 不换锁：「拿掉单飞锁」那条变异不会被悄悄修好

    # ②
    calls["n"] = 0
    rs = burst(port, 100, "GET", "/api/chart?symbol=ZECUSDT&tf=4h")
    codes = {c for c, _ in rs}
    same = len({b for _, b in rs}) == 1
    cell("② 同格并发 100 次：全 200、拉 1 次、内容一致", codes == {200} and calls["n"] == 1 and same,
         "codes=%s 拉=%d 内容种数=%d" % (codes, calls["n"], len({b for _, b in rs})))
    meta = json.loads(rs[0][1])
    cell("   带 fetched_at、stale=false、refreshing=false",
         meta.get("stale") is False and meta.get("refreshing") is False and str(meta.get("fetched_at", "")).endswith("Z"),
         str({k: meta.get(k) for k in ("symbol", "tf", "fetched_at", "stale", "refreshing")}))

    # ③
    calls["n"] = 0
    paths = ["/api/chart?symbol=%s&tf=%s" % (s, t) for s in server.SYMBOLS for t in server.TFS]
    with cf.ThreadPoolExecutor(max_workers=150) as ex:
        rs = list(ex.map(lambda p: req(port, "GET", p), [p for p in paths for _ in range(10)]))
    want = len(paths) - 1                                # ZECUSDT 4h 已经在缓存里
    cell("③ 15 格各并发 10 次：每格最多拉 1 次", {c for c, _ in rs} == {200} and calls["n"] == want,
         "拉=%d（应 %d）" % (calls["n"], want))

    # ④
    calls["n"] = 0
    junk = [("GET", p) for p in [
        "/api/chart", "/api/chart?symbol=ZECUSDT", "/api/chart?tf=4h",
        "/api/chart?symbol=ETHUSDT&tf=4h", "/api/chart?symbol=ZECUSDT&tf=1d", "/api/chart?symbol=ZECUSDT&tf=4H",
        "/api/chart?symbol=ZECUSDT&tf=4h&limit=99999", "/api/chart?symbol=ZECUSDT&symbol=BTCUSDT&tf=4h",
        "/api/chart?symbol=ZECUSDT&tf=4h&url=http://evil", "/api/chart?symbol=%ff%fe&tf=4h",
        "/api/chart?symbol=ZECUSDT;rm%20-rf&tf=4h", "/api/chart?" + "a=1&" * 5000,
        "/api/chart?symbol=" + "Z" * 10000 + "&tf=4h", "/api/meta?x=1",
        "/../config.py", "/%2e%2e/config.py", "/..%2fweb/server.py", "/server.py", "/static/../server.py",
        "/%2e%2e/%2e%2e/%2e%2e/etc/passwd", "/index.html/..", "/.git/config", "/nope.html", "//etc/passwd",
        "/server.py", "/check_abuse.py", "/README.md", "/vendor/lightweight-charts/LICENSE", "/.DS_Store",
    ]] + [(m, "/api/chart?symbol=ZECUSDT&tf=4h") for m in ("POST", "PUT", "DELETE", "PATCH", "OPTIONS")]
    worst = []
    for m, p in junk:
        try:
            code, body = req(port, m, p)
        except Exception as e:                            # 连接被掐也算「没出 200」，但要记下来
            code, body = type(e).__name__, b""
        lk = leaks(body)
        if not (isinstance(code, int) and 400 <= code < 500) or lk:
            worst.append("%s %s ⇒ %s %s" % (m, p[:60], code, lk))
    cell("④ 乱参数/白名单外/穿越/写方法 %d 条：全 4xx、无泄漏" % len(junk), not worst, " ｜ ".join(worst[:4]))
    cell("   ④ 期间拉币安 0 次", calls["n"] == 0, "拉=%d" % calls["n"])

    # ④b：前端文件真送得出来（不是把什么都 404 掉才「安全」）
    ok_static = [req(port, "GET", p)[0] for p in ("/", "/app.js", "/style.css", "/fixtures/btc_4h.json")]
    cell("④b 前端文件照常 200（/、app.js、style.css、样本）", ok_static == [200] * 4, str(ok_static))

    # ⑤
    calls["n"] = 0
    burst(port, 100, "GET", "/api/chart?symbol=BTCUSDT&tf=1h")
    cell("⑤ 刷新期内再并发 100 次：拉 0 次", calls["n"] == 0, "拉=%d" % calls["n"])

    def settle(sl, limit=15.0):
        """等后台刷新收尾（refreshing 落回 False）；超时就算这格没收尾。"""
        t = time.time()
        while time.time() - t < limit:
            with sl.lock:
                if not sl.refreshing:
                    return True
            time.sleep(0.05)
        return False

    def flags(rs):
        ms = [json.loads(b) for c, b in rs if c == 200]
        return ms, {(m["stale"], m["refreshing"]) for m in ms}

    # ⑥：把 ZEC 4h 的「上次碰币安」拨回刷新期之前，再让币安挂掉
    slot = server.SLOTS[("ZECUSDT", "4h", 1)]
    old_at = json.loads(slot.body)["fetched_at"]
    slot.tried_at -= server.REFRESH_S + 1
    calls["n"], calls["down"] = 0, True
    rs = burst(port, 100, "GET", "/api/chart?symbol=ZECUSDT&tf=4h")
    ms, fl = flags(rs)
    lk = sorted({w for _, b in rs for w in leaks(b)})
    cell("⑥ 过期 + 币安挂了：先回旧缓存（stale=F refreshing=T）",
         len(ms) == 100 and fl == {(False, True)} and all(m["fetched_at"] == old_at for m in ms) and not lk,
         "200 有 %d 条 · (stale, refreshing)=%s · 泄漏 %s" % (len(ms), fl, lk))
    done = settle(slot)
    rs = burst(port, 100, "GET", "/api/chart?symbol=ZECUSDT&tf=4h")
    ms, fl = flags(rs)
    cell("   ⑥ 后台失败后：回上次结果（stale=T refreshing=F）、旧 fetched_at",
         done and len(ms) == 100 and fl == {(True, False)} and all(m["fetched_at"] == old_at for m in ms),
         "收尾=%s (stale, refreshing)=%s" % (done, fl))
    cell("   ⑥ 两轮并发 200 次只试 1 次（失败退避）", calls["n"] == 1, "试=%d" % calls["n"])

    # ⑦：一格从没成功过
    slot7 = server.SLOTS[("AAPLUSDT", "15m", 1)]
    slot7.reset()
    calls["n"] = 0
    rs = burst(port, 100, "GET", "/api/chart?symbol=AAPLUSDT&tf=15m")
    lk = sorted({w for _, b in rs for w in leaks(b)})
    cell("⑦ 从没成功过 + 币安挂了：503 固定措辞",
         {c for c, _ in rs} == {503} and {b for _, b in rs} == {b'{"error": "data not available yet"}'} and not lk,
         "codes=%s 泄漏 %s" % ({c for c, _ in rs}, lk))
    cell("   ⑦ 并发 100 次只试 1 次", calls["n"] == 1, "试=%d" % calls["n"])

    # ⑧：恢复
    calls["down"] = False
    slot.tried_at -= server.RETRY_S + 1
    time.sleep(1.1)                                      # fetched_at 精确到秒：保证换了一秒再比
    code, body = req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=4h")
    m1 = json.loads(body)
    done = settle(slot)
    code2, body2 = req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=4h")
    m = json.loads(body2)
    cell("⑧ 币安恢复：重试那下先回旧的（stale=T refreshing=T），收尾后 stale=F refreshing=F、新 fetched_at",
         code == code2 == 200 and (m1["stale"], m1["refreshing"]) == (True, True) and done
         and (m["stale"], m["refreshing"]) == (False, False) and m["fetched_at"] > old_at,
         "重试那下 %s → 收尾后 %s · fetched_at %s → %s" % ((m1["stale"], m1["refreshing"]),
                                                       (m["stale"], m["refreshing"]), old_at, m["fetched_at"]))

    # ⑨：币安慢 5 秒，过期请求仍然立刻回旧缓存、币安只被调一次
    calls["delay"], calls["n"] = 5.0, 0
    old9 = m["fetched_at"]
    slot.tried_at -= server.REFRESH_S + 1
    time.sleep(1.1)

    def timed(_):
        t = time.time()
        c, b = req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=4h")
        return time.time() - t, c, b
    with cf.ThreadPoolExecutor(max_workers=50) as ex:
        rs9 = list(ex.map(timed, range(50)))
    worst = max(t for t, _, _ in rs9)
    ms9 = [json.loads(b) for _, c, b in rs9 if c == 200]
    fl9 = {(x["stale"], x["refreshing"]) for x in ms9}
    cell("⑨ 币安慢 5 秒：过期请求 50 个最慢 <100ms、回旧缓存（stale=F refreshing=T）",
         len(ms9) == 50 and worst < 0.1 and fl9 == {(False, True)} and all(x["fetched_at"] == old9 for x in ms9),
         "最慢 %.0f ms · (stale, refreshing)=%s" % (worst * 1000, fl9))
    done = settle(slot, 10)
    m9 = json.loads(req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=4h")[1])
    cell("   ⑨ 币安只被调 1 次；收尾后 refreshing=F、新 fetched_at",
         calls["n"] == 1 and done and (m9["stale"], m9["refreshing"]) == (False, False) and m9["fetched_at"] > old9,
         "调=%d 收尾=%s %s → %s" % (calls["n"], done, old9, m9["fetched_at"]))
    calls["delay"] = 0.3

    # ⑩ span 契约（Nova 10-04）：不在 {1,2,4,8,16} 的一律 400、拉 0 次；在里面但超封顶的钳到封顶、如实回显
    calls["n"] = 0
    junk = ["0", "3", "-1", "999", "abc", "1.0", "02", "%202", "", "32", "1e1", "0x2", "2&span=4", "6"]
    codes = [(j, req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=15m&span=" + j)[0]) for j in junk]
    badc = [(j, c) for j, c in codes if c != 400]
    cell("⑩ span 不在五个值里 %d 条：全 400、拉 0 次" % len(codes), not badc and calls["n"] == 0,
         "不是 400 的：%s · 拉=%d" % (badc, calls["n"]))
    clamp = []
    for tf_, ask in (("15m", 8), ("15m", 16), ("30m", 16)):
        code_, body_ = req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=%s&span=%d" % (tf_, ask))
        try:
            m_ = json.loads(body_) if code_ == 200 else {}
        except ValueError:
            m_ = {}
        clamp.append((tf_, ask, code_, m_.get("span"), m_.get("span_max")))
    want = [("15m", 8, 200, 4, 4), ("15m", 16, 200, 4, 4), ("30m", 16, 200, 8, 8)]
    cell("   ⑩ 超封顶：钳到封顶、回显 span=span_max", clamp == want, "%s" % clamp)

    # ⑪ 同一格同一档冷启动并发 100 次：只拉 1 次（只补更早那一段 —— 上一档已在缓存）
    #   用 4h：假历史是 4 小时一根，拿去冒充 1h 的话 span=1 第一根离窗口左沿超过一步 ⇒ 被（如实地）判成 earliest
    for kk in (1, 2, 4):
        server.SLOTS[("BTCUSDT", "4h", kk)].reset()
    req(port, "GET", "/api/chart?symbol=BTCUSDT&tf=4h")      # span=1 先进缓存（预拉还关着）
    calls["n"] = 0
    rs = burst(port, 100, "GET", "/api/chart?symbol=BTCUSDT&tf=4h&span=2")
    ms = [json.loads(b) for c, b in rs if c == 200]
    m1 = json.loads(req(port, "GET", "/api/chart?symbol=BTCUSDT&tf=4h")[1])
    t1 = [x["t"] for x in m1["bars"]]
    t2 = [x["t"] for x in ms[0]["bars"]] if ms else []
    only_older = calls.get("last") is not None and t1 and calls["last"][1] < t1[0]
    ok = (len(ms) == 100 and calls["n"] == 1 and {(m["span"], m["span_max"]) for m in ms} == {(2, 16)}
          and len(t2) > len(t1) and t2[-len(t1):] == t1 and t2 == sorted(set(t2)) and only_older)
    cell("⑪ span=2 冷并发 100：拉 1 次、span/span_max 回显、更早一段接在前面且时间连续不重",
         ok, "拉=%d（只要更早那段=%s）回显=%s 根数 %d→%d 尾部对齐=%s" % (
             calls["n"], only_older, {(m["span"], m["span_max"]) for m in ms},
             len(t1), len(t2), t2[-len(t1):] == t1 if t2 else None))

    # ⑫ 预拉：送出 span=k 之后后台单飞把 2k 拉好；之后请求 2k 拉 0 次、立刻回
    server.start_prefetch = real_prefetch
    for (s_, t_, kk), sl_ in server.SLOTS.items():      # 按真有的格子清，不信 spans_of（变异臂会换掉它）
        if (s_, t_) == ("ZECUSDT", "4h"):
            sl_.reset()
    calls["n"] = calls["peak"] = 0
    req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=4h")
    s2 = server.SLOTS[("ZECUSDT", "4h", 2)]
    t0 = time.time()
    while time.time() - t0 < 10:
        with s2.lock:
            if s2.body is not None and not s2.prefetching:
                break
        time.sleep(0.05)
    n_after_pre = calls["n"]
    server.start_prefetch = lambda *a: None              # 量「再要 span=2」这一下本身拉了几次：别让它连带预拉 span=4
    t0 = time.time()
    code, body = req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=4h&span=2")
    dt = time.time() - t0
    m = json.loads(body)
    n_req = calls["n"] - n_after_pre
    server.start_prefetch = real_prefetch
    cell("⑫ 预拉：送出 span=1 后后台把 span=2 拉好（共拉 2 次）；再要 span=2 拉 0 次、立刻回",
         n_after_pre == 2 and code == 200 and m["span"] == 2 and n_req == 0 and dt < 0.1,
         "预拉后累计拉=%d（应 2）· 再要 span=2 拉 %d 次、用了 %.0f ms" % (n_after_pre, n_req, dt * 1000))

    # ⑬ 到最早 / 到封顶：earliest 为真之后不再往下预拉；到封顶那档也不再预拉
    for kk in (4, 8, 16):
        req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=4h&span=%d" % kk)
        sl = server.SLOTS[("ZECUSDT", "4h", kk)]
        settle(sl, 10)
    time.sleep(0.5)
    def _earliest(kk):
        code_, body_ = req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=4h&span=%d" % kk)
        try:
            return json.loads(body_).get("earliest") if code_ == 200 else "HTTP %d" % code_
        except ValueError:
            return "不是 JSON"
    flags_ = {kk: _earliest(kk) for kk in (1, 2, 4, 8, 16)}
    n_before = calls["n"]
    req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=4h&span=16")
    req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=15m&span=4")   # 15m 封顶 4：不许去预拉 8
    time.sleep(0.5)
    extra = calls["n"] - n_before
    cell("⑬ earliest 如实（约 840 天的假历史：span 1/2/4 假、8/16 真）；封顶 / 到最早后不再多拉",
         flags_ == {1: False, 2: False, 4: False, 8: True, 16: True} and extra <= 1,
         "earliest=%s · 之后多拉 %d 次（15m span=4 冷拉 1 次，不该再有）" % (flags_, extra))
    server.start_prefetch = lambda *a: None

    # ⑭ 背驰看法 measure（Atlas 10-04 定的量法）：四种各回显对、结构逐字节相同、币安 0 次、
    #    每种的买卖点 ≡ 引擎在吐出的那段 K 线上直接 signals(r, 层, measure)；不比四种彼此（结果可以碰巧一样）。
    #    前提：引擎在这份夹具上至少有一种看法的买卖点跟 macd 不同 —— 否则探针「忽略 measure」红不出来，记未执行。
    import sys as _sys
    from core.analyze import analyze as _analyze
    from config import tick_of as _tick_of
    _S = _sys.modules["core.signals"]
    calls["n"] = 0
    bad_m = [m for m in ("abc", "MACD", "", "macd2", "1") if
             req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=4h&span=2&measure=" + m)[0] != 400]
    cell("⑭ measure 不认的 5 种写法全 400", not bad_m, "不是 400 的：%s" % bad_m)
    # 夹具换成真 zec15（15m）：zec_4h 的假历史上四种看法买卖点全一样，分不开（实测）；zec15 类中枢层分得开
    global BARS
    saved_bars = BARS
    BARS = json.load(open(os.path.join(ROOT, "data", "zec15.json"), encoding="utf-8"))
    for (s_, t_, k_), sl_ in server.SLOTS.items():
        if (s_, t_) == ("ZECUSDT", "15m"):
            sl_.reset()
    req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=15m")            # 先进缓存（这一下拉 1 次）
    calls["n"] = 0
    got = {}
    for m in _S.MEASURES:
        code_, body_ = req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=15m&cut=extend&measure=" + m)   # 结构逐字节同只在不切那份上成立（turn 的切点跟着看法走）
        got[m] = json.loads(body_) if code_ == 200 else {}
    BARS = saved_bars
    bars_ = [dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"]) for b in got["macd"].get("bars", [])]
    r_ = _analyze(bars_, tick=_tick_of("zec_.json"))
    eng = {m: {lv: json.loads(json.dumps(server._clean(_S.signals(r_, lv, m)))) for lv in ("seg", "pen")}
           for m in _S.MEASURES}
    separable = any(eng[m] != eng["macd"] for m in _S.MEASURES if m != "macd")
    strip = lambda d: {k: v for k, v in d.items() if k not in ("signals", "measure", "fetched_at", "refreshing")}
    echo_ok = all(got[m].get("measure") == m for m in _S.MEASURES)
    same_struct = all(strip(got[m]) == strip(got["macd"]) for m in _S.MEASURES)
    match_eng = {m: got[m].get("signals") == eng[m] for m in _S.MEASURES}
    if not separable:
        cell("⑭ 四种看法（未执行：夹具上四种看法的买卖点全一样，分不开 —— 不算绿）", False, "")
    else:
        cell("⑭ 四种看法：回显对、结构逐字节同、币安 0 次、各自买卖点 ≡ 引擎",
             echo_ok and same_struct and calls["n"] == 0 and all(match_eng.values()),
             "回显=%s 结构同=%s 拉=%d ≡引擎=%s" % (echo_ok, same_struct, calls["n"], match_eng))

    # ⑮ 副图 /api/macd：跟 /api/chart 同一格同一份 K 线 —— 乱参 400、冷并发 100 拉 1 次、
    #    先要了图再要副图拉 0 次、头部（span / span_max / earliest / fetched_at）跟图一样、t 跟 bars 同一份
    calls["n"] = 0
    junk_m = ["symbol=ZECUSDT&tf=4h&span=3", "symbol=ZECUSDT&tf=4h&measure=lines", "symbol=ETHUSDT&tf=4h",
              "symbol=ZECUSDT&tf=1d", "symbol=ZECUSDT", "symbol=ZECUSDT&tf=4h&x=1", "symbol=ZECUSDT&tf=4h&span=2&span=4"]
    badj = [j for j in junk_m if req(port, "GET", "/api/macd?" + j)[0] != 400]
    cell("⑮ /api/macd 乱参 %d 条全 400、拉 0 次" % len(junk_m), not badj and calls["n"] == 0,
         "不是 400 的：%s · 拉=%d" % (badj, calls["n"]))
    for (s_, t_, k_), sl_ in server.SLOTS.items():
        if (s_, t_) == ("BTCUSDT", "2h"):
            sl_.reset()
    calls["n"] = 0
    rs = burst(port, 100, "GET", "/api/macd?symbol=BTCUSDT&tf=2h&span=2")
    n_cold = calls["n"]
    calls["n"] = 0
    ch = json.loads(req(port, "GET", "/api/chart?symbol=BTCUSDT&tf=2h&span=2")[1])
    mc = json.loads(req(port, "GET", "/api/macd?symbol=BTCUSDT&tf=2h&span=2")[1])
    n_warm = calls["n"]
    head_ok = all(mc.get(k) == ch.get(k) for k in ("span", "span_max", "earliest", "fetched_at"))
    t_ok = mc.get("t") == [x["t"] for x in ch.get("bars", [])]
    cell("   ⑮ 副图冷并发 100 拉 1 次；跟图同一格：再要图和副图拉 0 次、头部同、t 同",
         {c for c, _ in rs} == {200} and n_cold == 1 and n_warm == 0 and head_ok and t_ok
         and mc.get("hist_def") == "dif-dea" and mc.get("span") == 2,
         "冷拉=%d 热拉=%d 头部同=%s t 同=%s span=%s" % (n_cold, n_warm, head_ok, t_ok, mc.get("span")))

    # ⑯ /api/tick（小栋 10-05 A：最后一根实时跳价）：乱参 400 拉 0 次；冷并发 100 只拉 1 次、全 200；
    #    2.5 秒内再来 100 拉 0 次；币安挂了 ⇒ 200 + stale=true、fetched_at 停在上次成功、不漏堆栈；
    #    整个过程 /api/chart 那一格的字节不变（跳价不碰结构）
    calls.update(n=0, delay=0.3, down=False)
    for ts_ in server.TICKS.values():
        ts_.bar, ts_.tried_at, ts_.failed, ts_.ok_at = None, 0.0, False, 0.0
    junk_t = ["symbol=ZECUSDT", "tf=15m", "symbol=ZECUSDT&tf=15m&span=2", "symbol=ZECUSDT&tf=15m&measure=macd",
              "symbol=ETHUSDT&tf=15m", "symbol=ZECUSDT&tf=1d", "symbol=ZECUSDT&tf=15m&tf=4h", ""]
    badt = [j for j in junk_t if req(port, "GET", "/api/tick?" + j)[0] != 400]
    cell("⑯ /api/tick 乱参 %d 条全 400、拉 0 次" % len(junk_t), not badt and calls["n"] == 0,
         "不是 400 的：%s · 拉=%d" % (badt, calls["n"]))
    before = req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=4h")[1]
    calls["n"] = 0
    rs = burst(port, 100, "GET", "/api/tick?symbol=ZECUSDT&tf=4h")
    n1 = calls["n"]
    rs2 = burst(port, 100, "GET", "/api/tick?symbol=ZECUSDT&tf=4h")
    n2 = calls["n"] - n1
    tk = json.loads(rs[0][1]) if rs[0][0] == 200 else {}
    shape_ok = set(tk) == {"symbol", "tf", "t", "o", "h", "l", "c", "v", "fetched_at", "stale", "engine"} \
        and tk.get("t") == BARS[-1]["t"] + ((int(time.time() * 1000) // 14400_000) * 14400_000 - BARS[-1]["t"])
    cell("   ⑯ 冷并发 100 拉 1 次、全 200；2.5 秒内再 100 拉 0 次；字段对、t 是最后一根",
         {c for c, _ in rs + rs2} == {200} and n1 == 1 and n2 == 0 and shape_ok,
         "冷拉=%d 再拉=%d 字段=%s" % (n1, n2, sorted(tk)))
    calls["down"] = True
    time.sleep(server.TICK_S + 0.1)
    c3, b3 = req(port, "GET", "/api/tick?symbol=ZECUSDT&tf=4h")
    d3 = json.loads(b3) if c3 == 200 else {}
    calls["down"] = False
    after = req(port, "GET", "/api/chart?symbol=ZECUSDT&tf=4h")[1]
    strip = lambda b: {k: v for k, v in json.loads(b).items() if k not in ("fetched_at", "stale", "refreshing")}
    cell("   ⑯ 币安挂了：200、stale=true、fetched_at 停在上次、不漏；图那一格结构没被碰",
         c3 == 200 and d3.get("stale") is True and d3.get("fetched_at") == tk.get("fetched_at")
         and not leaks(b3) and strip(before) == strip(after),
         "code=%s stale=%s 漏=%s 结构同=%s" % (c3, d3.get("stale"), leaks(b3), strip(before) == strip(after)))

    # 收尾：等每一格的后台刷新都落地再返回。不等的话，上一条变异臂留下的后台线程（⑨ 里睡 5 秒的那种）
    # 会在下一条臂的 ⓪ 里继续调假币安、把计数和峰值打脏 —— 自测里「错误回堆栈」那臂 ⓪ 莫名变红就是它。
    calls["delay"] = 0.0
    for sl in server.SLOTS.values():
        settle(sl, 20)
        t0 = time.time()
        while sl.prefetching and time.time() - t0 < 20:
            time.sleep(0.05)
    srv.shutdown()
    srv.server_close()
    print("%d 格不过" % len(bad) if bad else "全部通过")
    return 1 if bad else 0


class _NoLock:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def self_test():
    """把服务改坏六种，main() 必须各自 rc≠0：没有单飞锁 ／ 没有刷新节流 ／ 报错把堆栈回给前端 ／ 静态放行源码 ／ 预热并发 ／ 刷新挂在请求上。"""
    import importlib
    import io
    import contextlib as cl

    def no_lock():
        for sl in server.SLOTS.values():
            sl.lock = _NoLock()

    def no_throttle():
        server.REFRESH_S = server.RETRY_S = 0

    def tick_no_cache():
        server.TICK_S = 0

    def leaky():
        orig = server.Handler._err

        def err(self, code):
            import traceback as tb
            self._send(code, json.dumps({"error": server.ERR[code], "where": tb.format_stack()[-1]}).encode())
        server.Handler._err = err
        return orig

    def parallel_prewarm():
        def pw():
            ths = [threading.Thread(target=server.get_chart, args=k) for k in server.SLOTS if k[2] == 1]
            [t.start() for t in ths]
            [t.join() for t in ths]
        server.prewarm = pw

    def sync_refresh():
        server.start_refresh = lambda sl, sy, tf: server._bg_refresh(sl, sy, tf)

    def any_span():
        server.SPAN_VALUES = tuple(range(1, 1000))

    def no_clamp():
        server.SPAN_MAX = {k: 16 for k in server.SPAN_MAX}

    def no_prefetch():
        server.start_prefetch = lambda *a: None

    def no_seed():
        class _NoHalf(dict):                             # _refresh 只用 SLOTS.get 找上一档：让它永远找不到
            def get(self, k, d=None):
                return None
        server.SLOTS = _NoHalf(server.SLOTS)

    def never_earliest():
        real = server._refresh
        server._refresh = lambda slot, symbol, tf: (lambda b, body, e: (
            b, body.replace(b'"earliest":true', b'"earliest":false', 1), False))(*real(slot, symbol, tf))

    def ignore_measure():
        real = server.get_chart

        def g(symbol, tf, span=1, prefetch=True, touch=True, measure="macd"):
            out = real(symbol, tf, span, prefetch, touch, "macd")    # 全按 macd 算
            if out is None:
                return None
            body = out[0].replace(b'"measure":"macd"', ('"measure":"%s"' % measure).encode(), 1)   # 只改回显
            return body, gzip.compress(body, 6)
        server.get_chart = g

    def macd_ignores_span():
        real = server.get_chart

        def g(symbol, tf, span=1, prefetch=True, touch=True, measure="macd"):
            return real(symbol, tf, 1 if measure == server.MACD_KEY else span, prefetch, touch, measure)
        server.get_chart = g

    def macd_own_fetch():
        orig = server._macd_body

        def own(slot, symbol, tf):
            server.fetch(symbol, tf, 0, int(time.time() * 1000))          # 副图自己另去拉一遍
            return orig(slot, symbol, tf)
        server._macd_body = own

    def serve_source():
        server.STATIC_EXT[".py"] = "text/plain; charset=utf-8"

    miss = 0
    for name, f in [("拿掉单飞锁", no_lock), ("拿掉刷新节流", no_throttle), ("错误回堆栈", leaky),
                    ("静态放行 .py", serve_source), ("预热改成并发", parallel_prewarm),
                    ("刷新挂在请求上", sync_refresh), ("span 不设白名单", any_span), ("超封顶不钳", no_clamp), ("不预拉", no_prefetch),
                    ("不拿上一档当底（整窗重拉）", no_seed), ("earliest 恒为假", never_earliest),
                    ("忽略 measure（全按 macd 算、只改回显）", ignore_measure),
                    ("副图不认 span（总给 1 档）", macd_ignores_span), ("副图自己另去拉币安", macd_own_fetch),
                    ("跳价不缓存（每趟都打币安）", tick_no_cache)]:
        importlib.reload(server)
        f()
        buf = io.StringIO()
        with cl.redirect_stdout(buf):
            rc = main()
        reds = [l.split()[1] for l in buf.getvalue().splitlines() if l.startswith("✗")]
        print("%s 变异 %-10s ⇒ rc=%d 红格 %s" % ("✓" if rc else "✗", name, rc, " ".join(reds)))
        miss += 0 if rc else 1
    importlib.reload(server)
    return 3 if miss else 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
