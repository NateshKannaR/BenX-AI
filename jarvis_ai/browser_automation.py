"""
Browser Automation - Playwright wrapper for BenX
Install: pip install playwright && playwright install chromium
"""
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=60)
        return loop.run_until_complete(coro)
    except Exception as e:
        return f"❌ Browser error: {e}"


class BrowserAutomation:

    @staticmethod
    def _check() -> Optional[str]:
        try:
            import playwright  # noqa
            return None
        except ImportError:
            return ("❌ Playwright not installed.\n"
                    "Run: pip install playwright && playwright install chromium")

    @staticmethod
    def open_url(url: str, headless: bool = False) -> str:
        err = BrowserAutomation._check()
        if err:
            return err
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        async def _go():
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless)
                page = await browser.new_page()
                await page.goto(url, timeout=30000)
                title = await page.title()
                await browser.close()
                return f"✅ Opened: {title} ({url})"
        return _run(_go())

    @staticmethod
    def scrape(url: str, selector: str = "body") -> str:
        err = BrowserAutomation._check()
        if err:
            return err
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        async def _scrape():
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=10000)
                el = page.locator(selector).first
                text = await el.inner_text()
                await browser.close()
                return f"📄 Scraped from {url}:\n{text[:3000]}"
        return _run(_scrape())

    @staticmethod
    def click(url: str, selector: str) -> str:
        err = BrowserAutomation._check()
        if err:
            return err

        async def _click():
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                page = await browser.new_page()
                await page.goto(url, timeout=30000)
                await page.click(selector, timeout=10000)
                await page.wait_for_load_state("networkidle", timeout=10000)
                title = await page.title()
                await browser.close()
                return f"✅ Clicked '{selector}' → {title}"
        return _run(_click())

    @staticmethod
    def fill_form(url: str, fields: dict, submit_selector: str = "") -> str:
        """fields = {selector: value, ...}"""
        err = BrowserAutomation._check()
        if err:
            return err

        async def _fill():
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                page = await browser.new_page()
                await page.goto(url, timeout=30000)
                for sel, val in fields.items():
                    await page.fill(sel, str(val), timeout=8000)
                if submit_selector:
                    await page.click(submit_selector, timeout=8000)
                    await page.wait_for_load_state("networkidle", timeout=10000)
                title = await page.title()
                await browser.close()
                return f"✅ Form filled on {url} → {title}"
        return _run(_fill())

    @staticmethod
    def screenshot(url: str, output_path: str = "/tmp/benx_browser.png") -> str:
        err = BrowserAutomation._check()
        if err:
            return err
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        async def _shot():
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=10000)
                await page.screenshot(path=output_path, full_page=True)
                await browser.close()
                return f"✅ Screenshot saved: {output_path}"
        return _run(_shot())

    @staticmethod
    def search_and_scrape(query: str) -> str:
        """Search DuckDuckGo and return top result text"""
        import urllib.parse
        url = f"https://duckduckgo.com/?q={urllib.parse.quote(query)}&ia=web"
        return BrowserAutomation.scrape(url, ".results")
