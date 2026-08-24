# Vue2 → Vue3 升级 — 残留审计包（样例·residual-audit）

> 仅作校验器与写法参考；数值为示意。
> 本包不推荐迁移路径：workspace 已是 Vue3，剩下的是上一轮迁移遗留的清理面。

## 状态

| 字段 | 取值 |
|---|---|
| analysis_status | complete |
| decision_status | decided |
| batch_implementation_gate | ready |
| implementation_readiness | not_assessed |
| behavior_parity_required | yes |
| entry_mode | residual-audit |
| schema | vue3-upgrade-report/v1 |
| producer | vue2-to-vue3-upgrade-impact-analysis |
| summary_path | fixtures/residual-audit/upgrade-summary.json |
| visual_acceptance_required | yes |
| network_mode | online |
| report_path | fixtures/residual-audit |
| evidence_as_of | 2026-08-21 |

**横幅：** 残留审计完成；`batch_implementation_gate=ready` 仅 handoff only——清理实施需另授权，本技能不改代码；`implementation_readiness=not_assessed`

## 1. 基线与假设

- 项目根路径：`/repo/legacy-portal`
- 前端 workspace：`legacy-portal`
- 环境前置：Node 20 / pnpm / Python PASS
- host_node_version: `v20.14.0`
- current_node_contract: `>=18`（package.json engines + CI）
- current_node_evidence: `engines.node >=18` 为声明；CI Node 20 build 为已知绿色基线
- target_node_requirement: `^18.0.0 || >=20.0.0`（沿用现有工具链，本包不提出升级）
- target_node_sources: `vite@5.4.19 → ^18.0.0 || >=20.0.0; https://registry.npmjs.org/vite/5.4.19`
- node_compatibility_status: compatible
- node_transition_strategy: same-node
- 构建变体 / 批次范围：`default` / `full-stack`
- 入口：workspace
- lockfile：`pnpm-lock.yaml`
- lockfile_status: present
- repo_revision: `9c41de70ab52`（git HEAD，样例；分析包绑定此仓库状态）
- browser_support_floor: `.browserslistrc` = `defaults, not IE 11`
- evidence_as_of: 2026-08-21
- 报告路径（解析结果）：见状态表 `report_path`
- 假设与限制：workspace 已在 Vue3 运行时上；本包只盘点上一轮迁移的残留，不写 Vue2 基线，也不推荐迁移路径

## 2. 仓画像与依赖就绪度

| 包名 | 当前版本 | Vue3 就绪度 | 建议 | 证据 |
|---|---|---|---|---|
| `vue` | 3.5.39 | ready | 保持 | lock |
| `@vue/compat` | 3.5.39 | ready | 清理后移除（仍在 alias 生效中） | lock + `vite.config.ts` alias |
| `vue-router` | 4.4.5 | ready | 保持 | lock |
| `element-plus` | 2.8.4 | ready | 保持 | lock |
| `vite` | 5.4.19 | ready | 保持 | lock |

## 3. 推荐迁移路径

- 推荐路径 id：`residual-audit`
- runtime_axis: direct-vue3
- build_axis: existing-vite
- topology_axis: single-cutover
- 理由：workspace 已完成运行时与构建切换，无 cutover 可规划；本包只对残留面定级并命名清理验证
- 备选路径：—（不提出升级路径；若后续决定重构，另开分析）
- Composition API 全仓重写：另立项，本次不评估工作量
- 命名配方（Name, never run）：`residual-compat-removal`、`residual-sync-prop-reresolve`（本技能不执行）

## 4. 子系统影响清单

| 子系统 | scope_status | 风险 | 就绪度 | required_for_path | 命名配方 | 说明 |
|---|---|---|---|---|---|---|
| `core-vue` | in_scope | high | ready | yes | `residual-compat-removal`, `residual-sync-prop-reresolve` | compat alias 未摘 + 上一轮 codemod 残留 |
| `router` | in_scope | low | ready | no | — | Router 4 已切完，无残留命中 |
| `build` | in_scope | medium | ready | no | — | Vite 已切完；`require.context` 残留见 residual_findings |
| `store` | in_scope | low | ready | no | — | Pinia 已切完 |
| `ui` | in_scope | medium | ready | no | — | 已在 Element Plus；本包不换库，只重解析被 codemod 改错的 prop |
| `test` | in_scope | low | ready | no | — | 无残留命中 |
| `lint-ide` | in_scope | medium | ready | no | — | Vue3 规则已启用，但未开 compat 残留规则 |
| `i18n-plugins` | in_scope | low | ready | no | — | 无残留命中 |
| `composition-existing` | in_scope | low | ready | no | — | 已有 Composition 代码，不在本包范围 |
| `blockers` | not_applicable | n/a | ready | no | — | 无阻塞项 |

