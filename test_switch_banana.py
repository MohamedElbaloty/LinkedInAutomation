import asyncio
import os
import sys
from playwright.async_api import async_playwright

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

async def main():
    profile = os.path.expandvars(r"%LOCALAPPDATA%\ffroliva\gflow-cli\profile_default")
    project_url = "https://flow.google.com/project/84dc3114-9c59-4ac5-b676-0e5050c74a74"
    
    print("Connecting to Flow project...")
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=profile,
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.goto(project_url, wait_until="domcontentloaded", timeout=40000)
        
        comp = page.locator('div[contenteditable=true], [contenteditable="true"], .ProseMirror').first
        print("Waiting for composer to mount...")
        await comp.wait_for(state="visible", timeout=35000)
        print("Composer mounted successfully!")
        
        # Check current model / mode text in bottom controls
        buttons = await page.locator('.bottom-controls button').all()
        print(f"Found {len(buttons)} buttons in bottom-controls:")
        target_btn = None
        for i, b in enumerate(buttons):
            t = (await b.inner_text()).replace("\n", " ").strip()
            print(f"Btn {i}: '{t}'")
            if "video" in t.lower() or "فيديو" in t:
                target_btn = b
                
        if target_btn:
            print("Clicking Video mode pill to switch to Image mode...")
            await target_btn.click()
            await page.wait_for_timeout(1500)
            await page.screenshot(path="flow_mode_popup.png")
            print("Screenshot saved: flow_mode_popup.png")
            
            # Switch to Image tab
            img_tab = page.locator('button:has-text("Image"), button:has-text("صورة"), [role="tab"]:has-text("Image"), [role="tab"]:has-text("صورة")').first
            if await img_tab.is_visible():
                print("Clicking Image / صورة tab...")
                await img_tab.click()
                await page.wait_for_timeout(1000)
                await page.screenshot(path="flow_switched_to_image.png")
                
                # Verify 16:9
                r169 = page.locator('button:has-text("16:9"), [role="radio"]:has-text("16:9")').first
                if await r169.is_visible():
                    print("Selecting 16:9 widescreen...")
                    await r169.click()
                    await page.wait_for_timeout(500)
                    
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(1000)
                await page.screenshot(path="flow_ready_banana_pro.png")
                print("SUCCESS: Google Flow is now in Nano Banana Pro 🍌 Image Mode (16:9)!")
        else:
            print("Video mode button was not found, checking if already in Nano Banana Pro...")
            pill = page.locator('text=Nano Banana Pro').first
            if await pill.is_visible():
                print("Already in Nano Banana Pro mode!")
            await page.screenshot(path="flow_current_state.png")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
