# Human Confirmation Gates

This skill ends at a finalized analysis/decision packet (`analysis_status=complete`).
It does not implement upgrades.

## Modes

| Mode | Input | Ask |
|---|---|---|
| Exact target | clear `from → to` | Per **decision unit**: `proceed:groupId:artifactId:version` / `defer` / `other` (plus treatment-specific options when applicable) |
| Open target | GAV without `to`, inventory pick, CVE without fix version, or replace path | Per unit: recommended GA `g:a:v` (with URL) **or** `remove` / `exclude` / `replace:g:a[:v]` / `defer` / `other` — **human must pick**; Agent never defaults the target |

## Decision unit

One unit = same `authority_layer × boot_line × build_variant × bounded batch_scope`
× same `recommended_treatment` × same target version (or replacement candidate
set) × one family. Different variants, scopes, families, treatments, or targets
→ separate units. See
`references/treatment-ladder.md`.

## Queue statuses

| Status | Meaning | Agent action |
|---|---|---|
| `ready` | Askable for a version/treatment move; awaiting human answer | List **all** ready units in the **same wave**; each needs its **own explicit answer** |
| `pending` | Target reachable + treatment known, but `resolved_from` / tooling not yet confirmed（可行·待补证） | Ask **tooling/baseline catch-up** only (`defer` / `other`); **no** `proceed:` until baseline confirmed → then promote to `ready` |
| `blocked` | Evidence / existence / GA / claimed-from mismatch gap，且没有已验证替代 | Do **not** ask proceed/defer; gather evidence or ask only to **restate target** |
| `decided` | Human chose proceed / remove / exclude / replace | Keep in queue after regenerate; counts as cleared for completion |
| `deferred` | Human chose `defer` | Keep in queue; counts as cleared for completion |
| after `other` / clarifying follow-up | stays `ready`/`pending` until follow-up records a final answer or rewrites/removes the candidate | Open next wave only; do not treat `other` as `decided`/`deferred` |

## Status transition (completion)

| Condition | `analysis_status` | `decision_status` | `batch_implementation_gate` |
|---|---|---|---|
| Batch-wide gate: environment preflight failed (`java` / selected `mvn`\|`gradle`\|wrapper / Python missing; `preflight.py` exit `5`) | **`blocked`** | `not_needed` | `frozen` — chat-only gaps; **no report write** |
| Dual-build needs tool choice (`preflight.py` exit `6`) | stay pre-packet | — | ask Maven vs Gradle; **not** batch-wide `blocked`; re-run with `--build-tool` |
| Batch-wide gate: claimed `from` ≠ effective baseline (unresolved), or both registry+GitHub unreachable pending offline confirm | **`blocked`** | `not_needed` (no askable wave yet) | `frozen` |
| Any `ready` or `pending` remains (batch-wide gate cleared) | `partial` | `needs_choice` | `frozen` |
| All askable units answered (`decided` / `deferred`); only evidence `blocked` rows remain (gaps documented) | **`complete` allowed** | `decided` | **`frozen`** (callers must not implement blocked rows) |
| Every unit `decided` or `deferred`; **no** `blocked` / `pending` / `ready` | `complete` | `decided` | `ready` |
| Nothing askable and nothing blocked (e.g. empty after inventory defer-all) | `complete` | `not_needed` or `decided` | per remaining work |

**Packet `analysis_status=blocked`** is for **batch-wide** blockers (environment preflight failure; baseline mismatch not yet chosen; offline gate awaiting human). It is **not** the same as a queue-row `blocked`. Environment-preflight failure: list missing probes in chat, do **not** write report files, and do **not** invent baselines from manifest skim — see `references/environment-preflight.md`. While packet status is `blocked`, do **not** keep or ask any `ready`/`pending` rows — clear the batch-wide gate first (fix environment / pick baseline / confirm offline), then reclassify rows to `partial` + `needs_choice` if units become askable. Row-level existence/non-GA gaps alone keep those rows `blocked` but leave packet `partial` if other units are `ready`/`pending`.

**Cleared queue** means: zero `ready` and zero `pending` rows. Residual evidence-`blocked` rows do **not** block `analysis_status=complete`, but they **do** keep `batch_implementation_gate=frozen`.

**Requested target missing:** preserve the request and verify 1–3 alternatives.
At least one verified same-GAV version or replacement coordinate becomes a
`ready` choice (`proceed:g:a:v` for same GAV; `replace:g:a:v` for changed
coordinates). Never substitute automatically. Only zero verified candidates (or
unreachable evidence) stays `blocked` and asks to **restate a reachable GA target**.

