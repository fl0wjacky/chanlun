#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""iris 版引号自查 —— 默认用**整块尺**，不是宽松门。

★★ 2026-10-01 重写。上一版默认判据是「存在一段 ≥THRESH 字的连续逐字」，
   这条**已撤回**：它对**删字/改字结构性失明** —— 把中间一整句摘掉、两头照样连得上，它就放行。
   同一天、同一份文件，旧尺报「非语料「」＝0」，整块尺报 **46 条真红**。
   ⇒ 本脚本默认（也是唯一）的判据是整块尺。**不要再给一把能放松的门。**

判据（三选一即算语料引文）：
  A. **整块逐字**：把 `↵` 还原成换行后，整块是**某一课**语料的连续子串；
  B. **剥装饰后整块逐字**：剥掉装饰（`**` ／ `↵` ／ 各式引号 ／ 括号 ／ 反引号）后同上；
  C. **省略号按序**：块内按 `…` 切片，**每一片都逐字**，且**按顺序落在同一课**里。

  装饰一律**双侧**剥（只剥一侧 ⇒ 语料自带引号/空格的句子全判不中，那是假红）。
  **`…` 是唯一的例外**：删字必须在块里显式打出 `…`；**没标 `…` 的不连续，直接红。**

语料之脏（本尺认这个脏，不做「修字」）：
  · 语料有 OCR 重字 ⇒ 逐字引用必然把重字一起引进来，**照引**；
  · 语料自带半角逗号/半角括号/游离反引号 ⇒ **照引**，反引号当装饰剥掉。

用法：
  python3 notes/checkquotes_iris.py <我的md> [--min 1]
  （--min 是**门槛**，默认 1 ＝ 全量。门槛会吃掉分母，所以默认不设门槛。）
