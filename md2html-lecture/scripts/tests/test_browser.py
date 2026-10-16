"""Opt-in browser checks. Set MD2HTML_BROWSER to a Chromium/Edge executable."""
import os

import pytest

from test_build_html import THREE_MD, _build


@pytest.fixture(scope="module")
def browser():
    executable = os.environ.get("MD2HTML_BROWSER")
    if not executable:
        pytest.skip("set MD2HTML_BROWSER to run browser verification")
    api = pytest.importorskip("playwright.sync_api")
    with api.sync_playwright() as playwright:
        instance = playwright.chromium.launch(executable_path=executable, headless=True)
        yield instance
        instance.close()


@pytest.fixture
def page(browser, tmp_path):
    output = _build(tmp_path, THREE_MD)
    figure = (
        '<figure class="diagram"><pre class="mermaid">flowchart LR\n'
        'A[步骤甲] --> B[步骤乙]\nB -. 尚未连接 .-> C[步骤丙]\n'
        '</pre><figcaption>步骤与缺口。</figcaption></figure>'
    )
    target = tmp_path / "sample_整理文档.html"
    target.write_text(output.replace('<h2 id="一节" class="sec">一节</h2>', '<h2 id="一节" class="sec">一节</h2>\n' + figure), encoding="utf-8")
    context = browser.new_context()
    context.route("**/cdn.jsdelivr.net/**", lambda route: route.abort())
    view = context.new_page()
    view.goto(target.as_uri(), wait_until="domcontentloaded")
    yield view
    context.close()


def open_settings(page):
    if page.locator("#settings-panel").is_hidden():
        page.locator("#settings-toggle").click()


def close_settings(page):
    if page.locator("#settings-panel").is_visible():
        page.locator("#settings-toggle").click()


def pick_theme(page, name):
    if page.locator("#theme-menu").is_hidden():
        page.locator("#theme-toggle").click()
    page.locator(f'[data-theme-choice="{name}"]').click()


def pick(page, setting, value):
    open_settings(page)
    page.locator(f'.seg[data-setting="{setting}"] button[data-value="{value}"]').click()


def other_theme(page):
    return "dark" if page.locator("html").get_attribute("data-theme") != "dark" else "sepia"


def test_transcript_toggle_restores_saved_choice(page):
    assert page.locator("details.dialogue-fold").evaluate_all("els => els.every(el => !el.open)")
    assert page.locator("#skim-toggle").get_attribute("aria-pressed") == "true"
    page.locator("#skim-toggle").click()
    assert page.locator("details.dialogue-fold").evaluate_all("els => els.every(el => el.open)")
    page.reload(wait_until="domcontentloaded")
    assert page.locator("details.dialogue-fold").evaluate_all("els => els.every(el => el.open)")
    page.locator("details.dialogue-fold > summary").first.click()
    assert page.locator("details.dialogue-fold").first.evaluate("el => !el.open")


def test_guest_filter_prints_all_speakers_and_restores_folds(page):
    page.locator("#skim-toggle").click()
    page.locator("#guest-only-toggle").click()
    assert not page.locator(".step.speaker-host").is_visible()
    assert page.locator(".step.speaker-guest-1").is_visible()
    page.reload(wait_until="domcontentloaded")
    assert not page.locator(".step.speaker-host").is_visible()
    page.locator("#skim-toggle").click()
    page.emulate_media(media="print")
    page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
    assert page.locator("details.dialogue-fold").evaluate_all("els => els.every(el => el.open)")
    assert page.locator(".step.speaker-host").is_visible()
    assert page.locator(".step.speaker-host").evaluate("el => getComputedStyle(el).display") == "grid"
    page.evaluate("window.dispatchEvent(new Event('afterprint'))")
    page.emulate_media(media="screen")
    assert page.locator("details.dialogue-fold").evaluate_all("els => els.every(el => !el.open)")
    page.locator("details.dialogue-fold > summary").first.click()
    assert not page.locator(".step.speaker-host").is_visible()
    assert page.locator("#guest-only-toggle").get_attribute("aria-pressed") == "true"


