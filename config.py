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

# 取 .notdef 的模样用**三个**私用区码位，不是取一个——因为**字体可以映射私用区**。
# 实测（fontTools 现造一支把 U+E000 映射到 'A' 字形的字体）：
#   探针拿到的是 'A' 的墨迹 → 真缺的「中」（渲成真 .notdef）跟它比 → 判成"有"（**假绿**）
#                             → 真有的 'A' 跟它比 → 判成"缺"（**假红**）
#   两个方向都错，**而且探针是有墨的**——所以"先看探针有没有墨"这条判据抓不住它。
# 正常字体三个码位都渲成 .notdef（同一个遮罩）；被映射的那个会不一样。
# 取多数票：三个里有两个相同 → 那个就是 .notdef；三个互不相同 → **判不了**，不猜。
_NOTDEF_CHARS = ("\ue000", "\ue001", "\uf8ff")
# 哨兵字取自卡片真的会画出来的字符。**口径必须写全，因为这个数随口径变**：`cards/` + `render/`
# 的字符串字面量、排 docstring、排空白、排探测器自己的哨兵 `U+E000` —— 在 `origin/main` 上是
# **834 个不同字符**（同一个扫描器不排 docstring 则是 911）。上界链上的数字离开定义就没法接。
# 三类独立计数：某一类缺就说那一类，不因为"整体看着还行"把它吞掉。
#
# 第四类「符号」原先刻意不收，理由是「收了就是一条永远响、又永远没法照办的警告——没有一支候选
# 字体同时有中文和 `✗`」。**那个理由绑在具体哪一支字体上，换一支就失效**：2026-09-30 维护者装了
# `/home/cumora/fonts/DroidSansFallbackFull.ttf`（sha256 97320619…，4529044 字节），它同时有中文和
# `✔✗✘✓×`，只缺 `⟺`（`⟺` 只活在 docstring 里、永远画不到图上，不进语料）。⇒ 在这一支上，符号类
# 的警告是**能照办的**：换掉它就消掉。
#
# 但「某类缺了就报」在**没有任何候选覆盖它**时仍然会变成噪音。所以判据不变、覆盖面变大之后，
# 由 `_warn_incomplete` 自己判该不该出声：**只有候选里还真有一支覆盖得更全，才劝人换**；
# 一支候选都没有那样东西时，改成陈述事实（谁缺什么），不给空话建议。
#
# 不收它就有一个具体代价（实测 2026-09-30）：Droid 97320619 与 Noto 2c76254f 在只比这三类时
# **同分 (1, 3)**，`max` 平局取 `_FONTS` 里靠前的——于是「选出覆盖更全的那支」这件事退化成
# **列表顺序**，而这两支真正的差别恰好就在符号类（Noto 缺 `✔✗✘`，实测 `_missing` → `✔✗✘✔`）。
_PROBES = (
    ("拉丁字母/数字/ASCII 标点", "Aaz09%(),.[]"),
    ("中文",                     "中枢线段买点背驰趋势"),
    ("全角标点",                 "、。《》「」（）"),
    # 从语料里取的（只在 cards/ + render/ 的**字符串字面量**、排 docstring、排探测器哨兵 U+E000），
    # 重算：见 README「字体覆盖」一节。手写会随语料漂，这串是现算的，28 个。
    ("符号/圈号/箭头",           "±·×–—“”…↑→↓↔≠≤≥①②③④⑤⑥⑦▲★✓✔✗✘"),
)
_PROBE_CACHE = {}


def _notdef_mask(f):
    """这支字体给"没有字形的码位"画的遮罩；**判不了返回 None**。

    多数票：三个私用区码位里若有两个遮罩相同，那个就是 .notdef（另有一个被映射了）；
    三个互不相同 → 这支字体的私用区被映射得不只一个，挑不出基准 → 判不了。
    """
    masks = [bytes(f.getmask(c)) for c in _NOTDEF_CHARS]    # ImagingCore 没有 .tobytes()
    counts = {}
    for m in masks:
        counts[m] = counts.get(m, 0) + 1
    for m, n in counts.items():
        if n >= 2:
            return m
    return None


def _missing(font_path, probe, size=16):
    """probe 里画不出来的字；字体加载失败则整串都算缺；**判不了返回 None**。

    None 和 "" 是两回事："" 是"查过，一个都不缺"，None 是"这一格查不了"。
    混起来就成了今晚反复栽的那个坑——查不了被读成没问题。
    """
    key = (font_path, probe, size)
    if key not in _PROBE_CACHE:
        try:
            f, notdef = _load(font_path, size)          # 字体对象按 (路径, 字号) 缓存，别每类重载
            if notdef is None:
                _PROBE_CACHE[key] = None
            else:
                _PROBE_CACHE[key] = "".join(c for c in probe if bytes(f.getmask(c)) == notdef)
        except Exception:
            _PROBE_CACHE[key] = probe                   # 加载不了就当它一个都画不出来，不猜
    return _PROBE_CACHE[key]


_FONT_CACHE = {}


