# Delivery Visual Evidence

> Delivery family 自有验证记录。外部报告只填路径/digest，不复制正文，也不依赖其 schema 或 Skill。

| 字段 | 取值 |
|---|---|
| schema | delivery-visual-evidence/v1 |
| producer | delivery-execute-verify |
| state_owner | openspec_change |
| implementation_authority | delivery |
| change_dir | <absolute OpenSpec change directory> |
| source_artifact_revision | <approved-64-hex> |
| analysis_status | complete |
| remediation_status | done |
| assessment_mode | strict_parity / consistency_review |
| visual_acceptance_required | yes |
| final_visual_result | pass |
| adapter / browser | |
| viewport / device_scale_factor | |
| locale / timezone / theme | |
| font_ready_condition | |
| animation_policy | |
| data_fixture / dynamic_masks | |

- baseline_source / substitute_standard：<image-path> | <sha256-64-hex>
- Implementation gate reference：approver / RFC3339 / approved-64-hex-revision
- External artifacts（optional）：path / digest / `claims_used`
  白名单（仅这些）：`baseline_state_ids` · `identity_route` · `identity_marker` ·
  `comparison_boundary` · `style_closure_status` · `color_metrics` ·
  `typography_metrics` · `icon_identity` · `table_metrics` · `rollback_fixture`
  引用外部字段不能让 G9 `final_visual_result` 自动 pass。

### Required state evidence

| id | route | state | baseline_path | baseline_digest | current_path | current_digest | diff_path | diff_digest | policy | result |
|---|---|---|---|---|---|---|---|---|---|---|

`policy` 只能为 `strict`、`tolerance_bound` 或 `explicitly_accepted`。

## Verification

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
