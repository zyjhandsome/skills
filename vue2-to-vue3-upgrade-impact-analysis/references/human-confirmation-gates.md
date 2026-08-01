# Human confirmation gates

This skill ends at `analysis_status=complete`. It does not implement upgrades.
`batch_implementation_gate=ready` means **analysis handoff OK only** — never
install/codemod authorization. `implementation_readiness` is always
`not_assessed` in this skill.

## Waves

| Wave | Unit type | When | Options |
|---|---|---|---|
| 1 | Migration **path** | After draft; path row `ready` | `proceed:path:<id>` / `defer` / `other` |
| 2+ | **Subsystem** High/blocker | After path is `decided` | `proceed:subsystem:<id>` / `defer` / `other` |

Path ids: see `migration-path-ladder.md` (`compat-big-bang`, `direct-vue3`,
`microfrontend-coexist`, `deferred-inventory-only`). Wave 1 still picks one path
id; §3 must also state the three axes (`runtime_axis` / `build_axis` /
`topology_axis`).

Subsystem ids: see `subsystem-inventory.md`. Rows with `required_for_path=yes`
must enter the queue when `in_scope`.

## Queue statuses

| Status | Meaning | Agent action |
|---|---|---|
| `ready` | Askable | Ask **all** current ready units in **one wave**; each needs own answer |
| `pending` | Path/tooling catch-up only | `defer` / `other` only until promoted |
| `blocked` | Evidence gap | Do not ask proceed; gather evidence or restate |
| `decided` | Human proceeded | Cleared |
| `deferred` | Human deferred | Cleared for asking; **blocks handoff ready** if High/blocker or `required_for_path=yes` |

Medium/low subsystems may appear in inventory without entering the queue
unless `required_for_path=yes` or the caller expands scope.

## Status transition

| Condition | `analysis_status` | `decision_status` | `batch_implementation_gate` | `implementation_readiness` |
|---|---|---|---|---|
| Preflight hard fail | `blocked` | `not_needed` | `frozen` — no report write | `not_assessed` |
| Path or High/blocker/`required_for_path` still `ready`/`pending` | `partial` | `needs_choice` | `frozen` | `not_assessed` |
| Askable cleared; any High/blocker or `required_for_path=yes` is `deferred`/`blocked`; or §1 `lockfile_status` is `absent`/`unparsed` | `complete` allowed | `decided` | **`frozen`** | `not_assessed` |
| Path `decided`; every High/blocker and every `required_for_path=yes` is **`decided`**; §1 `lockfile_status: present`; no blocked residuals | `complete` | `decided` | **`ready`** (handoff only) | `not_assessed` |

Never `complete` while any `ready`/`pending` remains.
Never set `batch_implementation_gate=ready` while any High/blocker or
`required_for_path=yes` row is `deferred`/`blocked`.
Never paste draft and wait for「继续/放行」— **ask now**.

## Natural-language answers

| User says | Agent must |
|---|---|
| 「继续 / 放行 / 全部放行 / 别再问了 / 全部纳入」 | **Not** a proceed token. Re-prompt the current wave with verbatim options. Do not set `decided`. |
| Exact `proceed:path:<id>` / `proceed:subsystem:<id>` / `defer` / `other` | Record into `人工答复` and regenerate |
| Ambiguous mix | Ask once to pick a single verbatim token per unit |

Never infer Wave-1 path `decided` from blanket language, then skip or auto-answer Wave 2.

## Protocol

1. Draft full packet (profile + recommended path + axes + subsystems + queue).
2. Ask Wave 1 path immediately if `ready`.
3. After path answer recorded, regenerate; open Wave 2 for every High/blocker
   / `required_for_path=yes` `ready` subsystem in one wave.
4. `other` keeps unit askable until a final answer.
5. No blanket「全部 proceed」.
6. Record answers into `decision-records/`; regenerate; Agent-review → `complete`.
7. On complete banner: remind `batch_implementation_gate=ready` = handoff only;
   `implementation_readiness=not_assessed`; implementation needs separate auth.
