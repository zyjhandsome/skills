# vue2-to-vue3-upgrade-impact-analysis 完整模拟与审计报告

> 审计日期：2026-08-01  
> Skill：`C:\Users\zyjhandsome\.cursor\skills\vue2-to-vue3-upgrade-impact-analysis`  
> 实证项目：`D:\Hzhao\AI_Test\Vue2_Test`  
> 原项目全程只读；安装与升级尝试均位于临时克隆。

## 1. 结论

**作为“升级影响分析/决策包”Skill：有价值，但尚未达到可靠生产级。** 结构、边界和人类确认流程设计较好，正常前向执行能产出质量较高的项目画像与 Wave 1/Wave 2 决策包。

**作为“在不影响功能的情况下完成 Vue2→Vue3 升级”的能力：明确不成立。** 该 Skill 按契约只分析、不实施，也不执行迁移后的 build、unit、E2E、视觉回归或前后差分。即使 `analysis_status=complete`、`batch_implementation_gate=ready`、validator exit 0，也不能证明升级成功或功能等价。

对 `Vue2_Test` 的外部隔离升级实证也没有通过：旧版基线可 build/lint/test，但迁移候选最终仍有 153 个构建错误、5/26 单测失败、lint 配置失败，且没有 E2E/视觉证据。

综合判断：

| 评估口径 | 结论 |
|---|---|
| 影响分析 Skill | 6.4 / 10，条件可用 |
| 生产级决策门禁 | 4.5 / 10，需要修复 P0 校验与 gate 语义 |
| 无功能回归升级能力 | 2.0 / 10，不具备 |
| 对 `Vue2_Test` 立即升级可行性 | 暂不通过；先补可复现基线、依赖闭包与 E2E/视觉基线 |

## 2. 审计方法与证据

本次完成了以下检查：

1. 完整读取 `SKILL.md`、11 个 references、2 个 templates、3 个 scripts、18 个 tests、fixtures、`agents/openai.yaml`，以及仓库外 3 份 Vue2→Vue3 相关 usage/research 文档。
2. 使用 codebase-memory 知识图谱索引 Skill 和 `Vue2_Test`，再做调用链、legacy API 与关键配置核查。
3. 运行 Skill 自带 18 个测试：全部通过。
4. 运行 `quick_validate.py`：在 Windows 上需额外提供 PyYAML，并设置 `PYTHONUTF8=1` 后通过。
5. 在原项目执行只读 preflight/profile；在临时克隆建立旧版可执行基线。
6. 对临时迁移候选做多轮依赖、构建、测试、lint 压力模拟。
7. 完整走过多轮确认流程：Wave 1、含糊自然语言、精确 path token、Wave 2、混合 proceed/defer、最终 complete。
8. 独立代理交叉核对：正常前向执行、validator 对抗审计、功能等价可证明性。
9. 核对 2026-08-01 当前官方资料与 npm registry。

## 3. Vue2_Test 基线

### 3.1 仓画像

| 项 | 结果 |
|---|---|
| Vue | `2.6.10` |
| 构建 | Vue CLI `4.4.4` / Webpack 4 时代配置 |
| Router | `3.0.2` |
| Store | Vuex `3.1.0` |
| UI | Element UI `2.13.2` |
| Test Utils | `1.0.0-beta.29` |
| Node | 主机 `v26.5.0`；项目仅声明 `>=8.9` |
| Lockfile | 无 |
| 代码规模 | 约 130–131 个 SFC、87 个 JavaScript 文件 |
| 测试 | 6 suites / 26 tests；仅 2 个组件，其余为工具函数 |

### 3.2 Vue 2 特有迁移面

知识图谱与限定源码检索确认：

| 模式 | 命中 |
|---|---|
| `.sync` | 12 处 / 9 文件 |
| `slot-scope` | 69 处 / 14 文件 |
| `$listeners` | 3 处 / 2 文件 |
| `<template functional>` | 3 处 / 3 文件 |
| `beforeDestroy` | 14 处 / 14 文件 |
| `Vue.use` | 8 处 / 8 文件 |
| `new Vue` | 1 处 |
| Element UI 相关 | 至少 22 个源码命中 / 17 文件；独立复核统计约 436 个 `<el-*>` 使用点 |
| Router 私有/移除 API | `router.addRoutes`、`router.matcher`、`path: '*'` |

额外高风险点：Element UI 私有内部导入 `element-ui/src/utils/resize-event`、运行时主题 CSS 替换、SVG sprite、自定义 splitChunks、mock middleware、`require.context`、动态权限路由、登录/退出与角色切换。

### 3.3 旧版可执行基线

