#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""静态扫「用了但没定义的名字」—— **不跑代码**，只读 AST。

守的这一格（card-6adfd2c9-dca）：`tools/selfcheck.py:250` 的 `ROOT` 是个 **NameError**，
但它的触发条件写在 `if _skipped:` 里面 —— **干净树上永远不跑**，只有"仓库里有个文件读不成"
时才炸，而那一刻报出来的又是「查不了」而不是「哪一行没定义」。**这种 bug 靠跑是跑不出来的**
（本仓没有 CI，`pyflakes` / `flake8` 都没装、且实测 `pip install pyflakes` 装不上 ⇒
这件事只有这一条路，或者不做）。

    python3 tools/undef_scan.py                 # 扫本仓（分母 git ls-files '*.py'）
    python3 tools/undef_scan.py --selftest      # 判据前提自测：八个探针，全格对才 rc=0
    python3 tools/undef_scan.py <仓库根> [文件...]   # 指定分母（探针用）

★ **边界写死在这里，不许当默认值猜**（写了就得认）：

  认：
    · 模块级 / 函数（含嵌套 def、lambda）/ 推导式，各自一个作用域，名字按词法链向上找
    · `from X import *` 按**被导入模块的模块级绑定**展开（含相对导入）
    · 算作绑定的：形参（含 *args / **kw / kwonly）、赋值、推导式目标、except as、with as、
      for 目标、import as、walrus（绑定到最近的函数/模块作用域）、global / nonlocal 声明
    · 模块级 = **模块顶层语句树里的任何位置**（含写在 if / try / for 里的），
      不以 `col_offset` 判 —— 那是"我判'模块级'的判据"≠"什么叫模块级"（本仓 @nova-8980
      第一版就栽在这：拿 `col_offset == 0` 当门，把写在 try/if 里的 import 全滤掉 ⇒ 满屏假报）
  不认（**这格子对它们是瞎的**）：
    · `exec` / `eval` / `getattr` / `globals()` 这类**动态取的名**
    · 「一个 if 分支里先定义、另一个分支里先用」—— 那是 UnboundLocalError，另一种病，别混进来
    · 类体**不是**方法的外层作用域（Python 就是这么定的）：方法里引用类体里的名字 ⇒ **报，这是对的**

★ 两个数分开印，**不许加和**（单位不同，本仓 ⑮ 那条）：
    UNDEF   = 用了但没定义的名字，单位 **处**
    SKIPPED = 没扫成的文件（解析不了 / 读不了），单位 **个文件**
  没扫成的文件**不进** UNDEF 的分母（本仓 ⑬ 那条：`except SyntaxError: continue` 让成员从分母里
  整张消失，而报告照印一个正常的数 —— 比"扫到 0"更安静）⇒ 有 SKIPPED 时「0 处」不许当通过。
