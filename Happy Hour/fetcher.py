"""
fetcher.py — Playwright-rendered page fetch for JS-heavy restaurant sites.

`requests` only sees the empty shell of Squarespace/Wix/Toast/BentoBox sites
(El Rey, Tequilas, …). This renders the page in a headless Chromium so the real
links, text, and menus are present, and returns them in a JSON-friendly shape
the LLM pass can reason over.

Setup (one time):
    pip install playwright
    python -m playwright install chromium

Use a single browser_session across a batch and call render()/screenshot() per URL.
"""

from contextlib import contextmanager

DEFAULT_TIMEOUT = 25000     # ms for navigation
NETWORKIDLE_TIMEOUT = 6000  # ms extra wait for late-loading content
USER_AGENT = 'Mozilla/5.0 (compatible; MappyHourBot/1.0; +happy-hour discovery)'


def _sync_playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError as e:
        raise RuntimeError(
            'Playwright is not installed. Run:\n'
            '    pip install playwright\n'
            '    python -m playwright install chromium'
        ) from e


@contextmanager
def browser_session(headless=True):
    """Open one Chromium for a whole batch: `with browser_session() as ctx: ...`."""
    sync_playwright = _sync_playwright()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(user_agent=USER_AGENT, viewport={'width': 1280, 'height': 2000})
        ctx.set_default_timeout(DEFAULT_TIMEOUT)
        try:
            yield ctx
        finally:
            ctx.close()
            browser.close()


# JS run in the page to collect links/images as plain dicts.
_LINKS_JS = """() => Array.from(document.querySelectorAll('a[href]')).map(a => ({
    text: (a.innerText || a.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 100),
    href: a.href,
}))"""
_IMGS_JS = """() => Array.from(document.querySelectorAll('img[src]')).map(i => ({
    alt: (i.alt || '').slice(0, 100), src: i.src,
}))"""


def render(ctx, url, timeout=DEFAULT_TIMEOUT):
    """Render `url` and return {final_url, text, links:[{text,href}], imgs:[{alt,src}]}."""
    page = ctx.new_page()
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=timeout)
        try:
            page.wait_for_load_state('networkidle', timeout=NETWORKIDLE_TIMEOUT)
        except Exception:
            pass  # some sites never go fully idle — proceed with what rendered
        return {
            'final_url': page.url,
            'text': page.inner_text('body'),
            'links': page.evaluate(_LINKS_JS) or [],
            'imgs': page.evaluate(_IMGS_JS) or [],
        }
    finally:
        page.close()


def screenshot(ctx, url, timeout=DEFAULT_TIMEOUT):
    """Full-page PNG bytes — for image/PDF-style menus that need Claude vision."""
    page = ctx.new_page()
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=timeout)
        try:
            page.wait_for_load_state('networkidle', timeout=NETWORKIDLE_TIMEOUT)
        except Exception:
            pass
        return page.screenshot(full_page=True)
    finally:
        page.close()
