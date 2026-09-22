"""
LinkedIn Authentic Sector Commenting Engine (Anti-AI Persona).
Drafts high-caliber, human-sounding CTO comments on FinTech, PropTech, and AI posts
across Saudi Arabia & GCC to organically elevate profile visibility.
Authored strictly as Mohamed Elbaloty, CTO @ Sahalat.
"""

from datetime import datetime
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional
import urllib.parse
import requests

from google import genai
from google.genai import types

from config import BASE_DIR, GEMINI_API_KEY, TEXT_MODEL
from fetcher import fetch_unread_articles
from linkedin_api import extract_urn_from_linkedin_url, publish_comment_to_linkedin

logger = logging.getLogger(__name__)

COMMENT_CONFIG_FILE = BASE_DIR / "comment_settings.json"


def load_comment_settings() -> Dict[str, any]:
    """Loads commenting configuration from disk or defaults."""
    if COMMENT_CONFIG_FILE.exists():
        try:
            with open(COMMENT_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Error reading %s: %s", COMMENT_CONFIG_FILE, e)

    default_settings = {
        "auto_comment_enabled": False,  # Disabled until user confirms test
        "max_daily_comments": 4,
        "comments_today": 0,
        "last_comment_date": datetime.now().strftime("%Y-%m-%d"),
        "last_comment_time": None,
        "target_sectors": ["FinTech", "PropTech", "AI Infrastructure", "SAMA Regulations"],
        "history": []
    }
    save_comment_settings(default_settings)
    return default_settings


def save_comment_settings(settings: Dict[str, any]) -> None:
    """Persists commenting settings to disk."""
    try:
        with open(COMMENT_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("Failed to save comment settings: %s", e)


# Curated high-relevance Saudi Arabia & GCC FinTech & PropTech feeds (Published Today / Past 24h)
SAUDI_GCC_TODAY_FEEDS: List[dict] = [
    {
        "name": "Saudi FinTech & SAMA (Today)",
        "url": "https://news.google.com/rss/search?q=(Saudi+Fintech+OR+SAMA+Open+Banking+OR+Saudi+payments)+when:24h&hl=en-US&gl=US&ceid=US:en",
        "category": "FinTech Saudi",
    },
    {
        "name": "Saudi PropTech & Real Estate (Today)",
        "url": "https://news.google.com/rss/search?q=(Saudi+Proptech+OR+Saudi+Real+Estate+tech+OR+ROSHN)+when:24h&hl=en-US&gl=US&ceid=US:en",
        "category": "PropTech Saudi",
    },
    {
        "name": "GCC FinTech & PropTech (Today)",
        "url": "https://news.google.com/rss/search?q=(GCC+OR+UAE+OR+Saudi)+(Fintech+OR+Proptech)+when:24h&hl=en-US&gl=US&ceid=US:en",
        "category": "FinTech & PropTech GCC",
    },
    {
        "name": "Fintech News Middle East",
        "url": "https://fintechnews.ae/feed/",
        "category": "FinTech ME",
    },
]


def clean_anti_ai_comment(text: str) -> str:
    """
    Cleanses and ensures the comment strictly avoids AI cliches, greetings, pleasantries, and bot-like intros.
    """
    cleaned = text.strip()
    # Remove enclosing quotes if any
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()

    # Disallowed greetings and compliments
    banned_prefixes = [
        r"^(great post|fascinating post|insightful share|thanks for sharing|100% agree|spot on|well said|love this)[,!.\s]*",
        r"^(as a cto|as an engineering leader|in my opinion|in today's world|in today's fast-paced world)[,!.\s]*",
        r"^(this is (a |such a )?(game[- ]changer|revolutionary|testament|milestone))[,!.\s]*",
        r"^(here is my take|my two cents|couldn't agree more|totally agree)[,!.\s]*",
        r"^(مقال|بوست|طرح|منشور)\s+(رائع|ممتاز|قيم|جميل|مهم)[،,.\s]*",
        r"^(أحسنت|شكراً لك|شكرا جزيلا|سلمت يداك|بارك الله فيك)[،,.\s]*",
        r"^(اتفق معك تماما|أتفق معك تماماً)[،,.\s]*",
        r"^(تلخيصاً|باختصار|في رأيي|في الحقيقة)[،,.\s]*",
    ]
    for pattern in banned_prefixes:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

    # Strip any meta labels like "Comment:" or "Executive Comment:"
    cleaned = re.sub(r"^(comment|executive comment|cto insight|perspective):\s*", "", cleaned, flags=re.IGNORECASE).strip()

    # Capitalize first character
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]

    return cleaned


class CommentGenerator:
    """Generates authentic, pragmatic CTO comments in fluent, executive English using Gemini."""

    def __init__(self, api_key: Optional[str] = None):
        key = (api_key or GEMINI_API_KEY).strip()
        if not key:
            raise ValueError("GEMINI_API_KEY is missing for comment generator.")
        self.client = genai.Client(api_key=key)
        self.text_model = TEXT_MODEL

    def generate_comment(
        self,
        post_content: str,
        post_title: str = "",
        post_author: str = "",
        sector: str = "FinTech & PropTech (Saudi Arabia & GCC)",
    ) -> str:
        """
        Drafts a high-impact, authentic executive CTO comment strictly in professional English.
        Deeply comprehends the target post and delivers a genuine engineering / architectural perspective.
        """
        system_instruction = (
            "You are Mohamed Elbaloty, CTO @ Sahalat. You are an experienced engineering executive, enterprise software architect, "
            "and technical authority in FinTech (التقنية المالية) and PropTech (التقنية العقارية) across Saudi Arabia and the GCC.\n\n"
            "YOUR OBJECTIVE:\n"
            "Write a sharp, authentic, high-impact executive comment on a LinkedIn post in your industry. "
            "The comment must stand out to founders, CTOs, engineers, and VCs as pure, genuine engineering & product leadership. "
            "It must NEVER look or sound like it was generated by AI or an automated bot.\n\n"
            "STRICT RULES (CRITICAL):\n"
            "1. LANGUAGE: MUST BE WRITTEN IN NATURAL, FLUENT, EXECUTIVE ENGLISH. Even if the target post is written in Arabic, deeply comprehend the Arabic content, but author your response strictly in high-caliber English.\n"
            "2. DEEP COMPREHENSION: Address the exact operational, architectural, or regulatory reality described in the post (e.g. SAMA Open Banking API latency, REGA digital land registry integration, automated valuation models (AVM) accuracy, SARIE instant settlement reconciliation, payment orchestration, escrow automation, or tenant/buyer KYC friction).\n"
            "3. NO BOT PLEASANTRIES OR GREETINGS: Never start with or include 'Great post', 'Fascinating share', 'Thanks for sharing', '100% agree', 'Well said', or 'Spot on'. Never say 'As a CTO...'. Jump straight into the technical or economic core.\n"
            "4. NO SUMMARIES: Do not recap what the post just stated. Contribute a genuine practitioner's trade-off, architectural reality, or market dynamic.\n"
            "5. NO AI BUZZWORDS: Never use words like 'game-changer', 'delve', 'testament', 'revolutionize', 'unleash', 'cornerstone', 'in today's digital era', 'tapestry', 'crucial role'.\n"
            "6. CONCISE & PUNCHY: Exactly 2 to 4 sentences (between 35 and 75 words). Dense, authoritative, conversational executive style.\n"
            "7. RAW OUTPUT ONLY: Output ONLY the exact comment text. No quotation marks, no markdown headers, no preamble like 'Here is a comment:'."
        )

        user_prompt = (
            f"Target Post Topic / Title: {post_title}\n"
            f"Author / Organization: {post_author or 'Industry Leader'}\n"
            f"Industry Focus: {sector} (Saudi Arabia & GCC - Published Today)\n"
            f"Post Content:\n{post_content}\n\n"
            "Read and comprehend the full content above. Write your sharp executive CTO comment in English now (no greeting, raw comment only):"
        )

        candidate_models = [
            "gemini-3.6-flash",
            self.text_model,
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3-flash-preview",
        ]
        candidate_models = list(dict.fromkeys(candidate_models))

        for model_name in candidate_models:
            try:
                resp = self.client.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.5,
                        max_output_tokens=1024,
                    ),
                )
                raw_text = resp.text.strip()
                if raw_text:
                    return clean_anti_ai_comment(raw_text)
            except Exception as e:
                logger.warning("Comment generation failed on %s: %s", model_name, e)
                continue

        # Pragmatic English executive fallback if AI call fails
        return (
            "The real engineering bottleneck in these regional integrations isn't the interface layer—it's backend data resilience "
            "and ensuring payment gateways and Open Banking APIs maintain sub-second idempotency during high-volume transaction spikes."
        )


