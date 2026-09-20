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
        await page.goto("https://flow.google.com/?hl=ar", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        
        card = page.locator('text=Mohamed Elbaloty').first
        if await card.is_visible():
            print("Found Mohamed Elbaloty card!")
            # Find parent or anchor
            await card.click()
            await page.wait_for_timeout(4000)
            print("Project URL:", page.url)
            await page.screenshot(path="flow_elbaloty_project.png")
            print("Screenshot saved!")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
