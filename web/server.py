#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公开站点的后台：只读 API + 静态页面（web/ 下的前端），一个进程。

    python3 web/server.py --port <端口>          # 端口必填，没有默认值；地址默认回环

这是**公网**入口（小栋 10-03 定），所以：
  · 只绑回环地址 —— 默认 127.0.0.1，传了非回环地址直接拒绝起服务；
  · 完全只读：只有 GET / HEAD，没有任何写文件、跑命令、改配置的接口；
  · 品种 × 周期白名单（SYMBOLS × TFS），白名单外 400；不接受任意参数去拉币安；
  · 每个（品种, 周期）最多每 REFRESH_S 秒拉一次币安，同一时刻只有一个线程在拉（其余等它的结果）；
    拉失败就回上一次的结果，并标 stale=true + 那份数据的拉取时间 fetched_at；
  · 前端只看得到固定措辞的错误，**不出本机路径、密钥、堆栈**（详细原因只进 stderr）。

接口：
  GET /api/chart?symbol=ZECUSDT&tf=15m
      → tools/make_web_fixture.shape() 的那一份（形状只在那里定义一处，前端离线样本也是它烤的），
        顶上再加 fetched_at（拉币安的时间，UTC …Z，与 updated 同一写法）/ stale（这次拉失败、回的是上一次的结果）。
        结构直接是 core.analyze / core.signals 的输出，不另写算法。
  GET /api/meta            → 白名单（前端拿来做下拉）
  GET /  /<静态文件>       → web/ 下的前端文件（只送 STATIC_EXT 里的类型，.py / .md / 点文件一律 404）
