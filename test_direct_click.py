import asyncio, os
from playwright.async_api import async_playwright

async def main():
    profile = os.path.expandvars(r"%LOCALAPPDATA%\ffroliva\gflow-cli\profile_default")
    project_url = "https://flow.google.com/project/84dc3114-9c59-4ac5-b676-0e5050c74a74"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=profile,
            headless=True,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = await browser.new_page()
        await page.goto(project_url, wait_until="domcontentloaded", timeout=35000)
        await page.wait_for_timeout(4000)
        
        rect = await page.evaluate('''() => {
            const el = document.querySelector('.ProseMirror') || document.querySelector('[contenteditable="true"]');
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return {x: r.x, y: r.y, w: r.width, h: r.height};
        }''')
        print("Composer rect:", rect)
        
        if rect:
            click_x = rect['x'] + 30
            click_y = rect['y'] + rect['h'] / 2
            print(f"Clicking at ({click_x}, {click_y})...")
            await page.mouse.click(click_x, click_y)
            await page.wait_for_timeout(500)
            
            prompt = "Deep Manim 3Blue1Brown mathematical visualization of calibrated probability vector space"
            await page.keyboard.type(prompt, delay=15)
            await page.wait_for_timeout(1000)
            
            await page.screenshot(path="flow_typed_direct.png")
            print("Screenshot saved: flow_typed_direct.png")
            
            print("Pressing Enter...")
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(5000)
            
            await page.screenshot(path="flow_after_enter.png")
            print("Screenshot saved: flow_after_enter.png")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