def _load(font_path, size):
    """(字体对象, .notdef 遮罩或 None)，按 (路径, 字号) 缓存。

    **不加这层缓存的话，每一类探针都会重新 `truetype()` 一次**——4.5MB 的字体一次 20ms 上下，
    而 `config` 是每个 headless 工具都会 import 的：实测 import 从 6ms 涨到 64ms，其中大头就是
    同一支字体被加载 4 遍。缓存之后回到 20ms 量级。
    """
    key = (font_path, size)
    if key not in _FONT_CACHE:
        from PIL import ImageFont
        f = ImageFont.truetype(font_path, size)
        _FONT_CACHE[key] = (f, _notdef_mask(f))
    return _FONT_CACHE[key]


def _font_probe(font_path):
    """(判得了吗, [(类别名, 缺的字), …])。判不了时第二个元素无意义。"""
    gaps = []
    for name, probe in _PROBES:
        miss = _missing(font_path, probe)
        if miss is None:
            return False, []
        if miss:
            gaps.append((name, miss))
    return True, gaps


def _font_score(font_path):
    """排序用：先看判不判得了，再看覆盖了几个类。判不了排在任何判得了的字体后面。"""
    ok, gaps = _font_probe(font_path)
    return (1 if ok else 0, len(_PROBES) - len(gaps))


def _best_alternative(font_path, cands):
    """cands 里有没有真比 font_path 覆盖得更全的一支。**没有就别劝人换。**"""
    ok, gaps = _font_probe(font_path)
    for c in cands or ():
        if c == font_path:
            continue
        ok2, gaps2 = _font_probe(c)
        if ok2 and len(gaps2) < len(gaps):
            return c
    return None


def _warn_incomplete(font_path, why, cands=None):
    ok, gaps = _font_probe(font_path)
    if not ok:
        print("[字体] 警告（%s）：%s 的私用区码位被映射了，取不到可比的 .notdef，"
              "**覆盖查不了**——「查不了」不等于「覆盖好」，出图仍可能静默出方框；"
              "请用 CHANLUN_FONT 指定一支能验的字体。"
              % (why, os.path.basename(font_path)), file=sys.stderr)
    elif gaps:
        detail = "、".join("%s（%s）" % (n, m) for n, m in gaps)
        alt = _best_alternative(font_path, cands)
        if alt:
            tail = "换成 %s 能覆盖得更多。" % alt
        else:
            # 候选里没有一支覆盖得更全 —— 那就只陈述事实，不给一条照办不了的建议。
            tail = ("候选表（_FONTS，本机命中 %d 条）里没有一支覆盖得更全，"
                    "换字体解决不了这类缺字。" % (len(cands) if cands else 1))
        # 措辞的分寸（2026-09-30 实测，见 tools/verify_warn.py）：
        # `gaps` 报的是**探针类的代表字**，不是"本轮要画上去的全部字"——两者常常不是同一个集合
        # （探针表 28 个字里有 3 个已经不在语料里了）。拿一支删掉 `✔✗✘` 的字体实测：这行说
        # "会被画成方框"，而**同一支字体**上 `tools/fontcheck.py` 扫完 831 个会画上去的字符
        # 判 rc=0 —— 因为语料里根本没有那三个字，谁也画不到它们。
        # ⇒ 一律用**条件句**（画到才出方框），不说**陈述句**（本轮会出方框）：后者是代理量偏强。
        #   同时点明这是哪一份名单，免得和 fontcheck 那份混起来（同一个屏幕上两份名单指向不同的字）。
        print("[字体] 警告（%s）：%s 缺 %s —— 这是**探针类的代表字**，和 fontcheck 扫出来的"
              "那份名单（本轮要画的字）不是同一个集合；一旦有卡片画到它们，会静默变成方框"
              "（PIL 不报错、退出码也不会替你发现）。%s"
              % (why, os.path.basename(font_path), detail, tail), file=sys.stderr)


def _pick_font():
    """显式指定的照用（缺字只警告，不推翻人的选择）；否则取候选里覆盖类数最多的那支。"""
    env = os.environ.get("CHANLUN_FONT")
    if env:
        if not os.path.exists(env):
            raise FileNotFoundError("CHANLUN_FONT 指向的字体不存在：%s" % env)
        # 显式指定时，警告里要能说清「换哪一支更好」，所以把别的候选也带上（人指定了就不推翻）。
        others = [f for f in _FONTS if f and f != env and os.path.exists(f)]
        _warn_incomplete(env, "来自 CHANLUN_FONT", others)
        return env
    cands = [f for f in _FONTS if f and os.path.exists(f)]
    if not cands:
        return None
    # 取覆盖最全的，同分取靠前的（保留 _FONTS 的偏好顺序；max 遇平局取第一个）。
    # 为什么不是"按顺序取第一支过线的"：Linux 上 Droid 排第一但只覆盖 2/4，
    # 第一支过线的会把 Noto 挡在身后——那正是这次这个坑。
    #
    # 同分仍然只由列表顺序决定，这是既定行为、不是判据（2026-09-30 复核：只比三类时
    # Droid 97320619 与 Noto 2c76254f 同分 (1,3)，喂入顺序一换结论就反）。**要动的是
    # 「比几类」，不是偏好顺序**——收了符号类之后这两支不再同分（(1,4) vs (1,3)）。
    best = max(cands, key=_font_score)
    _warn_incomplete(best, "候选里没有一支覆盖完整", cands)
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
