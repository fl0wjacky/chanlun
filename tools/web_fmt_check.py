#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""价签数字格式的一把尺（第四把，配 web_theme_sync.py / web_footer_check.py）。

**为什么单独立一把**：网页原来把中枢价签的数字写成
`Math.abs(v) >= 1000 ? String(Math.round(v)) : String(Math.round(v*100)/100)` ——
**1000 以上一律取整**。而 Python 那边是 `"[%g, %g]" % (round(z["ZD"], 2), round(z["ZG"], 2))`。
区间上下沿是**判三买三卖的价**，1681.99 显示成 1682 就"看起来破了"，其实没破 ——
所以这是**读数**问题，不是审美问题（Nova 2026-10-03 拍板：跟 Python 对齐）。
两边各写一份格式＝两处判据：这条尺子把「一致」变成能跑的断言。

判据（一句话）：**对同一张值表，网页的 `fmtG(v)` 必须与 Python 的 `"%g" % round(v, 2)` 逐字相同。**

值表怎么选的：真数据里出现过的价（ZEC 的 1004 / 1312 / 1324 / 1539.69 / 1558.8 / 1631.1 / 1681.99）、
另外把 `%g` 的**两个分界**钉住 —— **≥1e6 走指数**（999999.9 → `1e+06`）、**<1e-4 走指数**（0.00001 → `1e-05`）、
以及 6 位有效数字的**进位**（123456.78 → `123457`、1234.5 → `1234.5`）和尾零（1682.0 → `1682`）。
分界值全在表里：这三样漏掉任何一样，尺子会红（探针 ②③④ 就是拿它们钉的）。

★ **半位取偶，别退回 `toFixed`**：Python 的 `round()` / `%g` 在「正好一半」时**取偶**，
  而 JS 的 `toFixed` / `toPrecision` 是「一半就进位」。100000.5 两边差 1（Python `100000`、
  toFixed `100001`），123456.5 同理 —— 这跟「1681.99 显示成 1682」是同一个病（读数差 1 像破了）。
  所以 `fmtG` 是自己把 20 位有效数字摊开、判第 7 位起有没有过半，再按取偶走；
  表里那四个卡半位的值就是钉这一条的，探针 ⑤ 拿「交给 toFixed」的版本试过：**必红**。

★ **仍存在的差异（都碰不到，写下来免得下次当成尺子坏了）**：
  ① 只有「输入多于 2 位小数、且正好卡在 x.xx5」时，JS 的 `Math.round(v*100)`（半上进）
     与 Python 的 `round(v, 2)`（取偶）会差 1 分。本仓 tick 是 0.01 / 0.1 / 1 ⇒ 价格本身 ≤2 位小数。
  ② `-0.0`：Python 给 `-0`，`fmtG` 给 `0`（要走到得先有 −0.0 的价，那是数据出问题）。
  真碰到这两格，该改的是 `fmtG`，不是把值从表里删掉。

跑法：
  python3 tools/web_fmt_check.py            # 主跑：值表逐值对账
  python3 tools/web_fmt_check.py --selftest # 探针：六格都得变红（尺子先证明自己会红）
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = os.path.join(ROOT, "web", "layers.js")
BEGIN = "// >>> FMT_G"
END = "// <<< FMT_G"

# 值表：见文件头。分数、负数、0、指数两端、6 位有效数字的进位、尾零、**正好卡在半位** —— 都在。
VALUES = [
    1681.99, 1631.1, 1682.0, 1004.0, 1312.0, 1324.0, 1539.69, 1558.8, 1372.0, 1413.0,
    1234.5, 88.88, 0.01, 0.5, 1.5, 0.0, -1681.99, -0.5, -1004.0,
    12345.67, 123456.78, 99999.99, 100000.0, 100000.5, 999999.9, 1000000.0,
    1234567.8, 12345678.9, 0.0001, 0.00001, 0.000012, 0.000015,
    # ↓ 正好卡在第 6 位有效数字的半位：Python 取偶（100000 / 123456 / 1e+06），
    #   而 `toFixed` 的「半上进」会给 100001 / 123457 / 1e+06 —— 探针 ⑤ 就是拿这一格钉的。
    100001.5, 123456.5, 999999.5, 12345.5,
]


def py_ref(v):
    """Python 那一侧的**原文** —— 不是这里另写一个格式，就是把 chart_full_smooth.py 的式子跑一遍。"""
    return "%g" % round(v, 2)


def block(path=JS):
    """把带标记的那一段从 layers.js 里抠出来。抠不到 ⇒ 报错，不许静默跳过。"""
    src = open(path, encoding="utf-8").read()
    a, b = src.find(BEGIN), src.find(END)
    if a < 0 or b < 0 or b < a:
        raise SystemExit("✗ 在 %s 里找不到 %s / %s 标记 —— 抠不到被测量，尺子不猜" %
                         (os.path.relpath(path, ROOT), BEGIN, END))
    return src[src.index("\n", a) + 1:b]


class Crash(Exception):
    """候选实现自己跑崩了 —— 那也是「对不上」（探针里就跑崩过一版）。"""


