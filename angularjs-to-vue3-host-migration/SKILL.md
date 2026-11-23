---
name: angularjs-to-vue3-host-migration
description: Use when assessing, designing, or verifying migration of AngularJS 1.x/jQuery/JSP/Thymeleaf mixed legacy pages or user behaviors into an existing Vue 3 host repository. Use for dual-repo source-to-host parity work, shell-page repair packets, or final domain verification. Not for greenfield Vue 3 creation unless no host repository exists.
---

# AngularJS To Vue 3 Host Migration

Use this skill to produce evidence and page-level designs for moving AngularJS 1.x, jQuery, JSP, Thymeleaf, and server-rendered page islands into an existing Vue 3 host. Default to **hosted migration**: source repo A supplies legacy behavior; host repo B owns the final entry, shell, auth, build, API conventions, components, state, i18n, proxy, and runtime gates.

This skill is independent and read-only for application code. Do not depend on `delivery-*` or other migration skills, and do not edit source A or host B application files from this skill. Reuse ideas only by restating the needed rule here.

## Modes

- `assess`: compare source A and Vue3 host B, identify overlaps, gaps, risks, and candidate migration units.
- `design`: produce an implementation-ready page/user-behavior design for 1 to 5 specified migration units.
- `verify`: define and/or run parity checks for behavior, permission, URL, API, display contract, visual evidence, rollback, and host build gates.
- `greenfield`: use only when the user explicitly has no Vue3 host. This is not the default path.

`design` may be scoped as repair when the host already has the unit's entry and the goal is source parity repair, but it still produces evidence, matrix updates, and slice plans only. There is no execute mode. See Shell-Page Repair in `references/hosted-vue3-migration-method.md`.

Default mode is `assess` unless the user names a page or asks for implementation design/verification.

## When Not To Use

- Do not use this skill for a routine Vue 3 feature that has no legacy AngularJS/jQuery/server-template parity target.
- Do not use the hosted path to create a new Vue 3 shell when a usable host B already exists. Use `greenfield` only when the user confirms that no host exists.
- Do not use this skill as the implementation or completion authority. It produces domain evidence; approved application changes and final Delivery state belong to the delivery workflow.

## Required Inputs

For hosted migration, require:

- source repo A path (the legacy AngularJS/jQuery/JSP/Thymeleaf repository)
- host repo B path (the existing Vue 3 host repository)
- migration unit when doing `design` or `verify`: page, URL, route, menu item, or user behavior

If only one repo is available, perform source-only assessment and state that host landing design cannot be completed.

## Workflow

1. Confirm mode, source repo A, host repo B, and optional migration unit.
2. Prefer Codebase Memory when available: index both repos, use graph search/trace/snippets for code discovery, then fall back to `rg` for templates, literals, configs, and vendor-excluded scans.
3. Load `references/hosted-vue3-migration-method.md` before any hosted migration assessment or design.
4. Load supporting analysis references only when their evidence shape appears:
   - Load `references/angularjs-construct-mapping.md` when the selected unit has AngularJS controllers, directives, components, or filters.
   - Load `references/jquery-vue3-business-logic-analysis.md` when the selected unit has jQuery entry functions, handlers, DOM mutation, or plugins.
   - Load `references/business-logic-variable-flow-analysis.md` when material behavior crosses functions/stores/server values, derives visible formulas, or builds non-trivial request/response payloads.
5. Do not load `references/angularjs-vue3-migration-method.md` on the hosted path. Load it only in `greenfield` mode, or when the user confirms no Vue3 host exists.
6. First read host B conventions before proposing landing code:
   - MPA/SPA entry layout, router, route meta, auth/permission, axios/API client, state store, component library, i18n, proxy, env config, lockfile, Node baseline, lint/build/test gates.
   - Host compile/diagnostic overlay: Vue CLI `lintOnSave`, Vite/Webpack ESLint or checker plugins, HMR overlay scope, TS `noImplicitAny`/`strict`, Prettier/EditorConfig, lint baseline, and actual `node -v` versus the declared baseline. Rules: `Host Compile And Diagnostic Overlay` in the hosted method.
