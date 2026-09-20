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
        await page.goto("https://flow.google.com/project/a6bff29c-b003-4ddd-86af-84bb350f50cd", wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)
        
        imgs = await page.locator('img[src*="/asb/"]').all()
        print(f"Found images: {len(imgs)}")
        for i, img in enumerate(imgs):
            src = await img.get_attribute("src")
            resp = await page.request.get(src)
            data = await resp.body()
            print(f"Img {i}: len={len(data)}")
            with open(f"output_images/quantum_banana_{i}.jpg", "wb") as f:
                f.write(data)
                
        await page.screenshot(path="flow_a6b_finished.png")
        print("Done!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
