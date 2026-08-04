# UI Stack Visual Parity — 定界包

> 保存为 `ui-stack-visual-parity-report.md`。  
> 枚举、包名、路径、类前缀、命令、URL 保持英文原文；说明默认简体中文。

## 状态

| 字段 | 取值 |
|---|---|
| schema | visual-parity-report/v1 |
| producer | frontend-ui-stack-visual-parity |
| execution_scope | analysis_only / analysis_and_remediation |
| source_snapshot | git SHA / content hash / working-tree timestamp |
| analysis_status | partial / blocked / complete |
| strategy_status | needs_choice / decided / not_needed |
| remediation_status | not_started / awaiting_go / in_progress / done / skipped |
| behavior_parity_required | yes / no |
| report_path | 实际报告目录（禁止单独 `.`） |
| evidence_as_of | YYYY-MM-DD |
| packet_revision | r1 / r2 / … |
| assessment_mode | strict_parity / consistency_review |
| behavior_parity_required | yes / no |
| visual_acceptance_required | yes / no |
| final_visual_result | pending / pass / fail |

**横幅：** （定界中 / 待选策略 / 待 go 修复 / 修复完成）

## 1. 基线与假设

- 项目根 / 前端 workspace：
- 主样本页（路由或文件）：
- 辅样本页（若有）：
- 表格主次：`table.primary` / `table.secondary`
- 假设与限制：
- baseline_source / substitute_standard：

### Capture context

| 字段 | 值 |
|---|---|
| adapter / browser | |
| viewport / device_scale_factor | |
| locale / timezone / theme | |
| font_ready_condition | |
| animation_policy | |
| data_fixture / dynamic_masks | |

## 2. CSS / UI 栈画像

| 字段 | 值 | 证据（路径） |
|---|---|---|
| tailwind.preflight | | |
| tailwind.prefix | | |
| tailwind.important | | |
| ui_kit | | |
| ui_kit.theme_vars | | |
| css_entry_order | | |
| table.primary / secondary | | |
| icons / heavy_css_libs | | |

## 3. 症状与分层结果

| 层 | 结果（好/坏/未测） | 事实或推断 |
|---|---|---|
| Preflight 对照 | | |
| 仅搜索区 | | |
| 空表 | | |
| 表内控件 | | |
| 其他（拖拽/图标/…） | | |

### Required state evidence

| id | route | state | baseline | current | diff/policy | result |
|---|---|---|---|---|---|---|

## 4. 原因排序

1.
2.
3.

## 5. 策略

- primary_cause：
- required_remediations：
- optional_remediations：
- 备选：
- 可能改动的文件：
- 禁止范围：
- 残留风险：

### 策略确认

- 状态：needs_choice / decided  
- 用户选择：  
- 批准人 / 时间 / packet_revision：

## 6. 验证清单

| Id | 结果 | 备注 |
|---|---|---|
| V0 | | |
| V1 | | |
| V2 | | |
| V3 | | |
| V4 | | |
| P1 | | |
| P2 | | |
| P3 | | |
| P4 | | |
| P5 | | |
| P6 | | |
| P7 | | |
| S1 | skip / | |
| S2 | skip / | |

## 7. 状态与修复记录

- Phase B go：未批准 / 已批准（原文 token + 批准人 + 时间 + packet_revision）/ N/A-analysis-only
- 已改文件：
- 未做项 / 跟进：

## 8. 未决问题

-

## 9. Output index

- blocking_decisions：
- change_candidates：
- validation_scope：
- residual_risks：
- artifact_index：report / visual-summary.json / capture-manifest.json / image paths
- next_action：complete / choose_strategy / approve_remediation / rerun_capture