def run(js, values):
    """把抠出来的 JS 段丢给 node 跑。`export function` 在脚本里是语法错 ⇒ 这里拆掉那个关键字
    （拆的是**关键字**，不是函数体 —— 被测量的那一行原文照跑）。"""
    body = js.replace("export function fmtG", "function fmtG")
    if "function fmtG" not in body:
        raise SystemExit("✗ 抠出来的段里没有 `fmtG` 的定义 —— 标记范围被改动了")
    harness = body + """
const vals = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(vals.map(fmtG)));
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(harness)
        path = f.name
    try:
        p = subprocess.run(["node", path, json.dumps(values)], capture_output=True, text=True)
    finally:
        os.unlink(path)
    if p.returncode != 0:
        raise Crash(p.stderr.strip().splitlines()[0] if p.stderr.strip() else "rc=%d" % p.returncode)
    return json.loads(p.stdout)


def check(js=None, values=None, verbose=True):
    """→ [(值, 网页, Python)]；空表＝逐字相同。"""
    js = block() if js is None else js
    values = VALUES if values is None else values
    try:
        got = run(js, values)
    except Crash as ex:
        if verbose:
            print("  ✗ 候选实现跑不动：%s" % ex)
        return [(values[0], "崩了", py_ref(values[0]))]      # 非空 ⇒ 算红
    bad = [(v, g, py_ref(v)) for v, g in zip(values, got) if g != py_ref(v)]
    if verbose:
        for v, g, want in bad[:12]:
            print("  ✗ %-12g 网页 %-12s Python %-12s" % (v, g, want))
        if len(bad) > 12:
            print("  … 还有 %d 个" % (len(bad) - 12))
    return bad


# ---- 探针：六格都得变红（尺子自己先证明会红，不然"全绿"证明不了任何事）----
OLD_WEB = '''function fmtG(v) { return Math.abs(v) >= 1000 ? String(Math.round(v)) : String(Math.round(v * 100) / 100); }
'''
NO_EXP = '''function fmtG(v) {
  if (!Number.isFinite(v)) return String(v);
  const r = Math.round(v * 100) / 100;
  if (r === 0) return '0';
  const e = Math.floor(Math.log10(Math.abs(r)));
  return String(Number(r.toFixed(Math.max(0, 5 - e))));
}
'''
NO_STRIP = '''function fmtG(v) { return (Math.round(v * 100) / 100).toFixed(2); }
'''
SIG3 = '''function fmtG(v) {
  const r = Math.round(v * 100) / 100;
  if (r === 0) return '0';
  const e = Math.floor(Math.log10(Math.abs(r)));
  return String(Number(r.toFixed(Math.max(0, 2 - e))));
}
'''
# ↑ 我自己那第一版就是这么写的（取整交给 toFixed）—— 32/36 相同，**正好卡半位的四个值全差 1**。
HALF_UP = '''function fmtG(v) {
  if (!Number.isFinite(v)) return String(v);
  let x = Math.round(v * 100) / 100;
  if (x === 0) return '0';
  const sign = x < 0 ? '-' : '';
  x = Math.abs(x);
  let e = Math.floor(Math.log10(x));
  const rs = Number(x.toFixed(Math.max(0, 5 - e)));
  e = Math.floor(Math.log10(Math.abs(rs)));
  if (e >= 6 || e < -4) {
    const m = rs / Math.pow(10, e);
    return sign + String(Number(m.toFixed(5))) + 'e' + (e < 0 ? '-' : '+') + String(Math.abs(e)).padStart(2, '0');
  }
  return sign + String(rs);
}
'''


def selftest():
    ok = True
    for name, js in [
        ("① 旧版（≥1000 取整）", OLD_WEB),
        ("② 去掉指数分支", NO_EXP),
        ("③ 不去尾零（恒两位小数）", NO_STRIP),
        ("④ 有效数字 6→3", SIG3),
        ("⑤ 取整交给 toFixed（半上进，不是取偶）", HALF_UP),
    ]:
        bad = check(js, verbose=False)
        hit = ", ".join("%g→%s(要%s)" % (v, g, w) for v, g, w in bad[:2])
        print("  %s %s：%d 个对不上  %s" % ("✓" if bad else "✗ 没变红", name, len(bad), hit))
        ok = ok and bool(bad)
    # ⑥ 标记被删 ⇒ 必须报错，不许静默跳过
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(open(JS, encoding="utf-8").read().replace(BEGIN, "// (marker removed)"))
        tmp = f.name
    try:
        block(tmp)
        print("  ✗ ⑥ 标记没了却不报错")
        ok = False
    except SystemExit:
        print("  ✓ ⑥ 标记没了 ⇒ 报错")
    finally:
        os.unlink(tmp)
    return ok


# ── 命令行参数：两种自测拼法都认，**不认识的参数直接报错退出**（rc=2）─────────────
# ★ card-b6609942-1ad：原来写的是 `if "--selftest" in argv` —— 不认识的参数被**静默吞掉**、
#   闷头跑主跑。自测没跑，看着却像跑过了：`--self-test`（带连字符，check_parity 就是这么写的）
#   在这一版会被吞 ⇒ 印出来的是**主跑**的结果；拼错的旗标同理，而主跑恰好绿的时候，
#   看上去就是「一次通过的自测」。rc=2 跟 argparse 的用法错误同码（①② 本来就是这么退的）。
_SELFTEST_FLAGS = ("--selftest", "--self-test")


def _selftest_requested(argv):
    unknown = [x for x in argv if x not in _SELFTEST_FLAGS]
    if unknown:
        sys.stderr.write("不认识的参数：%s（只认 %s）\n"
                         % (" ".join(unknown), " / ".join(_SELFTEST_FLAGS)))
        sys.exit(2)
    return any(x in _SELFTEST_FLAGS for x in argv)


def main(argv):
    if _selftest_requested(argv):
        print("探针（每格都必须变红）：")
        sys.exit(0 if selftest() else 1)
    bad = check()
    if not bad:
        print("✓ 价签格式与 Python 的 `\"%%g\" %% round(v, 2)` 逐字相同（%d 个值，含 1e6 / 1e-4 / 6 位有效数字三处分界）"
              % len(VALUES))
        return 0
    print("✗ 有 %d 个值与 Python 对不上" % len(bad))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
