# Vue2 → Vue3 升级影响分析 — 使用逻辑总览

> 受众：Skill 维护/扩展者与操作者。  
> 基准：`vue2-to-vue3-upgrade-impact-analysis/SKILL.md` + `references/*`。  
> 语言：正文简体中文；枚举、包名、路径、命令保持英文原文。

本 Skill **只做证据驱动的决策包（Stage A）**，不做实施。与其他 Skill **解耦**。  
`analysis_status=complete` / `batch_implementation_gate=ready` **≠** 可改代码、可装依赖、可发布。

---

## 1. 一句话心智模型

Agent：preflight → 仓画像 → 推荐路径（含三轴）→ 子系统清单 → **当场**确认队列（Wave 1 路径，Wave 2 High/blocker / `required_for_path=yes`）→ 决策落盘 → 校验 → `analysis_status=complete`。

| 轴 | 问题 | 取值 |
|---|---|---|
| `analysis_status` | 分析材料是否闭环？ | `partial` / `blocked` / `complete` |
| `decision_status` | 人是否已确认？ | `needs_choice` / `not_needed` / `decided` |
| `batch_implementation_gate` | 可否交给**实施规划**（handoff only）？ | `frozen` / `ready` |
| `implementation_readiness` | 本 Skill 是否评估过可实施性？ | 固定 `not_assessed` |
| 实施授权 | 是否允许改代码/装依赖？ | **否**；须另授权 |

`batch_implementation_gate=ready` 额外要求：§1 `lockfile_status: present`；每个 High/blocker 与每个 `required_for_path=yes` 均为 `decided`（`deferred` 只允许 `complete`+`frozen`）。

---

## 2. 默认推荐路径与三轴

默认 path id：`compat-big-bang`。  
§3 必须同时写出：

- `runtime_axis:` `compat` / `direct-vue3`
- `build_axis:` `vite` / `cli5-webpack5` / `existing-vite`
- `topology_axis:` `single-cutover` / `coexist`

三轴须与 path preset 一致；非默认组合走 Wave 1 `other` 或改选匹配 path id。  
Composition API 全仓重写：**另立项，本次不评估工作量**。  
迁移工具：**只点名、不执行**（Name, never run）。

---

## 3. 入口与报告目录

| 入口 | 用法 |
|---|---|
| 单仓 workspace | 给出项目根 / workspace |
| 多仓 inventory | 先巡检候选表，人选批次后再出完整决策包 |

报告目录解析：显式 `--output-dir` → 既有 change 的 `evidence/vue2-to-vue3-upgrade/` → 唯一 openspec change → 默认候选 `<project-root>/.vue2-to-vue3-upgrade-analysis`（须 `confirm:output-dir` 后才写）。  
`report_path` 禁止单独 `.`；须与实际报告目录 resolve 等价。

---

## 4. 常用命令

```shell
cd vue2-to-vue3-upgrade-impact-analysis
python scripts/preflight.py --project-root <app> --json
python scripts/profile_inventory.py --project-root <app> --json
python scripts/validate_report.py fixtures/valid-report.md
python scripts/validate_report.py --evidence-dir fixtures/evidence-complete
python -m unittest discover -s tests -v
```

---

## 5. 确认队列

1. Wave 1：`proceed:path:<id>` / `defer` / `other`（并复述三轴）  
2. Wave 2：每个 High/blocker 与 `required_for_path=yes`：`proceed:subsystem:<id>` / `defer` / `other`（同波）  
「继续 / 全部放行 / 别再问了」**不是** proceed token；须 verbatim 菜单。  
报告须含 `evidence_as_of`（`YYYY-MM-DD`），标记证据采集日。

---

## 6. 相关文档

- 调研摘要：[`vue2-to-vue3-migration-research.md`](./vue2-to-vue3-migration-research.md)  
- 可选 delivery 软挂载：[`vue2-to-vue3-upgrade-delivery-usage.md`](./vue2-to-vue3-upgrade-delivery-usage.md)
