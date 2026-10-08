#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文字落框（夹视口 + 避让）的一把尺（第五把，配 web_fmt_check.py / web_footer_check.py / web_theme_sync.py）。

**为什么单独立一把**：`fitBox()` 是价签和买卖点文字**共用**的那一份框守卫 —— 它一改，画面里
所有标签的落点都跟着动，而"动了多少"在截图里看不出来（几百个框，眼睛只看得到最挤的那几处）。
这条改动是 Nova 2026-10-03 拍的：⑦ 给买卖点文字补上实体深底之后，左上角「二卖」的框压住价签左半截
（墨盒实测相交 22.5×3.75px，画面上 `[1631.1,` 那半截被压暗），而那一簇已被视口顶边钉在 y=0
⇒ **只会往上挪**的避让在那儿一步都挪不动。补的是「往上挪不动就回头往下试」，
并且**往下也要夹视口下沿**（Atlas 提的：不夹就是把顶边那个问题原样挪到底边去）。

判据（一句话）：**框永远不出视口**（`0 ≤ y0` 且 `y1 ≤ H`）；**有空格子时不许压着别人**；
**横向一格都不许动**（锚点是那根 K 线，横着挪＝把标签从它的点上挪开）；**高不许变**（夹边是整框移，不是裁）。

怎么量：把 `fitBox()`（含它用的常量、判据小函数）从 `web/layers.js` 的标记里抠出来丢给 node，
在一组**造的**场景上逐条对账。场景里的数字不是编的 —— S4/S5/S6 用的是真机上量出来的那一簇
（左上角价签框、`二卖` 框的实测几何），见每条自己的注释。

第二只镜头（`tag()` 的**顺序**）：价签是「先夹右边界、再避让」还是反过来，`fitBox()` 自己看不出来 ——
它只知道自己被喂进来的框。所以另抠 `tag()` 一段，配一个**假的 ctx**（`measureText` 每字 8px、
`fillRect` 记下来）跑一格：自然框不压、夹完右边界才压的那种情形。顺序反了 ⇒ 推回来的框没有
复查碰撞 ⇒ 登记框压在别人身上 ⇒ 探针必须红（T1）。夹右边界是**几何**（贴到 W−2），
所以它属于「算框」这一段，得在避让**之前**（Atlas 2026-10-03 指出）。

★ 两条**照搬**来的语义，写在这儿免得下次当成 bug：
  ① 上下两条路都是「判 12 个候选行」（原位 ＋ 每格 19px）。第 12 次位移的结果**不再判** ——
     这跟 Python `draw_labels` 的 `for n in range(12)` 同构，S8 把这个边界钉住了。
     要改"12 到底是 12 还是 13"，上下两条一起改（别只改一条，两条不一致才是真问题）。
  ② 两头都挤不下时返回**往上那条的终点**（＝改之前的行为），不返回一个"更聪明"的位置：
     这种情况在真数据里没有，宁可退回已知行为也不要发明第三种落点。

跑法：
  python3 tools/web_fitbox_check.py            # 主跑：场景逐条对账
  python3 tools/web_fitbox_check.py --selftest # 探针：每格都得变红（尺子先证明自己会红）
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = os.path.join(ROOT, "web", "layers.js")
BEGIN = "// >>> FIT_BOX"
END = "// <<< FIT_BOX"
TBEGIN = "// >>> TAG_BOX"
TEND = "// <<< TAG_BOX"

NUDGE = 19          # 跟 layers.js 里的常量同一档：改那边这个探针就红，改这里没用
TAG_H = 15


def rows(n, x0=9, x1=42, h=TAG_H):
    """造 n 个**占满格**的框：第 k 格 = y [19k, 19k+h)。用来钉"往下试到第几格"的边界。"""
    return [[x0, NUDGE * k, x1, NUDGE * k + h] for k in range(n)]


