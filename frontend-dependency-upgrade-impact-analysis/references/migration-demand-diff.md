# Migration demand diff (A→B)

Use when Vue2 source **A** content will be adapted into existing Vue3 host **B**.
This is **not** an in-place upgrade of A and **not** an exact `from→to` on B alone.

## Inputs

| Input | Meaning |
|---|---|
| `--source-root` | A (read-only) |
| `--implementation-target` | B (analysis/implement-on) |
| `--output-dir` | Writable report dir (must be confirmed by caller) |
| `--closure-packages` | Optional allowlist of package names for page closure |
| `--stack-map` | Optional JSON `{ "element-ui": "element-plus", ... }` |

## Dispositions

| Id | Meaning | Queued? |
|---|---|---|
| `reuse-B` | B has package with same major (or host `vue`) | no |
| `reuse-B-major-review` | B has package but **major differs** | **yes** |
| `add-to-B` | Missing on B; human must approve adding | yes |
| `replace-as-B-stack` | A package maps to a different host stack package | yes |
| `copy-local` | Vendor/first-party snippet; copy into B, no npm add | yes |
| `unknown` | Needs human triage | yes |

## Hard rules

- `forbid_source_mutation: yes` — never edit A from this mode
- Do not recommend installing Vue2 or `@vue/compat` on B as the primary path
- **Lock dual-root:** `host_lockfile_status` (B) drives `batch_implementation_gate`;
  `source_lockfile_status` (A) is informational only for host-port
- `batch_implementation_gate=ready` only when B lock is `present` and every
  askable demand row is decided via `--decision-file`
- Prefer page-closure demand sets over A's entire `package.json`
- UI `replace-as-B-stack` (e.g. `element-ui`) emits
  `visual_strategy_hint=needs_choice` for the visual skill
- Exit `7` when queue non-empty; reject「继续 / 全部放行 / 别再问了 / 全部纳入」

## Generator

```shell
python scripts/generate_migration_demand_diff.py \
  --source-root <A> \
  --implementation-target <B> \
  --output-dir <dir> \
  [--closure-packages pkgs.txt] \
  [--stack-map map.json] \
  [--decision-file decisions.json]
```

Outputs: `migration-demand-diff-report.md`, `dependency-summary.json`, `demand-diff.json`.

`decisions.json` example:

```json
{
  "element-ui": "proceed:demand:element-ui:replace-as-B-stack",
  "axios": "proceed:demand:axios:reuse-B-major-review"
}
```
