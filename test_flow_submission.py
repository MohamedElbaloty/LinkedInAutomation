import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    profile = os.path.expandvars(r"%LOCALAPPDATA%\ffroliva\gflow-cli\profile_default")
    project_id = "84dc3114-9c59-4ac5-b676-0e5050c74a74"
    project_url = f"https://flow.google.com/project/{project_id}"
    
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
        
        comp = page.locator('div[contenteditable=true], [contenteditable="true"]').first
        if not await comp.is_visible():
            print("Composer not visible!")
            await page.screenshot(path="flow_comp_missing.png")
            await browser.close()
            return
            
        print("Composer is ready!")
        
        # Count existing images / videos
        initial_imgs = len(await page.locator('img[src*="/asb/"]').all())
        print(f"Initial images in project: {initial_imgs}")
        
        test_prompt = "3Blue1Brown Deep Manim mathematical animation, glowing cyan vector tensors, neural probability distribution, dark slate #0B0F19, 16:9 8k"
        await comp.click()
        await comp.fill(test_prompt)
        await page.wait_for_timeout(1000)
        
        # Take screenshot of filled prompt
        await page.screenshot(path="flow_prompt_typed.png")
        print("Screenshot of typed prompt saved: flow_prompt_typed.png")
        
        # Press Enter to submit
        print("Submitting to Google Flow...")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(6000)
        
        # Take screenshot right after submission
        await page.screenshot(path="flow_after_submit.png")
        print("Screenshot after submit saved: flow_after_submit.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
