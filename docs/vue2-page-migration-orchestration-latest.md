# Vue2 页面迁入 Vue3 Host：精简编排方案

> 适用前提：保持当前所有 Skill 不改动。  
> **会话边界：** 每个步骤使用一个新会话窗口。步骤之间只通过磁盘交接，禁止同一窗口自动接力下一 Skill。  
> 这是编排覆盖，不是改 Skill：即使 Delivery Family 允许同会话读取下一 `SKILL.md`，本编排也要求阶段结束即停，由用户在新窗口粘贴下一节提示词。

## 0. 会话清单

| 会话 | 步骤 | 停在 |
|---|---|---|
| 1a | migrate `assess` | assessment 完成，packet 已写盘 |
| 1b | migrate `design` | design ready，packet 已写盘 |
| 2 | 依赖差分 | `analysis_status=complete`，或停在当前人闸 |
| 3a | `delivery-frame-spec` | 规格闸门通过，handoff 已写盘 |
| 3b | `delivery-plan-tasks` | 计划就绪；若本窗给出实施 go，写入 handoff 后仍停 |
| 3c | `delivery-execute-verify` | `overall_status=verified` |
| 4 | migrate `verify` | domain verification 结果已写盘 |
| 5b-a / 5b-b / 5b-c | 功能残差 Frame / Plan / Execute | 同 3a / 3b / 3c |
| 5a-A | visual-parity Phase A | 定界包已写盘，等待 go |
| 5a-B | visual-parity Phase B | CSS/配置修复完成 |
| 5c | migrate `verify` | 新 revision 上的领域复核 |

同时有样式和功能残差时：先跑完 5b-a→5b-b→5b-c，再 5a-A→5a-B，最后 5c。不要并行改同一批 B 文件。

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

### 1.1 每个新窗口的恢复协议

任何新会话都先做这一段（可与当步提示词一起粘贴）：

```text
读取：
D:\Hzhao\AI_Test\migration-artifacts\table-inline-edit\migration-run-config.json

只从磁盘恢复状态：
- artifact_root 中当前有效 domain packet（path + digest）
- 依赖 summary/report（若已有）
- visual-summary.json（若已有）
- <host_root>\openspec\changes\<openspec_change_id>\handoff.json（若已有）

校验 path、digest 与当前 A/B revision。
stale 时停止，要求重跑产生该工件的步骤。
不从上一窗口聊天记忆补结论。
未写入磁盘的批准视为不存在。
仍有效且条件未变化的已记录决定不重复询问。

本会话只做用户粘贴的那一个步骤。
完成后停止：不要读取、加载或执行下一 Skill。
结束时给出本步产物路径/digest，以及清单一里的下一步编号。
```

中断后的恢复也用同一协议：以 OpenSpec / 已写盘 artifact 为准，按 `handoff.stage`、`next_skill` 或 `next_action` 打开对应步骤的新窗口，不要在旧窗口里接力。

## 2. Wave 1a：摸底（assess）

新会话。先贴 1.1，再贴：

```text
本会话只做 /migrate-vue2-pages-to-vue3-host mode=assess。
不要进入 design、不要改应用代码。

A 只读；证据写入 artifact_root。
B 壳 host-native，迁入内容 strict parity，visual=required，
保留可演练的 legacy/iframe fallback；只修缺陷，不开发新功能。

B 的既有未提交内容属于用户改动，只检查碰撞，不覆盖、不丢弃。
页面闭包、双仓 revision、运行时、依赖、视觉、回滚和证据校验
全部按 Skill 当前契约执行。

结束时给出：
- domain packet path 与 canonical digest；
- source_revision 与 host_revision；
- 页面闭包包名单；
- blockers。
然后停止。下一步是新窗口的 1b。
```

## 3. Wave 1b：迁移图纸（design）

等 1a 写盘后，新会话。先贴 1.1，再贴：

```text
本会话只做 /migrate-vue2-pages-to-vue3-host mode=design。
不要重做完整 assess，除非 packet 相对当前 A/B revision 已 stale。
不要改应用代码，不要进入 execute。

约束与 1a 相同：A 只读，B 壳 host-native，内容 strict parity，
visual=required，保留 legacy fallback，只修缺陷。

结束时给出：
- 更新后的 packet path 与 digest；
- design readiness；
- blockers。
然后停止。下一步是新窗口的 2（或 packet 证明可跳过依赖差分时直接 3a）。
```

