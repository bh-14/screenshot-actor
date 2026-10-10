# Website Screenshot

Take clean screenshots of any list of web pages: full page or viewport, PNG or JPEG, on desktop, mobile or tablet.
Cookie banners are hidden, lazy-loaded images are loaded before the capture, and **you only pay for screenshots that succeed**.

## What does Website Screenshot do?

You give it a list of URLs. For each one it opens the page in a real Chromium browser, waits for it to load, and saves an image in the run's key-value store. The dataset gets one row per URL with a public link to the image, the page title, the HTTP status and, when something goes wrong, the reason.

## Why use it?

- **Pay only for results.** A page that times out or doesn't exist shows up in the dataset with its error, and costs you nothing.
- **No cookie walls in your images.** Consent banners from OneTrust, Cookiebot, Didomi, Usercentrics, Quantcast, TrustArc and other common frameworks are hidden with CSS. Nothing is clicked, so no consent is given on your behalf.
- **Complete full-page captures.** Before a full-page screenshot the page is scrolled from top to bottom, so images that load on scroll actually appear.
- **Desktop, mobile or tablet.** Mobile emulates an iPhone 13 and tablet an iPad, with the right user agent and pixel ratio, so you see the responsive layout real visitors see.
- **Hide anything else.** Add your own CSS selectors to remove chat widgets, popups or sticky headers.
- **Doesn't give up on heavy pages.** Ad-heavy sites that never finish loading are captured as they are, instead of failing on a timeout.
- **Fast batches.** Several pages are captured in parallel in one run.

Typical uses: visual monitoring of your own or competitors' pages, archiving pages as evidence, thumbnails for link previews and directories, QA of responsive layouts, and reports for clients.

## How to use it

1. Add the URLs in **URLs**, one per row, or use **Bulk edit** to paste a whole list.
2. Choose **Full page** or viewport only, the **Device** and the **Image format**.
3. Click **Start**. When the run finishes, open the **Output** tab: each row has a clickable screenshot.

You can also run it via the Apify API, on a schedule, or connect it to Make, Zapier, n8n and other integrations.

## Input example

```json
{
    "urls": [
        { "url": "https://apify.com" },
        { "url": "https://www.wikipedia.org" }
    ],
    "fullPage": true,
    "device": "desktop",
    "format": "png",
    "hideCookieBanners": true
}
```

The main options:

| Option | What it does | Default |
|---|---|---|
| `fullPage` | Whole scrollable page instead of the visible viewport | `true` |
| `device` | `desktop`, `mobile` (iPhone 13) or `tablet` (iPad) | `desktop` |
| `viewportWidth` / `viewportHeight` | Window size for desktop | `1280` × `800` |
| `format` / `jpegQuality` | `png` or `jpeg`, and JPEG quality from 1 to 100 | `png` / `80` |
| `hideCookieBanners` | Hide common consent banners | `true` |
| `hideSelectors` | Your own CSS selectors to hide | none |
| `scrollToBottom` | Scroll first so lazy images load | `true` |
| `waitUntil` | `load`, `domcontentloaded` or `networkidle` | `load` |
| `waitForSelector` | Wait for an element before the capture | none |
| `delayMs` | Extra wait before the capture, for animations | `0` |
| `timeoutSecs` | Maximum load time per page | `60` |
| `maxConcurrency` | Pages captured in parallel (1 to 10) | `2` |

## Output example

```json
{
    "url": "https://example.com",
    "finalUrl": "https://example.com/",
    "statusCode": 200,
    "pageTitle": "Example Domain",
    "screenshotUrl": "https://api.apify.com/v2/key-value-stores/<storeId>/records/screenshot-00001-327c3fda87.png",
    "screenshotKey": "screenshot-00001-327c3fda87.png",
    "format": "png",
    "fullPage": true,
    "device": "desktop",
    "sizeBytes": 59146,
    "takenAt": "2026-10-10T03:46:01.913309+00:00",
    "error": null
}
```

A failed URL looks like this, and is not charged:

```json
{
    "url": "https://this-domain-does-not-exist.com",
    "screenshotUrl": null,
    "error": "Page.goto: net::ERR_NAME_NOT_RESOLVED at https://this-domain-does-not-exist.com/"
}
```

You can download the dataset as JSON, CSV, Excel or HTML. The images themselves are in the run's key-value store.

## How much does it cost?

You pay a fixed price per **successful** screenshot; the exact price is on the **Pricing** tab. Failed pages are free. The run stops before going over the maximum cost per run you set, so you never pay more than you allowed.

## Tips

- Very long pages (infinite feeds, huge catalogs) produce very tall images. Turn off **Full page** if you only need what a visitor sees first.
- If a page still shows a popup, add its CSS selector to **Extra CSS selectors to hide**.
- For pages that load content after the initial load, use **Wait until: Network idle** or **Wait for selector**.

## Limitations

- Pages behind a login, a paywall or a CAPTCHA are captured as they appear to an anonymous visitor.
- Some sites block automated browsers. These pages are reported with their error and are not charged.
- Cookie banners from less common frameworks may still appear; hide them with your own selectors.

## Is it legal to take screenshots of websites?

Capturing publicly available pages is generally fine, but you are responsible for how you use the images, including copyright and the terms of the sites you capture. Don't use this Actor to collect personal data you have no legal basis for.

## Feedback

Found a bug or need a feature? Open an issue in the **Issues** tab and it will be looked at.
