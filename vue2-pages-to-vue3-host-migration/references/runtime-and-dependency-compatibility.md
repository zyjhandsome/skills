# Runtime and dependency compatibility

## Separate A and B

Treat source A and host B as independent runtime environments until evidence proves
otherwise. Record for each:

- `package.json` engines and package-manager declaration;
- `.nvmrc`, `.node-version`, Volta/asdf/fnm/nvm configuration;
- lockfile type, format version and authoritative importer;
- Node-sensitive build tools, native modules and scripts;
- CI image/runtime and production build runtime;
- current installed runtime only as an observation, never as the requirement.

Resolve conflicts from authoritative project constraints and tool compatibility,
not whichever global Node is active.

## Evidence contract

Produce one record for the revision pair:

```yaml
schema: runtime-compatibility-evidence/v1
producer: vue2-pages-to-vue3-host-migration
authority: domain_evidence_only
authority: domain_evidence_only
source_revision: <source A revision>
host_revision: <host B revision>
source_runtime:
  required_node: <range/exact/unknown>
  evidence: []
  package_manager: <name/version/unknown>
  lock_owner_format: <value/unknown>
  selected_runtime: <path/version/none>
  isolation_method: <value/none>
  command_readiness: ready | blocked | unknown
host_runtime: <same shape>
dependency_demands: []
approved_runtime_actions: []
restoration_plan: []
verification_commands: []
final_runtime_result: not_run | fail | pass
```

Each verification command row records `repository` (`source` or `host`),
`command`, `working_directory`, `runtime`, RFC3339 `timestamp`, numeric
`exit_code`, and SHA-256 `output_digest`. Validate completed JSON with
`scripts/validate_runtime_evidence.mjs`.

## Preflight before project commands

Block install/build/test/codemod commands when:

- Node constraints conflict or remain unknown;
- the required package manager is unavailable;
- the lock importer or format owner is unresolved;
- the command would rewrite an unapproved lockfile;
- a required registry, license, peer dependency, or package target is unavailable;
- runtime switching/installation lacks explicit authorization.

Prefer an isolated installed project runtime over changing the user's global Node.
Never share `node_modules` between A and B. Do not copy A's lockfile or dependency
tree into B.

## Resolve dependency demand

For every package in the page closure, record:

```text
package / provenance / source exact version / host exact version /
source usages / host usages / peer+engine constraints / license /
official evidence / disposition / decision_status / affected units
```

Choose one disposition:

```text
reuse-B
reuse-B-major-review
add-to-B
replace-as-B-stack
copy-local
retire
unknown
```

For cross-major, replacement, security, maintenance, license, peer, engine, CSS,
or build changes:

1. Resolve exact versions from the authoritative lock/importer.
2. Collect version-specific primary evidence from official documentation, release
   notes, migration guides, package metadata, repository tags and license text.
3. Map actual imports, wrappers and callers to migration units.
4. Compare behavior, API, DOM/CSS, bundle/runtime, browser and Node impact.
5. Record alternatives only when the current package cannot satisfy the contract.
6. Keep disposition `unknown` and block implementation when required primary
   evidence, license entitlement, registry access, or target availability is absent.

When network access is unavailable, use cached evidence only when its exact source,
version and freshness are provable. Otherwise record a blocker; do not turn an
offline guess into a package decision.

Dependency disposition approval is not implementation authorization. Keep the two
decisions separate.

## Node execution rules

- Run A baseline commands in A's compatible runtime.
- Run B implementation and final verification in B's compatible runtime.
- Record exact executable path, version, package manager and lock format.
- Split commands that span repositories or run explicit isolated processes; never
  silently choose one runtime for both.
- Require authorization for runtime installation, global/user state changes,
  dependency installation, lock mutation and registry credential changes.
- Restore approved temporary runtime state and verify restoration.

## Build and lock verification

Before `final_runtime_result=pass`:

- inspect manifest and lock diffs;
- confirm only intended B importers changed;
- confirm lockfile format did not drift;
- run source baseline where required and host typecheck, unit/component/E2E/build
  commands in their selected runtimes;
- compare output entries, chunks, assets and public base;
- verify CSS extraction/order and dynamic imports in production mode;
- record command, working directory, executable/runtime, timestamp, exit code and
  output digest;
- verify any temporary runtime change was restored.

Do not use “the dev server starts” as proof that CI or production builds are
compatible.