## 4. Wave 2：页面闭包依赖差分

等 1b 完成，新会话。先贴 1.1，再贴：

```text
本会话只做 /frontend-dependency-upgrade-impact-analysis，
mode=migration-demand-diff。
不要安装、不要修改应用代码、不要进入 Delivery。

source A 只读，implementation target 为 B。
自动使用 domain packet 的页面闭包包名单，不扫描 A 整个 package.json。
output-dir 使用：
<artifact_root>\evidence\frontend-dependency-upgrade\

禁止把 Vue2 或 @vue/compat 引入 B。
依赖确认、decision file、报告重生成和 finalize review
全部按 Skill 当前契约执行。

本窗口做到 analysis_status=complete 再停。
若在人闸处关闭窗口：新会话从已写盘的 report/decision file 继续，
禁止重新全量扫描。

结束时给出：
- dependency summary path 与 digest；
- demand diff report path 与 digest；
- decision file（若有）；
- batch_implementation_gate 状态及 frozen 的解除条件。
然后停止。下一步是新窗口的 3a。
```

只有 1b packet 明确证明页面闭包无需独立依赖决策时，才可跳过本会话。

## 5. Wave 3a：Delivery Frame

等 1b（及适用的 2）完成，新会话。先贴 1.1，再贴：

```text
本会话只做 /delivery-frame-spec。
规格闸门通过并写入 handoff.json 后立即停止。
不要读取或执行 delivery-plan-tasks / delivery-execute-verify。

本任务固定 High，visual=required；A 只读，B 是唯一代码 mutation target。
B 壳 host-native，迁入内容 strict parity，保留 legacy fallback，只修缺陷。

领域与依赖证据只作为 path+digest external_artifacts 引入。
把当前双仓 revision 纳入规格闸门。

B 中既有 staged、unstaged、untracked 内容全部属于用户改动，
必须保护并检查碰撞，不得覆盖、丢弃、stash 或冒充本轮成果。

如果 OpenSpec 尚未初始化，按 Delivery 硬前提协议请求初始化授权，
不得创建替代状态源。

结束时给出：
- OpenSpec change 路径；
- handoff.json 路径；
- 规格闸门状态与绑定的双仓 revision。
然后停止。下一步是新窗口的 3b。
```

## 6. Wave 3b：Delivery Plan

等 3a 规格批准且 handoff 已写盘，新会话。先贴 1.1，再贴：

```text
本会话只做 /delivery-plan-tasks。
计划就绪后停止。不要读取或执行 delivery-execute-verify。

从 handoff.json 恢复，校验 artifact revision 与当前 A/B revision。
计划覆盖挂载、页面闭包适配、feature switch、行为测试、
视觉/表格验证、legacy fallback 演练和回滚，并使用纵向切片。

G9 `final_visual_result=pass` 只证明 Delivery 自有视觉记录合格，
不等于迁入内容已肉眼对齐 A。计划里必须留下人眼残差可回流到 Wave 5 的口子。

若用户在本窗口给出实施 go：写入 handoff，绑定当前 artifact revision
与当前双仓 revision，然后仍必须结束本会话。
未持久化的 go 带到下一窗口视为不存在。

结束时给出：
- 更新后的 handoff.json 路径；
- 计划就绪状态；
- 实施 go 是否已落盘。
然后停止。下一步是新窗口的 3c。
```

## 7. Wave 3c：Delivery Execute

等 3b 计划就绪，新会话。先贴 1.1，再贴：

```text
本会话只做 /delivery-execute-verify。
它是本轮唯一代码修改 owner，只修改 B 的批准范围。

从 handoff.json 恢复。
若绑定当前 artifact revision 与当前双仓 revision 的实施 go 未落盘，停止；
回到 3b 或在本提示词末尾显式补写该 go。禁止用聊天记忆补批准。

OpenSpec、handoff、Node/lock、TDD、G1–G9、视觉证据、
独立审查和 Fresh Verification 全部按各 Skill 当前契约执行。

G9 pass 不等于肉眼对齐 A。人眼仍偏时不得宣告迁移完成。

达到 overall_status=verified 后停止：不 archive、不执行 Git 操作，
不部署、不切流、不移除 fallback、不关闭 A。
不要读取 migrate verify。

结束时给出：
- 最新 handoff.json 路径；
- artifact revision 与实施绑定的双仓 revision；
- 实施后的 host revision；
- Fresh Verification、独立审查和 residual risks。
然后停止。下一步是新窗口的 4。
```

