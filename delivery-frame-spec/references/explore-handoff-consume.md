# Explore → Frame handoff consume（Delivery Family 共用）

`delivery-frame-spec` 在收到 `delivery-explore` handoff 时按本表消费字段。不要从 explore 输出发明第二状态源；OpenSpec change 仍由本阶段创建/恢复。

硬前提 profile（`delivery-family/1.3`）：`evidence_mode` 必须为 `full`；不存在 degraded 续跑。Explore 若遇硬前提故障应已停止，不得带着非标称能力快照进入 Frame 转换。

## Incoming field → how consumed

| Incoming field | How this skill consumes it |
|---|---|
| `family_version` | Must be a supported Delivery Family major before automatic chaining |
| `source_revision` | Compare with current repo/artifact state; mismatch makes the handoff stale and triggers state recovery |
| `capability_snapshot` | Expect nominal values under hard profile; any non-nominal value blocks transition (`next_skill`/`next_action` null) and uses the fixed 3-line failure report in `family-contract.md` |
| `capability_bindings` | Reuse resolved aliases/versions that are still valid; refresh route-required operations when missing or changed |
| `evidence_mode` | Must be `full`; anything else is a hard-profile fault — stop and report, do not frame |
| `stage_payload.direction_alignment` | Must be `selected` before framing; `needs_choice` returns to `delivery-explore` instead of inventing a locked goal |
| `stage_payload.chosen_direction` | Seed **Intent** goal (user may revise; confirmation is still required) |
| `stage_payload.non_goals` | Seed **Intent** boundaries / non-goals |
| `stage_payload.code_anchors` | Starting points for **Code Facts** / **Mount Points** targeted inspection |
| `stage_payload.risk_signal` | Routing **hint only** (`none` → likely Quick/Standard; `standard-likely` → Standard/Medium; `high-likely` → High). Re-derive route/risk from evidence; never treat explore’s signal as an approved risk level |
| `stage_payload.unknowns` | Candidate entries for **Open Questions** (not automatic decisions) |
| `state_source` | Must be `none`; this skill creates/recovers the OpenSpec change as the sole state source |
| `required_inputs` / `stop_condition` | Honor stop; otherwise require user confirmation of the chosen (or revised) direction before the specification gate |

## Checkbox self-check（与 brief 一致）

规格闸门 / Quick 契约 go 前，活跃 change 的 `proposal.md` 必须含 **Explore Handoff Consume** / `Explore 交接消费`（见 `brief-template.md`）：

- 有 explore handoff：五条均勾选，且与简报/契约正文一致（空节、仅聊天摘要、未勾选 = 闸门失败）。
- 无 explore handoff：整节一行 `N/A — 无 explore handoff`（不得省略）。
