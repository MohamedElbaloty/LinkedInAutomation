"""
Direct Playwright automation module for Google Flow Pro (flow.google.com).
Drives the true 'Nano Banana Pro 🍌' model inside a SINGLE DEDICATED PROJECT
on the user's authenticated Google Flow Pro account.
"""

import asyncio
import logging
import os
from pathlib import Path
from playwright.async_api import async_playwright
from config import FLOW_PROJECT_ID

logger = logging.getLogger(__name__)

async def _async_generate_banana_pro(prompt: str, target_path: Path) -> Path:
    profile_dir = os.path.expandvars(r'%LOCALAPPDATA%\ffroliva\gflow-cli\profile_default')
    logger.info("Connecting to Google Flow Pro with profile: %s", profile_dir)

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
            project_id = FLOW_PROJECT_ID or "84dc3114-9c59-4ac5-b676-0e5050c74a74"
            project_url = f"https://flow.google.com/project/{project_id}"
            logger.info("Navigating directly to dedicated Flow project: %s", project_url)
            await page.goto(project_url, wait_until="domcontentloaded", timeout=35000)

            # Wait for workspace composer to mount
            comp = page.locator('div[contenteditable=true], [contenteditable="true"], .ProseMirror').first
            await comp.wait_for(state="visible", timeout=35000)
            logger.info("Flow project composer ready in dedicated workspace!")

            # Ensure model is set specifically to Nano Banana Pro (Image mode, 16:9)
            pill = page.locator('.bottom-controls button').first
            if await pill.count() > 0 and await pill.is_visible():
                pill_text = (await pill.inner_text()).replace("\n", " ").strip()
                logger.info("Current Flow model pill: '%s'", pill_text)
                if "banana pro" not in pill_text.lower():
                    logger.info("Switching Google Flow to Nano Banana Pro 🍌...")
                    await pill.click()
                    await page.wait_for_timeout(1000)

                    # Ensure Image tab is active
                    img_tab = page.locator('button:has-text("Image"), button:has-text("صورة"), [role="tab"]:has-text("Image"), [role="tab"]:has-text("صورة")').first
                    if await img_tab.is_visible():
                        await img_tab.click()
                        await page.wait_for_timeout(800)

                    # Click model selector dropdown
                    nb_btn = page.locator('button:has-text("Nano Banana"), div[role="button"]:has-text("Nano Banana"), [role="combobox"]').first
                    if await nb_btn.is_visible():
                        await nb_btn.click()
                        await page.wait_for_timeout(800)
                        pro_opt = page.locator('text="Nano Banana Pro", [role="option"]:has-text("Nano Banana Pro"), button:has-text("Nano Banana Pro")').first
                        if await pro_opt.is_visible():
                            await pro_opt.click()
                            await page.wait_for_timeout(800)
                        else:
                            # Fallback check all menu items
                            options = await page.locator('[role="option"], mat-option, .mat-mdc-menu-item').all()
                            for opt in options:
                                otxt = (await opt.inner_text()).strip()
                                if "banana pro" in otxt.lower():
                                    await opt.click()
                                    await page.wait_for_timeout(800)
                                    break

                    # Ensure 16:9 ratio
                    r169 = page.locator('button:has-text("16:9"), [role="radio"]:has-text("16:9")').first
                    if await r169.is_visible():
                        await r169.click()
                        await page.wait_for_timeout(500)

                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(800)

            # Record existing image URLs in this project
            existing_imgs = await page.locator('img[src*="/asb/"], img[src*="http"]').all()
            existing_srcs = set()
            for img in existing_imgs:
                src = await img.get_attribute("src")
                if src:
                    existing_srcs.add(src)
            initial_count = len(existing_srcs)
            logger.info("Initial tracked images in dedicated project: %d", initial_count)

            clean_prompt = prompt.replace("\n", " ").strip()
            logger.info("Submitting LinkedIn Infographic prompt to Nano Banana Pro 🍌: %s", clean_prompt[:95])
            await comp.click()
            await comp.fill(clean_prompt)
            await page.wait_for_timeout(600)

            # Submit generation via Enter
            await page.keyboard.press("Enter")
            logger.info("Generation triggered! Monitoring Google Flow for new Nano Banana Pro visual...")

            saved = False
            for attempt in range(1, 45):  # Poll up to ~150 seconds
                await page.wait_for_timeout(3500)
                current_imgs = await page.locator('img[src*="/asb/"]').all()
                for img in current_imgs:
                    src = await img.get_attribute("src")
                    if src and src not in existing_srcs:
                        logger.info("New Nano Banana Pro visual detected: %s", src[:60])
                        resp = await page.request.get(src)
                        data = await resp.body()
                        if len(data) > 15000:
                            with open(target_path, "wb") as f:
                                f.write(data)
                            logger.info("Nano Banana Pro infographic saved to %s (%d bytes)", target_path, len(data))
                            saved = True
                            break

                if saved:
                    break
                if attempt % 5 == 0:
                    logger.info("Rendering in progress on Google Flow... elapsed ~%ds (attempt %d/45)", int(attempt * 3.5), attempt)

            if not saved:
                # Capture snapshot if direct download timed out
                await page.screenshot(path="flow_banana_generation_state.png")
                logger.warning("Direct tile download timed out, snapshot saved.")

            return target_path

        finally:
            await browser.close()


def generate_flow_banana_pro(prompt: str, target_path: Path) -> Path:
    """Synchronous entry point for pipeline integration."""
    return asyncio.run(_async_generate_banana_pro(prompt, target_path))

