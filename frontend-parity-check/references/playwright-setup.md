# Playwright 环境与授权

## 探测

```bash
node scripts/preflight.mjs            # 默认检查 chromium
node scripts/preflight.mjs --browser firefox --cwd /path/to/project
```

输出 JSON 含：Node 版本、Playwright 是否可解析及来源路径、浏览器缓存目录与已装内核、
是否能真实启动（会实打实拉起一次浏览器）、`ready` 布尔值。

解析顺序：项目 `node_modules` → `NODE_PATH` → 平台全局目录 → `npm root -g`。
因此**全局安装的 Playwright 也能直接用**，无需在被测项目里装依赖。

## 缺失时的授权流程

`ready: false` 时**停下来**，用 `AskQuestion` 让用户在下列方案中选择，
拿到明确许可后才执行安装命令：

| 方案 | 命令 | 适用 |
|---|---|---|
| 项目内安装 | `npm i -D playwright` + `npx playwright install chromium` | 想把校验纳入项目 CI |
| 全局安装 | `npm i -g playwright` + `npx playwright install chromium` | 不想改动被测项目的 `package.json` |
| 只补内核 | `npx playwright install chromium` | Playwright 已在，缺浏览器 |
| Linux 补系统依赖 | `npx playwright install --with-deps chromium` | 容器/裸机缺 so 库 |
| 用户自行安装 | — | 由用户在自己终端执行，完成后重跑 preflight |

被拒绝就明确告知：**没有浏览器就无法产出任何视觉或功能证据**，本技能到此为止。
不要改用"读源码猜测差异"来冒充比对结论。

## 内网 / 离线

| 变量 | 用途 |
|---|---|
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

两侧登录到的**用户与权限必须相同**，否则菜单、按钮、数据范围都会不同，
这类差异会污染 L2 判定。若两侧只能用不同账号，必须在报告里写明。

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
