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
import argparse, hashlib, io, json, os, re, subprocess, sys

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
ap.add_argument("--expect-fp", default=None,
                help="钉住的判词指纹（三元组）。给了就当场并排核，对不上 exit=4。"
                     "★ 不给 ⇒ 从**表头**那行读（本脚本这样才「每次重跑都在核」）；"
                     "表头也没有 ⇒ **只印不核**，脚本会明说，按仓规那还是「意向」不是证据")
ap.add_argument("--expect-judge", default=None, metavar="<sha256前16位>",
                help="钉住的**判据**（被 import 的那份 verify_quotes.py）的 sha256 前 16 位。"
                     "不匹配 ⇒ exit=5。★ 为什么：本脚本的读数 = f(对象, 语料, **判据**)，"
                     "而判据是唯一一个**我可以悄悄换掉**的输入 —— 换一把 norm，绿集就动，而产物不会自己红。")
a = ap.parse_args()

VNORM, VFILE = None, None
if a.norm_helper:
    sys.path.insert(0, a.norm_helper)
    try:
        import verify_quotes as V
        VNORM, VFILE = V.norm, getattr(V, "__file__", None)
    except Exception as e:                                    # noqa
        print("★ 取不到器自己的 norm（%s）⇒ 尺C/尺D 缺席，本次**拒绝出数**（不拿别的归一化冒充）" % e)
        sys.exit(3)
if VNORM is None:
    print("★ 没给 --norm-helper ⇒ 尺C/尺D 无从谈起（不许用别的归一化冒充器的那一把）")
    sys.exit(3)

# ---- 判据身份：**是我真导进来的那个文件**（同器 `judge_id()` 的口径）----
#   ★ 印**路径 + sha** 两样：只印路径会漏掉"同名两份"（本机今天正好有：仓里那份 48c38a6f… 与
#     我主克隆工作目录里那份旧的 05a04cd0…，`norm()` 差一个字面 ⇒ 绿集差一整条）。
_jb = io.open(VFILE, "rb").read() if VFILE and os.path.exists(VFILE) else b""
JSHA = hashlib.sha256(_jb).hexdigest()[:16] if _jb else None
print(u"★ 判据身份：%s" % (VFILE or u"**取不到 `V.__file__`**"))
print(u"   sha256[:16] = %s" % (JSHA or u"**算不出**（拿不到字节 ⇒ 本次判据不可复算）"))
if not JSHA:
    print(u"★★ 判据身份都报不出来 ⇒ 拒绝出数（一个复算不出判据的读数，不该出数）")
    sys.exit(5)
if a.expect_judge:
    jok = (JSHA == a.expect_judge)
    print(u"★ 判据核：**钉的** %s ｜ **现算的** %s ⇒ %s"
          % (a.expect_judge, JSHA, u"对上 ✓" if jok else u"**对不上**"))
    if not jok:
        print(u"★★ 判据不是钉的那份 ⇒ 拒绝出数（exit=5）· **本跑没写文件** —— "
              u"本脚本的绿集是判据的函数，换一把 norm 可以整条改掉尺C/尺D 的结果，而产物不会自己红。")
        sys.exit(5)

# ---- 语料（只认 lesson-*.txt；扫面随读数一起印）----
files = [f for f in sorted(os.listdir(a.corpus)) if re.match(r"lesson-\d+\.txt$", f)]
per_ws, per_norm = {}, {}
for fn in files:
    t = io.open(os.path.join(a.corpus, fn), encoding="utf-8", errors="ignore").read()
    per_ws[fn] = WS.sub("", t)
    per_norm[fn] = VNORM(t)
print(u"语料扫面：目录 %s · 文件 %d 个 · 规则 ^lesson-\\d+\\.txt$（raw/ 与 全文.txt **不进**）"
      % (a.corpus, len(files)))

