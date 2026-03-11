"""
Playwright Test Script — Learn the Basics
==========================================
Run: python playwright_test.py [url]
Default URL: https://example.com (swap for http://localhost:3000 or whatever)

No API keys needed. This is pure browser automation.

What this does:
  1. Opens a real Chromium browser (headless by default, pass --headed to see it)
  2. Navigates to a URL
  3. Takes a full-page screenshot
  4. Extracts page info (title, links, buttons, inputs)
  5. Demonstrates clicking and typing
  6. Shows how to screenshot specific elements

Install:
  pip install playwright
  playwright install chromium
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright


# ---------------------------------------------------------------------------
# 1. BASIC NAVIGATION & SCREENSHOTS
# ---------------------------------------------------------------------------
async def demo_basics(page, url: str, output_dir: Path):
    """Navigate to a URL, screenshot, extract info."""
    print(f"\n{'='*60}")
    print(f"  DEMO 1: Basics — Navigate & Screenshot")
    print(f"{'='*60}")

    # Go to the page
    print(f"\n→ Navigating to {url} ...")
    await page.goto(url, wait_until="networkidle")
    print(f"  Page title: {await page.title()}")
    print(f"  Current URL: {page.url}")

    # Full page screenshot
    screenshot_path = output_dir / "01_full_page.png"
    # Note: timeout= is optional, increase if your page loads slowly
    await page.screenshot(path=str(screenshot_path), full_page=True, timeout=10000)
    print(f"  📸 Full page screenshot saved: {screenshot_path}")

    # Viewport-only screenshot (what you'd actually see in a browser window)
    screenshot_path2 = output_dir / "02_viewport.png"
    await page.screenshot(path=str(screenshot_path2), full_page=False, timeout=10000)
    print(f"  📸 Viewport screenshot saved: {screenshot_path2}")


    await page.click("text=Create account")
    await page.fill('input[placeholder="username"]', 'admin')
    await page.fill('input[placeholder="password"]', 'admin123')
    await page.click("text=Sign up")

    await page.wait_for_selector("input[placeholder='What universe are we exploring today?']")
    screenshot_path3 = output_dir / "03_dashboard.png"
    await page.screenshot(path=str(screenshot_path3), full_page=True, timeout=10000)
    print(f"  📸 Dashboard screenshot saved: {screenshot_path3}")


# ---------------------------------------------------------------------------
# 2. EXTRACTING PAGE INFO
# ---------------------------------------------------------------------------
async def demo_extraction(page, output_dir: Path):
    """Extract structured info from the page."""
    print(f"\n{'='*60}")
    print(f"  DEMO 2: Extract Page Info")
    print(f"{'='*60}")

    # Get all visible text
    body_text = await page.inner_text("body")
    print(f"\n→ Page text (first 300 chars):\n  {body_text[:300]}...")

    # Find all links
    links = await page.eval_on_selector_all(
        "a[href]",
        "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))"
    )
    print(f"\n→ Found {len(links)} links:")
    for link in links[:10]:  # show first 10
        print(f"  - [{link['text'][:40]}] → {link['href'][:80]}")

    # Find all buttons
    buttons = await page.eval_on_selector_all(
        "button, input[type='submit'], [role='button']",
        "els => els.map(e => ({text: e.innerText.trim() || e.value || '', tag: e.tagName, id: e.id, classes: e.className}))"
    )
    print(f"\n→ Found {len(buttons)} buttons:")
    for btn in buttons[:10]:
        print(f"  - <{btn['tag'].lower()}> \"{btn['text'][:40]}\" id={btn['id'] or '(none)'}")

    # Find all form inputs
    inputs = await page.eval_on_selector_all(
        "input, textarea, select",
        "els => els.map(e => ({tag: e.tagName, type: e.type || '', name: e.name, id: e.id, placeholder: e.placeholder || ''}))"
    )
    print(f"\n→ Found {len(inputs)} form inputs:")
    for inp in inputs[:10]:
        print(f"  - <{inp['tag'].lower()} type=\"{inp['type']}\"> name={inp['name'] or '(none)'} placeholder=\"{inp['placeholder']}\"")

    # Save extracted info
    info = {"links": links, "buttons": buttons, "inputs": inputs}
    info_path = output_dir / "page_info.json"
    with open(info_path, "w") as f:
        json.dump(info, f, indent=2)
    print(f"\n  💾 Full page info saved: {info_path}")


# ---------------------------------------------------------------------------
# 3. INTERACTIONS — Click, Type, Scroll
# ---------------------------------------------------------------------------
async def demo_interactions(page, output_dir: Path):
    """Show how to interact with page elements."""
    print(f"\n{'='*60}")
    print(f"  DEMO 3: Interactions — Click, Type, Scroll")
    print(f"{'='*60}")

    # --- Clicking ---
    # By CSS selector
    # await page.click("#my-button")
    # By text content
    # await page.click("text=Submit")
    # By role
    # await page.get_by_role("button", name="Sign in").click()

    # --- Typing ---
    # await page.fill("#email-input", "test@example.com")
    # await page.fill("input[name='password']", "secret123")

    # --- Scrolling ---
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(0.5)
    screenshot_path = output_dir / "03_after_scroll.png"
    await page.screenshot(path=str(screenshot_path))
    print(f"  📸 After scroll screenshot: {screenshot_path}")

    # Scroll back up
    await page.evaluate("window.scrollTo(0, 0)")

    # --- Hover ---
    # await page.hover("#menu-item")

    # --- Keyboard ---
    # await page.keyboard.press("Enter")
    # await page.keyboard.press("Tab")
    # await page.keyboard.type("Hello world", delay=50)  # simulates typing speed

    print("""
  ℹ️  The click/type/hover commands above are commented out since they
     depend on your specific page. Uncomment and modify them for your app!

  Common patterns for YOUR localhost app:
    await page.click("text=Login")           # click by visible text
    await page.fill("#username", "admin")     # fill input by ID
    await page.click("button.submit-btn")     # click by CSS class
    await page.wait_for_selector(".dashboard") # wait for element to appear
    await page.screenshot(path="result.png")  # capture the result
