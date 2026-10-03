#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""静态资源版本号检查：页面引用的每个本地 JS/CSS 都带 v，v 跟着内容走，缓存头对。

    python3 web/check_assets.py              # rc=0 才算过
    python3 web/check_assets.py --self-test  # 三条变异必须各自红

背景：Cloudflare 把 .js/.css 的浏览器缓存改写成 4 小时、边缘也缓存 ⇒ 不带版本号的 URL 前端一更新就旧
（Nova 10-03 外测：不带参数取 /app.js 拿到的是两个提交前的版本）。web/server.py 在送页面时把引用改写成
`x.js?v=<送出字节的 sha256 前 10 位>`。这里逐格核：
  ① index.html 不带参数取：no-cache；
  ② 从 index.html 顺着 src/href、JS 的 import 走完整个闭包：每个本地引用都带 v（漏一个就红）；
  ③ 每个带 v 的 URL：200、immutable、v == 送出字节的 hash、去掉 ?v=… 之后与磁盘上的文件逐字节相同；
  ④ 不带 v / v 不对：no-cache（不许占长缓存）；
  ⑤ 版本号跟着内容走（在 web/ 的临时副本上改文件）：改 theme.js ⇒ theme / app / layers / index 的 v 全变、
     style / vendor 不变；改 vendor ⇒ 只有 vendor 和 index 变。
"""
import contextlib
import hashlib
import os
import re
import shutil
import sys
import tempfile
import threading
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import server                                           # noqa: E402

REF = re.compile(r'''(?:\s(?:src|href)=|\bfrom\s*|\bimport\s*)["']([^"'#:]+\.(?:js|css))(?:\?v=([0-9a-f]+))?["']''')
VTAG = re.compile(rb"\?v=[0-9a-f]+")


@contextlib.contextmanager
def running(static=None):
    saved = server.STATIC
    if static:
        server.STATIC = static
    srv = server.make_server(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield srv.server_address[1]
    finally:
        srv.shutdown()
        srv.server_close()
        server.STATIC = saved


def get(port, path):
    with urllib.request.urlopen("http://127.0.0.1:%d/%s" % (port, path.lstrip("/")), timeout=10) as r:
        return r.status, r.headers.get("Cache-Control", ""), r.read()


def closure(port):
    """从 index.html 走完引用闭包 → {相对路径: v 或 None}。"""
    seen, todo = {}, [("index.html", None)]
    while todo:
        rel, _ = todo.pop()
        _, _, body = get(port, rel if rel != "index.html" else "/")
        base = os.path.dirname(rel)
        for ref, v in REF.findall(body.decode("utf-8")):
            dep = os.path.normpath(os.path.join(base, ref))
            if dep not in seen:
                seen[dep] = v or None
                if dep.endswith(".js") and not dep.startswith("vendor/"):
                    todo.append((dep, v))
    return seen


def versions(static):
    with running(static) as port:
        return closure(port), get(port, "/")[2]


def check(cell):
    with running() as port:
        code, cache, _ = get(port, "/")
        cell("① index.html：no-cache", code == 200 and cache == "no-cache", "%s %r" % (code, cache))
        refs = closure(port)
        bare = sorted(r for r, v in refs.items() if not v)
        cell("② 引用闭包 %d 个本地资源全带 v" % len(refs), refs and not bare, "没带 v：%s" % bare if bare else
             "、".join(sorted(refs)))
        bad = []
        for rel, v in refs.items():
            if not v:
                continue
            code, cache, body = get(port, "%s?v=%s" % (rel, v))
            disk = open(os.path.join(server.STATIC, rel), "rb").read()
            if code != 200 or "immutable" not in cache:
                bad.append("%s 缓存头 %r" % (rel, cache))
            if hashlib.sha256(body).hexdigest()[:10] != v:
                bad.append("%s v 不是送出字节的 hash" % rel)
            if VTAG.sub(b"", body) != disk:
                bad.append("%s 去掉 ?v= 后跟磁盘不同" % rel)
        cell("③ 带 v 的 URL：immutable、v=送出字节 hash、去 v 后与磁盘逐字节同", not bad, " ｜ ".join(bad[:4]))
        c1 = get(port, "app.js")[1]
        c2 = get(port, "app.js?v=0000000000")[1]
        cell("④ 不带 v / 旧 v：no-cache", c1 == c2 == "no-cache", "不带 %r · 旧 %r" % (c1, c2))

    tmp = tempfile.mkdtemp(prefix="assetver-")
    try:
        copy = os.path.join(tmp, "web")
        shutil.copytree(server.STATIC, copy, ignore=shutil.ignore_patterns("__pycache__"))
        v0, i0 = versions(copy)
        with open(os.path.join(copy, "theme.js"), "a", encoding="utf-8") as f:
            f.write("\n// probe\n")
        v1, i1 = versions(copy)
        changed = sorted(k for k in v0 if v0[k] != v1.get(k))
        want = sorted(k for k in v0 if k in ("theme.js", "app.js", "layers.js"))
        cell("⑤ 改 theme.js ⇒ theme/app/layers 的 v 变、其余不变、index 变", changed == want and i0 != i1,
             "变了：%s" % changed)
        vend = [k for k in v0 if k.startswith("vendor/")]
        with open(os.path.join(copy, vend[0]), "ab") as f:
            f.write(b"\n// probe\n")
        v2, i2 = versions(copy)
        changed = sorted(k for k in v1 if v1[k] != v2.get(k))
        cell("   ⑤ 改 vendor ⇒ 只有 vendor 的 v 变、index 变", changed == vend and i1 != i2, "变了：%s" % changed)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    bad = []

    def cell(name, ok, note=""):
        print("%s %-46s %s" % ("✓" if ok else "✗", name, note))
        if not ok:
            bad.append(name)
    check(cell)
    print("%d 格不过" % len(bad) if bad else "全部通过")
    return 1 if bad else 0


def self_test():
    """三种改坏：不改写引用 ／ 版本号是常数 ／ 任何 v 都给 immutable —— 各自必须红。"""
    import importlib
    import io

    def no_rewrite():
        real = server.served
        server.served = lambda full, _stack=(): (open(full, "rb").read(), real(full)[1])

    def const_ver():
        real = server.served
        server.served = lambda full, _stack=(): (real(full)[0], "0123456789")

    def any_v_immutable():
        server.cache_for = lambda ext, want, ver: ("no-cache" if ext == ".html"
                                                   else "public, max-age=31536000, immutable")

    miss = 0
    for name, f in [("不改写引用", no_rewrite), ("版本号是常数", const_ver), ("任何 v 都给 immutable", any_v_immutable)]:
        importlib.reload(server)
        f()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main()
        reds = [l.split()[1] for l in buf.getvalue().splitlines() if l.startswith("✗")]
        print("%s 变异 %-18s ⇒ rc=%d 红格 %s" % ("✓" if rc else "✗", name, rc, " ".join(reds)))
        miss += 0 if rc else 1
    importlib.reload(server)
    return 3 if miss else 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
