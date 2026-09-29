#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把《教你炒股票》108 课全文抓到本地。

背景：源站是单页应用，直接 curl 有时会返回目录页（限流）；
      判断办法是看 <title> 里有没有「第N课」。

产物：
  archive/chanlun108/raw/lesson-NNN.html    原始页
  archive/chanlun108/text/lesson-NNN.txt    去标签后的正文（便于 grep）
  archive/chanlun108/全文.txt               108 课合并（带分隔线，grep 用）
  archive/chanlun108/目录.txt               序号 + 标题清单
"""
import os, re, sys, time, html, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "archive", "chanlun108")
RAW, TXT = os.path.join(BASE, "raw"), os.path.join(BASE, "text")
URL = "https://www.furleader.cn/chanlun108/lesson-%03d.html"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")


def fetch(n):
    """返回 (html文本, 是否有效)"""
    out = subprocess.run(["curl", "-s", "-m", "30", "-A", UA, URL % n],
                         capture_output=True)
    s = out.stdout.decode("utf-8", errors="ignore")
    ok = ("第%d课" % n) in s[:3000]
    return s, ok


def to_text(s):
    s = re.sub(r"<(script|style).*?</\1>", "", s, flags=re.S)
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    # 只认白名单里的真标签。原文公式里有裸的「<」：「后 ZG<前 ZD」「gn<ZD」「<max」，
    # 泛匹配 <[^>]+> 或「< 后跟字母」都会把公式一直吃到下一个 > 为止
    # （第 20 课中心定理一、二曾被截）。源站只用到下面这些标签，全小写。
    # 行内标签直接删掉不换行 —— 否则公式里的 GG、DD 会被拆成单独一行。
    s = re.sub(r"</?(?:span|a|b|i|em|strong|font|sub|sup|u)\b[^>]*>", "", s)
    block = r"p|div|br|h[1-6]|li|ul|ol|table|tr|td|th|img|meta|link|nav|footer|header|button|title|html|head|body"
    t = html.unescape(re.sub(r"</?(?:%s)\b[^>]*>" % block, "\n", s))
    lines = [l.strip() for l in t.split("\n") if l.strip()]
    # 去掉页头页尾的导航块，只留正文
    try:
        a = next(i for i, l in enumerate(lines) if l.startswith("教你炒股票 第"))
        b = next(i for i, l in enumerate(lines) if l.startswith("‹ 第")
                 or l.startswith("相关推荐") or l.startswith("缠论108课目录"))
        lines = lines[a:b]
    except StopIteration:
        pass
    return "\n".join(lines)


def main():
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(TXT, exist_ok=True)
    ok, fail = [], []
    for n in range(1, 109):
        p = os.path.join(TXT, "lesson-%03d.txt" % n)
        if os.path.exists(p) and os.path.getsize(p) > 1500:
            ok.append(n)
            continue
        got = False
        for attempt in range(3):
            s, good = fetch(n)
            if good:
                open(os.path.join(RAW, "lesson-%03d.html" % n), "w",
                     encoding="utf-8").write(s)
                open(p, "w", encoding="utf-8").write(to_text(s))
                ok.append(n)
                got = True
                break
            time.sleep(3 + attempt * 4)
        if not got:
            fail.append(n)
            print("  ✗ 第%d课 抓取失败" % n, flush=True)
        else:
            print("  ✓ %d" % n, end="", flush=True)
        time.sleep(1.2)
    print()
    merge()
    print("成功 %d 课，失败 %d 课" % (len(ok), len(fail)))
    if fail:
        print("失败课号:", fail)


def reparse():
    """不联网：用 raw/ 里已存的原始页重新生成 text/ 与全文（改了 to_text 之后跑这个）。"""
    n = 0
    for f in sorted(os.listdir(RAW)):
        if f.endswith(".html"):
            s = open(os.path.join(RAW, f), encoding="utf-8").read()
            open(os.path.join(TXT, f[:-5] + ".txt"), "w", encoding="utf-8").write(to_text(s))
            n += 1
    merge()
    print("重新提取 %d 课" % n)


def merge():
    """把 text/ 下的每课合并成 全文.txt 与 目录.txt。"""
    parts, toc = [], []
    for n in range(1, 109):
        p = os.path.join(TXT, "lesson-%03d.txt" % n)
        if not os.path.exists(p):
            continue
        t = open(p, encoding="utf-8").read()
        _ls=[l for l in t.split("\n") if l.strip()]
        # 每课开头两行都以「教你炒股票」起头：「教你炒股票 第N课」「教你炒股票 N：课名」，取带课名的那行
        title = next((l for l in _ls[:3] if re.match(r"教你炒股票 \d+：", l)),
                     next((l for l in _ls[:3] if l.startswith("教你炒股票 ")), _ls[0] if _ls else ""))
        toc.append("%03d  %s" % (n, title))
        parts.append("\n\n" + "=" * 70 + "\n【第 %d 课】%s\n%s\n" % (n, title, t))
    open(os.path.join(BASE, "全文.txt"), "w", encoding="utf-8").write("".join(parts))
    open(os.path.join(BASE, "目录.txt"), "w", encoding="utf-8").write("\n".join(toc))
    size = os.path.getsize(os.path.join(BASE, "全文.txt"))
    print("全文 %.1f KB" % (size / 1024))


if __name__ == "__main__":
    reparse() if "--reparse" in sys.argv else main()
