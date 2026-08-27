# Vue2 Pages → Vue3 Host Migration × Delivery — 使用说明

> 受众：要把 `vue2-pages-to-vue3-host-migration` 和 `delivery-*` 组合使用的人。  
> **唯一顺序以粘贴剧本为准：** [`vue2-pages-to-vue3-host-migration-playbook.md`](./vue2-pages-to-vue3-host-migration-playbook.md)。  
> 本文件只解释解耦原则和交接字段。  
> `vue2-pages-to-vue3-host-migration` Skill **正文不依赖、不引用** `delivery-*` / OpenSpec。

---

## 0. 已作废（不要再用）

下列旧顺序和旁路已经作废，与当前剧本冲突：

- assess + design 先于建 change / Frame
- Frame 在摸底前做规格批准
- 主路径插入 `frontend-dependency-upgrade-impact-analysis`
- 主路径插入 `frontend-ui-stack-visual-parity` 做人眼残差修复
- migrate `execute` 或「不使用 Delivery 时由 migrate 改 B」
- `docs/vue2-page-migration-orchestration-latest.md`（已改名为剧本，不要再引用 latest）

---

## 1. 解耦原则

| 层 | 职责 |
|---|---|
| `vue2-pages-to-vue3-host-migration` | 跨仓页面迁移领域：assess / design / verify；产出 `vue-migration-domain/v1`、`visual-parity-evidence/v1`、`runtime-compatibility-evidence/v1`。没有 execute mode，不改应用代码 |
| `delivery-*` | 定框 / 计划 / 实施闸门 / Fresh Verification / G9 自有视觉记录。`delivery-execute-verify` 是唯一代码 mutation owner |
| OpenSpec change | 生命周期与状态真相（若团队使用） |
| 粘贴剧本 | 按名组合上述 Skill；不改任何 Skill 内部 schema |

- 领域 Skill 与 Delivery family **互不调用**；剧本可以按名排序。剧本启用 Delivery 的**会话停点覆盖**，每步一个新会话。
- Domain `verification=pass` **不等于** Delivery `verified`，更不等于生产切流或关停源仓 A。
- `implementation_authorization` 只是对外部批准的引用；批准权威在用户 / Delivery 闸门。implementation go 必须显式携带并绑定 `source_revision` + `host_revision`、批准人、时间、范围、验证义务与回退条件。

---

## 2. 唯一挂载顺序

```text
Wave 1  建 change（无规格闸门）
  → Wave 2  migrate assess
  → Wave 3  migrate design
  → Wave 4  Frame 规格批准
  → Wave 5  Delivery Plan go
  → Wave 6  Delivery Execute
  → Wave 7  migrate verify
```

跨仓页面迁移固定 High；单页闭包只用于收窄工件与任务深度，不降低闸门强度。

---

## 3. 交接时建议携带的事实（由调用方复制）

从 migrate domain packet / 视觉证据中摘：

- `packet` 路径与 `packet_digest`
- `source_revision` / `host_revision`
- `migration_unit.id`、source entry、host HTML/entry
- `runtime_evidence` / `visual_evidence` 路径与 digest（含 `visual-migration-contract/v1`）
- `implementation_authorization` 引用（若已有）
- `rollback` 状态与 iframe 回退开关位置
- blockers / decisions / non_goals

Delivery 侧：

- 自行重算 `quality_profiles`（不得要求 migrate schema 进入 Delivery 状态）
- G9 用 `delivery-visual-evidence/v1`；migrate 视觉 JSON 仅作 `external_artifacts` path/digest
- 禁改 A；保留 iframe 回退直至 observation / release-owner 条件满足
- 只由 `delivery-execute-verify` 修改 B；migrate 只用 `verify` 刷新领域证据

---

## 4. 不使用 Delivery 时

仍只用 migrate 的 assess → design → verify。改代码不在本 Skill 内；调用方自行实施后再跑 verify。
