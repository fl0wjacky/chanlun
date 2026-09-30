"""**方格：位点 × 异常类型** —— 走真 `assert_card`，逐格印脸（@nova-8980 §四 ①'' 要的那张表）。

为什么要方格：`except` 的射程是**代码**的属性、不是**异常类型**的属性 ⇒ 只在"异常类型"这一维上取样，
  一条 `except` 盖宽了，探针一格都照不出来（`card-8ce1d0ca-087` 上两版实现同时漏掉的两格）。

位点（4 个）：① `.dtype` 自己抛 ② `.dtype.kind` 自己抛 ③ `__index__` 自己抛 ④ 图自己的 `.width` 抛
类型（3 类）：`TypeError` · `AttributeError` · `RuntimeError`（"其余"的代表）

用法：python3 -B faces_grid.py <cardfit.py 路径> [<路径> …]   ⇒ 一列一个版本，行可逐格比。
"""
import importlib.util
import re
import sys

_norm = lambda s: re.sub(r"0x[0-9a-f]+", "<addr>", s)   # 对象 repr 里的地址是噪声，不是脸
_EXCS = [("TypeError", TypeError("炸了")),
         ("AttributeError", AttributeError("炸了")),
         ("RuntimeError", RuntimeError("炸了"))]


def load(path, tag):
    spec = importlib.util.spec_from_file_location("cf_" + tag, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _prop(exc):
    def f(self):
        raise exc
    return property(f)


def _v_dtype_boom(exc):          # ① `.dtype` 自己抛（`__index__` 好好的 = 5）
    return type("V", (), {"__index__": lambda self: 5, "dtype": _prop(exc)})()


def _v_kind_boom(exc):           # ② `dtype` 取得到，`.kind` 自己抛
    d = type("D", (), {"kind": _prop(exc)})()
    return type("V", (), {"__index__": lambda self: 5, "dtype": d})()


def _v_idx_boom(exc):            # ③ `__index__` 自己抛（没有 dtype）
    return type("V", (), {"__index__": lambda self: (_ for _ in ()).throw(exc), "dtype": None})()


def _img_width_boom(exc):        # ④ 图自己的 `.width` 抛（`.height` 正常 = 10）
    return type("Im", (), {"width": _prop(exc), "height": 10})()


def _img_plain(w, h):            # 对照：一副正常的图
    return type("Im", (), {"width": w, "height": h})()


ROWS = []                        # (行名, 造对象)
for _tn, _e in _EXCS:
    ROWS.append(("①.dtype 抛 %s" % _tn, (lambda e=_e: _img_plain(_v_dtype_boom(e), 5))))
    ROWS.append(("②.dtype.kind 抛 %s" % _tn, (lambda e=_e: _img_plain(_v_kind_boom(e), 5))))
    ROWS.append(("③__index__ 抛 %s" % _tn, (lambda e=_e: _img_plain(_v_idx_boom(e), 5))))
    ROWS.append(("④图.width 抛 %s" % _tn, (lambda e=_e: _img_width_boom(e))))
ROWS.append(("对照 真没 dtype · idx=5", lambda: _img_plain(type("V", (), {"__index__": lambda self: 5})(), 5)))
ROWS.append(("对照 自称布尔 dtype.kind='b'", lambda: _img_plain(type("V", (), {"__index__": lambda self: 5, "dtype": type("D", (), {"kind": "b"})()})(), 5)))
ROWS.append(("对照 Python bool", lambda: _img_plain(True, 5)))
ROWS.append(("对照 普通非整数（'7'）", lambda: _img_plain("7", 5)))
ROWS.append(("对照 零（0）", lambda: _img_plain(0, 5)))


def face(m, im):
    try:
        got = m.assert_card(im)
        return "放行 W=%r H=%r" % (got.width, got.height)
    except Exception as e:
        return "%s: %s" % (type(e).__name__, e)


paths = sys.argv[1:]
mods = [load(p, str(i)) for i, p in enumerate(paths)]
cols = []
for name, make in ROWS:
    cols.append((name, [_norm(face(m, make())) for m in mods]))

print("== 方格：位点 × 异常类型（走真 assert_card；地址已归一）")
for p in paths:
    print("   列：%s" % p)
print()
for name, faces in cols:
    same = len(set(faces)) == 1
    print("%-34s %s" % (name, ("逐字同  " + faces[0]) if same else " | ".join(faces)))
    if not same:
        for p, f in zip(paths[1:], faces[1:]):
            if f != faces[0]:
                print("%-34s   ↳ vs 第 1 列：%s" % ("", f[:160]))
