"""
Main orchestrator and scheduler module for ai_news_agent.
Coordinates news fetching, AI post & image generation, Telegram dispatch,
and schedules recurring runs using APScheduler.
"""

import argparse
import logging
import sys
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import SCHEDULE_HOURS, validate_config
from fetcher import get_latest_unread_article, mark_as_posted
from ai_generator import create_ai_bundle
from telegram_bot import TelegramPublisher

# Ensure Windows stdout supports UTF-8 and Arabic/emojis cleanly
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("ai_news_agent")


def run_pipeline(dry_run: bool = False) -> bool:
    """
    Executes an end-to-end run of the AI news pipeline:
    1. Fetches the latest unread high-relevance AI news article.
    2. Uses Gemini to draft an Arabic LinkedIn post and an English Imagen prompt.
    3. Uses Imagen 3 to generate a clean, editorial tech visualization.
    4. Publishes the image and post bundle to Telegram.
    5. Records the article ID in SQLite to prevent duplicate posts.

    Returns:
        bool: True if an article was processed and published, False otherwise.
    """
    logger.info("=" * 60)
    logger.info("Starting AI News Agent Pipeline Run at %s", datetime.now().isoformat())
    logger.info("=" * 60)

    # 1. Validate environment credentials
    if not dry_run:
        try:
            validate_config(require_keys=True)
        except ValueError as e:
            logger.error("Configuration error: %s", str(e))
            return False

    # 2. Fetch the latest unread AI article
    logger.info("Step 1/4: Fetching latest unread high-impact AI news...")
    article = get_latest_unread_article()
    if not article:
        logger.info("No new unread AI news found across configured feeds. Standing by.")
        return False

    logger.info("Selected article: '%s' from %s", article.title, article.source)

    try:
        # 3. Generate AI LinkedIn post and Imagen visual asset
        logger.info("Step 2/4: Generating Arabic LinkedIn post and Imagen 3 visual...")
        bundle = create_ai_bundle(article)
        post_text = bundle["post_text"]
        short_hook = bundle["short_hook"]
        image_path = bundle["image_path"]
        image_prompt = bundle["image_prompt"]

        logger.info("Generated Image Prompt: %s", image_prompt)
        logger.info("Generated Post Length: %d characters", len(post_text))

        if dry_run:
            logger.info("--- [DRY RUN MODE ENABLED] ---")
            logger.info("Short Hook:\n%s", short_hook)
            logger.info("Full Post Text:\n%s", post_text)
            logger.info("Local Image Path: %s", image_path)
            logger.info("Dry run finished successfully. Skipping Telegram dispatch & DB mark.")
            return True

        # 4. Dispatch bundle to Telegram
        logger.info("Step 3/4: Publishing bundle to Telegram...")
        publisher = TelegramPublisher()
        publisher.send_bundle(
            image_path=image_path,
            post_text=post_text,
            short_hook=short_hook,
        )

        # 5. Persist to SQLite to prevent duplicates
        logger.info("Step 4/4: Marking article as posted in SQLite database...")
        mark_as_posted(
            article_id=article.id,
            title=article.title,
            published_at=article.published_at,
        )

        logger.info("Pipeline run completed successfully for article: '%s'", article.title)
        return True

    except Exception as e:
        logger.error("Pipeline run failed: %s", str(e), exc_info=True)
        return False


def start_scheduler(hours=SCHEDULE_HOURS, dry_run: bool = False) -> None:
    """
    Runs the pipeline immediately once, then schedules recurring executions
    using APScheduler at the specified hours (e.g., 09:00 and 18:00).
    """
    logger.info("Starting initial pipeline run before scheduling...")
    run_pipeline(dry_run=dry_run)

    scheduler = BlockingScheduler()
    hours_str = ",".join(str(h) for h in hours)
    trigger = CronTrigger(hour=hours_str, minute="0")

    scheduler.add_job(
        func=run_pipeline,
        trigger=trigger,
        kwargs={"dry_run": dry_run},
        id="ai_news_agent_cron",
        name="Twice-Daily AI News Agent Run",
        replace_existing=True,
    )

    logger.info("Scheduler initialized. Scheduled runs active daily at hours: %s:00", hours_str)
    logger.info("Press Ctrl+C to terminate the agent.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler received shutdown signal. Stopping AI News Agent cleanly...")
        scheduler.shutdown(wait=False)


def parse_arguments() -> argparse.Namespace:
    """Parses command line flags."""
    parser = argparse.ArgumentParser(
        description="ai_news_agent: Automated AI news tracking, Arabic LinkedIn post generation, Imagen 3, and Telegram delivery."
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Execute a single pipeline run immediately and exit (do not start scheduler).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and generate content without sending to Telegram or writing to DB.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    if args.run_once:
        logger.info("Executing in single-run mode (--run-once)...")
        success = run_pipeline(dry_run=args.dry_run)
        sys.exit(0 if success else 1)
    else:
        start_scheduler(dry_run=args.dry_run)
