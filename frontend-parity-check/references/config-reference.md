# 配置与动作词表

完整可复制样例见 `templates/parity-config.json`。

## 顶层字段

| 字段 | 默认 | 说明 |
|---|---|---|
| `outputDir` | `./parity-run` | 证据与报告的落盘目录，相对配置文件解析 |
| `browser` | `chromium` | `chromium` / `firefox` / `webkit`，需对应内核已安装 |
| `channel` | — | 用本机浏览器：`chrome` / `msedge` / `chrome-beta`。企业环境下不来官方内核时的活路，由 preflight 的 `useConfig` 给出 |
| `executablePath` | — | 浏览器装在非标准路径时直接指过去；与 `channel` 二选一 |
| `assertLanded` | 见下 | 落地页硬校验：`{ forbidUrl[], allowUrl[], requireUrl }` |
| `defaultProbes` | `true` | `false` 关掉内置探针集；给数组只留其中几个（如 `["heading","table-header-cell"]`），用来消除壳层噪声 |
| `urlNormalizeRules` | `[]` | `[{pattern,replace}]`；比对 URL 前先做的自定义归一化（详情页 id、`.do` 后缀等） |
| `dataParity` | `different-data` | `same-data` 时数据类差异按缺陷判级 |
| `styleIntent` | `pixel-parity` | `redesign-allowed` 时 L4 全部降为参考 |
| `masks` | `[]` | 全局遮罩选择器，两侧同样遮罩，遮罩色相同故互相抵消 |
| `maskTextPatterns` | `[]` | 正则；命中的文本在比对前替换为 `{masked}` |
| `styleProbes` | `[]` | 追加到默认探针集之后的自定义探针 |
| `fullPage` | `false` | 整页截图；长页面开启后像素噪声会显著上升 |
| `beforeEachState` | `[]` | 每个状态进入后、快照前统一执行的动作（如关闭引导弹窗） |

日期、时间、13 位时间戳、UUID 在比对前会自动归一化，无需手写正则。

## `baseline` / `candidate`

| 字段 | 说明 |
|---|---|
| `baseUrl` | 必填。所有 `path` 相对它解析 |
| `label` | 报告里的人类可读标签 |
| `pathOverrides` | `{ id: "/新路径" }`，处理两侧路由不一致。**key 可以是 route id、journey id，或带 `id` 的 `goto` 动作 id** |
| `urlTokens` | `{ "/legacy/detail.do": "{detail}" }`，声明不属于任何 route 的等价路径 |
| `userAgent` / `extraHTTPHeaders` | 需要指定 UA 或注入网关头时使用 |
| `auth.storageState` | Cookie/localStorage 文件路径；存在则直接复用。可用 `scripts/export-storage-state.mjs` 从已登录浏览器生成 |
| `auth.actions` | 文件不存在时执行的登录动作序列，成功后自动写入该文件。**任一步失败即整侧作废** |

也可以在 `routes[].baselinePath` / `routes[].candidatePath`、
`journeys[].baselineStartPath` / `journeys[].candidateStartPath` 上做单页路径覆盖。

**声明过的路径迁移不会被判为缺陷**：比对前 `pathOverrides` / `<side>Path` / `urlTokens`
里的路径会被换成 `{route:id}` 这样的占位符，两侧因此相等；**没声明**的路径差异仍然按
跳转缺陷阻断。所以路由变了就写进配置，不要靠人工在报告里划掉。

## `assertLanded`

判断"采到的是不是目标页"。任一条不满足 → 该状态/流程证据作废，落 `failure.png` 后跳过比对。

| 字段 | 默认 | 说明 |
|---|---|---|
| `forbidUrl` | 内置登录/SSO 特征集 | 最终 URL 命中即作废：`/login`、`/signin`、`login-*.` 域名、`/cas/login`、`/oauth2/authorize`、`redirect_uri=`、`service=*login` |
| `allowUrl` | `[]` | 白名单，优先于 `forbidUrl`。**被测页本身就是登录页时必须配**，否则永远作废 |
| `requireUrl` | — | 正则；最终 URL 必须匹配（例如强制留在 `/dashboard`） |

`forbidUrl` 给空数组等于关掉该校验 —— 只在确认站点无 SSO 时这么做，且要在结论里写明。
可在 `routes[].assertLanded` 上按页覆盖。

## `context`

`viewports`（`[{name,width,height}]`）、`deviceScaleFactor`、`locale`、`timezoneId`、
`colorScheme`、`freezeTime`（ISO 字符串，冻结 `Date`）、`seedRandom`（固定
`Math.random`）、`timeoutMs`、`navTimeoutMs`、`ignoreHTTPSErrors`。

两侧强制共用同一份 `context` —— 这是 parity 结论成立的前提。

## `routes[]`

