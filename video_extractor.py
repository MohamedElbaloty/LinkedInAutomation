"""
Video Extractor module for LinkedIn & Telegram Publisher.
Discovers and extracts native videos (product demos, keynotes, smart city tours, AI showcases)
from news articles and tech media using BeautifulSoup and yt-dlp.
"""

import logging
import re
from pathlib import Path
from typing import Optional
from bs4 import BeautifulSoup
import requests
import yt_dlp

from config import BASE_DIR, VIDEOS_DIR

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def find_video_url_in_page(page_url: str) -> Optional[str]:
    """
    Inspects an article webpage to detect embedded videos:
    - Direct HTML5 <video> / <source> elements
    - YouTube embeds (iframe, embed, watch URLs)
    - Vimeo embeds
    - OpenGraph video metadata (og:video)
    - Twitter / X video embeds
    """
    if not page_url:
        return None

    # If the URL itself is already a direct video platform link
    direct_patterns = [
        r"youtube\.com/watch\?v=",
        r"youtu\.be/",
        r"youtube\.com/shorts/",
        r"vimeo\.com/\d+",
        r"\.mp4(\?.*)?$",
    ]
    for dp in direct_patterns:
        if re.search(dp, page_url, re.IGNORECASE):
            return page_url

    try:
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(page_url, headers=headers, timeout=12)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. Check OpenGraph video metadata
        og_video = soup.find("meta", property=re.compile(r"^og:video(:url)?$", re.I))
        if og_video and og_video.get("content"):
            v_url = og_video["content"].strip()
            if not v_url.endswith(".swf") and ("youtube" in v_url or "vimeo" in v_url or ".mp4" in v_url):
                logger.info("Found OpenGraph video URL in %s: %s", page_url, v_url)
                return v_url

        # 2. Check HTML5 <video> and <source> tags
        for vid in soup.find_all("video"):
            src = vid.get("src")
            if src and ".mp4" in src:
                return _normalize_url(src, page_url)
            for source in vid.find_all("source"):
                s_src = source.get("src")
                if s_src and ".mp4" in s_src:
                    return _normalize_url(s_src, page_url)

        # 3. Check iframes (YouTube, Vimeo)
        for iframe in soup.find_all("iframe"):
            src = iframe.get("src") or iframe.get("data-src") or ""
            if "youtube.com/embed/" in src:
                m = re.search(r"youtube\.com/embed/([a-zA-Z0-9_-]+)", src)
                if m:
                    yt_url = f"https://www.youtube.com/watch?v={m.group(1)}"
                    logger.info("Extracted YouTube video from embed: %s", yt_url)
                    return yt_url
            if "player.vimeo.com/video/" in src:
                m = re.search(r"player\.vimeo\.com/video/(\d+)", src)
                if m:
                    vimeo_url = f"https://vimeo.com/{m.group(1)}"
                    logger.info("Extracted Vimeo video from embed: %s", vimeo_url)
                    return vimeo_url

        # 4. Check explicit links to YouTube inside article body
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if re.search(r"youtube\.com/watch\?v=[a-zA-Z0-9_-]+", href):
                return href

    except Exception as e:
        logger.debug("Could not inspect page for video (%s): %s", page_url, e)

    return None


def _normalize_url(url: str, base_url: str) -> str:
    """Normalizes relative video URLs."""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{url}"
    return url


def download_video(video_url: str, article_id: str, target_dir: Path = VIDEOS_DIR) -> Optional[Path]:
    """
    Downloads a video cleanly using yt-dlp or direct stream.
    Formats video to MP4 (H.264), 720p/1080p, capped at 45MB for fast upload.
    Returns Path to local .mp4 file or None if unavailable.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(target_dir / f"{article_id}.%(ext)s")

    # Options configured for fast, clean, high-compatibility MP4 download
    ydl_opts = {
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
        "outtmpl": out_template,
        "max_filesize": 45 * 1024 * 1024,  # Max 45 MB
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "match_filter": _duration_filter(360),  # Max 6 minutes (optimal for LinkedIn video reach)
    }

    try:
        logger.info("Downloading native video via yt-dlp from: %s", video_url)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # Check for downloaded output file
        for ext in ["mp4", "mkv", "webm"]:
            candidate = target_dir / f"{article_id}.{ext}"
            if candidate.exists() and candidate.stat().st_size > 100 * 1024:  # At least 100KB
                logger.info("Successfully downloaded video: %s (size: %d bytes)", candidate, candidate.stat().st_size)
                return candidate

    except Exception as e:
        logger.warning("yt-dlp video download failed for %s: %s", video_url, e)

    return None


def _duration_filter(max_duration: int):
    """Filters out excessively long videos (e.g. full 2-hour webinars)."""
    def filter_fn(info_dict, *, incomplete):
        duration = info_dict.get("duration")
        if duration and duration > max_duration:
            return f"Video is too long ({duration}s > {max_duration}s) for LinkedIn short video"
        return None
    return filter_fn


def extract_and_download_video(article_url: str, article_id: str) -> Optional[Path]:
    """
    High-level orchestrator:
    1. Checks if article page has an embedded video.
    2. Downloads and validates the video file.
    3. Returns local Path to MP4, or None.
    """
    video_url = find_video_url_in_page(article_url)
    if not video_url:
        return None

    return download_video(video_url, article_id)