""")


# ---------------------------------------------------------------------------
# 4. ELEMENT-SPECIFIC SCREENSHOTS
# ---------------------------------------------------------------------------
async def demo_element_screenshots(page, output_dir: Path):
    """Screenshot specific elements instead of the whole page."""
    print(f"\n{'='*60}")
    print(f"  DEMO 4: Element-Specific Screenshots")
    print(f"{'='*60}")

    # Try to screenshot the first heading
    heading = page.locator("h1").first
    if await heading.count() > 0:
        path = output_dir / "04_heading_element.png"
        await heading.screenshot(path=str(path))
        print(f"  📸 <h1> element screenshot: {path}")
    else:
        print("  No <h1> found on page, skipping element screenshot")

    # Try to screenshot a nav or header area
    for selector in ["nav", "header", "[role='navigation']"]:
        el = page.locator(selector).first
        if await el.count() > 0:
            clean = selector.replace("[", "").replace("]", "").replace("=", "_").replace("'", "")
            path = output_dir / f"04_{clean}_element.png"
            await el.screenshot(path=str(path))
            print(f"  📸 <{selector}> element screenshot: {path}")
            break


# ---------------------------------------------------------------------------
# 5. MULTI-STEP FLOW (simulating a user journey)
# ---------------------------------------------------------------------------
async def demo_user_flow(page, output_dir: Path):
    """Show how you'd script a multi-step user flow."""
    print(f"\n{'='*60}")
    print(f"  DEMO 5: Multi-Step User Flow (template)")
    print(f"{'='*60}")

    print("""
  Here's what a real test flow for YOUR app might look like:

  ┌─────────────────────────────────────────────────────────┐
  │  async def test_signup_flow(page):                      │
  │      await page.goto("http://localhost:3000")           │
  │      await page.screenshot(path="step1_landing.png")    │
  │                                                         │
  │      await page.click("text=Sign Up")                   │
  │      await page.wait_for_selector("#signup-form")       │
  │      await page.screenshot(path="step2_signup.png")     │
  │                                                         │
  │      await page.fill("#email", "test@test.com")         │
  │      await page.fill("#password", "password123")        │
  │      await page.click("button[type='submit']")          │
  │                                                         │
  │      await page.wait_for_url("**/dashboard")            │
  │      await page.screenshot(path="step3_dashboard.png")  │
  │                                                         │
  │      # Now you have 3 screenshots showing the full flow │
  │      # Send these to an LLM for visual review!          │
  └─────────────────────────────────────────────────────────┘

  Each screenshot captures the state at that step.
  The LLM can then review them all and spot issues.
""")


