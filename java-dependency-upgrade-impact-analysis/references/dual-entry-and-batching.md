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
| `requested_gav` / `requested_to` | replace entry | Original coordinate/version supplied by inventory/table; preserve even when 404 |
| `requested_target_exists` | replace entry | Existence of the original requested target |
| `recommended_gav` / `recommended_to` | replace entry | Named replacement coordinate/version; never silently copied over the requested target |
| `recommended_target_exists` | replace entry | Registry-verified existence of the recommended replacement; must be `yes` before the replacement row becomes `ready` |
| `decision_domain` | isolated MAJOR/coordinate batch | Stable lowercase slug such as `commons-lang-major`; absent for the normal shared packet |
| `build_variant` | yes | Active Maven profiles / Gradle properties and toolchain; use `default` when none |
| `build_variant_source` | yes | `caller-specified` / `project-default` / `host-auto-activated`; never present host auto-activation as production fact |
| `production_variant_confirmed` | yes | `yes` / `no` / `unknown`; unknown is an explicit assumption/evidence gap |
| `batch_scope` | yes | Stable bounded family/business scope such as `json-yaml` or `bigdata-runtime`; never `all` for a large monorepo |
| `direction` | yes | `upgrade` / `downgrade` / `same` / `unknown` — not `remove`/`replace` (those are `recommended_treatment`) |
| `scope` | yes after resolve | `compile` / `runtime` / `provided` / `test` / `system` — decides whether a change can reach production at all |
| `classifier` | when present | e.g. native `linux-x86_64` for `netty-transport-native-*`; classified artifacts are published per platform and must be verified per classifier |
| `optional` | when true | `<optional>true</optional>` / Gradle `optional` feature — not inherited by consumers |
| `exclusions_present` | yes/no | An `<exclusions>` on the path explains a version the tree alone makes look wrong |
| `owner_class` | yes after resolve | See owner-and-resolution.md |
| `authority_layer` | yes | `jdk` / `boot-bom` / `platform-plugin` / `app-library` |
| `boot_line` | when Boot present | field value e.g. `3.2.x` → directory token `boot-3.2.x` (or `no-boot`) |
| `semver_class` | when comparable | `PATCH` / `MINOR` / `MAJOR` / `SECURITY` / `NON_SEMVER` |
| `entry_source` | yes | `inventory` / `exact-table` / `cve` / `other` |
| `usage_status` | direct candidates | `used` / `unused` / `ambiguous` — safe analyze-only plus call-site/config/SPI evidence |
| `recommended_treatment` | yes after classify | See `treatment-ladder.md` |
| `introducer_gav` | transitive / introducer treatments | Direct GAV that pulls this coordinate |
| `introducer_upgrade_available` | when introducer evaluated | `yes` / `no` / `unknown` |
| `target_channel` | when `target_to` set | `ga` / `non-ga` |
| `replacement_candidates` | replace treatments | 1–3 alternate coordinates (analysis-only) |
| `alternative_candidates` | requested target missing | 1–3 verified GA candidates; same-GAV version or replacement GAV |

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
- Batch CVE / open-target transitive holes by the **introducer**'s full packet key
  (`authority_layer × boot_line × build_variant × batch_scope`), not by the
  vulnerable leaf alone.
- `to < from` is valid explicit permission to **analyze** a downgrade. Mark
  `direction=downgrade`, show a prominent warning, keep High scrutiny, and use
  the normal per-unit confirmation. Missing rationale is an evidence gap, not a
  second authorization gate.
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
| target 404 while other members/classifiers resolve | `no` | preserve request; search verified alternatives before classifying the queue |
| registry unreachable / 403 / 429 | `unknown` | `blocked` on evidence; do not assume existence |
| treatment `remove` / `exclude` | `n/a` | may be `ready` for human confirm; not an existence pass for upgrades |
| treatment `no-viable-path` | `n/a`（或存在性 `no`/`unknown`） | always queue-`blocked`（restate / `other`）；never `ready`/`pending`/`defer` |
| version matches non-GA qualifier (Beta/RC/Snapshot/Milestone/Alpha/CR) | treat as `target_channel=non-ga` | `blocked` unless user explicitly allows non-GA |

When a candidate carries a `classifier`, existence is **per classifier**, not
just the base GAV. A `no` / `unknown` member invalidates the requested family
move — a partial family move is not a valid recommendation. Before blocking,
search 1–3 alternatives: a published same-GAV GA, renamed/split family, or
replacement component. Preserve the original as `requested_*`; probe every
candidate separately. Classify by candidate kind:

| Verified alternative | Treatment | Queue option |
|---|---|---|
| Same GAV, different GA version | `choose-alternative` | `proceed:g:a:v` |
| Different coordinates / package migration | `replace-component` or `replace-introducer` | `replace:g:a[:v]` |
| None / evidence unreachable | `no-viable-path` | evidence-`blocked` (restate / `other`) |

Document searched-and-rejected alternatives in 未决问题 even when the row stays
`blocked`. Do not spend full owner/impact work on the impossible request itself;
analyze verified alternatives deeply enough to support the human choice. Never
silently substitute a “probably equivalent” artifact. `n/a` is allowed only for
treatments that do not move a target artifact (`remove` / `exclude` /
`no-viable-path`).

## Batching hard rule

One decision packet / confirmation wave normally covers:

**one `authority_layer` × one `boot_line` × one `build_variant` × one bounded `batch_scope`**

Examples:

- OK: Boot `3.2.x` × default profile × `json` scope × Jackson patch family
- OK: Same `boot-bom × boot-3.2.x` packet with Jackson `ready` **and** Netty
  `blocked` (existence 404) — do **not** force a separate packet just because one
  family is blocked; ready + blocked may coexist until the blocked target is restated
- Not OK: JDK 17→21 + Boot 2.7→3.2 + commons-lang 2→3 in one batch
- Not OK: default and `apache` Maven profiles in one batch, even if both are
  nominally `boot-2.7.x`
- Not OK: hundreds of unrelated app libraries grouped only because they share
  the same authority and Boot line

Split MAJOR app-library migrations (e.g. `commons-lang` → `commons-lang3`) into
their own batch even if discovered in the same compliance table. When that
migration shares the same authority layer and Boot line with another packet,
append a stable `decision_domain` slug to the batch key:

`app-library__no-boot__variant-default__scope-commons-lang__domain-commons-lang-major`

Do not add a domain merely because one family is evidence-`blocked`; ready +
blocked rows of the same ordinary packet still coexist.

## SemVer classification

| Class | Typical meaning | Default scrutiny |
|---|---|---|
| PATCH | Bug/security fix, same minor | Lower; still confirm |
| MINOR | Compatible features (claimed) | Medium; verify notes |
| MAJOR | Breaking API/binary | High; migration evidence required |
| SECURITY | CVE-driven | High urgency; still owner-first |
| NON_SEMVER | Qualifiers, calver, `.Final` lines | Compare vendor notes |

Strip noise suffixes (`.RELEASE`, `.Final`) only for comparison display; record original resolved strings verbatim in the report.