def extract_smart_linkedin_keywords(title: str, text: str = "") -> str:
    """
    Extracts high-signal, focused entity and sector keywords (1-3 words max)
    so that LinkedIn search reliably returns active, matching discussions
    without the zero-results bug caused by long multi-word phrases.
    """
    KNOWN_ENTITIES = [
        ("ROSHN", ["roshn", "روشن"]),
        ("PhonePe", ["phonepe"]),
        ("SAMA", ["sama", "سما", "البنك المركزي السعودي", "البنك المركزي"]),
        ("REGA", ["rega", "الهيئة العامة للعقار", "عقارات السعودية"]),
        ("STC Pay", ["stc pay", "stcpay"]),
        ("Urpay", ["urpay"]),
        ("Tamara", ["tamara", "تمارا"]),
        ("Tabby", ["tabby", "تابي"]),
        ("Open Banking", ["open banking", "المصرفية المفتوحة"]),
        ("PropTech", ["proptech", "بروبتيك", "التقنية العقارية"]),
        ("FinTech", ["fintech", "فنتك", "التقنية المالية"]),
        ("SARIE", ["sarie", "سريع"]),
        ("Wafi", ["wafi", "وافي"]),
        ("Aqar", ["aqar", "عقار"]),
        ("Seamless", ["seamless"]),
        ("Apple Pay", ["apple pay"]),
        ("Mada", ["mada", "مدى"]),
    ]

    combined = f"{title} {text}".lower()
    matched = []
    for display_name, patterns in KNOWN_ENTITIES:
        for p in patterns:
            if re.search(r"\b" + re.escape(p) + r"\b", combined, re.IGNORECASE) or (p in combined and len(p) >= 4):
                if display_name not in matched:
                    matched.append(display_name)
                break

    if matched:
        if len(matched) == 1:
            ent = matched[0]
            if ent in ["ROSHN", "SAMA", "REGA", "SARIE", "PhonePe"]:
                return ent
            return f"{ent} Saudi"
        else:
            return " ".join(matched[:2])

    # If no known entity, strip common stop words and pick 2 core words
    clean = re.sub(r"[-|–—:,'\"].*$", "", title).strip()
    stopwords = {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with",
        "is", "are", "was", "were", "will", "be", "receives", "approval", "expands",
        "giant", "launches", "announces", "plans", "new", "first", "group", "company",
        "market", "set", "report", "growth", "overseas", "closer", "moves",
        "في", "من", "على", "إلى", "عن", "مع", "هذا", "هذه", "تم", "تعلن", "يطلق"
    }
    words = [w for w in clean.split() if w.lower() not in stopwords]
    return " ".join(words[:2]) if words else "Saudi Fintech Proptech"


