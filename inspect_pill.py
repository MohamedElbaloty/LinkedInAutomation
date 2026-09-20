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
        await page.goto("https://flow.google.com/project/84dc3114-9c59-4ac5-b676-0e5050c74a74", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        
        # Click on settings pill
        pill = page.locator('button:has-text("فيديو"), span:has-text("فيديو"), [aria-label*="إعدادات"]').first
        if await pill.is_visible():
            await pill.click()
            await page.wait_for_timeout(1500)
            await page.screenshot(path="flow_settings_pill_open.png")
            print("Pill clicked, screenshot saved.")
            
            # Print available tabs / buttons inside popup
            buttons = await page.locator('[role=tab], [role=radio], button').all()
            for b in buttons[:20]:
                t = (await b.inner_text()).replace('\n', ' ').strip()
                if t:
                    print("Popup item:", t)
                    
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
