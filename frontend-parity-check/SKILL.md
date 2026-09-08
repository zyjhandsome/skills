---
name: frontend-parity-check
description: >
  Verify that a rebuilt, migrated, or upgraded frontend page behaves and looks
  the same as before, by driving two live URLs (before/after) with Playwright
  and diffing them across six layers: reachability, user journeys, semantic DOM,
  layout geometry, computed style, and pixels. Use when the user supplies a
  pre-upgrade URL and a post-upgrade URL and asks whether 功能和样式一致 /
  回归 / 对比新旧页面 / 重构验收 / 迁移验收 / visual + functional regression
  after a refactor, framework migration, UI-kit swap, or design-system upgrade.
  Detects Playwright and requests explicit authorization before installing
  anything. Produces parity-report.md, parity-summary.json, and diff images.
  Not for in-repo CSS root-cause diagnosis without two runnable URLs — that is
  frontend-ui-stack-visual-parity.
---

# Frontend Parity Check

黑盒比对**两个可访问的 URL**（升级前 baseline / 升级后 candidate），回答一个问题：
**新页面在功能和样式上是否与旧页面一致，不一致在哪里、有多严重。**

## 与相邻技能的边界

| 场景 | 用这个 |
|---|---|
| 有两个能打开的 URL，要给出"是否一致"的验收结论 | **本技能** |
| 只有仓库代码，要定位 Tailwind Preflight / Element 主题冲突等样式根因 | `frontend-ui-stack-visual-parity` |
| 还没开始迁移，要评估升级影响面 | `vue2-to-vue3-upgrade-impact-analysis` 等分析类技能 |

本技能只**读取**两个 URL 并写入自己的输出目录，**不修改**任何业务代码。
定位到差异后，把结论交给上述技能或开发者去改。

## 前置门槛：Playwright

第一步必须先探测环境，**不要在未获授权时执行任何安装命令**：

```bash
node scripts/preflight.mjs
```

- 退出码 `0`：环境就绪。`useConfig` 字段给出该机器可用的启动配置，照抄进配置文件。
- 退出码 `3`：输出 JSON 的 `install` 字段列出候选命令。此时**停下来**，用
  `AskQuestion` 让用户选择：项目内安装 / 全局安装 / 只装浏览器内核 /
  **改用本机 Chrome·Edge**（`install.useSystemBrowser`）/ 用户自己装。
  拿到明确授权后才执行；被拒绝就停在这里，不要用截图以外的手段假装完成。

企业环境常见的是**装得上 npm 包、下不来浏览器内核**（自签证书拦截、代理 DNS 失败）。
preflight 已自动尝试本机 `chrome` / `msedge`，可用时直接在配置里写
`"channel": "chrome"`（或 `"executablePath"`），不必再折腾内核下载。
细节（企业证书与代理、离线镜像、Linux 系统依赖、CI）见 `references/playwright-setup.md`。

想在接触真实站点前确认工具链可用，跑一次内置自检（判定规则单测 + 两个故意有差异的
本地页面走完整流水线，约 60 秒，全部 PASS 即环境正常）：

```bash
node scripts/selftest/run.mjs     # 含 unit.mjs；也可单独跑 node scripts/selftest/unit.mjs
```

## 工作流

### 第 1 步：锁定输入契约（不要跳过）

必须问清、并写进配置文件的五件事：

1. **两个 URL**：baseline（升级前）与 candidate（升级后）的可访问地址；若路由不同，
   给出每个页面的路径映射。