def build_linkedin_search_urls(keywords: str) -> Dict[str, str]:
    """
    Constructs reliable LinkedIn content search URLs:
    1. search_url: Sorted by latest (date_posted), guaranteed to return posts without zero-results failure.
    2. today_search_url: Strictly filtered to past 24 hours.
    """
    clean_kw = keywords.strip() or "Saudi Fintech"
    encoded = urllib.parse.quote_plus(clean_kw)
    # URL 1: Newest posts chronologically (Today's posts at the top, guaranteed results)
    search_url = f"https://www.linkedin.com/search/results/content/?keywords={encoded}&sortBy=%22date_posted%22"
    # URL 2: Past 24 hours strict filter
    today_search_url = f"https://www.linkedin.com/search/results/content/?keywords={encoded}&datePosted=%22past-24h%22&sortBy=%22date_posted%22"
    return {
        "search_url": search_url,
        "today_search_url": today_search_url,
        "keyword": clean_kw,
    }


def get_today_trending_topics(limit: int = 6) -> List[Dict[str, any]]:
    """
    Fetches the top unread/fresh articles from regional Saudi & GCC FinTech & PropTech feeds (today),
    extracts smart LinkedIn search URLs, and returns structured topic items for the dashboard.
    """
    articles = fetch_unread_articles(feeds=SAUDI_GCC_TODAY_FEEDS)
    if not articles:
        articles = fetch_unread_articles()

    topics = []
    seen_titles = set()
    seen_keywords = set()
    for art in articles:
        clean_title = re.sub(r"[-|–—].*$", "", art.title).strip()
        if clean_title.lower() in seen_titles:
            continue
        seen_titles.add(clean_title.lower())

        summary = (art.summary or art.title).replace("\n", " ").strip()
        if len(summary) > 280:
            summary = summary[:277] + "..."

        smart_kw = extract_smart_linkedin_keywords(art.title, summary)
        kw_key = smart_kw.lower()
        if kw_key in seen_keywords and len(topics) < limit:
            continue
        seen_keywords.add(kw_key)

        urls = build_linkedin_search_urls(smart_kw)

        topics.append({
            "title": art.title,
            "clean_title": clean_title,
            "source": art.source or "Saudi & GCC Tech",
            "source_url": art.link,
            "published_at": getattr(art, "published_at", None),
            "search_keyword": smart_kw,
            "linkedin_search_url": urls["search_url"],
            "linkedin_search_today_url": urls["today_search_url"],
            "summary": summary,
            "sector": "FinTech & PropTech Saudi & GCC (Today)",
            "post_text": f"{art.title}\n\n{summary}",
            "is_feed_article": True,
        })
        if len(topics) >= limit:
            break

    # If we need more topics to fill the limit, do a second pass allowing same keyword
    if len(topics) < limit:
        for art in articles:
            clean_title = re.sub(r"[-|–—].*$", "", art.title).strip()
            if clean_title.lower() in seen_titles:
                continue
            seen_titles.add(clean_title.lower())
            summary = (art.summary or art.title).replace("\n", " ").strip()
            smart_kw = extract_smart_linkedin_keywords(art.title, summary)
            urls = build_linkedin_search_urls(smart_kw)
            topics.append({
                "title": art.title,
                "clean_title": clean_title,
                "source": art.source or "Saudi & GCC Tech",
                "source_url": art.link,
                "published_at": getattr(art, "published_at", None),
                "search_keyword": smart_kw,
                "linkedin_search_url": urls["search_url"],
                "linkedin_search_today_url": urls["today_search_url"],
                "summary": summary,
                "sector": "FinTech & PropTech Saudi & GCC (Today)",
                "post_text": f"{art.title}\n\n{summary}",
                "is_feed_article": True,
            })
            if len(topics) >= limit:
                break

    return topics


