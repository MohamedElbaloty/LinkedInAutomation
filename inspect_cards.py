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
        await page.goto("https://flow.google.com/?hl=ar", wait_until="networkidle", timeout=35000)
        await page.wait_for_timeout(3000)
        
        cards = await page.locator('a[href*="/project/"]').all()
        print(f"Cards count: {len(cards)}")
        for i, c in enumerate(cards[:6]):
            href = await c.get_attribute("href")
            # Get text or img alt
            text = (await c.inner_text()).replace("\n", " ").strip()
            imgs = await c.locator("img").all()
            srcs = [await img.get_attribute("src") for img in imgs]
            print(f"Card {i}: href={href} | text='{text}' | imgs={len(imgs)}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
