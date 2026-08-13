# Vue2 页面迁入 Vue3 Host：精简编排方案

> 适用前提：保持当前所有 Skill 不改动。  
> 使用方式：每个 Wave 使用一个新会话；Wave 3 的 Delivery 阶段在同一会话内自动接力。

## 1. 一次性配置

先保存配置文件：

```text
D:\Hzhao\AI_Test\migration-artifacts\table-inline-edit\migration-run-config.json
```

```json
{
  "source_root": "D:\\Hzhao\\AI_Test\\Vue2_Test",
  "host_root": "D:\\Hzhao\\AI_Test\\Vue3_Test",
  "migration_unit": {
    "id": "table-inline-edit",
    "source_route": "/table/inline-edit-table",
    "source_entry": "src/views/table/inline-edit-table.vue",
    "host_route": "/function/inline-edit-table",
    "host_html": "D:\\Hzhao\\AI_Test\\Vue3_Test\\index.html",
    "host_mount_hint": "由 Agent 根据 B 的真实结构提案"
  },
  "artifact_root": "D:\\Hzhao\\AI_Test\\migration-artifacts\\table-inline-edit",
  "openspec_change_id": "migrate-table-inline-edit-to-vue3",
  "constraints": {
    "source_mutation": "forbidden",
    "host_shell": "host-native",
    "content_parity": "strict",
    "visual": "required",
    "typescript": "required",
    "options_api": "allowed",
    "vue2_and_compat_in_host": "forbidden",
    "new_features": "forbidden",
    "keep_legacy_fallback": true
  }
}
```

该文件只保存用户输入。动态 revision、digest、批准和任务状态由相应 Skill 生成并持久化，不需要手工回填。

## 2. Wave 1：摸底与迁移图纸

在新会话中复制：

```text
读取配置：
D:\Hzhao\AI_Test\migration-artifacts\table-inline-edit\migration-run-config.json

使用 /migrate-vue2-pages-to-vue3-host，依次执行 assess 和 design。

A 只读，B 本阶段不改应用代码；证据写入 artifact_root。
B 壳保持 host-native，迁入内容 strict parity，visual=required，
保留可演练的 legacy/iframe fallback；只修缺陷，不开发新功能。

B 的既有未提交内容属于用户改动，只检查碰撞，不覆盖、不丢弃，
也不视为本 Wave 的实施成果。

页面闭包、双仓 revision、运行时、依赖、视觉、回滚和证据校验
全部按 Skill 当前契约执行。

结束时给出：
- domain packet path 与 canonical digest；
- source_revision 与 host_revision；
- 页面闭包包名单；
- blockers 与 design readiness。
```

## 3. Wave 2：页面闭包依赖差分

等待 Wave 1 完成，在新会话中复制：

```text
读取同一 migration-run-config.json，以及 artifact_root 中当前有效的
vue-migration-domain/v1 packet。

先校验 packet digest 和当前 A/B revision；stale 时停止并要求重跑 Wave 1。

使用 /frontend-dependency-upgrade-impact-analysis，
mode=migration-demand-diff。

source A 只读，implementation target 为 B。
自动使用 domain packet 的页面闭包包名单，不扫描 A 整个 package.json。
output-dir 使用：
<artifact_root>\evidence\frontend-dependency-upgrade\

只分析、不安装、不修改应用代码；禁止把 Vue2 或 @vue/compat 引入 B。
依赖确认、decision file、报告重生成和 finalize review
全部按 Skill 当前契约完成，直到 analysis_status=complete。

结束时给出：
- dependency summary path 与 digest；
- demand diff report path 与 digest；
- decision file（若有）；
- batch_implementation_gate 状态及 frozen 的解除条件。
```

只有 Wave 1 packet 明确证明页面闭包无需独立依赖决策时，才可跳过本 Wave。

## 4. Wave 3：Delivery 链式实施与验收

在新会话中复制。Frame、Plan、Execute 不再拆成不同会话：

