# Treatment Ladder（治理处置阶梯）

本技能分析-only：只推荐处置，不改 `pom` / Gradle、不执行 exclusion、不换组件。
处置阶梯与 Owner 版本权威阶梯**正交**——先选「做什么」，再选「版本归谁管」。

## 枚举 `recommended_treatment`

| 值 | 含义 | 典型适用 |
|---|---|---|
| `remove` | 删除无用直接依赖声明 | direct + `usage_status=unused` |
| `upgrade-self` | 升级该 GAV 自身到目标 GA | direct、正在使用 |
| `upgrade-owner` | 升主 Owner（BOM/parent/属性） | Boot/BOM 托管族 |
| `upgrade-introducer` | 升级引入该传递依赖的上层直接依赖 | transitive；上层新版本已带安全传递版本 |
| `move-self` / `move-owner` / `move-introducer` | 与对应 `upgrade-*` 权限/证据相同，但用于 `direction=downgrade` 或 `same`，避免把降级写成 upgrade | 显式降级或同版重对齐 |
| `exclude` | 排除未触达的传递依赖 | transitive + 有「业务未触达」证据 |
| `force-align` | dependencyManagement / force 强制对齐 | 上层滞后且不可等发版 |
| `replace-component` | 替换已死/无法修复的组件坐标 | dead project / 不可修 0-day |
| `replace-introducer` | 替换引入有洞传递依赖的上层直接依赖 | 排除与强制对齐皆不可行 |
| `choose-alternative` | 请求目标不存在；在人审队列中选择**已验证的同 GAV 其他版本** | 同坐标换版本（404→可达 GA） |
| `no-viable-path` | 分析认定暂无可行处置（≠ 人工 `defer`） | 无已验证候选、证据不足或风险不可接受 |

## Direct 路径（最优 → 兜底）

1. **`remove`** — 安全的 `dependency:analyze-only` 与调用点、配置/SPI、运行职责证据一致显示 unused；`ambiguous` 不得默认 remove。
   **表里写了 `from→to` 但证据为 unused：** 仍默认 `recommended_treatment=remove`，队列 `ready`，选项以 `remove` / `defer` / `other` 为主（可附注「表请求升级，分析建议删除」）。**不要**默认问 `proceed:…:to`；若用户坚持升级，用 `other` 进入下一波再改处置。
2. **`upgrade-self` / `upgrade-owner`**（上移）或 **`move-self` / `move-owner`**（降级/同版重对齐）— 在用则跟安全基线；Boot 托管优先 owner 处置。目标必须是 **GA/Release**。
3. **`replace-component`** — 停维且无法修洞；给出 1–3 个替代候选，**须人工逐单元确认**后才可 `proceed`/`replace:…`。

请求目标不存在时的处置决策树（保留原请求为 `requested_*`，不得自动替换）：

| 已验证候选 | `recommended_treatment` | 队列选项 |
|---|---|---|
| 同 GAV 其他 GA 版本 | `choose-alternative` | `proceed:g:a:v` / `defer` / `other` |
| 换坐标 / 包名迁移（如 lang→lang3） | `replace-component`（或传递侧 `replace-introducer`） | `replace:g:a[:v]` / `defer` / `other` |
| 零候选 / 证据不可达 | `no-viable-path` | 队列 **`blocked`**（仅重述目标 / `other`；不得 `defer`/`proceed`） |

存在性 `no`/`unknown` 且无已验证替代 → 永远 `blocked`，不要写成 `ready`/`pending`/`defer`。
`no-viable-path` **一律**队列 `blocked`（重述目标 / `other`），不得 `ready`+`defer`。
**不要**把清单处置写成 `defer`——`defer` 只保留给人在 `ready`/`pending` 行上的确认选项。
## Transitive 路径（最优 → 断腕）

升降级对称：上移用 `upgrade-*`，下移/同版重对齐用 `move-*`。叶子「简单钉版本」不是默认首选。

1. **`exclude`** — 仅当有证据表明业务未触达该传递分支。须在决策记录写明：排除后必做核心链路回归，否则可能 `ClassNotFoundException` / `NoClassDefFoundError`。验证成本过高 → 放弃本档，进入下一档。
2. **`upgrade-introducer` / `move-introducer`** — 工程默认最优：查 tree 找到 introducer，查其是否有能把传递依赖收敛到目标版的 GA（升或降列车/上层坐标）；有则推荐动 introducer，而不是先钉传递叶子。
3. **`force-align`** — 上层无法及时收敛时的干预；等同 Owner 阶梯的 per-GAV pin / force，须完整 Decision Record + 破例条件。显式降级的传递目标同样走此档，不要伪装成 `move-self`。
4. **`replace-introducer` / `replace-component`** — 排除与强制对齐都会崩、或存在更好的二合一 starter / 换栈坐标 → 替换上层或整族；须 1–3 个已验证候选供人选择。
5. **原生改造** — 调用面可去依赖时记入路径菜单（通常经确认词 `other` 进入下波），见 `next-action-choice-menus.md` §B。

传递单元出确认问题时，必须附路径选项菜单（introducer / force-align / 换 starter 或换栈 / 原生改造），不得只给「钉叶子版 proceed」。

## 与 Owner 阶梯的关系

| 处置 | 通常落在 Owner 档 |
|---|---|
| `upgrade-owner` / `move-owner` | 1–3（bump / property / family BOM） |
| `upgrade-self` / `move-self` / `upgrade-introducer` / `move-introducer` | 多为 direct / introducer 声明变更（实施期） |
| `force-align` | 4（per-GAV pin） |
| `exclude` | 5（exclusion；或仅 exclusion 无补声明） |
| `remove` / `replace-*` | 超出「升版本」；记入迁移路径选项 |

不得因为「想 pin 一个传递包」而跳过 Direct/Transitive 处置阶梯的更优档。
不得因为 Owner 阶梯把 exclusion 放在第 5 档，就禁止在「未触达」证据成立时推荐 `exclude`。

## 必填辅助字段

| 字段 | 何时必填 |
|---|---|
| `usage_status` | direct：`used` / `unused` / `ambiguous`（须引用 analyze 或调用点证据） |
| `introducer_gav` | `owner_class=transitive` 或处置为 `upgrade-introducer` / `exclude` / `replace-introducer` |
| `introducer_upgrade_available` | 评估过 `upgrade-introducer` 时：`yes` / `no` / `unknown` + 版本与依据 |
| `replacement_candidates` | `replace-component` / `replace-introducer`：1–3 个候选坐标 + 维护信号 |
| `alternative_candidates` | `choose-alternative`：1–3 个 `g:a:v` + `same-gav` / `replacement` + 独立存在性证据 |
| `target_channel` | 有 `target_to` 时：`ga` / `non-ga` |

## GA-only

生产目标禁止 Beta / RC / Snapshot / Milestone（大小写不敏感；含 `.Alpha`、`.Beta`、`.CR`、`-SNAPSHOT` 等）。  
`target_channel=non-ga` → 行不得进 `ready`（视为 `blocked`），除非用户**显式**允许非 GA。  
缺失目标时不要发明版本；CVE 入口须先查官方修复区间再提问（见 `human-confirmation-gates.md`）。

## 决策单元（确认粒度）

Canonical（与 `human-confirmation-gates.md` 一致）：一个确认单元 =
同一 `authority_layer × boot_line × build_variant × bounded batch_scope`
× 同一 `recommended_treatment` × 同一目标版本（或同一替换候选集）× 一个 **family**。  
跨族、不同变体/范围、不同处置、不同目标 → 拆成多个单元；每人每个单元一条显式答复。
