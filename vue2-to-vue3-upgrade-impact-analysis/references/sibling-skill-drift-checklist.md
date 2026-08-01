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
| Gate meaning | `batch_implementation_gate=ready` informational only; no install/codemod |
| Analysis endpoint | complete only after queue cleared + report regenerated + Agent review |
| Output confirmation | Writes still need explicit path confirmation |
| Independence | Neither skill's `SKILL.md` imports or requires the other |

If a semantic deliberately diverges, document the divergence in the PR/commit
message. Do **not** share code or load the sibling skill at runtime.
