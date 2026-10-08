#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""引擎速度门（card-5a1f2ec2-650）：每张图整段划一次（analyze ＋ trend_v3），跟基准那笔同机同时比，慢过 1.5 倍就红。

    python3 tools/speed_gate.py                  # HEAD（工作树）对 origin/main
    python3 tools/speed_gate.py --base <ref>     # 换基准
    python3 tools/speed_gate.py --head <ref>     # 测的那边也换成一笔提交（默认是本工作树）
    python3 tools/speed_gate.py --snap <json.gz> # 另加一份本地快照（{'<品种> <周期>': {'bars': [...]}}），不进仓
    python3 tools/speed_gate.py --self-test      # 牙：① HEAD 对 HEAD 必须绿；② build_segments 每次多划一遍（慢一倍）必须红

为什么要它：L77 硬合那一版（l77-exp 28a8128）规则对了，可 zec_1h 一份整段划 170 秒都没跑完（main 零点几秒）——
  别的尺全量的是「对不对」，没有一把量「快不快」，是事后手跑才发现的。线上每个请求都要整段划一次，慢一倍就是慢一倍。

口径（Nova 10-08 18:48 定）：
  · 每张图 analyze(bars, tick) ＋ trend_v3(r)，跟 web/server.py 线上那一格同一套调用；
  · 每张跑 3 轮取中位数；基准和 HEAD **轮流**跑（一轮基准、一轮 HEAD，交替 3 轮），机器忙闲两边一起吃；
    每一轮里同一张在同一个进程里连划 3 次取最快、计时时关 GC —— 这台机器是大家共用的，同一进程里同一张图
    实测能在 21ms 和 57ms 之间跳（10-08 18:5x），只取中位数压不住；取最快量的是代码本身；
  · 任何一张 HEAD/基准 > 1.5 ⇒ 红，印哪一张、几秒对几秒；
  · 整道门要在一分钟内跑完：先各跑一遍量出每张多长，要超时就只留最长的 5 张。
  ★ 绝对地板 FLOOR（100ms）：两边都短于它的图只印不判 —— 几十毫秒的图，调度抖一下比例就能过 1.5（第一版 50ms 的地板上
    aaplusdt_15m_s11 31ms→69ms 报了红，同一进程重划是 21～57ms 乱跳），那是噪声不是变慢。地板看的是两边里慢的那个：
    L77 那种 0.05s→170s 的照样判红。