## 5. 分层影响分析

| 层级 | 文件/模块 | 事实或推断 | 所需变更（仅描述，不实施） | 风险 |
|---|---|---|---|---|
| 构建 | `vite.config.ts` | 事实 | `vue` → `@vue/compat` alias 与 compatConfig 仍在，摘除前需先清 warning | 高 |
| 代码 | `src/views/**` | 事实 | 上一轮 codemod 把 `.sync` 改成了旧库 prop 名，需按 Element Plus 实际 prop 重解析 | 高 |
| 代码 | `src/utils/format.js` | 事实 | `$options.filters` 对象访问调用点仍在，模板管道已改完 | 中 |
| 构建 | `src/components/index.js` | 事实 | `require.context` 只在 dev 下被 esbuild 容忍，build 走 rollup 时失败 | 中 |

### ui_visual_risk

- triggers: element-plus-residual-cleanup
- legacy_selectors: 残留 `.el-*` 深选择器 12 处，摘 compat 后需复核
- css_entry_order: Element Plus 主题与 app CSS cascade 顺序已固定，清理时不得调整
- theme_and_teleport: `--el-*` 覆盖与 Select/DatePicker popper 容器需在清理后复看
- tailwind_reset: not_applicable（仓画像未发现 Tailwind）
- primary_sample: 登录后主列表的搜索区 + Element Plus 表格
- secondary_sample: not_applicable（未发现第二表格栈）
- baseline_status: required-before-implementation
- required_visual_states: search-default, table-empty, table-data, dialog-open, cell-popper
- recommended_next_action: run_visual_review

### residual_findings

- compat_shims_present: `vite.config.ts` 仍把 `vue` alias 到 `@vue/compat`，`compatConfig` 保留 `MODE: 2`；控制台每次启动 37 条 compat warning，未分类
- codemod_artifacts: 上一轮 `gogocode-vue` 把 7 处 `:visible.sync` 改成 `v-model:visible`，但同批换库后 Element Plus 的 prop 是 `modelValue`；build 与 lint 均绿，弹层回写静默失效
- silent_break_residues: `$options.filters` 对象访问 3 处（`src/utils/format.js`）；`.native` 修饰符 2 处；`size="mini"` 枚举 9 处，Element Plus 不识别且不报错
- runtime_lane_residues: `src/components/index.js` 的 `require.context` 在 dev（esbuild）下可用、在 build（rollup）下失败；MPA 第二入口只在 build 产物里 404
- required_cleanup_assertions: dialog-visible-write-back, filters-object-callsite-migrated, compat-warning-count-zero, require-context-replaced-in-build, size-enum-applies

## 6. 风险分级

| 项 | 分级 | 说明 | 上游链接 |
|---|---|---|---|
| core-vue | high | compat 未摘 + codemod 残留导致弹层回写静默失效 | https://v3-migration.vuejs.org/migration-build |

## 7. 确认队列

| 单元 | 类型 | 状态 | 问题 | 选项 |
|---|---|---|---|---|
| `path:residual-audit` | path | decided | 已是 Vue3：确认本次只做残留审计、不提出升级路径 | `proceed:path:residual-audit` |
| `subsystem:core-vue` | subsystem | decided | compat 摘除与 codemod 残留纳入清理面 | `proceed:subsystem:core-vue` |

## 8. 验证矩阵

| 命名配方 | 实施期命令 | 失败证明什么 | 证据状态 |
|---|---|---|---|
| `residual-compat-removal` | 摘 alias 后 dev 与 build 各启一次并读控制台 | compat 层仍在兜底，摘除即暴露未迁移调用点 | 待实施阶段 |
| `residual-sync-prop-reresolve` | 逐个弹层：打开→改值→关闭，断言父级 state 回写 | codemod 产出的 prop 名与实际组件契约不符 | 待实施阶段 |
| `residual-compat-removal` × `residual-sync-prop-reresolve` | 同一批弹层文件先摘 compat 再重解析 prop，两步各跑一次上述断言 | 两个清理配方改写同一批调用点，合起来才暴露的失效被漏掉 | 待实施阶段 |