def discover_trending_sector_post() -> Dict[str, any]:
    """
    Finds a trending, highly relevant FinTech or PropTech post or news item published TODAY (past 24h)
    in Saudi Arabia or the GCC.
    Returns metadata including title, source link, direct LinkedIn search links, and content snippet.
    """
    topics = get_today_trending_topics(limit=1)
    if topics:
        return topics[0]

    # Curated regional breaking discussion for today as rich fallback
    default_title = "Saudi FinTech & PropTech: SAMA Open Banking & Instant Real Estate Settlement"
    smart_kw = "Saudi Fintech Proptech"
    urls = build_linkedin_search_urls(smart_kw)
    return {
        "title": default_title,
        "clean_title": "SAMA Open Banking & Instant Real Estate Settlement Expansion",
        "source": "Fintech Saudi & PropTech Pulse",
        "source_url": "https://fintechsaudi.com",
        "search_keyword": smart_kw,
        "linkedin_search_url": urls["search_url"],
        "linkedin_search_today_url": urls["today_search_url"],
        "summary": "Recent developments across Saudi Arabia's Open Banking frameworks and automated real estate platforms enabling instant escrow settlement and verified deed integration.",
        "sector": "FinTech & PropTech Saudi Arabia (Today)",
        "post_text": "The Saudi Central Bank (SAMA) and real estate tech platforms accelerate API integration for automated escrow settlement and verified digital title deed transactions across the Kingdom.",
        "is_feed_article": False,
    }