## 8. Wave 4：领域最终复核

等 3c 达到 `overall_status=verified`，新会话。先贴 1.1，再贴：

```text
本会话只做 /migrate-vue2-pages-to-vue3-host mode=verify。
不重复实施，不修改应用代码、依赖、lock、fixture、runtime 或 feature switch。
不要进入 Wave 5 的任何修复步骤。

校验 Delivery 已达到 overall_status=verified，并重新校验当前 A/B revision。
若仓库或工件在 verified 后变化，停止并指出应重开的 3a/3b/3c 会话，
不得沿用旧验证。

功能、错误路径、权限、URL、视觉/表格、runtime/build、
rollback 和 legacy fallback 全部按 Skill 当前契约重新核验。

若必须修改 B，输出 discovery backflow，退出 verify，
指出下一步是新窗口的 5b-a，不得在本会话改代码。

结束时给出：
- Domain verification.status 与当前双仓 revision；
- 对照 A 仍存在的样式/功能残差（若有）；
- 清单一里的下一步编号（完成判定 / 5b-a / 5a-A）。

不得仅凭 Delivery verified + Domain pass 宣告“本次迁移验证完成”。
人眼对照 A 仍有样式或功能出入时，下一步是 Wave 5。
不得宣称已部署、已切流、已关闭 A 或已移除 fallback。
然后停止。
```

## 9. Wave 5：人眼残差修复

在会话 4 之后使用。触发条件（任一即可）：

- 对照源仓 A，迁入页样式仍有出入；
- 对照源仓 A，部分交互/功能仍有出入；
- 会话 4 输出 discovery backflow，必须改 B。

G9 pass 与 Domain visual pass **都不等于**肉眼对齐 A。  
`/frontend-ui-stack-visual-parity` 只修样式（CSS/配置）；功能残差必须交还 Delivery，禁止用视觉 skill 改业务 JS。

```text
同时有样式和功能残差：5b-a → 5b-b → 5b-c → 5a-A → 5a-B → 5c。
仅样式：5a-A → 5a-B → 5c。
仅功能：5b-a → 5b-b → 5b-c → 5c。
```

先功能再样式：行内编辑等交互态稳定后，视觉主样本才采得到编辑态。

### 9.1 会话 5b-a：功能残差 Frame

新会话。必须填入已观察的行为差；列表为空则停止询问，禁止扩成新一轮迁移。先贴 1.1，再贴：

```text
本会话只做 /delivery-frame-spec。
这不是新功能，是迁入后的行为残差修复。
规格闸门通过并写入 handoff 后停止。不要进入 plan/execute。

固定 High，visual=required；A 只读，B 是唯一代码 mutation target。
B 壳 host-native，迁入内容 strict parity，保留 legacy fallback。

只修下列已观察差异（未列出的不扩 scope）：
- <例如：进入行内编辑的触发条件与 A 不一致>
- <例如：失焦后未写回 / 未触发原校验>
- <例如：编辑态键盘行为或取消逻辑与 A 不一致>

禁止新功能、禁止 Composition 全量重写、禁止引入 Vue2 / @vue/compat。
B 中既有未提交内容属于用户改动，只检查碰撞，不覆盖、不丢弃。

结束时给出 handoff 路径与规格闸门状态。
然后停止。下一步是新窗口的 5b-b。
```

### 9.2 会话 5b-b：功能残差 Plan

新会话。先贴 1.1，再贴：

```text
本会话只做 /delivery-plan-tasks。
从 handoff 恢复残差范围。计划就绪后停止，不要进入 execute。
若本窗口给出实施 go：写入 handoff（绑定当前 artifact 与双仓 revision）后仍停。
修完后的 verified 不得沿用会话 3c/4 的旧结论。
然后停止。下一步是新窗口的 5b-c。
```

### 9.3 会话 5b-c：功能残差 Execute

新会话。先贴 1.1，再贴：

