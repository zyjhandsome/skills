# Business Logic And Variable Full-Chain Analysis

## Core Principle

Migration analysis must reconstruct what the application does and how each material value reaches that result. A grep hit is only a starting point: follow definitions, scopes, aliases, nested paths, function boundaries, asynchronous callbacks, templates, requests, state, and DOM effects using source evidence.

## Analysis Unit And Stable IDs

- Assign one stable `FLOW-ID` to each business action, such as query, save, approve, delete, or export.
- Assign one stable `VAR-ID` to each material value or canonical object path.
- Assign one stable `CHAIN-ID` to each end-to-end value trace.
- Link every business-flow row to its related `CHAIN-ID` values.
- Keep IDs stable within one report. Split a chain when values diverge into independent business outcomes.

## End-To-End Workflow

Trace each business action in this order:

```text
entry/event
  → guard/validation/permission
  → source read
  → transformation
  → service/Ajax/event call
  → response/error handling
  → state write
  → template/DOM/plugin/navigation side effect
```

Read the entry, every called function, service wrapper, callback, and consuming template. Record alternate and early-return branches rather than flattening them into the success path.

## Variable Node And Edge Types

| Operation | Meaning |
|---|---|
| `DEFINE` | Declare a local, controller field, service field, constant, or global. |
| `INJECT` | Receive a value through AngularJS DI, scope inheritance, binding, closure, or external input. |
| `ALIAS` | Create another name or reference for the same value or object. |
| `READ` | Read a variable or normalized nested path. |
| `WRITE` | Assign or mutate a variable or nested path. |
| `PASS` | Pass a value as an argument, callback payload, event payload, or request input. |
| `RETURN` | Return a value synchronously or through a Promise. |
| `WATCH` | Consume a value through `$watch`, `$watchCollection`, subscription, or timer. |
| `TEMPLATE` | Consume or mutate a value through interpolation, directive expression, or `ng-model`. |
| `AJAX` | Use a value in a request, response, or error contract. |
| `STATE` | Store a value in scope, a shared service, cache, or global state. |
| `DOM` | Cause text, attribute, class, visibility, HTML, navigation, or plugin effects. |
| `UNRESOLVED` | Preserve a dynamic or missing edge that static evidence cannot prove. |

## Scope And Injection Resolution

For each definition and use, record the owning scope/function and lifetime. Resolve:

- `$scope`, `$rootScope`, inherited scope, `controllerAs`, and `bindToController`
- component bindings and directive isolate scope
- controller, service, factory, provider, filter, and ordinary closure
- function arguments, return values, callbacks, Promise handlers, and event payloads
- jQuery `data-*`, hidden fields, plugin-managed state, and globals
- comparison operators and runtime types when they affect branches, display, payloads, navigation, or permissions

Do not assume an unqualified template expression resolves to a similarly named `$rootScope` path. Record the edge as unresolved until scope inheritance, binding, or runtime evidence proves it.

## Alias And Nested Path Normalization

Expand aliases while retaining where and for how long each alias is valid. Use one canonical path across the chain:

```text
vm.order.customer.address.city
items[*].price
settings[<dynamic:key>]
response.data.status
```

Distinguish object mutation (`vm.order.status = value`) from reference reassignment (`vm.order = other`). Preserve the field path affected by each `READ` and `WRITE`.

## Cross-Function And Async Tracing

At every call boundary:

1. map caller expressions to callee parameters with `PASS`;
2. trace aliases and nested reads inside the callee;
3. map returned fields back to the caller with `RETURN`;
4. continue through service/factory wrappers;
5. connect Promise resolution/rejection values to callbacks;
6. record error, retry, and short-circuit branches.

For Ajax, trace request URL fields and body fields separately, then trace response and error fields to their final consumers.

## Watch And Template Consumption

Treat templates as code consumers. Search interpolation, `ng-model`, `ng-if`, `ng-show`, `ng-repeat`, `ng-disabled`, event expressions, and directive bindings.

For `$watch` and related subscriptions, record the watched expression, old/new callback parameters, condition, state mutations, DOM effects, and cleanup. A two-way `ng-model` is both a template read and a possible write source.

## Ajax, State, And DOM Side Effects

End a chain only after identifying the business-visible result:

- `AJAX`: endpoint, method, request field, response/error field
- `STATE`: `$scope`, `$rootScope`, shared service, cache, or global write
- `DOM`: selector/element, operation, class/style/text/HTML/plugin change
- template/navigation: visibility, disabled state, route, redirect, or download

State which side effects depend on each guard or response condition.

## Dynamic And Unresolved References

Preserve uncertainty explicitly:

```text
obj[key]                → obj[<dynamic:key>] + UNRESOLVED edge
items[index].price      → items[*].price unless index is statically known
$parse(expr)            → preserve expr and require runtime logging/check
window[name]            → record global source and unresolved property
selector concatenation  → record DOM target pattern, not a fabricated element
```

