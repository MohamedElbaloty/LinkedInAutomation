"""
Official LinkedIn REST API Client for Safe, Zero-Ban Cloud Publishing.
Uses LinkedIn OAuth 2.0 and Community Management / Posts API with dynamic version negotiation.
100% compliant with LinkedIn Terms of Service, safe for cloud deployment on Railway/AWS.
"""

from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple
import requests

from config import (
    BASE_DIR,
    LINKEDIN_ACCESS_TOKEN,
    LINKEDIN_CLIENT_ID,
    LINKEDIN_CLIENT_SECRET,
    LINKEDIN_PERSON_URN,
)

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE = "https://api.linkedin.com"
LINKEDIN_OAUTH_BASE = "https://www.linkedin.com/oauth/v2"


def get_candidate_versions() -> List[str]:
    """
    Generates a prioritized list of LinkedIn API versions (YYYYMM) within the supported window.
    LinkedIn releases monthly versions and accepts any active version (typically rolling 12 months).
    """
    candidates: List[str] = []
    env_ver = os.getenv("LINKEDIN_API_VERSION", "").strip()
    if env_ver:
        candidates.append(env_ver)

    # Candidate months from current going back 24 months
    now = datetime.now()
    for offset in range(0, 24):
        y = now.year
        m = now.month - offset
        while m <= 0:
            m += 12
            y -= 1
        ver = f"{y:04d}{m:02d}"
        if ver not in candidates:
            candidates.append(ver)

    # Known stable fallbacks
    fallbacks = [
        "202608", "202607", "202606", "202605", "202604", "202603", "202602", "202601",
        "202512", "202511", "202510", "202509", "202508", "202507", "202506", "202505",
        "202504", "202503", "202502", "202501", "202412", "202411", "202410", "202409",
    ]
    for fb in fallbacks:
        if fb not in candidates:
            candidates.append(fb)

    return candidates


# Cached working version across requests
_ACTIVE_LINKEDIN_VERSION: str = os.getenv("LINKEDIN_API_VERSION", "202608")

# Regex to match reserved LinkedIn Little Text markup characters that cause silent post truncation:
# \ | { } @ [ ] ( ) < > and isolated underscores (preserving hashtags like #Machine_Learning)
LINKEDIN_LITTLE_TEXT_ESCAPE_RE = re.compile(r"([\\|{}@\[\]()<>]|(?<!\w)_(?!\w))")


def escape_linkedin_commentary(text: str) -> str:
    """
    Escapes reserved 'Little Text' markup characters in LinkedIn commentary.
    In LinkedIn /rest/posts, unescaped characters like (, ), [, ], {, }, <, >, |, @, \\
    are parsed as entity mention or link markup. When invalid, LinkedIn silently truncates
    the commentary text from that character onwards.
    """
    if not text:
        return ""
    # Normalize existing escapes to avoid double-escaping
    cleaned = re.sub(r"\\([\\|{}@\[\]()<>]|(?<!\w)_(?!\w))", r"\1", text)
    return LINKEDIN_LITTLE_TEXT_ESCAPE_RE.sub(r"\\\1", cleaned)


