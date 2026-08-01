# Vue2 → Vue3 升级 — 决策包模板

> 填写后保存为 `vue2-to-vue3-upgrade-report.md`。  
> 状态枚举、包名、版本、路径、命令、URL 保持英文原文；表头与说明默认简体中文。

## 状态

| 字段 | 取值 |
|---|---|
| analysis_status | partial / blocked / complete |
| decision_status | needs_choice / not_needed / decided |
| batch_implementation_gate | frozen / ready |
| behavior_parity_required | yes / no |
| network_mode | online / offline / partial |
| report_path | 待填 |

**横幅：** （待补证据 / 待人工确认·下一动作=提问 / 无）

## 1. 基线与假设

- 项目根路径：
- 前端 workspace：
- 环境前置：Node / package manager / Python（PASS 摘要）
- 主机 Node vs `engines`：
- lockfile：`<path>` / 无 lockfile（无 lock 时注明复现性风险升高）
- 构建变体 / 批次范围：
- 入口：workspace / inventory
- 报告路径（解析结果）：
- 假设与限制：

## 2. 仓画像与依赖就绪度

| 包名 | 当前版本 | Vue3 就绪度 | 建议 | 证据 |
|---|---|---|---|---|

## 3. 推荐迁移路径

- 推荐路径 id：`compat-big-bang` / `direct-vue3` / `microfrontend-coexist` / …
- 理由：
- 备选路径：
- Composition API 全仓重写：另立项，本次不评估工作量
- 命名配方（Name, never run）：…（本技能不执行）

## 4. 子系统影响清单

| 子系统 | scope_status | 风险 | 就绪度 | 命名配方 | 说明 |
|---|---|---|---|---|---|

## 5. 分层影响分析

| 层级 | 文件/模块 | 事实或推断 | 所需变更（仅描述，不实施） | 风险 |
|---|---|---|---|---|

## 6. 风险分级

| 项 | 分级 | 说明 | 上游链接 |
|---|---|---|---|

## 7. 确认队列

| 单元 | 类型 | 状态 | 问题 | 选项 |
|---|---|---|---|---|
| `path:compat-big-bang` | path | ready | … | `proceed:path:compat-big-bang` / `proceed:path:direct-vue3` / `defer` / `other` |

## 8. 验证矩阵

| 范围 | 测试项 | 预期结果 | 证据状态 |
|---|---|---|---|

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
| lockfile 缺失或未解析 | |

其他未决：
-
