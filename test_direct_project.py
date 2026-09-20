import asyncio, os
from pathlib import Path
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
        print("Navigating directly to Flow project...")
        await page.goto("https://flow.google.com/project/6b2eb34d-44a8-4c91-9e7c-87d98305f63d", wait_until="domcontentloaded", timeout=30000)
        
        # Wait for composer
        comp = page.locator('div[contenteditable=true], [contenteditable="true"]').first
        await comp.wait_for(state="visible", timeout=25000)
        print("Composer ready!")
        
        # Count existing images
        initial_imgs = await page.locator('img[src*="/asb/"]').all()
        initial_count = len(initial_imgs)
        print(f"Initial images in project: {initial_count}")
        
        # Submit prompt
        prompt = "Editorial cinematic photograph of sovereign AI data center with glowing glass cube servers, 8k"
        await comp.click()
        await comp.fill(prompt)
        await page.wait_for_timeout(500)
        await page.keyboard.press("Enter")
        print("Prompt submitted to Nano Banana Pro 🍌! Waiting 35s...")
        
        await page.wait_for_timeout(35000)
        
        # Check for new images
        target = Path("output_images/sovereign_banana_direct.jpg")
        saved = False
        for attempt in range(15):
            imgs = await page.locator('img[src*="/asb/"]').all()
            if len(imgs) > initial_count:
                # The newest image is at the top/first
                src = await imgs[0].get_attribute("src")
                if src:
                    resp = await page.request.get(src)
                    data = await resp.body()
                    if len(data) > 20000:
                        with open(target, "wb") as f:
                            f.write(data)
                        print(f"SUCCESS! Saved {target} ({len(data)} bytes)")
                        saved = True
                        break
            print(f"Still rendering... ({attempt+1}/15)")
            await page.wait_for_timeout(3000)
            
        await browser.close()
        if not saved:
            print("Failed to save new image")

if __name__ == "__main__":
    asyncio.run(main())
