#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性重组脚本：把散落一地的脚本拆成 core / render / cards / tools 四层。"""
import os, re

R = "/var/minis/workspace/chanlun_mag"
def rp(p): return os.path.join(R, p)
def rd(p): return open(rp(p), encoding="utf-8").read()
def wr(p, s):
    os.makedirs(os.path.dirname(rp(p)), exist_ok=True)
    open(rp(p), "w", encoding="utf-8").write(s)

BOOT = ('import os, sys\n'
        'sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n')

# ============ 1) 包标记 ============
wr("render/__init__.py", '# -*- coding: utf-8 -*-\n"""出图：公共图元 + 各类图表。"""\n')
wr("cards/__init__.py", '# -*- coding: utf-8 -*-\n"""概念卡脚本包。"""\n')
wr("core/__init__.py", rd("core/__init__.py"))

# ============ 2) concepts.py → cards/base.py + c03..c09 ============
src = rd("concepts.py").splitlines(keepends=True)
marks = [(i, m.group(1)) for i, l in enumerate(src)
         if (m := re.match(r"^# =+ (\d\d) ", l))]
header = "".join(src[:marks[0][0]])
secs = {}
for k, (i, no) in enumerate(marks):
    end = marks[k + 1][0] if k + 1 < len(marks) else next(
        i for i, l in enumerate(src) if l.startswith("# ===") and "合集" in l)
    secs[no] = "".join(src[i:end])

# base.py：把 Mini / dash / tri 交给 render.style，只保留卡片专用件
base = '''# -*- coding: utf-8 -*-
"""概念卡公共层：卡片页框、要点列表、简笔图元。

卡片脚本只负责「画什么」，字体 / 配色 / 坐标映射 / 虚线 / 三角
这些「怎么画」统一由 render.style 提供，不要在这里再复制一份。
"""
''' + BOOT + '''from render.style import *            # noqa: F401,F403

W, H = 1400, 1180          # 默认卡片尺寸；个别卡片用 set_size() 覆盖
OUT = "/var/minis/attachments/"

f_b, f_n, f_p, f_t = F(24), F(23), F(27), F(20)


def set_size(w, h):
    """覆盖卡片尺寸（head / foot 依赖这两个值）。"""
    global W, H
    W, H = w, h


def cs(m, X, Y, bars, w=16):
    """在 Mini 上画一组 K 线。"""
    candles(m.d, X, Y, bars, w=w)


def zig(m, pts, col=BL, w=5):
    """按像素坐标连折线。"""
    d = m.d
    for a, b in zip(pts, pts[1:]):
        d.line([a, b], fill=col, width=w)


def zigp(m, pts, col=BL, w=5):
    """pts 为 (x像素, 价格)，自动把价格映射成 y。"""
    d = m.d
    q = [(x, m.Y(p)) for x, p in pts]
    for a, b in zip(q, q[1:]):
        d.line([a, b], fill=col, width=w)
    return q


def dot(d, x, y, col, r=11, txt=""):
    d.ellipse([x - r, y - r, x + r, y + r], fill=BG, outline=col, width=4)
    if txt:
        tw = d.textlength(txt, font=f_b)
        d.text((x - tw / 2, y - 25), txt, font=f_b, fill=col)


def head(d, no, name, oneliner):
    """卡片页眉：编号 + 名称 + 一句话定义。"""
    d.text((56, 34), no, font=F(38), fill=(70, 78, 96))
    d.text((132, 24), name, font=F(58), fill=TX)
    d.text((136, 104), oneliner, font=F(28), fill=MU)
    d.line([56, 168, W - 56, 168], fill=LINE, width=2)


def foot(d, src, trap):
    """卡片页脚：原文出处 + 最易踩的坑。"""
    d.line([56, H - 150, W - 56, H - 150], fill=LINE, width=2)
    d.text((56, H - 136), "原文", font=F(22), fill=(96, 104, 122))
    d.text((132, H - 136), src, font=F(24), fill=(168, 176, 192))
    d.text((56, H - 96), "陷阱", font=F(22), fill=(96, 104, 122))
    d.text((132, H - 96), trap, font=F(24), fill=AM)


def points(d, items, y0=828):
    """页脚上方的要点列表（左侧彩色小标签 + 右侧说明）。"""
    bw = max(d.textlength(k, font=f_n) for k, _ in items) + 40
    vx = 56 + bw + 24
    for i, (k, v) in enumerate(items):
        yy = y0 + i * 62
        d.rounded_rectangle([56, yy + 2, 56 + bw, yy + 46], 10, fill=BL + (52,))
        tw = d.textlength(k, font=f_n)
        d.text((56 + (bw - tw) / 2, yy + 8), k, font=f_n, fill=(190, 210, 255))
        d.text((vx, yy + 9), v, font=f_p, fill=TX)


def newcard(no, name, oneliner, accent=BL):
    """开一张空卡片，返回 (image, draw)。"""
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im, "RGBA")
    head(d, no, name, oneliner)
    d.rounded_rectangle([56, 196, W - 56, 800], 20, fill=PANEL, outline=LINE, width=2)
    return im, d
'''
wr("cards/base.py", base)

