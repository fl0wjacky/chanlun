#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""代读笔记 · 坐标核（atlas）

为什么另写这一把：`notes/audit_lines.py` 认的是『第 N 课 `:行号`「引文」』那种写法，
本笔记用的是 `L14:28「…」`／`:28` 的形式 ⇒ 它在本文件上**抽出 0 条、rc=0**
—— 那是「空输入与全绿长得一模一样」的危险一侧，**不能当查过**。
所以这里直接把笔记里每一条「引文 ＋ 我标的坐标」拿出来，回语料逐条对。

判据＝**严档**：把该课文本的换行删掉（接缝不加空格，与语料惯例一致），
定位引文**首次出现**的字符区间，映射回**行号**；要求
  · 起点行 == 我标的首行
  · 终点行 == 我标的末行（单行引文则首末相同）

用法：python3 notes/核坐标-代读.py
      加 --perturb 跑**阳性对照**（把一条坐标故意改错，应报红、rc=1）
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT = os.path.join(ROOT, 'archive', 'chanlun108', 'text')

# (课号, 我标的首行, 我标的末行, 引文)
CLAIMS = [
    (14, 28, 28, '大级别的第二类买点，由次一级别相应走势的第一类买点构成。'),
    (14, 39, 39, '大级别买点介入的，在次级别第一类卖点出现时，可以先减仓'),
    (15,  7,  7, '就是走势的三种分类：上涨、下跌、盘整。'),
    (15,  7,  7, '所有走势都可以分解成这三种情况。'),
    (15, 10, 11, '所有上涨、下跌、盘整都建立在一定的周期图表上，例如在日线上的盘整，在 30 分钟线上可能就是上涨或下跌'),
    (15, 18, 19, '因为高高点、低点是有其级别的'),
    (15,  2,  2, '教你炒股票 15：没有趋势，没有背驰。'),
    (15, 34, 34, '在盘整中是无所谓“背驰”的'),
    (15, 59, 59, '最后先有一段离开中枢随即紧跟一段回抽，但这个回抽的顶点未落在中枢里，这时候是买卖的最后机会，为第 3 买卖点。'),
    (15,101,101, '任何的上涨转折都是由某级别的第一类卖点构成的；任何的下跌转折都是由某级别的第一类买点构成的'),
    (16,  5,  6, '走势是分级别的，在 30 分钟上的上涨，可能在日线图上只是盘整的一段，甚至是下跌中的反弹，所以抛开级别前提而谈论趋势与盘整是毫无意义的'),
    (78, 51, 51, '例如把线段为基础构成最小级别的中枢等，都可以把该线段标准化为最高或最低点都在端点。'),
    (78, 52, 52, '都把线段当成一个没有内部结构的基本部件'),
    (78, 56, 56, '也为后面的中枢、走势类型等分析提供了最标准且基础的部件。'),
    (98,  5,  5, '理论只能保证其回拉原来的中枢'),
    (98, 16, 16, '因为已经存在的第二个线段类中枢'),
    (98, 17, 17, '那么这线段类上涨结束形成一个 1 分钟中枢就要情理之中了。'),
    (98, 18, 19, '一个线段的类背驰是否需要抛点货'),
]


def locate(course, quote):
    """回语料：删换行后定位，映射回 (起行, 止行)。找不到返回 None。"""
    path = os.path.join(TXT, 'lesson-%03d.txt' % course)
    lines = open(path, encoding='utf-8').read().split('\n')
    merged = ''.join(lines)
    pos = merged.find(quote)
    if pos < 0:
        return None
    # 字符位置 -> 行号
    end = pos + len(quote) - 1
    starts, acc = [], 0
    for i, l in enumerate(lines, 1):
        starts.append((acc, acc + len(l), i))
        acc += len(l)
    def line_of(p):
        for a, b, i in starts:
            if a <= p < b:
                return i
        return starts[-1][2]
    return line_of(pos), line_of(end)


def main():
    perturb = '--perturb' in sys.argv
    bad = 0
    print('课   我标      语料实得    引文')
    print('-' * 78)
    for n, (course, a, b, q) in enumerate(CLAIMS):
        ca, cb = a, b
        if perturb and n == 0:          # 阳性对照：把 L14:28 故意改成 :9999
            ca = cb = 9999
        got = locate(course, q)
        if got is None:
            print('L%-3d %-8s  %-10s  ★ 语料里找不到：%s' % (course, '%d-%d' % (ca, cb), '缺', q[:28]))
            bad += 1
            continue
        ok = (got[0] == ca and got[1] == cb)
        if not ok:
            bad += 1
        print('L%-3d %-8s  %-10s  %s%s' % (
            course, '%d-%d' % (ca, cb), '%d-%d' % got, '' if ok else '★ 对不上  ', q[:34]))
    print('-' * 78)
    print('计 %d 条 ｜ 对不上 %d 条 ｜ %s' % (len(CLAIMS), bad, '红' if bad else '绿'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
