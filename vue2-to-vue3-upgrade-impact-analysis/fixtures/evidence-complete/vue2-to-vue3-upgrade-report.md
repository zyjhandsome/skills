# Vue2 → Vue3 升级 — 决策包（样例·complete）

> 仅作校验器与写法参考；数值为示意。

## 状态

| 字段 | 取值 |
|---|---|
| analysis_status | complete |
| decision_status | decided |
| batch_implementation_gate | ready |
| implementation_readiness | not_assessed |
| behavior_parity_required | yes |
| schema | vue3-upgrade-report/v1 |
| producer | vue2-to-vue3-upgrade-impact-analysis |
| summary_path | fixtures/evidence-complete/upgrade-summary.json |
| visual_acceptance_required | yes |
| network_mode | online |
| report_path | fixtures/evidence-complete |
| evidence_as_of | 2026-08-01 |

**横幅：** 分析完成；`batch_implementation_gate=ready` 仅 handoff only——实施需另授权，本技能不改代码；`implementation_readiness=not_assessed`

## 1. 基线与假设

- 项目根路径：`/repo/admin-web`
- 前端 workspace：`admin-web`
- 环境前置：Node 18 / npm / Python PASS
- host_node_version: `v18.20.4`
- current_node_contract: `>=18`（package.json engines + CI）
- current_node_evidence: `engines.node >=18` 为声明；CI Node 18 build 为已知绿色基线
- target_node_requirement: `^18.0.0 || >=20.0.0`
- target_node_sources: `vue@3.5.39 → no engines.node; vite@5.4.19 → ^18.0.0 || >=20.0.0; https://registry.npmjs.org/vite/5.4.19`
- node_compatibility_status: compatible
- node_transition_strategy: same-node
- 构建变体 / 批次范围：`default` / `full-stack`
- 入口：workspace
- lockfile：`package-lock.json`（示例）
- lockfile_status: present
- repo_revision: `3f2a1b7c9d0e`（git HEAD，样例；分析包绑定此仓库状态）
- browser_support_floor: 无 browserslist 配置；Vite 默认 modern target（不含 IE11），已在 build 决策中确认
- evidence_as_of: 2026-08-01
- 报告路径（解析结果）：见状态表 `report_path`
- 假设与限制：决策已确认；实施另授权

## 2. 仓画像与依赖就绪度

| 包名 | 当前版本 | Vue3 就绪度 | 建议 | 证据 |
|---|---|---|---|---|
| `vue` | 2.7.16 | needs-major | vue@3 + `@vue/compat` | lock |
| `vue-router` | 3.6.5 | needs-major | vue-router@4 | lock |
| `element-ui` | 2.15.14 | replace | element-plus | lock |
| `@vue/cli-service` | 5.0.8 | needs-major | Vite | lock |
| `vue-count-to` | 1.0.13 | unknown | 替代或移除 | lock |

## 3. 推荐迁移路径

- 推荐路径 id：`compat-big-bang`（已确认）
- runtime_axis: compat
- build_axis: vite
- topology_axis: single-cutover
- ui_cutover_staging: after-runtime（compat 让 element-ui 在 Vue3 运行时下先继续工作，UI 库替换单独成步，缩小爆炸半径）
- 理由：人工已 `proceed:path:compat-big-bang`
- 备选路径：—
- Composition API 全仓重写：另立项，本次不评估工作量
- 命名配方（Name, never run）：`vue-compat`、`webpack-to-vite`、`gogocode-vue`、`gogocode-element`、`manual-router4`（本技能不执行）

## 4. 子系统影响清单