7. Build a source A page-entry inventory before deep scanning:
   - JSP, Thymeleaf, HTML, server templates, page-level `ng-app`/`ng-controller`, AngularJS modules/controllers/services/directives/filters, jQuery entry functions, Ajax, DOM operations, plugins.
   - Exclude dependency noise at any depth: `.git`, `node_modules`, `bower_components`, `dist`, `build`, `target`, `coverage`, `vendor`, `vendors`, `lib`, `libs`, `locale`, `locales`, `test`, `tests`, `e2e-tests`, generated bundles, minified files, `*.spec.*`, `*.test.*`, `*.e2e.*`. Exclude `reports`, `evidence`, `openspec`, `docs`, and `doc` only when they are the repository root's first directory.
8. Produce A/B page comparison:
   - Classify each candidate with the statuses defined in `A/B Page Comparison`.
   - Include old URL/template and new host entry/route when evidence exists.
   - Treat filename/path matches as candidates only. Include match basis, candidate score, and whether human correction is required. Never mark `already-migrated` from filename matching alone.
   - Keep comparison status separate from the four unit axes (identity kind, landing strategy, switch disposition, archive disposition). Do not create compound status names for every combination. Definitions and tables live in `references/hosted-vue3-migration-method.md`.
   - Mark `already-migrated` only when source parity is closed, the approved landing strategy is satisfied, and the unit is independently reachable at runtime. Native or reused-B strategies require authorized exits to land on B; an explicitly approved `iframe-keep-A` boundary may instead complete by preserving A origin and behavior.
   - Distinguish host pages/entries from reusable components and shell files. Do not treat every `.vue` file or root `index.html` as a page.
9. Produce URL and entry mapping:
   - Prefer Java/Spring route annotations, menu config, server template returns, MPA `getPages()`/`src/pages/*/*.ts`, and host route/menu evidence over guessed file paths.
   - When Java/Spring routes are absent, AngularJS `$routeProvider`, ui-router states, hash routes, or template URL mappings are source URL evidence. When MPA is absent, Vue Router route records are host entry evidence. When i18n files are absent, visible template literals are the source copy baseline.
   - Mark file-derived URL guesses as low confidence until backed by route/menu/MPA evidence.
10. Choose migration units as independently switchable pages or user behaviors, not whole-repo batches. `design` and `verify` accept up to 5 units per run (repeat or comma-separate `--unit`); a batch is several independent units, never one large page.
11. For each selected unit, produce a page closure:
   - source templates/fragments/scripts/controllers/services/APIs/assets, including page CSS and the shared CSS/sprite/plugin styles it depends on
   - display-contract matrix rows for every source region of the unit
   - page-init and side-effect list: `angular.module(...).run`, controller init, `$timeout`/`setInterval`, first-paint `$http`, default filter values
   - host files/components/stores/API modules to reuse or change
   - old URL -> new entry mapping
   - permissions/session assumptions
   - API contracts and response-code handling
   - rollback switch and rollback condition
   - parity checks and unresolved evidence
12. When the unit is `partial-overlap` because a host shell/page already exists, treat it as unmigrated until a display-contract matrix exists. Layout presence is not migration evidence: data, copy, widget shape, defaults, and CSS are separately verifiable and usually missing. One or two filled click flows never release an existing shell page.
13. Generate evidence baseline artifacts when requested:

```bash
python -B "<skill-dir>/scripts/generate_migration_plan.py" assess --project-name "<source>-to-<host>" --source-repo "<A>" --host-repo "<B>" --output-dir "<evidence-dir>"
python -B "<skill-dir>/scripts/generate_migration_plan.py" design --unit "<unit>" --source-repo "<A>" --host-repo "<B>" --output-dir "<evidence-dir>"
python -B "<skill-dir>/scripts/generate_migration_plan.py" verify --unit "<unit>" --matrix "<ledger.md|.csv>" --source-repo "<A>" --host-repo "<B>" --output-dir "<evidence-dir>"
# After a person corrects 19-unit-decisions.csv, pass it back. Placeholder values that start with "[" are ignored.
python -B "<skill-dir>/scripts/generate_migration_plan.py" verify --unit "<unit>" --matrix "<ledger.md|.csv>" --unit-decisions "<19-unit-decisions.csv>" --source-repo "<A>" --host-repo "<B>" --output-dir "<evidence-dir>"
```

14. Treat script output as evidence baseline only. Do not treat generated tables as implementation design until reviewed against source and host code. Header-only FLOW/VAR/CHAIN contracts are not design-ready, and generated tables never substitute for the display-contract matrix.

