# -*- coding: utf-8 -*-
"""全量图共用的画法（ZEC 分面板版 / 顺滑版 / 概览，BTC 等任意标的的顺滑版）：结构层、标签、图例、刻度。

约定：未完成的笔 / 线段一律虚线；中枢框按规则 B（2026-10-02 小栋定，见 draw_layers.box_split）——
仍在延续的中枢拆两截（前三笔那截实线、延续那截虚线），已结束的整框实线，
前三笔里夹着没走完的那根则整框虚线。
标签（中枢区间、价格刻度）一律最后画、带底色、互相避让 —— 免得被 K 线和笔压住。
"""
from render.style import *


def draw_layers(g, r, X, Y, keep=lambda a, b: True, bar_w=2):
    """在画布 g 上画：类中枢（笔构成，淡）→ 线段中枢 → K 线 → 笔 → 线段。

    X(i) / Y(p)：K 线下标、价格 → 像素（X 给的是这根 K 线的中心）；
    keep(a, b)：下标区间 [a, b] 要不要画（分面板时筛本月）；bar_w：每根 K 线占的像素宽。
    返回标签请求 [((x, y), 文本) 或 ((x, y), 文本, 颜色)]，交给 draw_labels 最后画：
    线段中枢的区间，以及满 9 段中枢的「↑高一级」标记（第 33 课，引擎 z["up"]；满 27 段标「↑高两级」）。
    """
    bars, pens, segs = r["bars"], r["pens"], r["segs"]
    done = [s for s in segs if not s.get("live")]     # 线段中枢的序号指向「已完成线段」
    labels = []
    C = CHART
    lighter = lambda c: tuple(min(255, v + 40) for v in c)

    def frame(box, col, w, fill, xm, solid):
        """画一个框。xm 为 None ⇒ 整框一个样式（solid 定实/虚）；否则在 xm 处拆两截，左实右虚。

        ★ 拆两截是 2026-10-02 小栋定的新规则（分支 agent/iris/render-style-A），取代旧的
        「延续中的整框虚线」：前三笔那截实线、延续那截虚线。填充整块只铺一次，免得两截各铺
        一遍在分界处叠出一条深缝。
        """
        x0, y0, x1, y1 = [int(v) for v in box]
        if fill:
            g.rectangle([x0, y0, x1, y1], fill=col + (fill,))
        if xm is not None and x0 < int(xm) < x1:
            m = int(xm)
            edges = [((x0, y0), (m, y0), True), ((x0, y1), (m, y1), True), ((x0, y0), (x0, y1), True),
                     ((m, y0), (x1, y0), False), ((m, y1), (x1, y1), False), ((x1, y0), (x1, y1), False)]
        else:
            edges = [((x0, y0), (x1, y0), solid), ((x0, y1), (x1, y1), solid),
                     ((x0, y0), (x0, y1), solid), ((x1, y0), (x1, y1), solid)]
        for a, b, so in edges:
            if so:
                g.line([a, b], fill=col + (235,), width=w)
            else:
                dashed_line(g, a, b, col, width=w, dash_len=16, gap=10)

    def box_split(z, host, unfinished_j):
        """→ (分界像素 x 或 None, 整框是否实线)。

        规则 B（小栋 2026-10-02T06:21Z 定，见卡面）三档，按顺序判：
          ① 前三笔（线段中枢＝前三条线段）里夹着「还没走完」的那一员 ⇒ **整框虚线**，等它走完再转实线；
          ② 中枢**已结束**（not live）⇒ **整框实线** —— 上下沿早就定死了，延续那截不用再标虚线；
          ③ 中枢**仍在延续**（live）⇒ 前三那截实线、延续那截虚线。
        所以「拆两截」**只在 live 的中枢上看得见**：一个数据集里没有 live 中枢，就一条虚线都不会出
        （zec15 就是这种，142 个类中枢 + 19 个线段中枢全是 live=False ⇒ 规则 B 在它上面画不出差别）。
        框短到装不下那个分界时，退回整框一个样式。

        unfinished_j：host 里「还没走完」的那个成员下标，None ＝ host 里没有这一员。
        两层的成员不是同一个东西，别混：笔层是**最后一根笔**（终点还会被更极端的分型替换，
        见下面画笔那段的约定）；线段层是**还没完成的那条线段** —— 而线段中枢只由已完成线段算，
        那条 live 段根本不进 done，所以线段层传 None，这一支不触发。
        """
        j0, last = z["PI0"], len(host) - 1
        if unfinished_j is not None and j0 <= unfinished_j < min(j0 + 3, len(host)):
            return None, False                        # ① 前三里夹着没走完的 ⇒ 整框虚线
        if not z["live"]:
            return None, True                         # ② 中枢已结束 ⇒ 整框实线
        return X(host[min(j0 + 2, last)]["i1"]), True  # ③ 仍在延续 ⇒ 拆两截，前三实线、延续虚线

    # ★ 价签先塞进哪张表 —— 决定**谁先占位**。`draw_labels` 的避让是「先到先得」：先放进
    #   `placed` 的那一个占住原位，后来的重叠了才往上挪。类中枢一多（zec15 那份有 142 个），
    #   要是它们先进表，就会把线段中枢的价签挤到上面去 —— 2026-10-02 小栋的原话是
    #   「别把线段中枢的价签挤掉」。他说的虽然是 TradingView 的标签配额，同一条优先次序在
    #   这边的避让上一样成立，所以**类中枢（含它升上去的）的价签攒着，两个循环跑完再进表**。
    sink = labels

    def tag(x, y, text, col):
        """挂一个中枢价签：`col` 的**实底 + 黑字**，放在 (x, y) 上方一行。进 `sink` 那张表。

        ★ 颜色**跟着框走**：谁的框用什么色，它的标签就用那个色（2026-10-02 小栋：
          「每一个中枢左上角都标 [ZD, ZG]，颜色跟框一样」）。
        ★★ 样式本身在 2026-10-02 下半天改过一次口：原来是「30% 同色底 + 白字」，那是**只按深色底
          挑的** —— 小栋看的是**白底**图，30% 的淡底压在白底上几乎还是白，白字对比度只有 1.33~1.45:1。
          现在统一成「**实底 + 黑字**」：底不透明 ⇒ 读不读得清与图底色无关，六色 × 两底全部过 AA。
          数字在 notes/theme-contrast.py，`style.py` 的 `tag_fill` / `tag_ink` 是取值处。
          （上午那把 notes/pricetag-contrast.py 是从成图上量旧写法的那一版，已标注过期，别拿它复核这一版。）
        """
        sink.append(((max(x, 0) + 8, y - 36), text, C.get("tag_ink", BLACK),
                     col + (C.get("tag_fill", 255),)))

    def up_box(box, z, w, col):
        """高一级别框（满 9 段，第 33 课）：**两族分色**，线宽跟母框一样。

        2026-10-02 小栋定：① 类中枢升上去的、线段中枢升上去的**要分开**（浅紫 vs 品红，
        见 style.py 的 UP_PEN／UP_SEG）；② **不再加粗** —— 原来 `w + up_w × 级别`，现在
        直接就是母框的 `w`，级别靠颜色和标签文字区分（满 27 段的框只多一行「↑高两级」，
        框本身与满 9 段那个同色同宽 —— 线宽这条通道已经让给「不加粗」了）。

        ★ 它没跟着「拆两截」—— 高一级别的「前三笔」没有定义（它由子级别中枢构成，不是笔/线段）。
        """
        for u in z.get("up", []):
            ub = [box[0], Y(u["ZG"]), box[2], Y(u["ZD"])]
            frame(ub, col, w, C.get("up_fill", 0), None, not z["live"])
            tag(box[0], ub[1], "↑高%s级 [%g, %g]" % (
                "一两三四"[u["up"] - 1], round(u["ZD"], 2), round(u["ZG"], 2)), col)

    pen_tags = []                                     # 类中枢那族的价签：先攒着，最后进表（见上面的 `sink`）
    sink = pen_tags
    for z in r["centers"]:                            # 类中枢：与笔同色
        a, b = pens[z["PI0"]]["i0"], pens[z["PI1"]]["i1"]
        if keep(a, b):
            box = [X(a), Y(z["ZG"]), X(b), Y(z["ZD"])]
            xm, solid = box_split(z, pens, len(pens) - 1)     # 未走完的那根＝最后一根笔
            frame(box, C["pen"], C["pc_w"], C["pc_fill"], xm, solid)
            up_box(box, z, C["pc_w"], C["up_pen"])    # ↑ 类中枢升上去的：浅紫
            tag(box[0], box[1], "[%g, %g]" % (round(z["ZD"], 2), round(z["ZG"], 2)), C["pen"])
    sink = labels
    for z in r["seg_centers"]:                        # 线段中枢：与线段同色
        a, b = done[z["PI0"]]["i0"], done[z["PI1"]]["i1"]
        if keep(a, b):
            box = [X(a), Y(z["ZG"]), X(b), Y(z["ZD"])]
            xm, solid = box_split(z, done, None)              # 线段层没有「没走完」这一员，见 box_split
            frame(box, C["seg"], C["sc_w"], C["sc_fill"], xm, solid)
            up_box(box, z, C["sc_w"], C["up_seg"])    # ↑ 线段中枢升上去的：品红
            tag(box[0], box[1], "[%g, %g]" % (round(z["ZD"], 2), round(z["ZG"], 2)), C["seg"])
    labels.extend(pen_tags)                           # 线段中枢的价签已经占好位了，类中枢的补在后面
    for i, b in enumerate(bars):                      # K 线：影线 + 实体
        if keep(i, i):
            col = UP if b["c"] >= b["o"] else DN
            top, bot = Y(max(b["o"], b["c"])), Y(min(b["o"], b["c"]))
            if bar_w <= 2:                            # 2 像素：影线占左边 1 像素，实体铺满 2 像素
                x = X(i) - 1
                g.line([x, Y(b["h"]), x, Y(b["l"])], fill=col + (160,), width=1)
                g.rectangle([x, top, x + 1, bot], fill=col + (210,))
            else:                                     # 更宽：影线居中，实体两侧各留 1 像素缝
                x = X(i)
                g.line([x, Y(b["h"]), x, Y(b["l"])], fill=col + (200,), width=max(1, bar_w // 5))
                g.rectangle([x - bar_w / 2 + 1, top, x + bar_w / 2 - 1, max(bot, top + 1)], fill=col + (230,))
    for k, p in enumerate(pens):                      # 最后一笔未完成（终点还会被更极端的分型替换）→ 虚线
        if keep(p["i0"], p["i1"]):
            a, b = (X(p["i0"]), Y(p["p0"])), (X(p["i1"]), Y(p["p1"]))
            if k == len(pens) - 1:
                dashed_line(g, a, b, lighter(C["pen"]), width=C["pen_w"] + 1, dash_len=12, gap=8)
            else:
                g.line([a, b], fill=C["pen"] + (235,), width=C["pen_w"])
    for s in segs:                                    # 未完成（live）→ 虚线；端点：顶红、底绿
        if keep(s["i0"], s["i1"]):
            a, b = (X(s["i0"]), Y(s["p0"])), (X(s["i1"]), Y(s["p1"]))
            if s.get("live"):                         # 未完成段画到「迄今的极值」（向上段最高、向下段最低）——
                ext = s["hi"] if s["dir"] == "up" else s["lo"]    # 那才是它眼下可能的终点；之后的走势由笔表达
                k = max(j for j in range(s["PI0"], s["PI1"] + 1) if pens[j]["p1"] == ext)
                b = (X(pens[k]["i1"]), Y(ext))
            if s.get("live"):
                dashed_line(g, a, b, C["seg"], width=C["seg_w"], dash_len=26, gap=16)
            else:
                g.line([a, b], fill=C["seg"], width=C["seg_w"])
            up = s["dir"] == "up"
            for (x, y), col in ((a, GR if up else RD), (b, RD if up else GR)):
                g.ellipse([x - 9, y - 9, x + 9, y + 9], fill=BG, outline=col, width=4)
    return labels


def draw_signals(g, r, X, Y, keep=lambda a, b: True):
    """买卖点：在点位画一个小三角（买点朝上、在低点下方；卖点朝下、在高点上方），返回文字标签请求。

    线段中枢层用实心三角 + 大字；类中枢层用空心三角 + 「·笔」；待确认的加「?」、更淡（core/signals.py）。
    """
    from core.signals import signals
    C = CHART
    out = []
    for lv, on, sz, tag in (("pen", C["sig_pen"], 9, "·笔"), ("seg", C["sig_seg"], 15, "")):
        if not on:
            continue
        for s in signals(r, lv, C["sig_measure"]):
            if not keep(s["bar"], s["bar"]) or not (s["confirmed"] or C["sig_pending"]):
                continue
            buy = s["kind"].endswith("买")
            col = C["buy"] if buy else C["sell"]
            a = 255 if s["confirmed"] else 140
            x, y = X(s["bar"]), Y(s["price"])
            d = 1 if buy else -1                       # 买点画在下方，卖点画在上方
            tip, y0 = y + d * 6, y + d * (6 + 2 * sz)
            tri = [(x, tip), (x - sz, y0), (x + sz, y0)]
            if lv == "seg":
                g.polygon(tri, fill=col + (a,), outline=BG)
            else:
                g.polygon(tri, outline=col + (a,), width=2)
            txt = s["kind"] + ("(弱)" if s["weak"] else "") + tag + ("" if s["confirmed"] else "?")
            out.append(((x - sz, y0 + (8 if buy else -40 - sz)), txt, col if s["confirmed"] else tuple(int(v * .7) for v in col)))
    return out


def draw_labels(g, labels, font, col, placed=None):
    """带底色的标签，最后画；与已放下的框重叠就往上挪一行（最多 12 次）。

    标签元组两种形状：
        ((x, y), 文本)                 深底 + `col` 色的字（价格刻度这类）
        ((x, y), 文本, 文字色)         深底 + 指定的字色
        ((x, y), 文本, 文字色, 底色)   ★ 价签：自带底色，**字色也自带**
    ★ 价签（中枢区间、↑高N级）走第三种，两边同一条规矩。样式 2026-10-02 下半天改过口：
      原来第四项一出现就**硬把字色设成纯白**（对应 TradingView 的 `color.new(col, 70)` + 白字）——
      那是只按深色底挑的，白底上白字对淡底只有 1.33~1.45:1。现在统一「实底 + 黑字」，
      字色由调用方给（价签一律 `tag_ink`），这里**不再覆盖** —— 覆盖就是一个藏起来的假设。
      数字见 notes/theme-contrast.py。
    """
    placed = [] if placed is None else placed
    for lab in labels:
        (x, y), text = lab[0], lab[1]
        c = lab[2] if len(lab) > 2 else col
        bg = lab[3] if len(lab) > 3 else BG + (215,)
        tw = g.textlength(text, font=font)
        box = lambda yy: (x - 6, yy - 2, x + tw + 6, yy + font.size + 8)
        # ★ 挪几次：原来只挪 4 行（每行 = 字高 + 12 ≈ 36 px，共 144 px）。2026-10-02 给小栋的
        #   zec15 图实测：每一个中枢都挂价签之后标签从 21 个涨到 38 个，**4 行不够用了，
        #   有 2 对标签摞在一起**（挪 4 次上面 4 行也占满了，再挪就放弃 —— 放弃就重叠着画）。
        #   改成 12 行（432 px），并且**只在真的挪不动时才认输**：notes/label-overlap.py 量得到
        #   改前 0 对、改后 0 对。别把它调回小数字 —— 它不是一个审美参数，是避让的成功条件。
        for _ in range(12):
            bx = box(y)
            if not any(bx[0] < q[2] and q[0] < bx[2] and bx[1] < q[3] and q[1] < bx[3] for q in placed):
                break
            y -= font.size + 12
        g.rounded_rectangle(box(y), 6, fill=bg)
        g.text((x, y), text, font=font, fill=c)
        placed.append(box(y))
    return placed


def legend(d, x, y, font, wrap_x=None):
    """图例样例与实际画法一致：K 线红绿、笔 / 线段是线、中枢是框、未完成是虚线。

    线宽**直接取 `CHART`**（笔 2 / 段 5 / 类中枢框 2 / 线段中枢框 4），不再各写一个手抄的数字 ——
    2026-10-02 小栋「线段 3→2」这一改，图例要是还画着 7，图例就是唯一一处说假话的地方。

    `wrap_x` 给了就在**放不下下一项之前**换行（返回最后一项的右边界，语义跟不换行时一样）。
    加这个是因为这一行本来就已经装不下了：2900 宽的图上，图例原样排到 x=3286，
    最后那项「买卖点（…）」有 386 px 被画布切掉 —— 我量过 `out/zec15_duan.png` 的图例行，
    最右边的像素一直到 x=2899（画布最后一列）都还有墨。**是旧账**（这一行的项和字都没动过），
    但中枢价签这一改正要再往这行里塞东西，先把它收干净。
    """
    x0 = x

    def item(draw_sample, name, sw=84):
        """`sw` = 给样例留的宽度（样例比 84 宽就得自己说，不然字会贴上去）。"""
        nonlocal x, y
        if wrap_x is not None and x > x0 and x + sw + d.textlength(name, font=font) > wrap_x:
            x = x0
            y += font.size + 22
        draw_sample(x, y)
        d.text((x + sw, y - 14), name, font=font, fill=TX)
        x += sw + d.textlength(name, font=font) + 56
    item(lambda x0, y0: [d.rectangle([x0 + k * 14, y0 - 10 + (k % 2) * 6, x0 + k * 14 + 8, y0 + 6 + (k % 2) * 6],
                                     fill=(UP, DN)[k % 2]) for k in range(5)], "K线")
    C = CHART
    pc, sc = C["pen"], C["seg"]
    item(lambda x0, y0: d.line([x0, y0, x0 + 70, y0], fill=pc, width=C["pen_w"]), "笔")
    item(lambda x0, y0: d.rectangle([x0, y0 - 14, x0 + 70, y0 + 14], fill=pc + (C["pc_fill"],),
                                    outline=pc, width=C["pc_w"]), "类中枢（与笔同色）")
    item(lambda x0, y0: d.line([x0, y0, x0 + 70, y0], fill=sc, width=C["seg_w"]), "线段")
    item(lambda x0, y0: d.rectangle([x0, y0 - 14, x0 + 70, y0 + 14], fill=sc + (C["sc_fill"],),
                                    outline=sc, width=C["sc_w"]), "线段中枢（与线段同色）")
    item(lambda x0, y0: [d.rectangle([x0, y0 - 14, x0 + 34, y0 + 14], fill=C["up_pen"] + (C.get("up_fill", 0),),
                                     outline=C["up_pen"], width=C["pc_w"]),
                         d.rectangle([x0 + 40, y0 - 14, x0 + 74, y0 + 14], fill=C["up_seg"] + (C.get("up_fill", 0),),
                                     outline=C["up_seg"], width=C["sc_w"])],
         "高一级（满 9 段，第 33 课）：浅紫＝类中枢升 / 品红＝线段中枢升；框线跟母框一样粗，不另行加粗")
    item(lambda x0, y0: [d.rounded_rectangle([x0, y0 - 14, x0 + 122, y0 + 15], 6, fill=pc + (C["tag_fill"],)),
                         d.text((x0 + 10, y0 - 13), "[ZD, ZG]", font=font, fill=C["tag_ink"])],
         "价签（每个中枢都有，颜色跟框一样）：实底 + 黑字（白底/深底都读得清）", sw=168)
    item(lambda x0, y0: [d.line([x0, y0, x0 + 34, y0], fill=sc, width=C["seg_w"]),
                         dashed_line(d, (x0 + 34, y0), (x0 + 70, y0), sc, C["seg_w"], 22, 12)],
         "中枢框拆两截：前三笔实线 / 延续虚线")
    item(lambda x0, y0: [d.polygon([(x0 + 18, y0 - 12), (x0 + 6, y0 + 12), (x0 + 30, y0 + 12)], fill=C["buy"]),
                         d.polygon([(x0 + 52, y0 + 12), (x0 + 40, y0 - 12), (x0 + 64, y0 - 12)], fill=C["sell"])],
         "买卖点（线段中枢层；空心「·笔」= 类中枢层，「?」= 待确认）")
    return x


def price_ticks(pmin, pmax):
    """对数轴上的价格刻度：跨度大（≥3 倍）用 1/1.2/1.5/2/…×10^n；跨度小用线性整数间隔（约 10 条）。"""
    import math
    if pmax / pmin >= 3:
        steps = (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8)
        return [v * 10 ** k for k in range(-2, 8) for v in steps if pmin <= v * 10 ** k <= pmax]
    raw = (pmax - pmin) / 10
    e = 10 ** math.floor(math.log10(raw))
    step = next(s * e for s in (1, 2, 2.5, 5, 10) if s * e >= raw)
    return [k * step for k in range(math.ceil(pmin / step), math.floor(pmax / step) + 1)]
