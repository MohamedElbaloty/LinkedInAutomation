"""
One-time LinkedIn login helper.
Opens a visible Chrome window for the user to log in to LinkedIn once.
Saves the session/cookies for automated headless publishing.
"""

import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

LINKEDIN_PROFILE_DIR = Path(r"c:\Users\lenovo\Downloads\LinkedInWorkFlow\linkedin_profile")
LINKEDIN_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

async def login():
    print("=" * 60)
    print("Opening Chrome for LinkedIn login...")
    print("Please enter your LinkedIn credentials in the opened browser window.")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(LINKEDIN_PROFILE_DIR),
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ],
            no_viewport=True
        )
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        
        print("\nWaiting for you to log in...")
        print("The script will automatically detect when you reach the LinkedIn Feed (/feed).\n")
        
        # Poll until user logs in and reaches /feed
        while True:
            await page.wait_for_timeout(2000)
            url = page.url
            if "/feed" in url or "/in/" in url:
                print("\n✅ SUCCESS! Login detected! Logged into LinkedIn Feed.")
                break
                
        print("Saving session and closing browser in 3 seconds...")
        await page.wait_for_timeout(3000)
        await browser.close()
        print("Session saved successfully! You are now ready for automated publishing.")

if __name__ == "__main__":
    asyncio.run(login())
