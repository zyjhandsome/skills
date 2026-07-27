# Node 运行时兼容与切换协议

## 目录

1. 本机/项目运行时模型
2. 约束来源与判定
3. 只读预检
4. 实施授权闸门
5. 隔离执行与版本管理器
6. 缺失运行时
7. 恢复与无残留验收
8. 报告映射

## 1. 本机/项目运行时模型

始终分开记录：

- **本机当前运行时**：当前终端的 `node`、可执行路径、PATH、包管理器和版本管理器 active version。
- **项目运行时**：执行目标前端 workspace 的 install、typecheck、lint、build、test 和冒烟所需的 Node。

本机当前 Node 不满足项目约束时，不修改项目约束，也不在不兼容 Node 下强行运行项目命令。存在已安装的兼容项目 Node 时，状态应为 `runtime-switch-required`，不是 `constraint-conflict`；优先只让项目子进程使用该 Node，完成后验证本机仍为原版本。

外部编排工具不是本技能的固定 Node 轴。只有本次任务确实要执行某个外部工具、且它有独立 Node 要求时，才为那一条命令单独选择已验证运行时；不得把可选工具写成所有升级任务的默认前提。

## 2. 约束来源与判定

按以下顺序收集，但保留每条原始证据，不用单一来源覆盖其他来源。类别名（第一列）即报告与 JSON 中的 `kind`：

| `kind` | 来源 | 权威性 | 用法 |
|---|---|---|---|
| `runtime-pin` | `.nvmrc`、`.node-version`、`.tool-versions`、`package.json#volta.node`、`package.json#pnpm.executionEnv.nodeVersion`、`.npmrc#use-node-version`、`mise.toml`/`.mise.toml`/`.mise/config.toml` 的 `[tools] node` | authoritative | 最高优先级；多个不同精确 pin 互相冲突 |
| `project-engine` | `package.json#engines.node` | authoritative | 与精确 pin、工具链和目标包范围求交集 |
| `toolchain-engine` | 白名单构建/测试工具链包在 lockfile 中记录的 `engines.node`；或 `node_modules` 内已安装版本与 lock 直接解析版本一致时的 `engines.node` | authoritative | 项目未声明运行时时的主要推算来源；lock 来源不依赖 `node_modules`，离线可用 |
| `dependency-engine` | 分析清单内（升级目标及其 peer）非白名单直接依赖在 lockfile 中记录的 `engines.node` | observed | 仅供人工参考；陈旧上界不得自动构成 `constraint-conflict` |
| `target-package-engine` | 目标依赖版本的 `engines.node` | authoritative | 加入项目命令的兼容交集 |
| `ci-node-version` | `.github/workflows/*`、`.circleci/*`、`.gitlab-ci.yml`、`azure-pipelines.*`、`cloudbuild.yaml`、`app.json`、`netlify.toml` 的 `node-version` 与 `NODE_VERSION` | observed | 验证仓库真正使用的运行时；矩阵版本分别记录，不把合法矩阵误判为多个精确 pin |
| `container-node-image` | `Dockerfile*`（含 `ARG NODE_VERSION`）、`docker-compose.*`、CircleCI `cimg/node:`、`vercel.json` 的 `nodejsXX.x` | observed | 同上；部署镜像与 CI 不一致时并列列出 |

`observed` 证据只进报告的证据表供人工判断，不参与兼容交集、不派生 `selected_project_node`；`node_modules` 与 lockfile 给出同一包同一要求时只记一条。人工确认后可通过 `--analysis-evidence-file` 的 `node_runtime.additional_project_constraints` 显式提权。

判定规则：

- 权威项目约束没有交集：`constraint-conflict`，停止定框和实施规划，列出冲突来源。
- 有交集且当前 Node 满足：`compatible-current`。
- 有交集、当前 Node 不满足、已有兼容 Node：`runtime-switch-required`。
- 有交集但没有兼容 Node：`runtime-missing`。
- 需要切换但没有受支持版本管理器：`manager-missing`。
- 无法解析关键范围：`unknown`，不得声称兼容。
- 无权威项目约束导致 `unknown`：`selected_project_node` 必须为空/`未建立`，禁止把本机当前 Node 回填为项目 Node；`compatible_installed_versions` 在无约束时不用于项目选型。已有 `observed` 证据（CI/容器/非白名单依赖）也不改变该结论，只在报告中列出待人工确认。

