# Vue 2 → Vue 3 升级调研摘要（方法地图 + 选型）

> 受众：多仓 Vue2 前端团队的技术决策者 / 负责人。  
> 范围：核心框架 + Router + **构建工具必须同升** + 状态管理 + UI 库 + TS/测试工具链。  
> 策略偏好：**单仓大爆炸切流**；栈差异大时用「仓画像决策树」选型。  
> 详细论述见同会话调研回复；本文只保留可分享的结论层。

---

## 1. 结论（先看这个）

| 问题 | 建议 |
|---|---|
| 官方主路径是什么？ | 读 [Vue 3 Migration Guide](https://v3-migration.vuejs.org/)；用 [`@vue/compat`](https://v3-migration.vuejs.org/migration-build) 做仓内桥接，再摘掉兼容层 |
| 官方新默认栈是什么？ | Vite、Vue Router 4、Pinia、Volar/`vue-tsc`、`@vue/test-utils` v2（见 [Recommendations](https://v3-migration.vuejs.org/recommendations)） |
| 和你们「单仓大爆炸」怎么对齐？ | **切流可以大爆炸**；**仓内改造仍建议分步**（先依赖审计与 Vite，再 compat 清 warning，再摘 compat）。不要把 Composition API 重写绑进同一次升级 |
| 多仓怎么推？ | 先做仓画像 → 挑低风险试点仓 → 沉淀 checklist → 再批量复制；不要假设一条路径打天下 |
| 通常最难的一块？ | 不是 Vue 核心 API，而是 **插件/UI 库/构建/测试**（尤其 Element UI → Element Plus、Vuetify 等） |

Vue 2 已于 **2023-12-31 EOL**。Extended LTS 仅作过渡，不是长期方案。

---

## 2. 方法地图（三类来源）

### 2.1 官方（首选权威）

| 资源 | 用途 |
|---|---|
| [v3-migration.vuejs.org](https://v3-migration.vuejs.org/) | Breaking changes 总清单 |
| [Migration Build / `@vue/compat`](https://v3-migration.vuejs.org/migration-build) | Vue2 行为跑在 Vue3 引擎上，靠 runtime warning 驱动改造 |
| [Framework recommendations](https://v3-migration.vuejs.org/recommendations) | CLI→Vite、Vuex→Pinia、Vetur→Volar 等新默认 |
| [Vue Router 4 migration](https://router.vuejs.org/guide/migration/) | `createRouter` / `history` 等 |
| [Vuex 4 migration](https://vuex.vuejs.org/guide/migrating-to-4-0-from-3-x.html) | 可先 Vuex4 再 Pinia |
| [Pinia](https://pinia.vuejs.org/) | 官方推荐状态管理 |
| [Element Plus Migration](https://element-plus.org/en-US/guide/migration.html) | Element UI → Plus；兼容模式注意点 |

### 2.2 业界可复用做法

| 做法 | 要点 |
|---|---|
| 先升 Vue 2.7 | 缩小与 Vue3 的语法/心智差距（过渡台阶，不长期停留） |
| 先迁 Vite（仍 Vue2）再迁 Vue3 | 365talents 等案例：Vue3 生态对 Vite 文档更全；符合「构建工具必须同升」 |
| 依赖双版本/可共存优先 | 能先升到「同时支持 Vue2/3」的插件版本，再换引擎 |
| UI 库单独留「大步」窗口 | Element/Vuetify 类迁移难拆，需整块时间 |
| E2E/冒烟测试价值最高 | 组件单测迁移痛；路由级 smoke 更保值 |
| 范围锁死 | 「Vue2 语法跑在 Vue3 引擎」先交付；Composition API 另立项 |

参考：[365talents 迁移复盘](https://inside.365talents.com/blog/migration-vue-2-3/)、[Legacy 迁移教训](https://www.nazarboyko.com/articles/vue-3-migration-lessons-from-legacy-codebases)。

### 2.3 开源工具 / 仓库

| 工具 | 星级量级（调研时） | 用途 | 注意 |
|---|---|---|---|
| [`@vue/compat`](https://www.npmjs.com/package/@vue/compat)（vuejs/core） | 官方 | 仓内兼容桥 | 必须设摘除日期，忌长期滞留 |
| [`vuejs/vue-codemod`](https://github.com/vuejs/vue-codemod) | ~300★ | 批量改 filters/`$listeners`/slot 等 | 辅助，不是一键完工 |
| [`originjs/webpack-to-vite`](https://github.com/originjs/webpack-to-vite) | ~750★ | Vue CLI/Webpack → Vite 脚手架转换 | 生成后仍需人工验收 |
| [`thx/gogocode`](https://github.com/thx/gogocode) + [`gogocode-plugin-element`](https://github.com/thx/gogocode/tree/main/packages/gogocode-plugin-element) | ~6k★ | Element UI → Element Plus AST 迁移 | Element Plus 官方推荐；需回归 |
| [`UnrefinedBrain/vue-metamorph`](https://github.com/UnrefinedBrain/vue-metamorph) 等 | 社区 | AST codemod 框架 | 按需评估成熟度 |
| `create-vue` | 官方脚手架 | 对照「干净 Vue3 基线」 | 适合新仓或对照配置，不替代存量改造 |

---

## 3. 针对你们场景的选型（决策树）

前提：多仓、栈不一、**切流偏好单仓大爆炸**、升级范围含 UI/TS/测试、**构建工具必须跟着升**、无额外红线。

### 3.1 推荐默认路径（大多数仓）

**「单仓大爆炸切流 + 仓内分步改造」**

1. **仓画像**（半天～1 天）：构建（CLI/Webpack/Vite）、Router/Vuex、UI 库、TS、测试、阻塞插件清单  
2. **准备台阶**（可合并进升级分支）：升到 Vue 2.7；能先迁 Vite 则先迁（`vite-plugin-vue2` 仅作过渡）；依赖审计  
3. **升级分支（大爆炸准备）**：Vue3 + `@vue/compat` → 清编译/运行时 warning → Router4 → Vuex4 或并行引入 Pinia → UI 大步（如 Element Plus）→ 测试工具链 → **摘 compat**  
4. **切流**：整仓一次上线；回滚方案=回退该仓发布  
5. **后续**：Composition API / `<script setup>` 按功能迭代慢慢做，不绑本次

### 3.2 何时改用别的路径

| 仓画像信号 | 改用路径 |
|---|---|
| 组件少、无重型 UI、依赖已 Vue3 就绪 | 可弱化 compat，直接 Vue3 标准构建（仍建议短分支验证） |
| Element UI / Vuetify / 大量私有 Vue2 插件 | 仍单仓切流，但 **UI/插件单独排「大步周」**；compat 期间注意 Element Plus 可能需 `compatConfig` MODE 3 |
| 已是微前端宿主/子应用 | 切流仍可按应用大爆炸；应用间可用微前端做**仓间**并存（不是你们默认首选，仅当业务不能停时） |
| 仓库巨大且无法冻结功能 | 下调「大爆炸纯度」：长期 feature 分支 + 频繁 rebase，或阶段性允许 `@vue/compat` 上预发（仍设硬截止日期） |

### 3.3 多仓推进顺序（建议）

1. **试点**：小仓、依赖少、有 E2E/冒烟、业务窗口好  
2. **样板仓**：含典型 UI 库的中型仓，产出可复制 runbook  
3. **批量**：按阻塞依赖相似度分组（同 Element / 同 Vuex 形态 / 同构建）一起推  
4. **硬骨头最后**：私有组件库、无维护插件、测试薄弱的大仓

### 3.4 明确不建议

- 同一次 PR 里：换引擎 + 全量 Composition API + 业务大重构  
- 长期生产依赖 `@vue/compat`  
- 构建仍停在旧 Webpack/Vue CLI，只升 `vue@3`（与「构建必须同升」及官方推荐相悖）  
- 未做依赖审计就开干（插件断更通常才是真正 blockers）

---

## 4. 一仓内建议阶段（可直接当 checklist 骨架）

| 阶段 | 产出 |
|---|---|
| P0 画像 | 依赖矩阵：必须同升 / 可 Vuex4 过渡 / 需替换 / 无维护 |
| P1 工具链 | Vite 就绪；Volar；eslint-plugin-vue（Vue3 rules）；Node 版本对齐 |
| P2 桥接 | `@vue/compat` + warning 清单 backlog |
| P3 生态 | Router4；Store（Vuex4→Pinia）；i18n 等 |
| P4 UI | Element Plus（gogocode）或对应 Vue3 UI；视觉/交互回归 |
| P5 测试 | `@vue/test-utils` v2；保留/加强 E2E smoke |
| P6 摘桥 | 去掉 compat alias；标准 `vue` 构建绿 |
| P7 切流 | 单仓发布；监控与回滚 |

---

## 5. 已落地 Skill

影响面分析（只分析、不实施）：  
[`vue2-to-vue3-upgrade-impact-analysis/SKILL.md`](../vue2-to-vue3-upgrade-impact-analysis/SKILL.md)

- 使用说明：[`vue2-to-vue3-upgrade-impact-analysis-usage.md`](./vue2-to-vue3-upgrade-impact-analysis-usage.md)  
- 可选 delivery 软挂载：[`vue2-to-vue3-upgrade-delivery-usage.md`](./vue2-to-vue3-upgrade-delivery-usage.md)

## 6. 下一步（可选）

- 对某一真实仓库跑 `profile_inventory.py` + 人工确认队列，验证决策树是否缺轴  


---

## 7. 主要来源

- https://v3-migration.vuejs.org/  
- https://v3-migration.vuejs.org/migration-build  
- https://v3-migration.vuejs.org/recommendations  
- https://router.vuejs.org/guide/migration/  
- https://element-plus.org/en-US/guide/migration.html  
- https://inside.365talents.com/blog/migration-vue-2-3/  
- https://www.nazarboyko.com/articles/vue-3-migration-lessons-from-legacy-codebases  
- https://github.com/originjs/webpack-to-vite  
- https://github.com/thx/gogocode  
- https://github.com/vuejs/vue-codemod  
