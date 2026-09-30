# -*- coding: utf-8 -*-
"""数据边界预处理层：前复权 + 会话/停牌/除权断点检测。

插位置（Atlas spec docs/04_数据边界）：quantize → preprocess → standardize。
preprocess 不改K线形状（除前复权回调 h/l/o/c），额外产出 breaks 交给
standardize(bars, breaks=breaks) —— 断点两侧的K线永不合并。

三类断点来源：
    session_gap   会话断点：隔夜 / 周末 / 节假日（A股、港股用；加密永续 7×24 没有）
    halt          停牌：区间内没有K线，复牌第一根与停牌前最后一根不该算连续
    dividend      除权除息：未复权价在除权日不连续（跳空不是行情走出来的）

不变量 C（crypto 恒等，Atlas C1）：加密永续调用
    preprocess(bars, adjust="none", session=None)
必须等价恒等 —— breaks == [] 且 bars_adj == bars 逐字段相等。
任何对 preprocess 的重构把这条打破 = 回归。
"""


def preprocess(bars, *, adjust="auto", session=None):
    """骨架——恒等返回 (bars, [])，待断点来源的 fixture schema 定了再填真检测。

    现在是刻意不做事的：pipeline 可以先端到端接通（quantize → preprocess →
    standardize(bars, breaks=[])），行为与不插这一层时逐字节相同，crypto 回归
    基准（不变量 C）自动满足；真实检测逻辑接进来时再也不用动这一层之外的东西。

    为什么停在骨架：断点检测要判「两根K线之间是不是真的连续」，得有真实时间戳。
    现有 harness 喂的是 dict(t=i, ...)、t 是**位置下标**不是时间（Nova #96），
    真 ts 在解包时就丢了 —— schema 没定之前，任何检测实现都是在猜。

    adjust: "auto" / "none" / "qfq"（前复权）。"none" 必须恒等、不碰价格。
    session: 交易时段定义（None = 7×24 连续市场，无会话断点）。
    返回 (bars_adj, breaks)，breaks 形如 [{"i": 原始下标, "reason": "session_gap"}]。
    """
    return bars, []
