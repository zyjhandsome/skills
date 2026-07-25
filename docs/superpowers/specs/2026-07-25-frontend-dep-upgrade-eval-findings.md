# Frontend Dependency Upgrade Impact Analysis — Post-Hardening Findings

Date: 2026-07-25  
Skill: `frontend-dependency-upgrade-impact-analysis/`  
Host baseline: Node `v26.5.0`, Python `3.14.6`  
Suite: `python tests/run_all.py` → **63 tests OK**

## Dimension matrix

| ID | Dimension | Score | Notes |
|---|---|---|---|
| D1 | Contract integrity | Pass | SKILL/refs document `importer_resolution`, exit `5`, and Node `unknown` selected-empty rule; structure test keeps SKILL &lt; 200 lines |
| D2 | Scope / baseline | Pass | VoiceInk L2: exit `5`, `importer_resolution=failed`, `analysis_status=blocked`, `change_type=unknown`, action `resolve-frontend-workspace` |
| D3 | Impact evidence quality | Partial | Generator still heuristic for call graphs; Agent review required before `complete` |
| D4 | Risk model repeatability | Pass | Seven-factor unit lock + synthetic dual-run equal totals |
| D5 | Node gate | Pass | No-constraint `unknown` clears `selected_project_node`; synthetic pin `20.18.0` vs host `26.5.0` → `manager-missing` (not `compatible-current`) |
| D6 | Safety boundary | Pass | Runner approval granularity + restore tests unchanged |
| D7 | Agent operability | Pass | Explicit CLI precondition + completion gate for workspace/Node unknown |
| D8 | Stability | Pass | `test_synthetic_fixture_dual_run_is_stable` |
| D9 | Robustness | Pass | Missing `package.json` short-circuits to blocked packet with exit `5`, not soft “added upgrade” |
| D10 | Testability | Pass | L0 unit suite + checked-in L1 fixture; L2 VoiceInk as external negative control |

## Contrast transcripts

### L1 — synthetic frontend (offline)

```text
python scripts/generate_upgrade_report.py fixtures/synthetic-frontend \
  --upgrade axios::1.7.9 --offline --output-dir %TEMP%/synthetic-dep-report
```

Observed: exit `0`; `importer_resolution=confirmed`; `node_runtime_status=manager-missing`; host `26.5.0`; selected project Node `20.18.0`; fixture `.nvmrc` unchanged (`20.18.0`).

### L2 — VoiceInk negative control (read-only)

```text
python scripts/generate_upgrade_report.py D:\Hzhao\AI_Test\VoiceInk-main \
  --upgrade axios::1.7.9 --offline --output-dir %TEMP%/voiceink-dep-report-after
```

Observed: exit `5`; `importer_resolution=failed`; `analysis_status=blocked`; project Node `未建立`; recommended action `resolve-frontend-workspace`; no `npm install` guidance for VoiceInk; VoiceInk tree not modified.

## P0 closed

1. Host Node no longer selected when project constraints are absent (`unknown`).
2. Missing frontend `package.json` → `importer_resolution=failed`, exit `5`, no default `added` upgrade framing.
3. Synthetic fixture + dual-run locks; docs synced.

## P1 backlog

- Automatic multi-workspace discovery beyond ask/stop (generator still assumes resolved importer root).
- Richer seven-factor explainability in Markdown.
- HTTP cache operator docs for stale version-identity edge cases.
