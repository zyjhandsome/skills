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
    page.locator("#theme-toggle").click()
    assert page.locator("html").get_attribute("data-theme") != theme
    assert page.locator(".mermaid-fallback").inner_text() == text
    page.locator("#theme-toggle").click()
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


def test_theme_toggle_works_when_storage_is_blocked(page):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.add_init_script("Object.defineProperty(window, 'localStorage', {get() {throw new DOMException('blocked', 'SecurityError')}})")
    page.reload(wait_until="domcontentloaded")
    theme = page.locator("html").get_attribute("data-theme")
    page.locator("#theme-toggle").click()
    assert page.locator("html").get_attribute("data-theme") != theme
    assert not errors