| 子系统 | scope_status | 风险 | 就绪度 | required_for_path | 命名配方 | 说明 |
|---|---|---|---|---|---|---|
| `core-vue` | in_scope | high | needs-major | yes | `vue-compat`, `gogocode-vue` | 已 proceed；模板/API codemod 与 UI 库 codemod 命中同一批调用点 |
| `router` | in_scope | high | needs-major | yes | `manual-router4` | 已 proceed；`router_major: 4`（迁移文档区间是 v3→v4；`latest` 已是 v5，裸装会落错） |
| `build` | in_scope | high | needs-major | yes | `webpack-to-vite` | 已 proceed |
| `store` | in_scope | medium | needs-major | no | `manual-pinia-or-vuex4` | 未进队 |
| `ui` | in_scope | blocker | replace | yes | `gogocode-element` | 已 proceed |
| `test` | in_scope | medium | needs-major | no | — | 未进队 |
| `lint-ide` | in_scope | medium | needs-major | no | `eslint-vue3` | 未进队 |
| `i18n-plugins` | not_applicable | n/a | unused | no | — | 未命中 vue-i18n 或已证明归属的 Vue 插件 |
| `composition-existing` | in_scope | low | unused | no | — | 未进队 |
| `blockers` | in_scope | blocker | unknown | yes | — | 已 proceed；`vue-count-to`：`confirm:blocker:vue-count-to:replace` |

## 5. 分层影响分析

| 层级 | 文件/模块 | 事实或推断 | 所需变更（仅描述，不实施） | 风险 |
|---|---|---|---|---|
| 代码 | `src/**` | 推断 | compat warning 清单清理 | 高 |
| 路由 | `src/router` | 事实 | Router 4 | 高 |
| UI | Element 页面 | 事实 | Element Plus | 阻塞 |
| 构建 | CLI | 事实 | Vite | 高 |

### ui_visual_risk

- triggers: element-ui-to-element-plus
- legacy_selectors: 待实施阶段按 `.el-*` 与 deep selector 清单逐项迁移
- css_entry_order: 需记录最终 Element/theme/app CSS cascade
- theme_and_teleport: 检查 `--el-*` 与 Select/DatePicker popper 容器
- tailwind_reset: not_applicable（仓画像未发现 Tailwind）
- primary_sample: 登录后主列表的搜索区 + Element 表格
- secondary_sample: not_applicable（未发现第二表格栈）
- baseline_status: required-before-implementation
- required_visual_states: search-default, table-empty, table-data, cell-popper, icon-toolbar
- recommended_next_action: run_visual_review

### ui_behavior_contract

- mount_timing: Element Plus 弹层（el-dialog / el-drawer）按 modelValue 懒挂载，子组件在打开前不存在；已登记 4 处「先取 `$refs` 再打开」的调用点，须改为打开后 nextTick
- prop_renames: 弹层可见性逐组件查 Element Plus 的 props+emits，两族方向相反：dialog/drawer 由 `:visible.sync` 去掉参数改裸 `v-model`（7 处命中），popover/tooltip 由旧库裸 `v-model` 加上参数改 `v-model:visible`（3 处命中，其中【配置角色】一处 popover 若沿用裸 `v-model` 会落到无 `modelValue` 的 attrs、弹层不开而本地标志已翻、遮罩孤存）；受控模式下 EP popover 的 `trigger` 失效，产品要的 click 须靠绑定与 reference 节点修复，不得改 `trigger` 充数。另 checkbox/radio `:label` → `:value`（2 处）
- kit_internal_traversal: 3 处 `$parent.$parent` 写宿主 `drawer`（EP 在 slot 内容与页面之间多了 overlay/focus-trap，赋值落在内部实例，取消钮静默无效而关闭图标因走 `$emit` 仍可用）、2 处嵌套 `$refs` 链、1 处 `$nextTick` 改 `td.classList` 做表格合并（改用 `:span-method`）、1 处对 `getElementById` 结果 `click()`（节点在 dialog footer 内，关闭态不挂 DOM）；逐点改公开 API 并断言宿主状态翻转
- enum_renames: size `mini` → `small`、`medium` → `default`；已登记 9 处 `size="mini"`，旧值不被识别且不报错
- event_contract: `update:<prop>` 事件名随 prop 改名同步变化；3 个组件未声明 emits，存在 attrs fallthrough 双触发风险
- slot_contract: `slot=` / `slot-scope` → `#name` / `v-slot`；el-table 列插槽作用域参数按 Element Plus 文档逐列核对
- slot_content_shape: el-popover / el-tooltip / el-dropdown 的 `reference` 触发插槽在 Element Plus 下会对唯一子节点挂指令，要求元素型根；已登记 3 处 `#reference` 内直接放组件（含 1 处 el-autocomplete），构建仍绿、运行时报 non-element root node 且定位失效，须包一层元素或改用 `virtual-triggering`
- required_behavior_assertions: drawer-open-mounts-child, dialog-visible-write-back, pagination-page-change, select-popper-teleport, table-size-enum-applies, popover-reference-element-root

