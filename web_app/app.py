"""
FastAPI Backend Application for LinkedIn AI News Publisher & Web Dashboard.
Provides REST APIs for live scheduling, immediate 'Publish Now' testing, and status monitoring.
"""

import asyncio
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from comment_engine import (
    draft_comment_for_target,
    execute_linkedin_comment,
    get_today_trending_topics,
    load_comment_settings,
    save_comment_settings,
)
from config import (
    BASE_DIR,
    DB_PATH,
    DEFAULT_SCHEDULE_TIMES,
    LINKEDIN_ACCESS_TOKEN,
    LINKEDIN_CLIENT_ID,
    LINKEDIN_PERSON_URN,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from fetcher import fetch_unread_articles
from linkedin_api import LinkedInAPIClient
from web_app.scheduler import load_schedule_settings, save_schedule_settings, scheduler_service

WEB_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager to start and stop the background scheduler gracefully."""
    print("Starting Autonomous LinkedIn Growth Scheduler...")
    scheduler_service.start()
    yield
    print("Shutting down Scheduler...")
    scheduler_service.stop()


app = FastAPI(
    title="LinkedIn AI Organic Growth Hub",
    description="Automated AI news intelligence pipeline and LinkedIn publisher.",
    version="2.0.0",
    lifespan=lifespan,
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class ScheduleUpdateRequest(BaseModel):
    times: List[str]
    enabled: bool = True


class TokenUpdateRequest(BaseModel):
    access_token: str
    person_urn: Optional[str] = None


class CommentDraftRequest(BaseModel):
    target_url: Optional[str] = None
    target_text: Optional[str] = None


class CommentPublishRequest(BaseModel):
    target_urn: str
    comment_text: str
    post_title: Optional[str] = None


class CommentToggleRequest(BaseModel):
    enabled: bool


def get_posted_history(limit: int = 15) -> List[Dict[str, str]]:
    """Fetches recently posted articles from SQLite."""
    if not DB_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, title, published_at FROM posted_news ORDER BY rowid DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        return [{"id": r[0], "title": r[1], "published_at": r[2]} for r in rows]
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Renders the main dashboard interface."""
    settings = load_schedule_settings()
    history = get_posted_history(limit=8)
    unread = fetch_unread_articles()[:5]

    is_linkedin_connected = bool(os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip() or LINKEDIN_ACCESS_TOKEN)
    is_telegram_connected = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    is_railway = bool(os.getenv("RAILWAY_ENVIRONMENT"))

    comment_settings = load_comment_settings()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "settings": settings,
            "comment_settings": comment_settings,
            "history": history,
            "unread": unread,
            "is_linkedin_connected": is_linkedin_connected,
            "is_telegram_connected": is_telegram_connected,
            "is_railway": is_railway,
            "default_times": DEFAULT_SCHEDULE_TIMES,
        },
    )


@app.get("/api/status")
async def get_status():
    """Returns current system health, schedule state, and connection status."""
    settings = load_schedule_settings()
    is_linkedin_connected = bool(os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip() or LINKEDIN_ACCESS_TOKEN)
    
    # Check next job execution
    next_run_time = None
    jobs = scheduler_service.scheduler.get_jobs()
    if jobs:
        # Find earliest next run time
        upcoming = [j.next_run_time for j in jobs if j.next_run_time]
        if upcoming:
            next_run_time = min(upcoming).strftime("%Y-%m-%d %H:%M:%S")

    return {
        "status": "online",
        "version": "v2.3-full-story-watermark",
        "timestamp": datetime.now().isoformat(),
        "scheduler_enabled": settings.get("enabled", True),
        "schedule_times": settings.get("times", DEFAULT_SCHEDULE_TIMES),
        "next_run": next_run_time,
        "last_run": settings.get("last_run"),
        "is_running_job": scheduler_service.is_running_job,
        "linkedin_connected": is_linkedin_connected,
        "telegram_connected": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID),
        "railway_mode": bool(os.getenv("RAILWAY_ENVIRONMENT")),
    }


@app.get("/api/queue")
async def get_queue():
    """Returns upcoming unread AI articles awaiting publication."""
    unread = fetch_unread_articles()[:10]
    return {
        "count": len(unread),
        "articles": [
            {
                "id": a.id,
                "title": a.title,
                "source": a.source,
                "published_at": a.published_at,
                "score": a.relevance_score,
                "link": a.link,
            }
            for a in unread
        ],
    }


