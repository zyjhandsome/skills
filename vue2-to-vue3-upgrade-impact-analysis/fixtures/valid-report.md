# Vue2 → Vue3 升级 — 决策包（样例·partial）

> 仅作校验器与写法参考；数值为示意。

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
| evidence_as_of | 2026-08-01 |

**横幅：** 待人工确认·下一动作=提问（迁移路径）

## 1. 基线与假设

- 项目根路径：`/repo/admin-web`
- 前端 workspace：`admin-web`
- 环境前置：Node 18 / npm / Python PASS
- 主机 Node vs `engines`：均为 `>=18`
- 构建变体 / 批次范围：`default` / `full-stack`
- 入口：workspace
- lockfile：`package-lock.json`（样例；若缺失须写「无 lockfile」且 handoff 保持 frozen）
- lockfile_status: present
- evidence_as_of: 2026-08-01
- 报告路径（解析结果）：见状态表 `report_path`
- 假设与限制：单仓画像；不实施、不执行 codemod

## 2. 仓画像与依赖就绪度

| 包名 | 当前版本 | Vue3 就绪度 | 建议 | 证据 |
|---|---|---|---|---|
| `vue` | 2.7.16 | needs-major | 升至 vue@3 + compat 桥 | package.json / lock |
| `vue-router` | 3.6.5 | needs-major | vue-router@4 | package.json |
| `vuex` | 3.6.2 | needs-major | 先 Vuex4 或迁 Pinia | package.json |
| `element-ui` | 2.15.14 | replace | Element Plus | package.json |
| `@vue/cli-service` | 5.0.8 | needs-major | 迁 Vite | package.json |
| `vue-count-to` | 1.0.13 | unknown | 确认 Vue3 替代或移除 | package.json |

## 3. 推荐迁移路径

- 推荐路径 id：`compat-big-bang`
- runtime_axis: compat
- build_axis: vite
- topology_axis: single-cutover
- 理由：单仓可切流；依赖含 Element UI 与 CLI，需仓内 compat 清 warning，构建必须同升
- 备选路径：`direct-vue3`（表面太大，不推荐）
- Composition API 全仓重写：另立项，本次不评估工作量
- 命名配方（Name, never run）：`vue-compat`、`webpack-to-vite`、`gogocode-element`、`manual-router4`（本技能不执行）

## 4. 子系统影响清单

| 子系统 | scope_status | 风险 | 就绪度 | required_for_path | 命名配方 | 说明 |
|---|---|---|---|---|---|---|
| `core-vue` | in_scope | high | needs-major | yes | `vue-compat` | 2.7 → 3 |
| `router` | in_scope | high | needs-major | yes | `manual-router4` | vue-router 3 → 4 |
| `build` | in_scope | high | needs-major | yes | `webpack-to-vite` | CLI → Vite |
| `store` | in_scope | medium | needs-major | no | `manual-pinia-or-vuex4` | Vuex3；不进 Wave 2 |
| `ui` | in_scope | blocker | replace | yes | `gogocode-element` | Element UI → Plus |
| `test` | in_scope | medium | needs-major | no | — | test-utils v1 |
| `lint-ide` | in_scope | medium | needs-major | no | `eslint-vue3` | eslint-plugin-vue |
| `i18n-plugins` | in_scope | high | unknown | yes | — | vue-count-to 等残余插件 |
| `composition-existing` | in_scope | low | unused | no | — | 未使用 composition-api 桥 |
| `blockers` | in_scope | n/a | replace | no | — | element-ui 已由 `ui` 覆盖，不单列进队 |

## 5. 分层影响分析

| 层级 | 文件/模块 | 事实或推断 | 所需变更（仅描述，不实施） | 风险 |
|---|---|---|---|---|
| 代码 | `src/**/*.vue` | 推断：存在 `.sync` / 过滤器可能 | 按 warning 清单清理 | 高 |
| 配置 | `vue.config.js` | 事实：Vue CLI | 迁 Vite 配置 | 高 |
| 路由 | `src/router` | 事实：vue-router@3 | Router 4 + 通配符 | 高 |
| UI | Element 表单页 | 事实：element-ui | 换 Element Plus | 阻塞 |
| 测试 | 少量 Jest | 事实：无 test-utils v2 | 升级挂载 API | 中 |

### ui_visual_risk

- triggers: element-ui-to-element-plus
- legacy_selectors: 待实施阶段按 `.el-*` 与 deep selector 清单逐项迁移
- css_entry_order: 需记录最终 Element/theme/app CSS cascade
- theme_and_teleport: 检查 `--el-*` 与 Select/DatePicker popper 容器
- tailwind_reset: not_applicable（仓画像未发现 Tailwind）
- primary_sample: 登录后主列表的搜索区 + Element 表格
- secondary_sample: not_applicable（未发现第二表格栈）
- baseline_status: required-before-implementation
- required_visual_states: search-default, table-empty, table-data, cell-popper
- recommended_next_action: run_visual_review

## 6. 风险分级

| 项 | 分级 | 说明 | 上游链接 |
|---|---|---|---|
| Element UI | blocker | 无 Vue3 线 | https://element-plus.org/en-US/guide/migration.html |
| 构建 | high | CLI 维护态 | https://v3-migration.vuejs.org/recommendations |
| 路由 | high | major + 动态路由 | https://router.vuejs.org/guide/migration/ |

## 7. 确认队列

| 单元 | 类型 | 状态 | 问题 | 选项 |
|---|---|---|---|---|
| `path:compat-big-bang` | path | ready | 是否确认推荐路径 compat-big-bang？ | `proceed:path:compat-big-bang` / `proceed:path:direct-vue3` / `defer` / `other` |
| `subsystem:core-vue` | subsystem | pending | 路径确认后纳入 core-vue | `defer` / `other` |
| `subsystem:router` | subsystem | pending | 路径确认后纳入 router | `defer` / `other` |
| `subsystem:build` | subsystem | pending | 路径确认后纳入构建同升 | `defer` / `other` |
| `subsystem:ui` | subsystem | pending | 路径确认后纳入 UI 大步（Element Plus） | `defer` / `other` |
| `subsystem:i18n-plugins` | subsystem | pending | 路径确认后纳入残余 Vue 插件 | `defer` / `other` |

## 8. 验证矩阵

| 范围 | 测试项 | 预期结果 | 证据状态 |
|---|---|---|---|
| 构建 | `vite build`（实施阶段） | 通过 | 待执行 |
| 冒烟 | 登录 + 主列表 | 无控制台 compat 残留 warning | 待执行 |

## 9. 回滚与责任人

| 单元 | 触发条件 | 恢复目标 | 责任人 |
|---|---|---|---|
| 整仓切流 | 冒烟失败或错误率上升 | 回布上一版本 admin-web | 前端组 |

## 10. 未决问题与证据缺口

### 人工补搜检查

| 项 | 结果 |
|---|---|
| `slot-scope` / 旧 `slot=` | 待精确扫描 |
| 全局 `Vue.filter` | 待精确扫描 |
| 非 `vue-*` Vue2-only / 编辑器包 | 待核对候选（含 vue-count-to） |
| `Vue.prototype.$*` / `this.$*` 定义与消费点 | 待逐一登记 |
| `globalProperties` / `provide/inject` 迁移目标 | 待逐一登记 |
| lockfile 缺失或未解析 | lockfile_status=present（样例 package-lock.json） |

- 过滤器与 `$listeners` 的静态命中数待补精确扫描
- Element Plus 视觉回归范围待产品确认
