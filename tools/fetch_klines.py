#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拉取币安 U 本位永续 K 线，存到 data/。

用法：
    python3 tools/fetch_klines.py                          # 默认：AAPLUSDT 4h / 30m（卡片用的那段）
    python3 tools/fetch_klines.py ZECUSDT 15m --days 210 --out zec15.json   # 拉到当前时刻
    python3 tools/fetch_klines.py BTCUSDT 4h --start 2026-01-01 --out btc_4h.json  # 从某天（UTC）拉到当前
"""
import json, time, urllib.request, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA

BASE = "https://fapi.binance.com/fapi/v1/klines"
UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)"}

def fetch(symbol, interval, start_ms, end_ms):
    out, cur = [], start_ms
    while cur < end_ms:
        url = "%s?symbol=%s&interval=%s&startTime=%d&endTime=%d&limit=1500" % (
            BASE, symbol, interval, cur, end_ms)
        req = urllib.request.Request(url, headers=UA)
        batch = json.loads(urllib.request.urlopen(req, timeout=30).read())
        if not batch:
            break
        out += batch
        nxt = batch[-1][0] + 1
        if nxt <= cur:
            break
        cur = nxt
        time.sleep(0.25)
    seen, res = set(), []
    for k in out:
        if k[0] in seen:
            continue
        seen.add(k[0])
        res.append(dict(t=int(k[0]), o=float(k[1]), h=float(k[2]),
                        l=float(k[3]), c=float(k[4])))
    res.sort(key=lambda r: r["t"])
    return res


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol", nargs="?")
    ap.add_argument("interval", nargs="?")
    ap.add_argument("--days", type=float, default=210, help="从现在往前拉多少天")
    ap.add_argument("--start", help="起始日期 YYYY-MM-DD（UTC），给了就忽略 --days")
    ap.add_argument("--out", help="输出文件名（data/ 下）")
    a = ap.parse_args()
    if a.symbol:
        import datetime
        E = int(time.time() * 1000)
        S = (int(datetime.datetime.strptime(a.start, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
             if a.start else E - int(a.days * 86400 * 1000))
        fn = a.out or "%s_%s.json" % (a.symbol.lower(), a.interval)
        data = fetch(a.symbol, a.interval, S, E)
        json.dump(data, open(os.path.join(DATA, fn), "w"))
        print(a.symbol, a.interval, len(data), "根", data[0]["t"], "→", data[-1]["t"], "last close", data[-1]["c"])
    else:
        S = 1785024000000          # 2026-07-26 00:00 UTC
        E = 1790553600000          # 2026-09-28 00:00 UTC
        for iv, fn in (("4h", "aaplusdt_4h.json"), ("30m", "aaplusdt_30m.json")):
            data = fetch("AAPLUSDT", iv, S, E)
            json.dump(data, open(os.path.join(DATA, fn), "w"))
            print(iv, len(data), data[0]["t"], data[-1]["t"], "last close", data[-1]["c"])