# 场景：{名, H（视口高）, placed（已登记的框）, box（要落的框）, want（唯一正确答案）}
SCENARIOS = [
    {
        "name": "① 往上挪一格（原有行为，不许变）",
        "H": 400, "placed": [[100, 200, 200, 215]], "box": [100, 200, 200, 215],
        "want": [100, 200 - NUDGE, 200, 215 - NUDGE],
        "why": "跟已登记的框完全重合 ⇒ 往上挪一行。这是 2026-10-02 就在的行为，新加的两条都不许碰它。",
    },
    {
        "name": "② 上沿夹进视口（整框下压，高不变）",
        "H": 400, "placed": [], "box": [10, -12, 60, 3],
        "want": [10, 0, 60, 15],
        "why": "视口没有 Python 那 300px 上边距 ⇒ 最高的卖点本来就贴顶。夹，但不许改高。",
    },
    {
        "name": "③ 下沿夹进视口（整框上顶，高不变）",
        "H": 400, "placed": [], "box": [10, 392, 60, 407],
        "want": [10, 400 - TAG_H, 60, 400],
        "why": "跟②同一个原因的另一头（Atlas：往下也夹，不然就是把顶边的问题挪到底边）。",
    },
    {
        "name": "④ 顶上挪不动 ⇒ 回头往下试（那条发现本身）",
        "H": 400,
        # 实测几何（390×844 @3x、?symbol=ZECUSDT&tf=15m）：左上角价签框 ＋ 二卖框。
        # 价签墨盒 [9.25, 8.38, 93.95, 19.26] ⇒ 框（字左 +5 起）[4.25, 8.5, 98.95, 23.5]；
        # 二卖框 [9.5, 0, 42, 15]（被顶边钉在 0）。
        "placed": [[4.25, 8.5, 98.95, 23.5]],
        "box": [9.5, 0, 42, 15],
        "want": [9.5, 2 * NUDGE, 42, 2 * NUDGE + TAG_H],
        "why": "往上被顶边钉死 ⇒ 往下试：第 1 格还压在价签上（19–34 vs 8.5–23.5），第 2 格才空出来。",
    },
    {
        "name": "⑤ 往下也不许出视口（装不下的矮画布）",
        "H": 40, "placed": [[9, 8, 42, 23]], "box": [9.5, 0, 42, 15],
        "want": [9.5, 0, 42, 15],
        "why": "往下唯一的空格子在 38–53，可视口只有 40 高 ⇒ 不许挪过去。停在往上那条的终点"
                "（还压着，但**看得见** —— 出画布比重叠更糟）。※ 探针②③就是拿这条钉的。",
    },
    {
        "name": "⑥ 两头都挤不下 ⇒ 退回往上那条的终点",
        "H": 30, "placed": [[9, 0, 42, 15]], "box": [9.5, 0, 42, 15],
        "want": [9.5, 0, 42, 15],
        "why": "整张视口只装得下这一格 ⇒ 上下都无处可去。返回的必须还是「往上那条的结果」，"
                "不许发明第三种落点（这是「不比重叠更糟」的下限）。",
    },
    {
        "name": "⑦ 往下第 11 格够得着（候选行 = 原位 + 11 格）",
        "H": 400, "placed": rows(11), "box": [9.5, 0, 42, 15],
        "want": [9.5, 11 * NUDGE, 42, 11 * NUDGE + TAG_H],
        "why": "0–10 格都被占满、第 11 格空 ⇒ 必须挪到第 11 格（不能只试一两格就放弃）。",
    },
    {
        "name": "⑧ 第 12 格不再判（照搬 Python 的循环结构）",
        "H": 400, "placed": rows(12), "box": [9.5, 0, 42, 15],
        "want": [9.5, 0, 42, 15],
        "why": "0–11 格占满、第 12 格空：循环判满 12 个候选行就停，跟 Python `range(12)` 同构 ⇒"
                "退回终点。★ 这条是**照搬**来的边界，不是新规矩；要改就上下两条一起改。※ 探针④钉它。",
    },
]


