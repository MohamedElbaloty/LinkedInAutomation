import asyncio, os
from playwright.async_api import async_playwright

async def main():
    profile = os.path.expandvars(r"%LOCALAPPDATA%\ffroliva\gflow-cli\profile_default")
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=profile,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = await browser.new_page()
        await page.goto("https://flow.google.com", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        
        btn = page.locator('text=Create with Google Flow, text=Start Creating').first
        if await btn.is_visible():
            print("Clicking button...")
            await btn.click()
            await page.wait_for_timeout(5000)
            
        print("Current URL:", page.url)
        await page.screenshot(path="flow_after_create_btn.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
