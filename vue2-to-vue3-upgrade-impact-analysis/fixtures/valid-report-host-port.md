# Vue2 → Vue3 升级 — 决策包（样例·host-port·partial）

> A→B host-port 写法参考；数值为示意。

## 状态

| 字段 | 取值 |
|---|---|
| analysis_status | partial |
| decision_status | needs_choice |
| batch_implementation_gate | frozen |
| implementation_readiness | not_assessed |
| behavior_parity_required | yes |
| schema | vue3-upgrade-report/v1 |
| producer | vue2-to-vue3-upgrade-impact-analysis |
| summary_path | fixtures/upgrade-summary.json |
| visual_acceptance_required | yes |
| network_mode | online |
| report_path | fixtures |
| evidence_as_of | 2026-08-10 |

**横幅：** 待人工确认·下一动作=提问（host-port 路径）

## 1. 基线与假设

- 项目根路径（分析根=A）：`/repo/vue2-source`
- source_root: `/repo/vue2-source`
- implementation_target: `/repo/vue3-host`
- forbid_source_mutation: yes
- batch_scope: page-closure
- 前端 workspace：`vue2-source`（只读）
- 环境前置：Node 18 / npm / Python PASS
- host_node_version: `v18.20.4`
- current_node_contract: B `>=18`（pnpm + CI）；A Node 16 仅用于只读源基线
- current_node_evidence: B `engines.node >=18` + CI Node 18 build 为已知绿色基线；A `.nvmrc=16` 为声明
- target_node_requirement: `^18.0.0 || >=20.0.0`
- target_node_sources: `vue@3.5.18 → no engines.node; vite@5.4.19 → ^18.0.0 || >=20.0.0; https://registry.npmjs.org/vite/5.4.19`
- node_compatibility_status: compatible
- node_transition_strategy: same-node
- 构建变体 / 批次范围：`default` / `page-closure`
- 入口：host-port
- lockfile：B `pnpm-lock.yaml`（A 可能无 lock）
- lockfile_status: present
- source_lockfile_status: absent
- host_lockfile_status: present
- repo_revision: `a1b2c3d4e5f6`（A 仓 git HEAD，样例；只读画像绑定此状态）
- browser_support_floor: 跟随宿主 B 的 browserslist（modern target，不含 IE11）
- evidence_as_of: 2026-08-10
- 假设与限制：读 A 对照 B；compat 非主路径；不改 A；不实施；gate 跟 B lock

## 2. 仓画像与依赖就绪度

| 包名 | 当前版本 | Vue3 就绪度 | 建议 | 证据 |
|---|---|---|---|---|
| `vue` | 2.6.10 | needs-major | 在 B 使用已有 vue@3；不给 A 装 compat | package.json |
| `vue-router` | 3.0.2 | needs-major | 适配 B 的 vue-router@4 | package.json |
| `vuex` | 3.1.0 | needs-major | 对接 B store（Pinia/Vuex4） | package.json |
| `element-ui` | 2.13.2 | replace | 映射 B UI（Element Plus 或宿主组件） | package.json |

## 3. 推荐迁移路径

- 推荐路径 id：`host-port-direct`
- runtime_axis: direct-vue3
- build_axis: existing-vite
- topology_axis: host-port
- 理由：实施落点为已有 Vue3 宿主 B；页闭包适配迁入；@vue/compat 禁止作为主路径
- 备选路径：`microfrontend-coexist`（仅当必须长期双部署）
- Composition API 全仓重写：另立项，本次不评估工作量
- 命名配方（Name, never run）：`manual-adapt-to-host`、`manual-router4-on-host`、`map-ui-to-host`（本技能不执行；vue-compat 非主路径）
- 宿主对照摘要：B 已是 Vue3 + Vite；A 的 Element UI 须映射到 B 组件栈

## 4. 子系统影响清单

| 子系统 | scope_status | 风险 | 就绪度 | required_for_path | 命名配方 | 说明 |
|---|---|---|---|---|---|---|
| `core-vue` | in_scope | high | needs-major | yes | `manual-adapt-to-host` | 在 B 写 Vue3 SFC，不升 A |
| `router` | in_scope | high | needs-major | yes | `manual-router4-on-host` | 挂到 B 路由 |
| `build` | not_applicable | n/a | unused | no | — | 复用 B Vite；不迁 A 构建 |
| `store` | in_scope | medium | needs-major | no | `manual-pinia-or-host-store` | 对接 B |
| `ui` | in_scope | blocker | replace | yes | `map-ui-to-host` | Element UI → B UI |
| `test` | not_applicable | n/a | unused | no | — | 页闭包未含测试 |
| `lint-ide` | not_applicable | n/a | unused | no | — | 跟 B |
| `i18n-plugins` | not_applicable | n/a | unused | no | — | 本闭包未命中 |
| `composition-existing` | not_applicable | n/a | unused | no | — | 未使用 |
| `blockers` | in_scope | n/a | replace | no | — | UI 映射已由 `ui` 覆盖 |