2. **登录方式**：问的时候 `AskQuestion` 的选项 label **必须逐字**如下（第一项放首位并标推荐）：

   1. 我来登录，完成后回复「已登录」（推荐）
   2. 免登录直接可访问
   3. 从我的浏览器导出会话
   4. 提供测试账号

   用户没特别偏好时采用第 1 项（`auto-interactive`）。不要改写成「自动探测加我手动登录」，
   也不要砍成 3 项。交互组件自带的 `Other/其他` 保留。
   - **每址最多弹一次登录窗。** 固定顺序：已有 `storageState` → 无头验证 → 通过则静默结束 →
     失败才开窗。用户说“我来登录”只保证第三步会开窗，**不跳过复用**。
   - 只有脚本输出 `LOGIN_WINDOW_READY`（且 `visible:true`）后，才可以说窗口已经创建。
     “准备创建”不是成功；若进程先退出，直接回报启动错误，禁止让用户寻找不存在的窗口。
   - 确认开窗后**立刻结束本轮**，告诉用户准确的 side 和目标地址：在该窗口登录，完成后回复
     「已登录」，不要发密码。若窗口未置顶，提示从任务栏或 Alt+Tab 查找，不要称“最新窗口”。
     **禁止**说「不用回复」。**禁止**在同一轮对话里死等 `timeoutMs`（默认 10 分钟）。
   - 用户回复「已登录」后立刻执行
     `node scripts/prepare-auth.mjs --config <file> --side <side> --confirm`，
     让后台窗口马上校验并保存；未就绪要把脚本打印的原因原样告诉用户。
   - 不要加 `--skip-probe`（自检/调试专用）。不要因为用户说了“我来登录”就加
     `--force-interactive` 去跳过探测——该开关现在只表示「未就绪必须开窗」。
   - 采集因 SSO 作废后重跑：先 `prepare-auth`（不加 force / skip-probe）。探测失败再开窗。
   - 专用浏览器使用 Skill 独立 profile，不复用用户日常 Chrome/Edge profile。
   - "我已经在浏览器里登录了"**不等于**脚本已登录；若用户坚持复用现有窗口，才使用
     `scripts/export-storage-state.mjs` 的 CDP 方案。
   - 说"免登录"也要验证：内网站点经常静默跳 SSO。短探测通不过就开窗，不要自己点站排查。
3. **数据前提** `dataParity`：两侧是否连**同一套数据**。
   - `same-data`：行数、文案、链接差异都算真实缺陷。
   - `different-data`（默认）：数据类差异降级为参考项，**此时不能宣称"内容一致"**。
4. **样式口径** `styleIntent`：
   - `pixel-parity`（默认）：要求视觉对齐，字体/颜色/字号变化按重要项处理。
   - `redesign-allowed`：本次允许改版，计算样式差异仅作参考，只卡功能与结构。
5. **比较面** `compareSurface`：验收整页（宿主 + 页体），还是只验业务页体。
   - 两侧都直接打开业务页时可以省略，默认比较整个主文档。
   - 一侧是宿主壳内 iframe、另一侧是独立页时，必须分别声明 `frame` / `root`，并用
     `mainUrlPattern`、`frameUrlPattern` 锁定实际落地位置；不要拿壳 DOM 与页体 DOM 硬比。
   - 宿主 Header、侧栏等已确认不在验收范围内的区域写进 `exclude`，统一作用于 L2–L5。

用户没主动给的，用 `AskQuestion` 一次性问齐，不要边跑边猜。
登录题的 4 个 label 以本节第 2 条为准，不要自行改写。
其余填表见 `references/ask-template.md`（也可直接发给用户，让其照填）。

### 第 2 步：写配置文件

按被测页面的形态挑一份模板复制到工作目录：

| 模板 | 适用 |
|---|---|
| `templates/parity-config.json` | 列表 + 查询 + 详情的表单/表格类页面 |
| `templates/parity-config-hosted-iframe.json` | 托管页 / 门户壳：iframe 顶栏或菜单、看板、图表 |

然后填 `routes`（要比的页面 + 每个页面要覆盖的**状态**）和 `journeys`（要验证的**用户流程**）。

覆盖面的最低要求：

- 每个页面至少 `default` 一个状态；含搜索/表格的页面补 `search-filled`、`table-empty`。
- 至少一条 `journey` 走完"查询 → 打开详情/提交表单"的主链路——
  **只截图不点，等于没验功能。**
- 明显会漂移的元素（时间戳、进度条、轮播、验证码、canvas 图表）写进 `masks`。
- **两侧路由不同就必须声明** `pathOverrides`（route 和 journey 都认这份映射）。
  没声明的路径差异会被判为跳转缺陷——这是有意的。
- `waitFor` / `interactive.readySelector` 必须是**登录后才出现**的节点（例如权限接口成功后的
  `.tab-list`、业务表）。禁止用整页壳、`#app` / `#root`、Header、面包屑、登录前就有的标题。
  登录前会先画出的壳节点当成功，会把空会话存成 `ready`，采集立刻被打回 SSO。
  也不要用“必须有数据行”的选择器当登录成功。命中不了整个状态作废。
