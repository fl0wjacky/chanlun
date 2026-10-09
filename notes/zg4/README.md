# 总纲④ 给小栋那页的三张图（只看，不合）

在仓库根目录跑，`LIVE15` 指向 10-07 快照那 15 张（gzip JSON），引擎只读：

- `eng.py`：五条整体要求逐条计数
- `cost.py`、`extra.py`：三件各自 A／B 的代价
- `d20replay.py`：D2-0 标准化线段的前缀回放，在每一笔终点后一根取前缀
- `figs.py <输出目录>`：画三张图
  - `zg4-1-retract.png`：AAPLUSDT 15m H 345.38，撤回前、撤回后
  - `zg4-2-twosets.png`：data/zec_4h，原始线段和标准化线段叠在一起
  - `zg4-3-centers.png`：AAPLUSDT 15m 第 4 段，7 个中枢