## 6. 风险分级

| 项 | 分级 | 说明 | 上游链接 |
|---|---|---|---|
| UI | blocker | Element 大步 | https://element-plus.org/en-US/guide/migration.html |

## 7. 确认队列

| 单元 | 类型 | 状态 | 问题 | 选项 |
|---|---|---|---|---|
| `path:compat-big-bang` | path | decided | 路径已确认 | `proceed:path:compat-big-bang` |
| `subsystem:core-vue` | subsystem | decided | core-vue 纳入 | `proceed:subsystem:core-vue` |
| `subsystem:router` | subsystem | decided | router 纳入 | `proceed:subsystem:router` |
| `subsystem:build` | subsystem | decided | 构建同升纳入 | `proceed:subsystem:build` |
| `subsystem:ui` | subsystem | decided | UI 大步纳入 | `proceed:subsystem:ui` |
| `subsystem:blockers` | subsystem | decided | vue-count-to 替换纳入 | `proceed:subsystem:blockers` |

## 8. 验证矩阵

| 命名配方 | 实施期命令 | 失败证明什么 | 证据状态 |
|---|---|---|---|
| `vue-compat` | alias `vue` → `@vue/compat` 后构建 | 构建失败或缺 migration build | 待实施阶段 |
| `webpack-to-vite` | `vite build`（人接受配置后） | 非 0 退出或 `base`/`publicPath` 错 | 待实施阶段 |
| `gogocode-vue` | 按目录逐批 review codemod diff | `.sync` / filters / 已移除实例 API 改写错误 | 待实施阶段 |
| `gogocode-element` | Element 主表单/表格页渲染 | Plus 映射缺失或样式崩 | 待实施阶段 |
| `gogocode-vue` × `gogocode-element` | 同一批弹层文件：打开→改值→关闭，断言父级回写 | 两个各自正确的改写合起来错：`.sync` 变成 `v-model:<旧库 prop>`，build 与 lint 全绿但绑定已死 | 待实施阶段 |
| `manual-router4` | 登录跳转 + 404 通配 | history / catch-all 行为错 | 待实施阶段 |
| `manual-pinia-or-vuex4` | Vuex 4 安装 API 冒烟 | store 注入失败 | 待实施阶段 |
| `eslint-vue3` | Vue3 eslint 规则 | 残留 Vue2 API lint | 待实施阶段

## 9. 回滚与责任人

| 单元 | 触发条件 | 恢复目标 | 责任人 |
|---|---|---|---|
| 整仓 | 冒烟失败 | 上一版本 | 前端组 |

## 10. 未决问题与证据缺口

### 人工补搜检查