def test_offline_diagram_survives_theme_changes(page):
    text = page.locator(".mermaid-fallback").inner_text()
    assert text == "步骤甲 → 步骤乙\n步骤乙 ⇢（尚未连接）步骤丙"
    theme = page.locator("html").get_attribute("data-theme")
    pick_theme(page, other_theme(page))
    assert page.locator("html").get_attribute("data-theme") != theme
    assert page.locator(".mermaid-fallback").inner_text() == text
    pick_theme(page, theme)
    assert page.locator(".mermaid-fallback").inner_text() == text


def test_mobile_toc_opens_and_closes_from_keyboard(page):
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator("#toc-toggle").click()
    assert page.locator("#toc").get_attribute("aria-hidden") == "false"
    assert page.locator("#toc").get_attribute("aria-modal") == "true"
    page.keyboard.press("Escape")
    assert page.locator("#toc").get_attribute("aria-hidden") == "true"
    assert page.locator("#toc-toggle").evaluate("el => el === document.activeElement")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_theme_cycles_through_sepia_and_font_scale_persists(page):
    assert page.locator("[data-theme-choice]").count() == 3
    for name in ["reader", "dark", "sepia"]:
        pick_theme(page, name)
        assert page.locator("html").get_attribute("data-theme") == name
        assert page.locator("#theme-menu").is_hidden()             # a pick closes the menu
        assert page.locator(f'[data-theme-choice="{name}"]').get_attribute("aria-checked") == "true"
        if name == "reader":
            assert "Serif" in page.evaluate("getComputedStyle(document.querySelector('.content p')).fontFamily")
    page.reload(wait_until="domcontentloaded")
    assert page.locator("html").get_attribute("data-theme") == "sepia"
    for retired, kept in (("light", "sepia"), ("eink", "reader")):    # saved retired themes map over
        page.evaluate(f"localStorage.setItem('md2html-theme', '{retired}')")
        page.reload(wait_until="domcontentloaded")
        assert page.locator("html").get_attribute("data-theme") == kept
    page.locator("#theme-toggle").click()
    page.keyboard.press("Escape")
    assert page.locator("#theme-menu").is_hidden()
    assert page.locator("#theme-toggle").evaluate("el => el === document.activeElement")

    body_px = lambda: page.evaluate("parseFloat(getComputedStyle(document.querySelector('.content p')).fontSize)")
    base = body_px()
    assert page.locator("#font-reset").inner_text() == "100%"
    assert page.locator("#font-reset").is_disabled()
    for _ in range(5):
        page.locator("#font-up").click(force=True)
    assert page.locator("#font-up").is_disabled()
    assert page.locator("#font-reset").inner_text() == "130%"
    assert body_px() > base * 1.25
    page.reload(wait_until="domcontentloaded")
    assert body_px() > base * 1.25
    assert page.locator("#font-up").is_disabled()
    page.locator("#font-reset").click()
    assert body_px() == base
    assert page.locator("#font-reset").inner_text() == "100%"
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert page.locator("#font-up").is_hidden()                    # phones: A−/A+ move into the Aa sheet
    open_settings(page)
    page.locator('#settings-panel [data-fs="up"]').click()
    assert page.locator('#settings-panel [data-fs="reset"]').inner_text() == "110%"


def test_theme_toggle_works_when_storage_is_blocked(page):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.add_init_script("Object.defineProperty(window, 'localStorage', {get() {throw new DOMException('blocked', 'SecurityError')}})")
    page.reload(wait_until="domcontentloaded")
    theme = page.locator("html").get_attribute("data-theme")
    pick_theme(page, other_theme(page))
    assert page.locator("html").get_attribute("data-theme") != theme
    assert not errors


@pytest.fixture
def long_page(browser, tmp_path):
    output = _build(tmp_path, THREE_MD)
    filler = "".join(
        f"<p>第{i}段：这是用来撑开页面长度的正文，模拟一篇需要读很久的长文，读者会在中途离开再回来继续阅读。</p>"
        for i in range(60)
    )
    target = tmp_path / "long_整理文档.html"
    target.write_text(output.replace('<h2 id="一节" class="sec">一节</h2>', '<h2 id="一节" class="sec">一节</h2>\n' + filler), encoding="utf-8")
    context = browser.new_context(viewport={"width": 1200, "height": 700})
    context.route("**/cdn.jsdelivr.net/**", lambda route: route.abort())
    view = context.new_page()
    view.goto(target.as_uri(), wait_until="load")
    yield view
    context.close()


