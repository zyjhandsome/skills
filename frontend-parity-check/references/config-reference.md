# 配置与动作词表

完整可复制样例见 `templates/parity-config.json`。

## 顶层字段

| 字段 | 默认 | 说明 |
|---|---|---|
| `name` | `unnamed` | 本次验收的稳定名称；也用于未显式指定 `outputDir` 时生成页面级目录 |
| `outputDir` | `./parity-runs/<name>` | 证据与报告目录，相对配置文件解析；必须按页面/模块隔离 |
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
| `compareSurface` | 整个主文档 | 两侧真正参与 L2–L5 的业务表面，可分别声明 frame/root/URL 闸与排除区域 |
| `runtimePolicy` | 见下 | 新增失败请求的分级/忽略策略 |
| `dataSelectors` | 常见表格数据区 | 明确标记数据依赖区域；`different-data` 只降级这些区域 |
| `fullPage` | `false` | 整页截图；长页面开启后像素噪声会显著上升 |
| `beforeEachState` | `[]` | 每个状态进入后、快照前统一执行的动作（如关闭引导弹窗） |

日期、时间、13 位时间戳、UUID 在比对前会自动归一化，无需手写正则。两侧 capture
会记录同一份配置的 SHA-256 指纹；compare 发现指纹、浏览器版本或 context 不同会拒绝比对。

## `compareSurface`

比较面是验收契约，不是单纯的截图遮罩。例如旧版业务页在宿主 iframe 中、新版为独立页：

```jsonc
{
  "compareSurface": {
    "id": "task-report-body",
    "baseline": {
      "mainUrlPattern": "report\\.do",
      "frame": "iframe#task-report-frame",
      "frameUrlPattern": "/apmweb3/taskReport\\.html",
      "root": "#task-report-main"
    },
    "candidate": {
      "mainUrlPattern": "/taskReport\\.html",
      "root": "#task-report-main"
    },
    "exclude": [".global-header", ".aside-wrapper"]
  }
}
```

- `frame` 是 iframe 元素的 CSS/Playwright selector；省略表示主文档。
- `root` 是该 frame/document 内业务根节点。DOM、探针、截图及默认 journey 定位均以它为根。
- `mainUrlPattern` 校验浏览器主 frame；`frameUrlPattern` 校验选中的业务 iframe。
- `readySelector` 可替代 route/journey 的 `waitFor.selector`。
- `exclude` 同时排除 DOM/探针并遮罩截图，适合已确认不属于验收面的宿主区域。
- route/journey 可局部覆盖；popup capture 使用 `compareSurface: {"reset":true,...}` 清除全局表面。

不要把 `shell-vs-dest` 当成一种可以直接出结论的模式；必须把两侧解析成同一业务表面。

## `baseline` / `candidate`

| 字段 | 说明 |
|---|---|
| `baseUrl` | 必填。所有 `path` 相对它解析 |
| `label` | 报告里的人类可读标签 |
| `pathOverrides` | `{ id: "/新路径" }`，处理两侧路由不一致。**key 可以是 route id、journey id，或带 `id` 的 `goto` 动作 id** |
| `urlTokens` | `{ "/legacy/detail.do": "{detail}" }`，声明不属于任何 route 的等价路径 |
| `userAgent` / `extraHTTPHeaders` | 需要指定 UA 或注入网关头时使用 |
| `auth.mode` | 推荐 `auto-interactive`：先无头验证，必要时打开专用可见浏览器供用户登录；省略则沿用 `storageState` / `actions` 旧流程 |
| `auth.storageState` | Cookie/localStorage 文件路径；`auto-interactive` 默认 `./auth/<side>.json` |
| `auth.interactive` | `{startPath,successUrlPattern,readySelector,timeoutMs,probeTimeoutMs,readinessTimeoutMs,readyHoldMs,waitSliceMs,heartbeatMs,confirmPath,profileDir,channel,executablePath,openOnUnready}`；profile 必须是 Skill 专用目录；`readySelector` 必须是登录后才出现的节点 |
| `auth.actions` | 非交互备选：文件不存在时执行登录动作，成功后自动写入。**不能与 `auto-interactive` 混用，任一步失败即整侧作废** |

也可以在 `routes[].baselinePath` / `routes[].candidatePath`、
`journeys[].baselineStartPath` / `journeys[].candidateStartPath` 上做单页路径覆盖。

**声明过的路径迁移不会被判为缺陷**：比对前 `pathOverrides` / `<side>Path` / `urlTokens`
里的路径会被换成 `{route:id}` 这样的占位符，两侧因此相等；**没声明**的路径差异仍然按
跳转缺陷阻断。所以路由变了就写进配置，不要靠人工在报告里划掉。

