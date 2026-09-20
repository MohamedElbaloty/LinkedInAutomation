import asyncio
import os
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
        print("Opening 84dc3114-9c59-4ac5-b676-0e5050c74a74...")
        await page.goto("https://flow.google.com/project/84dc3114-9c59-4ac5-b676-0e5050c74a74", wait_until="domcontentloaded", timeout=35000)
        await page.wait_for_timeout(5000)
        
        await page.screenshot(path="flow_84dc_current.png")
        print("Screenshot saved to flow_84dc_current.png")
        
        # Check composer & tiles
        comp = page.locator('div[contenteditable=true], [contenteditable="true"]').first
        print("Composer visible:", await comp.is_visible())
        
        tiles = await page.locator('flow-image-tile, flow-video-tile').all()
        print(f"Total tiles: {len(tiles)}")
        
        imgs = await page.locator('img[src*="/asb/"]').all()
        print(f"Total /asb/ images: {len(imgs)}")
        
        videos = await page.locator('video').all()
        print(f"Total videos: {len(videos)}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