"""
import ast
import builtins
import os
import subprocess
import sys
import tempfile

# 模块自带的隐式全局（不是谁写的，别报）
IMPLICIT = {
    "__name__", "__file__", "__doc__", "__builtins__", "__spec__",
    "__package__", "__loader__", "__path__", "__cached__",
}
BUILTINS = set(dir(builtins)) | IMPLICIT

SCOPE_MODULE = "module"
SCOPE_FUNC = "function"
SCOPE_CLASS = "class"
SCOPE_COMP = "comprehension"

DIVIDE_BY = "git ls-files '*.py'"


class Scope:
    def __init__(self, kind, node, parent):
        self.kind = kind
        self.node = node
        self.parent = parent
        self.bound = {}          # name -> lineno
        self.uses = []           # (name, lineno, col)
        self.declared_global = set()
        self.declared_nonlocal = set()
        self.star_from = []      # [(module, level, node)]

    def bind(self, name, lineno):
        self.bound.setdefault(name, lineno)

    def add_use(self, name, lineno, col):
        self.uses.append((name, lineno, col))


class Builder:
    def __init__(self, path, tree):
        self.path = path
        self.tree = tree
        self.scopes = []
        self.module = Scope(SCOPE_MODULE, tree, None)
        self.scopes.append(self.module)

    # ---------- 作用域与绑定 ----------

    def visit_body(self, stmts, scope):
        for st in stmts:
            self.visit_stmt(st, scope)

    def visit_stmt(self, node, scope):
        cls = type(node).__name__

        if cls in ("FunctionDef", "AsyncFunctionDef"):
            scope.bind(node.name, node.lineno)
            for d in node.decorator_list:
                self.visit_expr(d, scope)
            self.bind_args_defaults(node.args, scope)
            inner = Scope(SCOPE_FUNC, node, scope)
            self.scopes.append(inner)
            self.bind_args(node.args, inner)
            if node.returns is not None:
                self.visit_expr(node.returns, scope)
            self.visit_body(node.body, inner)
            return

        if cls == "ClassDef":
            scope.bind(node.name, node.lineno)
            for d in node.decorator_list:
                self.visit_expr(d, scope)
            for b in node.bases:
                self.visit_expr(b, scope)
            for k in node.keywords:
                self.visit_expr(k.value, scope)
            inner = Scope(SCOPE_CLASS, node, scope)
            self.scopes.append(inner)
            self.visit_body(node.body, inner)
            return

        if cls in ("Import", "ImportFrom"):
            self.bind_import(node, scope)
            return

        if cls in ("Global", "Nonlocal"):
            tgt = scope.declared_global if cls == "Global" else scope.declared_nonlocal
            tgt.update(node.names)
            return

        if cls == "Assign":
            self.visit_expr(node.value, scope)
            for t in node.targets:
                self.bind_target(t, scope)
            return

        if cls == "AnnAssign":
            if node.value is not None:
                self.visit_expr(node.value, scope)
            if node.annotation is not None:
                self.visit_expr(node.annotation, scope)
            self.bind_target(node.target, scope)
            return

        if cls == "AugAssign":
            # `x += 1` —— 既是读也是写；按"写"算，不当未定义报（否则满屏假报）
            self.visit_expr(node.value, scope)
            self.bind_target(node.target, scope)
            return

        if cls in ("For", "AsyncFor"):
            self.visit_expr(node.iter, scope)
            self.bind_target(node.target, scope)
            self.visit_body(node.body, scope)
            self.visit_body(node.orelse, scope)
            return

        if cls in ("With", "AsyncWith"):
            for item in node.items:
                self.visit_expr(item.context_expr, scope)
                if item.optional_vars is not None:
                    self.bind_target(item.optional_vars, scope)
            self.visit_body(node.body, scope)
            return

        if cls in ("Try", "TryStar"):
            self.visit_body(node.body, scope)
            for h in node.handlers:
                if h.type is not None:
                    self.visit_expr(h.type, scope)
                if h.name:
                    scope.bind(h.name, h.lineno)
                self.visit_body(h.body, scope)
            self.visit_body(node.orelse, scope)
            self.visit_body(node.finalbody, scope)
            return

        if cls == "Return":
            if node.value is not None:
                self.visit_expr(node.value, scope)
            return

        if cls == "Raise":
            if node.exc is not None:
                self.visit_expr(node.exc, scope)
            if node.cause is not None:
                self.visit_expr(node.cause, scope)
            return

        if cls in ("Expr", "Delete", "Assert"):
            for child in ast.iter_child_nodes(node):
                self.visit_expr(child, scope)
            return

        if cls == "Match":
            self.visit_expr(node.subject, scope)
            for case in node.cases:
                self.visit_pattern(case.pattern, scope)
                if case.guard is not None:
                    self.visit_expr(case.guard, scope)
                self.visit_body(case.body, scope)
            return

        # 其余语句：走通用遍历（if/while/嵌套块都由 stmt 列表键处理）
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.stmt):
                        self.visit_stmt(item, scope)
                    elif isinstance(item, ast.expr):
                        self.visit_expr(item, scope)
            elif isinstance(value, ast.stmt):
                self.visit_stmt(value, scope)
            elif isinstance(value, ast.expr):
                self.visit_expr(value, scope)

    def bind_args_defaults(self, args, scope):
        for d in list(args.defaults) + [d for d in args.kw_defaults if d is not None]:
            self.visit_expr(d, scope)
        for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
            if a.annotation is not None:
                self.visit_expr(a.annotation, scope)
        if args.vararg and args.vararg.annotation is not None:
            self.visit_expr(args.vararg.annotation, scope)
        if args.kwarg and args.kwarg.annotation is not None:
            self.visit_expr(args.kwarg.annotation, scope)

    def bind_args(self, args, scope):
        for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
            scope.bind(a.arg, a.lineno if hasattr(a, "lineno") else 0)
        if args.vararg:
            scope.bind(args.vararg.arg, 0)
        if args.kwarg:
            scope.bind(args.kwarg.arg, 0)

    def bind_target(self, node, scope):
        cls = type(node).__name__
        if cls == "Name":
            scope.bind(node.id, node.lineno)
        elif cls in ("Tuple", "List"):
            for e in node.elts:
                self.bind_target(e, scope)
        elif cls == "Starred":
            self.bind_target(node.value, scope)
        # Attribute / Subscript 不是绑定

    def bind_import(self, node, scope):
        if isinstance(node, ast.Import):
            for a in node.names:
                scope.bind(a.asname or a.name.split(".")[0], node.lineno)
        else:
            for a in node.names:
                if a.name == "*":
                    scope.star_from.append((node.module, node.level, node))
                else:
                    scope.bind(a.asname or a.name, node.lineno)

    def visit_pattern(self, pat, scope):
        cls = type(pat).__name__
        if cls == "MatchAs":
            if pat.name:
                scope.bind(pat.name, pat.lineno)
            if pat.pattern is not None:
                self.visit_pattern(pat.pattern, scope)
        elif cls == "MatchStar":
            if pat.name:
                scope.bind(pat.name, pat.lineno)
        elif cls == "MatchMapping":
            for k in pat.keys:
                self.visit_expr(k, scope)
            for p in pat.patterns:
                self.visit_pattern(p, scope)
            if pat.rest:
                scope.bind(pat.rest, pat.lineno)
        elif cls in ("MatchSequence", "MatchOr"):
            for p in pat.patterns:
                self.visit_pattern(p, scope)
        elif cls == "MatchClass":
            self.visit_expr(pat.cls, scope)
            for p in list(pat.patterns) + list(pat.kwd_patterns):
                self.visit_pattern(p, scope)
        elif cls == "MatchValue":
            self.visit_expr(pat.value, scope)

    def visit_expr(self, node, scope):
        if node is None:
            return
        cls = type(node).__name__

        if cls == "Name":
            if isinstance(node.ctx, ast.Load):
                scope.add_use(node.id, node.lineno, node.col_offset)
            return

        if cls == "Lambda":
            self.bind_args_defaults(node.args, scope)
            inner = Scope(SCOPE_FUNC, node, scope)
            self.scopes.append(inner)
            self.bind_args(node.args, inner)
            self.visit_expr(node.body, inner)
            return

        if cls in ("ListComp", "SetComp", "DictComp", "GeneratorExp"):
            inner = Scope(SCOPE_COMP, node, scope)
            self.scopes.append(inner)
            for gen in node.generators:
                self.visit_expr(gen.iter, inner)
                self.bind_target(gen.target, inner)
                for cond in gen.ifs:
                    self.visit_expr(cond, inner)
            if isinstance(node, ast.DictComp):
                self.visit_expr(node.key, inner)
                self.visit_expr(node.value, inner)
            else:
                self.visit_expr(node.elt, inner)
            return

        if cls == "NamedExpr":
            # walrus：绑定到最近的**非推导式**作用域
            self.visit_expr(node.value, scope)
            target = node.target
            host = scope
            while host is not None and host.kind == SCOPE_COMP:
                host = host.parent
            if isinstance(target, ast.Name) and host is not None:
                host.bind(target.id, target.lineno)
            return

        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                self.visit_expr(child, scope)
            elif isinstance(child, ast.stmt):
                self.visit_stmt(child, scope)

    # ---------- 解析 ----------

    def resolve(self, star_names):
        out = []
        for scope in self.scopes:
            for name, lineno, col in scope.uses:
                if name in scope.declared_global:
                    host = self.module
                else:
                    host = scope
                found = False
                while host is not None:
                    # ★ 类体**不是**方法的外层作用域（Python 就这么定的）：
                    #   只有**词法上直接**写在类体里的代码才看得见类体里的名字。
                    #   漏掉这一条就漏报 `class C: attr=1` / `def m: return attr`（真 NameError）。
                    if host.kind == SCOPE_CLASS and scope.kind != SCOPE_CLASS:
                        host = host.parent
                        continue
                    if name in host.bound:
                        found = True
                        break
                    if name in host.declared_nonlocal:
                        host = host.parent
                        continue
                    host = host.parent
                if found:
                    continue
                if name in BUILTINS:
                    continue
                if name in star_names.get(scope, ()) or name in star_names.get("module", ()):
                    continue
                out.append((lineno, col, name))
        out.sort()
        return out


def module_level_names(tree, path, root, seen):
    """一个模块的「模块级绑定」名字集合 —— 给 `from X import *` 展开用。"""
    scope = Scope(SCOPE_MODULE, tree, None)
    b = Builder(path, tree)
    b.module = scope
    b.scopes = [scope]
    # 只收模块级：不展开函数体（函数里绑的名字不是模块级）
    for st in tree.body:
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            scope.bind(st.name, st.lineno)
            continue
        b.visit_stmt(st, scope)
    return set(scope.bound)


def resolve_star(module, level, path, root, seen):
    if module is None:
        return set()
    parts = module.split(".")
    if level:
        base = os.path.dirname(path)
        for _ in range(max(level - 1, 0)):
            base = os.path.dirname(base)
        target = os.path.join(base, *parts) if parts != [""] else base
    else:
        target = os.path.join(root, *parts)

    out = set()
    for cand in (target + ".py", os.path.join(target, "__init__.py")):
        if os.path.isfile(cand):
            real = os.path.realpath(cand)
            if real in seen:
                return set()
            seen.add(real)
            try:
                src = open(cand, encoding="utf-8").read()
                sub = ast.parse(src, filename=cand)
            except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
                return set()
            names = module_level_names(sub, cand, root, seen)
            for st in sub.body:
                if isinstance(st, ast.ImportFrom):
                    for a in st.names:
                        if a.name == "*":
                            names |= resolve_star(st.module, st.level, cand, root, seen)
            return names
    return out


def scan_file(path, root):
    """→ (hits, None) 或 (None, 为什么没扫成)。hits = [(lineno, col, name)]"""
    try:
        src = open(path, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError) as e:
        return None, "%s: %s" % (type(e).__name__, e)
    except Exception as e:                      # 读文件这一步的意外也不许吞
        return None, "%s: %s" % (type(e).__name__, e)
    try:
        tree = ast.parse(src, filename=path)
    except (SyntaxError, ValueError) as e:
        return None, "SyntaxError: %s" % e
    except RecursionError as e:
        return None, "RecursionError: %s" % e

    b = Builder(path, tree)
    b.visit_body(tree.body, b.module)

    star_names = {}
    for scope in b.scopes:
        if scope.star_from:
            acc = set()
            for module, level, node in scope.star_from:
                acc |= resolve_star(module, level, path, root, set())
            star_names[scope] = acc
    star_names["module"] = star_names.get(b.module, set())

    return b.resolve(star_names), None


def git_py_files(root):
    """分母取法：**仓认的文件**，不用 find（find 会跟着工作区走，多扫少扫都没人知道）。"""
    # -z：路径原样、以 NUL 分隔。不加的话 git 默认 core.quotepath 会把非 ASCII 路径印成
    # "\347\273…" 这种带引号的八进制转义（selfcheck 永远 exit=1 就是它：那 4 个中文文件名打不开），
    # 而 .split() 还会把带空格的路径劈成两半。
    try:
        out = subprocess.run(["git", "-C", root, "ls-files", "-z", "*.py"], capture_output=True)
    except OSError as e:
        return None, "%s: %s" % (type(e).__name__, e)
    if out.returncode != 0:
        return None, out.stderr.decode("utf-8", "replace").strip()
    return [os.path.join(root, p) for p in out.stdout.decode("utf-8").split("\0") if p], None


def scan_paths(root, files):
    hits, skipped = [], []
    for p in files:
        for one in ([p] if not isinstance(p, list) else p):
            res, err = scan_file(one, root)
            if err is not None:
                skipped.append((one, err))
                continue
            for lineno, col, name in res:
                hits.append((one, lineno, col, name))
    hits.sort()
    skipped.sort()
    return hits, skipped


def show(p, root):
    """分母外的文件（探针）印**绝对路径** —— relpath 会印成一串 ../../..，读的人以为工具坏了。"""
    try:
        rel = os.path.relpath(p, root)
    except ValueError:
        return p
    return p if rel.startswith(os.pardir) else rel


# ---------------------------------------------------------------------------
# 判据前提自测：八个探针。
# 为什么要有它：这格子唯一的死法是**假报**（假红一次，之后没人信它），
# 另一个方向的死法是**真有 bug 看不见**（那这格子只是个安慰奖）。两个方向各要一条实测。
# 探针用字符串写在这里、跑到临时目录里 —— 不往仓里放 `.py`（那会进分母，把本格的 0 处弄红）。
# 同形先例：`tools/verify_notdef.py` 也是"不要字体文件、喂假对象"。
# ---------------------------------------------------------------------------
# (格子名, 期望命中数, 必须点到的名字 或 None, {文件名: 源码})
PROBES = [
    ("lambda 形参（含 *a / **k / kwonly / 默认值）", 0, None, {"p.py": (
        "f = lambda a, b=2, *c, d, **e: (a, b, c, d, e)\n"
        "g = lambda x: [y for y in x]\n"
        "f(1, 2, 3, d=4)\n"
    )}),
    ("嵌套函数体的局部量与形参", 0, None, {"p.py": (
        "def outer(a):\n"
        "    b = a + 1\n"
        "    def inner(c):\n"
        "        return a + b + c\n"
        "    return inner\n"
    )}),
    ("推导式目标（list/set/dict/gen + 嵌套 for）", 0, None, {"p.py": (
        "xs = [1, 2]\n"
        "a = [i for i in xs]\n"
        "b = {i for i in xs}\n"
        "c = {i: i for i in xs}\n"
        "d = list(i * j for i in xs for j in xs)\n"
        "e = [i for i in xs if i > 0]\n"
    )}),
    ("`from X import *` 进来的名字（含再引一个 X 里没有的 ⇒ 那个要报）", 1, "NOPE", {
        "config.py": "ROOT = '/tmp'\nDATA = {}\ndef build():\n    return 1\n",
        "p.py": "from config import *\nprint(ROOT, DATA, build())\nprint(NOPE)\n",
    }),
    ("模块级 try/except ImportError 里的 import", 0, None, {"p.py": (
        "try:\n"
        "    import json as J\n"
        "except ImportError:\n"
        "    J = None\n"
        "print(J)\n"
    )}),
    ("模块级 if 里的 import", 0, None, {"p.py": (
        "import sys\n"
        "if sys.version_info[0] >= 2:\n"
        "    import json as J2\n"
        "print(J2)\n"
    )}),
    ("★ 真形状①：`foo()` 而 foo 没定义", 1, "foo", {"p.py": "foo()\n"}),
    ("★ 真形状②：类体**不是**方法的外层作用域", 1, "attr", {"p.py": (
        "class C:\n"
        "    attr = 1\n"
        "    def m(self):\n"
        "        return attr\n"
    )}),
    ("★ 真形状③：解析不了的文件要进「没扫成」、不进那个 0", 1, "zz_bad", {
        "zz_bad.py": "def build(:\n    pass\n",
    }),
]


def run(verbose=False):
    """跑自测，返回**不过的格数**（0 = 全对）。接口照 `tools/verify_notdef.run`。

    不往仓里写任何东西：探针在临时目录里现造现扫，root 也指着那个临时目录。
    不 verbose 时**只印不过的格** —— 挂进 selfcheck 时那屏已经很长了，全对就不刷屏。
    """
    bad = 0
    for name, want, must_name, files in PROBES:
        d = tempfile.mkdtemp(prefix="undef_selftest_")
        for fn, src in files.items():
            with open(os.path.join(d, fn), "w", encoding="utf-8") as fh:
                fh.write(src)
        # 解析不了的探针：0 命中 **且** 正好 1 个没扫成 —— 两样都要对
        if must_name == "zz_bad":
            hits, skipped = scan_paths(d, [os.path.join(d, "zz_bad.py")])
            ok = (len(hits) == 0 and len(skipped) == 1)
            got = "命中 %d 处 · 没扫成 %d 个" % (len(hits), len(skipped))
        else:
            hits, skipped = scan_paths(d, [os.path.join(d, f) for f in sorted(files)])
            named = set(n for _, _, _, n in hits)
            ok = (len(hits) == want) and (must_name is None or must_name in named)
            got = "命中 %d 处" % len(hits) + ("" if want == len(hits) else "（期望 %d）" % want)
            if hits and verbose:
                got += " · " + "、".join("%s:%d 名字 '%s'" % (show(p, d), ln, n)
                                        for p, ln, _, n in hits)
        if not ok:
            bad += 1
        if verbose or not ok:
            print("  %s %-46s %s" % ("✓" if ok else "✗ 不过", name, got))
    if verbose:
        print("  （%d 个探针）" % len(PROBES))
    return bad


def selftest_paired(verbose=False):
    """门槛 ⑦：反例控制**同树同跑成对**，两个读数一起贴，不贴单边。

    A = 本仓原样（分母 git ls-files '*.py'）
    B = 同一棵树 + **一个仓外的探针文件**（`foo()`）—— 探针不进仓 ⇒ `git status` 照样是空的
    ⇒ 两次跑各自印自己的分母，读的人看得见 88 和 89 的差是怎么来的。
    """
    root = repo_root()
    base_files, err = git_py_files(root)
    if base_files is None:
        print("  ✗ 不过 成对读数：本仓分母取不到（%s）" % err)
        return 1
    a_hits, a_skip = scan_paths(root, base_files)

    d = tempfile.mkdtemp(prefix="undef_paired_")
    probe = os.path.join(d, "zz_probe_foo.py")
    with open(probe, "w", encoding="utf-8") as fh:
        fh.write("foo()\n")
    b_hits, b_skip = scan_paths(root, base_files + [probe])

    named = [h for h in b_hits if h[0] == probe]
    ok = (len(b_hits) == len(a_hits) + 1 and len(named) == 1 and named[0][3] == "foo")
    if verbose or not ok:
        print("  A 本仓原样        分母 %d 个 .py ⇒ 未定义名 %d 处 · 没扫成 %d 个" %
              (len(base_files), len(a_hits), len(a_skip)))
        print("  B 同树 + 1 个探针  分母 %d 个 .py ⇒ 未定义名 %d 处 · 没扫成 %d 个" %
              (len(base_files) + 1, len(b_hits), len(b_skip)))
        for p, ln, col, nm in b_hits:
            print("     ✗ %s:%d:%d  名字 '%s' 用了但没定义" % (show(p, root), ln, col, nm))
        print("  %s 成对断言：B 应比 A 正好多 1 处，且点名到探针里的 'foo'"
              % ("✓" if ok else "✗ 不过"))
    elif not verbose:
        print("  ✓ 成对读数：A 分母 %d ⇒ %d 处 ／ B 同树 +1 个 `foo()` 探针 ⇒ %d 处（点名到 'foo'）"
              % (len(base_files), len(a_hits), len(b_hits)))
    return 0 if ok else 1


def selftest_paths():
    """门槛 ⑧：分母取法认得「怪名字」—— 临时仓里放 2 个探针：中文文件名、带空格的文件名，
    各写一个未定义名。git_py_files 必须原样拿到这两条路径，扫出来正好是这两个名字、0 个没扫成。
    （修之前：中文名被 git 转义成 "\347…" 打不开、空格名被 split 劈开 ⇒ 这一格红。）"""
    d = tempfile.mkdtemp(prefix="undef_paths_")
    names = {"探针_中文名.py": "foo_cn", "with space.py": "bar_sp"}
    for fn, nm in names.items():
        with open(os.path.join(d, fn), "w", encoding="utf-8") as fh:
            fh.write("%s()\n" % nm)
    q = dict(capture_output=True)
    subprocess.run(["git", "-C", d, "init", "-q"], **q)
    subprocess.run(["git", "-C", d, "add", "."], **q)
    files, err = git_py_files(d)
    if files is None:
        print("  ✗ 不过 怪名字分母：临时仓取不到（%s）" % err)
        return 1
    hits, skipped = scan_paths(d, files)
    got = sorted(h[3] for h in hits)
    ok = sorted(os.path.basename(f) for f in files) == sorted(names) and got == sorted(names.values()) \
        and not skipped
    print("  %s 怪名字分母（中文 / 空格文件名）：拿到 %d 条路径、扫出 %s、没扫成 %d 个"
          % ("✓" if ok else "✗ 不过", len(files), got, len(skipped)))
    return 0 if ok else 1


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv):
    if "--selftest" in argv:
        print("=" * 72)
        raw = os.environ.get("UNDEF_SELFTEST_VERBOSE")
        bad = run(verbose=bool(raw))
        print("-" * 72)
        bad += selftest_paired()
        bad += selftest_paths()
        print("=" * 72)
        if bad:
            print("[判据前提] undef_scan 自测：**%d 格不过** ⇒ 这格子那份「0 处」不可读" % bad)
            return 1
        print("[判据前提] undef_scan 自测通过（%d 个探针 + 1 对成对读数 + 怪名字分母）" % len(PROBES))
        return 0

    if len(argv) >= 2 and not argv[1].startswith("-"):
        root = os.path.abspath(argv[1])
        files = [os.path.abspath(f) for f in argv[2:]]
        how = "给定文件"
        if not files:
            files, err = git_py_files(root)
            if files is None:
                print("查不了：分母取不到（git ls-files 失败：%s）" % err)
                print("[rc=2] 未定义名：查不了（分母都没拿到）")
                return 2
            how = DIVIDE_BY
    else:
        root = repo_root()
        files, err = git_py_files(root)
        if files is None:
            print("查不了：分母取不到（git ls-files 失败：%s）" % err)
            print("[rc=2] 未定义名：查不了（分母都没拿到）")
            return 2
        how = DIVIDE_BY

    hits, skipped = scan_paths(root, files)

    # 证据行：告诉读的人这个数是怎么量出来的（哪把尺、什么量法、分母是什么）
    print("[量法/对象] AST 静态解析（不跑代码）· 对象 用了但没定义的名字 · 分母 %s" % how)
    for p, lineno, col, name in hits:
        print("✗ %s:%d:%d  名字 '%s' 用了但没定义" % (show(p, root), lineno, col, name))
    for p, err in skipped:
        print("✗ %s  没扫成（%s）" % (show(p, root), err))
    print("扫了 %d 个 .py（分母：%s）" % (len(files), how))
    print("未定义名：%d 处" % len(hits))
    print("没扫成：%d 个文件" % len(skipped))

    if skipped and not hits:
        # 「查不出来」不许读成「没有」—— 它和「0 处」在纸面上必须不一样
        print("[rc=1] 未定义名：查不了（%d 个文件没扫成，结论不完整）" % len(skipped))
        return 1
    if hits:
        print("[rc=1] 未定义名：%d 处" % len(hits))
        return 1
    if skipped:
        print("[rc=1] 未定义名：0 处，但**有 %d 个文件没扫成** ⇒ 不许当通过" % len(skipped))
        return 1
    print("[rc=0] 未定义名：0 处（分母 %d 个文件全部扫成）" % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
