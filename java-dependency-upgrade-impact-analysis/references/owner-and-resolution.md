# Owner And Resolution

## Declared vs effective

| Source | Shows | Not enough alone |
|---|---|---|
| `pom.xml` / `build.gradle*` / version catalog | Intent / requested version | Selected runtime version |
| `mvn dependency:tree -Dverbose` | Selected + omitted + paths | Convergence policy proof |
| `mvn help:effective-pom -Dverbose` | Management origin hints | Full conflict reproduction |
| `./gradlew dependencies` | Configuration graph | Selection reason per GAV |
| `./gradlew dependencyInsight --dependency <name> --configuration <cfg>` | Why a version won | Cross-module picture |

Re-run the same graph command:

1. before recommending an owner change
2. after hypothesizing an owner change (record expected tree; do not mutate builds in this skill)
3. when justifying any override

A pom-only parser that skips managed dependencies (no explicit `<version>`) **under-reports** Boot-managed jars. Always pair inventory with resolution.

If a bounded tree/insight probe fails, a direct declaration plus management
property may establish `declared_from`, but **never** `resolved_from`. Keep the
effective baseline `unknown` and record the resolver failure. Do not clear a
claimed-from mismatch gate or offer `proceed` until a successful selected-version
probe (or equivalent lockfile/resolver evidence) confirms the effective version.

`maven-dependency-plugin` 3.x documents `-Dverbose` as **not fully accurate** (it reconstructs the graph with the legacy resolver and prints a warning). Treat verbose output as a lead for conflict paths, then confirm the selected version with non-verbose `dependency:tree -Dincludes=…`, `dependency:list`, or `help:effective-pom`. Never present a verbose-only line as the selected version.

## Ownership classes

| Class | Meaning | Typical evidence |
|---|---|---|
| `boot-bom` | Spring Boot parent or `spring-boot-dependencies` import | effective POM management |
| `imported-bom` | Other BOM/platform (Cloud, Jackson BOM, etc.) | import scope / platform |
| `direct` | Explicit project declaration with version or catalog pin | build file |
| `transitive` | Pulled by another dependency | full path in tree |
| `plugin` | Build plugin / Gradle plugin ownership | buildEnvironment / plugin portal |

Determine owner from evidence, not from wishful preference for “Boot-managed”.

## Owner-first sequence

1. Identify the effective owner of the contested GAV line.
2. Prefer a compatible upgrade of that owner (maintenance Boot line, BOM bump).
3. Predict post-change resolution (same modules, same family convergence).
4. If the conflict disappears, **do not** recommend a single-GAV override.
5. If it remains, an override is allowed only when **all** Decision Record fields are complete (`references/decision-record-schema.md`).

Prefer a tested Boot BOM set over the newest standalone artifact. Blanket-moving an entire family (Netty, Jackson) without alignment evidence is a red flag.

## Owner-internal adjustment before override

“Change the owner” is not limited to bumping the whole BOM. For a Boot-managed family the canonical **owner-internal** move is overriding the version property the BOM itself declares — this keeps the family aligned, which a per-GAV `dependencyManagement` pin does not. Recommend in this order and say which rung the recommendation sits on:

| Rung | Maven | Gradle | Keeps family aligned |
|---|---|---|---|
| 1. Owner bump | newer `spring-boot-starter-parent` / imported BOM version | newer `platform()` / `mavenBom` coordinate | yes |
| 2. Owner property override | `<properties><netty.version>…</netty.version></properties>` (also `jackson-bom.version`, `lucene.version` when the BOM declares it) | `ext['netty.version'] = '…'` **only** when `io.spring.dependency-management` is applied. A native `implementation(platform(...))` ignores `ext` silently; use `enforcedPlatform` or a BOM property that the platform actually reads | yes — whole family moves together |
| 3. Family BOM import | import `jackson-bom` / `netty-bom` at the target version | `platform("io.netty:netty-bom:…")` | yes, but adds a second authority |
| 4. Per-GAV pin / downgrade | `dependencyManagement` entry for one artifact | `version { strictly("v") }` or `resolutionStrategy.force("g:a:v")`. A plain `constraints { implementation("g:a:v") }` is a floor: Gradle still picks the highest version and will not downgrade | **no** — splits the family |
| 5. Exclusion + direct declaration | `<exclusions>` on the consumer plus a direct dependency | `exclude group:` plus explicit dependency | no — last resort for *version authority* |

Rungs 4–5 are the “override” that needs a complete Decision Record. Verify the property name exists in the resolved BOM (`help:effective-pom`, or read `spring-boot-dependencies` for the active line) before recommending rung 2 — an invented property silently does nothing.

### Orthogonal: treatment ladder

