# 决策记录 — `org.yaml:snakeyaml`

| 字段 | 内容 |
|---|---|
| 组件 | `org.yaml:snakeyaml` |
| 模块 | `service-api` |
| 版本（当前解析 → 目标） | 2.0 → 2.2（推荐 GA，待人确认） |
| 目标存在性 | yes |
| 目标通道 | ga |
| 建议处置 | upgrade-owner |
| usage_status | used |
| scope | compile |
| optional | no |
| exclusions_present | no |
| 依赖路径 | `spring-boot-starter` → snakeyaml |
| 有效 Owner | boot-bom |
| 权威层 | boot-bom |
| Boot 线 | 3.2.x |
| 构建变体 | default |
| 批次范围 | yaml |
| Owner 阶梯档位 | 2-property-override |
| 方向 | upgrade |
| 入口来源 | cve |
| 主 Owner 动作 | 已核实 effective POM 中 `snakeyaml.version`，建议 Owner 属性覆盖 |
| 兼容性证据（URL） | https://github.com/advisories/GHSA-mjmj-j48q-9wg2 |
| 已命名验证项 | 应用上下文启动；YAML 配置绑定回归 |
| 回滚触发条件 + 恢复目标 | 启动/绑定失败 → 恢复 `snakeyaml.version=2.0` |
| 责任人 | 平台组 |
| 确认队列状态 | ready |
| 推荐确认选项 | `proceed:org.yaml:snakeyaml:2.2` / `defer` / `other` |
| 人工答复 | — |
