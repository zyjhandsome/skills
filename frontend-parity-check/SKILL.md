---
name: frontend-parity-check
description: >
  Use when the user supplies two live URLs (pre-upgrade baseline and
  post-upgrade candidate) and asks whether 功能和样式一致 / 回归 /
  对比新旧页面 / 重构验收 / 迁移验收, or wants visual + functional
  regression after a refactor, framework migration, UI-kit swap, or
  design-system upgrade. Not for in-repo CSS root-cause diagnosis
  without two runnable URLs (use frontend-ui-stack-visual-parity),
  and not for accessibility, real-device, Canvas/WebGL content, or
  drag-and-drop upload checks.
---

# Frontend Parity Check

黑盒比对**两个可访问的 URL**（升级前 baseline / 升级后 candidate），回答一个问题：
**新页面在功能和样式上是否与旧页面一致，不一致在哪里、有多严重。**

本技能只**读取**两个 URL 并写入自己的输出目录，**不修改**任何业务代码。

## 何时用 / 何时不用

| 场景 | 去向 |
|---|---|
| 有两个能打开的 URL，要给出「是否一致」的验收结论 | **本技能** |
| 只有仓库代码，要定位 Tailwind Preflight / Element 主题冲突等样式根因 | `frontend-ui-stack-visual-parity` |
| 还没开始迁移，要评估升级影响面 | `vue2-to-vue3-upgrade-impact-analysis` 等分析类技能 |
| 跟设计稿对、没有 baseline URL | 设计走查，不是 parity |
| 无障碍 / 键盘 / 读屏 | 本技能不验 a11y |
| 真机、系统手势 | 只用 Playwright 视口，不是真机验收 |
| Canvas / WebGL 绘制内容 | 写进 `masks`，不验画布里的内容 |
| 拖拽、文件选择器上传 | 动作词表没有这些，不要假装验过 |

## 前置门槛：Playwright

第一步先探测环境，**不要在未获授权时执行任何安装命令**：

```bash
node scripts/preflight.mjs
```

- 退出码 `0`：环境就绪。把 `useConfig` 照抄进配置文件。
- 退出码 `3`：停下来，用 `AskQuestion` 让用户选：项目内安装 / 全局安装 / 只装浏览器内核 /
  **改用本机 Chrome·Edge**（`install.useSystemBrowser`）/ 用户自己装。
  拿到明确授权后才执行；被拒绝就停，不要用截图以外的手段假装完成。

企业环境常见「装得上 npm 包、下不来浏览器内核」。preflight 已尝试本机 `chrome` /
`msedge`，可用时配置 `"channel": "chrome"`（或 `"executablePath"`）。
细节见 `references/playwright-setup.md`。

接触真实站点前可跑内置自检（判定规则 + 两个故意有差异的本地页，约 60 秒）：

```bash
node scripts/selftest/run.mjs     # 含 unit.mjs；也可单独跑 node scripts/selftest/unit.mjs
```

## 工作流

### 第 1 步：锁定输入契约（不要跳过）

必须问清、并写进配置文件的五件事：

1. **两个 URL**：baseline 与 candidate；路由不同则给出路径映射。
2. **登录方式**：`AskQuestion` 的选项 label **必须逐字**如下（第一项放首位并标推荐）：

   1. 我来登录，完成后回复「已登录」（推荐）
   2. 免登录直接可访问
   3. 从我的浏览器导出会话
   4. 提供测试账号

   用户没特别偏好时采用第 1 项（`auto-interactive`）。不要改写成「自动探测加我手动登录」，
   也不要砍成 3 项。交互组件自带的 `Other/其他` 保留。

   配方（状态机见 `references/ask-template.md`）：
   - 每侧先 `prepare-auth`，不加 `--skip-probe`；不要因为用户说「我来登录」就加
     `--force-interactive`。
   - 只有脚本输出 `LOGIN_WINDOW_READY` 且 `visible:true`，才能说窗口已创建；然后立刻结束本轮，
     等用户回复「已登录」。禁止说「不用回复」，禁止本轮死等 `timeoutMs`。
   - 用户回复后立刻
     `node scripts/prepare-auth.mjs --config <file> --side <side> --confirm`。
     未就绪把脚本打印的原因原样告诉用户。
