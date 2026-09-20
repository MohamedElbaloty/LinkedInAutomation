"""
Direct Playwright automation module for Google Flow Video Generation.
Generates Deep Manim (3Blue1Brown mathematical style) technical videos
inside the user's dedicated project on Google Flow Pro.
"""

import asyncio
import logging
import os
from pathlib import Path
from playwright.async_api import async_playwright
from config import FLOW_PROJECT_ID

logger = logging.getLogger(__name__)


async def _async_generate_flow_video(prompt: str, target_path: Path) -> Path:
    profile_dir = os.path.expandvars(r'%LOCALAPPDATA%\ffroliva\gflow-cli\profile_default')
    logger.info("Connecting to Google Flow Pro for Deep Manim Video generation...")

    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            channel="chrome",
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()

        try:
            # 1. Open Google Flow dashboard
            logger.info("Accessing Google Flow Pro session...")
            await page.goto("https://flow.google.com/?hl=ar", wait_until="domcontentloaded", timeout=35000)
            await page.wait_for_timeout(3000)

            # 2. Enter dedicated project
            project_id = FLOW_PROJECT_ID or "84dc3114-9c59-4ac5-b676-0e5050c74a74"
            logger.info("Navigating to dedicated Flow project: %s", project_id)

            proj_link = page.locator(f'a[href*="{project_id}"]').first
            if not await proj_link.is_visible():
                proj_link = page.locator('a[href*="/project/"]').first

            await proj_link.click()
            await page.wait_for_url("**/project/**", timeout=25000)
            await page.wait_for_timeout(3000)
            logger.info("Connected to dedicated Flow workspace: %s", page.url)

            # Wait for composer
            comp = page.locator('div[contenteditable=true], [contenteditable="true"]').first
            await comp.wait_for(state="visible", timeout=30000)

            # 3. Ensure Video Mode is activated
            settings_pill = page.locator('[aria-label="مشغِّل الإعدادات"]').first
            pill_text = await settings_pill.inner_text() if await settings_pill.is_visible() else ""

            if "فيديو" not in pill_text and "video" not in pill_text.lower():
                logger.info("Switching Flow composer to Video Mode (Deep Manim)...")
                await settings_pill.click()
                await page.wait_for_timeout(1000)

                video_tab = page.locator('button:has-text("فيديو"), [role="tab"]:has-text("فيديو")').first
                if await video_tab.is_visible():
                    await video_tab.click()
                    await page.wait_for_timeout(1000)

                # Select 16:9
                r169 = page.locator('button:has-text("16:9"), [role="radio"]:has-text("16:9")').first
                if await r169.is_visible():
                    await r169.click()
                    await page.wait_for_timeout(500)

                await page.keyboard.press("Escape")
                await page.wait_for_timeout(1000)

            # Record initial state
            initial_tiles = await page.locator('flow-image-tile, flow-video-tile, video').all()
            initial_count = len(initial_tiles)
            logger.info("Initial tiles/videos in workspace: %d", initial_count)

            # 4. Submit Deep Manim prompt
            clean_prompt = prompt.replace("\n", " ").strip()
            logger.info("Submitting Deep Manim Video prompt to Google Flow: %s", clean_prompt[:95])
            await comp.click()
            await comp.fill(clean_prompt)
            await page.wait_for_timeout(500)

            # Click generate
            gen_btn = page.locator('flow-generate-icon-button, button[aria-label*="إنشاء"]').first
            if await gen_btn.is_visible():
                await gen_btn.click()
            else:
                await page.keyboard.press("Enter")

            logger.info("Deep Manim video rendering on Google Flow... (waiting up to 180s)")
            saved = False

            # Poll for new video
            for attempt in range(1, 60):
                await page.wait_for_timeout(4000)
                videos = await page.locator('video').all()
                for vid in videos:
                    src = await vid.get_attribute("src")
                    if src and ("blob:" not in src):
                        logger.info("Found video element with direct src: %s", src[:60])
                        resp = await page.request.get(src)
                        data = await resp.body()
                        if len(data) > 50000:
                            with open(target_path, "wb") as f:
                                f.write(data)
                            logger.info("Saved Deep Manim video to %s (%d bytes)", target_path, len(data))
                            saved = True
                            break

                if saved:
                    break

                current_tiles = await page.locator('flow-image-tile, flow-video-tile').all()
                if len(current_tiles) > initial_count:
                    new_tile = current_tiles[0]
                    vid_el = new_tile.locator('video').first
                    if await vid_el.is_visible():
                        src = await vid_el.get_attribute("src")
                        if src and "blob:" not in src:
                            resp = await page.request.get(src)
                            data = await resp.body()
                            if len(data) > 50000:
                                with open(target_path, "wb") as f:
                                    f.write(data)
                                logger.info("Saved Deep Manim video from tile to %s (%d bytes)", target_path, len(data))
                                saved = True
                                break

                if saved:
                    break
                if attempt % 5 == 0:
                    logger.info("Video still generating... elapsed ~%ds (attempt %d/60)", attempt * 4, attempt)

            if not saved:
                logger.warning("Direct video download timed out; taking workspace snapshot.")
                await page.screenshot(path="flow_video_generated_state.png")

            return target_path

        finally:
            await browser.close()


def generate_flow_video(prompt: str, target_path: Path) -> Path:
    """Synchronous entry point for pipeline integration."""
    return asyncio.run(_async_generate_flow_video(prompt, target_path))