# ---------------------------------------------------------------------------
# 6. DIFFERENT VIEWPORT SIZES (mobile, tablet, desktop)
# ---------------------------------------------------------------------------
async def demo_viewports(browser, url: str, output_dir: Path):
    """Test the same page at different screen sizes."""
    print(f"\n{'='*60}")
    print(f"  DEMO 6: Different Viewport Sizes")
    print(f"{'='*60}")

    viewports = {
        "mobile":  {"width": 375,  "height": 812},   # iPhone X
        "tablet":  {"width": 768,  "height": 1024},   # iPad
        "desktop": {"width": 1440, "height": 900},     # Standard desktop
    }

    for name, size in viewports.items():
        context = await browser.new_context(viewport=size)
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle")

        path = output_dir / f"05_viewport_{name}_{size['width']}x{size['height']}.png"
        await page.screenshot(path=str(path), full_page=True)
        print(f"  📸 {name} ({size['width']}x{size['height']}): {path}")

        await context.close()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
async def main():
    parser = argparse.ArgumentParser(description="Playwright Test Script")
    parser.add_argument("url", nargs="?", default="https://example.com",
                        help="URL to test (default: https://example.com)")
    parser.add_argument("--headed", action="store_true",
                        help="Run with visible browser window")
    parser.add_argument("--output", "-o", default="./pw_screenshots",
                        help="Output directory for screenshots")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"""
╔══════════════════════════════════════════════════════════╗
║         🎭 Playwright Test Script                        ║
║                                                          ║
║  URL:     {args.url:<46} ║
║  Headed:  {str(args.headed):<46} ║
║  Output:  {str(output_dir):<46} ║
╚══════════════════════════════════════════════════════════╝
""")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not args.headed)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()

        # Disable waiting for web fonts (prevents timeout in some environments)
        await page.add_init_script("document.fonts.ready = Promise.resolve()")

        # Run demos
        await demo_basics(page, args.url, output_dir)
        await demo_extraction(page, output_dir)
        await demo_interactions(page, output_dir)
        await demo_element_screenshots(page, output_dir)
        await demo_user_flow(page, output_dir)
        await demo_viewports(browser, args.url, output_dir)

        await context.close()
        await browser.close()

    print(f"\n{'='*60}")
    print(f"  ✅ All demos complete!")
    print(f"  📁 Screenshots saved in: {output_dir}/")
    print(f"{'='*60}")
    print(f"\n  Next steps:")
    print(f"  1. Look at the screenshots in {output_dir}/")
    print(f"  2. Try: python playwright_test.py http://localhost:3000")
    print(f"  3. Try: python playwright_test.py http://localhost:3000 --headed")
    print(f"     (--headed opens a visible browser so you can watch it work)")
    print(f"  4. Modify the demo_interactions() function for your app\n")


if __name__ == "__main__":
    asyncio.run(main())
