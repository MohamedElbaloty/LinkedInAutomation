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
        
        # Scroll down slightly to see project cards
        await page.mouse.wheel(0, 300)
        await page.wait_for_timeout(1000)
        await page.screenshot(path="flow_home_cards.png")
        print("Home screenshot saved!")
        
        # Find all clickable project elements
        elements = await page.locator('[role=gridcell], mat-card, .project-card, div:has(> a)').all()
        print(f"Total candidate project elements: {len(elements)}")
        for i, el in enumerate(elements[:10]):
            t = (await el.inner_text()).replace('\n', ' ').strip()
            if t:
                print(f"Element {i}: {t[:60]}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
