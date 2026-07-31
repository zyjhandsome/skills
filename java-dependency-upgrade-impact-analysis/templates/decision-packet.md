# Java 依赖升级 — 决策包模板

> 填写后保存为 `java-dependency-upgrade-report.md`。  
> 状态枚举、GAV、版本号、路径、命令、URL 保持英文原文；表头与说明默认简体中文。

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
- 构建工具：Maven / Gradle / 两者
- 环境前置：`java` / 选用 `mvn`|`gradle` / `python`（PASS 摘要或 blocked 缺口）
- 主机 JDK（探测）vs 工程声明：
- JDK / Spring Boot 线：
- 构建变体（Maven profiles / Gradle properties）：
- 批次范围（有界模块/依赖族）：
- 入口：inventory（整仓巡检） / exact-table（精确表）
- 报告路径（解析结果）：
- 假设与限制：

## 2. 依赖清单与解析路径

| 组件 | 模块 | 当前解析版本 | 目标版本 | 方向 | 目标存在性 | 建议处置 | 推荐替代 | 替代存在性 | 依赖路径 | 有效 Owner | 权威层 | 风险 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

目标存在性取值：`yes` / `no` / `unknown` / `n/a`；`no` / `unknown`
且无已验证替代时为 `blocked`，有替代则用 `choose-alternative` / `replace-*`
进入 `ready` 供用户选择。
`n/a` 仅用于无目标制品的处置（`remove` / `exclude` / `no-viable-path` 等）。
建议处置取值见 `treatment-ladder.md`（分析无路写 `no-viable-path`，不要写 `defer`）。含 classifier 的制品须按 classifier 单独探测存在性。scope / optional / exclusions / introducer 记入各组件决策记录。
`choose-alternative` / `replace-*` 行必须保留原请求目标，并填写独立探测为 `yes` 的 `g:a:v` 推荐替代；否则写 `推荐替代=—`、`替代存在性=n/a`。
显式降级写 `方向=downgrade`、风险=高，并在确认问题中标注“降级”；不增加第二个授权闸。

## 3. 主 Owner 决策

| Owner | 当前版本 | 目标版本 | 阶梯档位 | 兼容性证据 | 变更后预期结果 |
|---|---|---|---|---|---|

阶梯档位：`1-owner-bump` / `2-property-override` / `3-family-bom` / `4-per-gav-pin` / `5-exclusion-direct`（见 `owner-and-resolution.md`）。处置阶梯见 `treatment-ladder.md`。

## 4. 残差冲突与 Override

| 组件 | 残差证据 | 是否 Override | 兼容性 | 验证项 | 回滚 | 责任人 |
|---|---|---|---|---|---|---|

（无残差则写「无」）

## 5. 六层影响分析

| 层级 | 文件/模块 | 事实或推断 | 所需变更（仅描述，不实施） | 风险 |
|---|---|---|---|---|

层级取值：代码 / 配置 / 数据 / 接口 / 测试 / 部署

## 6. 风险与 SemVer 分类

| 组件 | 分类 | 说明 | 上游链接 |
|---|---|---|---|

分类取值：PATCH / MINOR / MAJOR / SECURITY / NON_SEMVER

## 7. 确认队列

| 组件 | 状态 | 问题 | 选项 |
|---|---|---|---|

状态：`ready` / `pending` / `blocked` / `decided` / `deferred`。  
`pending`=可行·待补证（选项仅 `defer`/`other`；问题须含待补证标记）；基线证实后升为 `ready`。  
人工答复后：`proceed`/`remove`/`exclude`/`replace` → `decided`；`defer` → `deferred`。`analysis_status=complete` 时不得残留 `ready`/`pending`。  
选项按**决策单元**逐条显式答复（禁止「全部 proceed」）：`proceed:g:a:v` / `remove` / `exclude` / `replace:g:a[:v]` / `defer` / `other`。  
无目标版本时每个需定版本或替换的单元必须由人选定。

## 8. 验证矩阵

| 范围 | 测试项 | 预期结果 | 证据状态 |
|---|---|---|---|

受影响测试范围：（列出测试文件，或写「空 — 存在验证缺口」）

## 9. 回滚与责任人

| 组件 | 触发条件 | 恢复目标（精确版本/配置） | 责任人 |
|---|---|---|---|

## 10. 未决问题与证据缺口

- （pending baseline：有序补证清单 — 恢复构建工具 / 分期 `dependency:tree` / 证实 `resolved_from`）
- （传递升降级：已探路径菜单摘要 — introducer / force-align / 换 starter 或换栈 / 原生改造；等人选）
-
