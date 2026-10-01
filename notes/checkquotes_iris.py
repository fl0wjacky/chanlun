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
import os
import re
import sys
import unicodedata

CORPUS = 'archive/chanlun108/text'
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
    """C：按 `…` 切片，每片逐字，且按顺序落在**同一课**里。"""
    segs = [s for s in re.split(r'…+', ''.join(ch for ch in block if ch not in DECOR)) if s.strip()]
    if len(segs) < 2:
        return False
    for fn, (raw, cn) in lessons.items():
        pos, ok = 0, True
        for s in segs:
            p = cn.find(canon(s), pos)
            if p < 0:
                ok = False
                break
            pos = p + len(canon(s))
        if ok:
            return True
    return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    path = sys.argv[1]
    threshold = 1
    if '--min' in sys.argv:
        threshold = int(sys.argv[sys.argv.index('--min') + 1])

    lessons = load()
    text = open(path, encoding='utf-8').read()
    # 块 = 「…」 内内容（不含嵌套；嵌套时外层不取，见文末告警）
    blocks = [b for b in re.findall(r'「([^「」]*)」', text, re.S) if len(canon(b)) >= threshold]
    nested = len(re.findall(r'「[^「」]*「', text))

    c = {'strict': 0, 'deco': 0, 'norm': 0, 'ellipsis': 0}
    miss = []
    for b in blocks:
        k = hit_whole(b, lessons)
        if k:
            c[k] += 1
        elif hit_ellipsis(b, lessons):
            c['ellipsis'] += 1
        else:
            miss.append(b)

    print(f'文件        : {path}')
    print(f'门槛        : 「」块内容 ≥ {threshold} 字（≥ 字数为 0 的块不计入分母）')
    print(f'「」块       : {len(blocks)}')
    print(f'  整块逐字   : {c["strict"]}')
    print(f'  剥装饰后   : {c["deco"]}')
    print(f'  仅空白归一 : {c["norm"]}')
    print(f'  省略号按序 : {c["ellipsis"]}')
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
