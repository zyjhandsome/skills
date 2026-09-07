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

- source repo A path, such as `hiapm`
- host repo B path, such as `apmweb3`
- migration unit when doing `design` or `verify`: page, URL, route, menu item, or user behavior

If only one repo is available, perform source-only assessment and state that host landing design cannot be completed.

## Workflow

1. Confirm mode, source repo A, host repo B, and optional migration unit.
2. Prefer Codebase Memory when available: index both repos, use graph search/trace/snippets for code discovery, then fall back to `rg` for templates, literals, configs, and vendor-excluded scans.
3. Load `references/hosted-vue3-migration-method.md` before any hosted migration assessment or design.
4. Load supporting analysis references only when their evidence shape appears:
   - Load `references/jquery-vue3-business-logic-analysis.md` when the selected unit has jQuery entry functions, handlers, DOM mutation, or plugins.
   - Load `references/business-logic-variable-flow-analysis.md` when material behavior crosses functions/stores/server values, derives visible formulas, or builds non-trivial request/response payloads.
5. Do not load `references/angularjs-vue3-migration-method.md` on the hosted path. Load it only in `greenfield` mode, or when the user confirms no Vue3 host exists.
6. First read host B conventions before proposing landing code:
   - MPA/SPA entry layout, router, route meta, auth/permission, axios/API client, state store, component library, i18n, proxy, env config, lockfile, Node baseline, lint/build/test gates.
   - Host compile/diagnostic overlay: Vue CLI `lintOnSave`, Vite/Webpack ESLint or checker plugins, HMR overlay scope, TS `noImplicitAny`/`strict`, Prettier/EditorConfig, lint baseline, and actual `node -v` versus the declared baseline.
7. Build a source A page-entry inventory before deep scanning:
   - JSP, Thymeleaf, HTML, server templates, page-level `ng-app`/`ng-controller`, AngularJS modules/controllers/services/directives/filters, jQuery entry functions, Ajax, DOM operations, plugins.
   - Exclude dependency and evidence noise: `.git`, `node_modules`, `dist`, `build`, `target`, `coverage`, `reports`, `evidence`, `openspec`, `test`, `tests`, `e2e-tests`, `vendor`, `vendors`, `lib`, `libs`, `locale`, `locales`, generated bundles, minified files, `*.spec.*`, `*.test.*`, `*.e2e.*`.
8. Produce A/B page comparison:
   - `unmigrated`, `partial-overlap`, `already-migrated`, `dest-built-unwired`, `wired-hidden`, `develop-native`, `orphan-mpa`, `deprecated-removed`, `host-page-only`, `host-component`, `host-shell`, `unknown`.
   - Include old URL/template and new host entry/route when evidence exists.
   - Treat filename/path matches as candidates only. Include match basis, candidate score, and whether human correction is required. Never mark `already-migrated` from filename matching alone.
   - Keep four decisions separate: comparison status, unit identity kind, landing strategy, and switch disposition. Do not create compound status names for every combination. Definitions and tables live in `references/hosted-vue3-migration-method.md`.
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
python scripts/generate_migration_plan.py assess \
  --project-name "hiapm-to-apmweb3" \
  --source-repo "D:/path/hiapm" \
  --host-repo "D:/path/apmweb3" \
  --output-dir reports/angularjs-vue3-migration
