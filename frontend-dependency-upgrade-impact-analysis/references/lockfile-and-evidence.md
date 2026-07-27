# Lockfile 与上游证据

## 目录

1. 工作区和基线
2. npm lock
3. pnpm lock
4. Yarn lock
5. Bun lock
6. Manifest 特殊字段
7. 官方证据完整性

## 1. 工作区和基线

受支持的 lockfile 按检测优先级为：`package-lock.json`、`npm-shrinkwrap.json`、`pnpm-lock.yaml`、`yarn.lock`、`bun.lock`、`bun.lockb`。其余类型（例如 Deno 的 `deno.lock`）必须报为不受支持并写出实际文件名，不得按 npm 语义猜测。

先确定真正拥有依赖声明的 `package.json`，再解析该 workspace/importer。根目录 lock 不等于根 workspace 的直接依赖。缺少 frontend `package.json`（`importer_resolution=failed`）是与 unknown baseline 同级的实施闸门阻塞：生成器退出码 `5`，不得当作可批准升级结论。

记录：

- manifest path 与依赖字段；
- package manager/lock path；
- workspace/importer；
- manifest spec；
- direct resolved version；
- all observed versions；
- claimed from/to；
- `matches_from`、`matches_to`、`mismatch`、`unknown`。

宽松声明如 `^4.24.16` 与 lock `4.24.16` 不算冲突；比较的是可提取的 exact baseline 和直接解析版本。`workspace:`、`file:`、`link:`、Git URL、npm alias 等协议不得被伪装成普通 semver。

### 前端工作区范围

本技能只分析**前端**依赖工作区：

- 用户未点名时：根据 manifest/importer 识别前端候选；明显的后端服务、API 包、小程序/原生应用 importer 默认排除。
- 恰好一个可信前端工作区 → 采用并写入报告。
- 多个前端工作区仍无法消歧 → 询问用户，禁止默默分析整仓或选中后端包。
- 不要把「管理后台 Web」写成全局默认名；只有仓库证据唯一指向该包时才可采用。

## 2. npm lock

- v2/v3：优先读取 `packages["node_modules/<package>"].version`；嵌套 `node_modules` 路径用于识别重复版本。
- v1：读取 `dependencies[package].version` 并递归观察嵌套 dependencies。
- 记录 `lockfileVersion`；解析不到直接版本时标 unknown，不回退猜测。
- `lockfileVersion` 是格式基线：授权升级可改依赖树，默认不得改格式；本机高版本 npm 造成的 v1↔v2↔v3 漂移视为污染。执行门禁见 `references/node-runtime-compatibility.md` §5.2 / §7.1。
- v2/v3 的直接依赖条目还带 `engines`：读取其中的 `node` 作为该解析版本声明的运行时要求，用途见 `references/node-runtime-compatibility.md` §2 的 `toolchain-engine` / `dependency-engine`。

只有**当前** lock 缺失才是发现项。分析升级前状态时没有 before/after lock 属正常，报告不得输出无主语的"未找到 lockfile"。lock 路径存在但类型不受支持时，必须写出实际文件名和受支持类型清单。

## 3. pnpm lock

- 识别 lockfileVersion 和 `importers`。
- 目标 workspace 对应 importer 下的 dependencies/devDependencies/optionalDependencies 可能是标量，也可能包含 `specifier`/`version`。
- `packages`/`snapshots` 键用于观察所有版本和 peer variant。
- 版本后缀如 `(react@18.2.0)` 是 peer context，不应混入基础版本。
- `packages` 块内的 `engines`（行内 `{node: ...}` 或缩进子键两种写法）按解析版本读取，作为 Node 约束证据。
- `catalog:` / `catalog:<name>` 协议不是 semver。必须从 `pnpm-workspace.yaml` 的 `catalog:` / `catalogs.<name>` 解析有效范围，在 manifest 声明中同时呈现协议与解析结果，并提示改动范围时需要同步 catalog。解析不到条目时保持人工确认，不得当作普通版本声明。

## 4. Yarn lock

- Yarn v1 selector 块通过 `version` 字段解析实际版本。
- Berry selector 常含 `npm:` 协议；保留 selector，用 `version` 作为解析版本。
- 多 selector 合并到同一块时仍需记录所有声明与实际版本。
- 没有 workspace importer 信息时必须注明限制。

## 5. Bun lock

- `bun.lock` 是 JSONC：解析前需要剥离注释和尾随逗号，且不得破坏字符串内容。
- `workspaces` 的根 importer 键是空字符串 `""`；`.` 应映射到该键。
- `packages` 的键即依赖路径：`axios` 是直接依赖，`wrapper/axios` 是嵌套重复；值数组第一项形如 `axios@1.7.9`，用于提取实际版本。
- Bun 文本锁与 Yarn v1 都不记录 `engines`，Node 约束只能来自 manifest、运行时 pin 或已安装元数据。
- `bun.lockb` 是二进制锁，不能读出直接解析版本。此时必须给出可执行出路（提交 `bun.lock` 或运行 `bun install --save-text-lockfile`），并保持基线 unknown，不猜测。

## 6. Manifest 特殊字段

除四类依赖外必须检查：

