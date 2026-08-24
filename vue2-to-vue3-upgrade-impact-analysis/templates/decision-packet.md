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
| entry_mode | upgrade（缺省，可省略该行）/ residual-audit（仓已是 Vue3 时的残留审计） |
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
- repo_revision:（git HEAD commit 或无 git 时的关键文件 digest；分析包绑定此仓库状态，下游须核对漂移）
- browser_support_floor:（browserslist / .browserslistrc 原文，或「无配置 + Vite 默认 modern target 需决策」；Vue3 不支持 IE11）
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

`unknown` 包在 complete 前必须由唯一 §4 owner 记录
`confirm:blocker:<pkg>:<replace|fork|remove|defer>`；无已证明专属 owner 时归 `blockers`。

## 3. 推荐迁移路径

- 推荐路径 id：`compat-big-bang` / `direct-vue3` / `host-port-direct` / `microfrontend-coexist` / `residual-audit`（仅 entry_mode=residual-audit） / …
- runtime_axis: compat / direct-vue3
- build_axis: vite / cli5-webpack5 / existing-vite
- topology_axis: single-cutover / coexist / host-port
- ui_cutover_staging: with-runtime / after-runtime（`ui` 为 replace / needs-major 时必填）
- default_path_deviation:（单仓原地升且 runtime_axis=direct-vue3 时必填：默认 compat 本可吸收什么、为何不需要、改由什么验证承接）
- 理由：
- 备选路径：
- Composition API 全仓重写：另立项，本次不评估工作量
- 命名配方（Name, never run）：…（本技能不执行；host-port 禁止 vue-compat 作主路径）

## 4. 子系统影响清单

| 子系统 | scope_status | 风险 | 就绪度 | required_for_path | 命名配方 | 说明 |
|---|---|---|---|---|---|---|

已答内部分叉时在说明写 marker / 逐包 token，并把同一精确 `confirm:` token 写入对应
Decision Record 的 `分叉人工答复`；`proceed:subsystem:<id>` 只写入 `人工答复`。

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

### ui_behavior_contract（`ui` 为 replace / needs-major 时必填）

- mount_timing:（新库是否懒挂载子树，`$refs` 何时可用）
- prop_renames:（值契约改名，如 `visible` → `modelValue`）
- enum_renames:（size / type 等枚举取值改名或删除）
- event_contract:（`update:<prop>` 事件名、payload、`emits` 与双触发）
- slot_contract:（插槽名与作用域参数结构）
- slot_content_shape:（触发型插槽对内容根节点类型的要求，如 popover/tooltip/dropdown 的 `reference` 面要元素型根；组件型根构建仍绿、运行时报 non-element root node）
- required_behavior_assertions:（逗号分隔，至少 3 条唯一断言，逐条对应 §8）

### residual_findings（`entry_mode: residual-audit` 时必填）

- compat_shims_present:（compat alias / compatConfig 是否仍生效，warning 是否已分类）
- codemod_artifacts:（上一轮 codemod 的错误改写特征，build/lint 为何没拦住）
- silent_break_residues:（`.sync` 产物 prop 身份、`$options.filters` 对象访问、`.native`、枚举改名等）
- runtime_lane_residues:（只在 dev 或只在 build 暴露的残留）
- required_cleanup_assertions:（逗号分隔，至少 3 条唯一断言，逐条对应 §8）

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
| `model:` 选项（自定义 v-model；区分父级 v-model 消费的活选项与死选项） | |
| `.native` / keyCode 修饰符 | |
| `emits` 声明与事件双触发（未声明 emit 走 fallthrough 触发两次） | |
| `Vue.component` / `Vue.directive` / `Vue.mixin` 全局注册与指令钩子改名 | |
| `<transition>` 过渡类名（v-enter → v-enter-from） | |
| 静默语义变更（v-if/v-for 优先级、v-bind 顺序、watch 数组、data 浅合并、attr coercion） | |
| `.sync` 修饰符与目标 UI 库 prop 身份（同批换库时按新库实际 prop 重解析） | |
| UI-kit `icon prop` 的 class/sprite 字符串（按目标 prop 分类 silent/mount 风险） | |
| `$options.filters` 过滤器对象访问（与模板管道是两处独立改写面） | |
| 裸 `<template>` 包默认槽（Vue2 透明拆包，Vue3 编成真实 `template` 元素后整块不渲染） | |
| 挂载容器选择器对撞（HTML 挂载点 vs 根组件根元素 id/class；同名则全局规则命中两次） | |
| 被 CSS 抑制的目标库 overlay chrome（teleport 后锚点失配，症状是重复控件而非缺失） | |
| dev 与 build 运行面差异（源码 CJS、`require.context`、多入口 URL 形态、base、env 分支） | |
| router 导航静默变抛错（旧版 `push/replace` 吞错覆写与 `.catch` 吞错；按 name 跳转缺必填参数） | |
| 外部全局脚本运行期契约（loader、ready/instance polling、真实挂载后 round-trip） | |
| 目标依赖弃用告警面（迁移后落在目标大版本已弃用的 API 上；样式/构建工具自身的弃用告警） | |

其他未决：
-
