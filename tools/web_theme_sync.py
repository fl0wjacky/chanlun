#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""尺：前端（web/theme.js）画的颜色和线宽，跟 Python（render/style.py）和 TradingView（chanlun.pine）**是不是同一套**。

为什么要它：卡面写的是「配色、虚实规则、价签跟现在 Python 出图 / TradingView 脚本一致」——
「一致」如果只靠人眼比截图，那它就是一句承诺，不是判据。前端一旦自己发明一个色（哪怕只差 3%），
两张图并排就会露馅，而那时已经推上去了。这把尺把「一致」变成一条能跑的断言。

查五样：
  ① CHART —— 笔/线段/四层框/价签/买卖点的色与线宽、填充不透明度（对 render/style.py 的 CHART）
  ② PAGE  —— 页面底色与四级文字色（对 style.BG/CARD/PANEL/LINE/TX/MU/DIM）
  ③ CANDLE —— 阴阳线与「未收盘」的琥珀（对 style.UP/DN/AM）
  ④ WIDTH —— 线宽对 **chanlun.pine 的输入默认值**（前端线宽跟 TradingView 走，不是按 17592 px 的位图等比缩）
  ⑤ CSS   —— style.css 里 `:root` 那几个兜底色值也得跟 theme.js 一样，**且 :root 之外一个色都不许写**
             （踩过：`.badge.live` 里写死过 `#ffbc3c`，而 style.AM 是 `#ffbe3c` —— 差 2，肉眼和这把尺
              当时都看不见，因为尺只读 theme.js。现在 CSS 里再冒出裸色值当场变红。）
  另加一条：vendor 里那个 js 的 sha256 要跟 VERSION.txt 里记的对得上（改了半个字节就跑不绿）。

用法：
    python3 tools/web_theme_sync.py            # 全绿 rc=0；任何一格对不上 rc=1 并逐格印出差在哪
    python3 tools/web_theme_sync.py --selftest # 探针：故意把一个色改错，尺子必须变红（证明它真会红）
