# 报告契约

## 文件名

- `java-dependency-upgrade-report.md`（必填）
- `java-dependency-upgrade-report.json`（可选）

语言：可见正文默认简体中文；机器枚举、GAV、版本、路径、命令、URL 保持英文原文。

## 多批次目录布局（确定性命名）

混合表按「一层权威 × 一条 Boot 线」拆包后，目录名不得逐次自拟：

| 批次数 | 布局 |
|---|---|
| 1 | 报告直接写在证据目录根 |
| ≥2 | `<entry-kind>/<authority-layer>__<boot-line>/java-dependency-upgrade-report.md`，且证据目录根**必须**有 `BATCH-INDEX.md` |

- `entry-kind`：`exact` / `open-target`
- `authority-layer`：`jdk` / `boot-bom` / `platform-plugin` / `app-library`
- `boot-line`：`boot-<线>`（如 `boot-3.2.x`）或 `no-boot`
- 示例：`exact/app-library__no-boot/java-dependency-upgrade-report.md`

`BATCH-INDEX.md` 每行（或每节）一个批次，**必须**写明：目录路径
（`<entry-kind>/<authority-layer>__<boot-line>/`）、权威层、Boot 线、成员 GAV、
以及字面量字段名 `analysis_status` / `decision_status` / `batch_implementation_gate`
（附各批取值）。每个批次目录内的文件名保持不变，便于调用方按固定路径读取。
校验器会检查索引非空、含上述三字段名，且每个批次目录被点名。

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
不代表证据充分；owner 判定与上游依据仍需 Agent 复核。样例见 `fixtures/valid-report.md`（partial）与
`fixtures/valid-report-complete.md`（定稿且可残留 blocked）。  
**注意：** `fixtures/` 是单文件样例目录（文件名不是 `java-dependency-upgrade-report.md`），
请用 `validate_report.py <fixture.md>` 校验；不要对 `fixtures/` 直接 `--evidence-dir`
（证据目录布局要求根下或批次子目录中存在 `java-dependency-upgrade-report.md`）。

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

确认队列行状态与决策记录「确认队列状态」同枚举：`ready` / `blocked` / `decided` / `deferred`（映射见 `decision-record-schema.md`）。

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
| `g:a` | `ready`/`blocked`/`decided`/`deferred` | 简短提问（含推荐处置与推荐 GA） | `proceed:…` / `remove` / `exclude` / `replace:…` / `defer` / `other` |

同波可列出全部 `ready` 单元，但**每个决策单元须有独立显式答复**；无 `to` 时禁止一条「全部 proceed」。  
人工答复后将队列状态改为 `decided`（proceed/remove/exclude/replace）或 `deferred`；`analysis_status=complete` 时不得残留 `ready`。残留的证据型 `blocked` 可与 `complete` 共存（见 `human-confirmation-gates.md` 状态转移）。  
`blocked` 行的「选项」列只写重述目标 / `other`（放弃或改写），**不要**列出 `proceed`/`defer`。

## 依赖清单表

| 组件 | 模块 | 当前解析版本 | 目标版本 | 目标存在性 | 建议处置 | 依赖路径 | 有效 Owner | 权威层 | 风险 |

`目标存在性` 取 `target_artifact_exists` 的 `yes` / `no` / `unknown` / `n/a`；
取 `no` 或 `unknown` 时该行必须为 `blocked`，并在「未决问题与证据缺口」写出探测证据
（HTTP 状态码 + `maven-metadata.xml` 实际发布版本范围）。  
`n/a` 仅用于 `remove` / `exclude` 等无目标制品处置。  
`建议处置` 取 `recommended_treatment`（见 `treatment-ladder.md`）。  
非 GA 目标（`target_channel=non-ga`）默认不得进 `ready`。若用户**显式**允许非 GA，须在该清单行或队列行写入字面量 `non-ga-allowed`，校验器才放行 `ready`。

## 横幅规则

- `needs_choice` + `ready` → 横幅：待人工确认；下一动作=提问
- 证据阻塞 → 待补证据
- `batch_implementation_gate=frozen` → 整批不得实施（调用方）

## JSON（可选）

镜像：状态字段、`report_path`、`candidates[]`、`decision_records[]`、`confirmation_queue[]`、`evidence_gaps[]`。
