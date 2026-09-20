"""
Fetcher module for ai_news_agent.
Handles RSS feed parsing, HTML sanitization, relevance scoring,
and SQLite persistence to prevent posting duplicate news.
"""

import hashlib
import logging
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from bs4 import BeautifulSoup
import feedparser

from config import AI_RSS_FEEDS, DB_PATH

logger = logging.getLogger(__name__)

# Keywords for detecting and scoring high-impact AI topics
AI_KEYWORDS = [
    "artificial intelligence",
    "ai",
    "llm",
    "large language model",
    "agentic",
    "autonomous agent",
    "ai agent",
    "machine learning",
    "deep learning",
    "neural network",
    "openai",
    "chatgpt",
    "gpt-4",
    "gpt-5",
    "anthropic",
    "claude",
    "google gemini",
    "deepmind",
    "meta ai",
    "llama",
    "mistral",
    "nvidia",
    "inference",
    "fine-tuning",
    "transformer",
    "diffusion",
    "rag",
    "benchmark",
    "reasoning model",
    "open-source ai",
]

# Keywords that indicate non-technical stock market noise / financial clickbait
NEGATIVE_KEYWORDS = [
    "stock",
    "stocks",
    "shares",
    "shareholder",
    "investor",
    "investing",
    "motley fool",
    "dividend",
    "market cap",
    "earnings",
    "wall street",
    "nasdaq",
    "buy now",
    "price target",
    "portfolio",
    "berkshire",
    "10x",
]

# Technical & algorithmic keywords that indicate suitability for Deep Manim breakdown
DEEP_MANIM_KEYWORDS = [
    "architecture",
    "transformer",
    "reasoning",
    "weights",
    "algorithm",
    "tensors",
    "vectors",
    "calibration",
    "moe",
    "mixture of experts",
    "diffusion",
    "rlhf",
    "attention",
    "latent",
    "kv cache",
    "quantization",
    "state space",
    "mamba",
    "loss function",
    "forward pass",
    "tokens",
    "mechanics",
]


@dataclass
class Article:
    """Represents a sanitized news article."""
    id: str
    title: str
    link: str
    summary: str
    published_at: str
    source: str
    relevance_score: int = 0


def init_db(db_path: Path = DB_PATH) -> None:
    """Initializes the SQLite database table for tracking posted news."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS posted_news (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                published_at TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def is_already_posted(article_id: str, db_path: Path = DB_PATH) -> bool:
    """Checks whether an article ID has already been recorded in SQLite."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM posted_news WHERE id = ?", (article_id,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def mark_as_posted(article_id: str, title: str, published_at: str, db_path: Path = DB_PATH) -> None:
    """Marks an article as posted in the SQLite database to avoid duplicates."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO posted_news (id, title, published_at)
            VALUES (?, ?, ?)
            """,
            (article_id, title, published_at),
        )
        conn.commit()
    finally:
        conn.close()
    logger.info("Marked article '%s' (%s) as posted in SQLite.", title, article_id)