基准那笔用 `git archive` 导到临时目录（不建 worktree、不碰工作树）；两边读**同一份**图（HEAD 这边的 data/ 和夹具）。
红线：不印本机路径（临时目录只印 $TMPDIR/ 下的名字）。
"""
import gc
import gzip
import json
import os
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RATIO = 1.5
FLOOR = 0.10            # 秒：两边都短于这个数的图只印不判（看的是两边里**慢的那个**：小图真炸了照样判）
REPS = 3            # 轮：基准、HEAD 交替，取中位数
INNER = 3           # 每轮里同一张在同一个进程里连划几次取最快（量的是代码，不是机器那一刻忙不忙）
BUDGET = 60.0           # 秒：整道门的上限
KEEP_IF_OVER = 5        # 超时就只留最长的这几张


def charts(snap=None):
    """→ [(名字, 精度, bars)]：data/ 下的 K 线样本 ＋ tools/fixtures 里的 K 线夹具（笔夹具跳过）＋ 可选快照。"""
    sys.path.insert(0, ROOT)
    from config import tick_of
    out = []
    for sub in ("data", os.path.join("tools", "fixtures")):
        d = os.path.join(ROOT, sub)
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json") or fn.endswith("_tmp.json"):
                continue
            try:
                raw = json.load(open(os.path.join(d, fn)))
            except ValueError:
                continue
            raw = raw["bars"] if isinstance(raw, dict) and "bars" in raw else raw
            if not (isinstance(raw, list) and raw and isinstance(raw[0], dict) and {"t", "o", "h", "l", "c"} <= set(raw[0])):
                continue
            out.append(("%s/%s" % ("data" if sub == "data" else "fixtures", fn), tick_of(fn), raw))
    if snap:
        s = json.loads(gzip.open(snap).read())
        for k in sorted(s):
            try:
                tick = tick_of(k.split()[0].lower() + "_.json")
            except KeyError:
                tick = None
            out.append(("快照 " + k, tick, s[k]["bars"]))
    return out


def worker(root, path):
    """子进程：在 root 那棵树的引擎上，把 path 里的每张图整段划一次 → 每张秒数（JSON 打到 stdout）。"""
    sys.path.insert(0, root)
    from core.analyze import analyze
    from core.trend import trend_v3
    items = json.load(open(path))
    for name, tick, bars in items:
        bars = [dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"]) for b in bars]
        best = float("inf")
        for _ in range(INNER):
            gc.collect()
            gc.disable()
            t0 = time.perf_counter()
            trend_v3(analyze(bars, tick=tick))
            best = min(best, time.perf_counter() - t0)
            gc.enable()
        print(best, flush=True)      # 一张一行、马上冲出去：超时被掐时，看得出卡在第几张


class TooSlow(Exception):
    """HEAD 一轮跑超了时限：已经跑完的张数在 done 里。"""
    def __init__(self, done, limit):
        Exception.__init__(self)
        self.done, self.limit = done, limit


def _floats(out):
    out = out.decode() if isinstance(out, bytes) else (out or "")
    return [float(x) for x in out.split()]


def run_side(root, path, timeout=None):
    try:
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "--worker", root, path],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise TooSlow(_floats(e.stdout), timeout)
    if p.returncode != 0:
        raise RuntimeError("引擎跑挂了（rc=%d）：%s" % (p.returncode, (p.stderr.strip().splitlines() or ["？"])[-1]))
    return _floats(p.stdout)


def export(ref, dest):
    """git archive <ref> → dest（只要 core/ 和 config.py：引擎就这些）。"""
    sha = subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref + "^{commit}"], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip()
    if not sha:
        raise RuntimeError("解析不出基准 %s（没 fetch？）" % ref)
    os.makedirs(dest, exist_ok=True)
    tar = os.path.join(dest, "base.tar")
    subprocess.run(["git", "archive", "-o", tar, sha, "core", "config.py"], cwd=ROOT, check=True)
    with tarfile.open(tar) as t:
        t.extractall(os.path.join(dest, "tree"))
    return os.path.join(dest, "tree"), sha[:7]


def tmpname(p):
    t = (os.environ.get("TMPDIR") or tempfile.gettempdir()).rstrip("/")
    return "$TMPDIR/" + p[len(t) + 1:] if p.startswith(t + "/") else os.path.basename(p)


def gate(base_root, head_root, items, base_label, head_label, quiet=False):
    """→ (红的张数, 行)。base_root/head_root：两棵引擎树；items：[(名字, 精度, bars)]。"""
    say = (lambda *a: None) if quiet else print
    tmp = tempfile.mkdtemp(prefix="speedgate-")
    try:
        def dump(sel):
            p = os.path.join(tmp, "items.json")
            json.dump([items[i] for i in sel], open(p, "w"))
            return p

        sel = list(range(len(items)))
        # 第一轮兼当量长短：两边各一遍
        t_start = time.perf_counter()
        p = dump(sel)
        b0 = run_side(base_root, p)
        tb = time.perf_counter() - t_start
        # HEAD 这一轮的时限：基准一轮的 2×RATIO 倍（至少 20s）。L77 那种一张 170s 起跳的，不用等它跑完就是红
        limit = max(20.0, tb * RATIO * 2)
        try:
            h0 = run_side(head_root, p, timeout=limit)
        except TooSlow as e:
            k = len(e.done)
            name = items[sel[k]][0] if k < len(sel) else "？"
            say("✗ %s 一轮跑了 %.0fs 还没完（%s 一轮 %.1fs，时限 %.0fs）：卡在第 %d 张 %s（基准这张 %.3fs）" % (
                head_label, e.limit, base_label, tb, e.limit, k + 1, name, b0[k] if k < len(b0) else float("nan")))
            return 1, [(name, b0[k] if k < len(b0) else 0.0, float("inf"), float("inf"), True)]
        spent = time.perf_counter() - t_start
        est = spent * REPS      # 一共要 REPS 轮
        if est > BUDGET:
            longest = sorted(sel, key=lambda i: -max(b0[i], h0[i]))[:KEEP_IF_OVER]
            say("（一轮 %.1fs，%d 轮估 %.0fs > %.0fs ⇒ 只留最长的 %d 张）" % (spent, REPS, est, BUDGET, KEEP_IF_OVER))
            keep = sorted(longest)
            B = [[b0[i]] for i in keep]
            H = [[h0[i]] for i in keep]
            sel = keep
            p = dump(sel)
        else:
            B = [[x] for x in b0]
            H = [[x] for x in h0]
        for _ in range(REPS - 1):
            for k, x in enumerate(run_side(base_root, p)):
                B[k].append(x)
            for k, x in enumerate(run_side(head_root, p)):
                H[k].append(x)
        red, rows = 0, []
        say("%-34s %9s %9s %7s" % ("图", base_label, head_label, "倍数"))
        for k, i in enumerate(sel):
            b, h = statistics.median(B[k]), statistics.median(H[k])
            ratio = h / b if b > 0 else float("inf")
            judged = max(b, h) >= FLOOR
            bad = judged and ratio > RATIO
            red += bad
            mark = "✗" if bad else ("✓" if judged else "·")
            rows.append((items[i][0], b, h, ratio, bad))
            say("%-34s %8.3fs %8.3fs %6.2fx %s" % (items[i][0], b, h, ratio, mark))
        tb, th = sum(r[1] for r in rows), sum(r[2] for r in rows)
        say("%-34s %8.3fs %8.3fs %6.2fx" % ("合计", tb, th, th / tb if tb else 0))
        return red, rows
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


SLOW_PATCH = ("\n_sg_orig = build_segments\n"
              "def build_segments(*a, **k):\n    _sg_orig(*a, **k)\n    return _sg_orig(*a, **k)\n")


def self_test(items):
    """① HEAD 对 HEAD 必须绿（噪声不许过门）；② build_segments 每次多划一遍必须红（门有牙）。
    只用按 K 线根数排第 2～5 的那 4 张：短图本来就只印不判，带上只是多花时间；最长那张（zec15）也不带 ——
    多划一遍时它一张就 1.8s×9 次，整个自检会拖到 87s（实测），过不了一分钟那条线。"""
    items = sorted(items, key=lambda x: -len(x[2]))[1:KEEP_IF_OVER]
    ok = True
    red, _ = gate(ROOT, ROOT, items, "HEAD", "HEAD", quiet=True)
    print("  %s 臂 ① HEAD 对 HEAD ⇒ %s" % ("✓" if red == 0 else "✗", "绿" if red == 0 else "红 %d 张（噪声过了门）" % red))
    ok &= red == 0
    tmp = tempfile.mkdtemp(prefix="speedgate-slow-")
    try:
        slow = os.path.join(tmp, "tree")
        shutil.copytree(os.path.join(ROOT, "core"), os.path.join(slow, "core"))
        shutil.copy(os.path.join(ROOT, "config.py"), slow)
        with open(os.path.join(slow, "core", "segment.py"), "a") as f:
            f.write(SLOW_PATCH)
        # trend 等模块 import 的是 core.segment.build_segments 这个名字 ⇒ 补在模块尾，所有 from-import 都拿到慢的那个
        red, rows = gate(ROOT, slow, items, "HEAD", "慢", quiet=True)
        worst = max(rows, key=lambda r: r[3])
        print("  %s 臂 ② build_segments 每次多划一遍 ⇒ %s（最慢 %s %.3fs→%.3fs）" % (
            "✓" if red else "✗", "红 %d 张" % red if red else "没红（门没牙）", worst[0], worst[1], worst[2]))
        ok &= red > 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("自检通过" if ok else "自检没过")
    return 0 if ok else 1


def main(argv):
    if argv[:1] == ["--worker"]:
        worker(argv[1], argv[2])
        return 0
    base, head, snap, selftest = "origin/main", None, None, False
    it = iter(argv)
    for a in it:
        if a == "--base":
            base = next(it)
        elif a == "--head":
            head = next(it)
        elif a == "--snap":
            snap = next(it)
        elif a == "--self-test":
            selftest = True
        else:
            print("不认识的参数：%s" % a, file=sys.stderr)
            return 2
    items = charts(snap)
    if selftest:
        return self_test(items)
    tmp = tempfile.mkdtemp(prefix="speedgate-base-")
    try:
        try:
            base_root, short = export(base, tmp)
            head_root, hshort = (ROOT, "HEAD") if head is None else export(head, os.path.join(tmp, "h"))
        except (RuntimeError, subprocess.CalledProcessError) as e:
            print("没比成：%s" % e)
            return 2
        t0 = time.perf_counter()
        try:
            red, rows = gate(base_root, head_root, items, "基准" + short, hshort if head is None else "测" + hshort)
        except RuntimeError as e:
            print("没比成：%s" % e)
            return 2
        print("%d 张，门限 %.1f 倍（两边都短于 %.0fms 只印不判），用时 %.0fs" % (len(rows), RATIO, FLOOR * 1000, time.perf_counter() - t0))
        for name, b, h, ratio, bad in rows:
            if bad:
                print("✗ %s：%.3fs → %.3fs（%.2f 倍）" % (name, b, h, ratio))
        print("全部通过（没有一张慢过 %.1f 倍）" % RATIO if not red else "%d 张慢过 %.1f 倍" % (red, RATIO))
        return 1 if red else 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
