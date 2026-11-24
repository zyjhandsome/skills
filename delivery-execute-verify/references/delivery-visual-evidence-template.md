# Delivery Visual Evidence

> Delivery family 自有验证记录，用来证明已批准规格里的外观类 Scenario 成立。外部报告只能在 handoff 的 `external_artifacts` 里以路径加 digest 引用，不能替代本记录。

| 字段 | 取值 |
|---|---|
| schema | delivery-visual-evidence/v1 |
| producer | delivery-execute-verify |
| state_owner | openspec_change |
| change_dir | <change 目录；相对本报告所在目录，或绝对路径> |
| source_artifact_revision | sha256:<实现闸门绑定的修订> |
| assessment_mode | strict_parity / consistency_review / spec_assertion |
| final_visual_result | pass |
| adapter / browser | |
| viewport / device_scale_factor | |
| locale / timezone / theme | |
| font_ready_condition | |
| animation_policy | |
| data_fixture / dynamic_masks | |

- baseline_source / substitute_standard：<按下表填写>
- Implementation gate reference：<批准人> / <RFC3339> / sha256:<修订>

| assessment_mode | 何时用 | baseline_source / substitute_standard | 每行的 baseline、diff 列 |
|---|---|---|---|
| strict_parity | 有可追溯的基线图，要求与基线一致 | `<图片路径> | <sha256 64 位 hex>` | 必填图片和摘要 |
| consistency_review | 没有同源基线，按已批准的替代标准对照 | `approved-substitute:<引用> | <批准人> | sha256:<修订>` | 必填图片和摘要 |
| spec_assertion | 新界面，没有基线；逐条验证规格里的外观断言 | `n/a` | 写 `n/a`，`assertion` 列必填 |

### Required state evidence

| id | route | state | baseline_path | baseline_digest | current_path | current_digest | diff_path | diff_digest | assertion | policy | result |
|---|---|---|---|---|---|---|---|---|---|---|---|

`id` 与 Plan「Visual validation matrix」里 `required_for_verified=yes` 的行一一对应，校验器从已批准的矩阵读取必测 ID。`assertion` 写可证伪的外观断言；`strict_parity` 和 `consistency_review` 可写 `n/a`。`policy` 只能是 `strict`、`tolerance_bound` 或 `explicitly_accepted`。
