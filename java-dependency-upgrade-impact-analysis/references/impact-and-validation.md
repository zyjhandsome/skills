# Impact And Validation

## Six-layer impact model

| Layer | Inspect | Acceptance evidence (analysis plans these; does not run mutating upgrades) |
|---|---|---|
| Code | imports, APIs, annotations, SPI | Focused unit/integration test list |
| Configuration | `application*.yml/properties`, logging, server | Startup/config binding checks |
| Data | SQL, dialect, serialization of persisted payloads | CRUD / migration compatibility notes |
| Interface | HTTP JSON, headers, errors, auth | Contract tests |
| Test | fixtures, slices, containers | Affected test scope (or explicit empty) |
| Deployment | JDK image, probes, TLS | Staging/canary monitoring signals |

For each impact row record: module/file, current vs target behavior, **fact or inference**, risk, required change (descriptive only), validation, rollback trigger idea.

## Finding call sites

Search candidates (treat hits as leads, then read definitions):

```shell
rg -n "import org\\.apache\\.lucene\\.|org\\.apache\\.lucene\\." .
rg -n "import io\\.netty\\.|io\\.netty\\." .
rg -n "import com\\.fasterxml\\.jackson\\.|ObjectMapper|JsonFormat" .
rg -n "import org\\.apache\\.commons\\.lang\\.|StringUtils" .
rg -n "eureka|DiscoveryClient|EnableEureka" .
```

Adjust patterns to the GAV under analysis. Empty static hits ≠ safe removal/upgrade; say so.

## JVM-specific traps a dependency tree does not show

Check each of these explicitly and record the result (including “not applicable”):

| Trap | Why the tree misses it | How to check |
|---|---|---|
| Shaded / relocated copies | a shaded jar inlines classes under a renamed package, so the GAV never appears | `maven-shade-plugin` / Gradle `shadow` in the build; `rg -n "shaded\.(io\.netty\|com\.fasterxml)"`; inspect jar entries of suspect uber-jars |
| `META-INF/services` SPI files | wiring is by file, not import | `rg -n --files-with-matches "" src/main/resources/META-INF/services` and compare provider names against the target release |
| JPMS `module-info` | automatic-module names and `requires` are compile-time contracts | `rg -n "requires .*(netty\|jackson\|lucene)" **/module-info.java` |
| Multi-Release jars | behavior differs per running JDK | `Multi-Release: true` in the jar manifest; confirm the deployed JDK |
| Native / classified artifacts | classifier variants are published per platform | verify the target version exists **per classifier**, not just for the base artifact |
| `provided` / `test` scope | a change there cannot reach production, or only affects CI | candidate `scope` field |
| Container-supplied jars | app server or agent supplies its own copy | deployment descriptors, `-javaagent`, container lib listings |

## Compatibility verification to name (plan only)

For MINOR/MAJOR and every downgrade, name a machine-checkable API-diff step instead of relying on compilation:

| Check | Tool candidates | Proves |
|---|---|---|
| Binary/source API diff between the two exact versions | `japicmp`, `revapi` | removed/changed signatures your code or its consumers touch |
| Bytecode target/JDK API floor | `animal-sniffer` | the target does not require a newer JDK API than deployed |
| Duplicate/conflicting classes after the move | `maven-enforcer` `banDuplicateClasses`, `duplicate-finder` | two versions of the same package on the classpath |

For MAJOR coordinate/package migrations, record that established migration
codemods/recipes exist for the pair (with a URL) as an **implementation-stage
option with its residual risk** — this skill names it, plans validation around it,
and never runs it. Prefer naming the concrete recipe when known (e.g. OpenRewrite
`commons-lang.MigrateCommonsLangToCommonsLang3`, or the project's chosen
equivalent). An unnamed migration path is an evidence gap, not a low risk.

## Validation matrix (for the packet)

| Area | Minimum checks to name | Raise priority when |
|---|---|---|
| Build/static | clean compile, convergence/duplicates | framework/JDK/BOM owner change |
| Startup | beans, config, DB | server/security/ORM |
| API | status, errors, headers | MVC/Security/Validation |
| JSON | dates, enums, nulls, unknown props | Jackson override/family move |
| Data | CRUD, transactions | Hibernate/drivers |
| Security | authz filters | Spring Security |
| Integration | messaging, cache, clients | transitive client libs |
| Performance | latency, pools | Netty/Tomcat/ORM |
| Smoke | health + critical path | every staged release recommendation |

Compilation is a gate suggestion, not release proof. Select tests from the dependency's runtime duties and the six-layer rows.

## Affected test scope

1. List tests that import or exercise the GAV (or wrappers).
2. If empty: state **verification gap** — passing unrelated suites does not prove the upgrade safe.
3. Carry this list into the report Completion / Validation sections.
