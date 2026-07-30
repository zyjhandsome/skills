# Environment Preflight

Run this **before** dependency resolution, owner classification, impact work, or
writing reports. Failure of a **tool** gate is a batch-wide hard stop.

## Probe order

1. Detect the build system for this analysis (Maven and/or Gradle roots).
2. If both Maven and Gradle look like production entry points and the caller did
   not choose: **ask which tool to use**. Do not require both on PATH.
3. Run the probes below for JDK, the **selected** build tool, and Python.
4. In the same wave, run the network probes in `reachability-and-upstream.md`
   (registry then GitHub). Network outcome does **not** use the tool hard-stop
   table below.

## Tool probes (PATH only)

Wrappers (`mvnw` / `gradlew`) **do not** satisfy the gate. Prefer system
commands on PATH.

| Gate | Pass command (exit 0) | Notes |
|---|---|---|
| JDK | `java -version` | Record major/vendor. Host vs project `release` / toolchain / `java.version` mismatch → **record only**, do not block. |
| Maven (when selected) | `mvn -v` | System `mvn` only. |
| Gradle (when selected) | `gradle -v` | System `gradle` only. |
| Python | `python --version` or `python3 --version` | Needed for `scripts/validate_report.py`. Either command passing is enough. |

Dual-build repos: only the **selected** tool must pass. The unused tool missing
from PATH is noted in chat assumptions, not a block.

## Failure semantics (tools / Python)

| Outcome | Action |
|---|---|
| Any required tool/Python probe fails | Set packet `analysis_status=blocked`, `decision_status=not_needed`, `batch_implementation_gate=frozen`. List exact missing probes in the chat. Do not read manifests for a fake baseline, run tree/insight, or ask the confirmation queue. Do not write report/evidence files. |
| Tools pass; host JDK ≠ project declaration | Continue; state both values as assumptions. |
| Tools pass; registry or GitHub OK | Stay online for upstream evidence. |
| Tools pass; both registry and GitHub fail | Ask the human; only then continue offline — see `reachability-and-upstream.md`. This is **not** a tool-preflight failure. |

Hard stop means: no pom/Gradle skim that invents effective versions; no partial
inventory sold as analysis. Re-run preflight after the environment is fixed.

## Gate vs later resolution commands

The hard gate requires **system** `mvn` / `gradle` on PATH. After that passes,
non-mutating resolution may use `./mvnw` / `./gradlew` when present (often pins
the correct tool version). If wrapper and system disagree, record both; prefer
the wrapper for tree/insight **only after** the system gate passed. Wrappers
never satisfy the gate alone.

## What this is not

- Not a caller-input requirement (humans need not paste JDK/Maven versions).
- Not JDK–project alignment enforcement.
- Not permission to use wrappers when system `mvn`/`gradle` is absent.
- Not a substitute for target existence or baseline mismatch gates.
