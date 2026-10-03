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

BARS = json.load(open(os.path.join(ROOT, "data", "zec_4h.json"), encoding="utf-8"))
calls = {"n": 0, "down": False, "inflight": 0, "peak": 0, "delay": 0.3}
lock = threading.Lock()


def fake_fetch(symbol, tf, a, b):
    with lock:
        calls["n"] += 1
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
    # 时间戳挪到「现在」附近，免得被 DAYS 窗口截掉
    shift = (int(time.time() * 1000) // step) * step - t0
    return [dict(b, t=b["t"] + shift) for b in BARS]


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
         pre_n == len(server.SLOTS) and pre_peak == 1 and calls["n"] == 0,
         "预热拉=%d（应 %d）同时在拉峰值=%d 之后拉=%d" % (pre_n, len(server.SLOTS), pre_peak, calls["n"]))
    for sl in server.SLOTS.values():                     # 清回冷态，后面各格照原样量 ——
        lk = sl.lock                                     # ★ 锁留原物：__init__ 会换回真锁，把「拿掉单飞锁」那条变异悄悄修好
        sl.__init__()
        sl.lock = lk

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
    slot = server.SLOTS[("ZECUSDT", "4h")]
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
    slot7 = server.SLOTS[("AAPLUSDT", "15m")]
    lk7 = slot7.lock
    slot7.__init__()
    slot7.lock = lk7
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

    # 收尾：等每一格的后台刷新都落地再返回。不等的话，上一条变异臂留下的后台线程（⑨ 里睡 5 秒的那种）
    # 会在下一条臂的 ⓪ 里继续调假币安、把计数和峰值打脏 —— 自测里「错误回堆栈」那臂 ⓪ 莫名变红就是它。
    calls["delay"] = 0.0
    for sl in server.SLOTS.values():
        settle(sl, 20)
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

    def leaky():
        orig = server.Handler._err

        def err(self, code):
            import traceback as tb
            self._send(code, json.dumps({"error": server.ERR[code], "where": tb.format_stack()[-1]}).encode())
        server.Handler._err = err
        return orig

    def parallel_prewarm():
        def pw():
            ths = [threading.Thread(target=server.get_chart, args=k) for k in server.SLOTS]
            [t.start() for t in ths]
            [t.join() for t in ths]
        server.prewarm = pw

    def sync_refresh():
        server.start_refresh = lambda sl, sy, tf: server._bg_refresh(sl, sy, tf)

    def serve_source():
        server.STATIC_EXT[".py"] = "text/plain; charset=utf-8"

    miss = 0
    for name, f in [("拿掉单飞锁", no_lock), ("拿掉刷新节流", no_throttle), ("错误回堆栈", leaky),
                    ("静态放行 .py", serve_source), ("预热改成并发", parallel_prewarm),
                    ("刷新挂在请求上", sync_refresh)]:
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