```

14. Treat script output as evidence baseline only. Do not treat generated tables as implementation design until reviewed against source and host code. Header-only FLOW/VAR/CHAIN contracts are not design-ready, and generated tables never substitute for the display-contract matrix.

## Scan Commands

Use Codebase Memory first. Use these `rg` commands only as fallback or for non-code/template evidence:

```bash
rg -n --glob '!{node_modules,dist,build,target,coverage,reports,evidence,openspec,test,tests,e2e-tests,vendor,vendors,lib,libs,locale,locales}/**' --glob '!*.min.*' --glob '!*.spec.*' --glob '!*.test.*' "ng-app|ng-controller|ng-repeat|ng-model|ng-src|ng-click|ng-change|angular\.module|\.controller\(|\.component\(|\.directive\(|\.service\(|\.factory\(|\.filter\(" <source>
rg -n --glob '!{node_modules,dist,build,target,coverage,vendor,vendors,lib,libs,locale,locales}/**' --glob '!*.min.*' "\$scope|\$rootScope|\$watch|\$emit|\$broadcast|\$http|\$resource|\$q" <source>
rg -n --glob '!{node_modules,dist,build,target,coverage,vendor,vendors,lib,libs,locale,locales}/**' --glob '!*.min.*' "\$\(document\)\.ready|\$\(function|\.on\(|\.click\(|\.change\(|\.submit\(|\$\.ajax\(|\.val\(|\.html\(|\.append\(" <source>
rg -n --glob '!{node_modules,dist,build,target,coverage,reports,evidence,openspec,test,tests,e2e-tests,vendor,vendors,lib,libs,locale,locales}/**' --glob '!*.min.*' --glob '!*.spec.*' --glob '!*.test.*' "th:(text|if|each|href|src|class|object|field|value|action|replace|insert|fragment|with|unless|switch|case|include|attr)\b|<%@|jsp:|session\.|request\.|data-|window\.|location\.href|setInterval\(" <source>
rg -n "createApp|createRouter|defineStore|axios|i18n|proxy|vite|webpack|scripts/getpage|element-plus|@opentiny/vue|ant-design-vue|naive-ui|pinia|jquery" <host>
```

These commands discover candidates only. Read definitions, callers, templates, callbacks, API wrappers, and final consumers before drawing conclusions.

## Hosted Migration Rules

- `references/hosted-vue3-migration-method.md` is authoritative for decision axes, field definitions, gates, and completion. The bullets below are only the hard stops most likely to be rationalized away.
- Reuse host B shell, auth/session, entry model, API client, state, i18n, proxy, runtime, and test gates. Do not replace the host stack unless evidence proves a blocker and the user approves.
- Do not copy source global layout. Close every selected page over source copy, field formulas, init effects, page/shared CSS, utilities, sprites, plugins, and click targets; host-extra regions and silent source "fixes" are deviations.
- A host component may replace a source widget only when the hosted-method interaction-equivalence axes pass. Generic chrome does not excuse changed selection semantics, defaults, validation, geometry, payload, rich text, or modal modes.
- Resolve unit identity and route shape before landing design. Filename similarity, a root `index.html`, a drawer, a parent shell, or a nearby tab never proves the selected source page; keep comparison status, identity, landing strategy, switch disposition, and archive disposition separate.
- Treat T16/outbound switching as separately authorized. Keep one landing function per UNIT, preserve query/hash identity and destination-specific absolute/relative URL semantics, and leave active exits on their approved fallback until parity and authorization are proven.
- Apply every Source Contract Gate, Comparison Surface row, and Host Integration Checklist item from the hosted method. A B skeleton, DOM presence without visibility, or a screenshot from a mismatched surface cannot pass.
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
| `verified_with_residuals`, `wired-unverified`, or a shortened skill id is used as completion/recovery evidence | Reject completion or recovery and return to the producing wave. |
| A Vite/Webpack host has no `lintOnSave` key | Inspect its ESLint/checker/HMR plugins and lint/type baseline before claiming there is no diagnostic overlay. |

## Display Contract

One matrix row per source region of the unit, with a stable `DISP-<unit>-<region>-<n>` ID. Columns and status enums are defined in `references/hosted-vue3-migration-method.md`.

Rules:

- The matrix is one persisted artifact reused across `assess`, `design`, and `verify`. Incremental repairs update existing rows instead of starting a new analysis round.
- A generated whole-page `(skeleton)` row is a placeholder, not a contract. Split it by source region before the unit can be design-ready.
- Display-contract parity is code-comparable and mandatory. It is separate from pixel/screenshot measurement, and `manual-only` never excuses copy, widget shape, defaults, geometry, or field formulas.
- DOM presence is not visibility. For rows marked as visible copy or visible numbers, confirm the element is actually visible at runtime, since host or shared CSS such as `font-size: 0` can hide correct markup.

## Host Compile And Diagnostic Overlay

Read these host facts before landing code, and record them as parity requirements:

- Active diagnostic mechanism: Vue CLI `lintOnSave`, Vite/Webpack ESLint/checker plugins, HMR/dev-server overlay scope, TS `noImplicitAny`/`strict`, and the current lint baseline.
- Actual `node -v` versus host-declared Volta/`.nvmrc`/`engines.node`. A test or build run on a different Node is not verification evidence.
- New or changed TS helpers in the selected UNIT must type callback parameters and empty arrays/objects when host strictness can infer implicit `any`, `any[]`, or `never[]`.
- Do not reformat, retype, or otherwise "fix along the way" legacy files outside approved scope. Any active diagnostic plugin or lint-on-save path can turn an unrelated dirty file into a full-page overlay; record those files as residuals with an owner instead of editing them.
- A compile failure on the current unit's entry is blocking. A repo-wide overlay from unrelated files is a residual, and neither may be reported as a healthy dev server.

## Output Contracts

User-facing evidence reports, copied table contracts, and filled FLOW/VAR/CHAIN rows default to Simplified Chinese. Keep status enums, IDs (`FLOW-ID`, `unmigrated`, `not-ready: empty-contract`), paths, commands, URLs, and CSV field keys in English.

Field-level column definitions, status enums, and table headers live in `references/hosted-vue3-migration-method.md`. Do not restate them here or in orchestration prompts. This section only lists what must exist for a mode to pass.

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
- vertical slices whose completion criterion is entry mounted and user-reachable
- for a batch: an admission table (units resolve to exactly one source page each, one shared design scope, no overlapping host landing) and a shared-host-surface table naming the single owner of router registration, menu, shared i18n, global stylesheets, and global store. Each unit keeps its own closure, matrix rows, and rollback switch; the gate is judged per unit and one `not-ready` unit blocks the batch.

### Verify

- behavior, page-init, permission, URL, API, runtime, rollback checks
- display-contract parity: matrix row by row, code-comparable, mandatory, with runtime visibility confirmed for visible copy and numbers
- entry-wiring parity: each slice is mounted, called, and reachable
- strategy parity: identity, approved landing, switch disposition, comparison surface, and host-integration checks remain current
- visual measurement parity: screenshots/measurements, otherwise `manual-only`. `manual-only` here does not exempt any display-contract row.
- completion authority: domain verify evidence cannot by itself declare migration complete; require Delivery verified evidence, current host revision, and no blocking residuals
- delivery boundary: completion reports may name downstream Delivery evidence as a required authority, but this skill must not load or call `delivery-*`
- open-state block: no selected unit may remain `dest-built-unwired`, `wired-hidden`, `develop-native`, `orphan-mpa`, `unknown`, or any other non-closed status
- archive gate table per `references/hosted-vue3-migration-method.md`: one row per unit carrying completion state, verified/total matrix count, unresolved row IDs, degradation labels, and archive disposition (`parity-complete` / `repair-done-partial` / `blocked`). Degradation labels stay attached in later reports, and known deviations enter the matrix before archive, not in a follow-up repair
- batch results are per unit and never averaged: report one conclusion per unit, and one failing unit fails the batch

## Bundled Resources

- `references/hosted-vue3-migration-method.md`: hosted dual-repo migration method, display-contract matrix, and report contracts. Load on every hosted run.
- `references/angularjs-vue3-migration-method.md`: AngularJS construct mapping and greenfield fallback guidance. Not loaded on the hosted path; load only in `greenfield` mode or when no host exists.
- `references/jquery-vue3-business-logic-analysis.md`: jQuery business logic analysis method and table contracts.
- `references/business-logic-variable-flow-analysis.md`: evidence-backed business-flow and variable-chain tracing contracts.
- `scripts/generate_migration_plan.py`: generates dual-repo evidence baseline artifacts for `assess`, `design`, or `verify`.