def block(path=JS, begin=BEGIN, end=END):
    """把带标记的那一段从 layers.js 里抠出来。抠不到 ⇒ 报错，不许静默跳过。"""
    src = open(path, encoding="utf-8").read()
    a, b = src.find(begin), src.find(end)
    if a < 0 or b < 0 or b < a:
        raise SystemExit("✗ 在 %s 里找不到 %s / %s 标记 —— 抠不到被测量，尺子不猜" %
                         (os.path.relpath(path, ROOT), begin, end))
    return src[src.index("\n", a) + 1:b]


class Crash(Exception):
    """候选实现自己跑崩了 —— 那也是「对不上」。"""


def run(js, scenarios):
    """把抠出来的 JS 段丢给 node 跑，每个场景返回落完的框。"""
    if "function fitBox" not in js:
        raise SystemExit("✗ 抠出来的段里没有 `fitBox` 的定义 —— 标记范围被改动了")
    harness = js + """
const SC = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(SC.map((s) => fitBox(s.box, s.placed, s.H))));
"""
    payload = [{"box": s["box"], "placed": s["placed"], "H": s["H"]} for s in scenarios]
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(harness)
        path = f.name
    try:
        p = subprocess.run(["node", path, json.dumps(payload)], capture_output=True, text=True)
    finally:
        os.unlink(path)
    if p.returncode != 0:
        raise Crash(p.stderr.strip().splitlines()[0] if p.stderr.strip() else "rc=%d" % p.returncode)
    return json.loads(p.stdout)


def _r(v):
    return round(float(v), 3)


def check(js=None, verbose=True):
    """→ [(场景, 拿到, 为什么红)]；空表＝逐条都对。

    三样一起判：**落点**（逐坐标）、**横不动/高不变**、**不出视口** ——
    后两样是全局不变量（每个场景都判），探针里有两格就是专门撞它们的。"""
    js = block() if js is None else js
    try:
        got = run(js, SCENARIOS)
    except Crash as ex:
        if verbose:
            print("  ✗ 候选实现跑不动：%s" % ex)
        return [(SCENARIOS[0], None, "崩了：%s" % ex)]
    bad = []
    for sc, g in zip(SCENARIOS, got):
        why = []
        if not g or len(g) != 4:
            why.append("没返回一个框：%r" % (g,))
        else:
            if [_r(v) for v in g] != [_r(v) for v in sc["want"]]:
                why.append("落在 %s，要 %s" % ([_r(v) for v in g], [_r(v) for v in sc["want"]]))
            if _r(g[3] - g[1]) != _r(sc["box"][3] - sc["box"][1]):
                why.append("高变了：%g → %g" % (sc["box"][3] - sc["box"][1], g[3] - g[1]))
            if _r(g[0]) != _r(sc["box"][0]) or _r(g[2]) != _r(sc["box"][2]):
                why.append("横向动了：%g/%g → %g/%g" % (sc["box"][0], sc["box"][2], g[0], g[2]))
            if g[1] < -1e-9 or g[3] > sc["H"] + 1e-9:
                why.append("出了视口：y %g–%g，视口高 %g" % (g[1], g[3], sc["H"]))
        if why:
            bad.append((sc, g, "；".join(why)))
    if verbose:
        for sc, g, why in bad:
            print("  ✗ %s\n      %s" % (sc["name"], why))
    return bad


# ---- 第二只镜头：价签整条路（tag）—— 夹右边界必须在 fitBox **之前** ----
# 假 ctx：measureText 每字 8px、fillRect 记下来。tag() 只用到这几个面，够跑。
TAG_STUBS = """const FONT_SM = '11px X';
const CHART = { tag_fill: 1, tag_ink: '#000' };
const rgba = () => 'rgba';
"""
TAG_CALL = """
const S = JSON.parse(process.argv[2]);
const rects = [];
const ctx = {
  font: '', textAlign: '', textBaseline: '',
  measureText: (t) => ({ width: 8 * [...t].length }),
  fillRect: (x, y, w, h) => rects.push([x, y, x + w, y + h]),
  fillText: () => {},
};
const placed = S.placed.map((b) => b.slice());
tag(ctx, placed, S.x, S.y, S.text, 0, S.W, S.H);
process.stdout.write(JSON.stringify({ box: placed[placed.length - 1], rect: rects[0], placed: placed }));
"""