```jsonc
{
  "id": "order-list",                 // 状态 id 前缀，必须唯一
  "path": "/order/list",
  "waitFor": { "selector": ".el-table__row", "state": "visible" },  // 未命中 → 本状态作废
  "waitUntil": "networkidle",         // goto 的等待策略
  "assertLanded": { "allowUrl": [] }, // 可按页覆盖顶层落地校验
  "fullPage": false,
  "masks": [".update-time"],          // 追加到全局 masks
  "styleProbes": [{ "id": "toolbar", "selector": ".table-toolbar" }],
  "states": [
    { "id": "default", "actions": [] },
    { "id": "search-filled", "actions": [ /* 动作序列 */ ] }
  ]
}
```

状态未声明时默认只跑 `default`。状态目录名为 `<routeId>__<stateId>`。

`route.waitFor` 有两重身份：既是"页面渲染完了"的信号，也是"确实到了这一页"的判据。
导航后未命中直接作废（不会再产出可比证据）；动作执行后未命中只记 `warning`，
因为动作本身可能就是要离开这个锚点。

## `journeys[]`

```jsonc
{
  "id": "search-then-open-detail",
  "startPath": "/order/list",
  "waitFor": { "selector": ".el-table__row" },
  "steps": [ /* 动作序列，可穿插 capture 与 expect* */ ]
}
```

Journey 只在**第一个视口**执行一次。某一步失败即中断（`stopOnFail: false` 可放行），
中断位置本身就是重要证据。`startPath` 同样认 `pathOverrides[journey.id]` 与
`journeys[].<side>StartPath`。

## 动作词表

| type | 参数 | 作用 |
|---|---|---|
| `goto` | `path`, `waitUntil`, `id` | 导航到相对路径；带 `id` 时可被 `pathOverrides[id]` 覆盖 |
| `click` / `dblclick` / `hover` | `selector`, `nth`, `force` | 指针操作 |
| `fill` | `selector`, `value` | 直接置值 |
| `type` | `selector`, `value`, `delay` | 逐字输入，触发联想/校验 |
| `press` | `key`, `selector?` | 键盘 |
| `select` | `selector`, `value` | 原生 `<select>` |
| `check` / `uncheck` | `selector` | 勾选框 |
| `scrollTo` | `selector` 或 `y` | 滚动 |
| `waitFor` | `selector`, `state`, `timeout` | 等元素 |
| `waitForUrl` | `pattern`（正则字符串） | 等跳转 |
| `waitTimeout` | `ms` | 兜底等待，尽量少用 |
| `expectVisible` | `selector` | 记录可见性 |
| `expectText` | `selector` | 记录文本（归一化后比对） |
| `expectValue` | `selector` | 记录输入框当前值 |
| `expectCount` | `selector`, `visibleOnly` | 记录匹配数量。**默认只数可见节点**；`visibleOnly: false` 才连隐藏节点一起数 |
| `expectUrl` | `ignorePath` | 记录当前 URL；比对前按 `pathOverrides`/`urlNormalizeRules` 归一化。`ignorePath: true` 时只比 query/hash |
| `capture` | `id` | 在流程中间打一次完整快照 |

`expect*` **不做断言**，只记录观测值；判定由 `compare.mjs` 在两侧之间进行。
这是有意设计：不需要预先知道正确答案，旧版的行为就是答案。

`expectCount` 默认只数可见节点，是因为旧框架把隐藏项留在 DOM 里（AngularJS `ng-hide`、
`v-show`）而新框架直接不渲染（`v-if`），连隐藏一起数会凭空报出"少了一项"。
两侧的原始总数记在 `observedTotal`，仅在报告里作为附注出现，不参与判定。

所有 `selector` 走 Playwright 定位语法，支持 CSS、`text=`、`role=` 等。
给动作加 `id` 能让报告里的条目可读。

## iframe 的处理边界

- **L2 语义摘要穿透 iframe**：主文档 + 每个可读 iframe（同域与跨域都试）的标题、按钮、
  字段、链接、表格、文案会合并进 `dom.json`。托管页把顶栏/菜单放在 iframe 里时，
  那些链接不再被误报成"缺失"。
- 真正读不到的 iframe（`sandbox` 禁脚本、已 detach）标记为 `unreadable` 并写进
  `meta.json` / `dom.json` 的 `frames`。此时"缺失的按钮/字段/链接/文案"会**降级**并附
  提示——它是"读不到"，不是"没有"。
- **L3/L4 探针只看主文档**：`styleProbes` 不穿 iframe。iframe 内的样式差异靠 L2（结构）
  和 L5（像素）覆盖；确实要量 iframe 内的计算样式，就把那个 iframe 的 URL 当独立
  route 单独比。
- 小于 20×20 或 `about:blank` 的 iframe 直接跳过（埋点、占位）。

## 输出结构