原仓无 lockfile。普通 `npm install` 因旧生命周期链路长时间静默，终止后改在新克隆使用 `--ignore-scripts` 建立诊断基线：

| 验证 | 结果 |
|---|---|
| install | 2083 packages；大量 deprecated/engine warnings |
| unit | 6/6 suites，26/26 tests 通过 |
| lint | 通过 |
| production build | 通过，2 个 bundle-size warnings |
| production-only audit | 17 vulnerabilities：2 critical、7 high、6 moderate、2 low |

这只能证明临时解析出的 2026 依赖树在本机可运行，不能恢复历史发布所用的精确依赖树。

## 4. 多轮压力模拟

### 4.1 正常 Skill 流程

| 轮次 | 输入/动作 | Skill 行为 | 结果 |
|---|---|---|---|
| 0 | 明确项目与临时 `--output-dir` | preflight → profile → 决策包 | 正常 |
| 1 | 到达 Wave 1 | 推荐 `compat-big-bang`，子系统 pending | `partial / needs_choice / frozen` |
| 2 | 用户说“继续，全部放行，别再问了” | 拒绝推断 token，报告不变 | 正确、安全 |
| 3 | `proceed:path:compat-big-bang` | 记录 path，全部 High/blocker 同波变 ready | 正常 |
| 4 | 5 个 subsystem proceed，UI 使用 `defer` | 所有行 cleared | 暴露严重逻辑问题 |
| 5 | 最终 regenerate + validate | `complete / decided / ready` | validator 0，但 UI blocker 仍 deferred |

**P0 问题：** UI 是 Vue3 切换的必需 blocker，`defer` 后仍得到 `batch_implementation_gate=ready`。这会让“ready”产生危险的实现就绪错觉。报告虽提醒 gate 仅信息性，但名称和状态仍会被后续编排误用。

### 4.2 隔离升级候选

在临时 `candidate` 中依次模拟：

1. 直接升级 Vue/compat、Router、Vuex、Element Plus、CLI、test-utils：npm 首先因 CLI 5 与 ESLint 6 peer conflict 失败。
2. 补 ESLint/parser：安装成功，但 test transform 缺失；build 因旧 `vue.config.js` preload 插件失败；lint 因旧规则 schema 失败。
3. 补 `@vue/vue3-jest`、compat alias、CLI5/Webpack5、Router/Store/Element Plus 入口：继续出现 Webpack 插件 peer 冲突。
4. 移除旧 HTML 插件并升级 SVG loader：进入源码编译后仍有 153 errors。

主要错误簇：

- Webpack 5 不再默认提供 `stream` / `path` polyfill。
- `core-js@3.6.5` 不包含新 Babel 注入的多个模块。
- 3 个 `<template functional>` 被 Vue 3 compiler 拒绝。
- 大量 `::v-deep` 迁移警告。
- Element UI 主题 SCSS、私有 resize API、ThemePicker 运行时换肤逻辑不能直接复用。
- Vue Router 动态路由/reset、Element Plus 图标与组件行为仍需专项迁移。
- 候选单测为 3 suites pass、3 fail；21/26 tests pass，5 个失败。
- 候选 lint 在正式扫描源码前即因规则 schema 变化失败。

候选仅修改 13 个文件（64 insertions / 97 deletions）就已暴露上述问题，远未达到功能验证阶段。

## 5. Validator 对抗测试

自带 18 个测试全部通过，但独立审计构造的 10 个对抗用例也全部得到 exit 0。最严重的可绕过项：

1. `decision-records/*.md` 只检查“文件存在”，不校验任何必填字段、枚举、文件名/单元键一致性或人工 token。
2. `complete` 报告可以没有 §2 依赖表、没有 §4 子系统行，所有章节只写占位符。
3. `complete` 不要求确认队列存在 path 行；任意 `migration-path__*.md` 空壳即可。
4. 整份报告放进 Markdown code fence 仍可通过；HTML comment 中的状态也可被 regex 读取。
5. 重复、冲突状态可用隐藏字段覆盖可见字段。
6. 根报告存在时，`--evidence-dir` 会提前返回并忽略非法嵌套批次。
7. 空 `BATCH-INDEX.md`、任意深度目录也可通过。
8. `scope_status=banana`、`risk=critical`、`readiness=magic` 可通过；非法 risk 反而绕过 High/blocker 门禁。
9. 必选章节可全部编号 42、乱序、重复。
10. `report_path` 不需要等于实际目录，marker 也不限制在规定章节。

本地主代理另构造了“无 path 决策、空子系统表、ghost blocked 行、错误 report_path、空壳 path record”的 `complete/ready` 报告，validator 同样返回 0。

因此 validator 当前只能被视为脆弱的文本 lint，不能称为契约校验器。

