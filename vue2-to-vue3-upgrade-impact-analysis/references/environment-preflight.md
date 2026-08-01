# Environment preflight

Run before any analysis write. Prefer `scripts/preflight.py`.

## Hard gates (failure → packet `blocked`, no report write)

| Probe | Pass | Fail |
|---|---|---|
| Node | `node -v` on PATH, or a project pin tool reports an installed version (nvm/fnm/volta recorded) | Missing → exit `5` |
| Package manager detect | At least one of npm/pnpm/yarn/bun detectable **or** lockfile present implying manager | No manager binary and no lockfile → exit `5` |
| Python | `python` or `python3 --version` (for validators) | Missing → exit `5` |

## Soft records (not hard blocks)

- Host Node vs `package.json` `engines.node` mismatch → record in baseline
- Multiple lockfiles → record; ask which workspace/manager if ambiguous
- Package-manager detection can pass without a lockfile; consume
  `profile_inventory.py`'s `lockfile_status` separately and keep handoff frozen
  for `absent` / `unparsed`
- Multiple frontend workspaces → ask (not exit `5`)
- Network: npm registry HEAD + `https://v3-migration.vuejs.org/` HEAD in same wave; dual failure → offline confirm gate (not tool-preflight failure)

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
