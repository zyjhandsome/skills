# 报告契约

## 文件名

- `java-dependency-upgrade-report.md`（必填）
- `decision-records/<groupId>__<artifactId>.md`（每个清单组件/族必填；`*` → `ALL`）
- `java-dependency-upgrade-report.json`（可选）

语言：可见正文默认简体中文；机器枚举、GAV、版本、路径、命令、URL 保持英文原文。

### 决策记录落盘

与报告**同目录**下建 `decision-records/`：

| 清单组件示例 | 文件名 |
|---|---|
| `com.fasterxml.jackson.core:jackson-databind` | `decision-records/com.fasterxml.jackson.core__jackson-databind.md` |
| `io.netty:netty-*` | `decision-records/io.netty__netty-ALL.md` |

字段见 `templates/decision-record.md` / `decision-record-schema.md`。
`analysis_status=complete` 时缺少对应决策记录 → 校验 **ERROR**；`partial` 时缺目录 → **WARN**。
队列组件键应与清单组件字面一致；族通配 `g:a-*` 可与族内成员 `g:a-foo` 互认，但仍推荐同字面键。

## 多批次目录布局（确定性命名）

混合表按「权威层 × Boot 线 × 构建变体 × 有界范围」拆包：

| 批次数 | 布局 |
|---|---|
| 1 | 报告直接写在证据目录根 |
| ≥2 | `<entry-kind>/<authority-layer>__<boot-line>__variant-<build-variant>__scope-<batch-scope>[__domain-<decision-domain>]/java-dependency-upgrade-report.md`，且根目录有 `BATCH-INDEX.md` |

- `entry-kind`：`exact` / `open-target`
- `authority-layer`：`jdk` / `boot-bom` / `platform-plugin` / `app-library`
- `boot-line`：`boot-<线>`（如 `boot-3.2.x`）或 `no-boot`；候选项字段 `boot_line=3.2.x` ↔ 目录 token `boot-3.2.x`
- `build-variant`：`default` 或 Maven profile / Gradle property 组合的稳定 slug
- `batch-scope`：有界模块或依赖族 slug；不得用 `all` 隐藏整仓无界探测
- `decision-domain`：仅同组合内必须隔离的 MAJOR/坐标迁移使用
- 示例：`exact/app-library__no-boot__variant-default__scope-commons-io/java-dependency-upgrade-report.md`
- MAJOR：`exact/app-library__no-boot__variant-default__scope-commons-lang__domain-commons-lang-major/java-dependency-upgrade-report.md`

`BATCH-INDEX.md` 必须使用结构化 Markdown 表，每行一个批次，**必须**写明：
目录路径、权威层、Boot 线、构建变体、批次范围、决策域（无则 `—`）、成员 GAV、
以及字面量字段名 `analysis_status` / `decision_status` / `batch_implementation_gate`
（附各批合法取值）。
每个批次目录内的文件名保持不变，便于调用方按固定路径读取。校验器会逐行
核对目录、层、Boot 线、成员、决策域和三状态值。

## 报告目录解析（对齐前端升级 Skill）

按优先级：

1. 显式 `--output-dir`（覆盖其它解析）
2. 既有 `--change-dir` → 写入  
   `<change-dir>/evidence/java-dependency-upgrade/`  
   OpenSpec 典型路径：`openspec/changes/<id>/evidence/java-dependency-upgrade/`
3. 均未提供时：在分析目标仓库下查找与本请求匹配的既有 `openspec/changes/<id>/`  
   - 唯一匹配 → 当作 `--change-dir`  
   - 多个 → 询问使用哪一个  
   - 没有 → 询问既有 `--change-dir` 或显式 `--output-dir`，然后停止写入直到明确

硬规则：

- 本技能可在**已存在**的 change 目录内创建 `evidence/java-dependency-upgrade/`
- **不得**自行创建 OpenSpec change、lifecycle 或并行状态文件
- **不得**在仓库根 invent 临时报告文件夹
- 路径未明确前：**允许只读分析**，**禁止写入**报告/证据文件

报告顶部须写出**实际解析到的报告路径**。

## 校验

出包前与决策后重生成时都要跑：

```shell
python scripts/validate_report.py <report.md>
python scripts/validate_report.py --evidence-dir <evidence-dir> --json
```

退出码 `0` 通过 / `3` 存在结构错误 / `4` 路径不存在。校验通过只代表**结构合规**，
不代表证据充分；owner 判定与上游依据仍需 Agent 复核。样例见 `fixtures/valid-report.md`（partial）、`fixtures/valid-report-complete.md`（定稿且可残留 blocked）、
`fixtures/valid-report-remove.md` / `valid-report-replace.md` / `valid-report-open-target.md` /
`valid-report-choose-alternative.md` / `valid-report-pending-baseline.md`，
以及多批布局 `examples/sample-evidence-multi/`（含 `BATCH-INDEX.md`）。
决策记录样例在 `fixtures/decision-records/`。
**注意：** `fixtures/` 根目录不是证据布局（文件名不是统一的 `java-dependency-upgrade-report.md`），
请用 `validate_report.py <fixture.md>` 校验单文件；多批请用
`validate_report.py --evidence-dir examples/sample-evidence-multi`。
不要对 `fixtures/` 根直接 `--evidence-dir`。

