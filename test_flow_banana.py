import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def main():
    profile = os.path.expandvars(r'%LOCALAPPDATA%\ffroliva\gflow-cli\profile_default')
    print(f"Using profile: {profile}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=profile,
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        page = await browser.new_page()
        print("Navigating to flow.google.com...")
        await page.goto("https://flow.google.com", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        
        # Click Start Creating or new project
        btn = page.locator('text=مشروع جديد').first
        if not await btn.is_visible():
            btn = page.locator('text=Start Creating').first
        print("Clicking project button...")
        await btn.click()
        
        # Wait for project URL
        await page.wait_for_url("**/project/**", timeout=20000)
        print(f"Editor URL: {page.url}")
        await page.wait_for_timeout(3000)
        
        # Ensure image mode is selected
        pill = page.locator('text=Nano Banana Pro').first
        if not await pill.is_visible():
            print("Configuring model to Nano Banana Pro...")
            p = page.locator('button:has-text("فيديو"), span:has-text("فيديو")').first
            if await p.is_visible():
                await p.click()
                await page.wait_for_timeout(1000)
            img_btn = page.locator('text=صورة').first
            if await img_btn.is_visible():
                await img_btn.click()
                await page.wait_for_timeout(1000)
        
        # Click 16:9
        r169 = page.locator('text=16:9').first
        if await r169.is_visible():
            await r169.click()
            await page.wait_for_timeout(500)
            
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(1000)
        
        # Locate composer input
        print("Locating composer...")
        comp = page.locator('[contenteditable=true]').first
        if not await comp.is_visible():
            comp = page.locator('textarea').first
            
        await comp.click()
        prompt = "Editorial tech photograph of Meta AI agent Muse, ultra detailed, cinematic studio lighting, 8k resolution"
        await comp.fill(prompt)
        print(f"Prompt filled: {prompt}")
        await page.wait_for_timeout(500)
        
        # Submit
        print("Submitting generation...")
        await page.keyboard.press("Enter")
        
        # Wait for generation
        for sec in range(1, 35):
            await page.wait_for_timeout(1000)
            if sec % 5 == 0:
                print(f"Elapsed: {sec}s...")
        
        await page.screenshot(path="flow_generation_result.png")
        print("Screenshot saved to flow_generation_result.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
