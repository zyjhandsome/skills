#!/usr/bin/env node
// @ts-check
/**
 * Delivery Family scaffold (R3 backlog P1-1/P1-2/P1-3): cut the hand-written JSON and
 * machine-anchor cost that dominated Quick-lane wall-clock time.
 *
 * Subcommands
 * -----------
 * new-handoff   Generate a valid delivery-handoff/v1 skeleton for any stage. Nominal
 *               capability snapshot, timestamps, per-stage stage_payload skeleton, and
 *               artifact_revision computed from the change dir when given. The skeleton
 *               validates as a non-transition (pending/blocked) handoff out of the box;
 *               the agent only edits business fields and the gate before transition.
 *
 * quick-pack    Scaffold a Quick/Debug-Low lightweight change: proposal.md (OpenSpec
 *               skeleton + Chinese lightweight contract with Explore-consume N/A),
 *               minimal delta spec (one Requirement + Scenario), and tasks.md whose task
 *               blocks carry the exact machine anchors validate_delivery_change.mjs reads.
 *               Never overwrites existing files.
 *
 * close-out     Execute verified close-out wizard: runs validate_delivery_change
 *               --claim-verified, computes artifact_revision, generates the verified
 *               execute handoff, validates it (hard profile), writes <change>/handoff.json,
 *               and prints the deferred archive next step. It never runs archive/git.
 *
 * All output artifacts remain drafts owned by the agent: gates, reviews, and approvals
 * still follow the family contracts. Zero dependencies (Node >= 18).
 */

