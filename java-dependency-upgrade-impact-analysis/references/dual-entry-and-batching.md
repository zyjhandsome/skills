# Dual Entry And Batching

## Candidate schema

Every inventory hit or table row normalizes to:

| Field | Required | Notes |
|---|---|---|
| `groupId` | yes | Maven coordinate |
| `artifactId` | yes | Maven coordinate |
| `module` | when multi-module | Gradle project / Maven module path |
| `declared_version` | if present | May be property/BOM-managed empty |
| `resolved_from` | yes for exact | Effective current version |
| `target_to` | exact entry | Effective intended version |
| `target_artifact_exists` | yes when `target_to` set | `yes` / `no` / `unknown` — registry-verified, per member |
| `direction` | yes | `upgrade` / `downgrade` / `same` / `unknown` — not `remove`/`replace` (those are `recommended_treatment`) |
| `scope` | yes after resolve | `compile` / `runtime` / `provided` / `test` / `system` — decides whether a change can reach production at all |
| `classifier` | when present | e.g. native `linux-x86_64` for `netty-transport-native-*`; classified artifacts are published per platform and must be verified per classifier |
| `optional` | when true | `<optional>true</optional>` / Gradle `optional` feature — not inherited by consumers |
| `exclusions_present` | yes/no | An `<exclusions>` on the path explains a version the tree alone makes look wrong |
| `owner_class` | yes after resolve | See owner-and-resolution.md |
| `authority_layer` | yes | `jdk` / `boot-bom` / `platform-plugin` / `app-library` |
| `boot_line` | when Boot present | e.g. `3.2.x` |
| `semver_class` | when comparable | `PATCH` / `MINOR` / `MAJOR` / `SECURITY` / `NON_SEMVER` |
| `entry_source` | yes | `inventory` / `exact-table` / `cve` / `other` |
| `usage_status` | direct candidates | `used` / `unused` / `ambiguous` — from `dependency:analyze` or call-site evidence |
| `recommended_treatment` | yes after classify | See `treatment-ladder.md` |
| `introducer_gav` | transitive / introducer treatments | Direct GAV that pulls this coordinate |
| `introducer_upgrade_available` | when introducer evaluated | `yes` / `no` / `unknown` |
| `target_channel` | when `target_to` set | `ga` / `non-ga` |
| `replacement_candidates` | replace treatments | 1–3 alternate coordinates (analysis-only) |

## Entry A — repo inventory

1. Detect Maven and/or Gradle roots (including multi-module aggregators).
2. List direct + managed + notable transitive candidates (security-sensitive and outdated signals first when MCP/CVE data exists).
3. Emit a candidate table; **ask which batch to analyze** before deep-diving all rows.
4. Do not silently analyze the entire monorepo as one packet.

## Entry B — exact table

Accept rows like:

| Software | Artifacts | From | To |
|---|---|---|---|
| Apache Lucene | lucene-core, … | 9.12.1 | 9.12.2 |

Rules:

- Expand multi-artifact families into per-GAV candidates **or** one family row with explicit member list.
- Infer `resolved_from` from the effective graph; if it disagrees with claimed `from`, set the **row** `blocked` and set packet `analysis_status=blocked` until the user picks the baseline (no `ready` rows while packet is `blocked`). Do not analyze the claimed interval as if it were effective.
- Batch CVE / open-target transitive holes by the **introducer**'s `authority_layer × boot_line`, not by the vulnerable leaf alone.
- `to < from` (downgrade) is valid input; mark `direction=downgrade` and keep High scrutiny in the packet.
- Verify `target_artifact_exists` for **every** member before deeper analysis (see “Target existence precheck” below).

## Target existence precheck

A pasted compliance table is often generated against the artifact list of the
**current** line, so a cross-line target can name coordinates that were never
published. Check existence per member, not per family:

```shell
# base artifact
curl -s -o /dev/null -w "%{http_code}\n" \
  https://repo1.maven.org/maven2/<group/path>/<artifactId>/<target>/<artifactId>-<target>.pom
# classified artifact (e.g. netty-transport-native-epoll:linux-x86_64)
curl -s -o /dev/null -w "%{http_code}\n" \
  https://repo1.maven.org/maven2/<group/path>/<artifactId>/<target>/<artifactId>-<target>-<classifier>.jar
curl -s https://repo1.maven.org/maven2/<group/path>/<artifactId>/maven-metadata.xml
```

| Probe result | `target_artifact_exists` | Candidate status |
|---|---|---|
| target `.pom` / classified `.jar` 200 | `yes` | continue analysis |
| target 404 while other members/classifiers resolve | `no` | `blocked`; report the published version range from `maven-metadata.xml` |
| registry unreachable / 403 / 429 | `unknown` | `blocked` on evidence; do not assume existence |
| treatment needs no target (`remove` / `exclude` / open `defer`) | `n/a` | may be `ready` for human confirm; not an existence pass for upgrades |
| version matches non-GA qualifier (Beta/RC/Snapshot/Milestone/Alpha/CR) | treat as `target_channel=non-ga` | `blocked` unless user explicitly allows non-GA |

When a candidate carries a `classifier`, existence is **per classifier**, not just
the base GAV. A `no` / `unknown` member (or missing classifier) blocks the **whole family
row** — a partial family move is not a valid recommendation. `n/a` is allowed only for
treatments that do not move a target artifact (`remove` / `exclude` / open `defer`).
Do not spend owner classification or six-layer impact analysis on a
blocked existence row; report the coordinate mismatch and ask the user to restate
the target. Substituting a “probably equivalent” artifact for a missing one is a
scope change, not an inference. `replace-component` is a separate treatment that
requires human confirmation of named candidates — never a silent substitute for a
404 target.

## Batching hard rule

One decision packet / confirmation wave should cover:

**one `authority_layer` × one `boot_line`**

Examples:

- OK: Boot `3.2.x` line × Jackson patch family members
- OK: Same `boot-bom × boot-3.2.x` packet with Jackson `ready` **and** Netty
  `blocked` (existence 404) — do **not** force a separate packet just because one
  family is blocked; ready + blocked may coexist until the blocked target is restated
- Not OK: JDK 17→21 + Boot 2.7→3.2 + commons-lang 2→3 in one batch

Split MAJOR app-library migrations (e.g. `commons-lang` → `commons-lang3`) into their own batch even if discovered in the same compliance table.

## SemVer classification

| Class | Typical meaning | Default scrutiny |
|---|---|---|
| PATCH | Bug/security fix, same minor | Lower; still confirm |
| MINOR | Compatible features (claimed) | Medium; verify notes |
| MAJOR | Breaking API/binary | High; migration evidence required |
| SECURITY | CVE-driven | High urgency; still owner-first |
| NON_SEMVER | Qualifiers, calver, `.Final` lines | Compare vendor notes |

Strip noise suffixes (`.RELEASE`, `.Final`) only for comparison display; record original resolved strings verbatim in the report.
