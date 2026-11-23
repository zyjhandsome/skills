# Environment Preflight

Run this **before** dependency resolution, owner classification, impact work, or
writing reports. Failure of a **hard** tool gate is a batch-wide stop.

## Probe order

Preferred executable:

```bash
python -B "<skill-dir>/scripts/preflight.py" <project-root> --build-tool auto --timeout 20 --json
```

`<skill-dir>` is the directory containing this skill's `SKILL.md`. If `python` is
missing, try `python3`, then `py -3`. `--skip-network` exists for unit tests
only; an analysis run must not pass it.

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
| JDK | `java -version` | Record major/vendor. If `java` is not on PATH, the script searches `JAVA_HOME`, common install roots, and SDKMAN, and prefers a JDK whose major matches the project declaration. Host vs project mismatch → **record only**, do not block. |
| Maven (when selected) | Prefer `mvn -v` on PATH. If that entry is missing or fails, `./mvnw -v` (or `mvnw.cmd`, including a parent directory) is a **graded pass**. | Record `build_tool_source=system` or `wrapper`. |
| Gradle (when selected) | Prefer `./gradlew -v` (or `gradlew.bat`) when the wrapper exists, including in a parent directory. Use `gradle -v` only when there is no wrapper, or when the wrapper itself fails. | The wrapper is the version the build locked. |
| Python | Prefer PATH `python --version` or `python3 --version`; if missing, the interpreter running `preflight.py` (`sys.executable`) is a **graded pass** (`python_source=current-interpreter`). | Needed for `scripts/validate_report.py`. Record which executable passed. |

**Graded pass rules:**

1. Maven prefers a working system `mvn`. Gradle prefers the project wrapper when
   the script exists, because a global `gradle` often cannot read that build.
2. A failing PATH entry is not final: try the other candidate before blocking.
   Wrapper-only is a **graded pass** when `-v` exits 0. State
   `build_tool_source=wrapper` plus wrapper path/version in 基线与假设.
3. If **neither** system CLI nor wrapper works → hard `blocked` (no report write).
   A settings-only Gradle root (`settings.gradle` / `settings.gradle.kts` and no
   `build.gradle`) is still a Gradle root.
4. After a graded pass, use that same executable for non-mutating
   `dependency:tree` / `dependencies` / `dependencyInsight`.
5. If system and wrapper disagree on major version, record both. Maven resolution
   follows the candidate that passed; Gradle resolution stays on the wrapper when
   the wrapper passed.

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