import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, readdirSync, realpathSync, statSync, writeFileSync } from "node:fs";
import { join, resolve, basename, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import process from "node:process";

import { hashChange, normalizeRevision } from "./hash_change_artifacts.mjs";
import { CURRENT_FAMILY_VERSION, validate } from "./validate_handoff.mjs";
import { emptyGateBlock, parseGateRecord, upsertGateLine, GATE_START } from "./gate_record.mjs";

import { checkChange, isRfc3339 } from "../../delivery-execute-verify/scripts/validate_delivery_change.mjs";

const STAGES = ["delivery-explore", "delivery-frame-spec", "delivery-plan-tasks", "delivery-execute-verify"];

const STAGE_PAYLOAD_SKELETONS = {
  "delivery-explore": {
    direction_alignment: "needs_choice",
    chosen_direction: "",
    non_goals: [],
    code_anchors: [],
    risk_signal: "none",
    quality_signals: [],
    unknowns: [],
  },
  "delivery-frame-spec": {
    route: "Standard",
    risk: "medium",
    confirmed_artifacts: [],
    forbidden_scope: [],
    open_questions: [],
    quality_profiles: {},
    external_artifacts: [],
  },
  "delivery-plan-tasks": {
    plan_tasks: [],
    plan_decisions: {
      agent_decided: [],
      user_decided: [],
      returned_to_frame: [],
      remaining_blockers: [],
    },
    traceability: [],
    readiness_result: { blockers: [], warnings: [], suggestions: [] },
    validation_plan: [],
    quality_profiles: {},
    visual_validation_plan: [],
    risk_gates: [],
    parallel_ownership: [],
  },
  "delivery-execute-verify": {
    overall_status: "in_progress",
    task_status: [],
    current_failures_or_blocks: [],
    artifact_backflow: "none",
    alignment_backflow: null,
    fresh_verification_evidence: [],
    visual_evidence: {
      required: false,
      report: null,
      source_artifact_revision: null,
      g9: "not_required",
    },
    spec_coherence: "pass",
    code_review: {
      status: "pass",
      mode: "independent",
      independent_review: "required_pass",
      reviewer: null,
      findings: [],
    },
    archive: { status: "deferred_to_openspec", reason: "execute-verify must not sync/archive" },
    asset_writeback: [],
  },
};

const STAGE_PRESENTATION = {
  "delivery-explore": ["探索·方向对齐", "定框·路由与需求边界", "请使用 delivery-frame-spec"],
  "delivery-frame-spec": ["定框", "技术设计与任务拆解", "请使用 delivery-plan-tasks"],
  // Fixed wording (R3 4.3): plan completion != tasks checked; checking belongs to Execute.
  "delivery-plan-tasks": [
    "计划·就绪审查完成",
    "实施·按 tasks.md 执行（任务勾选属 Execute 阶段）",
    "请使用 delivery-execute-verify",
  ],
  "delivery-execute-verify": ["实施·验证", "OpenSpec 归档", "<已解析的 archive_change 操作>"],
};

export function nowRfc3339() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

/** @param {string} cwd @returns {string | null} */
function gitHead(cwd) {
  const result = spawnSync("git", ["rev-parse", "HEAD"], {
    cwd,
    encoding: "utf-8",
    timeout: 15000,
  });
  if (result.error || result.status !== 0) return null;
  const head = (result.stdout ?? "").trim();
  return head || null;
}

/** @param {string | null} changeDir @returns {string | null} */
function computeRevision(changeDir) {
  if (changeDir === null) return null;
  const hashed = hashChange(changeDir);
  return hashed.entries.length ? hashed.revision : null;
}

/** @param {string} changeDir */
function changeAnchor(changeDir) {
  const parts = resolve(changeDir).split(sep);
  const index = parts.lastIndexOf("openspec");
  if (index !== -1) return parts.slice(index).join("/");
  return changeDir.split(sep).join("/");
}

/** @param {string} p */
function isDir(p) {
  try {
    return statSync(p).isDirectory();
  } catch {
    return false;
  }
}

/**
 * @param {string} stage
 * @param {string | null} changeDir
 * @param {string | null} previous
 * @returns {Record<string, any>}
 */
export function buildHandoff(stage, changeDir, previous) {
  const ts = nowRfc3339();
  const changeId = changeDir ? basename(resolve(changeDir)) : "<change-id>";
  /** @type {Record<string, any>} */
  let stateSource;
  /** @type {{status: string, summary: string}} */
  let gate;
  if (stage === "delivery-explore") {
    stateSource = { kind: "none", label: "none（探索非正式）", anchor: null };
    gate = { status: "n/a", summary: "探索非正式，无规格闸门" };
  } else {
    stateSource = {
      kind: "openspec_change",
      label: `change #${changeId}`,
      anchor: changeDir ? changeAnchor(changeDir) : null,
    };
    gate = { status: "pending", summary: "<闸门未放行；放行时补 status/approved_*/binds_to_revision>" };
  }

  const [fromTask, toTask, continuePrompt] =
    STAGE_PRESENTATION[/** @type {keyof typeof STAGE_PRESENTATION} */ (stage)];
  const stamp = ts.replaceAll(":", "").replaceAll("-", "").slice(0, 15);
  const handoff = {
    schema_version: "delivery-handoff/v1",
    family_version: CURRENT_FAMILY_VERSION,
    type: "delivery-handoff",
    handoff_id: `${changeId}-${stage.replace(/^delivery-/, "")}-${stamp}`,
    previous_handoff_id: previous,
    generated_at: ts,
    stage,
    source_revision: {
      repo_head: gitHead(changeDir ?? process.cwd()),
      artifact_revision: computeRevision(changeDir),
      revision_algo: 2,
      state_observed_at: ts,
    },
    state_source: stateSource,
    capability_snapshot: { memory: "ok", openspec: "initialized", superpowers: "loaded" },
    capability_bindings: { openspec: {}, memory: {}, superpowers: {}, subagents: {} },
    presentation_capability: { mode: "markdown", source: "unknown" },
    gate_status: {
      status: gate.status,
      summary: gate.summary,
      evidence: [],
      approved_by: null,
      approved_at: null,
      binds_to_revision: null,
      accepted_warning_ids: [],
    },
    evidence_mode: "full",
    next_skill: null,
    next_action: null,
    required_inputs: [],
    stop_condition: "<草稿：填写当前真实停止条件；允许转换时清空并设置 next_skill/next_action>",
    stage_payload: structuredClone(
      STAGE_PAYLOAD_SKELETONS[/** @type {keyof typeof STAGE_PAYLOAD_SKELETONS} */ (stage)]
    ),
    presentation: {
      schema: "delivery-presentation/v1",
      from_task: fromTask,
      to_task: toTask,
      summary: "<一句话结论>",
      evidence: [],
      continue_prompt: continuePrompt,
    },
  };
  if (stage === "delivery-execute-verify") {
    handoff.stage_payload.implementation_gate = readImplementationGate(changeDir);
  }
  return handoff;
}

/** @param {string | null} changeDir */
function readImplementationGate(changeDir) {
  if (!changeDir) return null;
  const path = join(changeDir, "proposal.md");
  if (!existsSync(path)) return null;
  const parsed = parseGateRecord(readFileSync(path, "utf8"));
  const gate = parsed.impl;
  if (!gate || gate.status !== "approved" || !gate.revision) return null;
  return {
    approved_by: gate.approvedBy,
    approved_at: gate.approvedAt,
    binds_to_revision: gate.revision,
  };
}

/** @param {string} text */
function ensureGateBlock(text) {
  if (text.includes(GATE_START)) return text;
  // Insert complete lines so stripping the block recovers the original approved bytes.
  const heading = /^### 状态源与工件位置[^\n]*\n/m.exec(text);
  const at = heading ? heading.index + heading[0].length : text.lastIndexOf("\n") + 1;
  const block = text.includes("\r\n") ? emptyGateBlock().replaceAll("\n", "\r\n") : emptyGateBlock();
  return text.slice(0, at) + block + text.slice(at);
}

/** @param {Record<string, any>} obj @param {string | null} out */
function emit(obj, out) {
  const text = JSON.stringify(obj, null, 2) + "\n";
  if (out) {
    writeFileSync(out, text, "utf-8");
    console.log(`wrote ${out}`);
  } else {
    console.log(text);
  }
}

/**
 * @param {{stage: string, changeDir: string | null, previous: string | null, out: string | null}} args
 */
function cmdNewHandoff(args) {
  const changeDir = args.changeDir ? resolve(args.changeDir) : null;
  if (changeDir && !isDir(changeDir)) {
    console.error(`ERROR: change dir does not exist: ${changeDir}`);
    return 2;
  }
  if (args.stage !== "delivery-explore" && changeDir === null) {
    console.error("ERROR: --change-dir is required for every stage except delivery-explore");
    return 2;
  }
  const handoff = buildHandoff(args.stage, changeDir, args.previous);
  const errors = validate(handoff, "hard");
  if (errors.length) {
    for (const error of errors) console.error(`ERROR (skeleton invalid — scaffold bug): ${error}`);
    return 1;
  }
  emit(handoff, args.out);
  console.error(
    "skeleton validates as a non-transition handoff; fill business fields, then re-validate " +
      "before any transition."
  );
  return 0;
}

/** @param {{goal: string, capability: string, impact: string, anchor: string, changeId: string, requirement: string}} f */
const quickProposal = (f) => `## Why

${f.goal}

## What Changes

<一句话：可观察行为变化>

## Capabilities

### New Capabilities

${f.skipSpecs ? "无（.openspec.yaml 已设 skip_specs: true）" : `- ${f.capability}`}

<!-- 修改既有 capability 时改用 ### Modified Capabilities，并在 delta spec 里用 ## MODIFIED Requirements（需整块复制原 Requirement） -->

## Impact

- ${f.impact}

---

# 轻量契约（Quick / Debug-Low）

目标：${f.goal}
非目标：<不做什么>
影响文件/符号：${f.impact}
可观察行为：<用户/系统可见的变化>
最小验证：<命令与预期>
禁止范围：<不得触碰的路径/行为>
风险/未知项：<一句话>
澄清完整性扫描：已检查适用维度；无实质阻塞项（有则列出）

### Explore 交接消费
N/A — 无 explore handoff

### 状态源与工件位置
- 后端：OpenSpec change
- 路径：${f.anchor}
${upsertGateLine(emptyGateBlock(), "spec", {
  status: "n/a",
  approvedBy: null,
  approvedAt: null,
  revision: null,
  acceptedWarnings: [],
  note: "Quick 车道",
})}

> Quick 车道无 \`design.md\` 属预期：\`openspec status\` 显示 design 未完成不代表变更不完整，
> 向用户解释时引用本行即可；不要为凑 status 写假 design。
`;

/** @param {{goal: string, requirement: string}} f */
const quickSpec = (f) => `## ADDED Requirements

### Requirement: ${f.requirement}

系统 MUST ${f.goal}。

#### Scenario: 基本行为

- **WHEN** <执行动作>
- **THEN** <可观察结果>
`;

/** @param {{goal: string, impact: string, anchor: string, changeId: string, requirement: string}} f */
const quickTasks = (f) => `# ${f.changeId}：实施任务清单

## 执行规则
- 权威状态源：${f.anchor}
- 风险/闸门：Quick / low；实施前须用户明确批准轻量契约
- 禁止范围：<同契约>
- 必须执行的最终验证：<命令>

## 任务

- [ ] 任务 1：${f.goal}
  - 对应需求/场景：${f.scenario}
  - 前置依赖：无
  - 目标文件/符号：${f.impact}
  - 允许修改：${f.impact}
  - 禁止修改：<路径>
  - 实施步骤：<1-2 步>
  - 失败测试或已批准替代验证：<测试文件/断言>
  - 验证命令/动作：<命令>
  - 预期结果：<如 exit 0，N passed>
  - 迁移/回滚：不适用（可逆小改动）
  - 完成定义：验证命令通过且行为可观察
  - 负责人/冲突说明：单人无冲突

## 集成顺序

单任务，无集成顺序。

## 最终验证
| 命令/动作 | 覆盖范围 | 预期结果 |
|---|---|---|
| <命令> | 本任务行为 + 相邻回归 | exit 0 |
`;

/**
 * @param {{changeDir: string, capability: string, goal: string, impact: string, requirement: string | null, skipSpecs: boolean}} args
 */
function cmdQuickPack(args) {
  const changeDir = resolve(args.changeDir);
  const existing = existsSync(changeDir) ? readdirSync(changeDir) : [];
  const openspecOnly = existing.length === 0 || (existing.length === 1 && existing[0] === ".openspec.yaml");
  if (!openspecOnly) {
    console.error(
      `ERROR: change dir not empty (${existing.slice(0, 5).join(", ")}…) — quick-pack never overwrites`
    );
    return 2;
  }
  const yamlPath = join(changeDir, ".openspec.yaml");
  if (args.skipSpecs && !existsSync(yamlPath)) {
    console.error("ERROR: --skip-specs requires an existing .openspec.yaml — run `openspec new change <id>` first");
    return 2;
  }
  mkdirSync(changeDir, { recursive: true });
  const anchor = changeAnchor(changeDir);
  const requirement = args.requirement ?? args.goal;
  const fields = {
    goal: args.goal,
    capability: args.capability,
    impact: args.impact,
    anchor,
    changeId: basename(changeDir),
    requirement,
    skipSpecs: args.skipSpecs,
    scenario: args.skipSpecs ? "不适用（skip_specs）" : `${requirement} / 基本行为`,
  };

  writeFileSync(join(changeDir, "proposal.md"), quickProposal(fields), "utf-8");
  if (!args.skipSpecs) {
    const specDir = join(changeDir, "specs", args.capability);
    mkdirSync(specDir, { recursive: true });
    writeFileSync(join(specDir, "spec.md"), quickSpec(fields), "utf-8");
  } else {
    const yaml = readFileSync(yamlPath, "utf8");
    if (!/^skip_specs:\s*true\s*$/m.test(yaml)) {
      writeFileSync(yamlPath, yaml.endsWith("\n") ? `${yaml}skip_specs: true\n` : `${yaml}\nskip_specs: true\n`, "utf-8");
    }
  }
  writeFileSync(join(changeDir, "tasks.md"), quickTasks(fields), "utf-8");

  const { revision } = hashChange(changeDir);
  console.log(`scaffolded Quick change at ${changeDir}`);
  console.log(`artifact_revision (pre-edit): ${revision}`);
  console.log(
    "next: fill the <placeholders>, run `openspec validate`, present the contract, and record " +
      "the user go bound to the post-edit artifact_revision (re-run hash_change_artifacts.mjs)."
  );
  return 0;
}

/**
 * @param {{changeDir: string, init: boolean, gate: string | null, approvedBy: string | null,
 *          acceptedWarnings: string | null, note: string | null, notApplicable: string | null,
 *          approvedAt: string | null, expectedRevision: string | null}} args
 */
function cmdRecordGate(args) {
  const changeDir = resolve(args.changeDir);
  if (!isDir(changeDir)) {
    console.error(`ERROR: change dir does not exist: ${changeDir}`);
    return 2;
  }
  const proposalPath = join(changeDir, "proposal.md");
  if (!existsSync(proposalPath)) {
    console.error("ERROR: proposal.md missing");
    return 2;
  }
  const text = readFileSync(proposalPath, "utf8");
  if (args.init) {
    const next = ensureGateBlock(text);
    if (next !== text) writeFileSync(proposalPath, next, "utf-8");
    console.log(hashChange(changeDir).revision);
    return 0;
  }
  if (!["spec", "impl"].includes(args.gate ?? "")) {
    console.error("ERROR: record-gate requires --gate spec|impl");
    return 2;
  }
  if (!text.includes(GATE_START)) {
    console.error("gate-record: block missing — run record-gate --change-dir <dir> --init first");
    return 3;
  }
  const kind = /** @type {"spec" | "impl"} */ (args.gate);
  /** @type {{ status: "pending" | "n/a" | "approved", approvedBy: string | null, approvedAt: string | null, revision: string | null, acceptedWarnings: string[], note: string | null }} */
  let gate;
  if (args.notApplicable !== null) {
    gate = {
      status: "n/a",
      approvedBy: null,
      approvedAt: null,
      revision: null,
      acceptedWarnings: [],
      note: args.notApplicable,
    };
  } else {
    if (!args.approvedBy) {
      console.error("ERROR: record-gate requires --approved-by");
      return 2;
    }
    const revision = hashChange(changeDir).revision;
    if (args.expectedRevision !== null && normalizeRevision(args.expectedRevision) !== revision) {
      console.error("record-gate blocked: the approved revision differs from the current change");
      return 1;
    }
    if (args.approvedAt !== null && (!args.expectedRevision || !isRfc3339(args.approvedAt) ||
        !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/i.test(args.approvedAt))) {
      console.error("record-gate: restoring an approval requires its RFC3339 time and --expected-revision");
      return 2;
    }
    gate = {
      status: "approved",
      approvedBy: args.approvedBy,
      approvedAt: args.approvedAt ?? nowRfc3339(),
      revision,
      acceptedWarnings: args.acceptedWarnings ? args.acceptedWarnings.split(",").filter((id) => id.length > 0) : [],
      note: args.note,
    };
  }
  writeFileSync(proposalPath, upsertGateLine(text, kind, gate), "utf-8");
  const after = hashChange(changeDir).revision;
  if (gate.status === "approved" && after !== gate.revision) {
    console.error("ERROR: record-gate moved the artifact revision");
    return 1;
  }
  console.log(`recorded ${kind} gate bound to ${gate.status === "approved" ? gate.revision : after}`);
  return 0;
}

/**
 * @param {{changeDir: string, reviewStatus: string, reviewer: string | null, evidence: string[],
 *          specCoherence: string, approvedBy: string | null, previous: string | null,
 *          nextAction: string | null, out: string | null, visualRequired: boolean,
 *          visualReport: string | null, expectedVisualRevision: string | null,
 *          requiredStateIds: string | null}} args
 */
function cmdCloseOut(args) {
  const changeDir = resolve(args.changeDir);
  if (!isDir(changeDir)) {
    console.error(`ERROR: change dir does not exist: ${changeDir}`);
    return 2;
  }
  const proposalPath = join(changeDir, "proposal.md");
  let impl = null;
  if (existsSync(proposalPath)) {
    try {
      impl = parseGateRecord(readFileSync(proposalPath, "utf8")).impl;
    } catch (error) {
      console.error(`close-out blocked: ${error instanceof Error ? error.message : error}`);
      return 1;
    }
  }
  const currentRevision = hashChange(changeDir).revision;
  if (!impl || impl.status !== "approved" || normalizeRevision(impl.revision) !== normalizeRevision(currentRevision)) {
    console.error("close-out blocked: implementation gate missing or stale — run record-gate after the user go");
    return 1;
  }

  // 1. Machine checks on tasks/verification (the R3 rework hotspot).
  const checked = checkChange(changeDir, {
    claimVerified: true, visualRequired: args.visualRequired, visualReport: args.visualReport,
    expectedVisualRevision: args.expectedVisualRevision,
    requiredStateIds: (args.requiredStateIds ?? "").split(",").map((id) => id.trim()).filter(Boolean),
    summaries: args.evidence,
  });
  if (checked.errors.length) {
    for (const error of checked.errors) console.error("close-out blocked: " + error);
    return 1;
  }

  // 2. Verified execute handoff draft.
  const handoff = buildHandoff("delivery-execute-verify", changeDir, args.previous);
  const revision = handoff.source_revision.artifact_revision;
  const payload = handoff.stage_payload;
  payload.overall_status = "verified";
  if (revision !== currentRevision) {
    console.error("close-out blocked: change artifacts moved during verification");
    return 1;
  }
  payload.fresh_verification_evidence = [...new Set([...checked.evidence, ...args.evidence])];
  payload.visual_evidence = checked.visualEvidence;
  payload.spec_coherence = args.specCoherence;
  Object.assign(payload.code_review, {
    status: args.reviewStatus,
    reviewer: args.reviewer,
  });
  Object.assign(handoff.gate_status, {
    status: "pass",
    summary: `新鲜验证 + 独立审查（${args.reviewer ?? "independent reviewer"}）通过；归档移交 OpenSpec`,
    evidence: [...payload.fresh_verification_evidence],
    approved_by: args.approvedBy,
    approved_at: args.approvedBy ? nowRfc3339() : null,
    binds_to_revision: args.approvedBy ? revision : null,
  });
  const nextAction = args.nextAction ?? `openspec archive ${basename(changeDir)}`;
  handoff.next_action = nextAction;
  handoff.stop_condition = "";
  handoff.presentation.summary = "verified；归档移交 OpenSpec（本技能不执行 archive）";
  handoff.presentation.continue_prompt = nextAction;

  const errors = validate(handoff, "hard");
  if (errors.length) {
    for (const error of errors) console.error(`ERROR: ${error}`);
    console.error(
      "close-out blocked: handoff draft invalid — usually missing --review-status/--evidence " +
        "or an approval field combination."
    );
    return 1;
  }

  const out = args.out ?? join(changeDir, "handoff.json");
  emit(handoff, out);
  console.log("\nverified close-out ready:");
  console.log(`  1. archive is DEFERRED — run the resolved archive operation yourself: ${nextAction}`);
  console.log("  2. commit / push / PR remain user-gated; ask before any git mutation.");
  console.log("  3. confirm the resolved archive binding in capability_bindings.openspec before running it.");
  return 0;
}

/**
 * Minimal option parser: flags in `spec` take one value, except boolean flags listed
 * in `booleans`. Repeatable flags listed in `arrays` accumulate.
 * @param {string[]} argv
 * @param {Record<string, string>} spec map of --flag to canonical key
 * @param {Set<string>} arrays canonical keys that accumulate
 * @param {Set<string>} [booleans] canonical keys that take no value
 * @returns {{opts: Record<string, any>, positional: string[], error: string | null}}
 */
function parseOptions(argv, spec, arrays = new Set(), booleans = new Set()) {
  /** @type {Record<string, any>} */
  const opts = {};
  /** @type {string[]} */
  const positional = [];
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg.startsWith("--")) {
      const key = spec[arg];
      if (!key) return { opts, positional, error: `unknown option: ${arg}` };
      if (booleans.has(key)) {
        opts[key] = true;
        continue;
      }
      const value = argv[++i];
      if (value === undefined) return { opts, positional, error: `option ${arg} requires a value` };
      if (arrays.has(key)) (opts[key] ??= []).push(value);
      else opts[key] = value;
    } else {
      positional.push(arg);
    }
  }
  return { opts, positional, error: null };
}