## 顶层状态字段

在 Markdown 报告顶部给出：

| 字段 | 取值 |
|---|---|
| `analysis_status` | `partial` / `blocked` / `complete`（`blocked`=批级环境前置/基线/离线闸，见 confirmation gates） |
| `decision_status` | `needs_choice` / `not_needed` / `decided` |
| `batch_implementation_gate` | `frozen` / `ready` |
| `behavior_parity_required` | `yes` / `no` |
| `network_mode` | `online` / `offline` / `partial` |
| `report_path` | 实际目录（绝对或相对仓库根） |

确认队列行状态与决策记录「确认队列状态」同枚举：`ready` / `pending` / `blocked` / `decided` / `deferred`（映射见 `decision-record-schema.md`）。

## 必选章节（按顺序）

1. 基线与假设
2. 依赖清单与解析路径
3. 主 Owner 决策
4. 残差冲突与 Override
5. 六层影响分析
6. 风险与 SemVer 分类
7. 确认队列
8. 验证矩阵
9. 回滚与责任人
10. 未决问题与证据缺口

## 确认队列表

| 组件 | 状态 | 问题 | 选项 |
|---|---|---|---|
| `g:a` | `ready`/`pending`/`blocked`/`decided`/`deferred` | 简短提问（含推荐处置与推荐 GA；`pending` 须含待补证标记） | `ready`：`proceed:…` / `remove` / `exclude` / `replace:…` / `defer` / `other`；`pending`：仅 `defer` / `other` |

同波可列出全部 `ready`/`pending` 单元，但**每个决策单元须有独立显式答复**；无 `to` 时禁止一条「全部 proceed」。  
人工答复后将队列状态改为 `decided`（proceed/remove/exclude/replace）或 `deferred`；`analysis_status=complete` 时不得残留 `ready`/`pending`。残留的证据型 `blocked` 可与 `complete` 共存（见 `human-confirmation-gates.md` 状态转移）。  
`blocked` 行的「选项」列只写重述目标 / `restate target` / `other`（放弃或改写），**不要**列出
`proceed`/`remove`/`exclude`/`replace`/`defer` 作为独立选项 token（说明性文字里提到这些词可以）。  
`pending` 行（可行·待补证）问题须含「待补证」/`pending-baseline`/「补证清单」；选项仅 `defer`/`other`，**不得** `proceed:`。  
`proceed:g:a:v` / `replace:g:a:v` 的版本必须与清单目标或推荐替代一致。

## 依赖清单表

| 组件 | 模块 | 当前解析版本 | 目标版本 | 方向 | 目标存在性 | 建议处置 | 推荐替代 | 替代存在性 | 依赖路径 | 有效 Owner | 权威层 | 风险 |

`目标存在性` 取 `target_artifact_exists` 的 `yes` / `no` / `unknown` / `n/a`；
取 `no` 或 `unknown` 且无已验证替代时必须为 `blocked`；若已有替代则用
`choose-alternative`（同 GAV 版本）或 `replace-*`（换坐标）进入 `ready`。探测证据
（HTTP 状态码 + `maven-metadata.xml` 实际发布版本范围）。  
`n/a` 仅用于 `remove` / `exclude` / `no-viable-path` 等无目标制品处置。
`建议处置` 取 `recommended_treatment`（见 `treatment-ladder.md`；分析无路写 `no-viable-path`，**不要**写 `defer`）。
非替代选择行的「推荐替代」写 `—`、「替代存在性」写 `n/a`。
`choose-alternative` / `replace-*` 行必须保留原请求并填写
`推荐替代=g:a[:v]`、`替代存在性=yes`；替代目标未验证可达前不得进入 `ready`。
非 GA 目标（`target_channel=non-ga`）默认不得进 `ready`。若用户**显式**允许非 GA，须在该清单行或队列行写入字面量 `non-ga-allowed`，校验器才放行 `ready`。

`方向=downgrade` 表示用户明确给出的降级目标：允许继续分析，不增加第二个
授权闸；风险必须标高，确认问题须醒目标注“降级/downgrade”。

目标可达但 `resolved_from` 未证实时：队列 **`pending`**（可行·待补证），在 §10 与决策记录写
有序补证清单与 `baseline_evidence_status`；**不要**因「缺环境证据」写成存在性式 `blocked`，
也**不要**在基线未证实前进 `ready`+`proceed`（见 `next-action-choice-menus.md` §A）。
基线证实后的传递升降级 `ready`「问题」须点名推荐路径（`move-introducer`/
`upgrade-introducer` 或破例 `force-align`）并摘要已探的换 starter / 换栈 / 原生改造选项（§B）。

## 横幅规则

- `needs_choice` + `ready` → 横幅：待人工确认；下一动作=提问
- `needs_choice` + `pending` → 横幅：待补基线证据；下一动作=补证清单（非降级否决）
- 证据阻塞 → 待补证据
- `batch_implementation_gate=frozen` → 整批不得实施（调用方）

## JSON（可选）

镜像：状态字段、`report_path`、`candidates[]`、`decision_records[]`、`confirmation_queue[]`、`evidence_gaps[]`。
