# -*- coding: utf-8 -*-
"""项目路径常量。所有脚本从这里取路径，不要各自硬编码。

可用环境变量覆盖：
    CHANLUN_OUT      产物目录
    CHANLUN_UPLOADS  用户上传截图所在目录
    CHANLUN_FONT     中文字体文件
"""
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
ARCHIVE = os.path.join(ROOT, "archive")

_MINIS = "/var/minis/attachments"        # Minis 沙箱：产物直接落到会话附件目录，方便贴到对话里

OUT = os.environ.get("CHANLUN_OUT") or (_MINIS if os.path.isdir(_MINIS)
                                         else os.path.join(ROOT, "out"))
UPLOADS = os.environ.get("CHANLUN_UPLOADS") or (os.path.join(_MINIS, "uploads")
                                                 if os.path.isdir(_MINIS)
                                                 else os.path.join(ROOT, "uploads"))
os.makedirs(OUT, exist_ok=True)

# 中文字体：按顺序取第一个**既存在、又真画得出拉丁和中文**的（Linux 沙箱 → macOS）。
#
# 为什么不能只判 os.path.exists：文件在、能加载，不等于画得出来。反例就在下面那张表里——
# DroidSansFallbackFull 是 CJK **fallback** 字体，拉丁部分在 Android 上由 Roboto 补，
# 单独用它会把每个数字、字母、括号、% 全画成方框，而且**不报错、退出码 0**，只有看图才发现。
# 判据（免 fontTools）：私用区 U+E000 没有字体会为它设计字形，所以任何字体给它的都是 .notdef；
# 一个字符画出来若和它一模一样，就是缺字。
_FONTS = [
    os.environ.get("CHANLUN_FONT"),
    "/usr/share/fonts/droid-nonlatin/DroidSansFallbackFull.ttf",
    "/Library/Fonts/Arial Unicode.ttf",           # macOS：中文 + ✓✗₁₂₃ 都有，字宽与 STHeiti 相差 <1%
    "/System/Library/Fonts/STHeiti Medium.ttc",   # 缺 ✓✗₁₂₃（显示成方框）
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

_NOTDEF_CHAR = ""        # 私用区探针，用来取 .notdef 的模样
# 哨兵字取自卡片真的会画出来的字符（cards/ + render/ 的字面量统计：origin/main 上 882 个字）。
# 三类独立计数：某一类缺就说那一类，不因为"整体看着还行"把它吞掉。
#
# **刻意不收「符号」类**（`× — ↑ ① ★ ✓ ✗` 那一族，Droid 上是 0/29）。理由不是它不要紧，而是
# 它放进这里只会制造一个**永远响、且永远没法按它办**的警告：实测没有一支候选字体同时具备中文和
# `✗`（Droid 0/29，Noto 也只差 `✗` 一个），所以「换一支覆盖更全的字体」这句建议在 Linux 上是空话，
# 而按字体的探针会每次运行都响，跟卡片改没改无关。缺 `✗` 是**卡片用字**问题，由 tools/fontcheck.py
# 报（rc=1），那是它该管的事——两个地方各报一遍、严重程度还不一样，只会让人两边都不信。
_PROBES = (
    ("拉丁字母/数字/ASCII 标点", "Aaz09%(),.[]"),
    ("中文",                     "中枢线段买点背驰趋势"),
    ("全角标点",                 "、。《》「」（）"),
)
_PROBE_CACHE = {}


def _missing(font_path, probe, size=16):
    """返回 probe 里画不出来的那些字；字体加载失败则整串都算缺。"""
    key = (font_path, probe, size)
    if key not in _PROBE_CACHE:
        try:
            from PIL import ImageFont
            f = ImageFont.truetype(font_path, size)
            notdef = bytes(f.getmask(_NOTDEF_CHAR))     # PIL 9.0 的 ImagingCore 没有 .tobytes()
            _PROBE_CACHE[key] = "".join(c for c in probe if bytes(f.getmask(c)) == notdef)
        except Exception:
            _PROBE_CACHE[key] = probe                   # 加载不了就当它一个都画不出来，不猜
    return _PROBE_CACHE[key]


def _font_gaps(font_path):
    """[(类别名, 缺的字), …]；空列表 = 四类全有。"""
    gaps = []
    for name, probe in _PROBES:
        miss = _missing(font_path, probe)
        if miss:
            gaps.append((name, miss))
    return gaps


def _font_score(font_path):
    """覆盖完整的类数。用来在候选之间排序。"""
    return len(_PROBES) - len(_font_gaps(font_path))


def _warn_incomplete(font_path, why):
    gaps = _font_gaps(font_path)
    if gaps:
        print("[字体] 警告（%s）：%s 缺 %s；这些字会被画成方框而且不会报错，"
              "请用 CHANLUN_FONT 指定一支覆盖更全的字体。"
              % (why, os.path.basename(font_path),
                 "、".join("%s（%s）" % (n, m) for n, m in gaps)), file=sys.stderr)


def _pick_font():
    """显式指定的照用（缺字只警告，不推翻人的选择）；否则取候选里覆盖类数最多的那支。"""
    env = os.environ.get("CHANLUN_FONT")
    if env:
        if not os.path.exists(env):
            raise FileNotFoundError("CHANLUN_FONT 指向的字体不存在：%s" % env)
        _warn_incomplete(env, "来自 CHANLUN_FONT")
        return env
    cands = [f for f in _FONTS if f and os.path.exists(f)]
    if not cands:
        return None
    # 取覆盖最全的，同分取靠前的（保留 _FONTS 的偏好顺序；max 遇平局取第一个）。
    # 为什么不是"按顺序取第一支过线的"：Linux 上 Droid 排第一但只覆盖 2/4，
    # 第一支过线的会把 Noto 挡在身后——那正是这次这个坑。
    best = max(cands, key=_font_score)
    _warn_incomplete(best, "候选里没有一支覆盖完整")
    return best


FONT = _pick_font()
if FONT is None:
    raise FileNotFoundError("找不到中文字体，请用环境变量 CHANLUN_FONT 指定")

SCREENSHOT = os.path.join(UPLOADS, "photo_26B0F906.png")   # TradingView 截图（chart_annotate / chart_signals / extract_chart_pens 用）


# 价格精度（第 64 课：「精度一旦预设，就一定要一路保持」）：按数据文件名前缀明写，取交易所最小价位。
# 想换精度（比如 AAPL 取整到 0.1）就改这里 —— 改了，所有结构和卡上的数字都会跟着变。
TICK = {
    "aaplusdt": 0.01,     # 币安 AAPLUSDT 永续
    "zec": 0.01,          # 币安 ZECUSDT 永续
    "btc": 0.1,           # 币安 BTCUSDT 永续
}


def tick_of(fn):
    """数据文件 → 精度。没写明的标的直接报错，不默默用原始价格。"""
    base = os.path.basename(fn)
    for k, v in TICK.items():
        if base.startswith(k):
            return v
    raise KeyError("config.TICK 里没有给 %s 写明精度" % base)


def data(name):
    return os.path.join(DATA, name)


def out(name):
    return os.path.join(OUT, name)