# 一格场景（数字是凑出来的，不是量的）：W=200 ⇒ 右边界 W−2=198。
# 自然框 [110, 0, 248, 15]（16 字 × 8px + 10 留白）**不压** left 那个已登记的框 [50, 0, 90, 15]；
# 夹到 198 之后变成 [60, 0, 198, 15]，横向就压上去了（x 60–198 vs 50–90）。
# ⇒ 顺序对了才会「夹完再避让」把这一压躲掉；顺序反了，推回来的框没人复查 ⇒ 直接压着。
TAG_SCENE = {
    "W": 200, "H": 400, "placed": [[50, 0, 90, 15]], "x": 110, "y": 15, "text": "价" * 16,
    "want": [60, NUDGE, 198, NUDGE + TAG_H],
    "why": "夹右边界是**几何**（贴到 W−2）；避让要看见的必须是最后要画的那个框。"
           "顺序反了＝推回来的框没有复查碰撞（Atlas 指出的老顺序）。",
}


def tag_check(fit=None, tg=None, verbose=True):
    """跑一格，判三样：落点 / 登记的框不压别人 / 画的框＝登记的框。"""
    fit = block(begin=BEGIN, end=END) if fit is None else fit
    tg = block(begin=TBEGIN, end=TEND) if tg is None else tg
    if "function tag" not in tg:
        raise SystemExit("✗ 抠出来的段里没有 `tag` 的定义 —— 标记范围被改动了")
    harness = TAG_STUBS + fit + "\n" + tg + TAG_CALL
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(harness)
        path = f.name
    try:
        p = subprocess.run(["node", path, json.dumps(TAG_SCENE)], capture_output=True, text=True)
    finally:
        os.unlink(path)
    if p.returncode != 0:
        err = p.stderr.strip().splitlines()[0] if p.stderr.strip() else "rc=%d" % p.returncode
        if verbose:
            print("  ✗ 价签那格跑不动：%s" % err)
        return [("tag", None, "崩了：%s" % err)]
    got = json.loads(p.stdout)
    box, rect, placed = got["box"], got["rect"], got["placed"]
    why = []
    if [_r(v) for v in box] != [_r(v) for v in TAG_SCENE["want"]]:
        why.append("落在 %s，要 %s" % ([_r(v) for v in box], [_r(v) for v in TAG_SCENE["want"]]))
    if [_r(v) for v in rect] != [_r(v) for v in box]:
        why.append("画的框 %s ≠ 登记的框 %s" % (rect, box))
    for q in placed[:-1]:
        if box[0] < q[2] and q[0] < box[2] and box[1] < q[3] and q[1] < box[3]:
            why.append("登记的框压在已登记的 %s 上" % ([_r(v) for v in q],))
    if _r(box[3] - box[1]) != TAG_H:
        why.append("高变了：%g" % (box[3] - box[1]))
    if box[1] < -1e-9 or box[3] > TAG_SCENE["H"] + 1e-9:
        why.append("出了视口：y %g–%g" % (box[1], box[3]))
    if why and verbose:
        print("  ✗ 价签顺序那格（%s）\n      %s" % (TAG_SCENE["why"], "；".join(why)))
    return [("tag", box, "；".join(why))] if why else []