"""
import hashlib
import os
import re
import sys
import unicodedata

# ★ 路径口径（2026-10-01 第 13 批补）：原版是相对路径，必须 cd 到仓库根才跑得动 ——
#   与 bram 那六个 /tmp 输入同一类毛病。现在按 __file__ 定位，**在哪个目录跑都一样**。
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, 'archive/chanlun108/text')
DECOR = '**「」『』“”‘’"\'()（）`↵'


def canon(x):
    """去装饰 + 全角/半角统一（**双侧同做**）。"""
    for ch in DECOR:
        x = x.replace(ch, '')
    return unicodedata.normalize('NFKC', re.sub(r'\s+', '', x))


def load():
    """每课一份原文；返回 {课名: (原文, canon 后原文)}。"""
    out = {}
    for fn in sorted(os.listdir(CORPUS)):
        if not fn.endswith('.txt'):
            continue
        raw = open(os.path.join(CORPUS, fn), encoding='utf-8', errors='replace').read().replace('\r', '')
        out[fn] = (raw, canon(raw))
    return out


def corpus_sig(lessons):
    """★★★ 第 14 批加（atlas 的第二层）：**断"我拿全了东西"**。

    「块数 0 就炸」只挡"什么都没检查"，**挡不住"语料只加载了一课"** —— 那时块数非 0、照绿。
    这里用**与 `notes/verify_inventory.py` 完全相同的算法**算语料指纹，
    ⇒ 两把工具对同一个数，**任何一方拿少了语料，两边就报不出同一个指纹**。
    断言写死本批的期望值；语料若真有变动，**先来改这一行、并说明为什么**，不许默默漂移。
    """
    h = hashlib.sha256()
    for n in range(1, 109):
        h.update(('%d:' % n).encode())
        raw = lessons.get('lesson-%03d.txt' % n)
        if raw is None:
            return None, n, 0          # 缺课 ⇒ 指纹算不出来，本身就是报警
        h.update(raw[0].encode())
    return h.hexdigest()[:16], None, len(lessons)


EXPECT_SIG = '14b4800f220a2a92'
EXPECT_N = 108


def hit_whole(block, lessons):
    """A/B：整块（原样，或剥装饰后）逐字落在某一课里。"""
    a = block.replace('↵', '\n')
    b = ''.join(ch for ch in block if ch not in DECOR).replace('↵', '\n')
    for fn, (raw, cn) in lessons.items():
        if a in raw or b in raw:
            return 'strict' if a in raw else 'deco'
    for fn, (raw, cn) in lessons.items():
        if canon(block) in cn:
            return 'norm'
    return None


def hit_ellipsis(block, lessons):
    """C：按 `…` 切片，每片逐字，且按顺序落在**同一课**里。

    ★★★ 2026-10-01 第 14 批修（**报红 4 条，Atlas 的对照法查出来 4 条全是尺乱咬**）：
    原版 `len(segs) < 2: return False` —— **只认块中间的 `…`**。
    而 `开头…`、`结尾…`、`…两头都…` 这三种写法切出来**只有一片**，
    于是**构造上必然落进 `都不中`**，无论引得多准。
    ⇒ 后果不是"漏报"，是**把这三种写法永久钉成假红**：4 条假红静静躺了三批，
      我管它叫『已知口径差』就过去了 —— 那等于**给真缺陷留了一个藏身处**。
    现在：一片也认（该片逐字即可），但**单列一栏 `截断引`**，
    **绝不与 `都不中` 混在一起报** —— 报数的人要知道红是哪一种红。
    """
    # ★★ 硬闸：**块里没有 `…` 就不归 C 管**。
    #   我第一版改完漏了这条 ⇒ 任何"剥装饰后恰好是语料子串"的块都从 C 走绿，
    #   等价于把 C 变成一把**宽松门**（正是本文件开头撤回过的那个东西）。
    #   **是 `--selftest` 的 ①b 当场逮住的**（自造词 `类第一类买点` 被判绿）。
    if '…' not in block:
        return None
    segs = [s for s in re.split(r'…+', ''.join(ch for ch in block if ch not in DECOR)) if s.strip()]
    if not segs:
        return None
    for fn, (raw, cn) in lessons.items():
        pos, ok = 0, True
        for s in segs:
            p = cn.find(canon(s), pos)
            if p < 0:
                ok = False
                break
            pos = p + len(canon(s))
        if ok:
            # 片数 ≥2 ⇒ 中间省略；片数 ==1 ⇒ 只有首或尾省略
            return 'ellipsis' if len(segs) >= 2 else 'trunc'
    return None


def selftest(lessons):
    """★★★ 尺的两条对照 —— 2026-10-01 第 14 批加（atlas 提的，且他说得对：**要两条**）。

    ① **阳性对照**：塞一个**该红**的块（真语料原句拿掉一个字），看它红不红 ⇒ 防**尺瞎了**。
    ② **阴性对照**：塞一句**真语料原句**，看它绿不绿 ⇒ 防**尺乱咬（假红）**。
    两条例都不靠人记得去做，**挂在尺里，每次跟主程序一起跑**。
    """
    print('=== 尺自检（两条对照）===')
    ok = True
    # 取一句真语料做基准：用第 15 课那句最短的定理句当阳性/阴性同源样本
    base = '没有趋势，没有背驰'
    hits = [fn for fn, (raw, cn) in lessons.items() if base in raw]
    if not hits:
        print('  ⚠ 阴性对照样本不在语料里，自检跳过（这本身也是报警）')
        return False
    fn = hits[0]
    raw = lessons[fn][0]
    # ② 阴性：原句原样 ⇒ 必须绿
    n_ok = hit_whole(base, lessons) is not None
    print(f'  ② 阴性对照（真原句，{fn}）: {"绿 ✓" if n_ok else "★ 红 ✗ —— 尺在乱咬"}')
    ok &= n_ok
    # ① 阳性：同句删掉一个字 ⇒ 必须红
    mut = base[:2] + base[3:]
    p_ok = hit_whole(mut, lessons) is None and hit_ellipsis(mut, lessons) is None
    print(f'  ① 阳性对照（同句删一字 {mut!r}）: {"红 ✓" if p_ok else "★ 绿 ✗ —— 尺瞎了"}')
    ok &= p_ok
    # ①b 阳性第二式 —— ★★★ 这一条本身就是第 14 批的收获，写死在尺里：
    #   `类第一类／类第二类买点` 是**两个真词用 `/` 拼起来的**，两半都在语料里（L27／L29／L86），
    #   拼起来**不是**任何一课的连续子串 ⇒ **必须红**。
    #   我原来在这条位置放的是 `类第一类买点`，还以为是自己造的词 ——
    #   它**本来就是语料里的词**（L27:2674「盘整背驰而形成的类第一类买点了」），
    #   于是这条"阳性对照"一直报绿，我差点把**真的阳性对照失灵**当成尺瞎了。
    #   ⇒ 教训：**阳性对照用的样本本身要先被验一次**，否则你验的是自己的错觉。
    fake = '类第一类／类第二类买点'
    f_ok = hit_whole(fake, lessons) is None and hit_ellipsis(fake, lessons) is None
    print(f'  ①b 阳性对照（两真词用 / 拼，非连续子串 {fake!r}）: {"红 ✓" if f_ok else "★ 绿 ✗ —— 尺瞎了"}')
    ok &= f_ok
    # ①c 阳性第三式：**语义反转**（真句拿掉一个「不」）—— 最阴的一种，它每个字都在语料里
    rev = '背驰的级别一定小於转折的级别'
    r_ok = hit_whole(rev, lessons) is None and hit_ellipsis(rev, lessons) is None
    print(f'  ①c 阳性对照（语义反转 {rev!r}）: {"红 ✓" if r_ok else "★ 绿 ✗ —— 尺瞎了"}')
    ok &= r_ok
    # ②b 阴性第二式：截断引（首 …）⇒ 必须**绿且归入 trunc 栏**，不是进 都不中
    tr = '…没有趋势'
    t_ok = hit_ellipsis(tr, lessons) == 'trunc'
    print(f'  ②b 阴性对照（首 … 截断引 {tr!r}）: {"绿/trunc ✓" if t_ok else "★ 落进 都不中 ✗ —— 假红的老病"}')
    ok &= t_ok
    print(f'=== 自检结论：{"两条都在 ✓" if ok else "★ 有一条不在，尺不可信"} ===')
    return ok


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    path = sys.argv[1]
    # ★★ 参数解析（第 14 批修）：原来只认 `--min`，**未知开关被静默吞掉** ——
    #   我自己的附录里写的是 `--thresh`，于是它一直用默认门槛在跑，
    #   报出一个**看着像数、其实是默认值**的结果（就是 §15.18 那条）。
    #   ⇒ 现在两个名字都收，**认不出的开关当场报错退出**（失败要长得像失败）。
    # ★ 注意 `--selftest` 也要在这里登记 —— 我第一版加这条硬闸时把它自己闸掉了（**当场跑出来的**，
    #   不是读出来的：`--selftest` 报"不认识的开关"）。同一个坑：加一道闸，先看它挡不挡自己人。
    known = {'--min', '--thresh', '--selftest'}
    argv = sys.argv[2:]
    unknown = [a for a in argv if a.startswith('--') and a not in known]
    if unknown:
        print('★ 不认识的开关：%s —— 本脚本只认 %s。**不猜、不吞**。' % (' '.join(unknown), '／'.join(sorted(known))))
        sys.exit(2)
    threshold = 1
    for flag in ('--min', '--thresh'):          # 只这两个带参数；`--selftest` 是无参开关
        if flag in sys.argv:
            threshold = int(sys.argv[sys.argv.index(flag) + 1])

    lessons = load()
    if '--selftest' in sys.argv:
        sys.exit(0 if selftest(lessons) else 1)
    text = open(path, encoding='utf-8').read()
    # 块 = 「…」 内内容（不含嵌套；嵌套时外层不取，见文末告警）
    blocks = [b for b in re.findall(r'「([^「」]*)」', text, re.S) if len(canon(b)) >= threshold]
    nested = len(re.findall(r'「[^「」]*「', text))

    # ★★ 空输入的特征签名（第 14 批，转自 bram 的统一尺 `cf04368`，atlas 提的方向）：
    #   块数 0 ⇒ 我原来报 `都不中 0` + exit 0，**和"引文全对"长得一模一样** —— 静默，危险的一侧。
    #   语料没加载到则是另一侧：全红 + exit 1，吵，安全。两侧都要写死在文件里。
    sig, missing, nloaded = corpus_sig(lessons)
    if sig is None:
        print(f'★ 语料缺第 {missing} 课 ⇒ 指纹算不出来 —— 不许当绿。')
        sys.exit(2)
    if sig != EXPECT_SIG or nloaded != EXPECT_N:
        print(f'★ 语料指纹不符：实得 {sig}（{nloaded} 课），期望 {EXPECT_SIG}（{EXPECT_N} 课）。')
        print('  ⇒ 断的不是"文件对不对"，是**"我拿全了没有"**。要改期望值，先说明语料为什么变了。')
        sys.exit(2)
    if not blocks:
        print(f'文件        : {path}')
        print(f'语料指纹     : {sig}（{nloaded} 课）')
        print('★ 块数 0 —— 这**不是"引文全对"**，是**什么都没检查**。')
        print('  两种可能：① 文件路径错/为空；② 语料没加载到。两种都不许当绿。')
        sys.exit(2)

    c = {'strict': 0, 'deco': 0, 'norm': 0, 'ellipsis': 0, 'trunc': 0}
    miss = []
    for b in blocks:
        k = hit_whole(b, lessons) or hit_ellipsis(b, lessons)
        if k:
            c[k] += 1
        else:
            miss.append(b)

    print(f'文件        : {path}')
    print(f'语料指纹     : {sig}（{nloaded} 课）  ← ★ 断"我拿全了东西"；与 verify_inventory.py 同一算法')
    print(f'门槛        : 「」块内容 ≥ {threshold} 字（≥ 字数为 0 的块不计入分母）')
    print(f'「」块       : {len(blocks)}')
    print(f'  整块逐字   : {c["strict"]}')
    print(f'  剥装饰后   : {c["deco"]}')
    print(f'  仅空白归一 : {c["norm"]}')
    print(f'  省略号按序 : {c["ellipsis"]}')
    print(f'  截断引     : {c["trunc"]}   ← 首/尾 `…`，片片逐字（★ 第 14 批前这栏**不存在**，全被算进「都不中」）')
    print(f'  ★ 都不中   : {len(miss)}')
    print(f'含 ↵ 折行    : {sum("↵" in b for b in blocks)}')
    print(f'含省略号     : {sum("…" in b for b in blocks)}')
    if nested:
        print(f'⚠ 疑似嵌套「」: {nested} 处 —— 本脚本的 `[^「」]*` 会**整块跳过外层**，'
              f'嵌套的地方要人工看（这是尺的已知缺口，不是文件的问题）')
    if miss:
        print('\n--- 都不中的块 ---')
        for b in miss:
            print(f'  ✗ {b[:100]!r}')


if __name__ == '__main__':
    main()
