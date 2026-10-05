#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回测加数据（card-3c7f0ccf-7b7）：按清单拉公开 K 线到 data/bt/（不进仓），sha1 记回清单。

    python3 tools/bt_fetch.py tools/bt_manifest.json            # 拉缺的，写 sha1 / bars 进清单
    python3 tools/bt_fetch.py tools/bt_manifest.json --check    # 不拉，只核本地文件跟清单 sha1 一致

清单每条：{symbol, tf, start, end, regime, why}；start / end 是 UTC 日期，取 [start, end) 的已收盘 K 线。
文件名 = data/bt/<symbol>_<tf>_<start>_<end>.json。币安已收盘的 K 线不会再改 ⇒ 别人照清单重拉，sha1 应当相同。
"""
import datetime
import hashlib
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fetch_klines import fetch                                 # noqa: E402

STEP = {"15m": 900_000, "30m": 1_800_000, "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000, "1d": 86_400_000}
OUT = os.path.join(ROOT, "data", "bt")


def ms(day):
    return int(datetime.datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)


def name(e):
    return "bt/%s_%s_%s_%s.json" % (e["symbol"].lower(), e["tf"], e["start"], e["end"])


def main():
    path, check = sys.argv[1], "--check" in sys.argv
    man = json.load(open(path, encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    now, bad = int(time.time() * 1000), 0
    for e in man:
        fn = os.path.join(ROOT, "data", name(e))
        if not os.path.exists(fn):
            if check:
                print("✗ 缺 %s" % name(e)); bad += 1; continue
            s, t = ms(e["start"]), ms(e["end"])
            bars = [b for b in fetch(e["symbol"], e["tf"], s, t - 1)
                    if s <= b["t"] and b["t"] + STEP[e["tf"]] <= min(t, now)]       # 只要区间内、已收盘的
            json.dump(bars, open(fn, "w"))
        raw = open(fn, "rb").read()
        sha, n = hashlib.sha1(raw).hexdigest(), len(json.loads(raw))
        if check and e.get("sha1") not in (None, sha):
            print("✗ %s sha1 %s ≠ 清单 %s" % (name(e), sha[:12], e["sha1"][:12])); bad += 1; continue
        e.update(file=name(e), sha1=sha, bars=n)
        print("✓ %-40s %6d 根 sha1 %s  %s" % (name(e), n, sha[:12], e["regime"]))
    if not check:
        json.dump(man, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