```text
<outputDir>/
  baseline/<viewport>/<state>/{shot.png,dom.json,styles.json,runtime.json,meta.json}
  baseline/<viewport>/<state>/{failure.png,failure.json}   # 仅作废状态：为什么没采到
  baseline/capture-log.json
  candidate/...
  diff/<viewport>__<state>.png
  parity-report.md
  parity-summary.json
```

`meta.json` 额外记录本状态实际生效的探针 id、iframe 读取结果（`frames`）与采集告警。
`parity-summary.json` 的 `invalidEvidence` 是作废证据条数，非 0 时结论不能推广到那些页面。

`parity-summary.json` 是给下游消费的紧凑视图（结论、计数、findings、图片路径）。
向用户或其他技能交接时给路径，不要把内容整体贴出来。

## 命令行参数

| 参数 | 适用 | 说明 |
|---|---|---|
| `--config <file>` | 全部 | 必填 |
| `--side <baseline\|candidate>` | capture | 必填 |
| `--out <dir>` | capture / compare | 覆盖 `outputDir` |
| `--only <id,id>` | capture | 只跑指定 route/journey，调试用 |
| `--headed` | capture | 有头模式，观察脚本卡在哪一步 |
| `--keepGoing` | capture | 有状态采集失败也返回 0 |
| `--channel <chrome\|msedge>` | capture / compare | 覆盖配置里的 `channel`，用本机浏览器 |
| `--executablePath <path>` | capture / compare | 覆盖配置里的 `executablePath` |

退出码：capture `0` 成功 / `1` 有采集错误 / `2` 参数或配置错 / `3` 找不到 Playwright；
compare `0` 通过或仅有警告 / `1` 存在阻断项 / `2` 缺少采集结果。

## 自检

```bash
node scripts/selftest/run.mjs      # 单测 + 端到端
node scripts/selftest/unit.mjs     # 只跑判定规则单测（无浏览器，1 秒内）
```

`unit.mjs` 断言判定规则本身：登录页识别（含"业务路径里带 login 字样"不误判）、
`pathOverrides` 归一化、探针裁剪、L4 聚合、iframe 合并与 `unreadable` 标记。

端到端在 9401/9402 起两个故意有差异的本地站点（少一个筛选项、少一个导出按钮、
表格列改名、主题色/圆角/字号漂移、详情按钮抛异常、SSO 跳转页、iframe 顶栏少一个链接、
旧版残留 `ng-hide` 隐藏项、声明过的路径迁移），跑完整流水线并同时断言两件事：
**该报的都报了**，且**不该报的一条都没报**（隐藏节点计数、已声明的路径迁移）。
全 PASS 说明采集、判定、像素 diff、报告生成都正常；用于排除"是环境问题还是被测页面问题"。

## 排查

| 症状 | 处理 |
|---|---|
| 状态 `error`，超时在 `waitFor` | 选择器在新版已改名；看 `failure.png` 确认落地页，再用 `--headed` 观察后修正 |
| 报告顶部提示"证据作废：落地 URL 命中禁止模式" | 站点静默跳了 SSO。补 `auth.storageState`（可用 `export-storage-state.mjs` 从已登录浏览器导出）；被测页本身是登录页则配 `assertLanded.allowUrl` |
| 用户说"我已经登录了"但脚本还是跳登录页 | Playwright 用的是干净会话，与用户浏览器不共享。带 `--remote-debugging-port=9222` 重启浏览器登录后导出 `storageState`；导出脚本不会关用户的浏览器 |
| 托管页顶栏/菜单链接被报"缺失"，截图里明明有 | 内容在 iframe 里。现已自动合并可读 iframe；若报告标了 `iframe 不可读`，说明该 frame 禁脚本或已 detach，按"读不到"处理，不要当缺陷 |
| 计数类差异"6 对 5"但页面上看着一样 | 旧版把隐藏项留在 DOM（`ng-hide`/`v-show`），新版 `v-if` 不渲染。`expectCount` 默认已只数可见节点；看 `observedTotal` 确认 |
| `expectUrl` 被判阻断，但地址本来就该不同 | 路径迁移没声明。写进 `<side>.pathOverrides` / `urlTokens`，或给该步加 `ignorePath: true` |
| 像素差异恒定在 1–3%，热点分散全页 | 字体未就绪或整体位移；检查字体加载与滚动条，或加 `settleMs` |
| 大量 L4 差异集中在 `font-size` | 根字号或 `html{font-size}` 变了，属于全局回归；报告会收敛成一条"全局样式漂移" |
| L4 全是壳层噪声（`body`/`button`/`link`） | 用 `defaultProbes: false` 或给数组只留业务探针，再用 `styleProbes` 指到真正关心的组件 |
| 每次跑差异比例都不同 | 存在未遮罩的动态内容；补 `masks` / `freezeTime` / `seedRandom` |
| 探针 `found: false` 但页面上有该元素 | 元素在 iframe 或 Shadow DOM 内（L4 探针不穿 iframe）；换具体选择器、把该 iframe 当独立 route，或改用 journey 验证 |
