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
        print("1. Loading Flow home to establish session...")
        await page.goto("https://flow.google.com", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)
        
        print("2. Navigating to dedicated project 16b5c658-73af-44aa-80ba-46b6593ad68b...")
        await page.goto("https://flow.google.com/project/16b5c658-73af-44aa-80ba-46b6593ad68b", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        
        comp = page.locator('div[contenteditable=true], [contenteditable="true"]').first
        print("Composer visible:", await comp.is_visible())
        
        pill = page.locator('text=Nano Banana Pro').first
        print("Nano Banana Pro pill visible:", await pill.is_visible())
        
        await page.screenshot(path="flow_dedicated_check.png")
        print("Saved flow_dedicated_check.png!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