### `auth.mode=auto-interactive`

```jsonc
{
  "auth": {
    "mode": "auto-interactive",
    "storageState": "./auth/candidate.json",
    "interactive": {
      "startPath": "/order/list",
      "successUrlPattern": "/order/list",
      "readySelector": ".tab-list",
      "timeoutMs": 600000,
      "probeTimeoutMs": 4000,
      "readyHoldMs": 1500
    }
  }
}
```

先运行 `node scripts/prepare-auth.mjs --config parity-config.json --side candidate`。脚本会先用
现有 `storageState`（若有）或干净会话做短探测（默认约 4 秒）。首个 route/journey 的 URL、比较面和
`waitFor` / `readySelector` 先通过、再保持一小段时间（`readyHoldMs`，默认 1.5 秒）仍通过，才算就绪。
未就绪则尝试打开隔离的持久化浏览器。`prepare-auth` 必须后台运行；只有输出
`LOGIN_WINDOW_READY` 且 `visible:true` 才能确认窗口已经创建。只有“准备创建”或进程已经退出时，
应报告启动错误，不能让用户寻找不存在的窗口。按 baseline → candidate 逐侧处理，不要同时开两侧。
确认开窗后让用户自行完成账号、扫码、MFA 或证书登录，并在对话回复「已登录」；随后执行
`node scripts/prepare-auth.mjs --config parity-config.json --side candidate --confirm`。
`--confirm` 会先检查该 side 的等待租约与后台 PID，只向仍在等待的窗口写确认标记；孤立确认会失败，
不会遗留到下一次运行。窗口会立刻校验，未就绪则马上打印 URL 和原因退出，不再默默等到
`timeoutMs`。页面自己就绪时仍会自动保存。
`--force-interactive` 只表示未就绪必须开窗，**不跳过**已有会话的无头验证。只有自检/调试才用
`--skip-probe`。关窗前会用刚写出的 `storageState` 冷启动再打开目标 URL，仍通过才报 `ready` 并落盘；
假就绪（壳子闪一下）不会替换上一份已验证的 `storageState`。
`capture.mjs` 发现该模式缺少状态文件时退出码为 `4`，不会悄悄采集登录页。

默认 `openOnUnready` 为开：扫码页、自定义 SSO、登录表单识别不到时也开窗，避免 agent 自行探究。
只有确认未就绪是 404 / `waitFor` 配错、且不要打扰用户时，才设 `openOnUnready: false`。

默认 profile 在 `./auth/profiles/<name>/<side>`，与用户日常浏览器隔离；配置若指向 Chrome/Edge
日常用户目录会被拒绝。通常无需设置端口。`channel` / `executablePath` 仅在交互登录要使用与
正式采集不同于顶层配置的浏览器二进制时覆盖；同一轮两侧仍应使用相同浏览器。
`readySelector` 必须是**登录后才出现**的节点，默认跟首个 route/journey 的 `waitFor` 对齐。
禁止用 `#app` / `#root`、Header、面包屑、登录前就画出的标题；也不要用“必须有数据行”的选择器。
`successUrlPattern` 可把登录成功限定在指定 URL。

## `assertLanded`

判断"采到的是不是目标页"。任一条不满足 → 该状态/流程证据作废，落 `failure.png` 后跳过比对。

| 字段 | 默认 | 说明 |
|---|---|---|
| `forbidUrl` | 内置登录/SSO 特征集 | 最终 URL 命中即作废：`/login`、`/signin`、`login-*.` 域名、`/cas/login`、`/oauth2/authorize`、`redirect_uri=`、`service=*login` |
| `allowUrl` | `[]` | 仅作为 `forbidUrl` 的精确例外；仍然必须通过 `requireUrl`。不要填写宽泛业务域名 |
| `requireUrl` | — | 正则；最终 URL 必须匹配（例如强制留在 `/dashboard`） |

`allowUrl` 不再是“全部落地规则放行”。即使它命中，`requireUrl` 仍会执行。业务域名写进
`allowUrl` 会扩大登录例外范围，应改为具体登录页路径；正常业务 URL 用 `requireUrl` 或
`compareSurface.mainUrlPattern` 表达。`forbidUrl` 给空数组等于关掉该校验 —— 只在确认站点
无 SSO 时这么做，且要在结论里写明。
可在 `routes[].assertLanded` 上按页覆盖。

## `runtimePolicy`

