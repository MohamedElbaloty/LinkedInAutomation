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
        
        # Click Start Creating / new project
        btn = page.locator('button:has-text("مشروع جديد"), div:has-text("مشروع جديد"), a:has-text("مشروع جديد"), [aria-label*="مشروع جديد"], text="مشروع جديد", text="Start Creating"').first
        await btn.wait_for(state="visible", timeout=20000)
        await btn.click()
        
        await page.wait_for_url("**/project/**", timeout=25000)
        project_url = page.url
        print(f"CREATED_PROJECT_URL: {project_url}")
        
        # Wait for workspace to mount
        comp = page.locator('div[contenteditable=true], [contenteditable="true"]').first
        await comp.wait_for(state="visible", timeout=30000)
        
        # Ensure model is set to Nano Banana Pro
        pill = page.locator('text=Nano Banana Pro').first
        if not await pill.is_visible():
            settings_btn = page.locator('button:has-text("فيديو"), span:has-text("فيديو")').first
            if await settings_btn.is_visible():
                await settings_btn.click()
                await page.wait_for_timeout(1000)
            img_tab = page.locator('text=صورة').first
            if await img_tab.is_visible():
                await img_tab.click()
                await page.wait_for_timeout(1000)
                
        # Ensure 16:9
        r169 = page.locator('text=16:9').first
        if await r169.is_visible():
            await r169.click()
            await page.wait_for_timeout(500)
            
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(1000)
        
        # Try to rename the project if title element exists in top bar
        title_elem = page.locator('input[aria-label*="عنوان"], input[placeholder*="مشروع"], span:has-text("سبتمبر")').first
        if await title_elem.is_visible():
            try:
                await title_elem.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.type("LinkedIn AI News")
                await page.keyboard.press("Enter")
                print("Renamed project to 'LinkedIn AI News'")
            except Exception as e:
                print(f"Could not rename: {e}")
                
        await page.screenshot(path="flow_dedicated_project.png")
        print("Dedicated project created and configured!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
