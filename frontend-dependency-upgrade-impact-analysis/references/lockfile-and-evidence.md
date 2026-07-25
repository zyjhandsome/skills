# Lockfile 与上游证据

## 目录

1. 工作区和基线
2. npm lock
3. pnpm lock
4. Yarn lock
5. Manifest 特殊字段
6. 官方证据完整性

## 1. 工作区和基线

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

## 3. pnpm lock

- 识别 lockfileVersion 和 `importers`。
- 目标 workspace 对应 importer 下的 dependencies/devDependencies/optionalDependencies 可能是标量，也可能包含 `specifier`/`version`。
- `packages`/`snapshots` 键用于观察所有版本和 peer variant。
- 版本后缀如 `(react@18.2.0)` 是 peer context，不应混入基础版本。

## 4. Yarn lock

- Yarn v1 selector 块通过 `version` 字段解析实际版本。
- Berry selector 常含 `npm:` 协议；保留 selector，用 `version` 作为解析版本。
- 多 selector 合并到同一块时仍需记录所有声明与实际版本。
- 没有 workspace importer 信息时必须注明限制。

## 5. Manifest 特殊字段

除四类依赖外必须检查：

- `peerDependencies` 和 `peerDependenciesMeta`；
- `overrides`；
- `resolutions`；
- `packageManager`；
- `engines`；
- workspaces 配置。

嵌套 overrides 应用完整键路径表达，不要把它误报成普通直接依赖升级。

## 6. 官方证据完整性

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
| offline | 未联网，仅生成待补来源 |

GitHub API 必须分页或明确页数限制。若人为设置 `max-versions` 截断，报告必须写出总数、保留区间和“不可视为完整证据”。

Release 与 changelog 解析规则：

- monorepo 同 semver 多 release 时必须匹配 package token/tag/path；禁止回退到第一条；
- URL-only Release 是指针，跟随官方页面后才可视为正文；
- 无 Release object 但有 tag 时标 `tag-only`，再从 changelog、官方博客或 docs 补正文；
- changelog 搜索覆盖 default branch、历史 tag/commit、仓库目录、`dev/docs`、大小写及本地化文件名；
- 章节解析覆盖 ATX、setext、HTML heading 和版本索引条目。找到文档但找不到章节必须单独标记，不得输出空白却称完整。
