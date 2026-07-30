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
| `exclude` | 排除未触达的传递依赖 | transitive + 有「业务未触达」证据 |
| `force-align` | dependencyManagement / force 强制对齐 | 上层滞后且不可等发版 |
| `replace-component` | 替换已死/无法修复的组件坐标 | dead project / 不可修 0-day |
| `replace-introducer` | 替换引入有洞传递依赖的上层直接依赖 | 排除与强制对齐皆不可行 |
| `defer` | 暂无可行处置 | 证据不足或风险不可接受 |

## Direct 路径（最优 → 兜底）

1. **`remove`** — `mvn dependency:analyze` / 等价证据显示 unused；`ambiguous` 不得默认 remove。  
   **表里写了 `from→to` 但证据为 unused：** 仍默认 `recommended_treatment=remove`，队列 `ready`，选项以 `remove` / `defer` / `other` 为主（可附注「表请求升级，分析建议删除」）。**不要**默认问 `proceed:…:to`；若用户坚持升级，用 `other` 进入下一波再改处置。
2. **`upgrade-self` 或 `upgrade-owner`** — 在用则跟安全基线；Boot 托管优先 `upgrade-owner`（见 `owner-and-resolution.md`）。目标必须是 **GA/Release**（见下）。
3. **`replace-component`** — 停维且无法修洞；给出 1–3 个替代候选，**须人工逐单元确认**后才可 `proceed`/`replace:…`。

## Transitive 路径（最优 → 断腕）

1. **`exclude`** — 仅当有证据表明业务未触达该传递分支。须在决策记录写明：排除后必做核心链路回归，否则可能 `ClassNotFoundException` / `NoClassDefFoundError`。验证成本过高 → 放弃本档，进入下一档。
2. **`upgrade-introducer`** — 工程默认最优：查 tree 找到 introducer，查其是否有已抬高传递依赖的 GA 新版本；有则推荐升 introducer，而不是先钉传递包。
3. **`force-align`** — 上层滞后时的干预；等同 Owner 阶梯的 per-GAV pin / force，须完整 Decision Record。
4. **`replace-introducer`** — 排除与强制对齐都会崩、且 introducer 长期不修 → 替换上层组件本身。

## 与 Owner 阶梯的关系

| 处置 | 通常落在 Owner 档 |
|---|---|
| `upgrade-owner` | 1–3（bump / property / family BOM） |
| `upgrade-self` / `upgrade-introducer` | 多为 direct / introducer 声明变更（实施期） |
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
| `target_channel` | 有 `target_to` 时：`ga` / `non-ga` |

## GA-only

生产目标禁止 Beta / RC / Snapshot / Milestone（大小写不敏感；含 `.Alpha`、`.Beta`、`.CR`、`-SNAPSHOT` 等）。  
`target_channel=non-ga` → 行不得进 `ready`（视为 `blocked`），除非用户**显式**允许非 GA。  
缺失目标时不要发明版本；CVE 入口须先查官方修复区间再提问（见 `human-confirmation-gates.md`）。

## 决策单元（确认粒度）

一个确认单元 = 同一 `authority_layer × boot_line` 下、同一 `recommended_treatment`、同一目标版本（或同一替换候选集）的 **family**。  
跨族、不同处置、不同目标 → 拆成多个单元；每人每个单元一条显式答复。