Never set `analysis_status=complete` while any queue row is still `ready`/`pending` or while `decision_status=needs_choice`.
Never set `analysis_status=blocked` while any queue row is `ready`/`pending` (resolve or reclassify first).

## Protocol

1. Draft the full packet once (evidence + recommended treatment + queue).
2. If any `ready` or `pending` remains: **ask now** in the same turn. Do not paste a draft and wait for “继续/放行”.
3. Never ask proceed on `blocked`/`pending` items (`pending` may offer `defer`/`other` for tooling catch-up; `blocked` only restates a missing target).
4. **No blanket `全部 proceed`.** Especially when `target_to` is missing: every unit that needs a version or replacement must get a human answer (`proceed:g:a:v` / `remove` / `exclude` / `replace:…` / `defer` / `other`).
5. Open-target / CVE-without-`to`: probe official fix range and owner security line first. If a GA fix is findable, put it in the question with URLs and set the unit **`ready`**. If no fix version is findable → keep evidence-`blocked` and ask only to **restate target** or `other` (abandon/rewrite next wave) — **never** invent a version and **never** offer `defer`/`proceed` while still `blocked`.
6. Explicit `from > to` is already permission to analyze a downgrade. Add a prominent downgrade warning and High scrutiny, then use the normal per-unit choice; do not ask for a second authorization.
6a. **Feasible but pending baseline** (Maven/`dependency:tree` not yet confirming `resolved_from`): queue status **`pending`** (not `blocked`, not `ready`). Publish the ordered补证清单 in chat + §10 + Decision Record; options = `defer` / `other` only. After baseline confirms, regenerate as `ready` with the full path menu + `proceed:` (`references/next-action-choice-menus.md` §A).
6b. **Transitive upgrade/downgrade:** confirmation「问题」must name the recommended path (introducer vs force-align) and summarize explored alternatives (other starter/BOM, stack replace, native rewrite). Do not offer leaf-pin as the only option (`references/next-action-choice-menus.md` §B).
7. Record final answers into the decision section / decision file analogue in the report directory.
8. Regenerate or amend the packet: answered `ready` → `decided` or `deferred`; statuses reflect the table above.
9. Agent-review heuristics and upstream summaries; only then set `analysis_status=complete`.

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
| `frozen` | Unconfirmed (`ready`/`pending`) or evidence-`blocked` items remain — callers must not implement |
| `ready` | All batch items are `decided` or `deferred` (no `blocked`, no `ready`, no `pending`) |

`frozen` does **not** block finishing analysis once askable items are answered and remaining blockers are explicitly `blocked` with evidence gaps documented — but do not mark the whole batch gate `ready` while blockers exist.

## Pressure guards

| Rationalization | Response |
|---|---|
| “Deadline allows a temporary override.” | Deadline changes staging, not compatibility evidence. |
| “JAVA_HOME unset but a JDK is installed somewhere.” | Set `JAVA_HOME` (and PATH) for the session and re-run `java -version`; do not skip the JDK gate. |
| “No mvn on PATH but mvnw exists — close enough.” | Wrapper-only is a **graded pass** if `./mvnw -v` / `./gradlew -v` works; record `build_tool_source=wrapper`. Neither system nor wrapper → hard block. |
| “Skip Python until report time.” | Python is an environment-preflight hard gate (validator). |
| “Prefer Boot-managed without changing owner.” | Owner-first action or evidence it is impossible. |
| “Tests passed once so skip confirmation.” | Confirmation queue is still mandatory. |
| “No target version — pick the latest for me.” | Recommend a GA with evidence; still require per-unit human confirmation. |
| “Same wave means one answer for the whole batch.” | Same wave = list together; answers stay per decision unit. |
| “Beta/RC is fine until GA ships.” | Non-GA targets stay `blocked` unless the user explicitly allows non-GA. |
| “Blocked Netty forces a separate packet from Jackson.” | Same packet key (`authority × boot × variant × scope`) may keep ready + blocked rows together; do not over-split. |
| “Existence-404 row can be deferred to unfreeze the gate.” | No — restate a reachable target (or abandon via follow-up); human `defer` only applies to `ready` units. Inventory treatment for no path is `no-viable-path`, not `defer`. |
| “Missing Maven/tree ⇒ block the Eureka downgrade.” | Target reachable ⇒ queue-`pending`（可行·待补证）; restore tooling + staged tree first. Not an existence/`blocked` downgrade veto. |
| “Transitive downgrade = pin the leaf.” | Prefer `move-introducer`; `force-align` needs a full DR; also offer verified replace-starter / stack / native-rewrite choices. |