- `outputDir` 必须带页面或模块名，例如 `./parity-runs/task-report`。每次采集会写
  `run-manifest.json` 与配置指纹；目录属于另一份契约时会拒绝覆盖。
- `styleProbes` 只能使用浏览器原生 CSS；页面动作使用 Playwright selector。
  新旧 DOM 类名不同可分别写 `baselineSelector` / `candidateSelector`。

字段与动作词表见 `references/config-reference.md`。

### 第 3 步：双侧采集

`auth.mode=auto-interactive` 时，写完配置后按 **baseline → candidate** 逐侧准备登录态，
不要先自己打开目标站探究，也不要同时弹两个窗口：

```bash
node scripts/prepare-auth.mjs --config parity-config.json --side baseline   # 后台运行
# baseline ready 后再启动 candidate；需要登录时先完成本侧再继续
node scripts/prepare-auth.mjs --config parity-config.json --side candidate  # 后台运行
```

已有会话仍有效、或页面免登录时，命令会在几秒内无头结束，不再开窗。
未就绪才会尝试打开专用窗口。`prepare-auth` 必须保持在后台运行，并等待下面两类真实结果：

- 输出 JSON `status=ready`：本侧完成，继续下一侧；
- 输出 `LOGIN_WINDOW_READY` 且 `visible:true`：窗口确实创建成功，此时才告诉用户：

**已创建 `<side>` 登录窗口，目标为 `<targetUrl>`。请在该窗口登录；完成后回复「已登录」。
不要把密码发给我。若窗口未置顶，请从任务栏或 Alt+Tab 打开。**

如果只看到“准备创建”后进程退出，或没有 `LOGIN_WINDOW_READY`，应把脚本错误原样告诉用户，
不得声称窗口已打开。重复执行同一 side 时，脚本会复用仍在等待的窗口并拒绝再开一个。

页面自己回到目标页并命中 `waitFor` 时仍会自动保存。用户回复后只对当前正在等待的 side 执行：

```bash
node scripts/prepare-auth.mjs --config parity-config.json --side <side> --confirm
```

`--confirm` 只接受仍有活跃登录进程的 side；孤立或过期确认会被拒绝，不会污染下一轮。
脚本收到确认会马上校验并保存；未就绪、仍停在 SSO、或冷启动失败时立刻退出并打印原因，不再干等。
超时、窗口被关闭、或确认后仍未就绪时不得继续采集。

**禁止**用 WebSearch、浏览器工具或手动点页面来“搞清楚怎么登录”。那是用户的事，不是探测循环。

```bash
node scripts/capture.mjs --config parity-config.json --side baseline
node scripts/capture.mjs --config parity-config.json --side candidate
```

每个状态落盘：`shot.png`、`dom.json`（语义摘要，含可读 iframe 的内容）、
`styles.json`（探针计算样式）、`runtime.json`（控制台/失败请求）、`meta.json`。
两侧共用同一份视口、locale、时区、冻结时间与随机种子，保证可比。

采集有四道硬闸，任一触发即该状态（或整侧）**作废**并落一张 `failure.png` 供排查：

1. 落地 URL 命中登录/SSO 特征（`/login`、`login-beta.`、`redirect_uri=` 等）；
2. 声明的 `compareSurface` frame/root/URL pattern 没命中；
3. `waitFor` 选择器在导航后没命中；
4. `auth.actions` 登录序列有任何一步失败，或 `auto-interactive` 尚未生成已验证的会话。

作废的状态不参与比对，报告顶部会列出来。**看到"证据作废"先修登录态或路径映射再重跑，
不要拿半截证据出结论。** 被测页本身就是登录页时，用 `assertLanded.allowUrl` 显式放行。

只有用户明确选择复用现有浏览器时，才从那个浏览器导出会话：

```bash
# 先让用户带调试端口重启浏览器并完成登录：chrome.exe --remote-debugging-port=9222
# 脚本会先探测 /json/version，再限时连接，避免把 target 枚举超时误报成“端口没开”
node scripts/export-storage-state.mjs --timeout 15000 --out auth/candidate.json --url https://new.example.com/home
```

导出的文件填进 `<side>.auth.storageState`。该脚本连的是用户自己的浏览器，
**不会**也不允许 `browser.close()`。

