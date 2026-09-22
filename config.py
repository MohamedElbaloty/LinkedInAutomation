"""
Configuration module for ai_news_agent.
Loads environment variables, manages database settings, and provides curated AI RSS feeds.
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load .env file from the base directory
load_dotenv(BASE_DIR / ".env")

# API Keys and Credentials
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Official LinkedIn REST API Credentials (Zero Ban Risk)
LINKEDIN_CLIENT_ID: str = os.getenv("LINKEDIN_CLIENT_ID", "").strip()
LINKEDIN_CLIENT_SECRET: str = os.getenv("LINKEDIN_CLIENT_SECRET", "").strip()
LINKEDIN_ACCESS_TOKEN: str = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
LINKEDIN_PERSON_URN: str = os.getenv("LINKEDIN_PERSON_URN", "").strip()

# Gemini & Nano Banana Image Model Configuration
TEXT_MODEL: str = os.getenv("TEXT_MODEL", "gemini-3.5-flash").strip()
IMAGE_MODEL: str = os.getenv("IMAGE_MODEL", "nano-banana-pro-preview").strip()
FLOW_PROJECT_ID: str = os.getenv("FLOW_PROJECT_ID", "84dc3114-9c59-4ac5-b676-0e5050c74a74").strip()

# Web Dashboard & Cloud Deployment (Railway)
WEB_HOST: str = os.getenv("HOST", "0.0.0.0")
WEB_PORT: int = int(os.getenv("PORT", "8000"))
APP_SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "linkedin-ai-growth-secure-secret-key")

# Strategic Organic Growth Schedule Times (HH:MM format, 24h)
DEFAULT_SCHEDULE_TIMES: List[str] = ["08:45", "13:15", "18:45"]
_times_raw = os.getenv("SCHEDULE_TIMES", "08:45,13:15,18:45")
SCHEDULE_TIMES: List[str] = [t.strip() for t in _times_raw.split(",") if ":" in t.strip()] or DEFAULT_SCHEDULE_TIMES

# Database & File Storage
DB_PATH: Path = BASE_DIR / os.getenv("DB_PATH", "news_history.db").strip()
IMAGES_DIR: Path = BASE_DIR / os.getenv("IMAGES_DIR", "output_images").strip()
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
VIDEOS_DIR: Path = BASE_DIR / os.getenv("VIDEOS_DIR", "output_videos").strip()
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

# Curated High-Quality Saudi, GCC & Global Tech Feeds (FinTech, PropTech, AI)
AI_RSS_FEEDS: List[dict] = [
    {
        "name": "Wamda Startups & VC",
        "url": "https://www.wamda.com/feed",
        "category": "Startups & Funding",
    },
    {
        "name": "Fintech News Middle East",
        "url": "https://fintechnews.ae/feed/",
        "category": "Fintech & Banking",
    },
    {
        "name": "Saudi & GCC FinTech Pulse",
        "url": "https://news.google.com/rss/search?q=(Saudi+OR+GCC+OR+UAE)+(Fintech+OR+Proptech)&hl=en-US&gl=US&ceid=US:en",
        "category": "Fintech & Proptech",
    },
    {
        "name": "Saudi PropTech & Real Estate Tech",
        "url": "https://news.google.com/rss/search?q=(Saudi+Arabia+Proptech)+OR+(Saudi+Real+Estate+tech)+OR+(ROSHN+technology)&hl=en-US&gl=US&ceid=US:en",
        "category": "Proptech",
    },
    {
        "name": "SAMA & Saudi Banking Innovations",
        "url": "https://news.google.com/rss/search?q=(Saudi+Fintech)+OR+(SAMA+Open+Banking)+OR+(Saudi+payments)&hl=en-US&gl=US&ceid=US:en",
        "category": "Fintech Regulations",
    },
    {
        "name": "TechCrunch AI & Enterprise",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "category": "AI Technology",
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "category": "AI Technology",
    },
]

# Backward compatibility alias
TECH_RSS_FEEDS = AI_RSS_FEEDS

# Scheduler execution hours (24-hour format)
_schedule_raw = os.getenv("SCHEDULE_HOURS", "9,18")
SCHEDULE_HOURS: List[int] = [int(h.strip()) for h in _schedule_raw.split(",") if h.strip().isdigit()]


def validate_config(require_keys: bool = True) -> None:
    """
    Validates required environment configurations.
    Raises ValueError if critical variables are missing.
    """
    if not require_keys:
        return

    missing = []
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")

    if missing:
        raise ValueError(
            f"Missing required environment variable(s): {', '.join(missing)}.\n"
            "Please create a .env file from .env.example and populate the values."
        )