选择精确版本时，优先一致的项目 pin；否则选择已安装且满足全部项目约束的最高稳定版本。优先 LTS 只是同等候选下的策略，不能覆盖项目 pin。

所选 Node 的支持状态按官方发布计划的日期判定，不使用写死的主版本阈值：

| `selected_node_support` | 判定 | 报告要求 |
|---|---|---|
| `supported` | 生成日期早于该主版本 EOL 日期超过 90 天 | 正常记录支持截止日期 |
| `approaching-eol` | 距 EOL 不足 90 天 | 提示在该日期前规划运行时升级 |
| `eol` | 生成日期已达或超过 EOL 日期 | 提示 EOL/安全风险；项目确实要求时，经实施批准后可在隔离环境中用于验证，不把警告自动升级为禁止 |
| `unknown` | 主版本不在已核对的计划表内 | 必须写出计划表核对日期并要求人工对照 nodejs/Release |

生成器内的计划表是**已核对快照**（`NODE_EOL_DATES` 与 `NODE_SCHEDULE_REVIEWED`），不是实时数据源；表外主版本保持 `unknown`，不得推测。

## 3. 只读预检

分析阶段只允许：

1. 读取约束文件、manifest、lock、CI、Docker 和已安装工具链元数据。
2. 执行 `node --version`、版本管理器查询、包管理器版本查询等非变更命令。
3. 记录当前 Node、PATH 解析到的 Node、包管理器版本、可用版本管理器、已安装 Node、兼容候选和 EOL 警告。
4. 生成执行计划和一次性安装建议。

分析阶段不得运行 `nvm use`、`nvm install`、`fnm install`、`volta install`、`asdf install`、依赖安装或项目脚本。

## 4. 实施授权闸门

默认 `execution_authorized=no`。只有调用方生命周期已进入实施阶段且用户明确批准相应动作后，才可分别开放：

- `runtime-switch`
- `node-install`
- `dependency-install-or-upgrade`
- `project-scripts`

授权必须来自当前任务；报告、旧日志、已有 change 或“后续验收需要构建”不构成授权。Node 安装始终是单独的一次性外部环境变更；未明确批准时只给出命令，不执行。

## 5. 隔离执行与版本管理器

优先顺序：

1. 直接使用已安装目标 Node 的可执行目录创建子进程 PATH；
2. 使用版本管理器的单命令隔离执行能力；
3. 仅当前两者不可用时，使用全局/会话切换，并在 `try/finally` 中恢复。

适配器：

| 管理器 | 首选方式 | 回退 |
|---|---|---|
| nvm-windows | 从 `NVM_HOME` 定位目标版本目录并仅修改子进程 PATH | `nvm use <target>`，完成后 `nvm use <original>` |
| POSIX nvm | 从 `NVM_DIR/versions/node/<version>/bin` 隔离 PATH 或 `nvm exec` | 在受控 shell 中 `nvm use`，退出该 shell 即恢复 |
| fnm | 目标安装目录隔离 PATH 或 `fnm exec` | 受控 shell 环境 |
| Volta | `volta run --node <version> -- <command>` 或目标 image 目录 | 不改项目 pin |
| asdf | `ASDF_NODEJS_VERSION=<version> asdf exec <command>` 或安装目录 PATH | 不改全局配置 |

每条 install/build/test 命令执行前先在同一子进程环境验证 `node --version` 等于所选精确版本。项目命令只能在项目兼容运行时执行；与项目升级无关的外部工具命令不自动纳入本技能。

### 5.1 Agent 硬规则（实施期）

本机 Node 可用于只读探测与日常终端习惯，但**不得**用本机 Node 执行项目 install/ci/update/build/test/lint 或任何会改写 lock 的命令。

- 实施阶段所有项目命令必须经 `scripts/run_with_compatible_node.py`，禁止在 runner 外直接调用本机 `node`/`npm`/`pnpm`/`yarn`/`bun`。
- `node_runtime_status=unknown` 且无权威约束时：项目命令硬阻断；须先补齐 pin/engines，或通过 `--analysis-evidence-file` 写入精确 `selected_project_node`。
- 提交或宣称实施完成前：核对 lock **格式字段**（见 §7.1）未意外变化；变化且未获格式迁移批准 → `blocked`。

