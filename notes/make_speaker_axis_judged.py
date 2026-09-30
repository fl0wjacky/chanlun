#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""旁档生成器（第 7 栏「依据的变换」）—— **带闸**：寻绿的围栏每次重算并印，超了就拒不出数。

跑法：
    python3 notes/make_speaker_axis_judged.py \
        --corpus /abs/path/to/archive/chanlun108/text \
        --sites  <abs path to gone-331.json> \
        --tsv    notes/speaker_axis_judged.tsv

三条闸（都在这一跑里现算，不靠"上次手量过"）：
  闸1  尺D 只许比尺C 多救 **1** 条 —— 超一条就是**寻绿**，不是变换 ⇒ 拒绝出数（exit=3）。
  闸2  剥法**逐字写死**（见 STRIP_RULE_TEXT / STRIP_RE），不许写成"剥 Markdown 标记"这种描述。
  闸3  每条判词=省略的行都必须拿到一个**尺名**；拿不到 ⇒ 拒绝出数（exit=3），不许留空。

★ 判词指纹的定义（**2026-09-30T15:0x 起 · nova 裁定第 7 栏进指纹**）：
     sha256 over 排序后的 (key_sha1, 判词, 依据的变换) 三元组
  旧定义（(key_sha1, 判词) 二元组）已作废 —— 它在"第 7 栏被改"时**不响**，是个洞。
