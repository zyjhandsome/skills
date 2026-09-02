# hiapm AngularJS Host Migration Appendix

> This appendix is project-specific. Use the generic `angularjs-to-vue3-host-migration-playbook.md` for orchestration rules, and consult this file only when the A/B pair is hiapm -> apmweb3 or a maintainer explicitly asks for the hiapm traps.

## 实战反例钉子

这些钉子只记录 hiapm -> apmweb3 已踩过的误判形状。不要把这里的页面名当成通用迁移规则。

- Home / 看板已 archive 后不要再填新 UNIT；不要用 `workbench` / `projectProgress` 文件名冒充首页/看板。
- `taskReport.html`、`deliverableReport.html`、`fieldConfig.html`、`projectInformation.html` 能打开，不等于对应 A hash 已迁。
- `taskReport` 接线但父级 `v-if="false"` 时是 `wired-hidden`，不能 archive 成 `already-migrated`。
- `tab=package` / `PackagePane` 已建但 T16 未授权时仍是 `dest-built-unwired`；`tab=basic` 不能冒充 `#!/package`。
- `TaskDetailDrawer` 不是 `taskDetail.do` 独立页；详情 URL 缺 `taskId` 时不能用项目码顶替。
- 顶栏 `keepOrigin: true` 挂 A `top_bar.do` 可以是完成态；不要把 native 顶栏当目标。
- 邮件体、外链、用户可复制链接要先证明是否必须保留绝对 `rootPath`，不要机械套应用内剥源函数。