```text
读取同一 migration-run-config.json、当前有效 domain packet，
以及 dependency summary/report（若 Wave 2 适用）。

校验所有 path、digest 和当前 A/B revision；stale 时停止，
不从聊天记忆恢复旧结论。

从 /delivery-frame-spec 开始。
本任务固定 High，visual=required；A 只读，B 是唯一代码 mutation target。
B 壳 host-native，迁入内容 strict parity，保留 legacy fallback，只修缺陷。

领域与依赖证据只作为 path+digest external_artifacts 引入。
把当前双仓 revision 纳入规格和实施闸门。

B 中既有 staged、unstaged、untracked 内容全部属于用户改动，
必须保护并检查碰撞，不得覆盖、丢弃、stash 或冒充本轮成果。

如果 OpenSpec 尚未初始化，按 Delivery 硬前提协议请求初始化授权，
不得创建替代状态源。

规格批准后，按 Delivery Family 当前契约在同一会话自动接力：
delivery-plan-tasks → delivery-execute-verify。

计划覆盖挂载、页面闭包适配、feature switch、行为测试、
视觉/表格验证、legacy fallback 演练和回滚，并使用纵向切片。

实施 go 必须绑定当前 artifact revision 与当前双仓 revision。
delivery-execute-verify 是唯一代码修改 owner，只修改 B 的批准范围。

OpenSpec、handoff、Node/lock、TDD、G1–G9、视觉证据、
独立审查和 Fresh Verification 全部按各 Skill 当前契约执行。

达到 overall_status=verified 后停止：不 archive、不执行 Git 操作，
不部署、不切流、不移除 fallback、不关闭 A。

结束时给出：
- OpenSpec change 与最新 handoff.json 路径；
- artifact revision 与实施绑定的双仓 revision；
- 实施后的 host revision；
- Fresh Verification、独立审查和 residual risks；
- next_action。
```

## 5. Wave 4：领域最终复核

等待 Wave 3 达到 `overall_status=verified`，在新会话中复制：

```text
读取同一 migration-run-config.json、当前 domain packet，以及：
<host_root>\openspec\changes\<openspec_change_id>\handoff.json

校验 Delivery 已达到 overall_status=verified，并重新校验当前 A/B revision。
若仓库或工件在 verified 后变化，停止并返回受影响的 Delivery 阶段，
不得沿用旧验证。

使用 /migrate-vue2-pages-to-vue3-host，mode=verify。

按当前双仓 revision 只做领域复核，不重复实施，
不修改应用代码、依赖、lock、fixture、runtime 或 feature switch。

功能、错误路径、权限、URL、视觉/表格、runtime/build、
rollback 和 legacy fallback 全部按 Skill 当前契约重新核验。

若必须修改 B，输出 discovery backflow，退出 verify，
交还 Delivery 并重新通过受影响闸门。

只有当前 revision 下同时满足：
- Delivery overall_status=verified；
- Domain verification.status=pass；
才宣告“本次迁移验证完成”。

不得宣称已部署、已切流、已关闭 A 或已移除 fallback。
```

## 6. Wave 3 中断恢复

仅在 Delivery 会话意外中断时使用：

```text
读取同一 migration-run-config.json，并从以下快照恢复：
<host_root>\openspec\changes\<openspec_change_id>\handoff.json

校验 handoff、当前 repo/worktree revision 和 artifact revision，
再与 OpenSpec 权威工件比较。

stale 时以 OpenSpec 为准恢复并重跑受影响 gate；
不从聊天记忆补状态，未持久化的批准视为不存在。

根据 handoff.stage、next_skill 或 next_action 恢复正确阶段。
仍有效且条件未变化的已记录决定不重复询问。
```

## 7. 完成判定

```text
有效的领域设计
+ 已完成的依赖决策（适用时）
+ Delivery overall_status=verified
+ Domain verification.status=pass
+ 两者均绑定当前 revision
+ legacy fallback 可演练
+ 无 blocking residual
= 本次迁移验证完成
```

OpenSpec archive、Git 操作、部署、切流、观察期结束、移除 fallback 和关闭 A 均需另行授权，不属于本编排的自动步骤。
