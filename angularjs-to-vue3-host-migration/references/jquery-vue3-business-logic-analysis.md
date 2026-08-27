# jQuery To Vue 3 Business Logic Analysis

Distilled from:

- `D:\projects\book2skills\jQuery 业务逻辑代码分析方法.txt`
- `D:\projects\book2skills\jQuery 迁移 Vue 影响范围分析表.txt`
- `D:\projects\book2skills\jQuery 业务逻辑分析表模板.txt`

## Core Principle

jQuery migration analysis is not line-by-line syntax translation. First reconstruct the business flow:

```text
page entry
  -> event binding
  -> form/data extraction
  -> frontend validation
  -> Ajax request
  -> backend response
  -> DOM update
  -> page state / permission / navigation change
  -> business result
```

Only after the flow is explicit should it be mapped to Vue components, reactive state, router, API modules, store, and tests.

## Where jQuery Business Logic Hides

| Location | Typical Logic |
|---|---|
| HTML inline `<script>` | page init, event binding, form validation |
| standalone `.js` files | business handlers, Ajax, DOM updates |
| plugin initialization | table, modal, date picker, tree, upload, chart, validation |
| Ajax callbacks | success/failure business handling |
| DOM attributes | `data-*`, hidden input state, row IDs |
| globals | user, permissions, mode, current ID, config |
| timers | polling, countdown, delayed refresh |
| URL params | page mode, detail ID, task ID, route state |

## Analysis Order

1. Page entry: find `$(document).ready`, `$(function)`, `initPage`, `loadData`, `bindEvents`.
2. Events: map selector -> event -> handler -> business action.
3. Ajax: map handler -> endpoint -> method -> params -> response handling.
4. Data: identify form fields, hidden inputs, URL params, table row data, globals, `data-*`.
5. Rules: extract validation, status checks, permissions, backend code handling.
6. DOM state: explain show/hide, disabled, class/style, dynamic HTML, table/list updates.
7. Plugins: list plugin purpose, pages, data contract, lifecycle, Vue replacement risk.
8. Navigation: record redirects, query params, history usage, file export links.
9. Tests: derive regression cases from features, states, permissions, interfaces, and plugins.

## Code Audit Commands

Use these as evidence collection, not as a substitute for reading handlers and callbacks:

```bash
rg -n "\$\(document\)\.ready|\$\(function|\.ready\(" .
rg -n "\.on\(|\.click\(|\.change\(|\.submit\(|\.keyup\(|\.blur\(" .
rg -n "\$\.ajax\(|\$\.get\(|\$\.post\(|url\s*:" .
rg -n "\.val\(|\.html\(|\.text\(|\.append\(|\.show\(|\.hide\(|\.addClass\(|\.removeClass\(|\.css\(" .
rg -n "\.prop\(|\.attr\(|return false|alert\(|confirm\(|if\s*\(|switch\s*\(" .
rg -n "DataTables|dataTable|jqGrid|bootstrapTable|datepicker|zTree|modal\(|upload|select2|chosen|validate\(" .
rg -n "window\.|setInterval\(|setTimeout\(|location\.href|window\.location|history\.back|data-" .
```

## jQuery To Vue Mapping

| jQuery Pattern | Vue 3 Target | Migration Rule |
|---|---|---|
| `$("#id").val()` | `v-model`, refs, form object | create field mapping before changing submit payload |
| `.click()`, `.on()` | `@click`, `@change`, component events | preserve preconditions and downstream actions |
| `$.ajax`, `$.get`, `$.post` | API module with `fetch`/`axios` | centralize auth, errors, timeout, response code handling |
| `.show()`, `.hide()` | `v-if`, `v-show`, computed state | name the business state behind visibility |
| `.addClass()`, `.removeClass()`, `.css()` | `:class`, `:style` | drive styling from explicit state |
| `.append(html)`, `.html()` | template, `v-for`, component rendering | avoid `v-html` unless content is trusted and reviewed for XSS |
| hidden input state | route params, reactive state, Pinia | do not keep invisible DOM as state source |
| globals on `window` | Pinia/store, config module, composables | define lifecycle and initialization order |
| table/modal/date/tree/upload plugins | Vue components or wrapped adapter | assess behavior parity and teardown needs |
| `location.href`, URL concat | Vue Router or download API | preserve query params, bookmarks, export behavior |

