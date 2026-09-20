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
        print("Opening project 6b2eb34d-44a8-4c91-9e7c-87d98305f63d...")
        await page.goto("https://flow.google.com/project/6b2eb34d-44a8-4c91-9e7c-87d98305f63d", wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)
        
        # Check composer
        comp = page.locator('div[contenteditable=true], [contenteditable="true"]').first
        print("Composer visible:", await comp.is_visible())
        
        # Check model pill
        pill = page.locator('text=Nano Banana Pro').first
        print("Nano Banana Pro pill visible:", await pill.is_visible())
        
        # Check current title in top bar
        title_elem = page.locator('span:has-text("سبتمبر"), [role=heading]').first
        if await title_elem.is_visible():
            print("Current title:", await title_elem.inner_text())
            
        await page.screenshot(path="flow_project_check.png")
        print("Screenshot saved to flow_project_check.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