```jsonc
{
  "runtimePolicy": {
    "ignoreConsolePatterns": ["known optional widget"],
    "ignoreRequestPatterns": ["/known-host-widget\\.png"],
    "majorRequestPatterns": ["/optional-module/"],
    "blockRequestPatterns": ["/task-report-main\\.js"]
  }
}
```

仅主文档导航失败默认阻断，其余新增失败请求默认重要。规则按 ignore → block → major 的
顺序匹配。不要把某个产品的 Gantt、图表或宿主路径写死进通用 Skill；只有用户确认与验收面
无关后才能在本次配置中降级。运行时证据会记录 `resourceType`、`frameUrl` 与是否导航请求。

## `context`

`viewports`（`[{name,width,height}]`）、`deviceScaleFactor`、`locale`、`timezoneId`、
`colorScheme`、`freezeTime`（ISO 字符串，冻结 `Date`）、`seedRandom`（固定
`Math.random`）、`timeoutMs`、`navTimeoutMs`、`networkIdleTimeoutMs`、`ignoreHTTPSErrors`。
导航默认等待 `domcontentloaded`；页面就绪以后只额外短等网络空闲（默认 2 秒），避免轮询、SSE、
WebSocket 页面长期卡在 `networkidle`。

两侧强制共用同一份 `context` —— 这是 parity 结论成立的前提。

## `routes[]`

```jsonc
{
  "id": "order-list",                 // 状态 id 前缀，必须唯一
  "path": "/order/list",
  "waitFor": { "baselineSelector": ".old-row", "candidateSelector": ".new-row", "state": "visible" },
  "waitUntil": "domcontentloaded",    // 默认值；再由 waitFor/readySelector 判定业务就绪
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
因为动作本身可能就是要离开这个锚点。登录就绪与采集共用这份选择器时，它还必须是
**登录后才出现**的节点：登录前就会画出的壳、Header、面包屑不能当成功。

## `journeys[]`

```jsonc
{
  "id": "search-then-open-detail",
  "startPath": "/order/list",
  "waitFor": { "selector": ".el-table__row" },
  "steps": [ /* 动作序列，可穿插 capture 与 expect* */ ]
}
```

Journey 只在**第一个视口**执行一次。默认定位在该 journey 的 `compareSurface.frame/root` 内。
某一步失败即中断（`stopOnFail: false` 可放行），
中断位置本身就是重要证据。`startPath` 同样认 `pathOverrides[journey.id]` 与
`journeys[].<side>StartPath`。

## 动作词表

| type | 参数 | 作用 |
|---|---|---|
| `goto` | `path`, `waitUntil`, `id` | 导航到相对路径；带 `id` 时可被 `pathOverrides[id]` 覆盖 |
| `click` / `dblclick` / `hover` | `selector`, `baselineSelector?`, `candidateSelector?`, `nth`, `force`, `scope?` | 指针操作 |
| `clickAndExpectPopup` | `selector`, `popupId`, `scope?`, `timeout?` | 点击并等待 `window.open`，保存 popup 供后续步骤使用 |
| `expectPopup` | `popupId`, `timeout?` | 等待已由其他动作触发的 popup |
| `fill` | `selector`, `value` 或 `valueEnv` | 直接置值；密码优先使用环境变量 |
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
| `expectCount` | `selector`, `visibleOnly`, `dataDependent` | 默认只数可见节点；计数默认视为数据依赖，可显式设 `false` |
| `expectUrl` | `ignorePath` | 记录当前 URL；比对前按 `pathOverrides`/`urlNormalizeRules` 归一化。`ignorePath: true` 时只比 query/hash |
| `capture` | `id` | 在流程中间打一次完整快照 |

每个带 selector 的动作都可用 `baselineSelector` / `candidateSelector`，避免用逗号把两个
不同 DOM 的候选节点混在一起。`scope: {"frame":"iframe#x"}` 显式切 frame；
`scope: {"page":"preview"}` 切到由 popup 动作保存的页面。

`expect*` **不做断言**，只记录观测值；判定由 `compare.mjs` 在两侧之间进行。
这是有意设计：不需要预先知道正确答案，旧版的行为就是答案。

`expectCount` 默认只数可见节点，是因为旧框架把隐藏项留在 DOM 里（AngularJS `ng-hide`、
`v-show`）而新框架直接不渲染（`v-if`），连隐藏一起数会凭空报出"少了一项"。
两侧的原始总数记在 `observedTotal`，仅在报告里作为附注出现，不参与判定。

动作、`waitFor`、`masks` 的 selector 走 Playwright 定位语法，支持 CSS、`text=`、`role=` 等。
**`styleProbes` 例外：只能使用浏览器原生 CSS**，因为它在页面内通过
`document.querySelectorAll` 执行。`:has-text()`、`text=`、`>>` 会在采集前直接报配置错误。
给动作加 `id` 能让报告里的条目可读。

## iframe 的处理边界

- **L2 语义摘要穿透 iframe**：主文档 + 每个可读 iframe（同域与跨域都试）的标题、按钮、
  字段、链接、表格、文案会合并进 `dom.json`。托管页把顶栏/菜单放在 iframe 里时，
  那些链接不再被误报成"缺失"。
- 真正读不到的 iframe（`sandbox` 禁脚本、已 detach）标记为 `unreadable` 并写进
  `meta.json` / `dom.json` 的 `frames`。此时"缺失的按钮/字段/链接/文案"会**降级**并附
  提示——它是"读不到"，不是"没有"。
- 未声明 `compareSurface` 时，L3/L4 仍只看主文档；声明 `compareSurface.frame` 后，
  DOM、L3/L4 与截图会在选中的业务 iframe/root 内执行。
- 未选中的 iframe 不会混入显式业务表面；兼容旧配置的整页模式仍会合并可读 iframe，
  且每个摘要项带 `source=main/frame:n`，避免跨 frame 错配。
- 小于 20×20 或 `about:blank` 的 iframe 直接跳过（埋点、占位）。

## 输出结构

```text
<outputDir>/
  run-manifest.json
  baseline/<viewport>/<state>/{shot.png,dom.json,styles.json,runtime.json,meta.json}
  baseline/<viewport>/<state>/{failure.png,failure.json}   # 仅作废状态：为什么没采到
  baseline/capture-log.json
  candidate/...
  diff/<viewport>__<state>.png
  parity-report.md
  parity-summary.json
