# 决策记录 — `groupId:artifactId`

> 枚举取值保持英文；字段名与说明默认简体中文。  
> 「确认队列状态」与报告确认队列表同一套枚举；见 `decision-record-schema.md` 映射表。

| 字段 | 内容 |
|---|---|
| 组件 | `groupId:artifactId`（含 classifier 时写明） |
| 模块 | |
| 版本（当前解析 → 目标） | |
| 目标存在性 | yes / no / unknown / n/a |
| 目标通道 | ga / non-ga / — |
| 请求目标（GAV / 版本 / 存在性） | （replace 时保留原请求） |
| 推荐替代目标（GAV / 版本 / 存在性） | （replace 时独立探测；ready 前必须为 yes） |
| 建议处置 | remove / upgrade-self / upgrade-owner / upgrade-introducer / move-self / move-owner / move-introducer / exclude / force-align / replace-component / replace-introducer / choose-alternative / no-viable-path |
| usage_status | used / unused / ambiguous / — |
| introducer_gav | （传递依赖时） |
| introducer_upgrade_available | yes / no / unknown / — |
| baseline_evidence_status | confirmed / pending-tooling / pending-tree / mismatch / — |
| 下一步补证 | （pending baseline 时：恢复 mvn → 分期 tree → 证实 from；见 next-action-choice-menus §A） |
| 路径选项菜单 | （传递升降级：A introducer / B force-align / C 换 starter / D 换栈 / E 原生改造 + 证据摘要） |
| 替代候选 | （replace-* 时 1–3 个） |
| scope | compile / runtime / provided / test / system |
| optional | yes / no |
| exclusions_present | yes / no |
| 依赖路径 | |
| 有效 Owner | |
| 权威层 | jdk / boot-bom / platform-plugin / app-library |
| Boot 线 | |
| 构建变体 | default / Maven profile slug / Gradle property slug |
| 批次范围 | 有界模块或依赖族 slug |
| Owner 阶梯档位 | 1-owner-bump / 2-property-override / 3-family-bom / 4-per-gav-pin / 5-exclusion-direct |
| 方向 | upgrade / downgrade / same / unknown |
| 入口来源 | inventory / exact-table / cve / other |
| 主 Owner 动作 | 已尝试 / 已证伪 + 证据（含属性名是否在 BOM 中核实） |
| 残差冲突 | |
| 兼容性证据（URL） | |
| 已命名验证项 | （含 japicmp/revapi 等机器可检项，若适用；exclude 须含回归） |
| 迁移路径选项（仅描述） | （MAJOR / replace 时命名 recipe/codemod 与残余风险；本技能不执行） |
| 回滚触发条件 + 恢复目标 | |
| 责任人 | |
| 推荐确认选项 | proceed:g:a:v / remove / exclude / replace:g:a[:v] / defer / other（与队列选项同词表；owner 路径仍写 proceed:…） |
| 确认队列状态 | ready / pending / blocked / decided / deferred |
| 人工答复 | （定稿后照抄：proceed:… / remove / exclude / replace:… / defer / other） |
