"""第三格（界）的验收断言：`dtype` **抛 `AttributeError`** 者，必须与 **真的没有 `dtype`** 者
**屏上逐字同脸**（@nova-8980 裁定 §五 ①'③）。

两边的对象**故意同名**（用 `type()` 造两个都叫 `V` 的类）：`ContractError` 那条消息里带
`type(im).__name__`，类名不同的话差异会被"类名"污染、而不是"脸"。同名 ⇒ 一切差异只能来自判据。

用法：python3 -B faces_third_cell.py <cardfit.py 路径>
"""
import importlib.util, re, sys

_norm = lambda s: re.sub(r"0x[0-9a-f]+", "<addr>", s)   # 对象 repr 里的地址是噪声，不是脸

spec = importlib.util.spec_from_file_location("cf", sys.argv[1])
cf = importlib.util.module_from_spec(spec); spec.loader.exec_module(cf)


def _v(has_dtype_prop, n):
    """两个都叫 `V` 的类：一个**没有** dtype；一个 dtype 属性**自己抛 AttributeError**。"""
    ns = {"__index__": lambda self: n}
    if has_dtype_prop:
        def _boom(self): raise AttributeError("模拟：dtype 抛 AttributeError")
        ns["dtype"] = property(_boom)
    return type("V", (), ns)()


I = type("I", (), {})          # 两边同一个"图"类名


def face(obj):
    try:
        return "放行 W=%r H=%r" % (cf.assert_card(obj).width, cf.assert_card(obj).height)
    except Exception as e:
        return "%s: %s" % (type(e).__name__, e)


runs = [
    ("合格 __index__（=5）", lambda: I()),
    ("不合格 __index__（=-1）", lambda: I()),
]
print("== 第 ① 对：__index__ 合格（两边都该「放行」）")
im = runs[0][1](); im.width = _v(False, 5); im.height = _v(False, 5)
a = face(im)
im2 = runs[0][1](); im2.width = _v(True, 5); im2.height = _v(True, 5)
b = face(im2)
print("  真没 dtype   : %s" % a)
print("  dtype 抛 AE  : %s" % b)
print("  ⇒ 逐字同（地址归一后）: %s" % (_norm(a) == _norm(b)))

print("== 第 ② 对：__index__ 不合格（两边都该「不是正整数」）")
im3 = I(); im3.width = _v(False, -1); im3.height = _v(False, -1)
c = face(im3)
im4 = I(); im4.width = _v(True, -1); im4.height = _v(True, -1)
d = face(im4)
print("  真没 dtype   : %s" % c)
print("  dtype 抛 AE  : %s" % d)
print("  ⇒ 逐字同（地址归一后）: %s" % (_norm(c) == _norm(d)))