# ---- 探针：每格都得变红（尺子自己先证明会红，不然"全绿"证明不了任何事）----
# ① 改之前那一版（只往上挪、只夹顶）—— 就是 Nova 拍板要补的那版
OLD = """const NUDGE = 19;
function fitBox(box, placed) {
  let out = box;
  if (out[1] < 0) out = [out[0], 0, out[2], out[3] - out[1]];
  for (let n = 0; n < 12; n++) {
    if (!placed.some((q) => out[0] < q[2] && q[0] < out[2] && out[1] < q[3] && q[1] < out[3])) break;
    if (out[1] - NUDGE < 0) break;
    out = [out[0], out[1] - NUDGE, out[2], out[3] - NUDGE];
  }
  return out;
}
"""
# ② 补了「往下试」，但往下不夹底（Atlas 点名要防的那一版）
NO_BOTTOM = """const NUDGE = 19;
function fitBox(box, placed, H) {
  let out = box;
  if (out[1] < 0) out = [out[0], 0, out[2], out[3] - out[1]];
  const hit = (b) => placed.some((q) => b[0] < q[2] && q[0] < b[2] && b[1] < q[3] && q[1] < b[3]);
  for (let n = 0; n < 12; n++) {
    if (!hit(out)) return out;
    if (out[1] - NUDGE < 0) break;
    out = [out[0], out[1] - NUDGE, out[2], out[3] - NUDGE];
  }
  let dn = out;
  for (let n = 0; n < 12; n++) {
    if (!hit(dn)) return dn;
    dn = [dn[0], dn[1] + NUDGE, dn[2], dn[3] + NUDGE];
  }
  return out;
}
"""
# ③ 「夹底边」理解成裁一刀（把框压扁）而不是整框移 —— 高的不变量就是拿它钉的
CLIP = """const NUDGE = 19;
function fitBox(box, placed, H) {
  let out = box;
  if (out[1] < 0) out = [out[0], 0, out[2], out[3] - out[1]];
  const hit = (b) => placed.some((q) => b[0] < q[2] && q[0] < b[2] && b[1] < q[3] && q[1] < b[3]);
  for (let n = 0; n < 12; n++) {
    if (!hit(out)) return out;
    if (out[1] - NUDGE < 0) break;
    out = [out[0], out[1] - NUDGE, out[2], out[3] - NUDGE];
  }
  let dn = out;
  for (let n = 0; n < 12; n++) {
    if (!hit(dn)) return dn;
    dn = [dn[0], dn[1] + NUDGE, dn[2], Math.min(dn[3] + NUDGE, H)];
  }
  return out;
}
"""
# ④ 往下试 20 格（"最多 12 行"没落实）
DEEP = """const NUDGE = 19;
function fitBox(box, placed, H) {
  let out = box;
  if (out[1] < 0) out = [out[0], 0, out[2], out[3] - out[1]];
  const hit = (b) => placed.some((q) => b[0] < q[2] && q[0] < b[2] && b[1] < q[3] && q[1] < b[3]);
  for (let n = 0; n < 12; n++) {
    if (!hit(out)) return out;
    if (out[1] - NUDGE < 0) break;
    out = [out[0], out[1] - NUDGE, out[2], out[3] - NUDGE];
  }
  let dn = out;
  for (let n = 0; n < 20; n++) {
    if (!hit(dn)) return dn;
    if (dn[3] + NUDGE > H) break;
    dn = [dn[0], dn[1] + NUDGE, dn[2], dn[3] + NUDGE];
  }
  return out;
}
"""
# ⑤ 「往左让一格」—— 拿横向那条不变量钉它（Atlas 原话：横着挪＝把标签从它的点上挪开）
SIDEWAYS = """const NUDGE = 19;
function fitBox(box, placed, H) {
  let out = box;
  if (out[1] < 0) out = [out[0], 0, out[2], out[3] - out[1]];
  const hit = (b) => placed.some((q) => b[0] < q[2] && q[0] < b[2] && b[1] < q[3] && q[1] < b[3]);
  for (let n = 0; n < 12; n++) {
    if (!hit(out)) return out;
    if (out[1] - NUDGE < 0) break;
    out = [out[0], out[1] - NUDGE, out[2], out[3] - NUDGE];
  }
  let dn = out;
  for (let n = 0; n < 12; n++) {
    if (!hit(dn)) return dn;
    if (dn[3] + NUDGE > H) break;
    dn = [dn[0] - NUDGE, dn[1] + NUDGE, dn[2] - NUDGE, dn[3] + NUDGE];
  }
  return out;
}
"""