"""
import argparse
import hashlib
import os
import re
import sys
import tempfile

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME = os.path.join(R, "web/theme.js")
CSS = os.path.join(R, "web/style.css")
VENDOR = os.path.join(R, "web/vendor/lightweight-charts")

GREEN, RED, DIM = "\033[32m", "\033[31m", "\033[2m"
if not sys.stdout.isatty():
    GREEN = RED = DIM = ""


def blocks(src):
    """theme.js 里的 `export const NAME = { … };` → {NAME: {key: 原始值字符串}}"""
    out = {}
    for m in re.finditer(r"export const (\w+) = \{(.*?)\n\};", src, re.S):
        name, body = m.group(1), m.group(2)
        kv = {}
        for line in body.split("\n"):
            mm = re.match(r"\s*([A-Za-z_]\w*):\s*([^,]+?),\s*(?://.*)?$", line)
            if mm:
                kv[mm.group(1)] = mm.group(2).strip()
        out[name] = kv
    return out


def hexv(t):
    """Python 的 (r, g, b) 元组 → '#rrggbb'（前端写的是小写十六进制）"""
    return "#%02x%02x%02x" % tuple(t)


def js_hex(v):
    return v.strip().strip("'\"").lower()


def js_int(v):
    return v.strip()


def mix(a, b, k):
    """app.js 里那个 mix(a,b,k) = k·a + (1−k)·b —— 徽标边框这类「同色压到底色上」的值由它算。
    这里照抄一遍是为了能**核**：两个语言各写一遍同一个公式，只要有一边改动，这把尺就会说话。
    （+0.5 取整是照 JS 的 Math.round 舍入方向；Python 的 round() 是银行家舍入，半边会差 1。）"""
    ra, rb = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(c * k + d * (1 - k) + 0.5) for c, d in zip(ra, rb))


def css_root(src):
    """style.css 的 `:root { --k: #rrggbb; … }` → {k: '#rrggbb'}；只收色值（--font 那种不管）"""
    m = re.search(r":root\s*\{(.*?)\}", src, re.S)
    if not m:
        return None
    out = {}
    for k, v in re.findall(r"--([\w-]+)\s*:\s*([^;]+);", m.group(1)):
        v = v.strip()
        if re.fullmatch(r"#[0-9a-fA-F]{6}", v):
            out[k] = v.lower()
    return out


def check_css(b, bad, css_path):
    """⑤ style.css：兜底色值必须跟 theme.js 相同；:root 之外不许出现裸色值。

    兜底值本身是有用的（JS 没跑起来时不至于白屏），但它**同时**是第二处写色的地方 ——
    所以它必须被核。:root 之外一个都不许有：那是「有人在规则里顺手写死一个色」的位置，
    也就是上次那个 `#ffbc3c` 藏身的地方。
    """
    src = open(css_path, encoding="utf-8").read()
    root = css_root(src)
    if root is None:
        bad.append(("CSS.:root", "（找不到）", "?", "style.css 里没有 :root 兜底块（判据失效，别当通过）"))
        return
    for blk in ("PAGE",):
        for k in b.get(blk, {}):
            if k in root and b[blk].get(k):
                if root[k] != js_hex(b[blk][k]):
                    bad.append((f"CSS.{k}", root[k], js_hex(b[blk][k]),
                                f"style.css 的兜底值跟 theme.js {blk}.{k} 不是同一个色"))
    # 由 app.js 现算的三个（值也抄在 :root 里当兜底）—— 公式一致才算一致
    want = {"am": js_hex(b.get("CANDLE", {}).get("open", "#000")),
            "rd": js_hex(b.get("CHART", {}).get("sell", "#000"))}
    if want["am"] != "#000" and want["rd"] != "#000":
        bg = js_hex(b.get("PAGE", {}).get("bg", "#000"))
        tx = js_hex(b.get("PAGE", {}).get("tx", "#000"))
        pn = js_hex(b.get("PAGE", {}).get("panel", "#000"))
        for k, exp in (("am", want["am"]), ("rd", want["rd"]),
                       ("am-line", mix(want["am"], bg, 0.26)), ("rd-line", mix(want["rd"], bg, 0.26)),
                       ("panel-hi", mix(tx, pn, 0.05))):
            if k not in root:
                bad.append((f"CSS.{k}", "（缺）", exp, f"app.js 会灌 --{k}，:root 里该有同一个值当兜底"))
            elif root[k] != exp:
                bad.append((f"CSS.{k}", root[k], exp, "跟 app.js 现算的值对不上（公式或取值动了）"))
    # :root 之外一个裸色值都不许有
    body = src.replace(re.search(r":root\s*\{.*?\}", src, re.S).group(0), "")
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)      # ★ 注释里的色值不算色值（说明里就得能写 rgb(...) 举例）
    # ★ 只认 `#hex` 是不够的：`rgb(0 0 0 / .35)` 这种写法当时**整条溜过去**（2026-10-04 往左加载那支的
    #   `.more` 阴影就是这么写进去的，尺子是绿的 —— 尺子量的判据是「有没有裸色值」，认的却只有十六进制）。
    #   现在两种都认。命名色只列**没有歧义**的那几个，两头都加 `(?<![-\w]) / (?![-\w])`：
    #   `white-space: nowrap` 里的那个 white 不是色值（踩过），而 `transparent` / `currentColor` 合法，
    #   遮罩那条就靠 transparent —— 别把它们算进来。
    NAKED = re.compile(r"#[0-9a-fA-F]{3,8}\b"
                       r"|(?<![-\w])(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\s*\("
                       r"|(?<![-\w])(?:white|black|silver|gray|grey|maroon|red|purple|fuchsia|green|lime"
                       r"|olive|yellow|navy|blue|teal|aqua|orange|pink|brown|gold|cyan|magenta|beige|ivory)(?![-\w])",
                       re.I)
    for n, line in enumerate(body.split("\n"), 1):
        for h in NAKED.findall(line):
            bad.append((f"CSS:裸色值", h, "var(--…)", "style.css 里 :root 之外不许写死颜色（出处只有 theme.js）"))


def check(theme_path, verbose=True, css_path=CSS):
    """→ [(键, 前端, 期望, 说明)]；空表＝全对得上"""
    src = open(theme_path, encoding="utf-8").read()
    b = blocks(src)
    sys.path.insert(0, R)
    from render import style as S                                    # noqa: E402
    pine = open(os.path.join(R, "tradingview/chanlun.pine"), encoding="utf-8").read()
    bad = []

    def col(blk, key, want, why):
        got = b.get(blk, {}).get(key)
        if got is None:
            bad.append((f"{blk}.{key}", "（缺）", want, why))
        elif js_hex(got) != want.lower():
            bad.append((f"{blk}.{key}", js_hex(got), want.lower(), why))

    def num(blk, key, want, why):
        got = b.get(blk, {}).get(key)
        if got is None or js_int(got) != str(want):
            bad.append((f"{blk}.{key}", "（缺）" if got is None else js_int(got), str(want), why))

    # ① CHART
    for k in ("pen", "seg", "up_pen", "up_seg", "buy", "sell", "tag_ink"):
        col("CHART", k, hexv(S.CHART[k]), "render/style.py CHART.%s" % k)
    for k in ("pc_w", "sc_w", "pc_fill", "sc_fill", "up_fill", "tag_fill"):
        num("CHART", k, S.CHART[k], "render/style.py CHART.%s" % k)
    # ② PAGE
    for k, v in (("bg", "BG"), ("card", "CARD"), ("panel", "PANEL"), ("line", "LINE"),
                 ("tx", "TX"), ("mu", "MU"), ("dim", "DIM")):
        col("PAGE", k, hexv(getattr(S, v)), "render/style.py %s" % v)
    # ③ CANDLE
    for k, v in (("up", "UP"), ("dn", "DN"), ("open", "AM")):
        col("CANDLE", k, hexv(getattr(S, v)), "render/style.py %s" % v)
    # ④ WIDTH ← TradingView 的输入默认值与调用点（pine 改了这几处，前端就得跟着改）
    for key, var in (("pen", "penW"), ("seg", "segW")):
        m = re.search(r"^%s\s*=\s*input\.int\((\d+)" % var, pine, re.M)
        if not m:
            bad.append((f"WIDTH.{key}", "—", "?", f"chanlun.pine 里找不到 {var} 的默认值（判据本身失效，别当通过）"))
        else:
            num("WIDTH", key, int(m.group(1)), f"chanlun.pine {var} 的默认值")
    # 框线宽：pine 在调用点直接给字面量（类中枢 penCol 那行是 1、线段中枢 segCol 那行是 2）
    for key, marker in (("pc", "penCol"), ("sc", "segCol")):
        m = re.search(r"drawCenter\(z, xc\(base \+ a\), xc\(base \+ b\), %s, (\d+)," % marker, pine)
        if not m:
            bad.append((f"WIDTH.{key}", "—", "?", f"chanlun.pine 里找不到 drawCenter(…, {marker}, ?) 这一行（判据失效）"))
        else:
            num("WIDTH", key, int(m.group(1)), f"chanlun.pine drawCenter(…, {marker}, ?) 的框线宽")

    # 买卖点几何：跟 render/full_common.py 的 draw_signals 对（找不到锚点＝判据失效）
    for key, tier in (("penSize", "pen"), ("segSize", "seg")):
        m = re.search(r'\("%s",\s*C\["sig_%s"\],\s*(\d+)' % (tier, tier), open(
            os.path.join(R, "render/full_common.py"), encoding="utf-8").read())
        if not m:
            bad.append((f"SIG.{key}", "—", "?", "full_common.draw_signals 里找不到该层的三角尺寸"))
        else:
            num("SIG", key, int(m.group(1)), "render/full_common.py draw_signals 的 %s 层尺寸" % tier)

    # ⑤ style.css 的兜底色值 + :root 之外不许有裸色值
    check_css(b, bad, css_path)

    # vendor 的指纹
    ver = open(os.path.join(VENDOR, "VERSION.txt"), encoding="utf-8").read()
    m = re.search(r"sha256[：:]\s*([0-9a-f]{64})", ver)
    js = os.path.join(VENDOR, "lightweight-charts.standalone.production.js")
    got = hashlib.sha256(open(js, "rb").read()).hexdigest()
    if not m:
        bad.append(("vendor.sha256", got[:12], "（VERSION.txt 里没记）", "vendor 的指纹没记，等于没钉"))
    elif m.group(1) != got:
        bad.append(("vendor.sha256", got[:12], m.group(1)[:12], "vendor 里的 js 跟 VERSION.txt 记的不是同一份"))

    if verbose:
        for k, got, want, why in bad:
            print(f"{RED}✗{DIM} {k:<18} 前端 {got}  期望 {want}   ← {why}")
    return bad


def selftest():
    """探针：把一个色改错、把线宽改错，尺子都必须红 —— 否则它只是一段不会红的代码。
    ⑤ 的两格探针单独打（要改的是 style.css，不是 theme.js）。"""
    src = open(THEME, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    cases = [("theme: pen 色改错", THEME, src, "pen: '#7a89a6'", "pen: '#7a89a7'"),
             ("theme: 笔线宽改错", THEME, src, "pen: 1,", "pen: 2,"),
             ("theme: 页面底色改错", THEME, src, "bg: '#101218'", "bg: '#101219'"),
             ("theme: 类中枢框线宽改错", THEME, src, "pc: 1,", "pc: 3,"),
             ("css: 兜底底色改错", CSS, css, "--bg: #101218;", "--bg: #101219;"),
             ("css: 徽标琥珀改错（差 2 那种）", CSS, css, "--am: #ffbe3c;", "--am: #ffbc3c;"),
             ("css: 在规则里写死一个色", CSS, css, "background: var(--panel-hi); }",
              "background: #1c2029; }"),
             # ★ 这一格钉的是「尺子认不认得另一种写法」：十六进制那一格早就红了，
             #   而 rgb()/hsl() 写成一样是裸色值，却曾经整条溜过去（我自己就这么写进去过）。
             ("css: 裸色值换个写法（rgb()）", CSS, css, ".foot .meta { color: var(--mu); }",
              ".foot .meta { color: rgba(142, 150, 168, .9); }")]
    ok = True
    for name, path, base, a, z in cases:
        with tempfile.NamedTemporaryFile("w", suffix=os.path.splitext(path)[1],
                                         delete=False, encoding="utf-8") as f:
            f.write(base.replace(a, z))
            p = f.name
        try:
            kw = {"theme_path": p} if path == THEME else {"theme_path": THEME, "css_path": p}
            bad = check(verbose=False, **kw)
        finally:
            os.unlink(p)
        hit = bool(bad)
        ok &= hit
        print("%s 探针「%s」：%s" % ("✓" if hit else "✗", name,
                                    "变红（%s）" % bad[0][0] if hit else "**没红** —— 这把尺对这一格是瞎的"))
    print("%s 自检：%d/%d 格探针都能变红" % ("✓" if ok else "✗", sum(1 for _ in cases) if ok else 0, len(cases)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--theme", default=THEME)
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(selftest())
    bad = check(a.theme)
    if bad:
        print("%s 前端配色/线宽与 Python + TradingView 有 %d 处对不上" % (RED + "✗", len(bad)))
        raise SystemExit(1)
    n = len(blocks(open(a.theme, encoding="utf-8").read()))
    print("%s 前端配色/线宽与 render/style.py ＋ chanlun.pine 逐格相同（%d 组常量 · vendor sha 吻合）" % (GREEN + "✓", n))


if __name__ == "__main__":
    main()
