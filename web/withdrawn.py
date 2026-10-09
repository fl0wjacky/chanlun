# -*- coding: utf-8 -*-
"""「已撤回」（小栋 10-09 12:47 决策页 Q-6 选 A；方案定稿在总纲①卡 12:22～12:24）。

引擎无状态：同一份 K 线只给一个答案，不知道自己以前说过什么。所以撤回只能由服务端比出来：
每张图（品种 × 周期 × span × 笔档）存一份「上次算出来的已确认集合」，每次重算跟它比——
上次是已确认的，这次**整个不见了**，记一条撤回。确认 → 待确认不记（图上本来就画成空心点）。

  · 键用 K 线开盘时间（不用下标：往左加载、窗口左边每次刷新被切，下标会平移）。
  · 只比「对齐点」之后：窗口是 span × 固定天数，每次刷新左边都会切掉旧 K 线，图头几段会重新划。
      刀（D2／S5）：新旧两次第一把相同的已确认 D2；
      线段：新旧两次第一条相同的已确认线段（有些图 span=1 上没有已确认 D2，线段照样要记得到）。
    找不到对齐点那一类这一轮不记（宁可漏记，不记假撤回），但「上次」照样换成这次。
  · 已确认线段 = 已完成线段去掉最后 PENDING_SEGS 条（D-3 改 C′，待小栋拍：最后两条终点还可能挪，画虚线、不记撤回）。
    哪几条算 pending **只在这里定**：服务端给 segs_std 每条标 state 也读这个数（前端只照 state 画，不自己数）。
  · 显示：各 span 的记录取并集（线上 15 张实测：对齐点之后 span=1 跟封顶 span 差异 0），
    只给本窗口里、并且在本次结果第一个已确认对象之后的；同一条撤回在几个 span 都记到了只给一次。
  · 存在状态目录（跟决策页同一个，仓库外）下 withdrawn/，一张图一个 JSON：{"last": …, "withdrawn": […]}，原子写。
    每张图最多留 CAP 条，超了从最老的删。服务端重启不丢（上次的集合在盘上）；部署前的历史不补。
"""
import json
import os
import threading

import decisions

CAP = 200
PENDING_SEGS = 2                                # C′：最后两条已完成线段算「还可能挪」。小栋要是选 A 改成 1；Pine 的 STD_PENDING_SEGS 要一起改（tools/pending_sync_check.py 比这两处）


def seg_states(n):
    """n 条已完成线段（segs_std）→ 每条的 state：最后 PENDING_SEGS 条 pending，其余 confirmed。"""
    k = min(PENDING_SEGS, n)
    return ["confirmed"] * (n - k) + ["pending"] * k
# 只有真起服务（server.py 的 __main__）才打开。各检查程序都是 import server 起临时服务，状态目录默认又在
#   checkout 旁边——不关着的话，在任何一份 checkout 里跑检查都会往那个目录写账本，搅了线上那本账。
ENABLED = False
_lock = threading.Lock()


def _dir():
    return os.path.join(decisions.STATE, "withdrawn")


def _path(key):
    symbol, tf, span, pen_min = key
    return os.path.join(_dir(), "%s_%s_%s_%s.json" % (symbol, tf, span, pen_min))


def _p(x):
    return round(float(x), 10)


def snapshot(bars, trend, segs):
    """→ (conf, seen)：conf 是这次的已确认对象（要存下来下次比的），seen 是这次出现的全部对象的键（判「整个不见了」）。
    刀：[t, kind, price, rule]；线段：[t0, t1, dir, p0, p1]。"""
    t = lambda i: bars[i]["t"]
    cuts = [[t(b["bar"]), b["kind"], _p(b["price"]), b["rule"]] for b in trend["bounds"] if b.get("state") == "confirmed"]
    done = [s for s in segs if not s.get("live")]
    st = seg_states(len(done))
    sg = [[t(s["i0"]), t(s["i1"]), s["dir"], _p(s["p0"]), _p(s["p1"])] for s, x in zip(done, st) if x == "confirmed"]
    seen_c = {(t(b["bar"]), b["kind"], _p(b["price"])) for b in trend["bounds"]}
    seen_s = {(t(s["i0"]), t(s["i1"]), s["dir"]) for s in segs}
    return dict(cuts=cuts, segs=sg), dict(cuts=seen_c, segs=seen_s)


def _anchor(old, new):
    """两组键里第一个共同的（按时间）→ 它的时间；没有 ⇒ None。"""
    common = set(map(tuple, old)) & set(map(tuple, new))
    return min(common)[0] if common else None


def diff(last, conf, seen, at):
    """上次的已确认（last）对这次（conf／seen）→ 新撤回的列表。at：这次最后一根的开盘时间（发现撤回的那一刻）。"""
    out = []
    t0 = _anchor([c for c in last["cuts"] if c[3] == "D2-2"], [c for c in conf["cuts"] if c[3] == "D2-2"])
    if t0 is not None:
        for c in last["cuts"]:
            if c[0] >= t0 and (c[0], c[1], c[2]) not in seen["cuts"]:
                out.append(dict(kind="d2" if c[3] == "D2-2" else "s5", t=c[0], dir=c[1], price=c[2], at=at))
    u0 = _anchor(last["segs"], conf["segs"])
    if u0 is not None:
        for s in last["segs"]:
            if s[0] >= u0 and (s[0], s[1], s[2]) not in seen["segs"]:
                out.append(dict(kind="seg", t=s[0], t1=s[1], dir=s[2], p0=s[3], p1=s[4], at=at))
    return out


def _load(key):
    try:
        with open(_path(key), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def _save(key, rec):
    os.makedirs(_dir(), exist_ok=True)
    p = _path(key)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, separators=(",", ":"))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)


def observe(key, bars, trend, segs):
    """每次重算完一张图调一次：跟上次比、记新撤回、把「上次」换成这次。→ 这次新记的撤回（列表）。"""
    conf, seen = snapshot(bars, trend, segs)
    with _lock:
        rec = _load(key) or dict(last=None, withdrawn=[])
        new = diff(rec["last"], conf, seen, bars[-1]["t"]) if rec["last"] else []
        rec["withdrawn"] = (rec["withdrawn"] + new)[-CAP:]
        rec["last"] = conf
        _save(key, rec)
    return new


def _ident(w):
    return (w["kind"], w["t"], w.get("t1"), w["dir"])


def view(symbol, tf, pen_min, spans, bars, trend, segs):
    """→ 给前端的 withdrawn：各 span 记录的并集，只要本窗口里、本次结果第一个已确认对象之后的，同一条只给一次（取最早的 at）。"""
    conf, _ = snapshot(bars, trend, segs)
    lo_c = min((c[0] for c in conf["cuts"]), default=None)
    lo_s = min((s[0] for s in conf["segs"]), default=None)
    end = bars[-1]["t"]
    got = {}
    for span in spans:
        rec = _load((symbol, tf, span, pen_min))
        for w in (rec or {}).get("withdrawn", []):
            lo = lo_s if w["kind"] == "seg" else lo_c
            if lo is None or not (lo <= w["t"] <= end):
                continue
            k = _ident(w)
            if k not in got or w["at"] < got[k]["at"]:
                got[k] = w
    return sorted(got.values(), key=lambda w: (w["t"], w["kind"]))
