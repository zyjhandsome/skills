# Vue2 → Vue3 升级影响分析 × Delivery — 使用说明（可选）

> 受众：希望把本分析 Skill 挂到 `delivery-*` 脊柱上的维护者。  
> **本文件是可选软挂载说明。**  
> `vue2-to-vue3-upgrade-impact-analysis` Skill **正文不依赖、不引用** `delivery-*`。

---

## 0. 解耦原则

| 层 | 职责 |
|---|---|
| 本 Skill | 只读分析 → 确认队列 → `analysis_status=complete` + `batch_implementation_gate` |
| delivery-* | 定框 / 计划 / 实施 / 验证（另授权） |
| OpenSpec change | 生命周期与状态真相（若团队使用） |

Skill 终点 **不等于** delivery 实现闸门，更不等于可以改仓库。

---

## 1. 建议挂载顺序（调用方编排，非 Skill 内逻辑）

```text
（可选）探索 / 多仓巡检
        │ 挂载：本 skill 的 inventory 入口
        ▼
定框 / 规格（若使用 delivery-frame-spec）
        │ 挂载：本 skill 的 workspace 分析 + 确认队列 → complete
        ▼
计划任务（若使用 delivery-plan-tasks）
        │ 仅当 batch_implementation_gate=ready 且调用方授权
        ▼
实施验证（若使用 delivery-execute-verify）
        │ 显式 go 后才改依赖/代码；可点名本 skill 报告中的命名配方
```

---

## 2. 交接时建议携带的事实（由调用方复制，非强制 schema）

- `report_path`
- `analysis_status=complete`
- `batch_implementation_gate`
- 已确认的 `proceed:path:…` 与 `proceed:subsystem:…`
- 命名配方列表（仍由实施阶段执行，分析阶段未跑）
- Composition API 全仓重写：不在范围内

---

## 3. 独立使用

不使用 delivery 时：直接调用本 Skill → 产出决策包 → 人工另开实施即可。  
详见 [`vue2-to-vue3-upgrade-impact-analysis-usage.md`](./vue2-to-vue3-upgrade-impact-analysis-usage.md)。
