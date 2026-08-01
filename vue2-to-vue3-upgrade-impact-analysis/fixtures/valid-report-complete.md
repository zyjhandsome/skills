# Vue2 → Vue3 升级 — 决策包（样例·complete）

> 仅作校验器与写法参考；数值为示意。

## 状态

| 字段 | 取值 |
|---|---|
| analysis_status | complete |
| decision_status | decided |
| batch_implementation_gate | ready |
| behavior_parity_required | yes |
| network_mode | online |
| report_path | . |

**横幅：** 分析完成；`batch_implementation_gate=ready` 仅信息性——实施需另授权，本技能不改代码

## 1. 基线与假设

- 项目根路径：`/repo/admin-web`
- 前端 workspace：`admin-web`
- 环境前置：Node 18 / npm / Python PASS
- 主机 Node vs `engines`：均为 `>=18`
- 构建变体 / 批次范围：`default` / `full-stack`
- 入口：workspace
- lockfile：`package-lock.json`（示例）
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
- 理由：人工已 `proceed:path:compat-big-bang`
- 备选路径：—
- Composition API 全仓重写：另立项，本次不评估工作量
- 命名配方（Name, never run）：`vue-compat`、`webpack-to-vite`、`gogocode-element`、`manual-router4`（本技能不执行）

## 4. 子系统影响清单

| 子系统 | scope_status | 风险 | 就绪度 | 命名配方 | 说明 |
|---|---|---|---|---|---|
| `core-vue` | in_scope | high | needs-major | `vue-compat` | 已 proceed |
| `router` | in_scope | high | needs-major | `manual-router4` | 已 proceed |
| `build` | in_scope | high | needs-major | `webpack-to-vite` | 已 proceed |
| `store` | in_scope | medium | needs-major | `manual-pinia-or-vuex4` | 未进队 |
| `ui` | in_scope | blocker | replace | `gogocode-element` | 已 proceed |
| `test` | in_scope | medium | needs-major | — | 未进队 |
| `lint-ide` | in_scope | medium | needs-major | `eslint-vue3` | 未进队 |
| `i18n-plugins` | in_scope | high | unknown | — | 已 proceed |
| `composition-existing` | in_scope | low | unused | — | 未进队 |
| `blockers` | in_scope | n/a | replace | — | 已由 `ui` / `i18n-plugins` 覆盖 |

## 5. 分层影响分析

| 层级 | 文件/模块 | 事实或推断 | 所需变更（仅描述，不实施） | 风险 |
|---|---|---|---|---|
| 代码 | `src/**` | 推断 | compat warning 清单清理 | 高 |
| 路由 | `src/router` | 事实 | Router 4 | 高 |
| UI | Element 页面 | 事实 | Element Plus | 阻塞 |
| 构建 | CLI | 事实 | Vite | 高 |

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
| `subsystem:i18n-plugins` | subsystem | decided | 残余插件纳入 | `proceed:subsystem:i18n-plugins` |

## 8. 验证矩阵

| 范围 | 测试项 | 预期结果 | 证据状态 |
|---|---|---|---|
| 冒烟 | 登录+列表 | 通过 | 待实施阶段 |

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
| 非 `vue-*` Vue2-only / 编辑器包 | 已核对 |
| lockfile 缺失或未解析 | 有 lockfile |

- 无阻塞缺口；实施需另授权
