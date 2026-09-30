#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 `config._warn_incomplete` 那行警告**没有把探针类的缺字说成本轮的图会出方框**。

为什么需要这个工具（实测，2026-09-30）：
`_font_probe()` 报的是 `_PROBES` 里四个**覆盖类**的代表字，不是"本轮会画上去的全部字"。
这两者常常不是同一个集合 —— 探针表 28 个字里已有 3 个（`✔ U+2714` / `✗ U+2717` / `✘ U+2718`）
**不在语料里**（`tools/fontcheck.py` 扫 `cards/` + `render/` 的字面量：831 个字符，这三个都不在）。

拿一支从现役字体删掉 `✔✗✘` 的字体（`notes/fonttest/make_stubs.py` 造的）实测：

    stderr  [字体] 警告（…）：no-check-marks.ttf 缺 符号/圈号/箭头（✔✗✘）；
            这些字会被画成方框而且不会报错。…
    stdout  ✓ 这份字体画得出会画上去的字符串里的全部字符          rc=0

**同一次运行、同一支字体，两句相反** —— 而"会被画成方框"那句说的是**不可能发生的事**：
语料里没有那三个字，谁也画不到它们。这正是本仓一直在防的那个病：**对正确的活报错**。

所以本工具断言三件：
  ① 缺字那行必须是**条件句**（画到时才出方框），不许出现陈述"本轮会出方框"的旧措辞；
  ② 必须点明这是**探针类代表字**、和 fontcheck 那份名单不是同一个集合；
  ③ 「判不了」那一支仍然要响，且必须说清"查不了 ≠ 覆盖好"。

不依赖任何字体文件、不依赖 fontTools（把 `_font_probe` 换成构造好的输入，只测措辞）。

**它现在挂在门上**（2026-09-30）：`tools/selfcheck.py` 单开一列 `WARN_WORDING` 调 `run()`。
理由：这个文件在 `agent/atlas/warn-incomplete-wording` 进 main 时**没有任何门调用它** ——
"文件在仓里"不等于"它在跑"，没人跑就没人会发现措辞被改回陈述句。挂上之前它是 0 个调用点。
"""
import io
import os
import sys
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config                                              # noqa: E402
from tools.fontcheck import default_paths, literal_chars   # noqa: E402


def run(verbose=True):
    """跑全部门。返回**不过的格数**（0 = 全过）。

    `verbose=False` 只打不过的格（selfcheck 一屏已经很长，通过的逐条打没人看）；
    不过的**永远打** —— 门红了却不说哪一格红，等于没说。
    这是照 `tools/verify_notdef.run` 的先例来的，两把自测同一个接口，门上才不用特判。
    """
    bad = 0
    checks = []

    def check(name, ok, why=""):
        nonlocal bad
        checks.append((name, ok))
        if not ok:
            bad += 1
        if verbose or not ok:
            print("  %s %s%s" % ("✓" if ok else "★", name, ("   ← " + why) if (why and not ok) else ""))

    def render(probe_result, cands=None):
        """把 `_font_probe` / `_best_alternative` 换成构造好的输入，抓 stderr。"""
        orig_probe, orig_alt = config._font_probe, config._best_alternative
        config._font_probe = lambda p: probe_result
        config._best_alternative = lambda p, c: None
        buf = io.StringIO()
        try:
            with redirect_stderr(buf):
                config._warn_incomplete("/tmp/自测字体.ttf", "自测", cands)
        finally:
            config._font_probe, config._best_alternative = orig_probe, orig_alt
        return buf.getvalue()

    if verbose:
        print(__doc__.strip().splitlines()[0])
        print("=" * 66)

    # ── 前提：夹具用的那三个字，现在真的不在语料里 ────────────────────────────
    chars, files, skipped = literal_chars(default_paths())
    if verbose:
        print("[前提] 语料 %d 个字符 / %d 个脚本 / 跳过 %d 个"
              % (len(chars), len(files), len(skipped)))
    absent = [c for c in "✔✗✘" if c not in chars]
    check("夹具前提：探针字 ✔✗✘ 不在语料里（不在才构成「本轮画不到」的用例）",
          len(absent) == 3,
          "现在在语料里的是 %r —— 这组夹具不再能证明该措辞，换字或删这一格" % ("".join(set("✔✗✘") - set(absent)),))

    # ── ① 缺字那行：条件句，不是陈述句 ────────────────────────────────────────
    msg = render((True, [("符号/圈号/箭头", "".join(absent))]))
    if verbose:
        print("[①] %s" % msg.strip())
    check("① 缺字行不含旧措辞「这些字会被画成方框而且不会报错」",
          "这些字会被画成方框而且不会报错" not in msg,
          "旧措辞仍在：那是陈述句，把探针类缺字说成了本轮的图")
    check("① 缺字行是条件句（出现「一旦有卡片画到」这类前提）",
          ("一旦有卡片画到" in msg) or ("画到时" in msg),
          "读起来像断言本轮出方框")
    check("① 缺字行不说「你的图/本轮的图 会出方框」",
          not any(s in msg for s in ("你的图会", "本轮的图会", "会被画成方框")),
          "把条件说成了结论")

    # ── ② 点明是哪一份名单 ────────────────────────────────────────────────────
    check("② 缺字行点明这是「探针类的代表字」", "探针类的代表字" in msg)
    check("② 缺字行点明与 fontcheck 那份名单不是同一个集合",
          ("fontcheck" in msg) and ("不是同一个集合" in msg))

    # ── ③ 判不了那一支仍然要响 ────────────────────────────────────────────────
    msg2 = render((False, []))
    if verbose:
        print("[③] %s" % msg2.strip())
    check("③ 判不了时必须出声", bool(msg2.strip()), "覆盖查不了却一个字没说 = 静默")
    check("③ 判不了时不许出现缺字断言", "缺 " not in msg2)
    check("③ 判不了时明说「查不了」不等于「覆盖好」",
          ("查不了" in msg2) and ("不等于" in msg2))

    # ── ④ 警告写 stderr，不污染 stdout（门是按 stdout 读的）──────────────────
    buf_out = io.StringIO()
    _probe = config._font_probe
    config._font_probe = lambda p: (True, [("符号/圈号/箭头", "✔✗✘")])
    try:
        with redirect_stderr(io.StringIO()):
            with redirect_stdout(buf_out):
                config._warn_incomplete("/tmp/自测字体.ttf", "自测")
    finally:
        config._font_probe = _probe
    check("④ 警告只走 stderr（stdout 保持干净）", buf_out.getvalue() == "",
          "stdout 收到 %r" % buf_out.getvalue()[:60])

    if verbose or bad:
        print("=" * 66)
        if bad:
            print("★ %d 格不过 —— 措辞会把探针类缺字说成本轮的图。" % bad)
        else:
            print("警告措辞的分寸正确：探针类缺字只作条件陈述，且点明了是哪一份名单。")
    return bad


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
