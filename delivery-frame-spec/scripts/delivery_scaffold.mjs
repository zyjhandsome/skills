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
import { existsSync, mkdirSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, resolve, basename, sep } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

import { hashChange } from "./hash_change_artifacts.mjs";
import { validate } from "./validate_handoff.mjs";

const SCRIPTS_DIR = dirname(fileURLToPath(import.meta.url));
const VALIDATE_DELIVERY_CHANGE = join(
  SCRIPTS_DIR,
  "..",
  "..",
  "delivery-execute-verify",
  "scripts",
  "validate_delivery_change.mjs"
);

const STAGES = ["delivery-explore", "delivery-frame-spec", "delivery-plan-tasks", "delivery-execute-verify"];

const STAGE_PAYLOAD_SKELETONS = {
  "delivery-explore": {
    direction_alignment: "needs_choice",
    chosen_direction: "",
    non_goals: [],
    code_anchors: [],
    risk_signal: "none",
    unknowns: [],
  },
  "delivery-frame-spec": {
    route: "Standard",
    risk: "medium",
    confirmed_artifacts: [],
    forbidden_scope: [],
    open_questions: [],
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
  const { digest, entries } = hashChange(changeDir);
  return entries.length ? `sha256:${digest}` : null;
}

/** @param {string} changeDir */
function changeAnchor(changeDir) {
  const parts = resolve(changeDir).split(sep);
  const index = parts.indexOf("openspec");
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
  return {
    schema_version: "delivery-handoff/v1",
    family_version: "delivery-family/1.3",
    type: "delivery-handoff",
    handoff_id: `${changeId}-${stage.replace(/^delivery-/, "")}-${stamp}`,
    previous_handoff_id: previous,
    generated_at: ts,
    stage,
    source_revision: {
      repo_head: gitHead(changeDir ?? process.cwd()),
      artifact_revision: computeRevision(changeDir),
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

- ${f.capability}

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
- 闸门记录：实施批准：待批准

> Quick 车道无 \`design.md\` 属预期：\`openspec status\` 显示 design 未完成不代表变更不完整，
> 向用户解释时引用本行即可；不要为凑 status 写假 design。
`;

/** @param {{goal: string, requirement: string}} f */
const quickSpec = (f) => `## ADDED Requirements

### Requirement: ${f.requirement}

系统必须 ${f.goal}。

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
  - 对应需求/场景：${f.requirement} / 基本行为
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
 * @param {{changeDir: string, capability: string, goal: string, impact: string, requirement: string | null}} args
 */
function cmdQuickPack(args) {
  const changeDir = resolve(args.changeDir);
  if (existsSync(changeDir) && readdirSync(changeDir).length > 0) {
    const existing = readdirSync(changeDir);
    console.error(
      `ERROR: change dir not empty (${existing.slice(0, 5).join(", ")}…) — quick-pack never overwrites`
    );
    return 2;
  }
  mkdirSync(changeDir, { recursive: true });
  const anchor = changeAnchor(changeDir);
  const fields = {
    goal: args.goal,
    capability: args.capability,
    impact: args.impact,
    anchor,
    changeId: basename(changeDir),
    requirement: args.requirement ?? args.goal,
  };

  writeFileSync(join(changeDir, "proposal.md"), quickProposal(fields), "utf-8");
  const specDir = join(changeDir, "specs", args.capability);
  mkdirSync(specDir, { recursive: true });
  writeFileSync(join(specDir, "spec.md"), quickSpec(fields), "utf-8");
  writeFileSync(join(changeDir, "tasks.md"), quickTasks(fields), "utf-8");

  const { digest } = hashChange(changeDir);
  console.log(`scaffolded Quick change at ${changeDir}`);
  console.log(`artifact_revision (pre-edit): sha256:${digest}`);
  console.log(
    "next: fill the <placeholders>, run `openspec validate`, present the contract, and record " +
      "the user go bound to the post-edit artifact_revision (re-run hash_change_artifacts.mjs)."
  );
  return 0;
}

/**
 * @param {{changeDir: string, reviewStatus: string, reviewer: string | null, evidence: string[],
 *          specCoherence: string, approvedBy: string | null, previous: string | null,
 *          nextAction: string | null, out: string | null}} args
 */
function cmdCloseOut(args) {
  const changeDir = resolve(args.changeDir);
  if (!isDir(changeDir)) {
    console.error(`ERROR: change dir does not exist: ${changeDir}`);
    return 2;
  }

  // 1. Machine checks on tasks/verification (the R3 rework hotspot).
  const claim = spawnSync(
    process.execPath,
    [VALIDATE_DELIVERY_CHANGE, changeDir, "--claim-verified"],
    { encoding: "utf-8" }
  );
  process.stderr.write(claim.stderr ?? "");
  console.log((claim.stdout ?? "").trim());
  if (claim.status !== 0) {
    console.error("close-out blocked: fix tasks/verification anchors above, then re-run.");
    return 1;
  }

  // 2. Verified execute handoff draft.
  const handoff = buildHandoff("delivery-execute-verify", changeDir, args.previous);
  const revision = handoff.source_revision.artifact_revision;
  const payload = handoff.stage_payload;
  payload.overall_status = "verified";
  payload.fresh_verification_evidence = args.evidence;
  payload.spec_coherence = args.specCoherence;
  Object.assign(payload.code_review, {
    status: args.reviewStatus,
    reviewer: args.reviewer,
  });
  Object.assign(handoff.gate_status, {
    status: "pass",
    summary: `新鲜验证 + 独立审查（${args.reviewer ?? "independent reviewer"}）通过；归档移交 OpenSpec`,
    evidence: [...args.evidence],
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
 * @returns {{opts: Record<string, any>, positional: string[], error: string | null}}
 */
function parseOptions(argv, spec, arrays = new Set()) {
  /** @type {Record<string, any>} */
  const opts = {};
  /** @type {string[]} */
  const positional = [];
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg.startsWith("--")) {
      const key = spec[arg];
      if (!key) return { opts, positional, error: `unknown option: ${arg}` };
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
  quick-pack --change-dir <dir> --capability <cap> --goal <text> --impact <text> [--requirement <text>]
      scaffold a Quick/Debug-Low lightweight change
  close-out --change-dir <dir> --review-status <pass|warn> [--reviewer <id>] [--evidence <line>]...
            [--spec-coherence <pass|warn>] [--approved-by <who>] [--previous <id>]
            [--next-action <op>] [--out <file>]
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
    const { opts, error } = parseOptions(rest, {
      "--change-dir": "changeDir",
      "--capability": "capability",
      "--goal": "goal",
      "--impact": "impact",
      "--requirement": "requirement",
    });
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
    });
  }

  console.error(`ERROR: unknown command: ${command}\n\n${USAGE}`);
  return 2;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exit(main());
}
