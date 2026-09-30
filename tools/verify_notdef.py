# -*- coding: utf-8 -*-
"""`config._notdef_mask` 的自测：**不要字体文件、不要 fontTools**（喂假字体对象）。

守的这一格（card-5ddb51d2-003）：私用区**可以**被字体映射 —— 图标字体就是靠这个活的。
三个私用区码位一起被映射成同一个**空白**字形时，三个遮罩全等且为空，多数票"齐"了，
于是那层「判不了」的保护根本不触发；代码把空白遮罩当成 .notdef，接着所有真字形都
"不等于 .notdef" ⇒ 报「查过，一个都不缺」，而真缺的字（会画成方框的那些）一个都不报。
**静默假绿，退出码也不会替你发现。**

    python3 tools/verify_notdef.py      # 退出码 0 = 全部格都对

`run()` 返回不过的格数 —— `tools/selfcheck.py` 直接调它，把它挂在「字体覆盖」那扇门**前面**：
那一门的基准（`.notdef`）就是这里在测的东西，基准错了那扇门就是假绿，先看这里再看那边。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# 假字体里的常数。**BOX 的 432 是这里编的，不是某支真字体在某个字号下的尺寸** ——
# 真字体：Droid@16 = 192B、@24 = 432B；Noto@16 = 256B、@24 = 624B（尺寸不说清就会对不上号）。
BOX = b"\x01" * 432          # "真 .notdef"：一个方框，有墨
BLANK = b""                  # 被映射到的空白字形：**没有墨**
B_MASK = b"\x03" * 270       # 一个真字形（'B'）：**有墨**，长度和 .notdef 不同


class FakeFont:
    """只实现 `getmask` —— `_notdef_mask` 只用得到它。表里没有的码位一律给真 .notdef。"""

    def __init__(self, table, notdef=BOX):
        self.table = table
        self.notdef = notdef

    def getmask(self, c):
        return self.table.get(c, self.notdef)


P = config._NOTDEF_CHARS                               # 三个私用区码位
UN = getattr(config, "_UNMAPPED_CHARS", ())            # 三个永久未分配码位（没有 = 缺口还没修）

CASES = [
    ("正常字体：私用区三个都画 .notdef，未分配码位也画 .notdef",
     FakeFont({}), BOX),
    ("私用区三个一起被映射成**空白**字形（← 本自测要守的那一格）",
     FakeFont({c: BLANK for c in P}), BOX),
    ("私用区三个互不相同（旧契约：判不了，不猜）",
     FakeFont({P[0]: b"\xaa", P[1]: b"\xbb", P[2]: b"\xcc"}), None),

    # --- 边界表（@bram-9d29 在 card-8ac04844-0ca 上列的五行，逐行收进夹具）---
    # 为什么把"两个→真字形"也收进来：基准**有墨但仍是错**的那一行，"遮罩长度为 0 ⇒ 判不了"
    # 那类改法**不响**（长度 270 不是 0），所以只测长度等于只测一半。见卡上对照表。
    ("边界① 一个私用区码位 → 空白字形",
     FakeFont({P[0]: BLANK}), BOX),
    ("边界② 两个 → 同一个空白字形",
     FakeFont({P[0]: BLANK, P[1]: BLANK}), BOX),
    ("边界④ 两个 → 同一个**真字形** 'B'（基准有墨、但是错的）",
     FakeFont({P[0]: B_MASK, P[1]: B_MASK}), BOX),

    # --- 交叉校验**自己**拿不到参照的两格（@bram-9d29 在 card-5ddb51d2-003 上逮到的残留）---
    # 守的是那行守卫的**写法**：`if not ref:` 不能写成 `if ref and …`。`ref` 是 bytes、
    # `b""` 是假值 ⇒ 写成真值判断时这两格会**静默跳过**校验、把 base 原样退回，
    # 于是「空白基准冒充 .notdef」原样回来。两格都是假字体，真字体不会这样。
    ("残留⑦ 未分配码位三个**都画空白**（参照自己也没墨）⇒ 判不了，不许退回空白基准",
     FakeFont({c: BLANK for c in P + UN}), None),
    ("残留⑧ 未分配码位三个**互不相同**（压根没有一致参照）⇒ 判不了，不许退回空白基准",
     FakeFont(dict({c: BLANK for c in P}, **{UN[0]: b"\xaa", UN[1]: b"\xbb", UN[2]: b"\xcc"})), None),
]


def run(verbose=True):
    """跑全部格，返回**不过的格数**（0 = 全过）。

    verbose=False 时只打印不过的格 —— 给 `selfcheck` 用，那里一屏已经很长；
    但**不过的格永远打印**，「出声」不跟着 verbose 走。
    """
    bad = 0
    if not UN:
        print("  · 这一版 config 没有 _UNMAPPED_CHARS：基准没和【永久未分配】码位对过 —— 就是要守的缺口")

    for why, font, want in CASES:
        got = config._notdef_mask(font)
        ok = got == want
        bad += not ok
        if verbose or not ok:
            print("  %s %s" % ("✓" if ok else "✗", why))
            print("      基准 = %s（长度 %d）" % (
                "None（判不了）" if got is None else ("空白遮罩" if got == BLANK else
                                                      ("真 .notdef" if got == BOX else repr(got[:8]))),
                len(got or b"")))
            if not ok:
                print("      期望 = %s" % ("None" if want is None else "真 .notdef"))

    # 把基准接到后果上：拿空白遮罩当基准时，一个真缺的字**不会被报出来** —— 这才是那条洞的代价。
    f = FakeFont({c: BLANK for c in P})
    silent = bytes(f.getmask("中")) != BLANK
    if verbose or not silent:
        print("  ✓ 夹具前提：真缺的「中」会被画成方框（≠ 空白基准）⇒ 拿空白当基准就报【不缺】，静默"
              if silent else
              "  ✗ 夹具前提不成立：真缺的字居然和空白基准一样 —— 这个用例证明不了东西")
    bad += not silent

    if verbose:
        print("=" * 66)
    if bad:
        print("_notdef_mask 自测未通过：%d 处。空白基准会被当成 .notdef。" % bad)
    elif verbose:
        print("_notdef_mask 自测通过：基准与【永久未分配】码位对齐，空白基准不再冒充 .notdef。")
    return bad


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
