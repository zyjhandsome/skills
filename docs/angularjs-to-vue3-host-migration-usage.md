# AngularJS To Vue3 Host Migration Playbook Usage

Use `angularjs-to-vue3-host-migration-playbook.md` when migrating AngularJS/jQuery/JSP/Thymeleaf mixed pages into an existing Vue3 host through the Delivery wave sequence.

## How To Run

1. Fill the playbook session header once with `<A>`, `<B>`, and `<UNITS>`.
2. Start a new session per wave and paste the session header plus exactly one wave prompt.
3. Use the complete skill id `angularjs-to-vue3-host-migration` in CONFIG, handoff, next_skill, and reports.
4. Keep all authoritative evidence under `<CHANGE_DIR>/evidence/angularjs-hosted-vue3-migration/`.
5. Treat `_live-eval*` and temporary report folders as lab output only.

## Routes

Main path: Wave 1 -> Wave 2 -> Wave 3 new-landing -> Wave 4 -> Wave 5 -> Wave 6 -> Wave 7.

Repair fast lane: Wave 1 -> Wave 2 -> Wave 3 repair -> Wave 4R -> Wave 6 -> Wave 7. Wave 4R combines the session only; it still needs scope/spec approval and implementation-go approval as separate records.

## Hard Stops

- No B application code changes before Wave 6.
- No Wave 6 when implementation go is denied, simulated, stale, or bound to an old artifact revision.
- No completion claim while MATRIX rows remain skeleton, missing, mismatched, or wired-unverified.
- No completion claim from Delivery `verified_with_residuals`.
