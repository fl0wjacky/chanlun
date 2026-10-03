#!/usr/bin/env python3
"""tradingview/chanlun.pine 画图 x 坐标检查：所有 line.new / box.new / label.new 的 x 都不早于
窗口左沿 xL = bar_index - drawBars（drawBars ≤ 9000）。

背景：小栋 10-03 真机 ZECUSDT 15m 报 'offset 9271 > 9270 at #main():1247'（画线段）。原来 xc 按
bar_index - 9990 夹，真机缓冲上限比 10000 小 ⇒ 起点早于缓冲的线一画就炸。本机没有 TradingView，
跑不了真机缓冲 ⇒ 这里只能静态证明「每个画图 x 都经过夹到 xL 的那一道」，外加 yAt 插值的数值性质。

判据（静态，逐个调用点）：
  ① 定义锚：xL / xc / drawBars 上限 9000 各一处，且没有残留的 9990；
  ② 每个 line.new / box.new / label.new 的 x 实参（line/box 是第 1、3 个，label 是第 1 个）必须是
     `bar_index`、`xc(...)`，或者一个**被证明是 xc 过的名字**：
       · 本函数内 `名字 = xc(...)` 赋的值（clipLine 的 a / b）；
       · drawCenter 的形参 x0 / x1 / xm —— 去它的**每个调用点**查对应位置实参是 xc(...)；
  ③ 数值：yAt 的 Python 逐行翻译，随机 2 万条线夹到 L，夹点 x ≥ L 且仍落在原线上（叉积 ≈ 0）。
--self-test：把源码里一处 xc 剥掉 / 把 xL 换回 9990，必须各自红。
"""
import os
import random
import re
import sys

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tradingview", "chanlun.pine")


def split_args(s, start):
    """从 s[start] == '(' 起切出顶层逗号分隔的实参，返回 (实参列表, 右括号位置)。"""
    depth, cur, out, i = 0, [], [], start
    q = None
    while i < len(s):
        c = s[i]
        if q:
            cur.append(c)
            if c == q:
                q = None
        elif c in "\"'":
            q = c
            cur.append(c)
        elif c in "([":
            depth += 1
            if depth > 1:
                cur.append(c)
        elif c in ")]":
            depth -= 1
            if depth == 0:
                out.append("".join(cur).strip())
                return out, i
            cur.append(c)
        elif c == "," and depth == 1:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)
        i += 1
    raise ValueError("括号没配上 @%d" % start)


def line_no(s, pos):
    return s.count("\n", 0, pos) + 1