```

`run-manifest.json` 记录配置绝对路径、指纹和两侧采集环境，防止目录撞车或中途改配置。
`meta.json` 额外记录比较面、实际生效的探针 id、iframe 读取结果与采集告警。
`parity-summary.json` 的 `invalidEvidence` 是作废证据条数，非 0 时结论不能推广到那些页面。

`parity-summary.json` 是给下游消费的紧凑视图（结论、计数、findings、图片路径）。
向用户或其他技能交接时给路径，不要把内容整体贴出来。

## 命令行参数

| 参数 | 适用 | 说明 |
|---|---|---|
| `--config <file>` | 全部 | 必填 |
| `--side <baseline\|candidate>` | capture | 必填 |
| `--out <dir>` | capture / compare | 覆盖 `outputDir`；仍会由 manifest 阻止混用不同契约 |
| `--only <id,id>` | capture | 只跑指定 route/journey，调试用 |
| `--headed` | capture | 有头模式，观察脚本卡在哪一步 |
| `--keepGoing` | capture | 有状态采集失败也返回 0 |
| `--force-interactive` | prepare-auth | 未就绪必须开窗；**仍先探测**已有会话，通过则不开窗 |
| `--skip-probe` | prepare-auth | 跳过无头探测。仅自检/调试；正式跑禁用 |
| `--confirm` | prepare-auth | 用户回复「已登录」后调用；先验证活跃等待租约，再让开着的窗口立刻校验；无窗口时拒绝 |
| `--channel <chrome\|msedge>` | capture / compare | 覆盖配置里的 `channel`，用本机浏览器 |
| `--executablePath <path>` | capture / compare | 覆盖配置里的 `executablePath` |

退出码：capture `0` 成功 / `1` 有采集错误 / `2` 参数或配置错 / `3` 找不到 Playwright；
compare `0` 通过或仅有警告 / `1` 存在阻断项 / `2` 缺少采集结果。

## 自检

```bash
node scripts/selftest/run.mjs      # 单测 + 端到端
node scripts/selftest/unit.mjs     # 只跑判定规则单测（无浏览器，1 秒内）
```

`unit.mjs` 断言判定规则本身：登录页识别（含 `allowUrl` 不能绕过 `requireUrl`）、
`pathOverrides` 归一化、比较面合并、CSS 探针校验、L4 聚合、iframe 来源与 `unreadable` 标记。

端到端在 9401/9402 起两个故意有差异的本地站点（少一个筛选项、少一个导出按钮、
表格列改名、主题色/圆角/字号漂移、详情按钮抛异常、SSO 跳转页、iframe 顶栏少一个链接、
旧版残留 `ng-hide` 隐藏项、声明过的路径迁移、iframe 内按钮与 popup 预览），跑完整流水线并同时断言两件事：
**该报的都报了**，且**不该报的一条都没报**（隐藏节点计数、已声明的路径迁移）。
全 PASS 说明采集、判定、像素 diff、报告生成都正常；用于排除"是环境问题还是被测页面问题"。

## 排查

| 症状 | 处理 |
|---|---|
| 状态 `error`，超时在 `waitFor` | 选择器在新版已改名；看 `failure.png` 确认落地页，再用 `--headed` 观察后修正 |
| 报告顶部提示"证据作废：落地 URL 命中禁止模式" | 站点静默跳了 SSO。补 `auth.storageState`（可用 `export-storage-state.mjs` 从已登录浏览器导出）；被测页本身是登录页则配 `assertLanded.allowUrl` |
| 用户说"我已经登录了"但脚本还是跳登录页 | 先无头跑 `prepare-auth.mjs` 验证已有 `storageState`；探测失败再开 Skill 专用窗口。不要加 `--skip-probe`。只有明确要复用原窗口时才带 `--remote-debugging-port=9222` 导出 |
| 刚登录成功，采集却跳到 `login-beta` / SSO | 就绪选择器太早（登录前就有的壳）。改成登录后才出现的节点，重跑 `prepare-auth`（不加 `--force-interactive`） |
| 同一网址登录了两次 | `--force-interactive` 已不再跳过探测。重跑不要加 `--skip-probe`；已有会话应静默复用 |
| 已经在窗口里登录了，脚本却几分钟没动 | 脚本在等 `waitFor` / 冷启动，不是在等你输入密码。回复「已登录」触发 `--confirm`；心跳会打印当前 URL 和未就绪原因 |
| 提示登录但没有窗口 | 只有 `LOGIN_WINDOW_READY visible:true` 才算开窗成功；若没有该握手，查看其后的浏览器启动错误。窗口未置顶时从任务栏或 Alt+Tab 查找 |
| 页面一直轮询，采集导航超时 | 不要把 `networkidle` 当业务就绪条件；保持默认 `domcontentloaded`，用登录后/数据加载后的 `waitFor`，必要时调 `networkIdleTimeoutMs` |
| 托管页顶栏/菜单链接被报"缺失"，截图里明明有 | 内容在 iframe 里。现已自动合并可读 iframe；若报告标了 `iframe 不可读`，说明该 frame 禁脚本或已 detach，按"读不到"处理，不要当缺陷 |
| 计数类差异"6 对 5"但页面上看着一样 | 旧版把隐藏项留在 DOM（`ng-hide`/`v-show`），新版 `v-if` 不渲染。`expectCount` 默认已只数可见节点；看 `observedTotal` 确认 |
| `expectUrl` 被判阻断，但地址本来就该不同 | 路径迁移没声明。写进 `<side>.pathOverrides` / `urlTokens`，或给该步加 `ignorePath: true` |
| 像素差异恒定在 1–3%，热点分散全页 | 字体未就绪或整体位移；检查字体加载与滚动条，或加 `settleMs` |
| 大量 L4 差异集中在 `font-size` | 根字号或 `html{font-size}` 变了，属于全局回归；报告会收敛成一条"全局样式漂移" |
| L4 全是壳层噪声（`body`/`button`/`link`） | 用 `defaultProbes: false` 或给数组只留业务探针，再用 `styleProbes` 指到真正关心的组件 |
| 每次跑差异比例都不同 | 存在未遮罩的动态内容；补 `masks` / `freezeTime` / `seedRandom` |
| 探针 `found: false` 但页面上有该元素 | 元素可能在 iframe/Shadow DOM，或选择器指错业务根；为 route 配 `compareSurface.frame/root`，Shadow DOM 则改用 journey 验证 |
| 报告提示“采集契约不一致” | 两侧配置、浏览器或 context 有变化，或复用了其他页面的目录；更换 outputDir 并重新采集两侧 |
| iframe 内按钮主文档点不到 | 给 route/journey 配 `compareSurface.frame`，或只给该动作配 `scope.frame`；不要把选择器失败直接解释成功能回归 |
| 点击后打开新窗口但报告没验预览 | 使用 `clickAndExpectPopup` 保存 `popupId`，后续步骤用 `scope.page` 断言 popup 内容 |
| CDP 端口通但导出仍超时 | `/json/version` 已通过说明不是端口问题；减少标签页/扩展后重试。Cookie-only 兜底不含完整 localStorage，报告必须注明 |
