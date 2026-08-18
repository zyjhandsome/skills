# Environment preflight

Run before any analysis write. Prefer `scripts/preflight.py`.

## Hard gates (failure → packet `blocked`, no report write)

| Probe | Pass | Fail |
|---|---|---|
| Node | `node -v` on PATH, or a project pin tool reports an installed version (nvm/fnm/volta recorded) | Missing → exit `5` |
| Package manager detect | At least one of npm/pnpm/yarn/bun detectable **or** lockfile present implying manager | No manager binary and no lockfile → exit `5` |
| Python | `python` or `python3 --version` (for validators) | Missing → exit `5` |

## Soft records (not hard blocks)

- Host Node vs project Node contract mismatch → record in baseline. The
  contract includes `.nvmrc`, `.node-version`, Volta, `engines.node`, CI
  workflow/setup-node, Docker/devcontainer base image, and deployment build
  settings when present; do not reduce it to `package.json#engines.node`.
- Multiple lockfiles → record; ask which workspace/manager if ambiguous
- Package-manager detection can pass without a lockfile; consume
  `profile_inventory.py`'s `lockfile_status` separately and keep handoff frozen
  for `absent` / `unparsed`
- Multiple frontend workspaces → ask (not exit `5`)
- Network: npm registry HEAD + `https://v3-migration.vuejs.org/` HEAD in same wave; dual failure → offline confirm gate (not tool-preflight failure)

## Node is a two-plane decision

Do not collapse Node compatibility into “Vue 3 needs Node X”. `vue` is a
browser/runtime package and may not declare an `engines.node` floor; the
effective floor usually comes from the selected build/test/SSR/package-manager
toolchain and changes by version.

Record both planes in report §1:

1. **Current plane** — active host Node plus every project/CI/container/deploy
   declaration. State which version is known to run the existing baseline; a
   pin alone is a contract signal, not proof of a green build. Start from
   `profile_inventory.py`'s `node_pins` and `node_contract_evidence`, then fill
   any deployment-provider settings the repository cannot expose.
2. **Target plane** — choose concrete target versions before claiming a Node
   range. Fetch each execution-critical package's `engines.node` from registry
   metadata and cross-check official release/migration docs. At minimum cover
   the selected build tool and Vue plugin, test runner, SSR framework when
   present, and pinned package manager. Record packages that declare no Node
   engine instead of inventing one.

Compute the satisfiable intersection, preserving disjoint semver ranges such as
`^20.19.0 || >=22.12.0`; do not reduce them to a misleading single integer.
Then classify:

| `node_compatibility_status` | Meaning | Handoff effect |
|---|---|---|
| `compatible` | one supported Node range covers current baseline and target toolchain | may proceed |
| `upgrade-required` | target floor is higher, but a staged or temporary dual-Node route is selected | `build` is High + `required_for_path=yes`; human decision required |
| `conflict` | current and target contracts have no proven transition | frozen |
| `unknown` | target versions/engines or current baseline evidence are insufficient | frozen |

Allowed `node_transition_strategy` values are `same-node`,
`upgrade-before-vue`, `temporary-dual-node`, `blocked`, and `undecided`.
For `upgrade-before-vue`, name a pre-change build/test under the target Node as
implementation evidence. For `temporary-dual-node`, name both lanes, their
owners (local/CI/container/deploy), the cutover condition, and removal
condition. Never silently change only the analyst's local Node.

## Exit codes (`preflight.py`)

| Code | Meaning |
|---|---|
| `0` | Hard gates passed |
| `5` | Hard gate failed — chat gaps only, no report |
| `2` | Usage error |

## Agent protocol

1. Run preflight with `--project-root`.
2. On exit `5`: list missing probes in Chinese; set mental `analysis_status=blocked`; stop.
3. On exit `0`: proceed to inventory / analysis; network gaps use offline gate after human confirm.
