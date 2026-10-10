"""Website Screenshot actor.

Takes screenshots of a list of URLs with a real Chromium browser and stores them in the default key-value store.
Each URL produces one dataset item with a public link to the image. Users pay only for successful screenshots
(the `screenshot` pay-per-event event); failed URLs are reported in the dataset for free.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any

from apify import Actor, Event
from playwright.async_api import Browser, Playwright, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

CHARGED_EVENT = 'screenshot'

# Consent banners of the most common cookie frameworks. Hidden with CSS, never clicked, so no consent is given.
COOKIE_BANNER_SELECTORS = [
    '#onetrust-consent-sdk',
    '#onetrust-banner-sdk',
    '#CybotCookiebotDialog',
    '#CybotCookiebotDialogBodyUnderlay',
    '#didomi-host',
    '.qc-cmp2-container',
    '#truste-consent-track',
    '.truste_box_overlay',
    '#usercentrics-root',
    '.cky-consent-container',
    '.osano-cm-window',
    '#cmplz-cookiebanner-container',
    '#iubenda-cs-banner',
    '.cc-window',
    '.cc-banner',
    '.klaro',
    '#termly-code-snippet-support',
    '#BorlabsCookieBox',
    'div[id^="sp_message_container"]',
]

# Scrolls down in steps so lazy-loaded images render before a full-page screenshot, then returns to the top.
SCROLL_SCRIPT = """
async () => {
    const step = Math.max(window.innerHeight, 400);
    for (let i = 0; i < 50; i++) {
        const before = window.scrollY;
        window.scrollBy(0, step);
        await new Promise((resolve) => setTimeout(resolve, 150));
        if (window.scrollY === before) break;
    }
    window.scrollTo(0, 0);
}
"""


def _device_options(playwright: Playwright, device: str, width: int, height: int) -> dict[str, Any]:
    """Return browser context options for the chosen device."""
    if device == 'mobile':
        return dict(playwright.devices['iPhone 13'])
    if device == 'tablet':
        return dict(playwright.devices['iPad (gen 7)'])
    return {'viewport': {'width': width, 'height': height}}


def _record_key(index: int, url: str, image_format: str) -> str:
    """Build a key-value store key that is unique per URL and valid for the Apify storage."""
    digest = hashlib.sha1(url.encode()).hexdigest()[:10]
    return f'screenshot-{index:05d}-{digest}.{"jpg" if image_format == "jpeg" else "png"}'


async def _screenshot(browser: Browser, playwright: Playwright, url: str, index: int, opts: dict[str, Any]) -> dict:
    """Take one screenshot and return the dataset item for it. Raises on failure."""
    context = await browser.new_context(
        **_device_options(playwright, opts['device'], opts['viewport_width'], opts['viewport_height'])
    )
    try:
        page = await context.new_page()
        # Navigate until the DOM is ready, then give the slower load state a bounded wait. Ad-heavy pages often
        # never fire `load`; they are still worth capturing instead of failing the whole URL.
        response = await page.goto(url, wait_until='domcontentloaded', timeout=opts['timeout_secs'] * 1000)
        if opts['wait_until'] != 'domcontentloaded':
            try:
                await page.wait_for_load_state(opts['wait_until'], timeout=min(opts['timeout_secs'], 30) * 1000)
            except PlaywrightTimeoutError:
                Actor.log.info(f'{url} did not reach "{opts["wait_until"]}" in time, capturing it as it is.')

        if opts['wait_for_selector']:
            await page.wait_for_selector(opts['wait_for_selector'], timeout=opts['timeout_secs'] * 1000)

        hide = (COOKIE_BANNER_SELECTORS if opts['hide_cookie_banners'] else []) + opts['hide_selectors']
        if hide:
            await page.add_style_tag(content=f'{", ".join(hide)} {{ display: none !important; }}')

        if opts['full_page'] and opts['scroll_to_bottom']:
            await page.evaluate(SCROLL_SCRIPT)

        if opts['delay_ms']:
            await page.wait_for_timeout(opts['delay_ms'])

        shot_args: dict[str, Any] = {'full_page': opts['full_page'], 'type': opts['format']}
        if opts['format'] == 'jpeg':
            shot_args['quality'] = opts['jpeg_quality']
        image = await page.screenshot(**shot_args)

        key = _record_key(index, url, opts['format'])
        store = await Actor.open_key_value_store()
        await store.set_value(key, image, content_type=f'image/{opts["format"]}')

        return {
            'url': url,
            'finalUrl': page.url,
            'statusCode': response.status if response else None,
            'pageTitle': await page.title(),
            'screenshotUrl': await store.get_public_url(key),
            'screenshotKey': key,
            'format': opts['format'],
            'fullPage': opts['full_page'],
            'device': opts['device'],
            'sizeBytes': len(image),
            'takenAt': datetime.now(timezone.utc).isoformat(),
            'error': None,
        }
    finally:
        await context.close()


async def main() -> None:
    """Read the input, take the screenshots concurrently and push one dataset item per URL."""
    async with Actor:

        async def on_aborting(_: Any) -> None:
            await Actor.exit()

        Actor.on(Event.ABORTING, on_aborting)

        actor_input = await Actor.get_input() or {}
        opts = {
            'full_page': bool(actor_input.get('fullPage', True)),
            'device': actor_input.get('device', 'desktop'),
            'viewport_width': int(actor_input.get('viewportWidth', 1280)),
            'viewport_height': int(actor_input.get('viewportHeight', 800)),
            'format': actor_input.get('format', 'png'),
            'jpeg_quality': int(actor_input.get('jpegQuality', 80)),
            'wait_until': actor_input.get('waitUntil', 'load'),
            'wait_for_selector': actor_input.get('waitForSelector') or None,
            'delay_ms': int(actor_input.get('delayMs', 0)),
            'hide_cookie_banners': bool(actor_input.get('hideCookieBanners', True)),
            'hide_selectors': [s for s in actor_input.get('hideSelectors', []) if isinstance(s, str) and s.strip()],
            'scroll_to_bottom': bool(actor_input.get('scrollToBottom', True)),
            'timeout_secs': int(actor_input.get('timeoutSecs', 60)),
        }
        max_concurrency = max(1, min(int(actor_input.get('maxConcurrency', 2)), 10))

        # Accept both the requestListSources format ({"url": ...}) and plain strings; keep only http(s) URLs.
        urls: list[str] = []
        for source in actor_input.get('urls', []):
            url = (source.get('url') if isinstance(source, dict) else source) or ''
            url = url.strip()
            if url.startswith(('http://', 'https://')):
                urls.append(url)
            else:
                Actor.log.warning(f'Skipping invalid URL: {url!r}')

        if not urls:
            Actor.log.info('No valid URLs in the input, exiting.')
            return

        # Never take more screenshots than the user's maximum cost per run allows.
        allowed = Actor.get_charging_manager().calculate_max_event_charge_count_within_limit(CHARGED_EVENT)
        if allowed is not None and allowed < len(urls):
            Actor.log.warning(f'The run cost limit allows only {allowed} of {len(urls)} screenshots.')
            urls = urls[:allowed]
            if not urls:
                return

        Actor.log.info(f'Taking {len(urls)} screenshot(s) with concurrency {max_concurrency}.')
        semaphore = asyncio.Semaphore(max_concurrency)
        done = 0

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=Actor.configuration.headless, args=['--disable-gpu'])

            async def handle(index: int, url: str) -> None:
                nonlocal done
                async with semaphore:
                    try:
                        item = await _screenshot(browser, playwright, url, index, opts)
                        await Actor.push_data(item, charged_event_name=CHARGED_EVENT)
                        Actor.log.info(f'OK {url}')
                    except Exception as exc:  # noqa: BLE001 - every failure becomes a free dataset item
                        Actor.log.warning(f'Failed {url}: {exc}')
                        await Actor.push_data({'url': url, 'screenshotUrl': None, 'error': str(exc)[:500]})
                    done += 1

            await asyncio.gather(*(handle(i, url) for i, url in enumerate(urls)))
            await browser.close()

        Actor.log.info(f'Finished {done} URL(s).')
