#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收盘后的那 30 秒窗口（card-7d3e8748-3d3，Nova 10-08 19:17）：后台重拉只看「距上次 ≥60s」、不看收盘时，
收盘前 1 秒被请求过的那一格，要到收盘后 59 秒才肯再拉；页面收盘后 2～10 秒补第一趟、5 秒一次补 4 次，
大约 22～30 秒就放弃 ⇒ 落空，又等一整根。

    python3 web/check_closedue.py              # rc=0 才算过；不碰真币安，时钟是假的（不用真等 15 分钟）
    python3 web/check_closedue.py --self-test  # 把 _close_due 摘掉（＝旧后台），主跑必须红

怎么造（真 HTTP、真 get_chart、真后台刷新线程；只有币安和钟是假的）：
  · 假钟：server 模块里的 time 换成一个 time() 回假时刻的壳（sleep 照真的）；假币安只给「假现在」之前开盘的 K 线；
  · 剧本：ZECUSDT 15m，收盘时刻 C。C−1s 请求一次（冷，同步拉）；C+4s 打开页面；之后照页面**真的**补数节奏敲
    （常量从 web/app.js 读：AUTO_LAG_MIN 之后第一趟、每 AUTO_RETRY_MS 再补、最多 AUTO_RETRY_MAX 次 —— 取最早放弃的那条，
    即错峰取下界）；每趟之间等后台刷新线程落地。
逐格：
  ① 收盘后打开，**10 秒内**拿到新那一根（最后一根 t == C）；
  ② 页面放弃之前（最后一趟补数）一直拿不到新那根 ⇒ 记「落空」—— 旧后台必须落空、新后台不许落空；
  ③ 不放大：C+4s 并发 50 个请求 ⇒ 这一根多拉币安**恰好 1 次**；之后到 C+59s 再怎么敲都是 0 次；
  ④ 连着 3 根、每 20 秒有人看一次：新后台比旧后台多拉的次数 ≤ 收盘次数（每格每根最多多 1 次）。