## 6. 分维度评分

| 维度 | 分数 / 10 | 评价 |
|---|---:|---|
| 名称 | 7 | 合规、准确、触发明确；但偏长、名词化，不符合“短、verb-led”偏好。建议 `analyze-vue2-to-vue3-upgrade`，或保留现名避免迁移成本。 |
| 逻辑性 | 5 | 工作流顺序清楚；但把 runtime 策略、build 工具和发布拓扑揉成一个 path，且 deferred blocker 仍 ready。 |
| 清晰性 | 8 | SKILL 170 行、表格和边界清楚，渐进披露较好。 |
| 准确性 | 6 | 主体迁移知识正确；profile 分类存在明显错误，默认路径过度泛化，部分官方 URL 已变。 |
| 时效性 | 5 | 没有 as-of、版本来源或刷新机制；2026 最新为 Vue 3.5.40、Vue Router 5.2.0、Vite 8.2.0，而 Skill 仍把 Router 4/CLI→Vite 当固定目标描述。 |
| 实用性 | 6 | 能产出较好的前置决策包；不能实施或证明结果，必须与 delivery/verification 明确衔接。 |
| 易用性 | 5 | 短提示可触发；但输出路径 token、两波逐项精确 token、无 bulk 签名确认，交互成本高。 |
| 重复/重叠度 | 7 | 长行跨文件逐字重复很少；但 gate、菜单、状态与契约概念在 SKILL、4 个 reference 和 3 个外部 docs 中多处维护。 |
| 可维护性 | 6 | 模块化和 tests 是优点；validator 单函数 147 行、cyclomatic 31、cognitive 56，枚举/契约散落。 |
| 繁冗性 | 7 | 主文件控制良好；“never run”、状态与确认规则重复较多，可由单一 schema 生成。 |
| 安全边界 | 8 | 不安装、不 codemod、不误认自然语言的设计很强；但 deferred blocker→ready 削弱安全性。 |
| 可测试性 | 4 | 有 18 个测试，但负向面很窄，10 个语义错误用例全漏。 |
| 可移植性 | 5 | 强依赖 Python/Node/包管理器和 HEAD 网络探针；Windows UTF-8/依赖体验不平滑，monorepo/pin 支持不足。 |
| 可审计性 | 6 | 决策记录与 fact/inference 设计好；实际 validator 不校验记录内容与 provenance。 |
| 可复现性 | 4 | 不要求 lockfile、工具版本、来源时间、证据 hash；无锁项目仍可 preflight PASS。 |
| 功能等价保障 | 2 | 只“命名”验证项，不运行、不绑定证据；complete/ready 与 parity 无直接关系。 |
| 安全/供应链视角 | 4 | 未把 EOL、audit、lockfile、恶意 lifecycle、registry 来源纳入默认证据矩阵。 |

## 7. 关键设计问题

### P0：重新定义 gate

建议将当前状态拆成：

- `analysis_status`：分析材料是否完成。
- `decision_status`：人类选择是否闭环。
- `analysis_handoff_gate`：是否可以交给实施规划。
- `implementation_readiness`：始终由后续实施/验证流程计算，本 Skill 固定为 `not_assessed`。

每个子系统增加：

- `required_for_path=yes|no`
- `resolution=accepted|deferred|rejected|blocked`
- `implementation_blocking=yes|no`

任何 `required_for_path=yes` 且 `resolution!=accepted` 的单元都必须冻结 handoff/implementation gate。Element UI→Element Plus 在本项目中不能 defer 后仍 ready。

### P0：重写 validator

1. 使用 Markdown AST，忽略 code fence 和 HTML comment。
2. 只允许一个可见状态表；键唯一、值枚举合法。
3. 强制章节 1–10 的顺序、编号、唯一性。
4. 校验 §2、§4、§7、§8、§9 的精确表头、最小行数、ID/枚举/唯一性。
5. complete 必须恰好一个 path row，且与推荐 path、record 文件名、单元键和人工 token 一致。
6. 完整解析每个 Decision Record；禁止空壳、垃圾内容和“全部放行”。
7. canonicalize `report_path` 并与实际目录匹配。
8. 校验单批/多批布局、BATCH-INDEX 内容、列举关系和多余报告。
9. 将对抗审计的 10 个 cases 纳入回归测试。

### P1：把路径拆为正交决策轴

当前 `compat-big-bang` 同时表达三件事，导致路径选择过早锁死：

| 轴 | 建议取值 |
|---|---|
| Runtime | `compat` / `direct-vue3` |
| Build | `cli5-webpack5` / `vite` / `existing-vite` |
| Release topology | `single-cutover` / `coexist` |

