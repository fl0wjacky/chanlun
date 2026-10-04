# rust-chan 线段划分例子 —— 出处与许可

- 上游：https://github.com/chan2zen/rust-chan （分支 v2）
- 提交：`1d1cc067be6b636df8c78f89e71fe91ad7a3e220`（2026-02-23）
- 文件：`src/tests/forest_tests.rs`，sha256 `a33a10409a57c53c2175de62e50c987cddde09f29ec954198780d540e19751da`
- 许可：MIT，Copyright (c) 2023 chan2zen —— 原文照抄在同目录 `LICENSE`（sha256 `acec028232a070267cc32f2df74e4f071f3d1d2ffd441b27bc2101a6a522c518`）

## 搬了什么

只搬**测试数据**：每个 `go_*` 测试里的笔端点值、期望的 `State` 名、期望的段界数组，原样进 `forest_cases.json`。
**没有搬任何上游代码**（`Forest` 状态机等一行没抄）。上游 54 个测试函数里 `go_reverse_nostandard_fenxing` 是 `todo!()`，没有数据，跳过；其余 53 个全收。

## 怎么用

```
python3 tools/rustchan_cases.py                          # 离线对一遍（selfcheck 也跑它）
python3 tools/rustchan_cases.py --extract <上游 checkout> # 重新抽（先核上面那个 sha256，变了就停）
```

## 判定

- **逐位相同（46 个）**：我们的已确认段界 == 上游 `forest.indexes()`。
- **口径不同（7 个）**：全是同一个方向 —— **上游多切一刀、我们不切**（我们的已确认段界是上游的真子集）。分两类，每个例子在 json 里带 `why` 和逐条 `cite`（原文行号回本课核过）：
  - `backward`（go_124 / go_12214 / go_12224）：上游以「反向跌破段起点」终结线段；原文 L071:26-28「先破第一笔的开始位置 ⇒ 旧线段依然延续」、L078:39-41「直接新高或新低 ⇒ 加起来只算一个线段」。
  - `unconverged`（go_12311 / go_12321 / go_122114 / go_123124）：反向序列还没走出底分型就切；原文 L067:31-33 第二种情况须反向序列出现底分型，L077:71-74「线段必须被线段所破坏才能确定其完成」。
- 上游图注「C 点是否跌破 A 点对线段划分并无影响」与原文一致；上游代码的 backward 分支与它自己的图注相反（Atlas 10-03 对照第三轮）。
- 两边喂的是**同一组笔**（端点值原样当笔），所以分歧在线段终结规则，不在笔的口径。