An unresolved record must state the known source, missing evidence, risk, and a concrete runtime check such as logging the evaluated key/expression, instrumenting the event, or capturing the actual selector.

## Evidence And Confidence Rules

Every material node includes `file:line`, scope/function, condition, business meaning, and confidence.

- **High:** definition and consumption both have direct source evidence.
- **Medium:** an explicit call relationship connects the nodes, but framework or runtime resolution remains.
- **Low:** a dynamic property, string event, plugin state, or missing caller requires inference.

Separate facts, inferences, and `UNRESOLVED` edges. Never raise confidence because a guessed chain appears plausible.

## Required Output Tables

Copy these headers into user-facing reports. Table titles and column labels are Simplified Chinese; IDs and operation enums stay English.

### 业务流

| FLOW-ID | 步骤 | 入口/触发 | 条件 | 输入 | 处理 | 输出 | 调用目标 | 副作用 | 业务含义 | 证据 | 置信度 | 关联 CHAIN-ID |
|---|---:|---|---|---|---|---|---|---|---|---|---|---|

### 变量定义与来源

| VAR-ID | 变量/路径 | 定义/来源 | 作用域 | 初值 | 证据 | 置信度 |
|---|---|---|---|---|---|---|

### 注入与作用域

| VAR-ID | 注入/绑定 | 源作用域 | 目标作用域 | 生命周期 | 证据 | 置信度 |
|---|---|---|---|---|---|---|

### 别名映射

| 别名 | 规范路径 | 别名类型 | 作用域/函数 | 创建于 | 有效至 | 证据 |
|---|---|---|---|---|---|---|

### 嵌套读写

| CHAIN-ID | VAR-ID | 规范化路径 | 读/写 | 值来源/去向 | 条件 | 证据 | 置信度 |
|---|---|---|---|---|---|---|---|

### 跨函数传递

| CHAIN-ID | 调用方 | 被调方 | 参数/返回 | 上游路径 | 下游路径 | 异步阶段 | 证据 | 置信度 |
|---|---|---|---|---|---|---|---|---|

### Watch 与模板消费

| CHAIN-ID | 消费类型 | 表达式/路径 | Watcher/模板 | 条件 | 结果 | 证据 | 置信度 |
|---|---|---|---|---|---|---|---|

### Ajax、状态与 DOM 副作用

| CHAIN-ID | 副作用类型 | 目标 | 输入路径 | 条件 | 业务结果 | 证据 | 置信度 |
|---|---|---|---|---|---|---|---|

### 端到端变量引用链

| CHAIN-ID | 步骤 | VAR-ID | 规范化路径 | 操作 | 作用域/函数 | 上游 | 下游 | 条件 | 业务含义 | 证据 | 置信度 | Vue3 Host 落点 |
|---|---:|---|---|---|---|---|---|---|---|---|---|---|

### 未决边

| 未决边 | 表达式 | 已知来源 | 缺失证据 | 运行时检查 | 风险 | 证据 |
|---|---|---|---|---|---|---|

## Worked Example

Given the `app.js` and `order.html` fixture used below, the save flow is:

| FLOW-ID | 步骤 | 入口/触发 | 条件 | 输入 | 处理 | 输出 | 调用目标 | 副作用 | 业务含义 | 证据 | 置信度 | 关联 CHAIN-ID |
|---|---:|---|---|---|---|---|---|---|---|---|---|---|
| FLOW-SAVE | 1 | form submit | — | `orderForm` | call `vm.submit` | form state | controller | begin save | user requests save | `order.html:2` | High | CHAIN-CITY, CHAIN-POSTAL, CHAIN-PERMISSION |
| FLOW-SAVE | 2 | `vm.submit` | valid and edit allowed | form, order, permission | build payload | id/city/postalCode | `buildPayload` | — | enforce save rules | `app.js:17-21` | High | CHAIN-CITY, CHAIN-POSTAL, CHAIN-PERMISSION |
| FLOW-SAVE | 3 | payload ready | guard passed | payload | POST order | Promise response | `OrderApi.save` | request | persist order | `app.js:5,21-22` | High | CHAIN-CITY, CHAIN-POSTAL |
| FLOW-SAVE | 4 | Promise resolved | success callback | response | map result | status/message | callback | state and DOM updates | show save result | `app.js:22-25` | High | CHAIN-STATUS |

Key aliases:

| 别名 | 规范路径 | 别名类型 | 作用域/函数 | 创建于 | 有效至 | 证据 |
|---|---|---|---|---|---|---|
| `vm.order` | `$scope.initialOrder` | object reference | `OrderCtrl` | controller init | reassignment/destruction | `app.js:14` |
| `customer` | `$scope.initialOrder.customer` | local alias | `OrderCtrl` | controller init | controller destruction | `app.js:15` |
| `address` | `$scope.initialOrder.customer.address` | local alias | `vm.submit` | submit entry | submit return | `app.js:18` |