def test_reader_settings_apply_persist_and_reset(long_page):
    page = long_page
    first_p = ".content > p"
    style = lambda prop: page.evaluate(f"getComputedStyle(document.querySelector('{first_p}')).{prop}")
    width = lambda: page.evaluate(f"document.querySelector('{first_p}').getBoundingClientRect().width")
    lh0, w0 = float(style("lineHeight")[:-2]), width()

    pick(page, "font", "kai")
    assert "KaiTi" in style("fontFamily")
    pick(page, "lh", "loose")
    assert float(style("lineHeight")[:-2]) > lh0 * 1.1
    pick(page, "para", "indent")
    assert style("textIndent") != "0px"
    pick(page, "flip", "page")
    assert page.locator("#flip-hint").is_visible()
    assert page.locator('.seg[data-setting="font"] button[data-value="kai"]').get_attribute("aria-checked") == "true"

    page.reload(wait_until="load")
    attrs = page.evaluate("['font','lh','para','flip'].map(k => document.documentElement.getAttribute('data-' + k))")
    assert attrs == ["kai", "loose", "indent", "page"]

    open_settings(page)
    page.locator("#settings-reset").click()
    attrs = page.evaluate("['font','lh','para','flip'].map(k => document.documentElement.getAttribute('data-' + k))")
    assert attrs == [None] * 4
    assert abs(width() - w0) < 1


def test_page_mode_turns_whole_screens(long_page):
    page = long_page
    pick(page, "flip", "page")
    page.mouse.click(600, 400)                                  # closes the panel only — no page turn
    assert page.evaluate("window.scrollY") == 0
    vh = page.evaluate("window.innerHeight")
    page.keyboard.press("Space")
    y1 = page.evaluate("window.scrollY")
    assert vh * 0.6 < y1 <= vh + 2                              # +2: sub-pixel line boxes
    page.keyboard.press("Space")
    y2 = page.evaluate("window.scrollY")
    assert vh * 0.6 < y2 - y1 <= vh + 2
    assert page.evaluate("document.body.classList.contains('chrome-hidden')")
    page.keyboard.press("ArrowLeft")
    assert abs(page.evaluate("window.scrollY") - y1) < 60       # back to (about) the previous page
    page.mouse.click(1000, 400)                                 # a click must not turn the page
    assert abs(page.evaluate("window.scrollY") - y1) < 60
    page.mouse.move(600, 20)                                    # pointer at the top brings the menu back
    page.wait_for_timeout(100)
    assert not page.evaluate("document.body.classList.contains('chrome-hidden')")


def test_reading_status_immersive_chrome_and_resume(long_page):
    page = long_page
    assert page.locator("#resume-toast").is_hidden()          # nothing saved yet
    assert page.locator("#read-status").is_hidden()            # at the top
    pick_theme(page, "reader")                                  # a clicked topbar button keeps focus...
    page.mouse.click(600, 400)                                  # ...and an outside click closes the panel
    assert page.locator("#settings-panel").is_hidden()
    page.mouse.wheel(0, 1500)
    page.wait_for_timeout(300)
    page.mouse.wheel(0, 300)
    page.wait_for_timeout(600)
    status = page.locator("#read-status").inner_text()
    assert "本节剩余约" in status and "全文" in status and "%" in status
    assert page.evaluate("document.body.classList.contains('chrome-hidden')")
    page.mouse.wheel(0, -200)
    page.wait_for_timeout(300)
    assert not page.evaluate("document.body.classList.contains('chrome-hidden')")

    reading = page.evaluate("""() => {
      const p = Array.from(document.querySelectorAll('.content p')).find(p => p.getBoundingClientRect().bottom > 96);
      return p.textContent.slice(0, 6);
    }""")
    page.wait_for_timeout(600)                                    # position save is debounced
    page.evaluate("window.scrollTo(0, 0)")
    page.evaluate("history.scrollRestoration = 'manual'")
    page.reload(wait_until="load")
    page.evaluate("window.scrollTo(0, 0)")
    page.locator("#resume-toast").wait_for(state="visible", timeout=3000)
    assert "一节" in page.locator("#resume-where").inner_text()
    page.locator("#resume-go").click()
    assert page.locator("#resume-toast").is_hidden()
    now = page.evaluate("""() => {
      const p = Array.from(document.querySelectorAll('.content p')).find(p => p.getBoundingClientRect().bottom > 96);
      return p.textContent.slice(0, 6);
    }""")
    assert now == reading
