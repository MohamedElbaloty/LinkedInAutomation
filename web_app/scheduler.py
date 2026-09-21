"""
Persistent Background Scheduler Service for Cloud and Local Automation.
Manages strategic LinkedIn organic growth posting windows (08:45, 13:15, 18:45).
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import BASE_DIR, DEFAULT_SCHEDULE_TIMES, SCHEDULE_TIMES, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from fetcher import get_latest_unread_article, mark_as_posted
from ai_generator import create_ai_bundle
from linkedin_api import publish_article_to_linkedin_safe

logger = logging.getLogger(__name__)

SCHEDULE_CONFIG_FILE = BASE_DIR / "schedule_config.json"


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
                    trigger=CronTrigger(hour=hour, minute=minute),
                    id=job_id,
                    replace_existing=True,
                    name=f"LinkedIn Organic Post at {t}",
                )
                logger.info("Registered scheduled job: %s at %02d:%02d UTC/Local", job_id, hour, minute)
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
        """Core publishing routine executed either on schedule or via 'Publish Now'."""
        if self.is_running_job:
            logger.warning("A publishing job is already in progress. Skipping duplicate run.")
            return {"success": False, "error": "Job already running"}

        self.is_running_job = True
        result = {
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "article_title": "",
            "linkedin": {},
            "telegram_sent": False,
            "error": None,
        }

        try:
            logger.info("Triggering autonomous news discovery...")
            article = get_latest_unread_article()
            if not article:
                logger.info("No unread AI articles found in configured feeds.")
                result["error"] = "No new unread articles available"
                return result

            result["article_title"] = article.title
            logger.info("Processing article: '%s' from %s", article.title, article.source)

            # 1. Generate post text & Nano Banana Pro image
            loop = asyncio.get_running_loop()
            bundle = await loop.run_in_executor(None, create_ai_bundle, article)

            post_text = bundle.get("linkedin_post") or bundle.get("post_text", "")
            telegram_caption = bundle.get("telegram_caption") or bundle.get("short_hook", "")
            image_path = Path(bundle["image_path"])

            # 2. Publish to LinkedIn (Safe official REST API or fallback)
            logger.info("Publishing in-depth article to LinkedIn (%d characters)...", len(post_text))
            try:
                def _publish_lk():
                    return publish_article_to_linkedin_safe(post_text, image_path)

                linkedin_res = await loop.run_in_executor(None, _publish_lk)
                result["linkedin"] = linkedin_res
                logger.info("LinkedIn publishing result: %s", linkedin_res)
            except Exception as lk_exc:
                logger.error("LinkedIn publish step failed: %s", lk_exc)
                result["linkedin"] = {"success": False, "error": str(lk_exc)}

            # 3. Deliver to Telegram channel / chat as unified post
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                try:
                    from telegram import Bot
                    from telegram.constants import ParseMode

                    bot = Bot(token=TELEGRAM_BOT_TOKEN)
                    caption = f"🚀 **[LinkedIn Auto-Publish]**\n{telegram_caption}"
                    if len(caption) > 1020:
                        caption = caption[:1017] + "..."

                    if image_path.exists():
                        with open(image_path, "rb") as pf:
                            await bot.send_photo(
                                chat_id=TELEGRAM_CHAT_ID,
                                photo=pf,
                                caption=caption,
                                parse_mode=ParseMode.MARKDOWN,
                            )
                    else:
                        await bot.send_message(
                            chat_id=TELEGRAM_CHAT_ID,
                            text=post_text,
                            parse_mode=ParseMode.MARKDOWN,
                        )
                    result["telegram_sent"] = True
                    logger.info("Delivered live post to Telegram!")
                except Exception as tg_err:
                    logger.warning("Telegram notification failed: %s", tg_err)

            # 4. Mark article as posted in SQLite database
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


# Global scheduler service instance
scheduler_service = GrowthSchedulerService()