Representative chains:

| CHAIN-ID | 步骤 | VAR-ID | 规范化路径 | 操作 | 作用域/函数 | 上游 | 下游 | 条件 | 业务含义 | 证据 | 置信度 | Vue3 Host 落点 |
|---|---:|---|---|---|---|---|---|---|---|---|---|---|
| CHAIN-CITY | 1 | VAR-ORDER | `$scope.initialOrder` | INJECT | `OrderCtrl` | scope input | `vm.order` | — | initial order source | `app.js:14` | High | route/prop/store input |
| CHAIN-CITY | 2 | VAR-CITY | `vm.order.customer.address.city` | ALIAS | `OrderCtrl/vm.submit` | `vm.order→customer→address` | `address.city` | — | locate shipping city | `app.js:14-18` | High | reactive form state |
| CHAIN-CITY | 3 | VAR-CITY | `vm.order.customer.address.city` | PASS | `vm.submit→buildPayload` | `address.city` | `payload.city` | form valid and allowed | request city | `app.js:19,21,29-33` | High | API request DTO |
| CHAIN-CITY | 4 | VAR-CITY | `payload.city` | AJAX | `OrderApi.save` | payload | POST body | guard passed | persist city | `app.js:5,22` | High | API client |
| CHAIN-CITY | 5 | VAR-CITY | `vm.order.customer.address.city` | WATCH | `$scope.$watch` | order city | callback `city` | city changes | refresh preview | `app.js:37-38` | High | Vue `watch` |
| CHAIN-CITY | 6 | VAR-CITY | `vm.order.customer.address.city` | DOM | watch callback | callback `city` | `#city-preview` text | city changes | display city preview | `app.js:38` | High | declarative template |
| CHAIN-POSTAL | 1 | VAR-POSTAL | `vm.order.customer.address.postal.code` | TEMPLATE | `order.html` | order state | interpolation | span rendered | display postal code | `order.html:5` | High | interpolation/computed |
| CHAIN-POSTAL | 2 | VAR-POSTAL | `vm.order.customer.address.postal.code` | PASS | `buildPayload` | `address.postal.code` | `payload.postalCode` | form valid and allowed | request postal code | `app.js:21,29-33` | High | API request DTO |
| CHAIN-STATUS | 1 | VAR-STATUS | `response.data.status` | READ | Promise callback | response | `vm.order.status` | request succeeds | receive saved status | `app.js:22-23` | High | API response DTO |
| CHAIN-STATUS | 2 | VAR-STATUS | `vm.order.status` | WRITE | Promise callback | response status | order state | request succeeds | update saved order | `app.js:23-24` | High | reactive state/store |
| CHAIN-STATUS | 3 | VAR-STATUS | `vm.order.status` | TEMPLATE | `order.html` | order state | `ng-if` | equals `saved` | show saved content | `order.html:4-6` | High | `v-if` |

Permission resolution remains explicit:

| 未决边 | 表达式 | 已知来源 | 缺失证据 | 运行时检查 | 风险 | 证据 |
|---|---|---|---|---|---|---|
| UNRESOLVED-PERMISSION | template `permissions.orderEdit` vs controller `$rootScope.permissions.orderEdit` | controller guard and template disable rule | scope inheritance/binding proof | inspect scope tree or log both values during submit | UI and controller may enforce different values | `app.js:19`; `order.html:7` |

The example additionally records `vm.order→$scope.lastSavedOrder` as a `STATE` effect (`app.js:24`) and `response.data.message→#save-result` as a `DOM` effect (`app.js:25`).

## Quick Reference

| 问题 | 所需证据 | 工件 |
|---|---|---|
| 动作从哪开始？ | handler/template/router `file:line` | 业务流 |
| 值从哪来？ | 定义、注入或输入 | 变量定义 |
| 是不是同一个对象？ | 赋值与生命周期 | 别名映射 |
| 哪个嵌套字段变了？ | 精确读写表达式 | 嵌套读写 |
| 怎么跨过函数边界？ | 调用、参数、返回、回调 | 跨函数传递 |
| 谁消费它？ | watch/模板/请求/状态/DOM 位置 | 消费/副作用表 |
| 什么无法证明？ | 动态表达式与缺失环节 | 未决边 |
| 在 Vue 里落到哪？ | 已证明的归属与生命周期 | Vue3 Host 落点列 |

## Common Mistakes

- Treating grep hits as a completed analysis instead of reading callers and consumers.
- Flattening aliases and losing object identity or alias lifetime.
- Losing AngularJS scope ownership across controllers, directives, and templates.
- Treating nested object mutation as whole-reference reassignment.
- Omitting template reads and `ng-model` writes.
- Stopping at an Ajax call instead of tracing response/error callbacks.
- Fabricating dynamic keys, parsed expressions, globals, selectors, or plugin state.
- Choosing a Vue store/composable/component target without preserving the business meaning and lifecycle proved by the chain.
