#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""观测法量「真会被画上去的字符」——渲染一遍，记下每一次 text() 的入参。

为什么不是「扫字面量」：
    扫字面量问的是「代码里写了什么字」，它的答案永远是**上界**。往上界收也没用——
    去掉 docstring 还是上界，再去掉 raise/assert 里的串还是上界，还能再去（只在
    debug 分支里的串、被 `if False` 包住的串……）。**这条链没有终点**，因为定义域
    一直是「代码里写了什么」。

    换成问「绘制真的被要求画哪些字」，定义域就换了，链才有终点：**没被画到的字符
    不经过这个钩子**。这不是更紧的上界，是另一个量。

它也有它自己的分母（别拿它当全集用）：
    得到的是「**跑通的模块 × 喂进去的那份数据**」的真值。跑不到的东西照样会画字，
    只是这次没进集合——所以输出里必须报分母：跑通几个 / 共几个 / 没跑通的是哪几个、
    卡在哪一步。**一个不报分母的扫描，和一个扫了空目录的扫描，打印出来一模一样。**

    数据也是一维：`cards/model_dissent.py:198` 那个 `if thru:` 只有存在「贯穿」行时
    才画那句话，所以集合是 (代码 × 数据) 的函数，不只是代码的函数。

用法（仓库根目录）：
    python3 tools/measure_drawn.py             # 打印 ref + 分母 + 分类清单
    python3 tools/measure_drawn.py --emit      # 多打一行可当 probe 的串
    CHANLUN_FONT=/path/to/cjk.ttf python3 tools/measure_drawn.py

    没装中文字体也能跑（本机用 DejaVu 顶替亦可）：这里量的是**交给绘制的字符串**，
    与字体无关。但若有卡片按量出来的宽度做分支，字体就会影响集合——那种分支目前
    没发现，「没发现」不等于「没有」。
"""
import glob
import importlib
import os
import subprocess
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if not os.environ.get("CHANLUN_FONT"):
    # 只为让 config 能 import；量的东西与字体无关（见文件头）。
    for c in ("/usr/share/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(c):
            os.environ["CHANLUN_FONT"] = c
            break

import PIL.ImageDraw as _ID

DRAWN = []                       # 每一次 text()/multiline_text() 的入参，按调用顺序
_text = _ID.ImageDraw.text


def _hooked(self, xy, t, *a, **k):
    DRAWN.append(t)
    return _text(self, xy, t, *a, **k)


_ID.ImageDraw.text = _hooked
_ID.ImageDraw.multiline_text = lambda self, xy, t, *a, **k: (DRAWN.append(t),
                                                            _text(self, xy, t, *a, **k))[1]


def targets():
    """要跑的模块：全部卡片（含不在合集里的两张）+ render/ 下每个出图脚本。"""
    out = []
    try:
        from cards.build_all import CARDS
        out += [("cards." + n, n) for n, _ in CARDS]
    except Exception as e:
        print("! 读不到 cards/build_all.py 的 CARDS：%s" % e)
    have = {n for _, n in out}
    for p in sorted(glob.glob(os.path.join("cards", "*.py"))):
        n = os.path.basename(p)[:-3]
        if n not in have and n not in ("__init__", "base", "build_all", "zec_data"):
            out.append(("cards." + n, n))
    for p in sorted(glob.glob(os.path.join("render", "chart_*.py"))):
        n = os.path.basename(p)[:-3]
        out.append(("render." + n, n))
    return out


def ref():
    """把数绑到 ref 上：换个分支，同一个口径的字符数会差几十个。

    报一个「真值」而不说是哪棵树上的真值，跟不报分母是同一个坑。
    """
    def g(*a):
        try:
            return subprocess.check_output(("git",) + a, stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            return "?"
    return g("rev-parse", "--abbrev-ref", "HEAD"), g("rev-parse", "HEAD")


def classify(c):
    o = ord(c)
    if o < 128:
        return "ascii"
    if 0x3000 <= o <= 0x303F or 0xFF00 <= o <= 0xFFEF:
        return "cjk标点"
    if 0x4E00 <= o <= 0x9FFF:
        return "cjk汉字"
    if 0x2460 <= o <= 0x24FF or 0x2070 <= o <= 0x209F:
        return "圈号/下标"
    return "其他符号"


ORDER = ("ascii", "cjk汉字", "cjk标点", "圈号/下标", "其他符号")


def main():
    ts = targets()
    ok, bad = [], []
    for mod, name in ts:
        try:
            m = importlib.import_module(mod)
            if mod.startswith("cards."):
                m.build()
            else:
                for fn in ("main", "build", "run"):
                    if hasattr(m, fn):
                        getattr(m, fn)()
                        break
                else:
                    raise RuntimeError("没有 main / build / run 入口")
            ok.append(name)
        except Exception as e:
            bad.append((name, "%s: %s" % (type(e).__name__, e)))

    chars = {c for s in DRAWN for c in s if c.strip()}
    g = defaultdict(set)
    for c in chars:
        g[classify(c)].add(c)

    br, sha = ref()
    print("\nref: %s @ %s" % (br, sha[:12]))
    # 分母先于分子：不报分母的数，和扫了空目录的数，打印出来一模一样。
    print("跑通 %d / 共 %d 个模块" % (len(ok), len(ts)))
    for n, e in bad:
        print("  跑不到 %-22s %s" % (n, e))
    print("draw.text() 调用 %d 次；**真画上去的字符 %d 个**（空白已剔）" % (len(DRAWN), len(chars)))
    for k in ORDER:
        print("【%s】%d 种" % (k, len(g[k])))
    if "--emit" in sys.argv:
        print("\nprobe = %r" % "".join(sorted(chars)))
    if bad:
        print("\n注意：这是「跑到的模块 × 喂进去的数据」的真值，**不是全集**——"
              "上面那 %d 个没跑到的模块照样会画字，每一个 `跑不到` 就是这次的一个盲区。" % len(bad))
    return 0


if __name__ == "__main__":
    sys.exit(main())
