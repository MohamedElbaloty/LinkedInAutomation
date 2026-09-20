import asyncio, os
from playwright.async_api import async_playwright

async def main():
    profile = os.path.expandvars(r"%LOCALAPPDATA%\ffroliva\gflow-cli\profile_default")
    project_url = "https://flow.google.com/project/84dc3114-9c59-4ac5-b676-0e5050c74a74"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=profile,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = await browser.new_page()
        await page.goto(project_url, wait_until="domcontentloaded", timeout=35000)
        await page.wait_for_timeout(4000)
        
        # Search for elements
        els = await page.locator('*:has-text("ما الذي أردت إنشاءه؟")').all()
        print(f"Elements matching Arabic placeholder text: {len(els)}")
        for i, el in enumerate(els[-5:]):
            tag = await el.evaluate("el => el.tagName")
            clz = await el.get_attribute("class")
            print(f"Match {i}: tag={tag} class={clz}")
            
        # Also check all contenteditable or textarea or input
        inputs = await page.locator('[contenteditable], textarea, input').all()
        print(f"Input elements total: {len(inputs)}")
        for j, inp in enumerate(inputs):
            tag = await inp.evaluate("el => el.tagName")
            ce = await inp.get_attribute("contenteditable")
            vis = await inp.is_visible()
            ph = await inp.get_attribute("placeholder")
            print(f"Input {j}: tag={tag} contenteditable={ce} visible={vis} placeholder={ph}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
