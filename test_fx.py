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
        print("Navigating to https://labs.google/fx/tools/flow...")
        await page.goto("https://labs.google/fx/tools/flow", wait_until="domcontentloaded", timeout=35000)
        await page.wait_for_timeout(4000)
        print("Final URL:", page.url)
        await page.screenshot(path="flow_fx_auth.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
