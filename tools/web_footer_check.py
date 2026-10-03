#!/usr/bin/env python3
"""图脚「买卖点」那段的一把尺（第三把，配 web_theme_sync.py）。

为什么单独立一把：2026-10-03 联调发现 `web/app.js` 那段买卖点文字是**逐个信号列出来**的，
长度跟着**信号数**涨。仓里的样本只有 4~17 个信号（最长 50 字符）＝看着像一句归纳，
所以配色尺、并排图、Atlas 的复核三把尺全是绿的 —— 真到了 Bram 后台的实时源
（ZECUSDT 15m，20160 根）一次 66 个信号 ⇒ 197 字符，390px 下图脚要 471px。**样本比线上小
两个数量级，尺子就量不到**。这条尺子拿一份**实时规模**的样本来量，且量的是「会不会换行」。

判据（说清楚主语和宽度，不然同一句规则两个结果 —— Atlas 2026-10-03 提的）：
  **每一个层级（线段中枢层 / 类中枢层）自己那段文字，在 390px 视口的图脚那一格（宽 362px、
  字号 10px）里必须放得下一行。** 不是「整条图脚一行」—— 整条还带着根数/笔数/精度/数据源，
  在手机上本来就是四行，那个当不成判据。

宽度怎么来的（都是**量**的，不是估的；量法：在真页面上用同字体的 span 量 getBoundingClientRect）：
  390px 视口 → 图脚那格 clientWidth = **362px**，字号 10px/行高 15px。
  同一批文字里最费的每字宽 = **8.11px**（`线段中枢层 三买×7·一卖·二卖·三卖×4` 21 字 170.3px）。
  362 ÷ 8.11 = 44.6 ⇒ **预算 44 字符**。取最费的每字宽是故意的：这是上界，宁可提前叫。
  ★ 这是**字符预算**，不是像素量 —— 仓里没有浏览器，真量像素得把 playwright 塞进仓，那是另一个决定。
    44 字在实测里 ≈357px（放得下），而「六种全齐＋待确认」49 字实测 356px —— 只差 6px 就换行，
    所以 44 这条线会把那种边缘情形叫红。**知道它偏保守，是保守，不是准。**

跑法：
  python3 tools/web_footer_check.py            # 主跑：拿实时规模的样本量
  python3 tools/web_footer_check.py --selftest # 探针：四格都得变红（尺子自己先证明会红）
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = os.path.join(ROOT, "web", "app.js")
FIX = os.path.join(ROOT, "web", "fixtures", "signals_zec15m_live.json")

BEGIN = "// >>> SIG_TIER_TEXT"
END = "// <<< SIG_TIER_TEXT"

LINE_PX = 362.0        # 390px 视口下图脚那格的 clientWidth（量出来的）
PX_PER_CHAR = 8.11     # 实测最费的每字宽（见文件头）
BUDGET = int(LINE_PX // PX_PER_CHAR)   # 44


def block(path=JS):
    """把带标记的那一段从 app.js 里抠出来。抠不到 ⇒ 直接报错，不许静默跳过。"""
    src = open(path, encoding="utf-8").read()
    a = src.find(BEGIN)
    b = src.find(END)
    if a < 0 or b < 0 or b < a:
        raise SystemExit("✗ 在 %s 里找不到 %s / %s 标记 —— 抠不到被测量，尺子不猜" %
                         (os.path.relpath(path, ROOT), BEGIN, END))
    # 从标记**那一行的行尾**开始切：标记行后面还跟着说明文字，带上它会变成 JS 语法错
    return src[src.index("\n", a) + 1:b]


def run(js, fixture):
    """把抠出来的 JS 段丢给 node 跑，喂 fixture，收每层那段文字。"""
    harness = js + """
const fs = require('fs');
const d = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));   // argv[1] 是脚本自己
process.stdout.write(JSON.stringify({
  seg: sigTierText(d.signals.seg || []),
  pen: sigTierText(d.signals.pen || []),
  n_seg: (d.signals.seg || []).length,
  n_pen: (d.signals.pen || []).length,
  nbars: d.nbars,
}));
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(harness)
        tmp = f.name
    try:
        p = subprocess.run(["node", tmp, fixture], capture_output=True, text=True, timeout=60)
    finally:
        os.unlink(tmp)
    if p.returncode != 0:
        raise SystemExit("✗ node 跑不起来：\n" + p.stderr.strip())
    return json.loads(p.stdout)


def measure(path=JS, fixture=FIX):
    """→ (结果 dict, 有没过)。"""
    d = json.load(open(fixture, encoding="utf-8"))
    got = run(block(path), fixture)
    rows, bad = [], []
    for tier, label in (("seg", "线段中枢层"), ("pen", "类中枢层")):
        t = got[tier]
        n = len(t)
        px = n * PX_PER_CHAR
        ok = n <= BUDGET
        rows.append((label, got["n_" + tier], n, px, ok))
        if not ok:
            bad.append((label, n))
    print("  样本：%s（%s 根，%s 个信号：线段中枢层 %d ＋ 类中枢层 %d）"
          % (d.get("_source", os.path.relpath(fixture, ROOT)), got["nbars"], got["n_seg"] + got["n_pen"],
             got["n_seg"], got["n_pen"]))
    print("  预算：每个层级 ≤ %d 字符（390px 视口 / 图脚格 %gpx / 最费每字 %gpx）\n"
          % (BUDGET, LINE_PX, PX_PER_CHAR))
    print("  %-14s %6s %6s %9s  %s" % ("层级", "信号数", "字符", "≈px", "判定"))
    for label, nsig, n, px, ok in rows:
        print("  %-14s %6d %6d %9.0f  %s" % (label, nsig, n, px, "✓ 一行" if ok else "✗ 放不下（要 %.1f 行）" % (px / LINE_PX)))
    print()
    for tier, label in (("seg", "线段中枢层"), ("pen", "类中枢层")):
        print("  %s：%s" % (label, got[tier]))
    print()
    return got, not bad