3. **数据前提** `dataParity`：
   - `same-data`：行数、文案、链接差异都算真实缺陷。
   - `different-data`（默认）：数据类差异降级为参考项，**此时不能宣称「内容一致」**。
4. **样式口径** `styleIntent`：
   - `pixel-parity`（默认）：字体/颜色/字号变化按重要项处理。
   - `redesign-allowed`：允许改版，计算样式仅作参考，只卡功能与结构。
5. **比较面** `compareSurface`：验收整页还是只验业务页体。
   - 两侧都直接打开业务页时可省略，默认比较整个主文档。
   - 一侧是宿主壳内 iframe、另一侧是独立页时，必须分别声明 `frame` / `root`，并用
     `mainUrlPattern`、`frameUrlPattern` 锁定落地位置；不要拿壳 DOM 与页体 DOM 硬比。
   - 已确认不在验收范围的宿主 Header、侧栏写进 `exclude`，统一作用于 L2–L5。

用户没主动给的，用 `AskQuestion` 一次性问齐，不要边跑边猜。
填表见 `references/ask-template.md`。

### 第 2 步：写配置文件

按被测页面形态复制模板到工作目录：

| 模板 | 适用 |
|---|---|
| `templates/parity-config.json` | 列表 + 查询 + 详情的表单/表格类页面 |
| `templates/parity-config-hosted-iframe.json` | 托管页 / 门户壳：iframe 顶栏或菜单、看板、图表 |

然后填 `routes`（页面 + **状态**）和 `journeys`（**用户流程**）。

覆盖面最低要求：

- 每个页面至少 `default` 一个状态；含搜索/表格的页面补 `search-filled`、`table-empty`。
- 至少一条 `journey` 走完「查询 → 打开详情/提交表单」——**只截图不点，等于没验功能。**
- **journey 只在第一个视口跑一次**；其余视口只做状态快照。结论里必须写明这条边界。
- 会漂移的元素（时间戳、进度条、轮播、验证码、canvas 图表）写进 `masks`。
- **两侧路由不同就必须声明** `pathOverrides`。没声明的路径差异会被判为跳转缺陷。
- `waitFor` / `interactive.readySelector` 必须是**登录后才出现**的节点。禁止用 `#app` /
  `#root`、Header、面包屑、登录前就有的标题，或「必须有数据行」。
- `outputDir` 必须带页面或模块名（如 `./parity-runs/task-report`）。目录属于另一份契约时会拒绝覆盖。
- `styleProbes` 只能用浏览器原生 CSS；页面动作用 Playwright selector。
  新旧类名不同可分别写 `baselineSelector` / `candidateSelector`。

字段与动作词表见 `references/config-reference.md`。

### 第 3 步：双侧采集

`auth.mode=auto-interactive` 时按 **baseline → candidate** 逐侧准备登录态：

```bash
node scripts/prepare-auth.mjs --config parity-config.json --side baseline   # 后台运行
node scripts/prepare-auth.mjs --config parity-config.json --side candidate  # 上一侧 ready 后再开
```

等待两类真实结果（开窗话术与 `--confirm` 见第 1 步配方；完整状态机见 `references/ask-template.md`）：

- JSON `status=ready`：本侧完成，继续下一侧；
- `LOGIN_WINDOW_READY` 且 `visible:true`：窗口已创建，结束本轮等「已登录」。

**禁止**用 WebSearch、浏览器工具或手动点页面来「搞清楚怎么登录」。

```bash
node scripts/capture.mjs --config parity-config.json --side baseline
node scripts/capture.mjs --config parity-config.json --side candidate
```

每个状态落盘：`shot.png`、`dom.json`、`styles.json`、`runtime.json`、`meta.json`。
两侧共用同一份视口、locale、时区、冻结时间与随机种子。

采集有四道硬闸，任一触发即该状态（或整侧）**作废**并落 `failure.png`：

