# -*- coding: utf-8 -*-
"""项目路径常量。所有脚本从这里取路径，不要各自硬编码。

可用环境变量覆盖：
    CHANLUN_OUT      产物目录
    CHANLUN_UPLOADS  用户上传截图所在目录
    CHANLUN_FONT     中文字体文件
"""
import os

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

# 中文字体：按顺序取第一个存在的（Linux 沙箱 → macOS）
_FONTS = [
    os.environ.get("CHANLUN_FONT"),
    "/usr/share/fonts/droid-nonlatin/DroidSansFallbackFull.ttf",
    "/Library/Fonts/Arial Unicode.ttf",           # macOS：中文 + ✓✗₁₂₃ 都有，字宽与 STHeiti 相差 <1%
    "/System/Library/Fonts/STHeiti Medium.ttc",   # 缺 ✓✗₁₂₃（显示成方框）
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]
FONT = next((f for f in _FONTS if f and os.path.exists(f)), None)
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
