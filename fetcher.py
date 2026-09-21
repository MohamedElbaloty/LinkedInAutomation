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

# Keywords for detecting FinTech & PropTech breakthroughs
FINTECH_PROPTECH_KEYWORDS = [
    "fintech",
    "proptech",
    "open banking",
    "digital banking",
    "digital bank",
    "payments",
    "payment gateway",
    "digital wallet",
    "bnpl",
    "buy now pay later",
    "sama",
    "saudi central bank",
    "real estate",
    "real estate tech",
    "property technology",
    "smart building",
    "smart cities",
    "tokenization",
    "fractional ownership",
    "digital escrow",
    "credit scoring",
    "automated valuation",
    "avm",
    "seed round",
    "funding round",
    "series a",
    "series b",
    "pre-seed",
    "venture capital",
    "fintech saudi",
]

# Priority geographic keywords for Saudi Arabia and the GCC
GCC_PRIORITY_KEYWORDS = [
    "saudi",
    "saudi arabia",
    "riyadh",
    "jeddah",
    "gcc",
    "gulf",
    "uae",
    "dubai",
    "abu dhabi",
    "qatar",
    "kuwait",
    "bahrain",
    "oman",
    "roshn",
    "neom",
    "red sea",
    "cityscape",
    "vision 2030",
]

# Keywords that indicate non-technical penny-stock clickbait
NEGATIVE_KEYWORDS = [
    "motley fool",
    "penny stock",
    "penny stocks",
    "day trading",
    "strong buy",
    "price target",
    "dividend yield",
    "berkshire",
    "10x stock",
    "top stock to buy",
]

# Technical, algorithmic, and financial architecture keywords
TECHNICAL_KEYWORDS = [
    "architecture",
    "api",
    "apis",
    "infrastructure",
    "pipeline",
    "transformer",
    "reasoning",
    "algorithm",
    "tensors",
    "vectors",
    "moe",
    "mixture of experts",
    "diffusion",
    "kv cache",
    "quantization",
    "tokens",
    "mechanics",
    "latency",
    "throughput",
    "protocols",
    "consensus",
    "security",
]
DEEP_MANIM_KEYWORDS = TECHNICAL_KEYWORDS


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
    Scores the relevance of an article across Saudi/GCC FinTech, PropTech, and AI topics.
    Gives priority weighting to Saudi Arabia and GCC market developments, open banking,
    proptech platforms, and technical architecture while eliminating spammy penny-stock noise.
    """
    title_lower = title.lower()
    summary_lower = summary.lower()
    full_text = f"{title_lower} {summary_lower}"

    # 1. Filter out spammy penny-stock clickbait
    for neg in NEGATIVE_KEYWORDS:
        pattern = r"\b" + re.escape(neg) + r"\b"
        if re.search(pattern, title_lower):
            return -100

    score = 0
    has_gcc = False
    has_fin_prop = False
    has_ai = False

    # 2. Check GCC & Saudi priority
    for kw in GCC_PRIORITY_KEYWORDS:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, title_lower):
            score += 10
            has_gcc = True
        elif re.search(pattern, summary_lower):
            score += 5
            has_gcc = True

    # 3. Check FinTech & PropTech domain
    for kw in FINTECH_PROPTECH_KEYWORDS:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, title_lower):
            score += 8
            has_fin_prop = True
        elif re.search(pattern, summary_lower):
            score += 4
            has_fin_prop = True

    # 4. Check AI topics
    for kw in AI_KEYWORDS:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, title_lower):
            score += 5
            has_ai = True
        elif re.search(pattern, summary_lower):
            score += 2
            has_ai = True

    # 5. Technical architecture keywords
    for tech in TECHNICAL_KEYWORDS:
        pattern = r"\b" + re.escape(tech) + r"\b"
        if re.search(pattern, title_lower):
            score += 6
        elif re.search(pattern, summary_lower):
            score += 3

    # Synergy bonus: If Saudi/GCC intersects with FinTech, PropTech, or AI -> highest priority
    if has_gcc and (has_fin_prop or has_ai):
        score += 20

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


def enrich_article_content(article: Article) -> Article:
    """
    Fetches the full web page text if the RSS summary is brief (< 500 chars)
    to give Gemini deep technical context for comprehensive LinkedIn breakdowns.
    """
    if not article.link:
        return article

    if len(article.summary) >= 600:
        return article

    try:
        import requests
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        resp = requests.get(article.link, headers=headers, timeout=8)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
                tag.decompose()

            main_container = (
                soup.find("article")
                or soup.find("main")
                or soup.find("div", class_=re.compile(r"article|content|post-body|entry-content", re.I))
                or soup
            )
            paragraphs = main_container.find_all("p")
            text_chunks = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 35]
            if text_chunks:
                full_body = " ".join(text_chunks[:12])
                if len(full_body) > len(article.summary):
                    article.summary = full_body[:3500]
                    logger.info("Enriched article content for '%s' (%d characters extracted)", article.title, len(article.summary))
    except Exception as e:
        logger.debug("Could not enrich article content for %s: %s", article.link, e)

    return article


def get_latest_unread_article(feeds: Optional[List[dict]] = None, db_path: Path = DB_PATH) -> Optional[Article]:
    """
    Fetches the highest-relevance unread article and enriches it with full body text.
    Does NOT mark it as posted yet (orchestrator should mark it upon successful delivery).
    """
    unread = fetch_unread_articles(feeds=feeds, db_path=db_path)
    if not unread:
        logger.info("No new unread AI articles found across all feeds.")
        return None

    selected = unread[0]
    # Enrich with full web page context
    selected = enrich_article_content(selected)
    logger.info(
        "Selected article: '%s' from %s (Score: %d, Summary len: %d)",
        selected.title,
        selected.source,
        selected.relevance_score,
        len(selected.summary),
    )
    return selected