## Scan Commands

Use Codebase Memory first. Run these from the repository root (working directory = `<source>` or `<host>`, path `.`) so root-only excludes anchor correctly. Patterns are single-quoted so PowerShell and bash both pass `$` through. A whitelist glob must come before `<EXCL>`. Use these `rg` commands only as fallback or for non-code/template evidence:

```text
EXCL = -g '!**/{node_modules,bower_components,dist,build,target,coverage,vendor,vendors,lib,libs,locale,locales,test,tests,e2e-tests}/**' -g '!/{reports,evidence,openspec,docs,doc}/**' -g '!**/*.min.*' -g '!**/*.{spec,test,e2e}.*'

rg -n <EXCL> 'ng-(app|controller|repeat|model|src|click|change|if|show|hide|include|bind-html)|ui-(view|sref)|angular\.module|\.(controller|component|directive|service|factory|filter)\(|\$(stateProvider|routeProvider|compile)\b' .
rg -n <EXCL> '\$(scope|rootScope|watch|watchCollection|emit|broadcast|http|resource|q|timeout|interval)\b' .
rg -n <EXCL> '\$\(document\)\.ready|\$\(function|\.on\(|\.click\(|\.change\(|\.submit\(|\$\.(ajax|get|post)\(|\.val\(|\.html\(|\.append\(' .
rg -n -g '*.{jsp,jspx,html,htm,ftl,vm}' <EXCL> 'th:(text|if|each|href|src|class|object|field|value|action|replace|insert|fragment|with|unless|switch|case|include|attr|inline)\b|<%@|<jsp:|<c:(if|forEach|choose)|sec:authorize|shiro:|_csrf|\$\{[^}]+\}' .
rg -n -g '*.{jsp,jspx,html,htm,ftl,vm,js}' <EXCL> 'session\.|request\.|window\.|location\.href|setInterval\(|postMessage\(' .
rg -n -g '!**/{node_modules,dist,build,coverage}/**' -g '!**/{package-lock.json,pnpm-lock.yaml,yarn.lock}' 'createApp|createRouter|defineStore|axios|createI18n|proxy|rollupOptions|getPages|element-plus|@opentiny/vue|ant-design-vue|naive-ui|pinia|jquery' .
```

These commands discover candidates only. Read definitions, callers, templates, callbacks, API wrappers, and final consumers before drawing conclusions.

## Hosted Migration Rules

- `references/hosted-vue3-migration-method.md` is authoritative for decision axes, field definitions, gates, and completion. The bullets below are only the hard stops most likely to be rationalized away.
- Reuse host B shell, auth/session, entry model, API client, state, i18n, proxy, runtime, and test gates. Do not replace the host stack unless evidence proves a blocker and the user approves.
- Do not copy source global layout. Close every selected page over source copy, field formulas, init effects, page/shared CSS, utilities, sprites, plugins, and click targets; host-extra regions and silent source "fixes" are deviations.
- A host component may replace a source widget only when the hosted-method interaction-equivalence axes pass. Generic chrome does not excuse changed selection semantics, defaults, validation, geometry, payload, rich text, or modal modes.
- Resolve unit identity and route shape before landing design. Filename similarity, a root `index.html`, a drawer, a parent shell, or a nearby tab never proves the selected source page. Keep comparison status separate from the four unit axes (identity kind, landing strategy, switch disposition, archive disposition).
- Treat outbound switching as separately authorized. Keep one landing function per UNIT, preserve query/hash identity and destination-specific absolute/relative URL semantics, and leave active exits on their approved fallback until parity and authorization are proven.
- Apply every Source Contract Gate, Comparison Surface row, and Host Integration Checklist item from the hosted method. A B skeleton, DOM presence without visibility, or a screenshot from a mismatched surface cannot pass.
- Pin identity context on every comparison surface, including a hidden-state and a visible-state surface when visibility is gated. Rules: `Comparison Surface` in the hosted method.
- Permission-list provenance is identity, and a cardinality gap is evidence of a wrong source. Rules: `Comparison And Identity` in the hosted method.
- Record a host chrome keep/hide/replace ledger before landing any unit under the host shell. An approved host chrome difference never legalizes an empty pane, a duplicated breadcrumb/footer, a base-font or title change, or a changed scroll model.
- Record host/session readiness per runtime surface (embedded in the logged-in shell vs a standalone entry); never gate the entire shell mount behind a signal one surface cannot produce.
- Contract-test counts are never MATRIX counts, and a ledger still wholly at design-time `missing` stops as `matrix-not-written-back`. Rules: `Display Contract Matrix` in the hosted method.
- `repair` requires a proven mounted host entry and matching route shape. Same-wrapper regions may extend its MATRIX; different wrappers or API, permission, traffic, or rollback changes return to full framing.
- Runtime evidence must be attempted through the host toolchain. Without agent evidence, affected runtime rows remain `wired-unverified`; only explicit per-row human evidence may produce `manual-verified`.
- A slice is complete only when its entry mounts, calls the intended API, and is user-reachable. Helpers, components, tabs, or files alone are not completion.
- Bind evidence to source/host revisions and the concrete contract files. Refresh stale digests, use file fallback when graph evidence is insufficient, and never use a negative graph result as sole absence proof.
- Keep FLOW/VAR/CHAIN and batch conclusions per selected UNIT. Do not emit whole-repo empty contracts or average a failing member into a passing batch.
- Do not create a greenfield Vue3 skeleton when a host exists. The greenfield reference remains unavailable on the hosted path.