## 5. 分层影响分析

| 层级 | 文件/模块 | 事实或推断 | 所需变更（仅描述，不实施） | 风险 |
|---|---|---|---|---|
| 代码 | 页闭包 SFC | 事实：Options API + element-ui | 拷贝/改写到 B | 高 |
| 路由 | A 菜单路由 | 事实：嵌在 iframe | 改为 B 原生路由 | 高 |
| UI | Element 表格 | 事实：el-table | 映射 B 表格组件 | 阻塞 |

### ui_visual_risk

- triggers: element-ui-to-host-ui
- legacy_selectors: `.el-*` 在 B 侧需替换或隔离
- css_entry_order: 跟 B 全局样式顺序
- theme_and_teleport: 检查宿主 popper/Teleport
- tailwind_reset: unknown-until-B-inventory
- primary_sample: 指定业务页列表+筛选
- secondary_sample: not_applicable
- baseline_status: capture-on-A-before-port
- required_visual_states: search-default, table-empty, table-data, cell-popper, icon-toolbar
- recommended_next_action: run_visual_review

## 6. 风险分级

| 项 | 分级 | 说明 | 上游链接 |
|---|---|---|---|
| UI 映射 | blocker | A Element UI vs B 栈 | https://element-plus.org/en-US/guide/migration.html |
| 路由挂载 | high | iframe → 原生 | https://router.vuejs.org/guide/migration/ |

## 7. 确认队列

| 单元 | 类型 | 状态 | 问题 | 选项 |
|---|---|---|---|---|
| `path:host-port-direct` | path | ready | 是否确认 host-port-direct（禁改 A，compat 非主）？ | `proceed:path:host-port-direct` / `proceed:path:microfrontend-coexist` / `defer` / `other` |
| `subsystem:core-vue` | subsystem | pending | 路径确认后纳入 core-vue 适配 | `defer` / `other` |
| `subsystem:router` | subsystem | pending | 路径确认后纳入 router 挂载 | `defer` / `other` |
| `subsystem:ui` | subsystem | pending | 路径确认后纳入 UI 映射 | `defer` / `other` |

## 8. 验证矩阵

| 命名配方 | 实施期命令 | 失败证明什么 | 证据状态 |
|---|---|---|---|
| `manual-adapt-to-host` | B 原生 SFC 挂载该页 | 仍依赖 iframe | 待执行 |
| `manual-router4-on-host` | B 路由打开该页 | 404 或残留 A router | 待执行 |
| `map-ui-to-host` | 搜索+主表对照 A 基线 | host UI 映射缺失 | 待执行 |
| `manual-pinia-or-host-store` | 对接 B store 冒烟 | 状态不同步 | 待执行

## 9. 回滚与责任人

| 单元 | 触发条件 | 恢复目标 | 责任人 |
|---|---|---|---|
| 单页切流 | 冒烟/视觉失败 | B 路由切回 iframe 指 A | 前端组 |

## 10. 未决问题与证据缺口

### 人工补搜检查

| 项 | 结果 |
|---|---|
| `slot-scope` / 旧 `slot=` | 闭包静态扫描待补精确命中数 |
| 全局 `Vue.filter` | 闭包静态扫描待补精确命中数 |
| 非 `vue-*` Vue2-only / 编辑器包 | 本闭包未命中额外编辑器包（样例） |
| `Vue.prototype.$*` / `this.$*` 定义与消费点 | 实施前在闭包内逐一登记 |
| `globalProperties` / `provide/inject` 迁移目标 | 对接 B 时逐一登记 |
| lockfile 缺失或未解析 | lockfile_status=present（A 侧 package-lock） |
| `model:` 选项（自定义 v-model prop/event） | 闭包内待精确扫描（改写到 B 时须迁 modelValue） |
| `.native` / keyCode 修饰符 | 闭包内待精确扫描 |
| `emits` 声明与事件双触发 | 改写到 B 时逐组件声明 emits |
| `Vue.component` / `Vue.directive` / `Vue.mixin` 全局注册与指令钩子改名 | 闭包内待精确扫描 |
| `<transition>` 过渡类名（v-enter → v-enter-from） | 闭包内待扫描 |
| 静默语义变更（v-if/v-for 优先级、v-bind 顺序、watch 数组、data 浅合并、attr coercion） | 同元素 v-if+v-for 待扫描；其余列入 B 侧改写核对 |
