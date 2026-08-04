# UI Stack Visual Parity — 定界包

## 状态

| 字段 | 取值 |
|---|---|
| schema | visual-parity-report/v1 |
| producer | frontend-ui-stack-visual-parity |
| execution_scope | analysis_and_remediation |
| source_snapshot | 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef |
| analysis_status | complete |
| strategy_status | decided |
| remediation_status | done |
| assessment_mode | strict_parity |
| behavior_parity_required | yes |
| visual_acceptance_required | yes |
| final_visual_result | pass |

## 1. 基线与假设

- baseline_source / substitute_standard：git:before-upgrade/screenshots

### Capture context

| 字段 | 值 |
|---|---|
| adapter / browser | existing-e2e / Chromium 130 |
| viewport / device_scale_factor | 1440x900 / 1 |
| locale / timezone / theme | zh-CN / Asia-Shanghai / light |
| font_ready_condition | document.fonts.ready |
| animation_policy | disabled |
| data_fixture / dynamic_masks | list-page-seed / clock only |

### Required state evidence

| id | route | state | baseline | current | diff/policy | result |
|---|---|---|---|---|---|---|
| search-default | /users | default | b/1.png | c/1.png | d/1.png | pass |
| search-wrap | /users | wrapped | b/2.png | c/2.png | d/2.png | pass |
| table-empty | /users | empty | b/3.png | c/3.png | d/3.png | pass |
| table-data | /users | data | b/4.png | c/4.png | d/4.png | pass |
| cell-popper | /users | select open | b/5.png | c/5.png | d/5.png | pass |

## 6. 验证清单

| Id | 结果 | 备注 |
|---|---|---|
| V0 | pass | baseline bound |
| V1 | pass | stable context |
| V2 | pass | all states captured |
| V3 | pass | bundle revision matches |
| V4 | pass | final pass |
| P1 | pass | aligned |
| P2 | pass | size scale |
| P3 | pass | table chrome |
| P4 | pass | centered |
| P5 | pass | popper OK |
| P6 | pass | vars apply |
| P7 | pass | non-table OK |

## 7. 状态与修复记录

- Phase B go：go:visual-fix / user / 2026-08-04T10:00:00+08:00 / r2

## 9. Output index

- blocking_decisions：[]
- change_candidates：[]
- validation_scope：[V0-V4, P1-P7]
- residual_risks：[]
- artifact_index：[ui-stack-visual-parity-report.md, visual-summary.json, capture-manifest.json, b/, c/, d/]
- next_action：complete
