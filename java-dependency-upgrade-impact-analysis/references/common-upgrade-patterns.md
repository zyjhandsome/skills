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
invalidates the requested family target and triggers alternative discovery; the
row is `blocked` only when no verified alternative exists.

## Pattern table

| Pattern | Signals | Default analysis stance |
|---|---|---|
| Unused direct | safe `dependency:analyze-only` + call-site/config/SPI/runtime-duty evidence agree | Prefer `recommended_treatment=remove`; confirm per unit with `remove` / `defer` / `other`. **Even if the pasted table supplies a `to`**, do not default-ask upgrade. Framework/reflection-only or conflicting evidence stays `ambiguous` |
| Same-line PATCH | e.g. Lucene `9.12.1→9.12.2` | Lower risk; still verify owner + changelog; may share a patch batch |
| Boot-managed JSON | `jackson-databind` / Jackson modules | Prefer **one family decision unit** under `upgrade-owner` (Boot/BOM property); list members in the Decision Record. Single-GAV pin only after owner-first ruled out |
| Transitive CVE / transitive version move | hole or exact `from→to` only on a transitive GAV | Prefer `upgrade-introducer` / `move-introducer` if parent GA converges; else `force-align` (full DR) / `exclude` / `replace-introducer`. **Never lead with a bare leaf pin.** Publish path menu A–E per `next-action-choice-menus.md` §B |
| Cross-minor Netty | e.g. `4.2.x→4.1.x` or reverse | Treat as high scrutiny / likely wrong pin; default lean `no-viable-path` or owner alignment, not blind proceed |
| Explicit downgrade | `to < from` (e.g. Eureka `2.0.6→2.0.5`) | Caller’s explicit target authorizes analysis; show downgrade warning + High scrutiny and use normal per-unit confirmation. Missing motive is an evidence gap, not a second authorization gate. If only Maven/tree is missing, queue-`pending`（可行·待补证；`next-action-choice-menus.md` §A）— do not queue-`blocked` as “needs environment evidence”, and do not offer `proceed:` until baseline confirms |
| Pending baseline | target exists; `resolved_from` unconfirmed | Ordered补证：restore `mvn`/`JAVA_HOME` → staged leaf `dependency:tree`/`dependencyInsight` → confirm claimed `from` → then open path menu. No `proceed` until baseline confirmed |
| Non-GA target | Beta / RC / Snapshot / Milestone | `target_channel=non-ga` → `blocked` unless user explicitly allows |
| Dead / unmaintained | abandoned upstream + unfixed CVE | `replace-component` with 1–3 candidates; human must confirm; own batch if MAJOR/coordinate change |
| commons-lang 2→3 | `commons-lang:commons-lang` → `org.apache.commons:commons-lang3` / `3.x` | MAJOR + groupId/artifactId/package triple change; **own batch** using a domain such as `commons-lang-major` when needed; preserve old coordinate as `requested_*` and new coordinate as independently probed `recommended_*`; describe migration only. Name an OpenRewrite/equivalent recipe only with a verified catalog/source URL; otherwise record “recipe unverified” as an evidence gap. Never run it here |
| Cloud train client | Eureka / Spring Cloud Netflix bits | Resolve Netflix vs Cloud groupId; if transitive, use path menu (move-introducer / force-align / other discovery starter / native rewrite). Check Cloud BOM / release train, not Maven Central “latest” alone |
| Open / CVE without `to` | GAV listed, no target version | Recommend GA fix version with URLs; **per-unit human confirm** — never invent or auto-pick |

## Mixed compliance tables

A single pasted table often mixes PATCH, downgrade, cross-line, and MAJOR rows.
**Split confirmation waves / packets** by authority layer, Boot line, build
variant, and bounded scope.
State explicitly why rows were split. Never force Netty cross-line + lang MAJOR
+ Lucene patch into one “all proceed” ask without separation.

## Chinese software-name rows

Tables may use display names (`Apache lucene`, `eureka`) plus jar lists.
Map jars → `groupId:artifactId` via project resolution and
`references/common-gav-repos.md`; record mapping assumptions in 基线与假设.