- `peerDependencies` 和 `peerDependenciesMeta`；
- `overrides`；
- `resolutions`；
- `packageManager`；
- `engines`；
- workspaces 配置。

嵌套 overrides 应用完整键路径表达，不要把它误报成普通直接依赖升级。

## 7. 官方证据完整性

每个**版本**先解析并记录：

- npm `versions[version].repository`、`directory`、`gitHead`；仅缺失时才回退顶层 `repository`；
- 在 `gitHead` 或精确 package-aware tag 上读取历史 `package.json`，核对 name/version；
- repository lineage；跨仓库区间必须拆分取证；
- 仓库 default branch；不得只假设 `main/master`。

每个包继续记录：

- npm 目标版本页和目标版本元数据；
- 官方 repository/homepage；
- release notes；
- changelog；
- migration/breaking guide；
- target peerDependencies/engines；
- security advisory（适用时）。

完整性状态：

| 状态 | 定义 |
|---|---|
| complete | 版本区间完整，且 registry/repository/release/changelog/migration/compatibility/security/support/license 均已确认或有明确 not-applicable 依据 |
| partial | 有官方来源但部分版本、标签或文档缺失 |
| ambiguous | monorepo tag/release 无法可靠归属到目标 package |
| offline | 调用方显式 `--offline` 且未取得联网证据；仅生成待补来源。**禁止**因 `.npmrc`/私有 registry/内网形态推断 |

### 公网可达性门禁

上游取证前必须用**实际公网探测**证明可达性（Agent `curl` + 生成器内置 probe，绕过 HTTP cache）。探测目标是公网端点，不是项目 `.npmrc` 镜像：

1. 先探 `https://registry.npmjs.org/`；
2. registry 失败时再探 `https://api.github.com/`；
3. 两者均不可达 → 停住问人是否显式 `--offline`；生成器 exit `8`，stderr JSON 含 `network_reachability=unreachable` 与 `awaiting_offline_confirmation=true`；确认前**禁止**回读本地 `upstream-evidence`，也不得把 `evidence_completeness` 标成 `offline`；
4. registry 通、或 registry 不通但 GitHub 通 → 保持联网模式；单次抓取失败记 `partial`/`missing` + diagnostics，不得改标 offline；
5. 精确升级取证中：若 `from→to` 区间内 release 与 changelog **均无可用正文**，再探 GitHub；仅当该探测失败才升级为「问人是否 `--offline`」。403/429 等有响应的失败不算公网不通。

`--offline` **仅**调用方/人显式传入。Agent 不得因私有 registry 或「像内网」擅自添加。

### 报告级 upstream-evidence

精确升级（明确 `from → to`）默认采用 **download-first**：先把官方 registry / release / changelog 下载落到报告输出目录旁的 `upstream-evidence/`，再以该本地包作为 release/changelog 依据之一。论证范围仅限该包升级区间。开放目标（无 `to`）不写、不读该目录。

目录内容：

- `manifest.json`：包名、区间、抓取时间、每版本状态与来源；
- `<package-safe>/registry.json`：npm 包元数据（供离线回放区间）；
- `<package-safe>/fetch-failure.json`：registry 级失败时的诊断（HTTP 状态、限流线索等）；
- `<package-safe>/<version>/release.md`、`changelog.md`、`sources.json`（`sources.json` **始终**写入，即使正文 missing）。

行为：

- 默认开启写入；`--no-upstream-evidence` 关闭；
- 联网抓取时即使 release/changelog 正文缺失，也必须创建证据目录与 `sources.json`，并写入 `fetch_diagnostics`（如 GitHub `403/429`、未设置 `GITHUB_TOKEN`、超时）；
- **本地回读仅在显式 `--offline` 时允许**；联网模式下单次 URL 失败不得静默 merge 本地包；本地回读最多把完整性标为 `partial`，不得标 `complete`；
- 默认保留目录；`--cleanup-upstream-evidence` 在报告写成功后删除；
- 与六小时 HTTP cache 并存：后者是传输缓存，前者是报告级可读证据包；可达性探测必须绕过该 cache。

### 混批自动拆分

同一轮同时包含精确升级与开放目标时，生成器在 `evidence/frontend-dependency-upgrade/` 下自动拆成：

- `exact/`：精确升级报告 + `upstream-evidence/`
- `open-target/`：开放目标报告（无 upstream-evidence）
- `BATCH-INDEX.md`：批次索引

单模式（只有精确或只有开放目标）仍写在 `frontend-dependency-upgrade/` 根下，保持旧布局。

GitHub API 必须分页或明确页数限制。若人为设置 `max-versions` 截断，报告必须写出总数、保留区间和“不可视为完整证据”。

Release 与 changelog 解析规则：

- monorepo 同 semver 多 release 时必须匹配 package token/tag/path；禁止回退到第一条；
- URL-only Release 是指针，跟随官方页面后才可视为正文；
- 无 Release object 但有 tag 时标 `tag-only`，再从 changelog、官方博客或 docs 补正文；
- changelog 搜索覆盖 default branch、历史 tag/commit、仓库目录、`dev/docs`、大小写及本地化文件名；
- 章节解析覆盖 ATX、setext、HTML heading 和版本索引条目。找到文档但找不到章节必须单独标记，不得输出空白却称完整。