### 第 4 步：比对与出报告

```bash
node scripts/compare.mjs --config parity-config.json
```

产出 `parity-report.md`、`parity-summary.json`、`diff/*.png`。
退出码 `1` 表示存在阻断项。

### 第 5 步：解读并给结论

按 `references/parity-ladder.md` 的判定口径逐条处理，向用户回报时必须包含：

- 一句话结论（通过 / 有重要差异 / 不一致）；
- `evidenceStatus`（证据有效/部分/无效）与 `parityVerdict`（仅针对有效证据）必须分开回报；
- 阻断项逐条列出，并区分"**回归缺陷**"与"**有意变更**"——
  后者需要用户确认，不能由本技能自行认定；
- 报告与差异图的**绝对路径**（不要把截图或整份报告塞进对话）；
- 本次结论的适用边界：覆盖了哪些页面/状态/视口，`dataParity` 与 `styleIntent` 取值。

## 判定分层（详见 references/parity-ladder.md）

| 层 | 看什么 | 典型失败含义 |
|---|---|---|
| L0 | HTTP 状态、JS 报错、失败请求 | 新版根本没跑起来 |
| L1 | 用户流程每一步的成败与观测值 | 功能坏了 |
| L2 | 标题/按钮/表单字段/表格列/文案/链接 | 功能"看起来在"但少了入口或字段 |
| L3 | 关键元素尺寸与位置 | 布局塌了、控件被挤压 |
| L4 | 计算样式（字体、颜色、间距、圆角、阴影） | 主题/设计令牌漂移 |
| L5 | 截图像素差异 + 热点区域 | 综合外观偏差 |

**L5 单独通过不能证明一致**：外观像而 L1/L2 失败，说明功能已经不同；
反之 L0–L2 全绿而 L5 超阈值，通常是纯样式漂移，交给样式修复流程。

## 红线

- 未获授权就执行 `npm install` / `npx playwright install`。
- 两侧采集环境不同（视口、缩放、时区、登录态不一致）却给出 parity 结论。
- baseline、candidate、compare 使用的配置指纹不同，或混用了其他页面的输出目录，仍继续比对。
- 拿**作废的证据**（登录页、落地页错误、`waitFor` 未命中）出任何一致性结论，
  或为了让报告变绿而放宽 `assertLanded`。
- `dataParity=different-data` 时把已标记为数据依赖的行数或文案差异当作缺陷上报。
- 把固定功能入口误标为数据项；只有 `dataDependent: true` 或 `dataSelectors` 内的内容才可按数据降级。
- 只跑截图、不跑 journey，就宣称"功能一致"。
- 把 base64 截图或整份报告贴进对话，而不是给路径。
- 修改被测站点的任何源码——本技能只做取证与判定。
- 目标页未就绪时自己探究 SSO / 改 waitFor / 反复无头重试，而不是打开登录窗口让用户登录。
- 已有 `storageState` 时为了「用户说过要登录」再弹一次窗。重跑先探测；只有探测失败再开窗。
- 开登录窗后说「不用回复」或在同一轮死等 10 分钟。必须等用户回复「已登录」再 `--confirm`。
- 未看到 `LOGIN_WINDOW_READY visible:true` 就声称窗口已经打开，或同时打开 baseline/candidate 让用户猜窗口。
- 把登录题改写成「自动探测加我手动登录」或只给 3 项。AskQuestion label 必须逐字用第 1 步那 4 条。
- 用登录前就存在的壳节点当登录成功，或把未通过冷启动校验的会话当成 `ready`。

## 参考文件

- `references/ask-template.md`：给用户的提问/填表模板
- `references/parity-ladder.md`：六层判定标准与验收口径
- `references/config-reference.md`：配置字段、动作词表、常见故障排查
- `references/playwright-setup.md`：安装授权、企业浏览器兜底、登录态导出、内网与 CI
- `templates/parity-config.json`：列表/表单页的完整配置样例
- `templates/parity-config-hosted-iframe.json`：托管页 + iframe 壳 + 看板的配置样例
- `scripts/export-storage-state.mjs`：从用户已登录的浏览器导出 `storageState`
- `scripts/prepare-auth.mjs`：先探测已有会话；未就绪才开窗并等用户回复「已登录」；`--confirm` 立刻校验，假就绪不落盘
