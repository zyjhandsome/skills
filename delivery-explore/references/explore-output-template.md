# 探索产出与交接模板

面向人的默认结构；正文可中文。机读键名保持与 handoff 块一致。

## 探索地图（非正式）

```text
## 探索结论（非正式）
证据模式：full | degraded
方向对齐状态：selected | needs_choice
代码锚点：

### 方向清单
1. <名称> — <一句话价值>
   证据：
   大致影响面：
   风险信号：none | standard-likely | high-likely

### 非目标（本次探索不建议碰）

### 未知项

### 推荐
首选：
备选：
```

## 交接块

使用 `handoff-template.md` 输出一个完整、有效的 `delivery-handoff/v1` JSON 对象。公共字段遵守 `../../delivery-frame-spec/references/handoff-contract.md`；方向、非目标、锚点、风险信号和未知项写入 `stage_payload`，不要再输出平行的伪 YAML 交接块。

## 与 framing 的最小差异检查

进入 `delivery-frame-spec` 前应能回答：

1. `chosen_direction` 是否用用户语义写清一个候选方向及其目标价值？
2. 会改变方向选择的分叉是否均已决定？若否，`direction_alignment` 必须为 `needs_choice`。
3. 已知边界是否进入 `non_goals`，其余产品细节是否作为 `unknowns` 交给 framing？
4. 是否仍宣称“规格已批准”？（若是，删除该表述。）
5. 是否已创建正式状态源？（探索阶段必须为 none。）
6. 交接 JSON 是否含 `capability_snapshot`、`presentation_capability` 和完整 `stage_payload`，并通过严格解析？

只有 `direction_alignment: selected` 才输出进入 `delivery-frame-spec` 的交接；`needs_choice` 应继续 explore 澄清，或在用户只需建议时结束。
