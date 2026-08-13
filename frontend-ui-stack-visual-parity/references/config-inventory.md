# Config inventory (Phase A)

Record each row as Fact (path + snippet) or Inference / unknown.

## Required fields

| Field | What to capture |
|---|---|
| `tailwind.present` | yes/no; config path (`tailwind.config.*` / CSS `@tailwind`) |
| `tailwind.preflight` | on/off (default on if corePlugins not disabling preflight) |
| `tailwind.prefix` | e.g. `tw-` / none |
| `tailwind.important` | selector/true/false/unset |
| `ui_kit` | e.g. `element-plus` / `ant-design-vue` / other + version from lock or package.json |
| `ui_kit.class_prefix` | e.g. `el-` |
| `ui_kit.theme_vars` | where `--el-*` (or peer) are set: `html` / `body` / `:root` / SCSS |
| `ui_kit.important` | any global important wrapper for the kit |
| `css_entry_order` | ordered list of global style imports (main.ts / main.scss / vite) |
| `table.primary` | `el-table` / `vxe-table` / other |
| `table.secondary` | optional; “specific scenarios only” if mixed |
| `icons` | e.g. `bootstrap-icons` + Element icons — note dual systems |
| `heavy_css_libs` | wangeditor / tree / DAG / etc. with own CSS |
| `legacy_selectors` | `/deep/`, `>>>`, old `::v-deep`, Element internal/structural selectors |
| `css_delivery` | global/scoped/module, `@layer`, route code splitting, dev vs production order |
| `teleport_roots` | body/custom append targets and theme-class/custom-property inheritance |
| `tailwind_dynamic` | constructed classes, safelist, content coverage, prefixed/unprefixed remnants |

## Suggested read order

1. `package.json` + lockfile versions for UI/CSS-related deps  
2. Tailwind config + root CSS that pulls Tailwind  
3. App entry style imports  
4. Theme/variable files for the UI kit  
5. Legacy/global override files and one primary list-page SFC (search form + table)
6. One built/dev matched-rule sample when import order or code splitting is suspect

## Notes

- `tw-` (or other) prefix **reduces class-name collision** but does **not** neutralize Preflight tag resets.  
- When `tailwind.present=no`, choose the `no-tailwind` diagnosis branch in
  `diagnosis-workflow.md` (kit major / reset / theme / Teleport first).
- Mixed `el-table` + `vxe-table`: primary sample follows `table.primary`; never let secondary drive global strategy.
