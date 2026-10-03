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
  ⑥ 过了刷新期、币安挂了 ⇒ 回上一次结果（200 + stale=true + 旧的 data_at），并发 100 次只试 1 次；
  ⑦ 一次都没成功过的格 + 币安挂了 ⇒ 503 固定措辞、并发 100 次只试 1 次；
  ⑧ 币安恢复 ⇒ 过了重试间隔后回到 stale=false。
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
LEAKS = [ROOT, os.path.expanduser("~"), "Traceback", 'File "', "/Users/", "/home/", ".py"]

BARS = json.load(open(os.path.join(ROOT, "data", "zec_4h.json"), encoding="utf-8"))
calls = {"n": 0, "down": False, "inflight": 0, "peak": 0}
lock = threading.Lock()


def fake_fetch(symbol, tf, a, b):
    with lock:
        calls["n"] += 1
        calls["inflight"] += 1
        calls["peak"] = max(calls["peak"], calls["inflight"])
    try:
        time.sleep(0.3)                                  # 模拟慢的币安，让并发真的撞在一起
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
    cell("   带 fetched_at、stale=false", meta.get("stale") is False and str(meta.get("fetched_at", "")).endswith("Z"),
         str({k: meta.get(k) for k in ("symbol", "tf", "fetched_at", "stale")}))

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

    # ⑥：把 ZEC 4h 的「上次碰币安」拨回刷新期之前，再让币安挂掉
    slot = server.SLOTS[("ZECUSDT", "4h")]
    old_at = json.loads(slot.body)["fetched_at"]
    slot.tried_at -= server.REFRESH_S + 1
    calls["n"], calls["down"] = 0, True
    rs = burst(port, 100, "GET", "/api/chart?symbol=ZECUSDT&tf=4h")
    metas = [json.loads(b) for c, b in rs if c == 200]
    lk = sorted({w for _, b in rs for w in leaks(b)})
    cell("⑥ 币安挂了：回上次结果、stale=true、旧 fetched_at",
         len(metas) == 100 and all(m["stale"] and m["fetched_at"] == old_at for m in metas) and not lk,
         "200 有 %d 条 · stale=%s · 泄漏 %s" % (len(metas), {m["stale"] for m in metas}, lk))
    cell("   ⑥ 并发 100 次只试 1 次", calls["n"] == 1, "试=%d" % calls["n"])

    # ⑦：一格从没成功过
    slot7 = server.SLOTS[("AAPLUSDT", "15m")]
    slot7.__init__()
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
    m = json.loads(body)
    cell("⑧ 币安恢复：过了重试间隔回到 stale=false", code == 200 and m["stale"] is False and m["fetched_at"] > old_at,
         "stale=%s fetched_at %s → %s" % (m["stale"], old_at, m["fetched_at"]))

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
    """把服务改坏五种，main() 必须各自 rc≠0：没有单飞锁 ／ 没有刷新节流 ／ 报错把堆栈回给前端 ／ 静态放行源码 ／ 预热并发。"""
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

    def serve_source():
        server.STATIC_EXT[".py"] = "text/plain; charset=utf-8"

    miss = 0
    for name, f in [("拿掉单飞锁", no_lock), ("拿掉刷新节流", no_throttle), ("错误回堆栈", leaky),
                    ("静态放行 .py", serve_source), ("预热改成并发", parallel_prewarm)]:
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
