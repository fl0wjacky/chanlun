#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公开站点的后台：只读 API + 静态页面（web/ 下的前端），一个进程。

    python3 web/server.py --port <端口>          # 端口必填，没有默认值；地址默认回环

这是**公网**入口（小栋 10-03 定），所以：
  · 只绑回环地址 —— 默认 127.0.0.1，传了非回环地址直接拒绝起服务；
  · 完全只读：只有 GET / HEAD，没有任何写文件、跑命令、改配置的接口；
  · 品种 × 周期白名单（SYMBOLS × TFS），白名单外 400；不接受任意参数去拉币安；
  · 每个（品种, 周期）最多每 REFRESH_S 秒拉一次币安，同一时刻只有一个线程在拉；有缓存时过期刷新放后台、
    请求立刻回旧缓存（标 refreshing=true）；拉失败就回上一次的结果，并标 stale=true + 那份数据的拉取时间 fetched_at；
  · 前端只看得到固定措辞的错误，**不出本机路径、密钥、堆栈**（详细原因只进 stderr）。

接口：
  GET /api/chart?symbol=ZECUSDT&tf=15m[&span=1|2|4|8|16][&measure=macd|slope|lines|peak]
      （span 缺省 1；不在这五个值里 400；超本周期封顶钳到封顶并回显。measure 缺省 macd；不认的 400；回显 measure）
      → tools/make_web_fixture.shape() 的那一份（形状只在那里定义一处，前端离线样本也是它烤的），
        顶上再加 fetched_at（拉币安的时间，UTC …Z，与 updated 同一写法）/ stale（上一次拉取失败、回的是之前的结果）/
        refreshing（缓存已过期、后台正在拉，这次先回旧的）/ span（回显）/ earliest（币安没有更早的了）/
        span_max（本周期封顶档）。span=k 看最近 k×210 天，缠论结构对整段重算，不拼接。
        结构直接是 core.analyze / core.signals 的输出，不另写算法。
  GET /api/macd?symbol=&tf=[&span=]   → 副图：同一格同一份 K 线上的 MACD(12,26,9)，dif / dea / hist（hist = DIF−DEA，
        不乘 2，hist_def 字段写明），带每根的 t；头部跟 /api/chart 一样（span / earliest / span_max / stale…）。
        副图打开才取，关着不付（ZEC 15m 全精度三列 gzip 约 +0.55 MB，所以不塞进 /api/chart）。
  GET /api/tick?symbol=&tf=  → 最后一根（未收盘）K 线 {t,o,h,l,c,v} ＋ fetched_at / stale / engine。同一格 2.5 秒内只碰
        一次币安（单飞，多人同看不放大）；失败回上次成功的值、stale=true；从没成功过 503。**不碰结构**（小栋 10-05 A：
        最后一根实时跳价，笔段中枢买卖点仍收盘才由 /api/chart 整份重算）。
  GET /api/meta            → 白名单（前端拿来做下拉）
        engine = 引擎版本（core/*.py 的 sha256 前 10 位，启动时算），/api/chart、/api/macd 头部也带同一个；
        measures 仍是字符串列表（契约不变）；measure_orig = {看法: 是否 108 课原文的判法}，slope 为 false（小栋 10-04 ①A）。
  GET /  /<静态文件>       → web/ 下的前端文件（只送 STATIC_EXT 里的类型，.py / .md / 点文件一律 404）
"""
import argparse
import gzip
import hashlib
import ipaddress
import re
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
from core.analyze import analyze                        # noqa: E402
from core.signals import MEASURES, MEASURE_ORIG, macd_lines, signals as engine_signals   # noqa: E402
import core.signals as _engine_signals_mod              # noqa: E402,F401  （见下行：模块对象从 sys.modules 取）
_ENGINE = sys.modules["core.signals"]                    # core/__init__ 把 signals 导成了函数，模块要从这里拿

HOST = "127.0.0.1"                       # 默认回环；make_server 拒绝任何非回环地址

# 品种 → config.TICK 里的前缀（精度只从 config 取一处，不在这里再写一份）
SYMBOLS = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
TFS = {"15m": 15 * 60_000, "30m": 30 * 60_000, "1h": 3600_000, "2h": 7200_000, "4h": 14400_000}
DAYS = 210                               # span=1 看最近 210 天（与 README 出图流程同一窗口）；span=k 看 k×210 天
# 往左加载的档位封顶（Nova 10-04 按实测表定：一次计算 ≤0.5s、gzip ≤约 1.6MB；15m 到 8 档 3MB/1.7s 太重不开）。
# span 只许 1、2、4…… 直到这里的封顶；白名单外 400。
SPAN_MAX = {"15m": 4, "30m": 8, "1h": 16, "2h": 16, "4h": 16}
SPAN_VALUES = (1, 2, 4, 8, 16)           # 契约（Nova 10-04）：span 只认这五个值，别的 400；在里面但超本周期封顶的钳到封顶
IDLE_S = 600                             # span>1 的格子闲置这么久就清掉（几十万根 K 线常驻太占内存）
def _engine_version():
    """引擎版本 = core/ 下全部 .py 源码的 sha256 前 10 位，**进程启动时算一次**（跑的就是这一份）。
    前端把它并进「同一份数据」的桶键：引擎一换就是换了一把尺，不能拿新旧两份比出「消失的点」（Iris 10-05）。
    只 pull 不重启时文件变了、进程里跑的还是旧代码 —— 所以只能启动时算，不能每次请求现算。"""
    h, root = hashlib.sha256(), os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core")
    for fn in sorted(f for f in os.listdir(root) if f.endswith(".py")):
        h.update(fn.encode() + b"\0" + open(os.path.join(root, fn), "rb").read() + b"\0")
    return h.hexdigest()[:10]


ENGINE = _engine_version()
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

def spans_of(tf):
    k, out = 1, []
    while k <= SPAN_MAX[tf]:
        out.append(k)
        k *= 2
    return out


class Slot:
    def __init__(self, span=1):
        # RLock：后台刷新线程收尾时也要拿它；自测里把「后台刷新」换成就地同步跑（变异臂）时不能自锁死
        self.lock = threading.RLock()
        self.span = span
        self.reset()

    def reset(self):
        """清掉数据（闲置清理用），**锁和 span 不动** —— 清理是在持锁时做的，换锁等于把锁丢了。"""
        self.bars = None                 # 上一次成功拉到的 K 线
        self.body = None                 # 上一次成功的 JSON（头上 stale=false, refreshing=false）
        self.variants = {}               # (stale, refreshing) → (json, gzip)：每种组合只压一次
        self.data_at = 0.0               # body 对应的数据是什么时候拉到的（epoch 秒）
        self.tried_at = 0.0              # 上一次碰币安的时间（成功失败都算）
        self.failed = False              # 上一次碰币安是不是失败了 ⇒ 响应里 stale
        self.refreshing = False          # 后台正在拉这一格 ⇒ 响应里 refreshing；也是后台刷新的单飞旗
        self.earliest = False            # 币安没有比这一份更早的数据了 ⇒ 响应里 earliest
        self.prefetching = False         # 后台正在预拉这一格（上一档送出之后触发）—— 预拉的单飞旗
        self.used_at = 0.0               # 上次被请求的时间（闲置清理用）
        self.mbodies = {}                # measure → 换了买卖点的那一份 JSON（默认 macd 就是 body 本身；数据一刷新就清）


SLOTS = {(s, t, k): Slot(k) for s in SYMBOLS for t in TFS for k in spans_of(t)}
FETCHES = {"n": 0}                       # 自计数：压测脚本拿来核「没多拉」


TICK_WAIT_S = 5                          # 冷启动时等第一份的上限（超了就 503，前端下一趟再来）
TICK_S = 2.5                             # /api/tick：同一（品种, 周期）这么久内只碰一次币安（小栋 10-05 A：多人同看只打一次）


class TickSlot:
    def __init__(self):
        self.lock = threading.Condition()   # 单飞：一个去拉；有旧值的直接拿旧值走，冷启动没值的等它（最多几秒）
        self.bar = None                  # 上一次成功拉到的最后一根（未收盘的那根）
        self.ok_at = 0.0                 # 上一次成功的时间（epoch 秒）—— 前端画「价格停在 HH:MM」用
        self.tried_at = 0.0              # 上一次碰币安的时间（成功失败都算；失败也不许 2.5 秒内重打）
        self.failed = False
        self.busy = False                # 正有一个请求在拉（单飞旗）


TICKS = {(s, t): TickSlot() for s in SYMBOLS for t in TFS}
TICK_FETCHES = {"n": 0}


def get_tick(symbol, tf):
    """最后一根 K 线（未收盘那根）的开高低收量。**不碰结构**：不改 SLOTS 里的 K 线、不重算笔段中枢买卖点。
    单飞但不排队：正有人在拉时，别的请求直接拿上一次的值走（币安慢的时候不把一串请求都挂住）。
    返回 JSON bytes；从来没成功拉到过 ⇒ None（503，前端下一趟再来）。"""
    ts, now = TICKS[(symbol, tf)], time.time()
    with ts.lock:
        go = not ts.busy and now - ts.tried_at >= TICK_S
        if go:
            ts.busy, ts.tried_at = True, now
    if go:
        TICK_FETCHES["n"] += 1
        bar, err = None, None
        try:
            end = int(now * 1000)
            got = fetch(symbol, tf, end - 2 * TFS[tf], end)
            if not got:
                raise RuntimeError("币安返回空")
            bar = got[-1]
        except Exception as e:                         # noqa: BLE001 —— 失败回上次的值、标 stale，不把栈回给用户
            err = e
        with ts.lock:
            ts.busy = False
            if bar is not None:
                ts.bar, ts.ok_at, ts.failed = bar, now, False
            else:
                ts.failed = True
            ts.lock.notify_all()
        if err is not None:
            log("tick %s %s 失败：%s" % (symbol, tf, err))
    with ts.lock:
        if ts.bar is None and ts.busy:                 # 冷启动：别人正在拉第一份 ⇒ 等它，别回 503
            ts.lock.wait_for(lambda: not ts.busy, timeout=TICK_WAIT_S)
        if ts.bar is None:
            return None
        b, ok_at, failed = ts.bar, ts.ok_at, ts.failed
    return json.dumps(dict(symbol=symbol, tf=tf, t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"], v=b.get("v"),
                           fetched_at=iso(int(ok_at * 1000)), stale=failed, engine=ENGINE),
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _refresh(slot, symbol, tf):
    """拉 + 算，不动 slot → (bars, body, earliest)。调用方保证同一格同一时刻只有一个在跑
    （冷启动那条持 slot.lock，后台那条靠 slot.refreshing）。
    · 已有 K 线：只从最后一根（可能未收盘）往后拉，再截回窗口（span × DAYS 天）；
    · 冷、span>1、上一档有 K 线：拿上一档的当底，**只向币安要更早缺的那一段**（往左加载的主路径）；
    · 冷、其它：整个窗口拉一次。
    earliest：要的起点之后币安才有数据（或更早那段拉回来是空的）⇒ 没有更早的了。"""
    now_ms = int(time.time() * 1000)
    step = TFS[tf]
    lo = now_ms - slot.span * DAYS * 86400_000
    earliest = slot.earliest
    half = SLOTS.get((symbol, tf, slot.span // 2)) if slot.span > 1 else None
    if slot.bars:
        FETCHES["n"] += 1
        new = fetch(symbol, tf, max(lo, slot.bars[-1]["t"]), now_ms)
        if not new:
            raise RuntimeError("币安返回空")
        base = slot.bars
    elif half is not None and half.bars:
        base, new = half.bars, []
        if half.earliest:
            earliest = True                  # 上一档已经到最早：更大的档是同一份数据，不碰币安
        else:
            FETCHES["n"] += 1
            new = fetch(symbol, tf, lo, base[0]["t"] - 1)
            earliest = not new or new[0]["t"] > lo + step
    else:
        FETCHES["n"] += 1
        base, new = [], fetch(symbol, tf, lo, now_ms)
        if not new:
            raise RuntimeError("币安返回空")
        earliest = new[0]["t"] > lo + step
    merged = {b["t"]: b for b in base}
    merged.update({b["t"]: b for b in new})              # 最后一根未收盘的那根用新值覆盖
    bars = [merged[t] for t in sorted(merged) if t >= lo]
    # fetched_at / stale / refreshing 放最前：两个旗只在响应时替换这一处，不重算结构
    body = json.dumps(dict(fetched_at=iso(now_ms), stale=False, refreshing=False,
                           span=slot.span, earliest=earliest, span_max=SPAN_MAX[tf], measure="macd", engine=ENGINE,
                           **build_payload(bars, symbol, tf)),
                      ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return bars, body, earliest


def _refresh_into(slot, symbol, tf):
    """拉一次并把结果（或失败）记进 slot。成功失败都在 slot.lock 里落账。"""
    try:
        bars, body, earliest = _refresh(slot, symbol, tf)
    except Exception:
        log("refresh failed", symbol, tf, traceback.format_exc().replace("\n", " | "))
        with slot.lock:
            slot.failed = True
            slot.variants = {}
        return
    with slot.lock:
        slot.bars, slot.body, slot.data_at, slot.failed = bars, body, time.time(), False
        slot.earliest = earliest
        # 刚填好的格子从现在起算闲置：预拉（不算「被请求」）填进来的格子 used_at 还是 0，
        # 不补这一下，下一个请求进来先跑闲置清理 ⇒ 刚预拉好的当场被清掉、又同步拉一遍（check_abuse ⑫ 抓到的）
        slot.used_at = max(slot.used_at, time.time())
        slot.variants = {}
        slot.mbodies = {}


def _bg_refresh(slot, symbol, tf):
    try:
        _refresh_into(slot, symbol, tf)
    finally:
        with slot.lock:
            slot.refreshing = False
            slot.variants = {}


def start_refresh(slot, symbol, tf):
    """在 slot.lock 里调用，slot.refreshing 已置 True。后台线程去拉，请求不等它。
    （自测的「刷新挂在请求上」变异就是把这个函数换成就地跑 _bg_refresh。）"""
    threading.Thread(target=_bg_refresh, args=(slot, symbol, tf), daemon=True).start()


MACD_PARAMS = (12, 26, 9)                # 跟引擎背驰判断用的同一组（signals.series_for / macd_hist 的缺省）
MACD_KEY = "__macd__"                    # mbodies / variants 里副图那一份的键（跟 measure 名字不会撞）


def _hist(bars):
    """副图的柱子＝**引擎背驰判断读的那一份**（signals.macd_hist），不在这里另减一遍 DIF−DEA：
    另减的话，引擎哪天改了柱子的定义，副图跟背驰就不是同一份柱子了，却没有一处会红（Atlas 10-04 核出）。
    走模块属性取函数（不是 import 时绑死的名字），引擎改了这里跟着变。"""
    return _ENGINE.macd_hist(bars, *MACD_PARAMS)


def _macd_body(slot, symbol, tf):
    """副图那一份：同一格、同一份 K 线（slot.bars）上用引擎的 macd_lines 算 DIF / DEA，柱子取引擎的
    macd_hist（背驰判断读的就是它；现在的定义是 DIF − DEA、不乘 2）。
    跟 /api/chart 共用头部（fetched_at / stale / refreshing / span / earliest / span_max），带每根 K 线的 t
    让前端按时间对齐；懒算一次，数据刷新就作废（跟 measure 那几份同一个口袋）。"""
    b = slot.mbodies.get(MACD_KEY)
    if b is None:
        head = json.loads(slot.body)
        dif, dea = macd_lines(slot.bars, *MACD_PARAMS)
        b = slot.mbodies[MACD_KEY] = json.dumps(dict(
            fetched_at=head["fetched_at"], stale=False, refreshing=False,
            span=head["span"], earliest=head["earliest"], span_max=head["span_max"], engine=head["engine"],
            symbol=symbol, tf=tf, params=list(MACD_PARAMS), hist_def="dif-dea",
            t=[x["t"] for x in slot.bars], dif=_clean(dif), dea=_clean(dea),
            hist=_clean(_hist(slot.bars))),
            ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return b


def _measure_body(slot, symbol, tf, measure):
    """在 slot.lock 里调用 → 这一格在某种背驰看法下的 JSON。买卖点之外的一切跟默认那份是同一份：
    K 线、笔、段、中枢跟看法无关，只有 signals 两层重算（懒算、按 measure 各存一份，数据刷新就作废）。
    切看法不碰币安。"""
    if measure == "macd":
        return slot.body
    if measure == MACD_KEY:
        return _macd_body(slot, symbol, tf)
    b = slot.mbodies.get(measure)
    if b is None:
        d = json.loads(slot.body)
        r = analyze(slot.bars, tick=tick_of(SYMBOLS[symbol] + "_.json"))
        d["signals"] = _clean({"seg": engine_signals(r, "seg", measure), "pen": engine_signals(r, "pen", measure)})
        d["measure"] = measure
        b = slot.mbodies[measure] = json.dumps(d, ensure_ascii=False, separators=(",", ":"),
                                               allow_nan=False).encode("utf-8")
    return b


def _variant(slot, symbol=None, tf=None, measure="macd"):
    """在 slot.lock 里调用 → (json, gzip)，头上两个旗按当下状态如实标。"""
    key = (slot.failed, slot.refreshing, measure)
    v = slot.variants.get(key)
    if v is None:
        body = _measure_body(slot, symbol, tf, measure)
        if slot.failed:
            body = body.replace(b'"stale":false', b'"stale":true', 1)
        if slot.refreshing:
            body = body.replace(b'"refreshing":false', b'"refreshing":true', 1)
        v = slot.variants[key] = (body, gzip.compress(body, 6))
    return v


def _evict_idle(now):
    """span>1 的格子闲置超过 IDLE_S 就清掉（锁不换；正在拉的不动）。只在请求路径上顺手扫一遍。"""
    for (s_, t_, k), sl in SLOTS.items():
        if k > 1 and sl.body is not None and now - sl.used_at > IDLE_S and sl.lock.acquire(blocking=False):
            try:
                if not sl.refreshing and not sl.prefetching and now - sl.used_at > IDLE_S:
                    sl.reset()
            finally:
                sl.lock.release()


def _prefetch(symbol, tf, span):
    target = SLOTS[(symbol, tf, span)]
    try:
        get_chart(symbol, tf, span, prefetch=False, touch=False)
    finally:
        with target.lock:
            target.prefetching = False


def start_prefetch(symbol, tf, span):
    """送出 span 之后，后台单飞把 2×span 预拉好（Nova 10-04 定的默认做法：15m 补一档要拉十几秒，
    用户从默认视图拖到左边要滑过上万根，那段时间里它早就拉好了）。到封顶 / 已到最早 / 已有 / 正在拉 ⇒ 不拉。"""
    nxt = span * 2
    if nxt > SPAN_MAX[tf] or SLOTS[(symbol, tf, span)].earliest:
        return
    target = SLOTS[(symbol, tf, nxt)]
    if not target.lock.acquire(blocking=False):
        return                                           # 有人正在拉它（冷路径持锁）
    try:
        if target.body is not None or target.prefetching or target.refreshing:
            return
        target.prefetching = True
    finally:
        target.lock.release()
    threading.Thread(target=_prefetch, args=(symbol, tf, nxt), daemon=True).start()


def get_chart(symbol, tf, span=1, prefetch=True, touch=True, measure="macd"):
    """→ (json bytes, gzip bytes) 或 None（一次都没拉成功过）。

    · 冷（还没有缓存）：同步拉，持锁 ⇒ 并发进来的都等这一次，不回空；
    · 有缓存、过期了（成功后 REFRESH_S / 失败后 RETRY_S）：起**一个**后台刷新，立刻回旧缓存
      （stale-while-revalidate；币安一抖不会挂到用户请求上）；
    · 旗：stale = 上一次拉取失败；refreshing = 这次回的是旧缓存、后台正在拉；
    · 送出之后：后台预拉下一档（start_prefetch）。"""
    slot = SLOTS[(symbol, tf, span)]
    now = time.time()
    _evict_idle(now)
    with slot.lock:
        if touch:
            slot.used_at = now
        due = now - slot.tried_at >= (RETRY_S if slot.failed else REFRESH_S)
        if slot.body is None:
            if due:
                slot.tried_at = now
                _refresh_into(slot, symbol, tf)
            if slot.body is None:
                return None
        elif due and not slot.refreshing:
            slot.tried_at = now
            slot.refreshing = True
            slot.variants = {}
            start_refresh(slot, symbol, tf)
        out = _variant(slot, symbol, tf, measure)
    if prefetch:
        start_prefetch(symbol, tf, span)
    return out


def prewarm():
    """起服务时把白名单里每一格按顺序拉一遍：**一格一格来，不并发**（Nova 10-03 定），
    免得冷启动一下打币安十几页 × 15。走的是 get_chart 同一条路（同一把锁、同一套节流），
    有人在预热途中访问某格，要么等这格的锁、要么直接吃已有缓存，不会多拉。"""
    t0 = time.time()
    ok = 0
    base = [(s_, t_) for (s_, t_, k) in SLOTS if k == 1]
    for symbol, tf in base:
        if get_chart(symbol, tf, prefetch=False) is not None:   # 预热只管 span=1，不连带预拉（免得一起打币安）
            ok += 1
    log("prewarm %d/%d in %.1fs" % (ok, len(base), time.time() - t0))


# ───────────────────────── 静态资源版本号 ─────────────────────────
# Cloudflare 会把 .js/.css 的浏览器缓存改写成 4 小时（max-age=14400，不管我们发 60），边缘也会缓存
# ⇒ 前端一更新，访客最多 4 小时拿旧 JS，app.js / layers.js 还可能一新一旧混着跑（Nova 10-03 外测）。
# 修法：送页面时把本地资源引用改写成 `x.js?v=<hash>`，hash = 这个资源**送出去的字节**的 sha256 前 10 位。
#   · 「送出去的字节」含它自己被改写过的 import ⇒ theme.js 一变，app.js 里那行 import 跟着变 ⇒ app.js
#     的 hash 也变 ⇒ index.html 也变。版本号由内容推出来，不靠人手改、也不靠 git（部署目录 pull 就生效）。
#   · 带对了 v 的请求：一年 + immutable（URL 变了就是新资源，旧的缓存永远不会被读到）；
#     不带 v / v 对不上（旧页面引用的旧版本）：只给 no-cache，不让错的内容占住一个长缓存的键。
#   · index.html 本身：no-cache（每次回源验证；Cloudflare 对 html 默认不缓存）。
VERSIONED = {".html", ".js", ".css"}     # 会被改写、也会被带上 v 的类型
_HTML_REF = re.compile(r'(\s(?:src|href)=)(["\'])([^"\'?#:]+\.(?:js|css))\2')
_JS_IMPORT = re.compile(r'((?:\bfrom|\bimport)\s*)(["\'])(\./[^"\'?#]+\.js)\2')


def _asset_path(rel_from, ref):
    """引用（相对 rel_from 所在目录）→ web/ 里的绝对路径；出了 web/ 返回 None。"""
    full = os.path.realpath(os.path.join(os.path.dirname(rel_from), ref))
    root = os.path.realpath(STATIC)
    return full if full.startswith(root + os.sep) and os.path.isfile(full) else None


def served(full, _stack=()):
    """→ (送出去的字节, 版本号)。.html / .js 会把引用改写成带 v 的；其它原样。
    每次现算、不缓存：一共几个小文件，读 + sha256 不到 1 ms；缓存了反而要操心「依赖变了自己没变」。"""
    with open(full, "rb") as f:
        body = f.read()
    ext = os.path.splitext(full)[1].lower()
    if ext in (".html", ".js") and full not in _stack:
        pat = _HTML_REF if ext == ".html" else _JS_IMPORT
        text = body.decode("utf-8")

        def sub(m):
            dep = _asset_path(full, m.group(3))
            if dep is None or dep in _stack:
                return m.group(0)
            return "%s%s%s?v=%s%s" % (m.group(1), m.group(2), m.group(3), served(dep, _stack + (full,))[1], m.group(2))
        body = pat.sub(sub, text).encode("utf-8")
    return body, hashlib.sha256(body).hexdigest()[:10]


def cache_for(ext, want, ver):
    """html：no-cache；带对了 v：一年 + immutable；不带 v / 旧 v：no-cache（别让它占一个长缓存的键）。"""
    if ext != ".html" and want == ver:
        return "public, max-age=31536000, immutable"
    return "no-cache"


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
            if not {"symbol", "tf"} <= set(q) <= {"symbol", "tf", "span", "measure"} or any(len(v) != 1 for v in q.values()):
                return self._err(400)                     # 多参数、少参数、重复参数一律不认
            symbol, tf = q["symbol"][0].upper(), q["tf"][0]
            if symbol not in SYMBOLS or tf not in TFS:
                return self._err(400)
            raw = q.get("span", ["1"])[0]
            if raw not in {str(v) for v in SPAN_VALUES}:
                return self._err(400)                     # 只认 "1" "2" "4" "8" "16" 这五个写法（"02"、"2.0" 都不认）
            span = min(int(raw), SPAN_MAX[tf])            # 超封顶：钳到封顶，响应里如实回显 span / span_max
            measure = q.get("measure", ["macd"])[0]
            if measure not in MEASURES:
                return self._err(400)                     # 背驰看法只认四个名字（macd / slope / lines / peak）
            got = get_chart(symbol, tf, span, measure=measure)
            if got is None:
                return self._err(503)
            return self._send(200, got[0], gz=got[1])
        if u.path == "/api/macd":
            try:
                q = urllib.parse.parse_qs(u.query, keep_blank_values=True, strict_parsing=True, max_num_fields=4)
            except ValueError:
                return self._err(400)
            if not {"symbol", "tf"} <= set(q) <= {"symbol", "tf", "span"} or any(len(v) != 1 for v in q.values()):
                return self._err(400)                     # 跟 /api/chart 同一套；measure 跟副图无关，带了也 400
            symbol, tf = q["symbol"][0].upper(), q["tf"][0]
            if symbol not in SYMBOLS or tf not in TFS:
                return self._err(400)
            raw = q.get("span", ["1"])[0]
            if raw not in {str(v) for v in SPAN_VALUES}:
                return self._err(400)
            got = get_chart(symbol, tf, min(int(raw), SPAN_MAX[tf]), measure=MACD_KEY)
            if got is None:
                return self._err(503)
            return self._send(200, got[0], gz=got[1])
        if u.path == "/api/tick":
            try:
                q = urllib.parse.parse_qs(u.query, keep_blank_values=True, strict_parsing=True, max_num_fields=2)
            except ValueError:
                return self._err(400)
            if set(q) != {"symbol", "tf"} or any(len(v) != 1 for v in q.values()):
                return self._err(400)                     # 只认 symbol + tf：span、measure 跟最后一根无关，带了也 400
            symbol, tf = q["symbol"][0].upper(), q["tf"][0]
            if symbol not in SYMBOLS or tf not in TFS:
                return self._err(400)
            body = get_tick(symbol, tf)
            if body is None:
                return self._err(503)
            return self._send(200, body)
        if u.path == "/api/meta":
            if u.query:
                return self._err(400)
            return self._send(200, json.dumps(dict(symbols=list(SYMBOLS), tfs=list(TFS), days=DAYS,
                                                   refresh_s=REFRESH_S, span_max=SPAN_MAX,
                                                   engine=ENGINE, measures=list(MEASURES),
                                                   measure_orig={m: MEASURE_ORIG.get(m, False) for m in MEASURES})).encode())
        return self._static(u.path, u.query)

    def _static(self, path, query=""):
        name = "index.html" if path in ("", "/") else urllib.parse.unquote(path).lstrip("/")
        full = os.path.realpath(os.path.join(STATIC, name))
        root = os.path.realpath(STATIC)
        rel = os.path.relpath(full, root)
        ext = os.path.splitext(full)[1].lower()
        if (not full.startswith(root + os.sep) or ext not in STATIC_EXT or not os.path.isfile(full)
                or any(part.startswith(".") for part in rel.split(os.sep))):
            return self._err(404)                         # 出了 web/、不认的类型、点文件、不存在：统一 404
        if ext in VERSIONED:
            body, ver = served(full)
            cache = cache_for(ext, urllib.parse.parse_qs(query).get("v", [None])[0], ver)
        else:
            with open(full, "rb") as f:
                body = f.read()
            cache = "public, max-age=60"
        self._send(200, body, ctype=STATIC_EXT[ext], cache=cache)


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