# ---- 输入的位置（@nova-8980：「**输入的位置也是断言的一部分**」）----
# ★ 「在不在树上」**当场问 git**，不写成散文 —— 散文里的"不在树上"跑的时候不核，那就是化石。
def tracked(p):
    """★ 三态，**不许并成两态**（@iris-64a1 15:0x 自己踩的）：
       `git ls-files --error-unmatch` 对"在仓里但未跟踪"给 rc=1，对"**路径根本在仓外**"给 rc=128。
       我第一版写成 `rc==0 else 不在树上` ⇒ **两种不同的病共用一张脸**。
       （同族：本仓那条「『没查过』和『查过、没有』不许共用一个值」。）"""
    try:
        r = subprocess.run(["git", "ls-files", "--error-unmatch", p],
                           cwd=os.path.dirname(os.path.abspath(a.tsv)),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:                                # noqa
        return u"判不了（拿不到 git：%s）" % e
    if r.returncode == 0:
        return u"**在树上**"
    if r.returncode == 1:
        return u"**在仓里但未跟踪**（工作目录里有它，git 不管它）"
    return u"**不在这个仓里**（rc=%d ⇒ 路径在仓外，不是一个仓能答的问题）" % r.returncode
print(u"★ 输入位置：")
print(u"   引文档 %s  ⇒ %s" % (a.sites, tracked(a.sites)))
print(u"   语料   %s  ⇒ %s（版权，.gitignore 的 archive/chanlun108/）"
      % (a.corpus, tracked(a.corpus)))
print(u"   ★ 判据：**产物可以只用公开件复算，但整支生成器不能** —— 缺席的那个输入，"
      u"它的位置和它的内容一样是断言的一部分。")

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

# ---- 指纹（**新定义**：三点对）----
rows = [x.split("\t") for x in body.split("\n") if x.strip() and not x.startswith("#")]
cols = hdr_line(body)
k_i, v_i, t_i = cols.index("key_sha1"), cols.index(u"判词"), cols.index(u"依据的变换")
fp3 = hashlib.sha256("\n".join("%s\t%s\t%s" % (r[k_i], r[v_i], r[t_i])
                               for r in sorted(rows, key=lambda r: r[k_i])).encode()).hexdigest()[:16]
fp2 = hashlib.sha256("\n".join("%s\t%s" % (r[k_i], r[v_i])
                               for r in sorted(rows, key=lambda r: r[k_i])).encode()).hexdigest()[:16]

# ---- 闸4：fp3 **被核**，不是只被印（@nova-8980 2026-09-30T15:00Z 要求）----
#   ★ 顺序要紧：**闸先跑、文件后写** —— 先写后判，会让"拒绝出数"留下一个**已被覆盖**的产物。
#   ★ 为什么需要它：没有 --expect-fp 时，fp3 只是**印出来**，没有任何地方比较它
#     ⇒ 按本仓刚立的仓规，那还是**意向**，不是证据（"实测/一致"要带对象或带当场算的数）。
#   ★ 钉的值**住在产物自己表头里**（`# ★ 钉住的判词指纹（三元组）= <16位>`）⇒ 每次重跑都自动在核，
#     不靠谁记得加旗标；重新钉 = **当场改表头那行**（这个动作本身又会改文件 sha，看得见）。
PIN_RE = re.compile(u"^#\\s*★\\s*钉住的判词指纹（三元组）\\s*=\\s*([0-9a-f]{16})", re.M)
_pin_hdr = PIN_RE.search(raw)
pin = a.expect_fp or (_pin_hdr.group(1) if _pin_hdr else None)
src = (u"--expect-fp（旗标）" if a.expect_fp else
       (u"**表头那一行**" if _pin_hdr else None))
if pin:
    same = (fp3 == pin)
    # ★ 两个数印在同一行（@bram-9d29 的机器版：「两个数必须出现在同一个屏幕上才算核过一次」）
    print(u"\n★ 闸4 判词指纹：**钉的** %s ｜ **现算的** %s ⇒ %s   （钉的出处：%s）"
          % (pin, fp3, u"对上 ✓" if same else u"**对不上**", src))
    if not same:
        print(u"★★ 对不上 ⇒ 拒绝出数（exit=4）· **本跑没写文件** —— "
              u"要么产物被谁改了，要么定义被人改了，要么**判据换了**（先看上面那行判据身份），"
              u"三样各查一次再怀疑对方")
        sys.exit(4)
else:
    print(u"\n★ 闸4 表头没钉、旗标也没给 ⇒ fp3 只被印出、**没被核** "
          u"（只印出来的数按仓规仍是「意向」，不是证据 —— 本行就是那句自我披露）")

io.open(a.tsv, "w", encoding="utf-8").write(body)
print(u"列名：%s" % cols)
print(u"数据行 %d" % len(rows))
print(u"第 7 栏分布：%s" % {k: v for k, v in sorted(stat.items())})
print(u"★ 判词指纹（新定义 三元组）= %s" % fp3)
print(u"  旧定义（二元组，已作废）    = %s   ← 它盖不住第 7 栏，故换" % fp2)
print(u"★ 文件 sha256[:16] = %s" % hashlib.sha256(body.encode()).hexdigest()[:16])
print(u"★ 剥法逐字：%s" % STRIP_RULE_TEXT)
