# hiapm AngularJS Host Migration Appendix

> This appendix is project-specific. Use `angularjs-to-vue3-host-migration-playbook.md` for orchestration and `angularjs-to-vue3-host-migration/references/hosted-vue3-migration-method.md` for generic gates. Consult this file only for hiapm -> apmweb3 or when a maintainer explicitly asks for these traps.

## 状态来源

本附录只保存稳定的误判形状，不保存“今天哪些页已切、哪个工作区未提交”之类会变化的状态。

- 当前 HEAD、T16 批准/切换结果、工作区未提交和逐页进度，以 `<PROJECT_STATUS_SOURCE>` 为准。
- `<PROJECT_STATUS_SOURCE>` 未配置时，按当前 A/B revision 重新取证；不得把本附录当状态日报。
- playbook 负责编排，附录不重复 Wave；playbook 若需要项目页名或常量，只引用本附录。

## 身份误判

- **能打开 HTML ≠ 命中源 hash。** `taskReport.html`、`deliverableReport.html`、`fieldConfig.html`、`projectInformation.html` 都只能作为候选；必须分别核对源 URL/hash/query、mounted wrapper、身份字段和可达入口。
- **Tab 参数 ≠ hash 合同。** `tab=basic` 不得冒充 `#!/package`；association 必须保留源证据要求的 `associate=1`。六个页签与独立 hash 清单分开阅读。
- **抽屉 ≠ 独立详情页。** `TaskDetailDrawer` 不等于 `taskDetail.do`；缺少 `taskId` 时不得用项目码或父实体 ID 顶替。
- **父壳 ≠ 真业务页。** `create.do` 若只做鉴权/Header 并挂载 Vue2 `createproject.html`，身份记为 `parent-shell`，不得用 AngularJS 迁移流程为父壳新建 MPA。Vue2 子页交给对应 Vue2 迁移流程。
- **遗留 hash ≠ 当前升级源。** `plan.do#!/detail` 只有在当前 A/SIT 仍挂载它时才是合同；若当前落点已是 `milestone.html`，旧 hash 只作历史线索。
- **产品日落 ≠ 待迁页。** `require/manage.do` 这类仅挂仓外系统且已日落的入口，必须取得 `do-not-migrate`/`deprecated-removed` 决策，不建 dest。
- **壳内 pane 不自动另建 UNIT。** 子系统/模板等 pane 没有独立 URL、身份或切换边界时，归属 `projectBasicInfo` 壳 UNIT 的独立 MATRIX 分组和 verify 结论，不单造 T16。

## 完成态误判

- **archive 过的页面不得重新塞入后续批次。** 新发现偏差开新 change；具体已 archive 名单以 `<PROJECT_STATUS_SOURCE>` 为准。
- **接线但隐藏仍是 `wired-hidden`。** `taskReport` 即使 MPA 可打开，只要父 Tab 仍由 `v-if="false"`、权限或 feature flag 隐藏，就不能记 `already-migrated`。
- **原生页也可能不是本合同。** `fieldConfig` / `projectInformation` 在 develop 中存在，不证明对应 A hash 已迁；`fieldConfig.html` 与 `#!/field/field`、`projectInformation.html` 与其它 tab/hash 必须逐一核对。
- **orphan MPA 不等于迁移。** 交付件原生入口若没有 A 的 DMH 合同或可达路由证据，仍按 `orphan-mpa` 处理。
- **顶栏保留 A 可以是完成态。** 经批准的 `iframe-keep-A` + `keepOrigin: true` 可作为最终边界；不要默认 native 重写顶栏。

## 出站与环境锁

- T16 按 UNIT/成员独立记录，当前已切、永不切、环境锁、可备切名单均从 `<PROJECT_STATUS_SOURCE>` 读取；不得在附录中长期双写。
- `never-switch` 用于明确决定不切的详情、仓外业务或保留边界，并附决策证据。
- `environment-locked` 用于 B 代码无法消除的外部依赖，例如 TTMS 根路径、仓外 CTMS、指定端口的 HIAMS；必须记录外部 owner 和解锁条件。
- `dest-built-unwired` 仍只描述 A/B 接线现状；不要用它替代上述切换处置。
- 邮件体、外链和用户可复制链接必须证明是否保留绝对 `rootPath`，不能机械套应用内剥源函数。

## 对照面与宿主集成

- hiapm -> apmweb3 的默认候选对照面是 `dest + host Header`，不是 SIT 独立弹窗；仍须把实际 chrome、viewport、登录态和当前 revision 写入 `<COMPARISON_SURFACE>` 后才成立。
- Header 历史上使用过 `z-index:999`，modal/full-screen 修复曾需要更高层级；`1010` 只是本项目已见值，不是永久常量。每次以当前 CSS/runtime 取证，并用 `elementFromPoint` 或等价检查确认命中层。
- parity 报告中的宿主顶栏链接差异、401、依赖端口不可达、SIT title 前缀、viewport 差异和 Vue feature-flag warning，先分别归类为 `host-chrome`、`environment-auth`、`environment-service` 或 `toolchain-warning`，不得直接算页体失败。
- TitleBar 语言跟切必须核对当前 `#switch-lang` 事件及 payload 形状；历史实现要求 Event 对象。写死中文、只在启动时读一次 `localStorage.lang`、跨域 iframe 无法绑定，都要在 `<HOST_INTEGRATION>` 单列。
- 日期等公共控件先核对宿主现有等价件；`HostDatePanel` 是已见实例，不是通用强制组件。
- 模块导出验证最终 Excel 文件名、`.xlsx`、blob 和有效文件 MIME；接口 request `Content-Type=multipart/form-data` 不是下载文件 MIME。
- `TaskTemplatePane.vue` 等并行占用文件只有在当前 ownership/freeze 证据仍成立时才冻结；记录 owner 和解冻条件，不把历史冻结永久化。

## 残差政策

- 源公式已经由代码和其它真实样本证明、但稀有真值样本不可达时，不得补假数据。将对应行记为 residual，写明受影响合同、owner、验证条件和是否获准不阻塞。
- CSS 闭包必须覆盖 `font-size: 0`、sprite/icon size、空态图和 runtime hide class；DOM 存在但不可见不算通过。
- 项目菜单阅读顺序：左栏按当前运行时从上到下；项目信息页签按当前壳从左到右；独立 hash 行不得并入页签表。具体列表始终从当前代码和 `<PROJECT_STATUS_SOURCE>` 刷新。