Version authority (this file) answers “who owns the version line.”  
**What to do** (remove / upgrade introducer / exclude unused branch / replace) is
`references/treatment-ladder.md`. Do not skip a safer treatment just because
rung 5 lists exclusion last — `exclude` as a *treatment* is valid when usage
evidence shows the transitive branch is untouched; rung 5 means “exclusion is a
weak *authority* move when you still need the artifact on the classpath.”

### Unused direct dependencies

Before recommending `upgrade-self` on a **direct** declaration, gather safe
usage evidence. Do **not** run bare `mvn dependency:analyze`: it forks
`test-compile` and can execute lifecycle-bound writers such as `spotless:apply`,
`flatten`, or code generation. Use `mvn dependency:analyze-only` only when
compiled outputs already exist and are demonstrably fresh; otherwise use
call-site/configuration/SPI evidence and record `usage_status=ambiguous`.

`dependency:analyze-only` is bytecode-reference based and commonly reports
Spring starters, JDBC drivers, logging bindings, serializers, SPI providers, and
reflection/configuration-loaded libraries as unused. Never accept that result
alone as `unused`. Prefer `recommended_treatment=remove` only when analyze-only,
call-site/config/SPI inspection, and runtime-duty review agree. If the compliance
table still supplies a `to`, keep recommending `remove` and ask
`remove` / `defer` / `other`.

Before and after any build-tool probe, capture `git status --short`. A new
tracked-file change is a hard safety stop; report the command and affected files
without reverting unrelated user work. Untracked files (a Gradle probe may create
`.gradle/`) are recorded in the assumptions, not a hard stop. When the directory
is not a git checkout, snapshot the mtimes of `pom.xml` / `build.gradle*` /
`settings.gradle*` / `gradle/libs.versions.toml` instead and stop on a change.

For Gradle, also read version catalogs (`gradle/libs.versions.toml` / catalog
aliases) as declaration evidence; still confirm the **selected** version with
`dependencies` / `dependencyInsight`, not the catalog pin alone.

## Commands (non-mutating)

### Maven

Prefer system `mvn` (environment-preflight gate). `./mvnw` may be used after a
system **or** wrapper graded pass; if only the wrapper exists, record
`build_tool_source=wrapper` and use it for tree/insight. Neither system nor
wrapper → `blocked`.

```shell
mvn -pl <module> -am dependency:tree -Dverbose -Dincludes=groupId:artifactId
mvn -pl <module> -am dependency:tree -Dincludes=groupId:artifactId
mvn -pl <module> -am help:effective-pom -Dverbose
# Only with fresh compiled outputs; does not fork test-compile:
mvn -pl <module> dependency:analyze-only
```

`-Dverbose` is a lead for conflict paths, not the selected-version authority
(see above). Do not start from an unbounded reactor tree.

When Enforcer dependency-convergence is configured:

```shell
mvn enforcer:enforce
```

Do not claim convergence from a tree alone.

### Gradle

Prefer `./gradlew` whenever the wrapper passed preflight, even if a system
`gradle` also exists (see `environment-preflight.md`). Record
`build_tool_source=wrapper`. If neither the wrapper nor system `gradle` works,
preflight must stay `blocked`.

```shell
./gradlew :<module>:dependencies --configuration runtimeClasspath
./gradlew :<module>:dependencyInsight --dependency <name> --configuration runtimeClasspath
./gradlew :<module>:buildEnvironment
```

Default the configuration to `runtimeClasspath`. Switch it for `provided`,
`test`, or `annotationProcessor` instead of assuming every dependency is runtime.
`dependencies` without a project path only shows the project you invoked.
Prefer the wrapper that passed preflight over a global `gradle`.

Report the project's actual conflict/verification gate; Gradle has no universal convergence task.

## Multi-module / multi-Boot

Record per module: Boot line, JDK, and whether the candidate is inherited from a parent BOM. Do not merge two Boot lines into one decision batch.

## Maven and Gradle do not arbitrate the same way

| Question | Maven | Gradle |
|---|---|---|
| Who wins a version conflict | Nearest definition; same depth → first declaration | Highest version, unless a rich version (`strictly`, `reject`) or a force says otherwise |
| BOM import order | `dependencyManagement` imports: the first declaration wins for a given managed GAV | `platform()` advises; `enforcedPlatform()` forces. Later platforms do not silently override an earlier enforced one |
| `${revision}` | Read `.flattened-pom.xml` when `flatten-maven-plugin` is bound; a new flattened POM after a probe is a tracked-file stop | Not applicable; read the version catalog or `gradle.properties` |
| Lockfile | None by default | `gradle.lockfile` is the selected version when dependency locking is enabled; prefer it over a catalog pin |
| Included build | Parent POM reactor | `buildSrc/` and `includeBuild` can supply versions the root catalog does not show; name them in assumptions |