"""
import argparse
import gzip
import ipaddress
import json
import math
import os
import socketserver
import sys
import threading
import time
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

sys.path.insert(0, os.path.join(ROOT, "tools"))
from config import tick_of                              # noqa: E402
from fetch_klines import fetch as binance_fetch         # noqa: E402
from make_web_fixture import iso, shape                 # noqa: E402

HOST = "127.0.0.1"                       # 默认回环；make_server 拒绝任何非回环地址

# 品种 → config.TICK 里的前缀（精度只从 config 取一处，不在这里再写一份）
SYMBOLS = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
TFS = {"15m": 15 * 60_000, "30m": 30 * 60_000, "1h": 3600_000, "2h": 7200_000, "4h": 14400_000}
DAYS = 210                               # 每个周期都看最近 210 天（与 README 出图流程同一窗口）
REFRESH_S = 60                           # 同一（品种, 周期）至少隔这么久才再碰一次币安
RETRY_S = 30                             # 拉失败之后，至少隔这么久才再试（失败也不许刷）
STATIC = os.path.dirname(os.path.abspath(__file__))     # web/ 自己：前端文件就在这里
# 只送这些类型（.py / .md / 无扩展名 / 其它一律 404 —— 本进程自己的源码不出门）
STATIC_EXT = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
              ".css": "text/css; charset=utf-8", ".json": "application/json", ".svg": "image/svg+xml",
              ".png": "image/png", ".ico": "image/x-icon", ".woff2": "font/woff2"}

fetch = binance_fetch                    # 模块级名字：对账 / 压测脚本换成假的，数调用次数


def log(*a):
    print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), *a, file=sys.stderr, flush=True)


# ───────────────────────── 结构 → JSON ─────────────────────────

def _clean(v):
    """tuple → list、NaN/inf → None；dict / list 递归（allow_nan=False 时不让一个 NaN 把整格打成 500）。"""
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    return v


def build_payload(bars, symbol, tf):
    """bars（fetch_klines 的格式）→ 前端那一份。形状 = make_web_fixture.shape，这里只补精度。"""
    return _clean(shape(bars, tick_of(SYMBOLS[symbol] + "_.json"), symbol, tf))


# ───────────────────────── 缓存：每个（品种, 周期）一格 ─────────────────────────

class Slot:
    def __init__(self):
        self.lock = threading.Lock()     # 同一时刻只有一个线程在拉 / 算这一格
        self.bars = None                 # 上一次成功拉到的 K 线
        self.body = None                 # 上一次成功的 JSON（已编码，原文 + gzip）
        self.gz = None
        self.data_at = 0.0               # body 对应的数据是什么时候拉到的（epoch 秒）
        self.tried_at = 0.0              # 上一次碰币安的时间（成功失败都算）
        self.failed = False              # 上一次碰币安是不是失败了


SLOTS = {(s, t): Slot() for s in SYMBOLS for t in TFS}
FETCHES = {"n": 0}                       # 自计数：压测脚本拿来核「没多拉」


def _refresh(slot, symbol, tf):
    """在 slot.lock 里调用。增量：已有 K 线时只从最后一根（可能未收盘）往后拉，再截回 DAYS 窗口。"""
    now_ms = int(time.time() * 1000)
    start = now_ms - DAYS * 86400_000
    if slot.bars:
        start = max(start, slot.bars[-1]["t"])
    FETCHES["n"] += 1
    new = fetch(symbol, tf, start, now_ms)
    if not new:
        raise RuntimeError("币安返回空")
    merged = {b["t"]: b for b in (slot.bars or [])}
    merged.update({b["t"]: b for b in new})              # 最后一根未收盘的那根用新值覆盖
    lo = now_ms - DAYS * 86400_000
    bars = [merged[t] for t in sorted(merged) if t >= lo]
    payload = build_payload(bars, symbol, tf)
    return bars, payload


def get_chart(symbol, tf):
    """→ (json bytes, gzip bytes) 或 None（一次都没拉成功过）。"""
    slot = SLOTS[(symbol, tf)]
    with slot.lock:
        now = time.time()
        wait = RETRY_S if slot.failed else REFRESH_S
        if now - slot.tried_at >= wait:
            slot.tried_at = now
            try:
                bars, payload = _refresh(slot, symbol, tf)
                # fetched_at / stale 放最前：失败时只替换这一处，不重算结构
                body = json.dumps(dict(fetched_at=iso(now * 1000), stale=False, **payload), ensure_ascii=False,
                                  separators=(",", ":"), allow_nan=False).encode("utf-8")
                slot.bars, slot.body, slot.gz, slot.data_at, slot.failed = bars, body, gzip.compress(body, 6), now, False
                return slot.body, slot.gz
            except Exception:
                slot.failed = True
                log("refresh failed", symbol, tf, traceback.format_exc().replace("\n", " | "))
        if slot.body is None:
            return None
        if not slot.failed:
            return slot.body, slot.gz
        # 失败：回上一次的结果，stale 翻成 true；fetched_at 仍是那份数据的拉取时间
        body = slot.body.replace(b'"stale":false', b'"stale":true', 1)
        return body, gzip.compress(body, 6)


def prewarm():
    """起服务时把白名单里每一格按顺序拉一遍：**一格一格来，不并发**（Nova 10-03 定），
    免得冷启动一下打币安十几页 × 15。走的是 get_chart 同一条路（同一把锁、同一套节流），
    有人在预热途中访问某格，要么等这格的锁、要么直接吃已有缓存，不会多拉。"""
    t0 = time.time()
    ok = 0
    for symbol, tf in SLOTS:
        if get_chart(symbol, tf) is not None:
            ok += 1
    log("prewarm %d/%d in %.1fs" % (ok, len(SLOTS), time.time() - t0))


# ───────────────────────── HTTP ─────────────────────────

ERR = {400: "bad request", 404: "not found", 405: "method not allowed", 503: "data not available yet"}


class Handler(BaseHTTPRequestHandler):
    server_version = "chanlun"
    sys_version = ""

    def log_message(self, fmt, *a):              # 只进本机日志
        log(self.address_string(), fmt % a)

    def _send(self, code, body, ctype="application/json; charset=utf-8", gz=None, cache="no-store"):
        use_gz = gz is not None and "gzip" in self.headers.get("Accept-Encoding", "")
        data = gz if use_gz else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if use_gz:
            self.send_header("Content-Encoding", "gzip")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _err(self, code):
        self._send(code, json.dumps({"error": ERR[code]}).encode())

    def do_GET(self):
        try:
            self._route()
        except Exception:
            log("handler error", self.path[:200], traceback.format_exc().replace("\n", " | "))
            try:
                self._send(500, b'{"error":"internal error"}')
            except Exception:
                pass

    do_HEAD = do_GET

    def _bad_method(self):
        self._err(405)

    do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _bad_method

    def _route(self):
        u = urllib.parse.urlsplit(self.path)
        if u.path == "/api/chart":
            try:
                q = urllib.parse.parse_qs(u.query, keep_blank_values=True, strict_parsing=True, max_num_fields=4)
            except ValueError:
                return self._err(400)
            if set(q) != {"symbol", "tf"} or any(len(v) != 1 for v in q.values()):
                return self._err(400)                     # 多参数、少参数、重复参数一律不认
            symbol, tf = q["symbol"][0].upper(), q["tf"][0]
            if symbol not in SYMBOLS or tf not in TFS:
                return self._err(400)
            got = get_chart(symbol, tf)
            if got is None:
                return self._err(503)
            return self._send(200, got[0], gz=got[1])
        if u.path == "/api/meta":
            if u.query:
                return self._err(400)
            return self._send(200, json.dumps(dict(symbols=list(SYMBOLS), tfs=list(TFS),
                                                   days=DAYS, refresh_s=REFRESH_S)).encode())
        return self._static(u.path)

    def _static(self, path):
        name = "index.html" if path in ("", "/") else urllib.parse.unquote(path).lstrip("/")
        full = os.path.realpath(os.path.join(STATIC, name))
        root = os.path.realpath(STATIC)
        rel = os.path.relpath(full, root)
        ext = os.path.splitext(full)[1].lower()
        if (not full.startswith(root + os.sep) or ext not in STATIC_EXT or not os.path.isfile(full)
                or any(part.startswith(".") for part in rel.split(os.sep))):
            return self._err(404)                         # 出了 web/、不认的类型、点文件、不存在：统一 404
        with open(full, "rb") as f:
            body = f.read()
        self._send(200, body, ctype=STATIC_EXT[ext], cache="public, max-age=60")


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False          # 端口被别人占着就直接起不来，不抢
    # listen 队列：socketserver 默认 5。并发一上来（压测 150 个连接同时进）macOS 直接丢 SYN，
    # 客户端重试到超时（实测 Errno 60）。128 = macOS 的 somaxconn 默认值。
    request_queue_size = 128

    def server_bind(self):
        # HTTPServer.server_bind 会调 socket.getfqdn(host) 反查主机名 —— 这台机器上实测 35.00 秒
        # （Iris 先量到的），进程起来了却 35 秒不 listen。只要 TCP 绑定，名字直接用写死的 HOST。
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def make_server(port, host=HOST):
    if not ipaddress.ip_address(host).is_loopback:
        raise SystemExit("只许绑回环地址（给的是 %s）" % host)
    return Server((host, port), Handler)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="只读 API + 前端静态页（只绑回环）")
    ap.add_argument("--port", type=int, required=True, help="监听端口（必填）")
    ap.add_argument("--host", default=HOST, help="回环地址，默认 %(default)s；非回环直接拒绝")
    ap.add_argument("--no-prewarm", action="store_true", help="起服务时不预热（默认按顺序把每格拉一遍）")
    a = ap.parse_args()
    srv = make_server(a.port, a.host)
    log("listening on %s:%d" % srv.server_address[:2])
    if not a.no_prewarm:                         # 先 listen 再预热：预热期间页面照常能开
        threading.Thread(target=prewarm, daemon=True).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
