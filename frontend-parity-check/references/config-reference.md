# 配置与动作词表

完整可复制样例见 `templates/parity-config.json`。

## 顶层字段

| 字段 | 默认 | 说明 |
|---|---|---|
| `outputDir` | `./parity-run` | 证据与报告的落盘目录，相对配置文件解析 |
| `browser` | `chromium` | `chromium` / `firefox` / `webkit`，需对应内核已安装 |
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
| `pathOverrides` | `{ routeId: "/新路径" }`，处理两侧路由不一致 |
| `userAgent` / `extraHTTPHeaders` | 需要指定 UA 或注入网关头时使用 |
| `auth.storageState` | Cookie/localStorage 文件路径；存在则直接复用 |
| `auth.actions` | 文件不存在时执行的登录动作序列，成功后自动写入该文件 |

也可以在 `routes[].baselinePath` / `routes[].candidatePath` 上做单页路径覆盖。

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
  "waitFor": { "selector": ".el-table__row", "state": "visible" },
  "waitUntil": "networkidle",         // goto 的等待策略
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
中断位置本身就是重要证据。

## 动作词表

| type | 参数 | 作用 |
|---|---|---|
| `goto` | `path`, `waitUntil` | 导航到相对路径 |
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
| `expectCount` | `selector` | 记录匹配数量 |
| `expectUrl` | — | 记录当前 URL（去 origin 后比对） |
| `capture` | `id` | 在流程中间打一次完整快照 |

`expect*` **不做断言**，只记录观测值；判定由 `compare.mjs` 在两侧之间进行。
这是有意设计：不需要预先知道正确答案，旧版的行为就是答案。

所有 `selector` 走 Playwright 定位语法，支持 CSS、`text=`、`role=` 等。
给动作加 `id` 能让报告里的条目可读。

## 输出结构

```text
<outputDir>/
  baseline/<viewport>/<state>/{shot.png,dom.json,styles.json,runtime.json,meta.json}
  baseline/capture-log.json
  candidate/...
  diff/<viewport>__<state>.png
  parity-report.md
  parity-summary.json
```

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

退出码：capture `0` 成功 / `1` 有采集错误 / `2` 参数或配置错 / `3` 找不到 Playwright；
compare `0` 通过或仅有警告 / `1` 存在阻断项 / `2` 缺少采集结果。

## 自检

```bash
node scripts/selftest/run.mjs
```

在 9401/9402 起两个故意有差异的本地页面（少一个筛选项、少一个导出按钮、表格列改名、
主题色/圆角/字号漂移、详情按钮抛异常），跑完整流水线并断言这些差异都被检出。
8 项全 PASS 说明采集、比对、像素 diff、报告生成都正常；用于排除"是环境问题还是被测页面问题"。

## 排查

| 症状 | 处理 |
|---|---|
| 状态 `error`，超时在 `waitFor` | 选择器在新版已改名；用 `--headed` 观察后修正 |
| 像素差异恒定在 1–3%，热点分散全页 | 字体未就绪或整体位移；检查字体加载与滚动条，或加 `settleMs` |
| 大量 L4 差异集中在 `font-size` | 根字号或 `html{font-size}` 变了，属于全局回归 |
| 每次跑差异比例都不同 | 存在未遮罩的动态内容；补 `masks` / `freezeTime` / `seedRandom` |
| 探针 `found: false` 但页面上有该元素 | 元素在 iframe 或 Shadow DOM 内；换用具体选择器或改用 journey 验证 |
| 候选侧只截到登录页 | `storageState` 过期，删掉文件让 `auth.actions` 重新登录 |
