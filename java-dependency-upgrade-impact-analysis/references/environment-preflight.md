# Environment Preflight

Run this **before** dependency resolution, owner classification, impact work, or
writing reports. Failure of a **hard** tool gate is a batch-wide stop.

## Probe order

Preferred executable:

```bash
python scripts/preflight.py <project-root> --build-tool auto --timeout 20 --json
```

Exit codes from `scripts/preflight.py`:

| Exit | Meaning |
|---|---|
| `0` | Hard tool gates passed (JDK + selected build tool + Python) |
| `5` | Hard gate failed (JDK / selected tool / Python) |
| `6` | Dual Maven+Gradle roots and no `--build-tool` → **ask which tool**; not a tool hard-stop |

The JSON preserves the exact command, executable/source, exit code, raw stdout
and stderr. Network results are reported independently and never turn exit `0`
into `5`/`6`. Dual-build exit `6` sets `needs_build_tool_selection=true` and
leaves `hard_gates_passed=false` only because no tool was selected yet — Agent
must ask, then re-run with `--build-tool maven|gradle`. Do **not** treat exit `6`
as batch-wide environment `blocked`.

1. Detect the build system for this analysis (Maven and/or Gradle roots).
2. If both Maven and Gradle look like production entry points and the caller did
   not choose: **ask which tool to use** (script exit `6`). Do not require both
   on PATH.
3. Run the probes below for JDK, the **selected** build tool, and Python.
4. In the same wave, run the network probes in `reachability-and-upstream.md`
   (registry then GitHub API). Network outcome does **not** use the tool
   hard-stop table below.

## Tool probes (graded build-tool gate)

| Gate | Pass command (exit 0) | Notes |
|---|---|---|
| JDK | `java -version` | Record major/vendor. If `java` is not on PATH, locate an installed JDK and set `JAVA_HOME` (and PATH) for the session before re-probing — still the same hard gate. Host vs project `release` / toolchain / `java.version` mismatch → **record only**, do not block. |
| Maven (when selected) | Prefer `mvn -v` on PATH. If missing, `./mvnw -v` (or `mvnw.cmd`) is a **graded pass**. | Record `build_tool_source=system` or `wrapper`. |
| Gradle (when selected) | Prefer `gradle -v` on PATH. If missing, `./gradlew -v` (or `gradlew.bat`) is a **graded pass**. | Same as Maven. |
| Python | Prefer PATH `python --version` or `python3 --version`; if missing, the interpreter running `preflight.py` (`sys.executable`) is a **graded pass** (`python_source=current-interpreter`). | Needed for `scripts/validate_report.py`. Record which executable passed. |

**Graded pass rules:**

1. System CLI on PATH is preferred when both exist.
2. Wrapper-only is allowed for analysis when the wrapper script exists in the
   project root (or module root in use) and `-v` exits 0. State clearly in
   基线与假设：`build_tool_source=wrapper` plus wrapper path/version.
3. If **neither** system CLI nor wrapper works → hard `blocked` (no report write).
4. After a graded/wrapper pass, use that same wrapper for non-mutating
   `dependency:tree` / `dependencies` / `dependencyInsight`.
5. If system and wrapper disagree on major version, record both; prefer the
   wrapper for resolution once the gate passed.

Always record active Maven profiles / Gradle properties as `build_variant`.
Also record `build_variant_source`. A profile auto-activated by the analyst's
host JDK/OS is `host-auto-activated`, not proof of the production build variant;
set `production_variant_confirmed=unknown` until caller/CI config confirms it.
Run subsequent tree/insight probes on a bounded leaf module or named scope, with
an explicit timeout. Do not begin with an unbounded whole-reactor dependency tree.

Dual-build repos: only the **selected** tool must pass. The unused tool missing
is noted in chat assumptions, not a block.

## Failure semantics (tools / Python)

| Outcome | Action |
|---|---|
| JDK or Python fails; or selected build tool has neither system nor wrapper | Set packet `analysis_status=blocked`, `decision_status=not_needed`, `batch_implementation_gate=frozen`. List exact missing probes in the chat. Do not invent baselines, run tree/insight, or ask the confirmation queue. Do not write report/evidence files. |
| Dual-build ambiguous (`preflight.py` exit `6`) | Ask Maven vs Gradle in chat; do **not** set batch-wide `blocked` or invent baselines. Re-run with `--build-tool` after the human picks. |
| Wrapper-only / current-interpreter graded pass | Continue; document `build_tool_source=wrapper` and/or `python_source=current-interpreter`. |
| Tools pass; host JDK ≠ project declaration | Continue; state both values as assumptions. |
| Tools pass; registry or GitHub OK | Stay online for upstream evidence. |
| Tools pass; both registry and GitHub fail | Ask the human; only then continue offline — see `reachability-and-upstream.md`. This is **not** a tool-preflight failure. |

Hard stop means: no pom/Gradle skim that invents effective versions; no partial
inventory sold as analysis. Re-run preflight after the environment is fixed.

## What this is not

- Not a caller-input requirement (humans need not paste JDK/Maven versions).
- Not JDK–project alignment enforcement.
- Not a substitute for target existence or baseline mismatch gates.
- Not permission to skip Python because “we will validate later”.
