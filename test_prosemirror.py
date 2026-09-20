import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    profile = os.path.expandvars(r"%LOCALAPPDATA%\ffroliva\gflow-cli\profile_default")
    project_url = "https://flow.google.com/project/84dc3114-9c59-4ac5-b676-0e5050c74a74"
    
    print(f"Connecting to Google Flow project: {project_url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=profile,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = await browser.new_page()
        await page.goto(project_url, wait_until="domcontentloaded", timeout=35000)
        await page.wait_for_timeout(4000)
        
        comp = page.locator('.ProseMirror, flow-rich-text-editor [contenteditable="true"]').first
        print("ProseMirror visible:", await comp.is_visible())
        
        if await comp.is_visible():
            await comp.click()
            await page.wait_for_timeout(500)
            
            prompt = "Deep Manim 3Blue1Brown mathematical visualization of calibrated probability vector space"
            await comp.fill(prompt)
            print("Filled prompt successfully!")
            await page.wait_for_timeout(1000)
            await page.screenshot(path="flow_typed_prosemirror.png")
            print("Saved flow_typed_prosemirror.png")
            
            # Check submit button
            # Usually Enter triggers generation or there is an enter button
            print("Pressing Enter...")
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(5000)
            await page.screenshot(path="flow_submitted_state.png")
            print("Saved flow_submitted_state.png")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
