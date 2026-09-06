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

- 退出码 `0`：环境就绪，直接进入工作流。
- 退出码 `3`：输出 JSON 的 `install` 字段列出候选命令。此时**停下来**，用
  `AskQuestion` 让用户选择：项目内安装 / 全局安装 / 只装浏览器内核 / 用户自己装。
  拿到明确授权后才执行；被拒绝就停在这里，不要用截图以外的手段假装完成。

细节（离线内网、镜像源、Linux 系统依赖、CI）见 `references/playwright-setup.md`。

想在接触真实站点前确认工具链可用，跑一次内置自检（自带两个故意有差异的本地页面，
约 30 秒，全部 PASS 即环境正常）：

```bash
node scripts/selftest/run.mjs
```

## 工作流

### 第 1 步：锁定输入契约（不要跳过）

必须问清、并写进配置文件的四件事：

1. **两个 URL**：baseline（升级前）与 candidate（升级后）的可访问地址；若路由不同，
   给出每个页面的路径映射。
2. **登录方式**：免登录 / 提供测试账号 / 提供 Cookie 或 storageState 文件。
3. **数据前提** `dataParity`：两侧是否连**同一套数据**。
   - `same-data`：行数、文案、链接差异都算真实缺陷。
   - `different-data`（默认）：数据类差异降级为参考项，**此时不能宣称"内容一致"**。
4. **样式口径** `styleIntent`：
   - `pixel-parity`（默认）：要求视觉对齐，字体/颜色/字号变化按重要项处理。
   - `redesign-allowed`：本次允许改版，计算样式差异仅作参考，只卡功能与结构。

用户没主动给的，用 `AskQuestion` 一次性问齐，不要边跑边猜。
提问模板见 `references/ask-template.md`（也可直接发给用户，让其照填）。

### 第 2 步：写配置文件

复制 `templates/parity-config.json` 到工作目录，按实际情况填 `routes`（要比的页面 +
每个页面要覆盖的**状态**）和 `journeys`（要验证的**用户流程**）。

覆盖面的最低要求：

- 每个页面至少 `default` 一个状态；含搜索/表格的页面补 `search-filled`、`table-empty`。
- 至少一条 `journey` 走完"查询 → 打开详情/提交表单"的主链路——
  **只截图不点，等于没验功能。**
- 明显会漂移的元素（时间戳、进度条、轮播、验证码）写进 `masks`。

字段与动作词表见 `references/config-reference.md`。

### 第 3 步：双侧采集

```bash
node scripts/capture.mjs --config parity-config.json --side baseline
node scripts/capture.mjs --config parity-config.json --side candidate
```

每个状态落盘：`shot.png`、`dom.json`（语义摘要）、`styles.json`（探针计算样式）、
`runtime.json`（控制台/失败请求）、`meta.json`。两侧共用同一份视口、locale、时区、
冻结时间与随机种子，保证可比。

采集报错先修配置再重跑；**不要拿半截证据出结论**。

### 第 4 步：比对与出报告

```bash
node scripts/compare.mjs --config parity-config.json
```

产出 `parity-report.md`、`parity-summary.json`、`diff/*.png`。
退出码 `1` 表示存在阻断项。

### 第 5 步：解读并给结论

按 `references/parity-ladder.md` 的判定口径逐条处理，向用户回报时必须包含：

- 一句话结论（通过 / 有重要差异 / 不一致）；
- 阻断项逐条列出，并区分"**回归缺陷**"与"**有意变更**"——
  后者需要用户确认，不能由本技能自行认定；
- 报告与差异图的路径（不要把截图或整份报告塞进对话）；
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
- `dataParity=different-data` 时把行数或文案差异当作缺陷上报。
- 只跑截图、不跑 journey，就宣称"功能一致"。
- 把 base64 截图或整份报告贴进对话，而不是给路径。
- 修改被测站点的任何源码——本技能只做取证与判定。

## 参考文件

- `references/ask-template.md`：给用户的提问/填表模板
- `references/parity-ladder.md`：六层判定标准与验收口径
- `references/config-reference.md`：配置字段、动作词表、常见故障排查
- `references/playwright-setup.md`：安装授权、登录态、内网与 CI
- `templates/parity-config.json`：可直接复制的完整配置样例