官方 migration build 同时给出 Vue CLI 和 Vite 配置；Vue CLI 已进入 maintenance mode，但“最终偏 Vite”不等于“每个仓必须把 build 迁移与 runtime 迁移压在同一故障域”。[Vue migration build](https://v3-migration.vuejs.org/migration-build)、[Vue CLI maintenance mode](https://cli.vuejs.org/)、[Vite guide](https://vite.dev/guide/)。

### P1：增强 preflight/profile

Preflight：

- 无 Node/Python 时允许 `manifest-only degraded analysis`，不要阻断所有只读价值。
- 读取 `.nvmrc`、`.node-version`、Volta、`packageManager`、parent workspace lock。
- 用 semver 真正比较 `engines`；记录当前 toolchain 支持区间。
- registry/docs 网络探针并行；HEAD 失败后 GET fallback。
- 无 lockfile 对“功能等价验证”应是 blocker，不只是普通说明。

Profile：

- 读取 lockfile 的精确解析版本，而非只看 package.json spec。
- 不用字符串比较 major；当前 `vue-router@10` 会被错误判成 needs-major。
- 正确分类 `@vue/test-utils@2`、`@vue/compiler-sfc@3`、Vite、eslint-plugin-vue、CLI5。
- 识别 `vuedraggable`、UI 私有 import、core-js、Sass、Webpack 插件、mock/devServer、require.context。
- 直接输出完整默认子系统表与 legacy API 计数，减少 Agent 自由发挥。

### P1：引入时效性元数据

报告必须记录：

- `evidence_as_of`
- registry 查询时间与 resolved latest/minimum supported versions
- 官方 URL 的最后验证时间
- Node/browser support matrix

截至本次审计：Vue registry latest 为 3.5.40；Vue Router 5 是 v4→v5 过渡版本，普通 Router 4 用户升级到 5 基本无代码变化；Vite 8.2.0 要求 Node `^20.19.0 || >=22.12.0`。[Vue registry](https://registry.npmjs.org/vue/latest)、[Vue Router 5 migration](https://router.vuejs.org/guide/migration/v4-to-v5)、[Vite guide](https://vite.dev/guide/)。

Element Plus 官方还明确提示：migration build 下部分组件依赖 Vue 3 内部 API，可能需要 MODE 3；2.8.5+ 要求 Sass 1.79+，而本项目只有 Sass 1.26.2。[Element Plus migration](https://element-plus.org/en-US/guide/migration)、[Element Plus installation](https://element-plus.org/en-US/guide/installation.html)。

### P2：降低重复与交互疲劳

- 用一个机器可读 schema 生成状态枚举、队列表头、Decision Record 字段和 validator 常量。
- 合并 `human-confirmation-gates.md` 与 `next-action-choice-menus.md`，或让前者只定义状态机、后者只保留 UI 文案。
- 外部 usage/research docs 只链接 Skill，不复制状态真相。
- 支持带 snapshot hash 的 batch token，例如确认明确列出的 6 个单元；仍禁止无对象的“全部放行”。

## 8. Vue2_Test 要达到“高置信功能等价”所需证据

在任何升级实施前，至少补齐：

1. 固定 Node LTS、包管理器、registry、lockfile，重建并存档 Vue2 baseline。
2. 将现有 lint/unit/build 日志与构建产物 hash 纳入基线。
3. E2E：登录/退出、401、权限/角色切换、动态路由、404、tags-view 缓存、CRUD、表格、上传、Excel/PDF、编辑器、图表 resize、主题、语言。
4. Element UI→Element Plus 跨视口视觉回归、键盘/焦点/表单校验断言。
5. 前后 API 请求/响应、关键 Vuex 状态、路由结果差分。
6. Router reset/addRoute、filters、directives、plugins、test-utils v2 专项测试。
7. `@vue/compat` warning 清零、browser console error 清零，再移除 compat。
8. production/staging 两套 build，验证 base/publicPath、SVG sprite、动态 import、env、mock、CSS、chunk、preview、回滚发布。

“零回归”无法被绝对证明；合理目标应是“在批准的功能清单、浏览器矩阵和测试证据范围内无已知回归”。

## 9. 最终验收结论

- **Skill 结构校验：通过。**
- **Skill 自带测试：通过，但充分性不通过。**
- **正常多轮交互：基本通过。**
- **deferred blocker gate：不通过，P0。**
- **validator 语义契约：不通过，P0。**
- **时效性与版本分类：部分通过。**
- **Vue2_Test 影响分析：可用。**
- **Vue2_Test 无功能回归升级：未完成、未证明，不通过。**

建议先修复 P0，再把该 Skill 定位为“分析交接门”，不要让 `complete/ready` 被解释为实现或发布就绪。