const USAGE = `usage: node delivery_scaffold.mjs <command> [options]

commands:
  new-handoff <stage> [--change-dir <dir>] [--previous <id>] [--out <file>]
      generate a delivery-handoff/v1 skeleton (stage: ${STAGES.join(" | ")})
  quick-pack --change-dir <dir> --capability <cap> --goal <text> --impact <text> [--requirement <text>] [--skip-specs]
      scaffold a Quick/Debug-Low lightweight change
  record-gate --change-dir <dir> (--init | --gate <spec|impl> (--approved-by <who> | --not-applicable <reason>) [--accepted-warnings <csv>] [--note <text>] [--expected-revision <revision>] [--approved-at <RFC3339>])
      write the proposal gate-record block without moving artifact_revision
  close-out --change-dir <dir> --review-status <pass|warn> [--reviewer <id>] [--evidence <line>]...
            [--spec-coherence <pass|warn>] [--approved-by <who>] [--previous <id>]
            [--visual-required <yes|no>] [--visual-report <path>]
            [--expected-visual-revision <assertion>] [--required-state-ids <additional-ids>] [--next-action <op>] [--out <file>]
      verified close-out wizard for execute`;

function main() {
  const [command, ...rest] = process.argv.slice(2);
  if (!command) {
    console.error(USAGE);
    return 2;
  }

  if (command === "new-handoff") {
    const { opts, positional, error } = parseOptions(rest, {
      "--change-dir": "changeDir",
      "--previous": "previous",
      "--out": "out",
    });
    if (error) {
      console.error(`ERROR: ${error}`);
      return 2;
    }
    if (positional.length !== 1 || !STAGES.includes(positional[0])) {
      console.error(`ERROR: new-handoff requires a stage argument: ${STAGES.join(" | ")}`);
      return 2;
    }
    return cmdNewHandoff({
      stage: positional[0],
      changeDir: opts.changeDir ?? null,
      previous: opts.previous ?? null,
      out: opts.out ?? null,
    });
  }

  if (command === "quick-pack") {
    const { opts, error } = parseOptions(
      rest,
      {
        "--change-dir": "changeDir",
        "--capability": "capability",
        "--goal": "goal",
        "--impact": "impact",
        "--requirement": "requirement",
        "--skip-specs": "skipSpecs",
      },
      new Set(),
      new Set(["skipSpecs"])
    );
    if (error) {
      console.error(`ERROR: ${error}`);
      return 2;
    }
    for (const required of ["changeDir", "capability", "goal", "impact"]) {
      if (!opts[required]) {
        console.error(`ERROR: quick-pack requires --${required.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)}`);
        return 2;
      }
    }
    return cmdQuickPack({
      changeDir: opts.changeDir,
      capability: opts.capability,
      goal: opts.goal,
      impact: opts.impact,
      requirement: opts.requirement ?? null,
      skipSpecs: opts.skipSpecs === true,
    });
  }

  if (command === "record-gate") {
    const { opts, error } = parseOptions(
      rest,
      {
        "--change-dir": "changeDir",
        "--gate": "gate",
        "--approved-by": "approvedBy",
        "--accepted-warnings": "acceptedWarnings",
        "--note": "note",
        "--not-applicable": "notApplicable",
        "--expected-revision": "expectedRevision",
        "--approved-at": "approvedAt",
        "--init": "init",
      },
      new Set(),
      new Set(["init"])
    );
    if (error) {
      console.error(`ERROR: ${error}`);
      return 2;
    }
    if (!opts.changeDir) {
      console.error("ERROR: record-gate requires --change-dir");
      return 2;
    }
    return cmdRecordGate({
      changeDir: opts.changeDir,
      init: opts.init === true,
      gate: opts.gate ?? null,
      approvedBy: opts.approvedBy ?? null,
      acceptedWarnings: opts.acceptedWarnings ?? null,
      note: opts.note ?? null,
      notApplicable: opts.notApplicable ?? null,
      expectedRevision: opts.expectedRevision ?? null,
      approvedAt: opts.approvedAt ?? null,
    });
  }

  if (command === "close-out") {
    const { opts, error } = parseOptions(
      rest,
      {
        "--change-dir": "changeDir",
        "--review-status": "reviewStatus",
        "--reviewer": "reviewer",
        "--evidence": "evidence",
        "--spec-coherence": "specCoherence",
        "--approved-by": "approvedBy",
        "--previous": "previous",
        "--next-action": "nextAction",
        "--out": "out",
        "--visual-required": "visualRequired",
        "--visual-report": "visualReport",
        "--expected-visual-revision": "expectedVisualRevision",
        "--required-state-ids": "requiredStateIds",
      },
      new Set(["evidence"])
    );
    if (error) {
      console.error(`ERROR: ${error}`);
      return 2;
    }
    if (!opts.changeDir) {
      console.error("ERROR: close-out requires --change-dir");
      return 2;
    }
    if (!["pass", "warn"].includes(opts.reviewStatus)) {
      console.error("ERROR: close-out requires --review-status pass|warn");
      return 2;
    }
    if (opts.specCoherence !== undefined && !["pass", "warn"].includes(opts.specCoherence)) {
      console.error("ERROR: --spec-coherence must be pass or warn");
      return 2;
    }
    if (opts.visualRequired !== undefined && !["yes", "no"].includes(opts.visualRequired)) {
      console.error("ERROR: --visual-required must be yes or no");
      return 2;
    }
    const visualRequired = opts.visualRequired === "yes";
    return cmdCloseOut({
      changeDir: opts.changeDir,
      reviewStatus: opts.reviewStatus,
      reviewer: opts.reviewer ?? null,
      evidence: opts.evidence ?? [],
      specCoherence: opts.specCoherence ?? "pass",
      approvedBy: opts.approvedBy ?? null,
      previous: opts.previous ?? null,
      nextAction: opts.nextAction ?? null,
      out: opts.out ?? null,
      visualRequired,
      visualReport: opts.visualReport ?? null,
      expectedVisualRevision: opts.expectedVisualRevision ?? null,
      requiredStateIds: opts.requiredStateIds ?? null,
    });
  }

  console.error(`ERROR: unknown command: ${command}\n\n${USAGE}`);
  return 2;
}

if (
  process.argv[1] &&
  pathToFileURL(realpathSync(resolve(process.argv[1]))).href.toLowerCase() ===
    pathToFileURL(realpathSync(fileURLToPath(import.meta.url))).href.toLowerCase()
) {
  process.exit(main());
}
