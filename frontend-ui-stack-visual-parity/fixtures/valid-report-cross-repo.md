# UI Stack Visual Parity — 定界包（cross-repo）

## 状态

| 字段 | 取值 |
|---|---|
| schema | visual-parity-report/v1 |
| producer | frontend-ui-stack-visual-parity |
| execution_scope | analysis_only |
| source_snapshot | abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789 |
| analysis_status | blocked |
| strategy_status | needs_choice |
| remediation_status | not_started |
| assessment_mode | strict_parity |
| parity_topology | cross-repo |
| behavior_parity_required | yes |
| visual_acceptance_required | yes |
| final_visual_result | pending |

## 1. 基线与假设

- baseline_root：`/repo/vue2-source`
- candidate_root：`/repo/vue3-host`
- forbid_baseline_mutation：yes
- baseline_artifacts_status：missing
- baseline_source / substitute_standard：A capture dir `/repo/vue2-source/.ui-stack-visual-parity/baseline`

### Capture context

| 字段 | 值 |
|---|---|
| adapter / browser | existing-e2e / Chromium 130 |
| viewport / device_scale_factor | 1440x900 / 1 |
| locale / timezone / theme | zh-CN / Asia-Shanghai / light |
| font_ready_condition | document.fonts.ready |
| animation_policy | disabled |
| data_fixture / dynamic_masks | list-page-seed / clock + iframe chrome |

### Required state evidence

| id | route | state | baseline | current | diff/policy | result |
|---|---|---|---|---|---|---|
| search-default | /users | default | A/b/1.png | B/c/1.png | pending | pending |
| search-wrap | /users | wrapped | A/b/2.png | B/c/2.png | pending | pending |
| table-empty | /users | empty | A/b/3.png | B/c/3.png | pending | pending |
| table-data | /users | data | A/b/4.png | B/c/4.png | pending | pending |
| cell-popper | /users | select open | A/b/5.png | B/c/5.png | pending | pending |

## 6. 验证清单

| Id | 结果 | 备注 |
|---|---|---|
| V0 | pass | baseline bound to A |
| V1 | pass | stable context |
| V2 | pending | candidate on B not yet |
| V3 | pending | |
| V4 | pending | |
| P1 | pending | |
| P2 | pending | |
| P3 | pending | |
| P4 | pending | |
| P5 | pending | |
| P6 | pending | |
| P7 | pending | |

## 9. Output index

- blocking_decisions：strategy for host UI mapping
- change_candidates：[]
- validation_scope：[V0-V4, P1-P7]
- residual_risks：[iframe chrome masks]
- artifact_index：[ui-stack-visual-parity-report.md, visual-summary.json, capture-manifest.json]
- next_action：capture candidate on B then diagnose