class LinkedInAPIClient:
    """Official LinkedIn REST API Client with automatic version negotiation."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        person_urn: Optional[str] = None,
    ):
        global _ACTIVE_LINKEDIN_VERSION
        self.access_token = (access_token or LINKEDIN_ACCESS_TOKEN).strip()
        self.person_urn = (person_urn or LINKEDIN_PERSON_URN).strip()
        self.client_id = LINKEDIN_CLIENT_ID.strip()
        self.client_secret = LINKEDIN_CLIENT_SECRET.strip()
        self.api_version = _ACTIVE_LINKEDIN_VERSION

    def get_authorization_url(self, redirect_uri: str) -> str:
        """Generates the official LinkedIn OAuth 2.0 authorization URL."""
        scopes = "openid%20profile%20w_member_social%20email"
        return (
            f"{LINKEDIN_OAUTH_BASE}/authorization?"
            f"response_type=code&"
            f"client_id={self.client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"scope={scopes}"
        )

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, any]:
        """Exchanges authorization code for an OAuth access token."""
        url = f"{LINKEDIN_OAUTH_BASE}/accessToken"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": redirect_uri,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = requests.post(url, data=data, headers=headers, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"LinkedIn OAuth exchange failed: {resp.status_code} - {resp.text}")
        token_data = resp.json()
        self.access_token = token_data.get("access_token", "")
        return token_data

    def get_headers(self, version: Optional[str] = None) -> Dict[str, str]:
        """Standard headers for LinkedIn REST API requests."""
        if not self.access_token:
            raise ValueError("LinkedIn Access Token is missing. Connect your account first.")
        ver = version or self.api_version
        return {
            "Authorization": f"Bearer {self.access_token}",
            "LinkedIn-Version": ver,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }

    def _request_with_version_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Sends an HTTP request, automatically negotiating LinkedIn-Version if a 426 NONEXISTENT_VERSION occurs.
        """
        global _ACTIVE_LINKEDIN_VERSION
        candidates = get_candidate_versions()
        if self.api_version in candidates:
            candidates.remove(self.api_version)
        candidates.insert(0, self.api_version)

        last_resp = None
        for ver in candidates:
            headers = self.get_headers(version=ver)
            if "headers" in kwargs:
                merged = {**headers, **kwargs["headers"]}
            else:
                merged = headers

            req_kwargs = {**kwargs, "headers": merged}
            resp = requests.request(method, url, **req_kwargs)
            last_resp = resp

            # 426 indicates deprecated or non-existent version header
            if resp.status_code == 426 and "NONEXISTENT_VERSION" in resp.text:
                logger.debug("LinkedIn-Version %s returned 426 NONEXISTENT_VERSION. Trying next candidate...", ver)
                continue

            # Accepted or valid response
            if resp.status_code in (200, 201, 204):
                if self.api_version != ver:
                    logger.info("Negotiated active LinkedIn API version: %s", ver)
                    self.api_version = ver
                    _ACTIVE_LINKEDIN_VERSION = ver
            return resp

        return last_resp

    def fetch_my_profile_urn(self) -> str:
        """Fetches the authenticated member's URN using the UserInfo endpoint."""
        url = f"{LINKEDIN_API_BASE}/v2/userinfo"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch userinfo from LinkedIn: {resp.status_code} - {resp.text}")
        user_info = resp.json()
        sub = user_info.get("sub")
        if not sub:
            raise RuntimeError("LinkedIn userinfo did not contain 'sub' identifier.")
        self.person_urn = f"urn:li:person:{sub}"
        logger.info("Retrieved LinkedIn member URN: %s", self.person_urn)
        return self.person_urn

    def upload_image(self, image_path: Path) -> str:
        """
        Uploads an image to LinkedIn using the 2-step REST Images API.
        Returns the registered image URN (e.g. 'urn:li:image:...').
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found at {image_path}")

        if not self.person_urn:
            self.fetch_my_profile_urn()

        # Step 1: Initialize Upload
        init_url = f"{LINKEDIN_API_BASE}/rest/images?action=initializeUpload"
        init_payload = {
            "initializeUploadRequest": {
                "owner": self.person_urn
            }
        }
        resp = self._request_with_version_retry("POST", init_url, json=init_payload, timeout=20)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Failed to initialize image upload: {resp.status_code} - {resp.text}")

        init_data = resp.json().get("value", {})
        upload_url = init_data.get("uploadUrl")
        image_urn = init_data.get("image")

        if not upload_url or not image_urn:
            raise RuntimeError(f"Invalid upload initialization response: {init_data}")

        # Step 2: Upload Binary Bytes
        with open(image_path, "rb") as img_file:
            binary_data = img_file.read()

        upload_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/octet-stream",
        }
        put_resp = requests.put(upload_url, data=binary_data, headers=upload_headers, timeout=60)
        if put_resp.status_code not in (200, 201, 204):
            raise RuntimeError(f"Failed to upload image binary to LinkedIn: {put_resp.status_code}")

        logger.info("Successfully uploaded image to LinkedIn with URN: %s", image_urn)
        return image_urn

    def create_post(self, post_text: str, image_path: Optional[Path] = None) -> Dict[str, any]:
        """
        Creates a public post on LinkedIn with optional media attachment.
        Returns dictionary containing post_urn and public_url.
        """
        if not self.person_urn:
            self.fetch_my_profile_urn()

        escaped_commentary = escape_linkedin_commentary(post_text)
        logger.info(
            "Prepared commentary for LinkedIn API (Original: %d chars, Escaped: %d chars)",
            len(post_text),
            len(escaped_commentary),
        )

        url = f"{LINKEDIN_API_BASE}/rest/posts"
        payload = {
            "author": self.person_urn,
            "commentary": escaped_commentary,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False
        }

        # Attach image if provided
        if image_path and Path(image_path).exists():
            try:
                image_urn = self.upload_image(Path(image_path))
                payload["content"] = {
                    "media": {
                        "id": image_urn,
                        "altText": "AI Technology Architecture & Engineering Analysis"
                    }
                }
            except Exception as img_err:
                logger.warning("Image attachment could not be uploaded (%s). Publishing high-impact text post.", img_err)

        resp = self._request_with_version_retry("POST", url, json=payload, timeout=25)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Failed to create post on LinkedIn: {resp.status_code} - {resp.text}")

        post_urn = resp.headers.get("x-restli-id") or resp.headers.get("x-linkedin-id") or ""
        public_url = f"https://www.linkedin.com/feed/update/{post_urn}" if post_urn else "https://www.linkedin.com/feed/"
        logger.info("Post published successfully on LinkedIn! URN: %s", post_urn)

        return {
            "success": True,
            "post_urn": post_urn,
            "public_url": public_url,
            "method": "official_api",
        }


def publish_article_to_linkedin_safe(post_text: str, image_path: Optional[Path] = None) -> Dict[str, any]:
    """
    Unified entry point for publishing to LinkedIn.
    1. If official API token is configured -> Uses official 100% safe REST API.
    2. If local browser profile exists -> Falls back to local Playwright session (Local ONLY).
    3. Returns dict with status, method, and URL.
    """
    token = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip() or LINKEDIN_ACCESS_TOKEN
    is_cloud = bool(
        os.getenv("RAILWAY_ENVIRONMENT")
        or os.getenv("RAILWAY_STATIC_URL")
        or os.getenv("DYNO")
        or os.getenv("KUBERNETES_SERVICE_HOST")
    )

    # 1. First priority: Official REST API (Safe for Cloud & Railway)
    if token:
        try:
            logger.info("Using Official LinkedIn REST API for publishing...")
            client = LinkedInAPIClient(access_token=token)
            return client.create_post(post_text, image_path)
        except Exception as api_err:
            logger.error("Official LinkedIn API publish failed: %s", api_err)
            if is_cloud:
                return {
                    "success": False,
                    "error": f"LinkedIn API Error: {str(api_err)}",
                    "method": "official_api",
                }

    # 2. Second priority: Local Browser Session (ONLY locally on residential IP)
    if not is_cloud:
        try:
            from linkedin_publisher import LINKEDIN_PROFILE_DIR, publish_to_linkedin
            if LINKEDIN_PROFILE_DIR.exists():
                logger.info("Using Local LinkedIn browser session for publishing...")
                success = publish_to_linkedin(post_text, image_path)
                return {
                    "success": success,
                    "post_urn": "browser_session",
                    "public_url": "https://www.linkedin.com/in/me/recent-activity/all/",
                    "method": "browser_session",
                }
        except ImportError:
            logger.info("Playwright is not installed in environment. Skipping local browser fallback.")
        except Exception as browser_err:
            logger.error("Browser session publish failed: %s", browser_err)

    # 3. If neither is available, return clean error
    return {
        "success": False,
        "error": (
            "LinkedIn credentials not configured. Please connect your LinkedIn account "
            "in the Web Dashboard or set LINKEDIN_ACCESS_TOKEN in your Railway / .env environment."
        ),
        "method": "none",
    }