1. 落地 URL 命中登录/SSO 特征；
2. 声明的 `compareSurface` frame/root/URL pattern 没命中；
3. `waitFor` 选择器在导航后没命中；
4. `auth.actions` 任一步失败，或 `auto-interactive` 尚未生成已验证会话。

作废状态不参与比对。**看到「证据作废」先修登录态或路径映射再重跑，不要拿半截证据出结论。**
被测页本身就是登录页时，用 `assertLanded.allowUrl` 显式放行。

只有用户明确选择「从我的浏览器导出会话」时，才走
`scripts/export-storage-state.mjs`（该脚本不得 `browser.close()`）。命令见
`references/playwright-setup.md`。

### 第 4 步：比对与出报告

```bash
node scripts/compare.mjs --config parity-config.json
```

产出 `parity-report.md`、`parity-summary.json`、`diff/*.png`。
退出码 `1` 表示存在阻断项。

### 第 5 步：解读并给结论

按 `references/parity-ladder.md` 判定。向用户回报时必须包含：

- 一句话结论（通过 / 有重要差异 / 不一致）；
- `evidenceStatus`（证据有效/部分/无效）与 `parityVerdict`（仅针对有效证据）分开回报；
- 阻断项逐条列出，并区分「**回归缺陷**」与「**有意变更**」——后者需用户确认；
- 报告与差异图的**绝对路径**（不要把截图或整份报告塞进对话）；
- 适用边界：覆盖了哪些页面/状态/视口，`dataParity` 与 `styleIntent`，以及 journey 是否只跑了第一视口。

## 判定分层（详见 references/parity-ladder.md）

| 层 | 看什么 | 典型失败含义 |
|---|---|---|
| L0 | HTTP 状态、JS 报错、失败请求 | 新版根本没跑起来 |
| L1 | 用户流程每一步的成败与观测值 | 功能坏了 |
| L2 | 标题/按钮/表单字段/表格列/文案/链接 | 功能「看起来在」但少了入口或字段 |
| L3 | 关键元素尺寸与位置 | 布局塌了、控件被挤压 |
| L4 | 计算样式（字体、颜色、间距、圆角、阴影） | 主题/设计令牌漂移 |
| L5 | 截图像素差异 + 热点区域 | 综合外观偏差 |

**L5 单独通过不能证明一致**：外观像而 L1/L2 失败，说明功能已经不同；
反之 L0–L2 全绿而 L5 超阈值，通常是纯样式漂移，交给样式修复流程。

## 红线

| 红线 | 去哪查 |
|---|---|
| 未授权就 `npm install` / `npx playwright install` | `references/playwright-setup.md` |
| 两侧视口/缩放/时区/登录态不同，仍给 parity 结论 | 第 3 步 |
| 配置指纹不同，或混用其他页面的输出目录，仍继续比对 | `references/config-reference.md` |
| 拿作废证据出结论，或为了变绿放宽 `assertLanded` | `references/parity-ladder.md` |
| `different-data` 把数据项当缺陷；或把固定功能入口标成数据 | `references/parity-ladder.md` |
| 只跑截图、不跑 journey，就宣称「功能一致」 | 第 2 步；压测见 `references/agent-pressure.md` |
| 把截图或整份报告贴进对话；修改被测站点源码 | 第 5 步 |
| 登录握手违规（改 label、未握手称开窗、说不用回复、已有会话再弹窗、壳节点当 ready） | `references/ask-template.md` |

## 参考文件

- `references/ask-template.md`：提问模板 + 登录状态机
- `references/parity-ladder.md`：六层判定标准与验收口径
- `references/config-reference.md`：配置字段、动作词表、常见故障排查
- `references/playwright-setup.md`：安装授权、企业浏览器兜底、登录态导出
- `references/agent-pressure.md`：三条纪律压测卡（只截图结案 / 未授权安装 / 作废仍给 verdict）
- `templates/parity-config.json`：列表/表单页配置样例
- `templates/parity-config-hosted-iframe.json`：托管页 + iframe 配置样例
- `scripts/prepare-auth.mjs`：先探测已有会话；未就绪才开窗；`--confirm` 立刻校验
- `scripts/export-storage-state.mjs`：仅在用户明确要求复用已打开的浏览器时使用