"""
import concurrent.futures as cf
import gzip
import http.client
import json
import os
import re
import sys
import threading
import time as _real_time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import server                                           # noqa: E402

server.Handler.log_message = lambda *a: None            # 访问日志不刷屏（只进本机日志那一条）

SYM, TF = "ZECUSDT", "15m"
STEP = server.TFS[TF]
# 只取最后 2000 根（约 21 天）：量的是「什么时候拉」，不是引擎；整份 2 万根每次刷新要整段重划，一跑两分钟
_B = json.load(open(os.path.join(ROOT, "data", "zec15.json"), encoding="utf-8"))[-2000:]


def _app_const(name):
    m = re.search(r"const %s = (\d+);" % name, open(os.path.join(HERE, "app.js"), encoding="utf-8").read())
    if not m:
        raise SystemExit("web/app.js 里找不到 %s —— 页面的补数节奏改了，这把尺得跟着改" % name)
    return int(m.group(1))


LAG_MIN, RETRY_MS, RETRY_MAX = (_app_const(n) / (1 if n == "AUTO_RETRY_MAX" else 1000.0)
                                for n in ("AUTO_LAG_MIN", "AUTO_RETRY_MS", "AUTO_RETRY_MAX"))
RETRY_MAX = int(RETRY_MAX)

CLOCK = {"now": 0.0}
CALLS = {"n": 0}
_lock = threading.Lock()


def fake_time():
    return CLOCK["now"]


# server 里只用 time.time / time.sleep / time.strftime 之类：壳子把 time() 换成假的，其余照转真模块
FAKE = types.SimpleNamespace(**{k: getattr(_real_time, k) for k in dir(_real_time) if not k.startswith("_")})
FAKE.time = fake_time


def fake_fetch(symbol, tf, a, b):
    """像真币安：只给「假现在」之前已经开盘的 K 线（最后一根是正在走的那根），按 [a, b] 截。"""
    with _lock:
        CALLS["n"] += 1
    now_ms = int(CLOCK["now"] * 1000)
    shift = BASE_CLOSE_MS - STEP - _B[-2]["t"]           # 数据倒数第二根 ⇒ C 之前那根（C−STEP 开盘、C 收盘）
    return [dict(x, t=x["t"] + shift) for x in _B
            if a <= x["t"] + shift <= b and x["t"] + shift <= now_ms]


# 收盘时刻 C：取一个整 15 分钟的时刻（远离真钟，免得有谁偷偷用了真 time.time）
BASE_CLOSE_MS = 2_000_000_000_000 // STEP * STEP


def req(port):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    try:
        c.putrequest("GET", "/api/chart?symbol=%s&tf=%s" % (SYM, TF), skip_accept_encoding=True)
        c.putheader("Accept-Encoding", "gzip")
        c.endheaders()
        r = c.getresponse()
        body = r.read()
        if r.getheader("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        d = json.loads(body)
        return r.status, d["bars"][-1]["t"], d.get("refreshing")
    finally:
        c.close()


def settle(limit=30.0):
    """等后台刷新线程落地（真时间）。"""
    sl = server.SLOTS[(SYM, TF, 1)]
    t0 = _real_time.time()
    while _real_time.time() - t0 < limit:
        with sl.lock:
            if not sl.refreshing:
                return True
        _real_time.sleep(0.02)
    return False


def at(port, t):
    """假钟拨到 t（秒），敲一次，等后台落地 → (最后一根 t 是不是 C, refreshing)。"""
    CLOCK["now"] = t
    st, last, refreshing = req(port)
    settle()
    if st != 200:
        raise SystemExit("HTTP %d" % st)
    return last, refreshing


def fresh_slot():
    sl = server.SLOTS[(SYM, TF, 1)]
    with sl.lock:
        sl.reset()


def main(quiet=False):
    say = (lambda *a: None) if quiet else print
    server.time = FAKE
    server.fetch = fake_fetch
    server.start_prefetch = lambda *a: None             # 只量这一格
    srv = server.make_server(0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    C = BASE_CLOSE_MS / 1000.0
    NEW = BASE_CLOSE_MS                                  # 新那一根的开盘时刻 ＝ C
    bad = []

    def cell(name, ok, note=""):
        say("%s %s %s" % ("✓" if ok else "✗", name, note))
        if not ok:
            bad.append(name)

    try:
        # ---- ①② 收盘前 1 秒请求过、收盘后 4 秒打开，照页面真的补数节奏敲 ----
        fresh_slot()
        CALLS["n"] = 0
        last, _ = at(port, C - 1)
        if last != NEW - STEP:
            raise SystemExit("剧本没搭对：C−1s 那一趟最后一根应是 C−STEP（%d），实为 %d" % (NEW - STEP, last))
        opened = C + 4
        times = [opened, opened + LAG_MIN] + [opened + LAG_MIN + RETRY_MS * (k + 1) for k in range(RETRY_MAX)]
        got = None
        trail = []
        for t in times:
            last, refreshing = at(port, t)
            trail.append("+%.0fs:%s%s" % (t - C, "新" if last == NEW else "旧", "(refreshing)" if refreshing else ""))
            if last == NEW and got is None:
                got = t
        cell("① 收盘前 1 秒请求过，收盘后 4 秒打开 ⇒ 10 秒内拿到新那根",
             got is not None and got - opened <= 10, "｜".join(trail))
        cell("② 页面放弃之前拿到过新那根（不落空）", got is not None,
             "最后一趟在收盘后 %.0fs" % (times[-1] - C))

        # ---- ③ 不放大：收盘后并发 50 ⇒ 这一根多拉 1 次；之后到 C+59s 0 次 ----
        fresh_slot()
        CALLS["n"] = 0
        at(port, C - 1)
        n0 = CALLS["n"]
        CLOCK["now"] = C + 4
        with cf.ThreadPoolExecutor(max_workers=50) as ex:
            rs = list(ex.map(lambda _: req(port), range(50)))
        settle()
        n1 = CALLS["n"]
        for t in range(int(C + 5), int(C + 59), 3):
            at(port, t)
        n2 = CALLS["n"]
        cell("③ 收盘后并发 50 ⇒ 这一根多拉币安恰好 1 次；之后到收盘后 59 秒 0 次",
             n1 - n0 == 1 and n2 == n1 and all(r[0] == 200 for r in rs),
             "并发那一下拉 %d 次，之后 %d 次" % (n1 - n0, n2 - n1))
    finally:
        srv.shutdown()
        srv.server_close()
    say("全部通过" if not bad else "%d 格不过" % len(bad))
    return 1 if bad else 0


def count_over_bars(port_unused=None):
    """④：连着 3 根、每 20 秒请求一次 → 拉币安的次数。"""
    server.time = FAKE
    server.fetch = fake_fetch
    server.start_prefetch = lambda *a: None
    srv = server.make_server(0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        fresh_slot()
        CALLS["n"] = 0
        C = BASE_CLOSE_MS / 1000.0
        t = C - 30
        while t < C + 2 * STEP / 1000.0 + 30:
            at(port, t)
            t += 20
        return CALLS["n"]
    finally:
        srv.shutdown()
        srv.server_close()


def run_all(quiet=False):
    rc = main(quiet)
    say = (lambda *a: None) if quiet else print
    n_new = count_over_bars()
    real = server._close_due
    server._close_due = lambda *a: False
    try:
        n_old = count_over_bars()
    finally:
        server._close_due = real
    ok = 0 <= n_new - n_old <= 3
    say("%s ④ 连着 3 根、每 20 秒看一次：拉币安 旧后台 %d 次、新后台 %d 次（多 %d，≤ 收盘 3 次）"
        % ("✓" if ok else "✗", n_old, n_new, n_new - n_old))
    return rc or (0 if ok else 1)


def self_test():
    """把 _close_due 摘掉（＝只看 60 秒的旧后台）⇒ 主跑必须红，而且红在 ①②。"""
    real = server._close_due
    server._close_due = lambda *a: False
    try:
        rc = main(quiet=True)
    finally:
        server._close_due = real
    print("%s 臂：摘掉 _close_due（旧后台）⇒ %s" % ("✓" if rc else "✗", "红" if rc else "没红（尺子没牙）"))
    return 0 if rc else 3


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    sys.exit(run_all())