```text
本会话只做 /delivery-execute-verify。
只修改 B 的批准残差范围。
实施 go 必须已落盘且绑定当前 revision；否则停止。
达到 verified 后停止：不 archive、不 Git、不部署、不切流、
不移除 fallback、不关闭 A，也不要读取 migrate verify 或 5a。
然后停止。下一步是新窗口的 5a-A（若还有样式残差）或 5c。
```

### 9.4 会话 5a-A：样式定界

新会话。把观察到的样式出入写进提示词；没有具体点时，仍用默认主样本。先贴 1.1，再贴：

```text
本会话只做 /frontend-ui-stack-visual-parity Phase A。
execution_scope=analysis_only。定界包写盘后停止。
不要进入 Phase B，不要改 CSS/配置。

parity_topology=cross-repo
baseline_root=A（source_root）
candidate_root=B（host_root）
assessment_mode=strict_parity
forbid_baseline_mutation=yes

页面：
- A：/table/inline-edit-table
- B：/function/inline-edit-table
主样本：搜索区 + 主表 + 单元格内控件；行内编辑态必采。
策略默认「对齐 A」，不要改成跟 B 设计系统，除非用户另有书面决定。

output-dir：
D:\Hzhao\AI_Test\migration-artifacts\table-inline-edit\evidence\visual-parity\

A 只读。不装包、不升依赖、不重开 Vue2→Vue3 路径选择、
不改业务 JS/API/路由。

结束时给出：
- visual-summary.json 路径与当前包 revision；
- 主因与最小修复集。
然后停止。下一步是新窗口的 5a-B（需用户在该窗口给出绑定 revision 的 go）。
```

### 9.5 会话 5a-B：样式修复

等 5a-A 定界包写盘后，新会话。先贴 1.1，再贴（必须含明确 go 与包 revision）：

```text
本会话只做 /frontend-ui-stack-visual-parity Phase B。
从已写盘的 visual-summary.json / report 恢复，校验包 revision。

go:visual-fix
绑定包 revision：<从 5a-A 结束输出抄写>

只改 B 的 CSS/配置。禁止改 A，禁止改业务 JS/API/路由，
禁止装包或升依赖。「继续 / 看起来没问题 / 全部放行」不是 go；
本窗口提示词里必须有上面这类明确 go。

结束时给出修复文件、更新后的 visual-summary 路径与 final_visual_result。
然后停止。下一步是新窗口的 5c。
```

### 9.6 会话 5c：残差后重验

5a-B 或 5b-c 任一改动 B 后，旧 `host_revision`、G9 与 Domain verify 全部作废。新会话。先贴 1.1，再贴：

```text
本会话只做残差后重验。不要再改应用代码。

校验 Wave 5 改动后的当前 A/B revision；
不得沿用 3c/4 或本轮修复前的 verified/pass。

若 5b-c 改过 B：确认 Delivery 已在新 host_revision 上达到 overall_status=verified。
若 5a-B 改过 CSS/配置：把 visual-summary.json 仅作为 path+digest external_artifacts 引入；
Delivery G9 仍只认自有 delivery-visual-evidence/v1，必须按新 revision 重出。
若 G9 尚未在新 revision 上重出：停止，指出应重开的 Delivery 会话，不要在 verify 里补做 G9。

然后使用 /migrate-vue2-pages-to-vue3-host，mode=verify。
只做领域复核，不重复实施。

若仍必须改 B，指出下一步是新窗口的 5b-a 或 5a-A，不要在本会话修复。
人眼对照 A 仍有 blocking 残差时，不得宣告完成。
然后停止。
```

## 10. 完成判定

```text
有效的领域设计
+ 已完成的依赖决策（适用时）
+ Delivery overall_status=verified（绑定当前双仓 revision）
+ Domain verification.status=pass（绑定同一 revision）
+ 人眼对照 A：无 blocking 样式残差、无 blocking 功能残差
+ 若跑过 Wave 5：修复后的 host_revision 上 G9 与 Domain verify 均重新 pass
+ 若跑过 5a：visual-summary 的 final_visual_result=pass
  （Phase B done，或经书面决定 skipped）
+ legacy fallback 可演练
+ 无 blocking residual
= 本次迁移验证完成
```

G9 pass ≠ 肉眼对齐 A。会话 4 两闸门 pass 后只要人眼仍偏，就还不是完成态。

OpenSpec archive、Git 操作、部署、切流、观察期结束、移除 fallback 和关闭 A 均需另行授权，不属于本编排的自动步骤。
