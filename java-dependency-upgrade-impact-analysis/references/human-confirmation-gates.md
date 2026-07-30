# Human Confirmation Gates

This skill ends at a finalized analysis/decision packet (`analysis_status=complete`).
It does not implement upgrades.

## Modes

| Mode | Input | Ask |
|---|---|---|
| Exact target | clear `from → to` | Per **decision unit**: `proceed:groupId:artifactId:version` / `defer` / `other` (plus treatment-specific options when applicable) |
| Open target | GAV without `to`, inventory pick, CVE without fix version, or replace path | Per unit: recommended GA `g:a:v` (with URL) **or** `remove` / `exclude` / `replace:g:a[:v]` / `defer` / `other` — **human must pick**; Agent never defaults the target |

## Decision unit

One unit = same `authority_layer × boot_line` × same `recommended_treatment` × same
target version (or same replacement candidate set) × one family.  
Different families, treatments, or targets → separate units. See
`references/treatment-ladder.md`.

## Queue statuses

| Status | Meaning | Agent action |
|---|---|---|
| `ready` | Askable; awaiting human answer | List **all** ready units in the **same wave**; each needs its **own explicit answer** |
| `blocked` | Evidence / existence / GA / baseline gap | Do **not** ask proceed/defer; gather evidence or ask only to **restate target** (not proceed options) |
| `decided` | Human chose proceed / remove / exclude / replace | Keep in queue after regenerate; counts as cleared for completion |
| `deferred` | Human chose `defer` | Keep in queue; counts as cleared for completion |
| after `other` / clarifying follow-up | stays `ready` until follow-up records a final answer or rewrites/removes the candidate | Open next wave only; do not treat `other` as `decided`/`deferred` |

## Status transition (completion)

| Condition | `analysis_status` | `decision_status` | `batch_implementation_gate` |
|---|---|---|---|
| Batch-wide gate: environment preflight failed (`java` / selected `mvn`\|`gradle` / Python missing) | **`blocked`** | `not_needed` | `frozen` — chat-only gaps; **no report write** |
| Batch-wide gate: claimed `from` ≠ effective baseline (unresolved), or both registry+GitHub unreachable pending offline confirm | **`blocked`** | `not_needed` (no askable wave yet) | `frozen` |
| Any `ready` remains (batch-wide gate cleared) | `partial` | `needs_choice` | `frozen` |
| All askable units answered (`decided` / `deferred`); only evidence `blocked` rows remain (gaps documented) | **`complete` allowed** | `decided` | **`frozen`** (callers must not implement blocked rows) |
| Every unit `decided` or `deferred`; **no** `blocked` | `complete` | `decided` | `ready` |
| Nothing askable and nothing blocked (e.g. empty after inventory defer-all) | `complete` | `not_needed` or `decided` | per remaining work |

**Packet `analysis_status=blocked`** is for **batch-wide** blockers (environment preflight failure; baseline mismatch not yet chosen; offline gate awaiting human). It is **not** the same as a queue-row `blocked`. Environment-preflight failure: list missing probes in chat, do **not** write report files, and do **not** invent baselines from manifest skim — see `references/environment-preflight.md`. While packet status is `blocked`, do **not** keep or ask any `ready` rows — clear the batch-wide gate first (fix environment / pick baseline / confirm offline), then reclassify rows to `partial` + `needs_choice` if units become askable. Row-level existence/non-GA gaps alone keep those rows `blocked` but leave packet `partial` if other units are `ready`.

**Cleared queue** means: zero `ready` rows. Residual evidence-`blocked` rows do **not** block `analysis_status=complete`, but they **do** keep `batch_implementation_gate=frozen`.

**Unblocking an evidence-`blocked` row** (existence `no`/`unknown`, non-GA without allow, unresolved baseline on that row, or CVE with no findable GA fix): ask only to **restate a reachable GA target** (or abandon the row via follow-up `other` → next wave that rewrites/removes the candidate). Do **not** offer `proceed` / `defer` on that row while it is still evidence-`blocked`; `defer` is only for `ready` units. After a valid restatement, re-run existence precheck, then the row may become `ready` (or stay `blocked`).