def check(src):
    bad = []
    # ① 定义锚
    for w in ["xL() => bar_index - math.min(drawBars, bar_index)", "xc(int x) => math.max(x, xL())"]:
        if src.count(w) != 1:
            bad.append("定义锚 %r 命中 %d 次（应为 1）" % (w, src.count(w)))
    m = re.search(r"drawBars\s*=\s*input\.int\([^)]*maxval\s*=\s*(\d+)", src)
    if not m or int(m.group(1)) > 9000:
        bad.append("drawBars 的 maxval 不是 ≤ 9000（%s）" % (m.group(1) if m else "没找到"))
    code = "\n".join(l.split("//")[0] for l in src.split("\n"))     # 去注释再查残留
    if "9990" in code:
        bad.append("代码里还有 9990（旧的夹法）")
    # drawCenter 形参 x0/x1/xm 的位置
    m = re.search(r"^drawCenter\(([^)]*)\)\s*=>", src, re.M)
    params = [p.strip().split()[-1] for p in m.group(1).split(",")]
    dc_pos = {nm: params.index(nm) for nm in ("x0", "x1", "xm")}
    # 名字的证明按**调用点**做：它前面最近那一处 `名字 = ...` / `名字 := ...` 必须是 xc(...)。
    #   （按全文件名字做是错的：一处 `xm = xc(...)` 会替另一处没夹的 xm 作保 —— 自测第 5 臂就是抓这个的。）
    def proven(name, pos):
        last = None
        for a in re.finditer(r"^[ \t]*%s[ \t]*:?=[ \t]*(.*)$" % re.escape(name), src[:pos], re.M):
            last = a.group(1)
        return last is not None and last.startswith("xc(")
    ok_dc = True
    for mm in re.finditer(r"\bdrawCenter\(", src):
        if src[mm.start() - 1] == "\n":          # 定义本身
            continue
        args, _ = split_args(src, mm.end() - 1)
        for nm, k in dc_pos.items():
            if not (args[k].startswith("xc(") or proven(args[k], mm.start())):
                ok_dc = False
                bad.append("L%d drawCenter 实参 %s = %r 没过 xc" % (line_no(src, mm.start()), nm, args[k]))
    # ② 逐个画图调用点
    n = 0
    for mm in re.finditer(r"\b(line|box|label)\.new\(", src):
        kind = mm.group(1)
        args, _ = split_args(src, mm.end() - 1)
        idx = [0, 2] if kind in ("line", "box") else [0]
        for k in idx:
            a = args[k]
            n += 1
            if a == "bar_index" or a.startswith("xc("):
                continue
            if a in ("x0", "x1", "xm") and ok_dc:
                continue
            if re.fullmatch(r"\w+", a) and proven(a, mm.start()):
                continue
            bad.append("L%d %s.new 第 %d 个实参 %r 没证明过 xc" % (line_no(src, mm.start()), kind, k + 1, a))
    if n == 0:
        bad.append("一个画图调用点都没找到 —— 查不了 ≠ 通过")
    return bad, n


def y_at(x0, y0, x1, y1, x):                     # pine: yAt(...) 逐行翻译
    return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def numeric(trials=20000, seed=7):
    rnd = random.Random(seed)
    bad = 0
    for _ in range(trials):
        bi = rnd.randint(9000, 40000)
        L = bi - min(9000, bi)
        x0 = rnd.randint(bi - 15000, bi)
        x1 = rnd.randint(L, bi)                  # 调用点的过滤保证终点在窗口里
        y0, y1 = rnd.uniform(1, 1000), rnd.uniform(1, 1000)
        a, b = max(x0, L), max(x1, L)
        ya, yb = y_at(x0, y0, x1, y1, a), y_at(x0, y0, x1, y1, b)
        on_line = lambda x, y: abs((x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)) <= 1e-6 * max(1, abs(x1 - x0) * 1000)
        if a < L or b < L or not on_line(a, ya) or not on_line(b, yb):
            bad += 1
    return bad, trials


def main():
    src = open(SRC, encoding="utf-8").read()
    if "--self-test" in sys.argv:
        arms = {
            "剥掉一处 xc（画线段起点）": src.replace("a = xc(x0)", "a = x0", 1),
            "夹法换回 9990": src.replace("xL() => bar_index - math.min(drawBars, bar_index)", "xL() => bar_index - 9990", 1),
            "drawCenter 调用点 x0 不夹": src.replace("drawCenter(z, xc(base + a)", "drawCenter(z, base + a", 1),
            "信号价签不夹": src.replace("label.new(xc(base + s.bar)", "label.new(base + s.bar", 1),
            "笔中枢 xm 不夹": src.replace("xm = xc(base + pens.get(", "xm = (base + pens.get(", 1),
        }
        miss = 0
        for name, mut in arms.items():
            if mut == src:
                print("★ 变异 %-24s 没改到源码（锚漂了）" % name)
                miss += 1
                continue
            b, _ = check(mut)
            print("%s 变异 %-24s ⇒ %d 条红" % ("✓" if b else "✗", name, len(b)))
            miss += 0 if b else 1
        return 3 if miss else 0
    b, n = check(src)
    nb, nt = numeric()
    for x in b:
        print("✗", x)
    print("画图 x 实参 %d 个，没证明过夹到窗口左沿的 %d 个；yAt 数值 %d 条，失败 %d 条" % (n, len(b), nt, nb))
    return 1 if (b or nb) else 0


if __name__ == "__main__":
    sys.exit(main())
