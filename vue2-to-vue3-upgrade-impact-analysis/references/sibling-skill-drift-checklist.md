# Sibling skill drift checklist (maintainer)

This skill stays **independent**: no imports, no runtime calls, and no required
loading of other skills.

When changing confirmation-queue, status-axis, or `batch_implementation_gate`
semantics here, manually compare (do not couple) with the sibling analysis skill
`frontend-dependency-upgrade-impact-analysis` in this repo:

| Topic | Check |
|---|---|
| Natural-language reject | 「继续 / 全部放行」still never writes `decided` |
| Ask-now vs wait | `needs_choice` / exit-style still means ask now |
| Gate meaning | `batch_implementation_gate=ready` = handoff only; `implementation_readiness=not_assessed`; no install/codemod |
| Lockfile / required_for_path | `ready` still blocked by `lockfile_status` ≠ `present` or deferred required rows |
| Freshness | status `evidence_as_of` (`YYYY-MM-DD`) required; external usage docs must not call gate “实施授权” |
| Analysis endpoint | complete only after queue cleared + report regenerated + Agent review |
| Output confirmation | Writes still need explicit path confirmation |
| Independence | Neither skill's `SKILL.md` imports or requires the other |
| Page host-port vs this packet | Description still sends single-page parity/rollback evidence to `vue2-pages-to-vue3-host-migration`; this skill stays path/axes analysis only |

If a semantic deliberately diverges, document the divergence in the PR/commit
message. Do **not** share code or load the sibling skill at runtime.