Never set `analysis_status=complete` while any queue row is still `ready` or while `decision_status=needs_choice`.
Never set `analysis_status=blocked` while any queue row is `ready` (resolve or reclassify first).

## Protocol

1. Draft the full packet once (evidence + recommended treatment + queue).
2. If any `ready` remains: **ask now** in the same turn. Do not paste a draft and wait for “继续/放行”.
3. Never ask proceed/defer on `blocked` items (restating a missing target is allowed).
4. **No blanket `全部 proceed`.** Especially when `target_to` is missing: every unit that needs a version or replacement must get a human answer (`proceed:g:a:v` / `remove` / `exclude` / `replace:…` / `defer` / `other`).
5. Open-target / CVE-without-`to`: probe official fix range and owner security line first. If a GA fix is findable, put it in the question with URLs and set the unit **`ready`**. If no fix version is findable → keep evidence-`blocked` and ask only to **restate target** or `other` (abandon/rewrite next wave) — **never** invent a version and **never** offer `defer`/`proceed` while still `blocked`.
6. Record final answers into the decision section / decision file analogue in the report directory.
7. Regenerate or amend the packet: answered `ready` → `decided` or `deferred`; statuses reflect the table above. After `other`, the row **stays `ready`** until the follow-up wave records a final option (or the candidate is rewritten/removed).
8. Agent-review heuristics and upstream summaries; only then set `analysis_status=complete`.

## Option vocabulary

| Option | When | Queue status after |
|---|---|---|
| `proceed:g:a:v` | Exact or chosen GA target (upgrade / force-align / owner path) | `decided` |
| `remove` | Confirm unused direct removal | `decided` |
| `exclude` | Confirm transitive exclusion (regression warning already in record) | `decided` |
| `replace:g:a` or `replace:g:a:v` | Confirm component / introducer replacement | `decided` |
| `defer` | Park the unit | `deferred` |
| `other` | Free-form; triggers a follow-up wave | stays `ready` until follow-up |

## batch_implementation_gate

| Value | Meaning |
|---|---|
| `frozen` | Unconfirmed (`ready`) or evidence-`blocked` items remain — callers must not implement |
| `ready` | All batch items are `decided` or `deferred` (no `blocked`, no `ready`) |

`frozen` does **not** block finishing analysis once askable items are answered and remaining blockers are explicitly `blocked` with evidence gaps documented — but do not mark the whole batch gate `ready` while blockers exist.

## Pressure guards

| Rationalization | Response |
|---|---|
| “Deadline allows a temporary override.” | Deadline changes staging, not compatibility evidence. |
| “Declared pom version is enough.” | Re-check effective resolution. |
| “No mvn on PATH but mvnw exists — close enough.” | System `mvn`/`gradle` required; wrappers do not pass preflight. |
| “Skip Python until report time.” | Python is an environment-preflight hard gate (validator). |
| “Prefer Boot-managed without changing owner.” | Owner-first action or evidence it is impossible. |
| “Tests passed once so skip confirmation.” | Confirmation queue is still mandatory. |
| “No target version — pick the latest for me.” | Recommend a GA with evidence; still require per-unit human confirmation. |
| “Same wave means one answer for the whole batch.” | Same wave = list together; answers stay per decision unit. |
| “Beta/RC is fine until GA ships.” | Non-GA targets stay `blocked` unless the user explicitly allows non-GA. |
| “Blocked Netty forces a separate packet from Jackson.” | Same `authority_layer × boot_line` may keep ready + blocked rows together; do not over-split. |
| “Existence-404 row can be deferred to unfreeze the gate.” | No — restate a reachable target (or abandon via follow-up); `defer` only applies to `ready` units. |
