import asyncio
import os
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
        await page.goto("https://flow.google.com/?hl=ar", wait_until="networkidle", timeout=35000)
        await page.wait_for_timeout(4000)
        
        # Take screenshot of home
        await page.screenshot(path="flow_home_projects_inspect.png")
        
        # Find all project links or cards
        links = await page.locator('a[href*="/project/"]').all()
        print(f"Total project links: {len(links)}")
        for i, l in enumerate(links):
            href = await l.get_attribute("href")
            text = (await l.inner_text()).replace("\n", " ").strip()
            print(f"Project [{i}]: href={href} | title={text}")
            
        # Check if there is a 'مشروع جديد' or 'start creating' button
        new_btns = await page.locator('button:has-text("مشروع"), a:has-text("مشروع"), button:has-text("إنشاء")').all()
        for j, b in enumerate(new_btns):
            t = (await b.inner_text()).replace("\n", " ").strip()
            print(f"Action button [{j}]: {t}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