"""
import argparse, hashlib, io, json, os, re, sys

EL = "……"
WS = re.compile("[\\s　]+")
STRIP_RE = re.compile(r"\*\*|`")
STRIP_RULE_TEXT = u're.sub(r"\\*\\*|`", "", key)  —— 逐字剥两个记号：**两个星号** 与 **一个反引号**；'
STRIP_RULE_TEXT += u'除这两个记号外**一个字符都不动**（剥完必须是原文的子序列）'

ap = argparse.ArgumentParser()
ap.add_argument("--corpus", required=True, help="目录，只认 lesson-<n>.txt")
ap.add_argument("--sites", required=True, help="gone-331.json（原始引文与坐标）")
ap.add_argument("--tsv", required=True)
ap.add_argument("--norm-helper", default=None, help="verify_quotes.py 所在目录（取器自己的 norm）")
a = ap.parse_args()

VNORM = None
if a.norm_helper:
    sys.path.insert(0, a.norm_helper)
    try:
        import verify_quotes as V
        VNORM = V.norm
    except Exception as e:                                    # noqa
        print("★ 取不到器自己的 norm（%s）⇒ 尺C/尺D 缺席，本次**拒绝出数**（不拿别的归一化冒充）" % e)
        sys.exit(3)
if VNORM is None:
    print("★ 没给 --norm-helper ⇒ 尺C/尺D 无从谈起（不许用别的归一化冒充器的那一把）")
    sys.exit(3)

# ---- 语料（只认 lesson-*.txt；扫面随读数一起印）----
files = [f for f in sorted(os.listdir(a.corpus)) if re.match(r"lesson-\d+\.txt$", f)]
per_ws, per_norm = {}, {}
for fn in files:
    t = io.open(os.path.join(a.corpus, fn), encoding="utf-8", errors="ignore").read()
    per_ws[fn] = WS.sub("", t)
    per_norm[fn] = VNORM(t)
print(u"语料扫面：目录 %s · 文件 %d 个 · 规则 ^lesson-\\d+\\.txt$（raw/ 与 全文.txt **不进**）"
      % (a.corpus, len(files)))

hdr_line = lambda t: [l for l in t.split("\n") if l.startswith("# columns\t")][0].split("\t")[1:]
raw = io.open(a.tsv, encoding="utf-8").read()
OLD_COLS = hdr_line(raw)
# ★ 幂等：本文件若已经带第 7 栏，**先摘掉再重算** —— 不然每跑一次就多长一栏。
#   （这一行是给"再跑一次"准备的；第一次生成时它不触发。）
if OLD_COLS and OLD_COLS[-1] == u"依据的变换":
    OLD_COLS = OLD_COLS[:-1]
print("输入列名：%s" % OLD_COLS)

# ---- 三把尺 ----
def segs(key, conv):
    if EL not in key or '"' in key:
        return None
    out = [f for f in (conv(p) for p in key.split(EL)) if f]
    return out or None

def in_order(f, table):
    for name, txt in table.items():
        pos, ok = 0, True
        for x in f:
            i = txt.find(x, pos)
            if i < 0:
                ok = False
                break
            pos = i + len(x)
        if ok:
            return name
    return None

_NOW = lambda p: WS.sub("", p)
rB = lambda k: bool((lambda f: f and in_order(f, per_ws))(segs(k, _NOW)))
rC = lambda k: bool((lambda f: f and in_order(f, per_norm))(segs(k, VNORM)))
rD = lambda k: bool((lambda f: f and in_order(f, per_norm))(segs(STRIP_RE.sub("", k), VNORM)))

sites = json.load(io.open(a.sites, encoding="utf-8"))
key_of = lambda q: hashlib.sha1(q.encode("utf-8")).hexdigest()[:16]
verdict_of = {}
for l in raw.split("\n"):
    if l.startswith("#") or not l.strip():
        continue
    r = l.split("\t")
    verdict_of[r[OLD_COLS.index("key_sha1")]] = r[OLD_COLS.index("判词")]

# 只在**判词=省略**的那些键上量（其余行的判词不由这把尺得出）
omit_keys = sorted({key_of(s["quote"]) for s in sites if verdict_of.get(key_of(s["quote"])) == "省略"})
B = {k for k in omit_keys if rB(next(s["quote"] for s in sites if key_of(s["quote"]) == k))}
C = {k for k in omit_keys if rC(next(s["quote"] for s in sites if key_of(s["quote"]) == k))}
D = {k for k in omit_keys if rD(next(s["quote"] for s in sites if key_of(s["quote"]) == k))}

# ---- 闸1：现算并印（"这一次手量过"明天会变成没人知道）----
print(u"★ 闸1 尺C 救 %d · 尺D 救 %d · **尺D 多救 %d**（上限 1）" % (len(C), len(D), len(D) - len(C)))
if len(D) - len(C) > 1:
    print(u"★★ 尺D 比尺C 多救 %d 条 > 1 ⇒ 这是**寻绿**不是变换 ⇒ 拒绝出数（exit=3）" % (len(D) - len(C)))
    sys.exit(3)

T_WS, T_NORM, T_MD = u"去空白（两侧·尺B）", u"norm()（两侧·尺C）", u"剥 **|` 后 norm()（两侧·尺D）"
T_NA = u"不适用（判词不由省略尺得出）"

out, stat = [], {}
for l in raw.split("\n"):
    if l.startswith("# columns\t"):
        cols = OLD_COLS + [u"依据的变换"]
        out.append("# columns\t" + "\t".join(cols)); continue
    if l.startswith("#") or not l.strip():
        out.append(l); continue
    r = l.split("\t")[:len(OLD_COLS)]
    k, v = r[OLD_COLS.index("key_sha1")], r[OLD_COLS.index("判词")]
    if v == u"省略":
        cell = T_WS if k in B else (T_NORM if k in C else (T_MD if k in D else None))
        if cell is None:                      # 闸3
            print(u"★★ %s 判词=省略 但三条尺全不绿 ⇒ 拒绝出数（不许留空 / 不许猜）" % k)
            sys.exit(3)
    else:
        cell = T_NA
    stat[cell] = stat.get(cell, 0) + 1
    out.append("\t".join(r) + "\t" + cell)

body = "\n".join(out)
io.open(a.tsv, "w", encoding="utf-8").write(body)

# ---- 指纹（**新定义**：三点对）----
rows = [x.split("\t") for x in body.split("\n") if x.strip() and not x.startswith("#")]
cols = hdr_line(body)
k_i, v_i, t_i = cols.index("key_sha1"), cols.index(u"判词"), cols.index(u"依据的变换")
fp3 = hashlib.sha256("\n".join("%s\t%s\t%s" % (r[k_i], r[v_i], r[t_i])
                               for r in sorted(rows, key=lambda r: r[k_i])).encode()).hexdigest()[:16]
fp2 = hashlib.sha256("\n".join("%s\t%s" % (r[k_i], r[v_i])
                               for r in sorted(rows, key=lambda r: r[k_i])).encode()).hexdigest()[:16]
print(u"\n列名：%s" % cols)
print(u"数据行 %d" % len(rows))
print(u"第 7 栏分布：%s" % {k: v for k, v in sorted(stat.items())})
print(u"★ 判词指纹（新定义 三元组）= %s" % fp3)
print(u"  旧定义（二元组，已作废）    = %s   ← 它盖不住第 7 栏，故换" % fp2)
print(u"★ 文件 sha256[:16] = %s" % hashlib.sha256(body.encode()).hexdigest()[:16])
print(u"★ 剥法逐字：%s" % STRIP_RULE_TEXT)