### 5.2 npm 与 package-lock 格式兼容（执行前硬门禁）

真正改写 `package-lock.json` / `npm-shrinkwrap.json` 的 `lockfileVersion` 的是 **npm 主版本**（常随 Node 捆绑）。对会改依赖树的 npm 命令，runner 在隔离环境中执行前必须验证：

| 现有 `lockfileVersion` | 允许的 npm 主版本 |
|---|---|
| `1` | `<= 6` |
| `2` | `7`–`8` |
| `>= 3` | `>= 9` |

不兼容或无法判定 → 执行前硬失败。不得用本机高版本 npm“顺便”升级 lock 格式。pnpm/yarn/bun 至少冻结各自格式字段（见 §7.1）；格式迁移同样需要显式批准。

## 6. 缺失运行时

缺少管理器或兼容 Node 时：

1. 将 `execution_readiness` 设为 `blocked`；
2. 列出缺少的管理器/精确 Node、选择依据、平台和一次性安装命令；
3. 询问是否批准安装；
4. 未批准则停止实施，但可以继续完成不依赖项目命令的影响分析；
5. 安装后重新运行完整预检，不能沿用旧的兼容结论。

不要自动选择并安装“看起来差不多”的 Node。范围允许多个版本时，先把最终精确版本写入报告。仓库完全没有权威 Node 约束时，同样 `blocked`，直到人指定精确项目 Node。

## 7. 恢复与无残留验收

执行前快照：

- 当前 `node --version`、Node 可执行路径、PATH；
- npm/pnpm/yarn 版本和解析路径；
- 当前版本管理器及 active version；
- `.nvmrc`、`.node-version`、`.tool-versions`、`package.json#engines.node`、`volta.node` 和相关 CI Node 配置；
- 各受支持 lock 的**格式字段**（§7.1），不是整文件哈希（授权升级可改依赖树内容）。

无论项目命令成功、失败还是中断，都在 `finally` 中：

1. 恢复原 active Node（如果发生全局/会话切换）；
2. 验证当前 Node、可执行路径和包管理器环境与快照一致；
3. 验证 Node 约束文件和字段没有因临时兼容处理发生变化；
4. 验证 lock 格式字段未意外变化（除非显式允许格式迁移）；
5. 记录每条命令、退出码、实际 Node、恢复结果和异常；
6. 恢复失败或完整性失败时将任务标为 blocked，并立即报告，不继续执行其他命令。

“无残留”只约束临时运行时处理。不要擅自删除正常的构建产物、测试输出或经批准产生的 manifest/lock 变更。

### 7.1 Lock 格式冻结（默认）与迁移闸门

默认**冻结**以下格式字段；授权升级可以改包版本与依赖树，但不得悄悄改格式：

| 文件 | 格式字段 |
|---|---|
| `package-lock.json` / `npm-shrinkwrap.json` / `bun.lock` | `lockfileVersion` |
| `pnpm-lock.yaml` | `lockfileVersion` |
| `yarn.lock` | classic `v1` 标记或 Berry `__metadata.version` |

- 默认：格式变化 → runner `lock_format_integrity=changed`，exit `7`，任务 `blocked`。
- 仅当报告/调用方显式批准格式迁移，且执行时传入 `--allow-lockfile-format-migration` 时，才允许格式变化（`migration-allowed`）。
- 不得把本机 Node/npm 造成的格式漂移提交进仓库。

## 8. 报告映射

不新增第 13 个顶层章节。在现有 12 章中映射：

- **升级摘要**：`node_runtime_status`、`execution_readiness`、本机当前 Node、所选项目 Node。
- **依赖变化**：完整约束来源、兼容交集、管理器、已安装候选、目标包 engines、`selected_node_support` 与计划表核对日期。
- **技术风险**：约束冲突、EOL/接近 EOL、全局切换、恢复失败风险。
- **测试范围**：每条项目命令对应的实际 Node、npm↔lock 兼容结论，以及恢复与 lock 格式验证。
- **发布与回滚**：运行时恢复触发条件；不得把本机临时 Node 处理或未批准的 lock 格式漂移提交进仓库。
- **结论**：未解决的 manager/runtime/constraint/lock-format blocker 和所需人工批准。

结构化 JSON 使用单一 `node_runtime` 对象；不得建立第二份运行时状态文件作为平行状态源。