## Required Tables

### Page Basic Information

| Item | Content |
|---|---|
| Page name | |
| URL / route | |
| HTML file | |
| JS files | |
| CSS files | |
| jQuery plugins | |
| backend interface count | |
| primary business functions | |

### Page Feature List

| Feature | Trigger | Interfaces | Core? | Risk | Notes |
|---|---|---|---|---|---|
| query | search button | | yes/no | low/medium/high | |
| add/edit/save/delete/export | | | | | |

### Entry Function Table

| Entry / function | Order | Purpose | Depends on API? | Affects page state? |
|---|---:|---|---|---|
| `$(function(){})` | 1 | page init | no | yes |
| `initPage()` / `loadData()` / `bindEvents()` | | | | |

### Event Binding Table

| Element | Selector | Event | Handler | Business action | Preconditions | Next action | Risk |
|---|---|---|---|---|---|---|---|

### Ajax Interface Table

| URL | Method | Caller | Input source | Input fields | Response handling | Failure handling | Business meaning | Risk |
|---|---|---|---|---|---|---|---|---|

### Form Field Table

| Field | Element | jQuery read/write | Type | Required? | Default | Validation | Business meaning |
|---|---|---|---|---|---|---|---|

### Validation Rule Table

| Field | Condition | Error message | Interrupt style | Function | Backend recheck? | Risk |
|---|---|---|---|---|---|---|

### Business Rule Table

| Rule ID | Rule | Condition | Action | Function | Elements | Risk |
|---|---|---|---|---|---|---|

### Page State And Permission Tables

| State / permission | Source | Condition | UI behavior | Allowed actions | Blocked actions | Risk |
|---|---|---|---|---|---|---|

### DOM Operation Table

| DOM operation | Type | Target | Trigger | Business meaning | Vue migration advice | Risk |
|---|---|---|---|---|---|---|

### Plugin Dependency Table

| Plugin type | Plugin | Pages | Purpose | Vue replacement | Difficulty | Risk | Advice |
|---|---|---|---|---|---|---|---|

### Navigation / Globals / Timer / Exception Tables

Include these when matching code exists:

- navigation: source page, target page, params, source, business meaning
- globals: variable, definition location, source, usage, Vue target, risk
- timers: interval, function, purpose, stop condition, cleanup risk
- exceptions: failure scenario, current handling, user message, blocking behavior, logging, improvement

### Vue Impact And Test Tables

| jQuery logic | Current implementation | Vue target | Impact | Difficulty | Risk | Test focus |
|---|---|---|---|---|---|---|

| Test scenario | Preconditions | Steps | Expected result | Related feature | Risk |
|---|---|---|---|---|---|

## Risk Rules

Mark these high risk unless code evidence proves otherwise:

- dynamic HTML insertion with `.html()` or `.append(html)`
- hidden inputs or globals used as business state
- plugin-managed table rows, selected nodes, uploads, dates, or modal state
- permission implemented only by hiding buttons
- save/delete/approval flows with hand-written validation and Ajax callbacks
- export links built through URL concatenation
- timers without explicit cleanup
- backend response code handling repeated across pages

## Output Conclusion Contract

For each page, end with:

| Item | Conclusion |
|---|---|
| page complexity | low / medium / high |
| core business functions | |
| high-risk logic | |
| primary interfaces | |
| primary states | |
| primary permission points | |
| suitable for early migration? | yes / no |
| Vue migration advice | |
| regression test focus | |
