"""两张脸对照表：同一批对象 × 两版 cardfit（旧 blob 90631cce / 新工作区那份）。

量的是**屏上那一行**（`measure()` 印的 `★ **没量成**：<类型>: <消息>`，或 `W=… 放行`），
不是"抛没抛" —— 本卡要的就是脸。用法：python3 -B faces_probe.py <cardfit.py 路径> [标签]
"""
import importlib.util, sys

path, label = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
spec = importlib.util.spec_from_file_location("cf", path)
cf = importlib.util.module_from_spec(spec); spec.loader.exec_module(cf)


class Idx:
    def __init__(self, n): self.n = n
    def __index__(self): return self.n


class Boolish:                      # 自称布尔元素类型
    dtype = type("D", (), {"kind": "b"})()
    def __init__(self, n): self.n = n
    def __index__(self): return self.n


class DtypeBoom:                    # .dtype 自己抛 RuntimeError
    @property
    def dtype(self): raise RuntimeError("模拟：尺寸值自己的 .dtype 炸了")
    def __index__(self): return 5


class KindBoom:                     # dtype 有、但 .kind 自己抛
    class _D:
        @property
        def kind(self): raise RuntimeError("模拟：.kind 炸了")
    dtype = _D()
    def __index__(self): return 5


class IdxValueErr:                  # __index__ 自己抛 ValueError
    def __index__(self): raise ValueError("模拟：__index__ 自己炸了")


class DtypeAttrErr:                 # .dtype 自己抛 AttributeError，__index__ 合格
    @property
    def dtype(self): raise AttributeError("模拟：dtype 抛 AttributeError")
    def __index__(self): return 5


class Img:
    """假装 build() 交出来的东西。"""
    def __init__(self, w, h):
        self.width, self.height = w, h


class ImgBoom(Img):                 # .width 自己抛 RuntimeError
    def __init__(self, h): self.height = h
    @property
    def width(self): raise RuntimeError("模拟：图的 .width 炸了")


class ImgAttrErr(Img):              # .width 自己抛 AttributeError
    def __init__(self, h): self.height = h
    @property
    def width(self): raise AttributeError("模拟：图的 .width 抛 AttributeError")


CELLS = [
    ("①none      build 交回 None",        None),
    ("②strwh     width='7'",              Img("7", "7")),
    ("③duck      Idx(1400)/Idx(2080)",    Img(Idx(1400), Idx(2080))),
    ("④zero      width=0",                Img(0, 0)),
    ("⑤bool      width=True",             Img(True, True)),
    ("⑥自称布尔  kind='b'",                Img(Boolish(1400), Boolish(2080))),
    ("⑦Idx       Idx(1400)",              Img(Idx(1400), Idx(2080))),
    ("⑧dtype炸   RuntimeError",            Img(DtypeBoom(), DtypeBoom())),
    ("⑨kind炸    RuntimeError",            Img(KindBoom(), KindBoom())),
    ("⑩idx炸     ValueError",              Img(IdxValueErr(), IdxValueErr())),
    ("⑪dtype抛AE __index__=5",             Img(DtypeAttrErr(), DtypeAttrErr())),
    ("⑫图.width炸 RuntimeError",           ImgBoom(2080)),
    ("⑬图.width抛AE",                      ImgAttrErr(2080)),
]

print("### 版本：%s" % label)
for name, obj in CELLS:
    try:
        im = cf.assert_card(obj)
        face = "放行 W=%r H=%r" % (im.width, im.height)
    except Exception as e:
        face = "%s: %s" % (type(e).__name__, e)
    print("%-30s %s" % (name, face))
