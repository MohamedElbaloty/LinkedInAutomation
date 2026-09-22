"""
Persistent Background Scheduler Service for Cloud and Local Automation.
Manages strategic LinkedIn organic growth posting windows (08:45, 13:15, 18:45).
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import BASE_DIR, DEFAULT_SCHEDULE_TIMES, SCHEDULE_TIMES, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from fetcher import get_latest_unread_article, mark_as_posted
from ai_generator import create_ai_bundle
from linkedin_api import publish_article_to_linkedin_safe
from video_extractor import extract_and_download_video

logger = logging.getLogger(__name__)

SCHEDULE_CONFIG_FILE = BASE_DIR / "schedule_config.json"
TIMEZONE_STR = os.getenv("TIMEZONE", "Africa/Cairo").strip() or "Africa/Cairo"


def load_schedule_settings() -> Dict[str, any]:
    """Loads scheduler settings from disk or defaults."""
    if SCHEDULE_CONFIG_FILE.exists():
        try:
            with open(SCHEDULE_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Error reading %s: %s", SCHEDULE_CONFIG_FILE, e)

    default_settings = {
        "enabled": True,
        "times": SCHEDULE_TIMES or DEFAULT_SCHEDULE_TIMES,
        "strategy": "Tech Organic Growth (3 Daily Windows)",
        "last_run": None,
        "next_run": None,
    }
    save_schedule_settings(default_settings)
    return default_settings


def save_schedule_settings(settings: Dict[str, any]) -> None:
    """Persists scheduler settings to disk."""
    try:
        with open(SCHEDULE_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("Failed to save schedule settings: %s", e)


async def send_telegram_broadcast(
    bot,
    chat_id: str,
    text: str,
    caption: str,
    media_path: Optional[Path] = None,
) -> bool:
    """
    Resilient Telegram publisher supporting native Video, Photo, or Text.
    Features:
    - Caption length truncation to <= 1000 characters (safe for Telegram's 1024 limit).
    - Message length truncation to <= 4000 characters (safe for Telegram's 4096 limit).
    - Automatic markdown parse fallback: if Telegram raises an entity parse error
      (e.g. "Can't parse entities: can't find end of the entity starting at byte offset ..."),
      it immediately catches the error and resends without parse_mode (as plain text).
    - Native video streaming support for .mp4, .mov, .mkv, .webm.
    """
    from telegram.constants import ParseMode

    safe_caption = caption.strip() if caption else ""
    if len(safe_caption) > 1000:
        safe_caption = safe_caption[:995] + "..."

    safe_text = text.strip() if text else ""
    if len(safe_text) > 4000:
        safe_text = safe_text[:3990] + "..."

    # Determine media type if file exists
    is_video = False
    is_image = False
    resolved_path: Optional[Path] = None

    if media_path:
        p = Path(media_path)
        if p.exists() and p.stat().st_size > 0:
            resolved_path = p
            ext = p.suffix.lower()
            if ext in [".mp4", ".mov", ".mkv", ".webm", ".m4v"]:
                is_video = True
            elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
                is_image = True

    # 1. Try sending Native Video
    if is_video and resolved_path:
        logger.info("Delivering native video to Telegram: %s", resolved_path.name)
        try:
            with open(resolved_path, "rb") as vf:
                await bot.send_video(
                    chat_id=chat_id,
                    video=vf,
                    caption=safe_caption,
                    parse_mode=ParseMode.MARKDOWN,
                    supports_streaming=True,
                )
            return True
        except Exception as e:
            err_str = str(e).lower()
            if "can't parse entities" in err_str or "entity" in err_str or "parse" in err_str:
                logger.warning("Telegram video Markdown error (%s). Retrying as plain text...", e)
                with open(resolved_path, "rb") as vf:
                    await bot.send_video(
                        chat_id=chat_id,
                        video=vf,
                        caption=safe_caption,
                        parse_mode=None,
                        supports_streaming=True,
                    )
                return True
            logger.warning("Failed sending video to Telegram (%s). Falling back to text/image.", e)

    # 2. Try sending Studio Infographic Photo
    if is_image and resolved_path:
        logger.info("Delivering studio infographic to Telegram: %s", resolved_path.name)
        try:
            with open(resolved_path, "rb") as pf:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=pf,
                    caption=safe_caption,
                    parse_mode=ParseMode.MARKDOWN,
                )
            return True
        except Exception as e:
            err_str = str(e).lower()
            if "can't parse entities" in err_str or "entity" in err_str or "parse" in err_str:
                logger.warning("Telegram photo Markdown error (%s). Retrying as plain text...", e)
                with open(resolved_path, "rb") as pf:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=pf,
                        caption=safe_caption,
                        parse_mode=None,
                    )
                return True
            logger.warning("Failed sending photo to Telegram (%s). Falling back to text message.", e)

    # 3. Text Message Fallback
    fallback_content = safe_text if safe_text else safe_caption
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=fallback_content,
            parse_mode=ParseMode.MARKDOWN,
        )
        return True
    except Exception as e:
        err_str = str(e).lower()
        if "can't parse entities" in err_str or "entity" in err_str or "parse" in err_str:
            logger.warning("Telegram text Markdown error (%s). Retrying as plain text...", e)
            await bot.send_message(
                chat_id=chat_id,
                text=fallback_content,
                parse_mode=None,
            )
            return True
        raise e


class GrowthSchedulerService:
    """Orchestrates scheduled background publishing jobs."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.current_settings = load_schedule_settings()
        self.is_running_job = False

    def start(self) -> None:
        """Starts the scheduler with active jobs."""
        if not self.scheduler.running:
            self.rebuild_jobs()
            self.scheduler.start()
            logger.info("Autonomous LinkedIn Growth Scheduler started!")

    def stop(self) -> None:
        """Stops the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped.")

    def rebuild_jobs(self) -> None:
        """Clears existing jobs and registers new ones based on current settings."""
        self.scheduler.remove_all_jobs()
        self.current_settings = load_schedule_settings()

        if not self.current_settings.get("enabled", True):
            logger.info("Scheduler is disabled in settings. No active cron jobs.")
            return

        times = self.current_settings.get("times", DEFAULT_SCHEDULE_TIMES)
        for t in times:
            try:
                parts = t.strip().split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0

                job_id = f"linkedin_post_{hour:02d}_{minute:02d}"
                self.scheduler.add_job(
                    self.execute_pipeline_job,
                    trigger=CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE_STR),
                    id=job_id,
                    replace_existing=True,
                    name=f"LinkedIn Organic Post at {t} ({TIMEZONE_STR})",
                )
                logger.info("Registered scheduled job: %s at %02d:%02d (%s timezone)", job_id, hour, minute, TIMEZONE_STR)
            except Exception as e:
                logger.error("Failed to register job for time '%s': %s", t, e)

    def update_times(self, new_times: List[str], enabled: bool = True) -> Dict[str, any]:
        """Updates schedule times and rebuilds cron jobs."""
        cleaned_times = []
        for t in new_times:
            t = t.strip()
            if ":" in t:
                cleaned_times.append(t)

        self.current_settings["times"] = cleaned_times or DEFAULT_SCHEDULE_TIMES
        self.current_settings["enabled"] = enabled
        save_schedule_settings(self.current_settings)
        self.rebuild_jobs()
        return self.current_settings

    async def execute_pipeline_job(self) -> Dict[str, any]:
        """Core publishing routine executed either on schedule or via 'Publish Now' (LinkedIn + Telegram)."""
        if self.is_running_job:
            logger.warning("A publishing job is already in progress. Skipping duplicate run.")
            return {"success": False, "error": "Job already running"}

        self.is_running_job = True
        result = {
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "article_title": "",
            "media_type": "none",
            "linkedin": {},
            "telegram_sent": False,
            "error": None,
        }

        try:
            logger.info("Triggering autonomous news discovery (FinTech / PropTech / AI)...")
            article = get_latest_unread_article()
            if not article:
                logger.info("No unread AI/FinTech/PropTech articles found in configured feeds.")
                result["error"] = "No new unread articles available"
                return result

            result["article_title"] = article.title
            logger.info("Processing article: '%s' from %s", article.title, article.source)

            loop = asyncio.get_running_loop()

            # 1. Scan for native video on article page (e.g. YouTube demo, MP4, ROSHN/NEOM project showcase)
            logger.info("Scanning article page for native video: %s", article.link)
            video_path = await loop.run_in_executor(None, extract_and_download_video, article.link, article.id)

            has_video = video_path is not None and video_path.exists()
            if has_video:
                result["media_type"] = "video"
                logger.info("Native video acquired (%s)! Skipping static image generation to post video directly.", video_path.name)
            else:
                result["media_type"] = "image"
                logger.info("No native video found on page. Falling back to Nano Banana Pro studio infographic.")

            # 2. Generate LinkedIn copy and dynamic modern visual if no video
            bundle = await loop.run_in_executor(None, create_ai_bundle, article, has_video)

            post_text = bundle.get("linkedin_post") or bundle.get("post_text", "")
            telegram_caption = bundle.get("telegram_caption") or bundle.get("short_hook", "")
            visual_archetype = bundle.get("visual_archetype", "editorial_hero")
            result["visual_archetype"] = visual_archetype
            logger.info("Dynamic Art Direction selected visual archetype: '%s'", visual_archetype)
            media_path = video_path if has_video else (Path(bundle["image_path"]) if bundle.get("image_path") else None)

            # 3. Publish to LinkedIn (Safe official REST API or browser fallback)
            logger.info(
                "Publishing in-depth article to LinkedIn (Length: %d chars, media: %s, archetype: %s)...",
                len(post_text),
                result["media_type"],
                visual_archetype,
            )
            try:
                def _publish_lk():
                    return publish_article_to_linkedin_safe(post_text, media_path=media_path)

                linkedin_res = await loop.run_in_executor(None, _publish_lk)
                result["linkedin"] = linkedin_res
                logger.info("LinkedIn publishing result: %s", linkedin_res)
            except Exception as lk_exc:
                logger.error("LinkedIn publish step failed: %s", lk_exc)
                result["linkedin"] = {"success": False, "error": str(lk_exc)}

            # 4. Deliver to Telegram channel / chat as unified post
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                try:
                    from telegram import Bot
                    bot = Bot(token=TELEGRAM_BOT_TOKEN)
                    caption = f"🚀 **[LinkedIn Auto-Publish]**\n{telegram_caption}"

                    sent = await send_telegram_broadcast(
                        bot=bot,
                        chat_id=TELEGRAM_CHAT_ID,
                        text=post_text,
                        caption=caption,
                        media_path=media_path,
                    )
                    result["telegram_sent"] = sent
                    logger.info("Delivered live post to Telegram successfully!")
                except Exception as tg_err:
                    logger.warning("Telegram notification failed: %s", tg_err)

            # 5. Mark article as posted in SQLite database
            mark_as_posted(article.id, article.title, article.published_at)

            # Update settings with last run
            self.current_settings["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_schedule_settings(self.current_settings)

            result["success"] = True
            logger.info("Autonomous execution completed successfully!")

        except Exception as e:
            logger.error("Error executing publishing pipeline: %s", e, exc_info=True)
            result["error"] = str(e)
        finally:
            self.is_running_job = False

        return result

    async def execute_telegram_job(self) -> Dict[str, any]:
        """Publishes directly and EXCLUSIVELY to Telegram (NEVER to LinkedIn)."""
        if self.is_running_job:
            logger.warning("A publishing job is already in progress. Skipping duplicate run.")
            return {"success": False, "error": "Job already running"}

        self.is_running_job = True
        result = {
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "article_title": "",
            "media_type": "none",
            "telegram_sent": False,
            "error": None,
        }

        try:
            logger.info("Triggering Telegram-exclusive news discovery (FinTech / PropTech / AI)...")
            article = get_latest_unread_article()
            if not article:
                logger.info("No unread AI/FinTech/PropTech articles found in configured feeds.")
                result["error"] = "No new unread articles available"
                return result

            result["article_title"] = article.title
            logger.info("Processing article exclusively for Telegram: '%s' from %s", article.title, article.source)

            loop = asyncio.get_running_loop()

            # 1. Scan for native video on article page
            logger.info("Scanning article page for native video: %s", article.link)
            video_path = await loop.run_in_executor(None, extract_and_download_video, article.link, article.id)

            has_video = video_path is not None and video_path.exists()
            if has_video:
                result["media_type"] = "video"
                logger.info("Native video acquired (%s)! Skipping static image generation to post video to Telegram.", video_path.name)
            else:
                result["media_type"] = "image"
                logger.info("No native video found on page. Generating Nano Banana Pro studio infographic for Telegram.")

            # 2. Generate copy and dynamic modern visual if no video
            bundle = await loop.run_in_executor(None, create_ai_bundle, article, has_video)

            post_text = bundle.get("linkedin_post") or bundle.get("post_text", "")
            telegram_caption = bundle.get("telegram_caption") or bundle.get("short_hook", "")
            visual_archetype = bundle.get("visual_archetype", "editorial_hero")
            result["visual_archetype"] = visual_archetype
            logger.info("Telegram Dynamic Art Direction selected visual archetype: '%s'", visual_archetype)
            media_path = video_path if has_video else (Path(bundle["image_path"]) if bundle.get("image_path") else None)

            # 3. Deliver to Telegram channel / chat (EXCLUSIVELY - NEVER TO LINKEDIN)
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                try:
                    from telegram import Bot
                    bot = Bot(token=TELEGRAM_BOT_TOKEN)
                    caption = f"🚀 **[AI & FinTech GCC Intelligence]**\n{telegram_caption}"

                    sent = await send_telegram_broadcast(
                        bot=bot,
                        chat_id=TELEGRAM_CHAT_ID,
                        text=post_text,
                        caption=caption,
                        media_path=media_path,
                    )
                    result["telegram_sent"] = sent
                    result["success"] = True
                    logger.info("Delivered post to Telegram successfully (Telegram exclusive)!")
                except Exception as tg_err:
                    logger.error("Telegram delivery failed: %s", tg_err)
                    result["error"] = f"Telegram error: {str(tg_err)}"
                    return result
            else:
                result["error"] = "Telegram credentials (TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID) are missing."
                return result

            # 4. Mark article as posted in SQLite database
            mark_as_posted(article.id, article.title, article.published_at)

            # Update settings with last run
            self.current_settings["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_schedule_settings(self.current_settings)

            result["success"] = True

        except Exception as e:
            logger.error("Error executing Telegram publishing: %s", e, exc_info=True)
            result["error"] = str(e)
        finally:
            self.is_running_job = False

        return result


# Global scheduler service instance
scheduler_service = GrowthSchedulerService()