## Red Flags

| Signal | Required response |
|---|---|
| B has a similarly named file/component | Treat it as a candidate only; prove entry, identity, runtime reachability, and MATRIX closure. |
| Root `index.html`, parent shell, drawer, or nearby tab is used as page evidence | Classify the shell separately and recover the selected unit's real mounted entry. |
| Generated `(skeleton)`, empty FLOW/CHAIN, or unresolved host gap is presented as design-ready | Stop at `not-ready` and fill the authoritative hosted-method gate. |
| `manual-only` visual evidence is used to waive MATRIX rows | Reject it; measurement fallback never closes display-contract rows. |
| An implementation status other than `verified` (for example `verified_with_residuals`), a `wired-unverified` row, or a shortened skill id is used as completion/recovery evidence | Reject completion or recovery and return it to the stage that produced it. |
| A Vite/Webpack host has no `lintOnSave` key | Inspect its ESLint/checker/HMR plugins and lint/type baseline before claiming there is no diagnostic overlay. |
| A host store/login permission list is wired as the page gate | Prove its provenance equals the list the source page reads. A cardinality gap is evidence of a wrong source and must be explained before the gate is wired. |
| Hidden-state (read-only) surface evidence is used to close permission-gated rows | Pin a visible-state surface and re-verify; gated rows stay open until the gated UI exists behind the same gate. |
| "N contract tests pass" is reported as MATRIX row status | Reject; each row's `B 现状` is written from row-level evidence, not test counts. |
| Verify starts on a ledger still wholly `missing` | Stop with `matrix-not-written-back` and return to the implementing stage. |

## Display Contract

One matrix row per source region of the unit, with a stable `DISP-<unit>-<region>-<n>` ID. Columns and status enums are defined in `references/hosted-vue3-migration-method.md`.

Rules:

- The matrix is one persisted artifact reused across `assess`, `design`, and `verify`. Incremental repairs update existing rows instead of starting a new analysis round.
- A generated whole-page `(skeleton)` row is a placeholder, not a contract. Split it by source region before the unit can be design-ready.
- All other ledger rules: `Display Contract Matrix` in the hosted method.

## Output Contracts

User-facing evidence reports, copied table contracts, and filled FLOW/VAR/CHAIN rows default to Simplified Chinese. Keep status enums, IDs (`FLOW-ID`, `unmigrated`, `not-ready: empty-contract`), paths, commands, URLs, and CSV field keys in English.

Field-level column definitions, status enums, and table headers live in `references/hosted-vue3-migration-method.md`. Do not restate them here or in orchestration prompts. This section only lists what must exist for a mode to pass. Persisted ledger tables (display-contract matrix, FLOW/VAR/CHAIN, host baseline gap) are table contracts and keep their Chinese column headers in CSV as well.

### Assess