def clean_html(raw_html: str) -> str:
    """Strips HTML tags and normalizes whitespace using BeautifulSoup."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.extract()
    text = soup.get_text(separator=" ", strip=True)
    # Filter common RSS boilerplates
    boilerplates = [
        "The post appeared first on",
        "appeared first on TechCrunch",
        "appeared first on VentureBeat",
    ]
    for bp in boilerplates:
        if bp in text:
            text = text.split(bp)[0].strip()
    return " ".join(text.split())


def calculate_relevance(title: str, summary: str) -> int:
    """
    Scores the relevance of an article to AI topics.
    Excludes stock/financial clickbait and strongly boosts technical topics
    suitable for Deep Manim mathematical/architectural explanations.
    """
    title_lower = title.lower()
    summary_lower = summary.lower()
    full_text = f"{title_lower} {summary_lower}"

    # 1. Filter out financial / stock market noise
    for neg in NEGATIVE_KEYWORDS:
        pattern = r"\b" + re.escape(neg) + r"\b"
        if re.search(pattern, title_lower):
            return -100  # Immediately disqualify stock picks

    # 2. Score standard AI keywords
    score = 0
    for kw in AI_KEYWORDS:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, title_lower):
            score += 3
        elif re.search(pattern, summary_lower):
            score += 1

    # 3. Heavily boost Deep Manim technical & architectural terms
    for tech in DEEP_MANIM_KEYWORDS:
        pattern = r"\b" + re.escape(tech) + r"\b"
        if re.search(pattern, title_lower):
            score += 10
        elif re.search(pattern, summary_lower):
            score += 4

    return score


def _parse_published_timestamp(entry: dict) -> float:
    """Extracts a Unix timestamp from entry date fields for chronological sorting."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return time.mktime(entry.published_parsed)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return time.mktime(entry.updated_parsed)
    return 0.0


def fetch_unread_articles(feeds: Optional[List[dict]] = None, db_path: Path = DB_PATH) -> List[Article]:
    """
    Scrapes all configured feeds, cleans content, filters out already posted items,
    and returns a list of unread Article objects sorted by relevance and recency.
    """
    init_db(db_path)
    active_feeds = feeds or AI_RSS_FEEDS
    candidates: List[Article] = []

    for feed_info in active_feeds:
        feed_name = feed_info.get("name", "Unknown Feed")
        feed_url = feed_info.get("url", "")
        logger.info("Parsing feed: %s (%s)", feed_name, feed_url)

        try:
            parsed = feedparser.parse(feed_url)
            if parsed.bozo and not parsed.entries:
                logger.warning("Feedparser warning for %s: %s", feed_name, parsed.bozo_exception)
                continue

            for entry in parsed.entries:
                title = clean_html(getattr(entry, "title", "")).strip()
                if not title:
                    continue

                link = getattr(entry, "link", "").strip()

                # Determine unique identifier: link or entry ID or hash of title
                raw_id = getattr(entry, "id", None) or link or title
                article_id = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()

                if is_already_posted(article_id, db_path):
                    continue

                # Clean summary / description
                raw_summary = (
                    getattr(entry, "summary", "")
                    or getattr(entry, "description", "")
                    or ""
                )
                summary = clean_html(raw_summary).strip()

                # Published date string
                pub_date = (
                    getattr(entry, "published", "")
                    or getattr(entry, "updated", "")
                    or datetime.now(timezone.utc).isoformat()
                )

                relevance = calculate_relevance(title, summary)
                # Filter out articles with zero AI relevance
                if relevance <= 0:
                    continue

                pub_timestamp = _parse_published_timestamp(entry)

                article = Article(
                    id=article_id,
                    title=title,
                    link=link,
                    summary=summary,
                    published_at=pub_date,
                    source=feed_name,
                    relevance_score=(relevance * 1000) + (int((pub_timestamp - 1_700_000_000) / 3600) if pub_timestamp > 0 else 0),
                )
                candidates.append(article)

        except Exception as e:
            logger.error("Failed to parse feed %s: %s", feed_name, str(e), exc_info=True)

    # Sort descending by relevance score (which factors in recency)
    candidates.sort(key=lambda a: a.relevance_score, reverse=True)
    return candidates


def get_latest_unread_article(feeds: Optional[List[dict]] = None, db_path: Path = DB_PATH) -> Optional[Article]:
    """
    Fetches the highest-relevance unread article.
    Does NOT mark it as posted yet (orchestrator should mark it upon successful delivery).
    """
    unread = fetch_unread_articles(feeds=feeds, db_path=db_path)
    if not unread:
        logger.info("No new unread AI articles found across all feeds.")
        return None

    selected = unread[0]
    logger.info(
        "Selected article: '%s' from %s (Score: %d)",
        selected.title,
        selected.source,
        selected.relevance_score,
    )
    return selected