# ⑥ 改之前那条顺序：先 fitBox、**后**推右边界（推回来的框没人复查碰撞）—— 6634be9 之前就在的老顺序
OLD_ORDER_TAG = """function tag(ctx, placed, x, y, text, col, W, H) {
  ctx.font = FONT_SM;
  const tw = ctx.measureText(text).width;
  let box = [x, y - TAG_H, x + tw + 10, y];
  box = fitBox(box, placed, H);
  if (box[2] > W - 2) box = [W - 2 - (box[2] - box[0]), box[1], W - 2, box[3]];
  ctx.fillStyle = rgba(col, CHART.tag_fill);
  ctx.fillRect(box[0], box[1], box[2] - box[0], box[3] - box[1]);
  ctx.fillStyle = CHART.tag_ink;
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText(text, box[0] + 5, (box[1] + box[3]) / 2 + 0.5);
  placed.push(box);
}
"""


def selftest():
    ok = True
    for name, js in [
        ("① 旧版（只往上、只夹顶）", OLD),
        ("② 往下不夹底", NO_BOTTOM),
        ("③ 夹底＝裁一刀（高变了）", CLIP),
        ("④ 往下试 20 格（不是 12）", DEEP),
        ("⑤ 横向也让一格", SIDEWAYS),
    ]:
        bad = check(js, verbose=False)
        hit = "，".join("%s（%s）" % (sc["name"][:2], why) for sc, _, why in bad[:2])
        print("  %s %s：%d 个场景红  %s" % ("✓" if bad else "✗ 没变红", name, len(bad), hit))
        ok = ok and bool(bad)
    # ⑥ 价签那条路：顺序反了必须红
    bad = tag_check(tg=OLD_ORDER_TAG, verbose=False)
    print("  %s ⑥ 价签顺序反了（先避让、后夹右边界）：%s"
          % ("✓" if bad else "✗ 没变红", bad[0][2] if bad else ""))
    ok = ok and bool(bad)
    # ⑦ 两个标记被删 ⇒ 都必须报错，不许静默跳过
    for begin, end, tag in ((BEGIN, END, "FIT_BOX"), (TBEGIN, TEND, "TAG_BOX")):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(open(JS, encoding="utf-8").read().replace(begin, "// (marker removed)"))
            tmp = f.name
        try:
            block(tmp, begin, end)
            print("  ✗ ⑦ %s 标记没了却不报错" % tag)
            ok = False
        except SystemExit:
            print("  ✓ ⑦ %s 标记没了 ⇒ 报错" % tag)
        finally:
            os.unlink(tmp)
    return ok


# ── 命令行参数：两种自测拼法都认，**不认识的参数直接报错退出**（rc=2）─────────────
# ★ card-b6609942-1ad：原来写的是 `if "--selftest" in argv` —— 不认识的参数被**静默吞掉**、
#   闷头跑主跑。自测没跑，看着却像跑过了：`--self-test`（带连字符，check_parity 就是这么写的）
#   在这一版会被吞 ⇒ 印出来的是**主跑**的结果；拼错的旗标同理，而主跑恰好绿的时候，
#   看上去就是「一次通过的自测」。rc=2 跟 argparse 的用法错误同码（①② 本来就是这么退的）。
_SELFTEST_FLAGS = ("--selftest", "--self-test")


def _selftest_requested(argv):
    unknown = [x for x in argv if x not in _SELFTEST_FLAGS]
    if unknown:
        sys.stderr.write("不认识的参数：%s（只认 %s）\n"
                         % (" ".join(unknown), " / ".join(_SELFTEST_FLAGS)))
        sys.exit(2)
    return any(x in _SELFTEST_FLAGS for x in argv)


def main(argv):
    if _selftest_requested(argv):
        print("探针（每格都必须变红）：")
        sys.exit(0 if selftest() else 1)
    bad = check() + tag_check()
    if not bad:
        print("✓ 落框守卫：%d 个场景逐条相同（夹两头 / 有格子就不许压 / 横不动 / 高不变）"
              "；价签那条路：夹右边界在避让之前、画的框＝登记的框" % len(SCENARIOS))
        return 0
    print("✗ 有 %d 处对不上" % len(bad))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
