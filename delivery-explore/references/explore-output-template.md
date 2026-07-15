# 探索产出与交接模板

面向人的默认结构；正文可中文。机读键名保持与 handoff 块一致。

## 探索地图（非正式）

```text
## 探索结论（非正式）
证据模式：full | degraded
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

与 `handoff-template.md` 保持同构；机读键名见该文件英文对照。

```text
当前阶段：delivery-explore
状态源：none（探索非正式）
证据模式：full | degraded
能力快照（capability_snapshot）：
  memory: ok | stale-index | down
  openspec: initialized | cli-only | unavailable
  superpowers: loaded | partial(<缺失项>) | missing
已选方向：
非目标：
代码锚点：
风险信号提示：none | standard-likely | high-likely
未知项：
下一技能标识：delivery-frame-spec
下一阶段必需输入：用户确认将该方向作为本次变更目标（或修订后的目标表述）
停止条件：用户仅需建议、或拒绝进入 framing
```

## 与 framing 的最小差异检查

进入 `delivery-frame-spec` 前应能回答：

1. 用户是否已选定（或明确修订）一个方向？
2. 是否仍宣称“规格已批准”？（若是，删除该表述。）
3. 是否已创建正式状态源？（探索阶段必须为 none。）
4. 交接块是否含 `capability_snapshot`（与 `handoff-template.md` 一致）？