def selftest():
    """四格探针：改坏一处必须变红。尺子先证明自己会红，绿才算数。"""
    old = ("const sigTierText = (s) => s.map((x) => `${x.kind}${x.confirmed ? '' : '?'}`)"
           ".join('·') || '无';")
    cases = []

    # ① 老写法（34b5739a 原来那一行）必须红
    try:
        _, ok = measure_quiet(old)
        cases.append(("① 老写法（逐个 join，34b5739a 原样）", ok is False))
    except SystemExit as e:
        cases.append(("① 老写法（逐个 join，34b5739a 原样）", False))

    # ② 标记删掉 ⇒ 必须报错（不许静默跳过被测量）
    src = open(JS, encoding="utf-8").read().replace(BEGIN, "// (marker removed)")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(src)
        tmp = f.name
    try:
        block(tmp)
        cases.append(("② 标记被删掉 ⇒ 报错", False))
    except SystemExit:
        cases.append(("② 标记被删掉 ⇒ 报错", True))
    finally:
        os.unlink(tmp)

    # ③ 认不出的 kind 必须**出现在**那段文字里（注释里写了「不许静默吞掉」，就得有探针）
    probe_js = block() + """
process.stdout.write(JSON.stringify({t: sigTierText([
  {kind: '四买', confirmed: true}, {kind: '三卖', confirmed: true}, {kind: '三卖', confirmed: false},
])}));
"""
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(probe_js)
            tmp2 = f.name
        p = subprocess.run(["node", tmp2], capture_output=True, text=True, timeout=60)
        os.unlink(tmp2)
        got = json.loads(p.stdout)["t"]
        # 四买 要露面；三卖 与 三卖? 要分开算（待确认单独计数）
        cases.append(("③ 认不出的 kind 没被吞掉、且待确认单独计数（%s）" % got,
                      "四买" in got and "三卖?" in got))
    except Exception:
        cases.append(("③ 认不出的 kind 没被吞掉、且待确认单独计数", False))

    # ④ 塞一份「12 项全带计数」的极端输入 ⇒ 必须红
    try:
        _, ok = measure_quiet(block(), fixture=None, synthetic=True)
        cases.append(("④ 极端输入（6 种 × 已确认/待确认 12 项）", ok is False))
    except SystemExit:
        cases.append(("④ 极端输入（6 种 × 已确认/待确认 12 项）", False))

    print("探针（每一格都必须红）：")
    for name, red in cases:
        print("  %s %s" % ("✓" if red else "✗ 没红", name))
    n_ok = sum(1 for _, r in cases if r)
    print("\n%s %d/%d 格探针都能变红" % ("✓" if n_ok == len(cases) else "✗", n_ok, len(cases)))
    return n_ok == len(cases)


def measure_quiet(js, fixture=None, synthetic=False):
    """不打印，只回报。synthetic：不看样本，直接喂 12 项的极端输入。"""
    if synthetic:
        payload = {"一买": 12, "一买?": 2, "二买": 9, "二买?": 3, "三买": 29, "三买?": 1,
                   "一卖": 5, "一卖?": 2, "二卖": 7, "二卖?": 3, "三卖": 29, "三卖?": 1}
        # ★ 每一项要**按它的计数重复生成**：只生成一个的话计数全是 1，那串就没有 ×N、
        #   长度根本到不了极端值 —— 探针会假绿（第一版就是这么写错的，量出来 41 字符，没过线）
        arr = ",".join("{kind:'%s',confirmed:%s}" % (k.rstrip("?"), "false" if k.endswith("?") else "true")
                       for k, c in payload.items() for _ in range(c))
        code = js + "\nconst t = sigTierText([%s]);\nprocess.stdout.write(JSON.stringify({t}));" % arr
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp = f.name
        try:
            p = subprocess.run(["node", tmp], capture_output=True, text=True, timeout=60)
        finally:
            os.unlink(tmp)
        if p.returncode != 0:
            raise SystemExit(p.stderr)
        t = json.loads(p.stdout)["t"]
        n = len(t)
        return {"极端": t}, n <= BUDGET

    got = run(js, fixture or FIX)
    ok = all(len(got[t]) <= BUDGET for t in ("seg", "pen"))
    return got, ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    print("图脚「买卖点」段的宽度尺（390px 视口）\n")
    try:
        _, ok = measure()
    except SystemExit as e:
        print(str(e))
        sys.exit(1)
    if ok:
        print("✓ 两个层级都在一行内（%s）" % os.path.relpath(JS, ROOT))
        sys.exit(0)
    print("✗ 有一段放不下一行 —— 图脚在手机上是几行糊在一起的字（见上面的 ≈px）")
    sys.exit(1)
