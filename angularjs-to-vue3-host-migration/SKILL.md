---
name: angularjs-to-vue3-host-migration
description: Use when assessing, designing, or verifying migration of AngularJS 1.x/jQuery/JSP/Thymeleaf mixed legacy pages into an existing Vue 3 host repository. Supports dual-repo source-vs-host comparison, page-level migration units, business-flow and variable-chain reconstruction, host-stack gap analysis, URL/permission/API rollback gates, and evidence reports for projects like hiapm -> apmweb3. Not for greenfield Vue 3 creation unless no host repository exists.
---

# AngularJS To Vue 3 Host Migration

Use this skill to produce evidence and page-level designs for moving AngularJS 1.x, jQuery, JSP, Thymeleaf, and server-rendered page islands into an existing Vue 3 host. Default to **hosted migration**: source repo A supplies legacy behavior; host repo B owns the final entry, shell, auth, build, API conventions, components, state, i18n, proxy, and runtime gates.

This skill is independent. Do not depend on `delivery-*` or other migration skills. Reuse ideas only by restating the needed rule here.

## Modes

- `assess`: compare source A and Vue3 host B, identify overlaps, gaps, risks, and candidate migration units.
- `design`: produce an implementation-ready page/user-behavior design for one specified migration unit.
- `verify`: define and/or run parity checks for behavior, permission, URL, API, visual evidence, rollback, and host build gates.
- `greenfield`: use only when the user explicitly has no Vue3 host. This is not the default path.

Default mode is `assess` unless the user names a page or asks for implementation design/verification.

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
4. Load `references/jquery-vue3-business-logic-analysis.md` and `references/business-logic-variable-flow-analysis.md` when analyzing a concrete page/user behavior.
5. First read host B conventions before proposing landing code:
   - MPA/SPA entry layout, router, route meta, auth/permission, axios/API client, state store, component library, i18n, proxy, env config, lockfile, Node baseline, lint/build/test gates.
6. Build a source A page-entry inventory before deep scanning:
   - JSP, Thymeleaf, HTML, server templates, page-level `ng-app`/`ng-controller`, AngularJS modules/controllers/services/directives/filters, jQuery entry functions, Ajax, DOM operations, plugins.
   - Exclude dependency and evidence noise: `.git`, `node_modules`, `dist`, `build`, `target`, `coverage`, `reports`, `evidence`, `openspec`, `test`, `tests`, `e2e-tests`, `vendor`, `vendors`, `lib`, `libs`, `locale`, `locales`, generated bundles, minified files, `*.spec.*`, `*.test.*`, `*.e2e.*`.
7. Produce A/B page comparison:
   - `unmigrated`, `partial-overlap`, `already-migrated`, `host-page-only`, `host-component`, `host-shell`, `unknown`.
   - Include old URL/template and new host entry/route when evidence exists.
   - Treat filename/path matches as candidates only. Include match basis, candidate score, and whether human correction is required. Never mark `already-migrated` from filename matching alone.
   - Distinguish host pages/entries from reusable components and shell files. Do not treat every `.vue` file or root `index.html` as a page.
8. Produce URL and entry mapping:
   - Prefer Java/Spring route annotations, menu config, server template returns, MPA `getPages()`/`src/pages/*/*.ts`, and host route/menu evidence over guessed file paths.
   - Mark file-derived URL guesses as low confidence until backed by route/menu/MPA evidence.
9. Choose migration units as independently switchable pages or user behaviors, not whole-repo batches.
10. For each selected unit, produce a page closure:
   - source templates/fragments/scripts/controllers/services/APIs/assets
   - host files/components/stores/API modules to reuse or change
   - old URL -> new entry mapping
   - permissions/session assumptions
   - API contracts and response-code handling
   - rollback switch and rollback condition
   - parity checks and unresolved evidence
11. Generate evidence baseline artifacts when requested:

```bash
python scripts/generate_migration_plan.py assess \
  --project-name "hiapm-to-apmweb3" \
  --source-repo "D:/path/hiapm" \
  --host-repo "D:/path/apmweb3" \
  --output-dir reports/angularjs-vue3-migration
```

12. Treat script output as evidence baseline only. Do not treat generated tables as implementation design until reviewed against source and host code. Header-only FLOW/VAR/CHAIN contracts are not design-ready.

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

- Reuse host B shell, auth/session, router/MPA entry, API client, component library, state, i18n, env, proxy, lint/build/test commands.
- Do not copy JSP/Thymeleaf/global layout from source A into host B. Extract behavior and contracts, then land them in host-native pages/components.
- Do not default to creating a Vue3 skeleton. Use greenfield Vite/create-vue only when no host exists.
- Do not replace host B runtime stack unless the gap analysis proves a blocker and the user approves.
- Bind evidence to source and host revisions. If either repo changes, affected evidence and design decisions expire.
- Keep FLOW/VAR/CHAIN tables scoped to the selected page/user behavior. Do not emit whole-repo empty chains.

## Output Contracts

### Assess

Include:

- source revision and host revision
- repo acquisition status, clone/fetch warnings, readable HEAD, and whether an existing repo was reused after acquisition failure
- git hygiene summary: dirty entries, dependency/cache/build noise, lockfile changes, business/source changes, and stage usability
- host stack summary: build, Node/Volta, lockfile, Vue version, router/MPA, MPA entry discovery, state, API client, UI library, i18n, proxy, host jQuery, test gates
- source page-entry inventory with mixed-stack signals
- A/B page comparison: unmigrated, partial-overlap, already-migrated, host-page-only, host-component, host-shell, unknown
- match basis, candidate score, human-correction flag, and host page/component classification
- URL / entry mapping from source server route/template evidence to host MPA/router/menu entry
- vendor-excluded coupling counts
- suggested first migration units and why
- gaps blocking implementation design
- risks and early warning signals

### Design

For one page or user behavior, include:

- page closure
- source behavior flow and variable/API chains
- reuse/change/create decisions in host B
- old URL -> new host entry mapping
- permission/session/API parity requirements
- rollback switch and rollback condition
- implementation slice order
- verification checklist
- unresolved edges with runtime checks
- design-ready gate proving page closure, at least 1-2 filled core behavior flows, material variable/API chains, host reuse/change/create decisions, URL mapping, permission/API/rollback draft

### Verify

Include concrete checks for:

- behavior parity: inputs, validation, branching, success/error states
- permission parity: menu, route, button, hidden/disabled behavior, server recheck
- URL parity: old deep link, query, hash, back/forward, redirect
- API parity: endpoint, method, request fields, response codes, error messages
- visual parity: screenshot/measurement evidence; otherwise mark manual-only
- runtime parity: host B Node, lockfile, lint/build/test commands
- rollback: trigger, scope, user impact, restore condition
- completion authority: domain verify evidence cannot by itself declare migration complete; require Delivery verified evidence, current host revision, and no blocking residuals

## Bundled Resources

- `references/hosted-vue3-migration-method.md`: hosted dual-repo migration method and report contracts.
- `references/angularjs-vue3-migration-method.md`: AngularJS construct mapping and greenfield fallback guidance.
- `references/jquery-vue3-business-logic-analysis.md`: jQuery business logic analysis method and table contracts.
- `references/business-logic-variable-flow-analysis.md`: evidence-backed business-flow and variable-chain tracing contracts.
- `scripts/generate_migration_plan.py`: generates dual-repo evidence baseline artifacts for `assess`, `design`, or `verify`.
