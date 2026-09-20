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
        await page.goto("https://flow.google.com/project/16b5c658-73af-44aa-80ba-46b6593ad68b", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        
        imgs = await page.locator('img[src*="/asb/"]').all()
        print(f"Found {len(imgs)} Flow images")
        for i, img in enumerate(imgs):
            src = await img.get_attribute("src")
            print(f"Fetching {src[:60]}...")
            resp = await page.request.get(src)
            data = await resp.body()
            print(f"Status: {resp.status}, length: {len(data)}")
            with open(f"output_images/banana_pro_{i}.jpg", "wb") as f:
                f.write(data)
            print(f"Saved banana_pro_{i}.jpg!")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