def draft_comment_for_target(
    target_url_or_urn: str = "",
    target_text: str = "",
    target_title: str = "",
) -> Dict[str, any]:
    """
    High-level orchestrator that:
    1. Resolves target post:
       - If user entered a real LinkedIn post URL -> extracts URN, points directly to that post.
       - If user entered raw post text -> drafts directly on the user's text and builds targeted search links.
       - If auto-discovered news topic -> provides direct LinkedIn discussion search link + news source link.
    2. Drafts an anti-AI executive comment from Mohamed Elbaloty (CTO @ Sahalat).
    3. Normalizes target URN for LinkedIn API publishing.
    """
    from linkedin_api import get_recent_published_linkedin_posts

    resolved_url = target_url_or_urn.strip()
    resolved_text = target_text.strip()
    resolved_title = target_title.strip()
    source_name = ""
    source_url = None
    linkedin_url = ""
    linkedin_search_url = ""
    linkedin_search_today_url = ""
    search_keyword = ""
    is_linkedin_post = False
    target_urn = ""

    # Check if the provided URL is a real LinkedIn URL or URN
    is_explicit_linkedin = (
        "linkedin.com" in resolved_url
        or resolved_url.startswith("urn:li:")
        or (resolved_url.isdigit() and len(resolved_url) >= 15)
    )
    is_http_url = resolved_url.startswith("http://") or resolved_url.startswith("https://")

    # If user passed text into the URL field (not a URL)
    if resolved_url and not is_explicit_linkedin and not is_http_url:
        if not resolved_text:
            resolved_text = resolved_url
        resolved_url = ""

    if is_explicit_linkedin:
        is_linkedin_post = True
        target_urn = extract_urn_from_linkedin_url(resolved_url)
        linkedin_url = resolved_url if resolved_url.startswith("http") else (
            f"https://www.linkedin.com/feed/update/{target_urn}" if target_urn else "https://www.linkedin.com/feed/"
        )
        if not resolved_text:
            slug_match = re.search(r"linkedin\.com/posts/([^/?]+)", resolved_url)
            if slug_match:
                slug = slug_match.group(1).replace("-", " ")
                resolved_title = f"منشور تقني: {slug[:60]}"
                resolved_text = f"نقاش قطاعي حول: {slug}"
            else:
                resolved_title = f"منشور على LinkedIn ({target_urn or 'تفاعل مجتمعي'})"
                resolved_text = "نقاش تنفيذي متخصص في قطاع التقنية المالية والتحول الرقمي والبنية التحتية السحابية."
        source_name = "LinkedIn Post"
        search_keyword = extract_smart_linkedin_keywords(resolved_title, resolved_text)
        urls = build_linkedin_search_urls(search_keyword)
        linkedin_search_url = urls["search_url"]
        linkedin_search_today_url = urls["today_search_url"]
    elif resolved_url and is_http_url:
        # User entered an external URL (e.g. external news article)
        is_linkedin_post = False
        source_url = resolved_url
        query_text = resolved_title or "FinTech PropTech Saudi Arabia"
        search_keyword = extract_smart_linkedin_keywords(resolved_title, resolved_text)
        urls = build_linkedin_search_urls(search_keyword)
        linkedin_url = urls["search_url"]
        linkedin_search_url = urls["search_url"]
        linkedin_search_today_url = urls["today_search_url"]
        source_name = "External Tech News"
    elif resolved_text:
        # User provided direct post content/text
        is_linkedin_post = False
        if not resolved_title:
            resolved_title = resolved_text.split("\n")[0][:70] + ("..." if len(resolved_text) > 70 else "")
        search_keyword = extract_smart_linkedin_keywords(resolved_title, resolved_text)
        urls = build_linkedin_search_urls(search_keyword)
        linkedin_url = urls["search_url"]
        linkedin_search_url = urls["search_url"]
        linkedin_search_today_url = urls["today_search_url"]
        source_name = "User Shared Post"
    else:
        # No URL or text provided: discover trending sector topic for today
        trending = discover_trending_sector_post()
        resolved_title = trending["title"]
        resolved_text = trending["post_text"]
        source_name = trending["source"]
        source_url = trending.get("source_url")
        search_keyword = trending.get("search_keyword", "Saudi Fintech Proptech")
        linkedin_url = trending.get("linkedin_search_url", "https://www.linkedin.com/search/results/content/")
        linkedin_search_url = trending.get("linkedin_search_url", linkedin_url)
        linkedin_search_today_url = trending.get("linkedin_search_today_url", linkedin_url)
        is_linkedin_post = False

    generator = CommentGenerator()
    comment = generator.generate_comment(
        post_content=resolved_text or resolved_title,
        post_title=resolved_title,
        post_author=source_name,
    )

    recent_user_posts = get_recent_published_linkedin_posts(limit=3)

    return {
        "success": True,
        "is_linkedin_post": is_linkedin_post,
        "can_publish": is_linkedin_post and bool(target_urn),
        "post_title": resolved_title,
        "post_urn": target_urn if is_linkedin_post else None,
        "post_url": linkedin_url,
        "linkedin_url": linkedin_url,
        "linkedin_search_url": linkedin_search_url,
        "linkedin_search_today_url": linkedin_search_today_url,
        "search_keyword": search_keyword,
        "source_url": source_url,
        "post_content_snippet": resolved_text[:240] + ("..." if len(resolved_text) > 240 else ""),
        "comment_text": comment,
        "author_persona": "Mohamed Elbaloty, CTO @ Sahalat",
        "recent_user_posts": recent_user_posts,
    }