- pass the hosted-method `assess` required-output contract; the list below names artifact groups, not a second schema
- source/host revision, repo acquisition status and warnings, git hygiene summary
- freshness manifest for the route/copy/behavior/entry/runtime files that supplied the contract
- host stack summary including host compile/diagnostic overlay and lint/type baseline
- host baseline gap table: which globals source A assumes (reset/base font, Bootstrap or other utility sheet, sprites, icon fonts, jQuery plugins, global JS libs, server-rendered globals) that host B does not provide
- source page-entry inventory, A/B page comparison with match basis and human-correction flags
- URL / entry mapping backed by Java route, menu, template return, or MPA entry, with route shape preserved and redirect hops excluded
- design-scope decision per source page: comparison status, host entry, entry-evidence type, and `repair` / `new-landing` conclusion
- per-unit identity, landing strategy, switch disposition, and initial comparison surface
- vendor-excluded coupling counts, suggested first units, gaps, risks
- for any `partial-overlap` unit: a first-pass display-contract matrix with `B 现状` filled, so shell presence is not mistaken for migration

### Design

For each selected page or user behavior (1 to 5 per run):

- pass the complete hosted-method `Design-Ready Gate`; it is the only normative checklist, while generated `11-design-ready-gate.csv` is a baseline scaffold
- page closure including CSS closure
- display-contract matrix with stable IDs
- page-init and side-effect list
- source i18n text table with any approved deviations
- behavior flow plus variable/API chains, including a field formula for each visible number/list
- host reuse/change/create decisions, URL mapping, permission/session/API parity, rollback switch and condition
- per-unit identity kind, landing strategy, switch disposition, comparison surface, and host-integration checklist
- host chrome ledger with a keep/hide/replace decision per chrome element, for every unit landing under the host shell
- vertical slices whose completion criterion is entry mounted and user-reachable
- for a batch: an admission table (units resolve to exactly one source page each, one shared design scope, no overlapping host landing) and a shared-host-surface table naming the single owner of router registration, menu, shared i18n, global stylesheets, and global store. Each unit keeps its own closure, matrix rows, and rollback switch; the gate is judged per unit and one `not-ready` unit blocks the batch.

### Verify

- matrix write-back precheck: a ledger still wholly at design-time `missing` stops as a `matrix-not-written-back` reflow to the implementing stage instead of a gate review; an unparsable ledger header stops as `matrix-header-mismatch`
- behavior, page-init, permission, URL, API, runtime, rollback checks
- display-contract parity: matrix row by row, code-comparable, mandatory, with runtime visibility confirmed for visible copy and numbers
- entry-wiring parity: each slice is mounted, called, and reachable
- strategy parity: identity, approved landing, switch disposition, comparison surface, and host-integration checks remain current
- visual measurement parity: screenshots/measurements, otherwise `manual-only`. `manual-only` here does not exempt any display-contract row.
- completion authority: domain verify evidence cannot by itself declare migration complete; require an implementation authority record from the caller (for example a Delivery `verified` handoff), current host revision, and no blocking residuals
- delivery boundary: completion reports may name downstream Delivery evidence as a required authority, but this skill must not load or call `delivery-*`
- open-state block: no selected unit may remain `dest-built-unwired`, `wired-hidden`, `develop-native`, `orphan-mpa`, `unknown`, or any other non-closed status
- archive gate table per `references/hosted-vue3-migration-method.md`: one row per unit carrying completion state, verified/total matrix count, unresolved row IDs, degradation labels, and archive disposition (`parity-complete` / `repair-done-partial` / `blocked`). Degradation labels stay attached in later reports, and known deviations enter the matrix before archive, not in a follow-up repair
- batch results are per unit and never averaged: report one conclusion per unit, and one failing unit fails the batch

## Bundled Resources

- `references/hosted-vue3-migration-method.md`: hosted dual-repo migration method, display-contract matrix, and report contracts. Load on every hosted run.
- `references/angularjs-construct-mapping.md`: AngularJS construct and runtime-semantics mapping. Load when the selected unit has AngularJS controllers, directives, components, or filters.
- `references/angularjs-vue3-migration-method.md`: greenfield fallback guidance. Not loaded on the hosted path; load only in `greenfield` mode or when no host exists.
- `references/jquery-vue3-business-logic-analysis.md`: jQuery business logic analysis method and table contracts.
- `references/business-logic-variable-flow-analysis.md`: evidence-backed business-flow and variable-chain tracing contracts.
- `scripts/generate_migration_plan.py`: generates dual-repo evidence baseline artifacts for `assess`, `design`, or `verify`.
