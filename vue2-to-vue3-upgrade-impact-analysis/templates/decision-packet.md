# Vue2 → Vue3 升级 — 决策包模板

> 填写后保存为 `vue2-to-vue3-upgrade-report.md`。  
> 状态枚举、包名、版本、路径、命令、URL 保持英文原文；表头与说明默认简体中文。

## 状态

| 字段 | 取值 |
|---|---|
| analysis_status | partial / blocked / complete |
| decision_status | needs_choice / not_needed / decided |
| batch_implementation_gate | frozen / ready |
| implementation_readiness | not_assessed |
| behavior_parity_required | yes / no |
| network_mode | online / offline / partial |
| report_path | 实际报告目录（禁止单独 `.`） |
| evidence_as_of | YYYY-MM-DD |
| schema | vue3-upgrade-report/v1 |
| producer | vue2-to-vue3-upgrade-impact-analysis |
| summary_path | 实际输出目录/upgrade-summary.json |
| visual_acceptance_required | yes / no |

**横幅：** （待补证据 / 待人工确认·下一动作=提问 / 分析完成·handoff only·实施需另授权）

## 1. 基线与假设

- 项目根路径：
- 前端 workspace：
- 环境前置：Node / package manager / Python（PASS 摘要）
- host_node_version:
- current_node_contract:（.nvmrc / .node-version / Volta / engines / CI / container / deploy）
- current_node_evidence:（区分声明与已知绿色基线）
- target_node_requirement:（精确目标版本的 engines.node 交集；保留完整联合范围）
- target_node_sources:（package@version → engines.node / no engines.node + 官方或 registry 证据）
- node_compatibility_status: compatible / upgrade-required / conflict / unknown
- node_transition_strategy: same-node / upgrade-before-vue / temporary-dual-node / blocked / undecided
- lockfile：`<path>` / 无 lockfile（无 lock 时 handoff gate 保持 frozen）
- lockfile_status: present / absent / unparsed
- evidence_as_of: YYYY-MM-DD（可与状态表一致复述）
- 构建变体 / 批次范围：
- 入口：workspace / inventory / host-port
- source_root:（host-port 必填 = A）
- implementation_target:（host-port 必填 = B）
- forbid_source_mutation: yes（host-port 必填）
- batch_scope: full-stack / page-closure
- 报告路径（解析结果）：
- 假设与限制：

## 2. 仓画像与依赖就绪度

| 包名 | 当前版本 | Vue3 就绪度 | 建议 | 证据 |
|---|---|---|---|---|

## 3. 推荐迁移路径

- 推荐路径 id：`compat-big-bang` / `direct-vue3` / `host-port-direct` / `microfrontend-coexist` / …
- runtime_axis: compat / direct-vue3
- build_axis: vite / cli5-webpack5 / existing-vite
- topology_axis: single-cutover / coexist / host-port
- 理由：
- 备选路径：
- Composition API 全仓重写：另立项，本次不评估工作量
- 命名配方（Name, never run）：…（本技能不执行；host-port 禁止 vue-compat 作主路径）

## 4. 子系统影响清单

| 子系统 | scope_status | 风险 | 就绪度 | required_for_path | 命名配方 | 说明 |
|---|---|---|---|---|---|---|

## 5. 分层影响分析

| 层级 | 文件/模块 | 事实或推断 | 所需变更（仅描述，不实施） | 风险 |
|---|---|---|---|---|

### ui_visual_risk（有视觉触发器时必填）

- triggers:
- legacy_selectors:
- css_entry_order:
- theme_and_teleport:
- tailwind_reset:
- primary_sample:
- secondary_sample:
- baseline_status:
- required_visual_states:
- recommended_next_action: run_visual_review / include_in_implementation_validation / no_action

## 6. 风险分级

| 项 | 分级 | 说明 | 上游链接 |
|---|---|---|---|

## 7. 确认队列

| 单元 | 类型 | 状态 | 问题 | 选项 |
|---|---|---|---|---|
| `path:compat-big-bang` 或 `path:host-port-direct` | path | ready | … | in-place：`proceed:path:compat-big-bang` / `direct-vue3`；host-port：`proceed:path:host-port-direct` / `microfrontend-coexist`；共用 `defer` / `other` |

## 8. 验证矩阵

| 命名配方 | 实施期命令 | 失败证明什么 | 证据状态 |
|---|---|---|---|
| | | | |

## 9. 回滚与责任人

| 单元 | 触发条件 | 恢复目标 | 责任人 |
|---|---|---|---|

## 10. 未决问题与证据缺口

### 人工补搜检查

| 项 | 结果（已扫/未发现/缺口说明） |
|---|---|
| `slot-scope` / 旧 `slot=` | |
| 全局 `Vue.filter` | |
| 非 `vue-*` Vue2-only / 编辑器包 | |
| `Vue.prototype.$*` 定义与 `this.$*` 消费点 | |
| 对应的 `app.config.globalProperties` 或 `provide/inject` 迁移目标 | |
| lockfile 缺失或未解析 | |

其他未决：
-
