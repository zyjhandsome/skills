# Migrate Vue2 Pages → Vue3 Host × Delivery — 使用说明（可选软挂载）

> 受众：希望把 `migrate-vue2-pages-to-vue3-host` 挂到 `delivery-*` 脊柱上的编排者。  
> **本文件是可选软挂载说明。**  
> `migrate-vue2-pages-to-vue3-host` Skill **正文不依赖、不引用** `delivery-*` / OpenSpec。

---

## 0. 解耦原则

| 层 | 职责 |
|---|---|
| `migrate-vue2-pages-to-vue3-host` | 跨仓页面迁移领域：assess / design / execute / verify；产出 `vue-migration-domain/v1`、`visual-parity-evidence/v1`、`runtime-compatibility-evidence/v1` |
| `delivery-*` | 定框 / 计划 / 实施闸门 / Fresh Verification / G9 自有视觉记录 |
| OpenSpec change | 生命周期与状态真相（若团队使用） |

- 领域 Skill 与 Delivery family **互不调用**；Delivery family 内部按 handoff 链式接力。编排者只传摘要路径 + digest。  
- Domain `verification=pass` **不等于** Delivery `verified`，更不等于生产切流或关停源仓 A。  
- `implementation_authorization` 只是对外部批准的引用；批准权威在用户 / Delivery 闸门。Delivery 的单一
  `artifact_revision` 或 `repo_head` 不能自动映射成该授权：implementation go 必须显式携带并绑定
  `source_revision`、`host_revision`、批准人、时间、范围、验证义务与回退条件，编排者再逐字段复制。

---

## 1. 建议挂载顺序（版 B / B-轻量）

```text
migrate-vue2… assess + design（只读；产出 revision-bound domain packet）
        │
        ├─ frontend-dependency-upgrade-impact-analysis（可选；migration-demand-diff）
        ▼
delivery-frame-spec（High：migration 红线；实施仓=B；禁改 A；visual=required）
        │
        ▼
delivery-plan-tasks（吃 packet/digest；纵向切片 + 视觉/表格/回退验证行）
        │ 用户 implementation go（绑定 revision）
        ▼
delivery-execute-verify（集成路线唯一代码 mutation owner，只改 B）
        │
        ├─ Delivery：tasks + G9 `delivery-visual-evidence/v1`
        ▼
migrate-vue2… verify（不重复实施；按新 revision 刷新领域证据）
```

Delivery 实施后 `host_revision` 会变化：先将旧 implementation authorization 标为 stale，
再以当前 A/B revision 执行纯只读 verify。只读 verify 不需要新的实施授权；若验证过程需要改代码、
依赖、fixture、runtime 或 feature switch，则必须退出 verify，另取绑定当前双 revision 的实施授权。

跨仓页面迁移命中 Delivery 的 migration 红线，Frame 固定走 High + plan；
单页闭包只用于收窄工件与任务深度，不降低闸门强度。若未来仅把“数据迁移”
定义为红线，必须先同步修改 `delivery-frame-spec` 的权威路由规则与负例测试。

---

## 2. 交接时建议携带的事实（由调用方复制）

从 migrate domain packet / 视觉证据中摘：

- `packet` 路径与 `packet_digest`
- `source_revision` / `host_revision`
- `migration_unit.id`、source entry、host HTML/entry
- `runtime_evidence` / `visual_evidence` 路径与 digest（含 `visual-migration-contract/v1`）
- `implementation_authorization` 引用（若已有）
- `rollback` 状态与 iframe 回退开关位置
- blockers / decisions / non_goals（Options API 允许、禁 Composition 全量重写、禁改 A 壳等）

Delivery 侧：

- 自行重算 `quality_profiles`（不得要求 migrate schema 进入 Delivery 状态）  
- G9 用 `delivery-visual-evidence/v1`；migrate 视觉 JSON 仅作 `external_artifacts` path/digest  
- 禁改 A；保留 iframe 回退直至 observation / release-owner 条件满足  
- 集成路线由 `delivery-execute-verify` 唯一拥有代码修改；后续 migrate 只用 `verify` 刷新领域证据。

---

## 3. 独立使用

不使用 Delivery 时：直接调用 migrate Skill → assess → design → 用户给出 revision 绑定的 `implementation_authorization` → execute → verify。  
细则见 Skill 正文与 `references/domain-packet-and-lifecycle-interoperability.md`。

---

## 4. 编排提示词

最新四波完整编排见
[`vue2-page-migration-orchestration-latest.md`](./vue2-page-migration-orchestration-latest.md)。
