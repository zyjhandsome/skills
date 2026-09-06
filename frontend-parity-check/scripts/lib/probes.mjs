// In-page probes. Functions must stay closure-free: Playwright ships their source to the browser.

export const STYLE_PROPS = [
  'display', 'position', 'box-sizing', 'flex-direction', 'justify-content', 'align-items', 'gap',
  'grid-template-columns', 'width', 'height', 'min-height', 'max-width', 'overflow',
  'margin', 'padding', 'font-family', 'font-size', 'font-weight', 'line-height', 'letter-spacing',
  'text-align', 'white-space', 'color', 'background-color', 'background-image',
  'border-top-width', 'border-bottom-width', 'border-color', 'border-radius', 'box-shadow',
  'opacity', 'z-index', 'transform',
];

/** Probe set applied to every page unless the route overrides it. */
export const DEFAULT_PROBES = [
  { id: 'body', selector: 'body' },
  { id: 'heading', selector: 'h1, h2, .page-title, .el-page-header__title' },
  { id: 'primary-button', selector: 'button.el-button--primary, .btn-primary, button[type=submit], .ant-btn-primary' },
  { id: 'button', selector: 'button' },
  { id: 'input', selector: 'input:not([type=hidden]), .el-input__inner, .ant-input' },
  { id: 'select', selector: 'select, .el-select, .ant-select' },
  { id: 'form-item', selector: '.el-form-item, .ant-form-item, .form-group, form label' },
  { id: 'table-header-cell', selector: '.el-table th, .vxe-header--column, thead th, [role=columnheader]' },
  { id: 'table-body-cell', selector: '.el-table__body td, .vxe-body--column, tbody td, [role=gridcell]' },
  { id: 'card', selector: '.el-card, .ant-card, .card, .panel' },
  { id: 'link', selector: 'a[href]' },
];

/** Compact semantic snapshot of what a user can see and interact with. */
export function domDigestFn() {
  const clip = (s, n) => (s || '').replace(/\s+/g, ' ').trim().slice(0, n);
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    const s = getComputedStyle(el);
    return s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
  };
  const text = (el) => clip(el.innerText || el.textContent, 200);
  const all = (sel, root = document) => Array.from(root.querySelectorAll(sel)).filter(visible);
  const box = (el) => {
    const r = el.getBoundingClientRect();
    return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)];
  };

  const labelFor = (el) => {
    if (el.getAttribute('aria-label')) return clip(el.getAttribute('aria-label'), 80);
    if (el.id) {
      const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (l) return clip(l.textContent, 80);
    }
    const wrap = el.closest('label, .el-form-item, .ant-form-item, .form-group');
    if (wrap) {
      const l = wrap.querySelector('label, .el-form-item__label, .ant-form-item-label');
      if (l) return clip(l.textContent, 80);
    }
    return '';
  };

  const gridSelectors = 'table, .el-table, .vxe-table, .ant-table, [role=grid], [role=table]';
  const grids = all(gridSelectors)
    .filter((g) => !g.parentElement?.closest(gridSelectors))
    .map((g) => {
      const heads = Array.from(g.querySelectorAll('thead th, .el-table__header th, .vxe-header--column, [role=columnheader]'));
      const headTexts = heads.map((h) => clip(h.innerText || h.textContent, 40)).filter(Boolean);
      const bodyRows = Array.from(g.querySelectorAll('tbody tr, .el-table__body tbody tr, .vxe-body--row, [role=row]'))
        .filter((r) => !r.closest('thead'));
      const first = bodyRows[0];
      return {
        columns: [...new Set(headTexts)],
        columnCount: headTexts.length,
        rowCount: bodyRows.length,
        firstRow: first ? Array.from(first.children).map((c) => clip(c.innerText || c.textContent, 60)) : [],
        box: box(g),
      };
    });

  return {
    title: document.title,
    url: location.href,
    lang: document.documentElement.lang || '',
    headings: all('h1,h2,h3,h4,[role=heading]').map((e) => ({ tag: e.tagName.toLowerCase(), text: text(e) })),
    actions: all('button,[role=button],input[type=submit],input[type=button],a.btn,.el-button,.ant-btn')
      .map((e) => ({
        text: clip(e.innerText || e.value || e.getAttribute('aria-label'), 60),
        disabled: !!(e.disabled || e.getAttribute('aria-disabled') === 'true' || e.classList.contains('is-disabled')),
      }))
      .filter((e) => e.text),
    fields: all('input:not([type=hidden]),select,textarea').map((e) => ({
      tag: e.tagName.toLowerCase(),
      type: e.getAttribute('type') || '',
      name: e.getAttribute('name') || e.id || '',
      label: labelFor(e),
      placeholder: e.getAttribute('placeholder') || '',
      required: !!e.required,
      disabled: !!e.disabled,
      readOnly: !!e.readOnly,
      options: e.tagName === 'SELECT' ? Array.from(e.options).map((o) => clip(o.textContent, 40)) : undefined,
    })),
    links: all('a[href]').map((e) => ({ text: text(e).slice(0, 60), href: e.getAttribute('href') })),
    images: all('img').map((e) => ({ alt: e.getAttribute('alt') || '', src: (e.currentSrc || e.src || '').slice(-120), natural: [e.naturalWidth, e.naturalHeight] })),
    grids,
    landmarks: all('header,nav,main,aside,footer,[role=navigation],[role=main]')
      .map((e) => ({ tag: e.tagName.toLowerCase(), box: box(e) })),
    textOutline: all('body *')
      .filter((e) => e.children.length === 0 && (e.innerText || e.textContent || '').trim())
      .map((e) => clip(e.innerText || e.textContent, 120))
      .filter(Boolean)
      .slice(0, 600),
    documentHeight: Math.round(document.documentElement.scrollHeight),
    counts: {
      elements: document.querySelectorAll('*').length,
      visibleElements: all('body *').length,
    },
  };
}

/** Computed style + geometry for each probe's first visible match. */
export function styleProbeFn({ probes, props }) {
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    const s = getComputedStyle(el);
    return s.visibility !== 'hidden' && s.display !== 'none';
  };
  const out = {};
  for (const probe of probes) {
    let el = null;
    let count = 0;
    try {
      const nodes = Array.from(document.querySelectorAll(probe.selector));
      count = nodes.length;
      el = nodes.find(visible) || null;
    } catch {
      out[probe.id] = { selector: probe.selector, error: 'invalid selector' };
      continue;
    }
    if (!el) {
      out[probe.id] = { selector: probe.selector, found: false, matches: count };
      continue;
    }
    const cs = getComputedStyle(el);
    const style = {};
    for (const p of props) style[p] = cs.getPropertyValue(p).trim();
    const r = el.getBoundingClientRect();
    out[probe.id] = {
      selector: probe.selector,
      found: true,
      matches: count,
      tag: el.tagName.toLowerCase(),
      classes: (el.getAttribute('class') || '').split(/\s+/).filter(Boolean).slice(0, 12),
      box: { w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y) },
      style,
    };
  }
  return out;
}
