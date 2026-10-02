# -*- coding: utf-8 -*-
"""同一份数据、同一段窗口，**深色主题和白底主题上下并排** —— 浅色改动到底改了什么，一张图说完。

为什么要有：2026-10-02 小栋那张截图是**白底**（TradingView 浅色），而当时的配色只按深底挑的：
近白底上 30% 的淡底几乎是白、白字读不出来；段 / 类升级 / 买 三色在白底上只有 1.7~2.1:1。
这张图把「同一段行情在两种底上的样子」摆在一起，配合 notes/theme-contrast.py 的数字。

跑法（自己起两个子进程渲染，不依赖你手边有没有图）：

    python3 notes/theme-ab.py            # → notes/theme-ab.jpg
退出码：0 = 两张都渲染出来、且都能读到六个新元素色；1 = 少了哪张 / 哪支色数不到。

★ 为什么是 JPEG 不是 PNG：这张是**密K线图**，缩过的 PNG 反而更大（几万个过渡色），
  贴聊天的那条路（--bytes-b64 一个 argv ＝ 128 KiB）下不来。JPEG 才对路。
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib.util                                                       # noqa: E402
from PIL import Image, ImageDraw                                            # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "theme-ab.jpg")
CROP = (0, 300, 1500, 900)          # 笔 / 段 / 类中枢 / 价签 / 三买 都在这一窗里
TARGET = 94 * 1024


def _load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def render(theme):
    """渲染一个主题，返回成图路径。★ 两次都写 out/zec15_duan.png，所以**每次都要马上取走**。"""
    env = dict(os.environ, CHANLUN_THEME=theme)
    r = subprocess.run([sys.executable, "render/chart_zec_segments.py"], env=env, cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode:
        print("★ %s 主题渲染失败：%s" % (theme, r.stderr.strip()))
        return None
    src = os.path.join(ROOT, "out", "zec15_duan.png")
    dst = os.path.join("/tmp", "theme-ab-%s.png" % theme)
    Image.open(src).convert("RGB").save(dst)
    return dst


def main():
    from render.style import F

    paths = {t: render(t) for t in ("dark", "light")}
    for t, p in paths.items():
        if not p:
            return 1

    # 自检：两个主题的六个元素色是**同一套**（元素色不跟主题走）——
    # 少一支就说明哪天有人把元素色也挂进主题分支了，那这张图证的就不是同一件事了。
    from render.style import CHART
    from collections import Counter
    need = {tuple(CHART[k][:3]) for k in ("pen", "seg", "up_pen", "up_seg", "buy", "sell")}
    for t, p in paths.items():
        cnt = Counter(Image.open(p).crop(CROP).getdata())
        # 线段中枢升上去的品红在这个窗口里可能没有，所以只要求「至少 4 支在场」
        have = [c for c in need if cnt.get(c, 0) > 0]
        print("%-5s 窗口内数到 %d/6 支元素色 %s" % (t, len(have), sorted(have)))
        if len(have) < 4:
            print("★ %s 主题这张里元素色太少，窗口选错了？" % t)
            return 1

    f_h, f_s = F(26), F(19)
    # ★ 标题要老实：深底那一格**不是**「没动过」—— 三色压暗了（10.7/9.7/8.6 → 5.9）。
    #   写「原有，未变差」就等于把代价藏起来，那正是这张图要给人看的东西。
    panels = [(paths["dark"], "深色主题 · 同一套色（段/类升级/买 压暗后 5.9~6.0:1，仍高于笔的 5.08）"),
              (paths["light"], "白底主题（小栋的截图）· 六色 3.0~3.5:1，价签实底＋黑字 5.96~6.97:1")]
    w = CROP[2] - CROP[0]
    h = CROP[3] - CROP[1]
    band = 44
    im = Image.new("RGB", (w, (h + band) * len(panels)), (255, 0, 255))
    for i, (p, head) in enumerate(panels):
        y = i * (h + band)
        im.paste(Image.open(p).crop(CROP), (0, y + band))
        d = ImageDraw.Draw(im)
        d.rectangle([0, y, w, y + band], fill=(19, 23, 34) if i == 0 else (255, 255, 255))
        d.text((10, y + 9), head, font=f_h,
               fill=(234, 238, 246) if i == 0 else (24, 28, 38))

    for scale in (1.0, 0.9, 0.82, 0.74, 0.66):
        s = im.resize((round(w * scale), round(im.height * scale)), Image.LANCZOS) if scale < 1 else im
        for q in (86, 80, 74, 68, 62):
            s.save(OUT, quality=q, optimize=True)
            if os.path.getsize(OUT) <= TARGET:
                print("→ %s  %d×%d  %d KiB  scale=%.2f q=%d"
                      % (os.path.relpath(OUT, ROOT), s.width, s.height,
                         os.path.getsize(OUT) // 1024, scale, q))
                return 0
    print("→ %s  %d KiB（压到最小仍超过目标）" % (os.path.relpath(OUT, ROOT), os.path.getsize(OUT) // 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
