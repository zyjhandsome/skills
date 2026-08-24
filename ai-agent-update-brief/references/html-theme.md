# HTML 主题契约（亮色 / 暗黑）

Every standalone brief must ship **both** modes in one file. Copy the tokens, toggle markup, and scripts below. Do not invent a new palette unless the user asks.

## Required behavior

- Modes: `light`（亮色）and `dark`（暗黑）.
- Default: follow `prefers-color-scheme` until the reader picks a mode.
- Persist the explicit pick in `localStorage` key `ai-agent-brief-theme` (`light` | `dark`).
- Put the toggle in the **sticky** nav so it stays visible while scrolling.
- Default Chinese labels: `亮色` / `暗黑`. English reports: `Light` / `Dark`.
- Drive **all** colors through CSS variables. Component rules must not contain leftover hex colors.
- Set `color-scheme` so scrollbars and native controls match the mode.
- After writing the HTML, verify **both** modes: first screen (header + 核心结论 cards), one table with chips, sticky nav, and footer.
- Keep the header as a dark masthead in both modes. The paper, cards, tables, chips, and sticky nav are what flip. Do not turn the header into a light bar unless the user asks.

## Head script (before CSS, prevents flash)

```html
<script>
(function () {
  try {
    var saved = localStorage.getItem('ai-agent-brief-theme');
    if (saved === 'light' || saved === 'dark') {
      document.documentElement.setAttribute('data-theme', saved);
    }
  } catch (e) {}
})();
</script>
```

## Toggle markup (last child of `nav.toc`)

```html
<div class="theme-switch" role="group" aria-label="外观">
  <button type="button" data-theme-set="light" aria-pressed="false">亮色</button>
  <button type="button" data-theme-set="dark" aria-pressed="false">暗黑</button>
</div>
```

## Tokens and component rules

Keep these variable names. Light values live on `:root`. Dark values apply when the OS is dark **or** `data-theme="dark"`. An explicit `data-theme="light"` always wins over the OS.

```css
:root {
  color-scheme: light;
  --ink: #1b1d21;
  --muted: #5b616b;
  --line: #d9dde3;
  --paper: #f7f5f1;
  --card: #ffffff;
  --accent: #1f4b99;
  --warn: #8a3b12;
  --risk: #9b1c2e;
  --ok: #1b6b45;
  --chip: #eef1f6;
  --header-bg: #1b1d21;
  --header-fg: #f4f1ea;
  --header-muted: #c9c4b8;
  --rule-bg: #2a2d33;
  --rule-fg: #efe8d8;
  --rule-accent: #c9a227;
  --toc-bg: rgba(247, 245, 241, 0.94);
  --toc-link-bg: #ffffff;
  --th-bg: #eef1f6;
  --code-bg: #eef1f6;
  --switch-bg: #e8e4dc;
  --switch-active-bg: #ffffff;
  --chip-break-bg: #f8d7dc;
  --chip-mig-bg: #fde8d2;
  --chip-sec-bg: #f3e2c8;
  --chip-sec-fg: #6d3b08;
  --chip-price-bg: #e3efe7;
  --chip-new-bg: #dce7f8;
  --chip-none-bg: #ececec;
  --chip-none-fg: #555555;
  --focus: #1f4b99;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --ink: #ece8e1;
    --muted: #9aa1ab;
    --line: #323842;
    --paper: #121418;
    --card: #1b1f26;
    --accent: #8fb4f0;
    --warn: #f0b27a;
    --risk: #f08a96;
    --ok: #7dcea0;
    --chip: #252a33;
    --header-bg: #0d0f12;
    --header-fg: #f4f1ea;
    --header-muted: #a8a396;
    --rule-bg: #252830;
    --rule-fg: #efe8d8;
    --rule-accent: #d4b44a;
    --toc-bg: rgba(18, 20, 24, 0.92);
    --toc-link-bg: #1b1f26;
    --th-bg: #222730;
    --code-bg: #252a33;
    --switch-bg: #252a33;
    --switch-active-bg: #323842;
    --chip-break-bg: #3a1f24;
    --chip-mig-bg: #3a2a18;
    --chip-sec-bg: #3a2e18;
    --chip-sec-fg: #f0c48a;
    --chip-price-bg: #1c3328;
    --chip-new-bg: #1d2c44;
    --chip-none-bg: #2a2d33;
    --chip-none-fg: #b0b4ba;
    --focus: #8fb4f0;
  }
}

[data-theme="dark"] {
  color-scheme: dark;
  --ink: #ece8e1;
  --muted: #9aa1ab;
  --line: #323842;
  --paper: #121418;
  --card: #1b1f26;
  --accent: #8fb4f0;
  --warn: #f0b27a;
  --risk: #f08a96;
  --ok: #7dcea0;
  --chip: #252a33;
  --header-bg: #0d0f12;
  --header-fg: #f4f1ea;
  --header-muted: #a8a396;
  --rule-bg: #252830;
  --rule-fg: #efe8d8;
  --rule-accent: #d4b44a;
  --toc-bg: rgba(18, 20, 24, 0.92);
  --toc-link-bg: #1b1f26;
  --th-bg: #222730;
  --code-bg: #252a33;
  --switch-bg: #252a33;
  --switch-active-bg: #323842;
  --chip-break-bg: #3a1f24;
  --chip-mig-bg: #3a2a18;
  --chip-sec-bg: #3a2e18;
  --chip-sec-fg: #f0c48a;
  --chip-price-bg: #1c3328;
  --chip-new-bg: #1d2c44;
  --chip-none-bg: #2a2d33;
  --chip-none-fg: #b0b4ba;
  --focus: #8fb4f0;
}

[data-theme="light"] {
  color-scheme: light;
}

html { background: var(--paper); }
header { background: var(--header-bg); color: var(--header-fg); }
.meta { color: var(--header-muted); }
.rule {
  background: var(--rule-bg);
  border-left-color: var(--rule-accent);
  color: var(--rule-fg);
}
nav.toc { background: var(--toc-bg); border-bottom-color: var(--line); }
nav.toc a { color: var(--accent); border-color: var(--line); background: var(--toc-link-bg); }
th { background: var(--th-bg); color: var(--muted); }
code { background: var(--code-bg); color: var(--ink); }
.chip.break { background: var(--chip-break-bg); color: var(--risk); }
.chip.mig { background: var(--chip-mig-bg); color: var(--warn); }
.chip.sec { background: var(--chip-sec-bg); color: var(--chip-sec-fg); }
.chip.price { background: var(--chip-price-bg); color: var(--ok); }
.chip.new { background: var(--chip-new-bg); color: var(--accent); }
.chip.none { background: var(--chip-none-bg); color: var(--chip-none-fg); }
```

## Toggle script (before `</body>`)

```html
<script>
(function () {
  var KEY = 'ai-agent-brief-theme';
  var root = document.documentElement;
  var buttons = document.querySelectorAll('[data-theme-set]');

  function current() {
    return root.getAttribute('data-theme') ||
      (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  }

  function apply(theme, persist) {
    root.setAttribute('data-theme', theme);
    if (persist) {
      try { localStorage.setItem(KEY, theme); } catch (e) {}
    }
    buttons.forEach(function (btn) {
      var on = btn.getAttribute('data-theme-set') === theme;
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  buttons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      apply(btn.getAttribute('data-theme-set'), true);
    });
  });

  apply(current(), false);
})();
</script>
```