## 9. 回滚与责任人

| 单元 | 触发条件 | 恢复目标 | 责任人 |
|---|---|---|---|
| 残留清理 | 摘 compat 后冒烟失败 | 恢复 alias 与 compatConfig | 前端组 |

## 10. 未决问题与证据缺口

### 人工补搜检查

| 项 | 结果 |
|---|---|
| `slot-scope` / 旧 `slot=` | 已扫描：无残留命中 |
| 全局 `Vue.filter` | 已扫描：filter 定义已清空，仅剩对象访问调用点 |
| 非 `vue-*` Vue2-only / 编辑器包 | 已扫描：无 Vue2-only 残留包 |
| `Vue.prototype.$*` / `this.$*` 定义与消费点 | 已扫描：原型挂载已清空，5 处消费点核对完毕 |
| `globalProperties` / `provide/inject` 迁移目标 | 已登记：上述消费点均已指向现有 app 级注入目标 |
| lockfile 缺失或未解析 | 有 lockfile |
| `model:` 选项（自定义 v-model prop/event） | 已扫描：无残留活选项 |
| `.native` / keyCode 修饰符 | 已扫描：2 处 `.native` 残留，列入 core-vue 清理面 |
| `emits` 声明与事件双触发 | 已核对：2 个组件未声明 emits，列入清理面 |
| `Vue.component` / `Vue.directive` / `Vue.mixin` 全局注册与指令钩子改名 | 已扫描：全局注册已迁至 app.component，指令钩子已改名 |
| `<transition>` 过渡类名（v-enter → v-enter-from） | 已扫描：过渡类名已改完 |
| 静默语义变更（v-if/v-for 优先级、v-bind 顺序、watch 数组、data 浅合并、attr coercion） | 已扫描：同元素 v-if+v-for 无命中；其余列入清理期核对 |
| `.sync` 修饰符与目标 UI 库 prop 身份 | 已扫描：源码已无 `.sync`，但 7 处 codemod 产出的 `v-model:visible` 绑的是旧库 prop 名，须按 Element Plus 重解析 |
| UI-kit `icon prop` 的 sprite 字符串 | 已扫描迁移产物：1 处 `sprite-icon` class prop 仍传目标组件，列入 mount/点击清理断言 |
| `$options.filters` 过滤器对象访问 | 已扫描：3 处对象访问调用点仍在，管道写法已改完 |
| 裸 `<template>` 包默认槽 | 已扫描迁移产物：5 处无属性缩进 `<template>` 仍在，正文整块不渲染；列入清理断言并补 `vue/no-lone-template` |
| 挂载容器选择器对撞 | 已核对：`index.html` 的 `#app` 与根组件根元素 `id="app"` 上次迁移后并存，`#app` 顶距被应用两次，列入清理项 |
| 被 CSS 抑制的目标库 overlay chrome | 已扫描：3 处隐藏 `.el-drawer__header` 的 `::v-deep` 规则在 teleport 后失配，现表现为重复关闭钮，列入清理断言 |
| dev 与 build 运行面差异（源码 CJS、`require.context`、多入口 URL 形态） | 已扫描：1 处 `require.context` 与第二入口只在 build 面失败 |
| router 导航静默变抛错（旧 `push/replace` 吞错覆写；按 name 跳转缺必填参数） | 已扫描：`prototype` 吞错覆写残留 1 处（在 Router 4 下已不生效，属死代码）；按 name 跳转 4 处参数齐备 |
| 外部全局脚本运行期契约 | 未发现 HTML/动态 loader 与 `globalThis.X` ready/instance polling 的关联命中 |
| 目标依赖弃用告警面（迁移后落在目标大版本已弃用 API；样式/构建工具自身弃用告警） | 已核对：上次迁移遗留 6 处已弃用 UI 库 API 与样式编译器 `@import` 前置注入，构成本次审计的 console 噪声清单 |

- 无阻塞缺口；清理实施需另授权
