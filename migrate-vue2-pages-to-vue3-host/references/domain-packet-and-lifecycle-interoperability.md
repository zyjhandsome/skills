# Domain packet and lifecycle interoperability

## Neutral evidence contract

Use one revision-bound evidence packet across assessment, design, and
verification rounds:

```yaml
schema_version: vue-migration-domain/v1
type: vue-migration-domain
authority: domain_evidence_only
packet_id: <stable unit id plus revision>
generated_at: <RFC3339>
mode: assess | design | verify
source:
  root: <absolute or caller-relative path>
  revision: <commit or content digest>
host:
  root: <absolute or caller-relative path>
  revision: <commit or content digest>
migration_unit:
  id: <stable id>
  source_entry: <path/route>
  host_entry: <path/route>
intent:
  goal: <observable result>
  non_goals: []
evidence:
  facts: []
  inferences: []
  decisions: []
closure: []
style_closure:
  status: pending | complete | blocked
  entries: []
  unresolved: []
host_protocols: []
runtime_evidence:
  schema: runtime-compatibility-evidence/v1
  path_or_inline: null
visual_evidence:
  schema: visual-parity-evidence/v1
  path_or_inline: null
design:
  target: null
  slices: []
rollback:
  status: missing | designed | tested | retired
implementation_authorization:
  status: missing | stale | approved
  source: direct_user | external_lifecycle
  approved_by: null
  approved_at: null
  binds_to_source_revision: null
  binds_to_host_revision: null
  allowed_scope: []
  forbidden_scope: []
  validation_obligations: []
  rollback_conditions: []
verification:
  status: not_run | fail | pass
  evidence: []
blockers: []
packet_digest: <digest of canonical packet content>
```

For a user-visible unit, `design` and `verify` packets require
`style_closure.status: complete`, at least one evidenced entry, and no unresolved
items. Entries use `id / kind / source / evidence / disposition / target` and
cover the page-owned and inherited style/assets described in
`discovery-and-page-closure.md`. A generic `closure` array without this style
inventory is not sufficient for design readiness.

For persisted JSON, canonicalize objects by recursively sorting keys, omit the
`packet_digest` field from the hash input, preserve array order, and write
`packet_digest` as `sha256:<64-hex>`. Validate with
`scripts/validate_domain_packet.mjs`; optionally pass the current source and host
revisions to reject stale packets.

The shape is a contract, not a requirement to hand-write YAML. Use JSON or
Markdown tables when the caller needs those formats, but preserve field semantics.
Do not store secrets, screenshots, logs, or large report bodies inline; reference
paths and digests.

For `verification.status: pass`, each `path_or_inline` must be either a complete
inline evidence object or `{path: <json>, digest: sha256:<64-hex>}`. Bare path
strings are rejected because they neither prove artifact identity nor allow the
domain validator to validate the nested pass claim.

## Authority boundary

The packet owns migration-domain evidence only. It does not own:

- product requirements or acceptance approval;
- implementation task completion;
- user authorization;
- release, deployment, traffic, monitoring, or shutdown state;
- another system's completion or archive claim.

Authorization fields copy a reference to an observed approval; they do not create
approval. The caller remains authoritative for lifecycle state.

## Multi-round recovery

At the start of every round:

1. Locate the caller-supplied packet, or begin inline when none exists.
2. Compare current A/B revisions with the packet.
3. Compare approved scope, dependency lock baseline, and visual baseline source.
4. Mark affected sections stale before collecting new evidence.
5. Recompute the packet digest after updates.
6. Continue only in the requested mode and only with current inputs.

Invalidation rules:

| Change | Invalidate |
|---|---|
| source revision | closure, source behavior/visual baseline, dependency demand, design, authorization, verification |
| host revision | host integration facts, dependency/runtime evidence, design, authorization, verification |
| goal/acceptance | design, slices, authorization, verification |
| dependency disposition/runtime | affected slices, authorization, build evidence, verification |
| visual policy/baseline | visual plan, authorization obligations, visual verification |
| slice or validation change | affected authorization and verification |

Never merge stale and current evidence into one pass claim.

## Standalone operation

This Skill has no execute mode. Never mutate A or B.

- `assess`: return the packet inline unless the user provides an output directory.
- `design`: update target, slices, validation and rollback without mutation.
- `verify`: run fresh read-only checks against the current revision pair and record
  evidence. A host revision change invalidates the earlier implementation authorization
  reference. If verification itself would mutate code, dependencies, fixtures,
  runtime, or feature switches, stop and return discovery backflow instead of
  hiding mutation inside `verify`.

When no lifecycle system exists, direct user authorization may populate the
authorization reference. It must still bind exact revisions and scope. The
reference still does not authorize this Skill to edit code.

After an external implementer changes the approved host slices, use `verify` to
refresh domain evidence against the current revision pair.

## External lifecycle interoperability

Accept a lifecycle-agnostic input envelope:

```text
goal / non_goals / acceptance
source_revision / host_revision
allowed_scope / forbidden_scope
risk_and_constraints
implementation_authorization reference
validation obligations
rollback and release boundaries
artifact_directory (optional)
```

Return the domain packet path/digest or inline packet. The external lifecycle may
cite selected claims and must recompute its own risk, approvals, tasks, visual
record, verification, and completion state. Never require the lifecycle to adopt
this packet as its state schema.

Use `<artifact_directory>/evidence/vue-cross-repo-migration/` only when the caller
explicitly supplies an artifact directory. Otherwise remain inline; never invent a
project-root report folder.

## Discovery backflow

Pause affected mutation and return a neutral discovery packet when:

- behavior, acceptance, permission, URL compatibility, or visual policy changes;
- target design, dependency disposition, runtime, cost, rollback, or validation
  strategy changes;
- authorization is missing, stale, or does not cover the operation;
- current evidence contradicts the caller's lifecycle state.

Include:

```text
discovery / evidence / affected_scope / invalidated_evidence /
decision_needed / recommended_resolution / safe_resume_point
```

The caller decides how to update its own artifacts and gates.
