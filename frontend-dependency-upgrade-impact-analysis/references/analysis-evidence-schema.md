# 分析证据输入契约

当 Agent 已通过官方资料、Codebase Memory 和定向代码调查补齐候选或删除证据时，把结果写成 JSON，并通过：

```bash
--analysis-evidence-file <path>
```

导入生成器。这个文件是报告的结构化证据输入，不是审批或实施授权。

## JSON 结构

```json
{
  "node_runtime": {
    "additional_project_constraints": [
      {
        "source": "legacy build plugin official support",
        "requirement": "<=16",
        "kind": "toolchain",
        "authority": "authoritative"
      }
    ],
    "selected_project_node": "16.20.2",
    "selection_reason": "满足项目 pin、engines 和目标包 engines 的最高已安装版本",
    "notes": ["Node 16 已 EOL，仅用于隔离验证"]
  },
  "packages": {
    "legacy-client": {
      "reason": "停止维护",
      "constraints": ["保持请求契约和错误语义不变"],
      "official_sources": [
        {
          "kind": "migration",
          "url": "https://example.invalid/official-migration",
          "status": "confirmed",
          "title": "官方迁移指南",
          "version": "2.4.1",
          "reason": "已核对目标版本范围"
        }
      ],
      "evidence_dimensions": {
        "registry": "confirmed",
        "repository": "confirmed",
        "release": "confirmed",
        "changelog": "confirmed",
        "migration": "confirmed",
        "compatibility": "confirmed",
        "security": "confirmed",
        "support": "confirmed",
        "license": "confirmed"
      },
      "target_candidates": [
        {
          "version": "2.4.1",
          "candidate_type": "supported-stable",
          "compliance_status": "eligible",
          "criteria_checked": ["security", "license", "maintenance", "peer", "engines"],
          "disqualifiers": [],
          "compatibility": "支持当前框架和 Node 版本",
          "compliance_and_maintenance": "未命中已知公告；仓库仍维护",
          "migration_cost": "medium",
          "validation_scope": "请求包装器、登录、上传下载",
          "rollback_difficulty": "low",
          "rationale": "满足治理要求且迁移面小于换库",
          "confidence": "high",
          "source": "https://registry.npmjs.org/legacy-client/2.4.1",
          "evidence_urls": ["https://example.invalid/official-release"],
          "checked_at": "2026-07-24"
        }
      ],
      "alternative_candidates": [
        {
          "package": "replacement-client",
          "version": "1.8.0",
          "compliance_status": "eligible",
          "criteria_checked": ["security", "license", "maintenance", "peer", "engines"],
          "disqualifiers": [],
          "compatibility": "需要适配拦截器",
          "compliance_and_maintenance": "维护中",
          "migration_cost": "high",
          "validation_scope": "全部请求流程",
          "rollback_difficulty": "medium",
          "rationale": "同库无可行版本时的候选",
          "confidence": "medium",
          "evidence_urls": ["https://example.invalid/official-docs"],
          "checked_at": "2026-07-24"
        }
      ],
      "removal": {
        "status": "requires_migration",
        "evidence": ["公共请求包装器直接使用"],
        "blockers": ["src/request/client.ts"],
        "unknowns": [],
        "confidence": "high",
        "coverage_checked": ["business", "runtime"]
      }
    }
  }
}
```

## 校验规则

- `node_runtime` 是可选的整单证据对象，不属于单个包，也不是实施授权。
- `additional_project_constraints` 每项必须包含 `source`、`requirement`、`kind` 和 `authority`；`authority` 只能为 `authoritative` 或 `observed`。`kind` 推荐复用 `references/node-runtime-compatibility.md` §2 的类别名，便于与生成器自动收集的证据并排阅读；这也是把自动探测到的 `observed` 证据（CI 镜像、非白名单依赖 engines）在人工确认后提权为项目约束的唯一通道。
- `selected_project_node` 必须是精确 semver，并满足所有可解析的权威项目约束；生成器探测结果不一致时保持 blocked。
- 证据文件不能包含或授予 `runtime-switch`、`node-install`、依赖安装或项目脚本权限；审批只从当前任务的调用方生命周期取得。
- 候选必须提供精确 semver。
- `compliance_status` 只能为 `eligible`、`ineligible` 或 `unknown`。
- `eligible` 必须同时提供非空 `criteria_checked` 和 `evidence_urls`。
- 删除状态只能为 `safe_removal_candidate`、`requires_migration`、`not_viable`、`uncertain` 或 `not_assessed`。
- `safe_removal_candidate` 必须覆盖 `business/runtime/dynamic/build/tooling/peer/transitive`，提供非空 evidence，且 unknowns 为空。
- 证据文件中的包必须属于本次分析清单；不得用它新增未声明的分析对象。
- `official_sources` 每项必须包含 `kind` 和直接 URL；`status` 使用 `confirmed/candidate/missing/ambiguous/not-applicable/offline`。
- `evidence_dimensions` 只允许 `registry/repository/release/changelog/migration/compatibility/security/support/license`。发现候选 URL 不等于 `confirmed`；Agent 必须实际核对正文、版本适用范围和官方归属。
- `complete` 要求所有审批维度为 `confirmed` 或有证据支持的 `not-applicable`；Release 与 changelog 不能用 OR 逻辑掩盖缺口。
- 该文件可以补充候选和证据，但不能记录审批、自动选择候选或授权实施。
