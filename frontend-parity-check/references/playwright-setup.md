# Playwright 环境与授权

## 探测

```bash
node scripts/preflight.mjs            # 默认检查 chromium，失败时自动试本机 chrome / msedge
node scripts/preflight.mjs --browser firefox --cwd /path/to/project
node scripts/preflight.mjs --channel msedge   # 只验证某个本机浏览器
```

输出 JSON 含：Node 版本、Playwright 是否可解析及来源路径、浏览器缓存目录与已装内核、
是否能真实启动（会实打实拉起一次浏览器）、`channels`（本机浏览器探测结果）、
`useConfig`（**照抄进配置文件即可用的启动配置**）、`ready` 布尔值。

解析顺序：项目 `node_modules` → `NODE_PATH` → 平台全局目录 → `npm root -g`。
因此**全局安装的 Playwright 也能直接用**，无需在被测项目里装依赖。

## 缺失时的授权流程

`ready: false` 时**停下来**，用 `AskQuestion` 让用户在下列方案中选择，
拿到明确许可后才执行安装命令：

| 方案 | 命令 / 配置 | 适用 |
|---|---|---|
| 项目内安装 | `npm i -D playwright` + `npx playwright install chromium` | 想把校验纳入项目 CI |
| 全局安装 | `npm i -g playwright` + `npx playwright install chromium` | 不想改动被测项目的 `package.json` |
| 只补内核 | `npx playwright install chromium` | Playwright 已在，缺浏览器 |
| **用本机 Chrome/Edge** | 配置 `"channel": "chrome"`（或 `msedge`） | **内核下不来**：企业代理、自签证书拦截、`PLAYWRIGHT_DOWNLOAD_HOST` 不可达 |
| Linux 补系统依赖 | `npx playwright install --with-deps chromium` | 容器/裸机缺 so 库 |
| 用户自行安装 | — | 由用户在自己终端执行，完成后重跑 preflight |

被拒绝就明确告知：**没有浏览器就无法产出任何视觉或功能证据**，本技能到此为止。
不要改用"读源码猜测差异"来冒充比对结论。

## 企业环境：装得上包、下不来内核

典型链路是"证书拦截 → 下载中断 → 代理域名 DNS 失败"。此时只需要 `playwright` 这个
JS 包本身（不含内核），浏览器改用本机已装的 Chrome / Edge：

```bash
npm i -D playwright --ignore-scripts     # 或 PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
node scripts/preflight.mjs               # 会自动探测 chrome / msedge
```

preflight 报出可用 channel 后，写进配置（两侧共用，保证可比）：

```json
{ "browser": "chromium", "channel": "chrome" }
```

浏览器装在非标准路径就用 `"executablePath": "C:\\Program Files\\...\\chrome.exe"`。

> `channel` 用的是本机浏览器版本，与官方 Chromium 的渲染可能有细微差别。
> **两侧必须用同一个 channel**，并在结论里写明浏览器与版本（报告已自动记录）。

其他可用旋钮：

| 变量 | 用途 |
|---|---|
| `NODE_EXTRA_CA_CERTS` | 指向企业根证书 pem，解决 npm/下载的证书拦截 |
| `PLAYWRIGHT_DOWNLOAD_HOST` | 指向内网镜像 |
| `PLAYWRIGHT_BROWSERS_PATH` | 指向共享或预置的浏览器缓存目录 |
| `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` | 复用系统已有内核时跳过下载 |

也可以让用户在能联网的机器上装好后，把 `ms-playwright` 缓存目录整体拷贝过来，
再用 `PLAYWRIGHT_BROWSERS_PATH` 指过去。

## 登录态

优先用 `storageState`，避免每个状态都重登：

1. 配置 `auth.storageState` 指向一个文件路径 + `auth.actions` 写登录步骤。
2. 首次 capture 时文件不存在 → 执行登录 → 自动保存。
3. 后续直接复用；过期就删掉文件重跑。

`auth.actions` 里**任何一步失败，或登录后仍停在登录页，整侧立即作废**。
以前这类失败是静默的，结果是采回二十张登录页截图还判 `ok`。

两侧登录到的**用户与权限必须相同**，否则菜单、按钮、数据范围都会不同，
这类差异会污染 L2 判定。若两侧只能用不同账号，必须在报告里写明。

### 用户"已经登录了"：从他的浏览器导出会话

企业 SSO（多因子、扫码、证书）往往没法用 `auth.actions` 脚本化，但用户自己的浏览器
里已经有会话了。Playwright 默认是干净会话，**不会**共享它——必须显式导出：

```bash
# 1) 让用户完全退出浏览器，再带调试端口启动，并正常登录被测系统
#    Windows: "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
#    macOS:   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222
# 2) 导出（--url 会开一个标签页，让 localStorage 里的 token 也能被采到）
node scripts/export-storage-state.mjs --out auth/candidate.json --url https://new.example.com/home
```

把生成的文件填进 `<side>.auth.storageState`。两侧同源共用一份；跨域各导一份。

注意事项：

- **已在运行的浏览器不会凭空开出调试端口**，必须先完全退出再带参数启动。
- 脚本连接的是用户自己的浏览器，因此**绝不调用 `browser.close()`**
  （那会连带关掉用户的所有窗口）；只关它自己新开的标签页，然后直接退出进程。
- 导出的文件等价于登录凭据：放进 `auth/`（已在 `.gitignore`），不要提交、不要贴进对话。
- 会话过期后重新导出即可；若报告出现"落地 URL 命中禁止模式"，通常就是它过期了。
- 无法加调试端口时的退路：让用户在浏览器里手工导出 Cookie，或复制一份用户数据目录后
  用 `launchPersistentContext` 拉起（Chrome 运行中会锁定该目录，必须复制而不是直连）。

密码不要硬编码进提交到仓库的配置文件；用环境变量或让用户在本地填写，
并把 `auth/` 目录加入 `.gitignore`。

## HTTPS 与网关

- 自签证书：`context.ignoreHTTPSErrors` 默认已开。
- 需要网关头或灰度标记：用 `extraHTTPHeaders`。
- 基线在线上、候选在本地：属于 `dataParity=different-data`，
  且网络延迟差异会影响 `networkidle`，必要时调大 `settleMs`。

## CI

capture 与 compare 都是纯 CLI，可直接进流水线：

```bash
node scripts/preflight.mjs || exit 1
node scripts/capture.mjs --config parity.json --side baseline
node scripts/capture.mjs --config parity.json --side candidate
node scripts/compare.mjs --config parity.json   # 有阻断项时退出码 1
```

把 `parity-run/` 作为构建产物归档。CI 容器的字体集通常与开发机不同，
**像素基线不要跨环境复用** —— 同一次运行内采集两侧才有可比性。
