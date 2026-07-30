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
| 2. Owner property override | `<properties><netty.version>…</netty.version></properties>` (also `jackson-bom.version`, `lucene.version` when the BOM declares it) | `ext['netty.version'] = '…'` with the Boot Gradle plugin | yes — whole family moves together |
| 3. Family BOM import | import `jackson-bom` / `netty-bom` at the target version | `platform("io.netty:netty-bom:…")` | yes, but adds a second authority |
| 4. Per-GAV pin | `dependencyManagement` entry for one artifact | `constraints { implementation("g:a:v") }` | **no** — splits the family |
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

Before recommending `upgrade-self` on a **direct** declaration, run or cite
`mvn dependency:analyze` (or Gradle equivalent / call-site search). Record
`usage_status` (`used` / `unused` / `ambiguous`). Prefer `recommended_treatment=remove`
when unused; never auto-remove when ambiguous. If the compliance table still
supplies a `to`, keep recommending `remove` and ask `remove` / `defer` / `other`
(see `treatment-ladder.md`).

For Gradle, also read version catalogs (`gradle/libs.versions.toml` / catalog
aliases) as declaration evidence; still confirm the **selected** version with
`dependencies` / `dependencyInsight`, not the catalog pin alone.

## Commands (non-mutating)

### Maven

Prefer system `mvn` (environment-preflight gate). `./mvnw` may be used **after**
system `mvn -v` already passed; wrapper-only environments stay `blocked`.

```shell
mvn dependency:tree -Dverbose
mvn dependency:tree -Dincludes=groupId:artifactId
mvn help:effective-pom -Dverbose
mvn dependency:analyze
```

When Enforcer dependency-convergence is configured:

```shell
mvn enforcer:enforce
```

Do not claim convergence from a tree alone.

### Gradle

Prefer `./gradlew` when present **after** system `gradle -v` already passed
environment preflight (see `environment-preflight.md`). If only the wrapper
exists, preflight must stay `blocked`.

```shell
./gradlew dependencies
./gradlew dependencyInsight --dependency <name> --configuration <configuration>
./gradlew buildEnvironment
```

Or the system CLI (`gradle …`) when that matches the project’s expected major.

Report the project's actual conflict/verification gate; Gradle has no universal convergence task.

## Multi-module / multi-Boot

Record per module: Boot line, JDK, and whether the candidate is inherited from a parent BOM. Do not merge two Boot lines into one decision batch.