@app.get("/api/history")
async def get_history():
    """Returns previously posted articles."""
    return {"history": get_posted_history(limit=25)}


@app.post("/api/schedule")
async def update_schedule(data: ScheduleUpdateRequest):
    """Updates active posting times and enables/disables scheduling."""
    updated = scheduler_service.update_times(data.times, data.enabled)
    return {"success": True, "settings": updated}


@app.post("/api/publish-now")
async def publish_now():
    """
    Triggers an immediate publishing cycle.
    Fetches latest article, generates copy and image, publishes to LinkedIn and Telegram.
    """
    if scheduler_service.is_running_job:
        return JSONResponse(
            status_code=409,
            content={"success": False, "error": "A generation job is currently in progress. Please wait a moment."},
        )

    result = await scheduler_service.execute_pipeline_job()
    return result


@app.post("/api/publish-telegram")
async def publish_telegram_only():
    """
    Triggers an immediate publishing cycle specifically to Telegram.
    Fetches latest article, generates copy and image, sends to Telegram channel/bot.
    """
    if scheduler_service.is_running_job:
        return JSONResponse(
            status_code=409,
            content={"success": False, "error": "A generation job is currently in progress. Please wait a moment."},
        )

    result = await scheduler_service.execute_telegram_job()
    return result


@app.post("/api/save-linkedin-token")
async def save_linkedin_token(data: TokenUpdateRequest):
    """Saves LinkedIn OAuth Access Token to environment and config."""
    token = data.access_token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token cannot be empty")

    os.environ["LINKEDIN_ACCESS_TOKEN"] = token
    if data.person_urn:
        os.environ["LINKEDIN_PERSON_URN"] = data.person_urn.strip()

    # Test token validity
    try:
        client = LinkedInAPIClient(access_token=token)
        urn = client.fetch_my_profile_urn()
        return {"success": True, "message": "LinkedIn token verified successfully!", "person_urn": urn}
    except Exception as e:
        return {"success": False, "error": f"Token validation failed: {str(e)}"}


# ---------------------------------------------------------------------------
# LinkedIn Organic Engagement & Commenting Engine APIs
# ---------------------------------------------------------------------------

@app.post("/api/comment/draft")
async def api_draft_comment(data: CommentDraftRequest):
    """
    Analyzes target post or discovers a trending sector post,
    then drafts an authentic CTO comment (Mohamed Elbaloty, CTO @ Sahalat).
    """
    try:
        res = draft_comment_for_target(
            target_url_or_urn=data.target_url or "",
            target_text=data.target_text or "",
        )
        return res
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.post("/api/comment/publish")
async def api_publish_comment(data: CommentPublishRequest):
    """
    Publishes an authentic comment live on LinkedIn via official REST API.
    """
    try:
        res = execute_linkedin_comment(
            target_urn_or_url=data.target_urn,
            comment_text=data.comment_text,
            post_title=data.post_title or "",
        )
        return res
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.get("/api/comment/settings")
async def api_get_comment_settings():
    """Returns current automated commenting settings and recent history."""
    return load_comment_settings()


@app.post("/api/comment/toggle")
async def api_toggle_commenting(data: CommentToggleRequest):
    """Enables or disables autonomous background commenting."""
    settings = load_comment_settings()
    settings["auto_comment_enabled"] = data.enabled
    save_comment_settings(settings)
    return {"success": True, "settings": settings}


@app.get("/api/comment/latest-post")
async def api_get_latest_post():
    """Returns the most recent published post on LinkedIn for 1-click test commenting."""
    from linkedin_api import get_recent_published_linkedin_posts
    posts = get_recent_published_linkedin_posts(limit=1)
    if posts:
        return {"success": True, "post": posts[0]}
    return {"success": False, "post": None}


@app.get("/api/comment/trending-today")
async def api_get_trending_today():
    """Returns today's curated FinTech and PropTech topics with smart LinkedIn search links."""
    try:
        topics = get_today_trending_topics(limit=6)
        return {"success": True, "topics": topics}
    except Exception as e:
        return {"success": False, "error": str(e), "topics": []}

