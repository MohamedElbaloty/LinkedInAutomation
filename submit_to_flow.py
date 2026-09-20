import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

async def submit_flow_prompt(prompt_text: str):
    profile = os.path.expandvars(r"%LOCALAPPDATA%\ffroliva\gflow-cli\profile_default")
    project_url = "https://flow.google.com/project/84dc3114-9c59-4ac5-b676-0e5050c74a74"
    
    print(f"Connecting to Flow project: {project_url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=profile,
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.goto(project_url, wait_until="domcontentloaded", timeout=40000)
        
        comp = page.locator('div[contenteditable=true], [contenteditable="true"], .ProseMirror').first
        await comp.wait_for(state="visible", timeout=30000)
        print("Flow project composer is visible and ready!")
        
        # Count initial items
        initial_imgs = len(await page.locator('img[src*="/asb/"]').all())
        initial_vids = len(await page.locator('video').all())
        print(f"Initial state: {initial_imgs} images, {initial_vids} videos")
        
        # Click and fill prompt
        await comp.click()
        clean_prompt = prompt_text.replace("\n", " ").strip()
        print(f"Submitting prompt: {clean_prompt[:80]}...")
        await comp.fill(clean_prompt)
        await page.wait_for_timeout(1000)
        
        # Submit via Enter
        await page.keyboard.press("Enter")
        print("Prompt submitted to Google Flow! Capturing live proof screenshot...")
        
        await page.wait_for_timeout(6000)
        live_proof_path = Path("output_images/flow_live_execution.png")
        live_proof_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(live_proof_path))
        print(f"Live Flow proof screenshot saved to {live_proof_path}!")
        
        # Wait for generation progress (up to 40 seconds)
        print("Monitoring Flow generation...")
        new_asset_path = None
        for attempt in range(12):
            await page.wait_for_timeout(3500)
            
            # Check for new video
            vids = await page.locator('video').all()
            if len(vids) > initial_vids:
                for v in vids:
                    src = await v.get_attribute("src")
                    if src and "blob:" not in src:
                        resp = await page.request.get(src)
                        data = await resp.body()
                        if len(data) > 30000:
                            v_path = Path("output_images/flow_generated_video.mp4")
                            with open(v_path, "wb") as f:
                                f.write(data)
                            print(f"New video downloaded: {v_path} ({len(data)} bytes)")
                            new_asset_path = v_path
                            break
            if new_asset_path:
                break
                
            # Check for new image
            imgs = await page.locator('img[src*="/asb/"]').all()
            if len(imgs) > initial_imgs:
                src = await imgs[0].get_attribute("src")
                if src:
                    resp = await page.request.get(src)
                    data = await resp.body()
                    if len(data) > 15000:
                        img_path = Path("output_images/flow_generated_asset.jpg")
                        with open(img_path, "wb") as f:
                            f.write(data)
                        print(f"New image downloaded: {img_path} ({len(data)} bytes)")
                        new_asset_path = img_path
                        break
            if new_asset_path:
                break
            print(f"Elapsed ~{(attempt+1)*3.5:.0f}s...")
            
        # Capture final state screenshot
        final_proof_path = Path("output_images/flow_final_state.png")
        await page.screenshot(path=str(final_proof_path))
        print(f"Final Flow workspace state saved to {final_proof_path}")
        
        await browser.close()
        return new_asset_path, live_proof_path, final_proof_path

if __name__ == "__main__":
    test_prompt = "A 3Blue1Brown Deep Manim mathematical animation on dark slate background (#0B0F19). Visualizing Jev transformer model: calibrated probability vectors over decision simplex, zero hallucinations, glowing vector tensors, clean LaTeX notation, 16:9 widescreen"
    asyncio.run(submit_flow_prompt(test_prompt))
