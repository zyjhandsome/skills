# Common Upgrade Patterns

Apply these heuristics whenever the exact table or inventory matches. They do
**not** replace effective resolution or owner-first evidence.

## Family expansion

When one row lists multiple jars (e.g. Lucene, Netty), expand to per-GAV
candidates **or** one family Decision Record that names every member. Do not
silently upgrade only the first artifact.

Compliance tables are usually generated from the artifact list of the **current**
line, so a cross-line target may name members that line never published (Netty
4.2 split `netty-codec` into `netty-codec-base` / `netty-codec-compression`,
neither of which exists on 4.1). Run the target existence precheck in
`references/dual-entry-and-batching.md` per member first; one missing member
blocks the whole family row.

## Pattern table

| Pattern | Signals | Default analysis stance |
|---|---|---|
| Unused direct | `dependency:analyze` unused / no call sites | Prefer `recommended_treatment=remove`; confirm per unit with `remove` / `defer` / `other`. **Even if the pasted table supplies a `to`**, do not default-ask upgrade; document the conflict. Never auto-remove when `ambiguous` |
| Same-line PATCH | e.g. Lucene `9.12.1→9.12.2` | Lower risk; still verify owner + changelog; may share a patch batch |
| Boot-managed JSON | `jackson-databind` / Jackson modules | Prefer **one family decision unit** under `upgrade-owner` (Boot/BOM property); list members in the Decision Record. Single-GAV pin only after owner-first ruled out |
| Transitive CVE | hole only on a transitive GAV | Prefer `upgrade-introducer` if parent GA already lifts it; else `force-align` / `exclude` / `replace-introducer` per `treatment-ladder.md` |
| Cross-minor Netty | e.g. `4.2.x→4.1.x` or reverse | Treat as high scrutiny / likely wrong pin; default lean `defer` or owner alignment, not blind proceed |
| Explicit downgrade | `to < from` (e.g. Eureka `2.0.6→2.0.5`) | Same workflow as upgrade; require motive + compatibility evidence before `proceed` |
| Non-GA target | Beta / RC / Snapshot / Milestone | `target_channel=non-ga` → `blocked` unless user explicitly allows |
| Dead / unmaintained | abandoned upstream + unfixed CVE | `replace-component` with 1–3 candidates; human must confirm; own batch if MAJOR/coordinate change |
| commons-lang 2→3 | `commons-lang:commons-lang` → `org.apache.commons:commons-lang3` / `3.x` | MAJOR + groupId/artifactId/package triple change; **own batch**; describe migration impact only (no code edits). Name established migration recipes (e.g. OpenRewrite `commons-lang.MigrateCommonsLangToCommonsLang3`, or equivalent) as an **implementation-stage option with residual risk** — never run them here |
| Cloud train client | Eureka / Spring Cloud Netflix bits | Check Cloud BOM / release train, not Maven Central “latest” alone |
| Open / CVE without `to` | GAV listed, no target version | Recommend GA fix version with URLs; **per-unit human confirm** — never invent or auto-pick |

## Mixed compliance tables

A single pasted table often mixes PATCH, downgrade, cross-line, and MAJOR rows.
**Split confirmation waves / packets** by `authority_layer` (and Boot line).
State explicitly why rows were split. Never force Netty cross-line + lang MAJOR
+ Lucene patch into one “all proceed” ask without separation.

## Chinese software-name rows

Tables may use display names (`Apache lucene`, `eureka`) plus jar lists.
Map jars → `groupId:artifactId` via project resolution and
`references/common-gav-repos.md`; record mapping assumptions in 基线与假设.
