import asyncio, os
from playwright.async_api import async_playwright

async def main():
    profile = os.path.expandvars(r"%LOCALAPPDATA%\ffroliva\gflow-cli\profile_default")
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=profile,
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.goto("https://flow.google.com/?hl=ar", wait_until="domcontentloaded", timeout=35000)
        await page.wait_for_timeout(3000)
        
        # Click the first existing project link on the home page
        project_link = page.locator('a[href*="/project/"]').first
        print("Project link visible:", await project_link.is_visible())
        href = await project_link.get_attribute("href")
        print(f"Clicking existing project: {href}")
        await project_link.click()
        
        await page.wait_for_url("**/project/**", timeout=25000)
        print("Current URL:", page.url)
        
        comp = page.locator('div[contenteditable=true], [contenteditable="true"]').first
        await comp.wait_for(state="visible", timeout=20000)
        print("SUCCESS! Composer is visible and ready in the existing project!")
        await page.screenshot(path="flow_existing_project_opened.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
