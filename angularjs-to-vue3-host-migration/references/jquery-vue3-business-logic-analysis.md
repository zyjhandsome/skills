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
| `$("#id").val()` | `v-model`, refs, form object | create field mapping before changing submit payload; for identity fields, prove the source-to-host mapping and do not substitute a nearby store getter |
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

Copy these headers into user-facing reports. Table titles and column labels are Simplified Chinese; IDs, selectors, URLs, and risk enums stay English.

### 页面基本信息

| 项 | 内容 |
|---|---|
| 页面名称 | |
| URL / 路由 | |
| HTML 文件 | |
| JS 文件 | |
| CSS 文件 | |
| jQuery 插件 | |
| 后端接口数 | |
| 主要业务功能 | |

### 页面功能清单

| 功能 | 触发 | 接口 | 是否核心 | 风险 | 备注 |
|---|---|---|---|---|---|
| query | search button | | yes/no | low/medium/high | |
| add/edit/save/delete/export | | | | | |

### 入口函数表

| 入口/函数 | 顺序 | 用途 | 是否依赖 API | 是否影响页面状态 |
|---|---:|---|---|---|
| `$(function(){})` | 1 | page init | no | yes |
| `initPage()` / `loadData()` / `bindEvents()` | | | | |

### 事件绑定表

| 元素 | 选择器 | 事件 | 处理函数 | 业务动作 | 前置条件 | 下一步 | 风险 |
|---|---|---|---|---|---|---|---|

### Ajax 接口表

| URL | 方法 | 调用方 | 输入来源 | 输入字段 | 成功处理 | 失败处理 | 业务含义 | 风险 |
|---|---|---|---|---|---|---|---|---|

### 表单字段表

| 字段 | 元素 | jQuery 读写 | 类型 | 是否必填 | 默认值 | 校验 | 业务含义 |
|---|---|---|---|---|---|---|---|

### 校验规则表

| 字段 | 条件 | 错误提示 | 中断方式 | 函数 | 后端是否再校验 | 风险 |
|---|---|---|---|---|---|---|

### 业务规则表

| 规则 ID | 规则 | 条件 | 动作 | 函数 | 元素 | 风险 |
|---|---|---|---|---|---|---|

### 页面状态与权限表

| 状态/权限 | 来源 | 条件 | UI 行为 | 允许动作 | 阻断动作 | 风险 |
|---|---|---|---|---|---|---|

### DOM 操作表

| DOM 操作 | 类型 | 目标 | 触发 | 业务含义 | Vue 迁移建议 | 风险 |
|---|---|---|---|---|---|---|

### 插件依赖表

| 插件类型 | 插件 | 页面 | 用途 | Vue 替代 | 难度 | 风险 | 建议 |
|---|---|---|---|---|---|---|---|

### 导航 / 全局量 / 定时器 / 异常表

有对应代码时再补：

- 导航：源页、目标页、参数、来源、业务含义
- 全局量：变量、定义位置、来源、用途、Vue 落点、风险
- 定时器：间隔、函数、用途、停止条件、清理风险
- 异常：失败场景、当前处理、用户提示、是否阻断、日志、改进

### Vue 影响与测试表

| jQuery 逻辑 | 当前实现 | Vue 落点 | 影响 | 难度 | 风险 | 测试重点 |
|---|---|---|---|---|---|---|

| 测试场景 | 前置条件 | 步骤 | 期望结果 | 相关功能 | 风险 |
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

| 项 | 结论 |
|---|---|
| 页面复杂度 | low / medium / high |
| 核心业务功能 | |
| 高风险逻辑 | |
| 主要接口 | |
| 主要状态 | |
| 主要权限点 | |
| 是否适合先迁 | yes / no |
| Vue 迁移建议 | |
| 回归测试重点 | |