NAMES = {"03": "c03_pen", "04": "c04_segment", "05": "c05_center",
         "06": "c06_trend", "07": "c07_level", "08": "c08_divergence",
         "09": "c09_buypoints"}
TITLES = {"03": "03 笔", "04": "04 线段", "05": "05 中枢", "06": "06 走势类型",
          "07": "07 级别", "08": "08 背驰", "09": "09 三类买卖点"}
for no, fn in NAMES.items():
    body = secs[no]
    if no == "08":      # 该段内定义了名为 bars 的小函数，改名避免与数据变量混淆
        body = body.replace("def bars(a, b, top):", "def macd_bars(a, b, top):")
        body = body.replace("bars(180, 340, 21)", "macd_bars(180, 340, 21)")
        body = body.replace("bars(400, 620, 3.2)", "macd_bars(400, 620, 3.2)")
        body = body.replace("bars(640, 760, 9)", "macd_bars(640, 760, 9)")
    wr("cards/%s.py" % fn,
       '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n"""概念卡 %s"""\n' % TITLES[no]
       + 'from cards.base import *\n\nset_size(1400, 1180)\n\n' + body)

# 合集脚本（原来藏在 concepts.py 末尾）
wr("cards/build_all.py", '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 cards/ 产出的全部概念卡竖向拼成一张长图。"""
import glob, os
from PIL import Image

W = 1400
files = sorted(glob.glob("/var/minis/attachments/c0*.png"))
ims = [Image.open(f) for f in files]
tot = Image.new("RGB", (W, sum(i.height for i in ims)), (16, 18, 24))
y = 0
for i in ims:
    tot.paste(i, (0, y)); y += i.height
tot.save("/var/minis/attachments/chanlun_cards_all.png")
print("合集", tot.size, len(files), "张")
''')

# ============ 3) card01 / card02 → cards/ ============
def strip_boilerplate(src_path, dst_path, anchor, size, title):
    s = rd(src_path)
    i = s.index('"""', s.index('"""') + 3) + 3        # 模块 docstring 结束
    j = s.index(anchor)                               # 第一处「本卡专有」的代码
    head_part = '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n"""概念卡 %s"""\n' % title
    boom = ('import os, sys\n'
            'sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n'
            'from cards.base import *\n\nset_size(%d, %d)\n\n' % size)
    wr(dst_path, head_part + boom + s[j:])

strip_boilerplate("card01.py", "cards/c01_containment.py", "def cell(", (1400, 2040), "01 包含处理")
strip_boilerplate("card02.py", "cards/c02_fractal.py", "def column(", (1400, 1600), "02 分型")

# ============ 4) cards.py → 两张框架卡 ============
src2 = rd("cards.py")
cut = src2.index("# ============================================================ 卡片二")
head2 = '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n'
boot2 = BOOT + 'from render.style import *\n\nf_t, f_s, f_b, f_m, f_n = F(50), F(30), F(34), F(27), F(24)\n\n'
p1 = src2[:cut].replace(
    '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n"""两张卡片：① 共识-分歧-证实模型  ② 级别与递归"""\n'
    'from PIL import Image, ImageDraw, ImageFont\n\n'
    'FT = "/usr/share/fonts/droid-nonlatin/DroidSansFallbackFull.ttf"\n'
    'F = lambda s: ImageFont.truetype(FT, s)\n\n'
    'BG = (16, 18, 24); CARD = (26, 29, 38); LINE = (52, 57, 70)\n'
    'TX = (236, 239, 246); MU = (146, 154, 172)\n'
    'BL = (86, 142, 255); GR = (0, 205, 125); RD = (255, 86, 86); AM = (255, 190, 60)\n\n',
    '"""框架卡一：共识 → 分歧 → 证实 / 证伪（机会模型）"""\n' + boot2)
wr("cards/model_dissent.py", head2 + p1)
p2 = '"""框架卡二：级别与递归（一条规则定级别）"""\n' + boot2 + src2[cut:]
wr("cards/level_recursion.py", head2 + p2)

# ============ 5) 图表脚本 ============
s = rd("chan2.py")
s = s.replace('''import json, datetime, sys
sys.path.insert(0, "/var/minis/workspace/chanlun_mag")
from chan import merge, fractals, build_pens, zhongshu, F, BG, CARD, LINE, TX, MU, BL, GR, RD, AM
from PIL import Image, ImageDraw
''', BOOT + '''import json, datetime
from PIL import Image, ImageDraw
from render.style import *
from core.kline import standardize as merge, fractals
from core.pen import build_pens
from core.center import find_centers as zhongshu
from config import data, out
''')
s = s.replace('"""双级别对照卡：4H 全景 / 30m 全景 / 30m 放大（嵌套演示）+ 结论"""',
              '"""双级别对照图：4H 全景 / 30m 全景 / 30m 放大（级别嵌套演示）+ 结论"""')
s = s.replace('json.load(open("/var/minis/workspace/chanlun_mag/k4h.json"))', 'json.load(open(data("aaplusdt_4h.json")))')
s = s.replace('json.load(open("/var/minis/workspace/chanlun_mag/k30m.json"))', 'json.load(open(data("aaplusdt_30m.json")))')
s = s.replace('im.save("/var/minis/attachments/chanlun_2levels.png")', 'im.save(out("chanlun_2levels.png"))')
wr("render/chart_levels.py", s)

for src_f, dst_f, title in (("annotate.py", "render/chart_annotate.py", "在用户 TradingView 截图上标注：笔编号、中枢 ZG/ZD、延伸虚线段"),
                            ("annotate2.py", "render/chart_signals.py", "在用户截图上标注一/二/三类买点（对每个中枢的回试点做 ZG 判定）")):
    t = rd(src_f)
    t = t.replace('from PIL import Image, ImageDraw, ImageFont',
                  'import os, sys\nsys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\nfrom PIL import Image, ImageDraw, ImageFont')
    t = re.sub(r'^"""[\s\S]*?"""', '"""%s"""' % title, t, count=1)
    wr(dst_f, t)

s = rd("fetch.py")
s = s.replace('from PIL import Image', 'from PIL import Image') if 'from PIL' in s else s
s = s.replace('json.dump(data, open("/var/minis/workspace/chanlun_mag/" + fn, "w"))',
              'json.dump(data, open(os.path.join(DATA, fn), "w"))')
s = s.replace('import json, time, urllib.request, os',
              'import json, time, urllib.request, os, sys\nsys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\nfrom config import DATA')
s = s.replace('for iv, fn in (("4h", "k4h.json"), ("30m", "k30m.json")):',
              'for iv, fn in (("4h", "aaplusdt_4h.json"), ("30m", "aaplusdt_30m.json")):')
wr("tools/fetch_klines.py", s)

# ============ 6) 删除旧文件 ============
for f in ("concepts.py", "cards.py", "card01.py", "card02.py", "chan.py", "chan2.py",
          "annotate.py", "annotate2.py", "fetch.py", "verts.json", "verts2.json"):
    if os.path.exists(rp(f)):
        os.remove(rp(f))
print("重组完成")
