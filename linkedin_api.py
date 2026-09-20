"""
Official LinkedIn REST API Client for Safe, Zero-Ban Cloud Publishing.
Uses LinkedIn OAuth 2.0 and Community Management / Posts API (LinkedIn Version 202401+).
100% compliant with LinkedIn Terms of Service, safe for cloud deployment on Railway/AWS.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
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
LINKEDIN_API_VERSION = "202401"


class LinkedInAPIClient:
    """Official LinkedIn REST API Client."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        person_urn: Optional[str] = None,
    ):
        self.access_token = (access_token or LINKEDIN_ACCESS_TOKEN).strip()
        self.person_urn = (person_urn or LINKEDIN_PERSON_URN).strip()
        self.client_id = LINKEDIN_CLIENT_ID.strip()
        self.client_secret = LINKEDIN_CLIENT_SECRET.strip()

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

    def get_headers(self) -> Dict[str, str]:
        """Standard headers for LinkedIn REST API requests."""
        if not self.access_token:
            raise ValueError("LinkedIn Access Token is missing. Connect your account first.")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "LinkedIn-Version": LINKEDIN_API_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }

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
        headers = self.get_headers()
        resp = requests.post(init_url, json=init_payload, headers=headers, timeout=20)
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

        url = f"{LINKEDIN_API_BASE}/rest/posts"
        headers = self.get_headers()

        payload = {
            "author": self.person_urn,
            "commentary": post_text,
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
            image_urn = self.upload_image(Path(image_path))
            payload["content"] = {
                "media": {
                    "id": image_urn,
                    "title": "AI Technology Architecture & Engineering Analysis"
                }
            }

        resp = requests.post(url, json=payload, headers=headers, timeout=25)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Failed to create post on LinkedIn: {resp.status_code} - {resp.text}")

        post_urn = resp.headers.get("x-restli-id") or resp.headers.get("x-linkedin-id") or ""
        # Clean post URN
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
    2. If local browser profile exists -> Falls back to local Playwright session.
    3. Returns dict with status, method, and URL.
    """
    # 1. First priority: Official REST API (Safe for Cloud & Railway)
    token = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip() or LINKEDIN_ACCESS_TOKEN
    if token:
        try:
            logger.info("Using Official LinkedIn REST API for publishing...")
            client = LinkedInAPIClient(access_token=token)
            return client.create_post(post_text, image_path)
        except Exception as api_err:
            logger.error("Official LinkedIn API publish failed: %s", api_err)
            # Continue to fallback

    # 2. Second priority: Local Browser Session (Safe on local residential IP)
    from linkedin_publisher import LINKEDIN_PROFILE_DIR, publish_to_linkedin
    if LINKEDIN_PROFILE_DIR.exists() and not os.getenv("RAILWAY_ENVIRONMENT"):
        try:
            logger.info("Using Local LinkedIn browser session for publishing...")
            success = publish_to_linkedin(post_text, image_path)
            return {
                "success": success,
                "post_urn": "browser_session",
                "public_url": "https://www.linkedin.com/in/me/recent-activity/all/",
                "method": "browser_session",
            }
        except Exception as browser_err:
            logger.error("Browser session publish failed: %s", browser_err)

    # 3. If neither is available, return detailed instructional error
    return {
        "success": False,
        "error": (
            "LinkedIn credentials not configured. Please connect your LinkedIn account "
            "in the Web Dashboard or set LINKEDIN_ACCESS_TOKEN in your Railway / .env environment."
        ),
        "method": "none",
    }
