# Reachability And Upstream

Network probes in this file run in the same wave as
`references/environment-preflight.md` (after JDK / build-tool / Python gates).
Dual registry+GitHub failure is an offline-confirm gate, **not** a tool-preflight
hard stop.

## Reachability gate

Before claiming online upstream evidence:

1. Probe the project's primary registry (Maven Central or the mirror reflected in settings). Example:

```shell
curl -I --max-time 12 https://repo1.maven.org/maven2/
```

2. If registry fails, probe GitHub API for changelog hosts:

```shell
curl -I --max-time 12 https://api.github.com/
```

| Result | Action |
|---|---|
| Registry or GitHub OK (HTTP 2xx / 3xx) | Stay online; fetch release/changelog/CVE |
| Both fail (timeout, DNS, or HTTP ≥400) | Ask the human; only then continue with `--offline` / local evidence |
| Partial (403/429 on one host) | Keep `partial` gaps; do not invent notes |

`scripts/preflight.py` probes the same URLs (`repo1.maven.org/maven2/` then
`api.github.com/`) and treats only `200 ≤ status < 400` as network OK.

Never infer offline solely because `.m2` or an internal mirror path exists.

## Upstream evidence pack (exact `from→to`)

Collect with URLs:

- Release notes / changelog for the interval
- Migration guide when MAJOR or namespace changes
- Security advisories fixed between versions (if any)
- Peer/Boot support matrix when owner is Boot/BOM

Store citations in the report. Subsequent impact claims must cite this pack, not re-guess.

## Maven Tools MCP (optional)

When available, prefer MCP tools for facts:

| Intent | Typical tool |
|---|---|
| Version exists | `check_version_exists` |
| Compare + CVE | `compare_dependency_versions` |
| POM health / safe bumps | `analyze_project_health` / `recommend_pom_upgrades` |

If MCP is absent: use Maven Central metadata, `gh release`, WebFetch on official repos, and record `evidence_source=fallback`.

## Locating changelogs

1. Check `references/common-gav-repos.md` for known `groupId:artifactId` → GitHub.
2. Else search GitHub / project site; verify the repository matches the artifact (watch forks and renamed coords).
3. Try common filenames: `CHANGELOG.md`, `RELEASENOTES.md`, `CHANGES.md`, GitHub Releases body.

Prioritize sections labeled Breaking Changes, Security, Migration, Removed, Deprecated.

## Credit

Inventory scripting and GAV→repo lookup patterns are informed by community helpers such as
[Jodu1005/java-dependency-upgrade](https://github.com/Jodu1005/java-dependency-upgrade)
(pom parse + GitHub changelog flow). This skill **rejects** treating declared-only pom
versions as the effective baseline and **forbids** mutating upgrades inside the analysis skill.
