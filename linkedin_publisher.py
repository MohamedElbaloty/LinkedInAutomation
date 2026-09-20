"""
Automated LinkedIn Publisher module using Playwright.
Publishes post copy and generated technical infographics to LinkedIn.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

LINKEDIN_PROFILE_DIR = Path(__file__).resolve().parent / "linkedin_profile"

async def _async_publish_to_linkedin(post_text: str, image_path: Optional[Path] = None) -> bool:
    if not LINKEDIN_PROFILE_DIR.exists():
        raise RuntimeError("LinkedIn profile directory not found. Please run login_linkedin.py first.")

    image_path = Path(image_path) if image_path else None
    if image_path and not image_path.exists():
        raise FileNotFoundError(f"Image not found at: {image_path}")

    logger.info("Opening LinkedIn session for publishing...")
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(LINKEDIN_PROFILE_DIR),
            channel="chrome",
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()

        try:
            logger.info("Navigating to LinkedIn feed...")
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=40000)
            await page.wait_for_timeout(4000)

            if "login" in page.url:
                raise RuntimeError("LinkedIn session expired or not logged in. Please run login_linkedin.py.")

            # 1. Click 'Start a post'
            logger.info("Locating 'Start a post' button...")
            start_btn = page.locator(
                'button:has-text("Start a post"), button:has-text("بدء منشور"), '
                'button.share-box-feed-entry__trigger, [aria-label*="Start a post"], [aria-label*="بدء منشور"]'
            ).first
            await start_btn.wait_for(state="visible", timeout=20000)
            await start_btn.click()
            await page.wait_for_timeout(2000)

            # 2. Upload image if provided
            if image_path:
                logger.info("Attaching infographic image: %s", image_path)
                # Check for file input
                file_input = page.locator('input[type="file"]').first
                if await file_input.count() > 0:
                    await file_input.set_input_files(str(image_path.resolve()))
                    await page.wait_for_timeout(3000)
                else:
                    # Click media button first
                    media_btn = page.locator('button[aria-label*="Add media"], button[aria-label*="إضافة وسائط"], button:has-text("Media"), button:has-text("وسائط")').first
                    if await media_btn.is_visible():
                        async with page.expect_file_chooser() as fc_info:
                            await media_btn.click()
                        file_chooser = await fc_info.value
                        await file_chooser.set_files(str(image_path.resolve()))
                        await page.wait_for_timeout(3000)

                # Click Next/Done on image editor dialog if it appears
                next_btn = page.locator('button:has-text("Next"), button:has-text("التالي"), button:has-text("Done"), button:has-text("تم")').first
                if await next_btn.is_visible():
                    logger.info("Confirming image upload...")
                    await next_btn.click()
                    await page.wait_for_timeout(2000)

            # 3. Enter post text
            logger.info("Typing post copy into LinkedIn editor...")
            editor = page.locator('div[role="textbox"], div.ql-editor, div[contenteditable="true"]').first
            await editor.wait_for(state="visible", timeout=15000)
            await editor.click()
            await page.wait_for_timeout(500)
            
            # Fill post text
            clean_text = post_text.strip()
            await editor.fill(clean_text)
            await page.wait_for_timeout(1000)

            # 4. Click 'Post'
            logger.info("Publishing post...")
            post_btn = page.locator(
                'button.share-actions__primary-action, '
                'button:has-text("Post"), button:has-text("نشر")'
            ).first
            await post_btn.wait_for(state="visible", timeout=15000)
            await post_btn.click()

            # Wait for post to submit
            logger.info("Waiting for post confirmation...")
            await page.wait_for_timeout(6000)
            await page.screenshot(path="linkedin_published_success.png")
            logger.info("SUCCESS! Post published to LinkedIn.")
            return True

        finally:
            await browser.close()


def publish_to_linkedin(post_text: str, image_path: Optional[Path] = None) -> bool:
    """Synchronous entry point."""
    return asyncio.run(_async_publish_to_linkedin(post_text, image_path))