| 项 | 结果 |
|---|---|
| `slot-scope` / 旧 `slot=` | 已纳入影响面 |
| 全局 `Vue.filter` | 已纳入影响面 |
| 非 `vue-*` Vue2-only / 编辑器包 | 已覆盖 vue-count-to 等残余候选 |
| `Vue.prototype.$*` / `this.$*` 定义与消费点 | 已登记定义与消费者 |
| `globalProperties` / `provide/inject` 迁移目标 | 已登记迁移目标 |
| lockfile 缺失或未解析 | 有 lockfile |
| `model:` 选项（自定义 v-model prop/event） | 已扫描：2 处活选项列入 core-vue 影响面 |
| `.native` / keyCode 修饰符 | 已扫描：6 处 `.native` 列入影响面 |
| `emits` 声明与事件双触发 | 已核对：无未声明 emit 的双触发风险 |
| `Vue.component` / `Vue.directive` / `Vue.mixin` 全局注册与指令钩子改名 | 已扫描：3 处全局组件注册列入影响面 |
| `<transition>` 过渡类名（v-enter → v-enter-from） | 已扫描：无 transition 组件使用 |
| 静默语义变更（v-if/v-for 优先级、v-bind 顺序、watch 数组、data 浅合并、attr coercion） | 已扫描：同元素 v-if+v-for 无命中；其余列入实施期核对 |
| `.sync` 修饰符与目标 UI 库 prop 身份 | 已扫描：11 处，其中 7 处绑在 element-ui 组件上，逐组件按 Element Plus 的 props+emits 重解析——dialog/drawer 去掉参数改裸 `v-model`，popover/tooltip 反而要加上参数，两族方向相反，不得互相套用 |
| 靠遍历伸进目标库内部的调用点 | 已扫描：3 处 `$parent.$parent` 写宿主弹层标志、2 处嵌套 `$refs` 链、1 处 `$nextTick` 改 `td.classList` 做表格合并、1 处对 `getElementById` 结果 `click()`（目标节点在弹层内，关闭态不挂 DOM）；逐点改公开 API 并断言宿主状态翻转 |
| 路由 history 实现与多页入口 URL 形态 | 已扫描：2 个入口的 Router 3 `mode` 均未设置（即 hash），沿用为 `createWebHashHistory`；改路径路由另立决策。断言首次 `replace` 后 `*.html` 入口名与 `crntProjectSelfCode` query 仍在 |
| `router-view` 上的 `ref` 归属 | 已扫描：2 处 `<router-view ref="routerView">`，Router 3 下 `ref` 落到匹配组件，Router 4 归 RouterView 自身；改 `v-slot="{ Component }"` 并断言父页仍调得到页面方法 |
| UI-kit `icon prop` 的 sprite 字符串 | 已扫描：2 处 `sprite-icon` class prop，均按目标组件 prop 重写并绑定 mount/点击断言 |
| `$options.filters` 过滤器对象访问 | 已扫描：3 处对象访问调用点，独立于管道写法列入 core-vue 影响面 |
| 裸 `<template>` 包默认槽 | 已扫描：4 处无属性缩进 `<template>`（Panel 正文与基本信息块），Vue3 下编成真实 `template` 元素后整块不渲染；逐处改具名槽并补 `vue/no-lone-template` |
| 挂载容器选择器对撞 | 已核对：`public/index.html` 挂载点 `#app` 与根组件根元素 `id="app"` 同名，Vue3 挂进容器后同一条 `#app` 规则命中两次（顶距翻倍），列入 ui 影响面并须二选一 |
| 被 CSS 抑制的目标库 overlay chrome | 已扫描：2 处 `::v-deep .el-drawer__header { display: none }`，Element Plus teleport 后锚点失配，被隐藏的 header 与应用自绘关闭钮并存；绑定弹层打开态断言 |
| dev 与 build 运行面差异（源码 CJS、`require.context`、多入口 URL 形态） | 已扫描：src 内 2 处 `module.exports`、单入口无 `require.context`；两条运行面各列一条验证 |
| router 导航静默变抛错（旧 `push/replace` 吞错覆写；按 name 跳转缺必填参数） | 已扫描：1 处 prototype 吞错覆写、5 处按 name 跳转，其中 1 处（启动期 `replace({name:'class'})`）缺必填参数，Router 4 下会抛错；逐调用点列入 §8 断言 |
| 外部全局脚本运行期契约 | 未发现 HTML/动态 loader 与 `globalThis.X` ready/instance polling 的关联命中 |
| 目标依赖弃用告警面（迁移后落在目标大版本已弃用 API；样式/构建工具自身弃用告警） | 已核对 Element Plus 弃用清单：`type="text"`（8 处）与 dialog `title` 插槽（3 处）落在已弃用 API 上，按 mount 刷告警；样式编译器 `@import` 前置注入为工具链弃用面，两类均在 console 处置协议内 |

- 无阻塞缺口；实施需另授权
