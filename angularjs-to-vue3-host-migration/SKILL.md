---
name: angularjs-to-vue3-host-migration
description: Use when assessing, designing, or verifying migration of AngularJS 1.x/jQuery/JSP/Thymeleaf mixed legacy pages into an existing Vue 3 host repository. Supports dual-repo source-vs-host comparison, page-level migration units, business-flow and variable-chain reconstruction, host-stack gap analysis, URL/permission/API rollback gates, and evidence reports for projects like hiapm -> apmweb3. Not for greenfield Vue 3 creation unless no host repository exists.
---

# AngularJS To Vue 3 Migration

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
   - Exclude dependency noise: `.git`, `node_modules`, `dist`, `build`, `target`, `coverage`, `vendor`, `vendors`, `lib`, `libs`, `locale`, `locales`, generated bundles, minified files.
7. Produce A/B page comparison:
   - `unmigrated`, `partial-overlap`, `already-migrated`, `host-only`, `unknown`.
   - Include old URL/template and new host entry/route when evidence exists.
8. Choose migration units as independently switchable pages or user behaviors, not whole-repo batches.
9. For each selected unit, produce a page closure:
   - source templates/fragments/scripts/controllers/services/APIs/assets
   - host files/components/stores/API modules to reuse or change
   - old URL -> new entry mapping
   - permissions/session assumptions
   - API contracts and response-code handling
   - rollback switch and rollback condition
   - parity checks and unresolved evidence
10. Generate evidence baseline artifacts when requested:

```bash
python scripts/generate_migration_plan.py assess \
  --project-name "hiapm-to-apmweb3" \
  --source-repo "D:/path/hiapm" \
  --host-repo "D:/path/apmweb3" \
  --output-dir reports/angularjs-vue3-migration
```

11. Treat script output as evidence baseline only. Do not treat generated tables as implementation design until reviewed against source and host code.

## Scan Commands

Use Codebase Memory first. Use these `rg` commands only as fallback or for non-code/template evidence:

```bash
rg -n --glob '!{node_modules,dist,build,target,coverage,vendor,vendors,lib,libs,locale,locales}/**' --glob '!*.min.*' "ng-app|ng-controller|angular\.module|\.controller\(|\.component\(|\.directive\(|\.service\(|\.factory\(|\.filter\(" <source>
rg -n --glob '!{node_modules,dist,build,target,coverage,vendor,vendors,lib,libs,locale,locales}/**' --glob '!*.min.*' "\$scope|\$rootScope|\$watch|\$emit|\$broadcast|\$http|\$resource|\$q" <source>
rg -n --glob '!{node_modules,dist,build,target,coverage,vendor,vendors,lib,libs,locale,locales}/**' --glob '!*.min.*' "\$\(document\)\.ready|\$\(function|\.on\(|\.click\(|\.change\(|\.submit\(|\$\.ajax\(|\.val\(|\.html\(|\.append\(" <source>
rg -n --glob '!{node_modules,dist,build,target,coverage,vendor,vendors,lib,libs,locale,locales}/**' --glob '!*.min.*' "th:|<%@|jsp:|session\.|request\.|data-|window\.|location\.href|setInterval\(" <source>
rg -n "createApp|createRouter|defineStore|axios|i18n|proxy|vite|webpack|element-plus|ant-design-vue|naive-ui|pinia" <host>
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
- host stack summary: build, Node, lockfile, Vue version, router, state, API client, UI library, i18n, proxy, test gates
- source page-entry inventory with mixed-stack signals
- A/B page comparison: unmigrated, partial-overlap, already-migrated, host-only, unknown
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