def execute_linkedin_comment(
    target_urn_or_url: str,
    comment_text: str,
    post_title: str = "",
) -> Dict[str, any]:
    """
    Executes a live comment publish on LinkedIn and records the action in history.
    """
    target_urn = extract_urn_from_linkedin_url(target_urn_or_url)
    if not target_urn or not target_urn.startswith("urn:li:"):
        return {
            "success": False,
            "error": (
                "تعذر تحديد معرف المنشور على LinkedIn (URN). "
                "للنشر الفعلي على LinkedIn، يجب استخدام رابط منشور كامل يبدأ بـ https://www.linkedin.com/posts/... "
                "أو تجربة التعليق على آخر منشور منشور في حسابك بنقرة واحدة."
            ),
        }

    res = publish_comment_to_linkedin(target_urn_or_url=target_urn, comment_text=comment_text)

    # Record in history
    settings = load_comment_settings()
    today_str = datetime.now().strftime("%Y-%m-%d")
    if settings.get("last_comment_date") != today_str:
        settings["comments_today"] = 0
        settings["last_comment_date"] = today_str

    if res.get("success"):
        settings["comments_today"] = settings.get("comments_today", 0) + 1
        settings["last_comment_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    history_item = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "target_urn": target_urn,
        "post_title": post_title or target_urn,
        "comment_text": comment_text,
        "success": res.get("success", False),
        "public_url": res.get("public_url", f"https://www.linkedin.com/feed/update/{target_urn}"),
        "error": res.get("error"),
    }
    history = settings.get("history", [])
    history.insert(0, history_item)
    settings["history"] = history[:30]  # Keep last 30 comments
    save_comment_settings(settings)

    return res
