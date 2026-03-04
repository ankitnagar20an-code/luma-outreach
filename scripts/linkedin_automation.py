"""LinkedIn automation via Playwright — posts, comments, DMs, connection requests, InMails."""

from __future__ import annotations

import base64
import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

LINKEDIN_BASE = "https://www.linkedin.com"


def _random_sleep(min_s: float = 5.0, max_s: float = 15.0) -> None:
    """Sleep for a random duration to mimic human behavior."""
    duration = random.uniform(min_s, max_s)
    logger.debug("Sleeping %.1fs", duration)
    time.sleep(duration)


def _load_session() -> list[dict]:
    """Load LinkedIn session cookies from file or env var."""
    b64 = os.environ.get("LINKEDIN_SESSION_B64")
    if b64:
        raw = base64.b64decode(b64)
        return json.loads(raw)

    session_path = Path("session.json")
    if session_path.exists():
        return json.loads(session_path.read_text(encoding="utf-8"))

    raise FileNotFoundError(
        "No LinkedIn session found. Set LINKEDIN_SESSION_B64 or place session.json in project root."
    )


class LinkedInAutomation:
    """Headless Playwright automation for LinkedIn actions."""

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def start(self) -> None:
        """Launch browser and restore LinkedIn session."""
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self._context = self._browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        # Restore session cookies
        cookies = _load_session()
        self._context.add_cookies(cookies)

        self._page = self._context.new_page()
        logger.info("LinkedIn browser session started.")

    def stop(self) -> None:
        """Close browser and cleanup."""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        logger.info("LinkedIn browser session closed.")

    def _ensure_page(self) -> Page:
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page

    def _check_login(self) -> bool:
        """Verify that the session cookies are valid."""
        page = self._ensure_page()
        page.goto(f"{LINKEDIN_BASE}/feed/", wait_until="domcontentloaded", timeout=30000)
        _random_sleep(3, 5)

        # If redirected to login, session is invalid
        if "/login" in page.url or "/checkpoint" in page.url:
            logger.error("LinkedIn session expired or invalid. Current URL: %s", page.url)
            return False

        logger.info("LinkedIn session is valid. Logged in.")
        return True

    # ── LinkedIn Posts ──────────────────────────────────────────────

    def create_post(self, text: str) -> dict[str, Any]:
        """
        Create a LinkedIn post on the feed.

        Returns dict with 'status' (SENT/FAILED) and optional 'error'.
        """
        page = self._ensure_page()
        try:
            page.goto(f"{LINKEDIN_BASE}/feed/", wait_until="domcontentloaded", timeout=30000)
            _random_sleep(3, 6)

            # Click "Start a post" button
            start_post_btn = page.locator("button.share-box-feed-entry__trigger").first
            if not start_post_btn.is_visible(timeout=10000):
                # Fallback selector
                start_post_btn = page.locator("[data-control-name='share.share_box']").first
            start_post_btn.click()
            _random_sleep(2, 4)

            # Type in the post editor
            editor = page.locator("div.ql-editor[data-placeholder]").first
            if not editor.is_visible(timeout=10000):
                editor = page.locator("[role='textbox']").first
            editor.click()
            _random_sleep(1, 2)

            # Type character by character for more human-like behavior
            editor.fill(text)
            _random_sleep(2, 4)

            # Click Post button
            post_btn = page.locator("button.share-actions__primary-action").first
            if not post_btn.is_visible(timeout=5000):
                post_btn = page.locator("button:has-text('Post')").last
            post_btn.click()
            _random_sleep(5, 10)

            logger.info("LinkedIn post published successfully.")
            return {"status": "SENT"}

        except Exception as e:
            logger.error("Failed to create LinkedIn post: %s", e)
            return {"status": "FAILED", "error": str(e)}

    # ── LinkedIn Comments ───────────────────────────────────────────

    def post_comment(self, post_url: str, comment_text: str) -> dict[str, Any]:
        """
        Post a comment on a specific LinkedIn post.

        Returns dict with 'status' (SENT/FAILED).
        """
        page = self._ensure_page()
        try:
            page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
            _random_sleep(3, 6)

            # Click the comment input area
            comment_btn = page.locator("button[aria-label*='Comment']").first
            if comment_btn.is_visible(timeout=5000):
                comment_btn.click()
                _random_sleep(2, 3)

            # Find and fill the comment box
            comment_box = page.locator("div.ql-editor[data-placeholder*='comment']").first
            if not comment_box.is_visible(timeout=10000):
                comment_box = page.locator("[role='textbox']").first

            comment_box.click()
            _random_sleep(1, 2)
            comment_box.fill(comment_text)
            _random_sleep(2, 4)

            # Submit the comment
            submit_btn = page.locator("button.comments-comment-box__submit-button").first
            if not submit_btn.is_visible(timeout=5000):
                submit_btn = page.locator("button[aria-label*='Post comment']").first
            if not submit_btn.is_visible(timeout=5000):
                submit_btn = page.locator("button:has-text('Post')").last
            submit_btn.click()
            _random_sleep(5, 10)

            logger.info("Comment posted on %s", post_url)
            return {"status": "SENT"}

        except Exception as e:
            logger.error("Failed to comment on %s: %s", post_url, e)
            return {"status": "FAILED", "error": str(e)}

    # ── Connection Requests ─────────────────────────────────────────

    def send_connection_request(self, profile_url: str, note: str = "") -> dict[str, Any]:
        """
        Send a connection request with an optional note.

        Returns dict with 'status' (SENT/FAILED/SKIPPED).
        """
        page = self._ensure_page()
        try:
            page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
            _random_sleep(3, 6)

            # Look for Connect button
            connect_btn = page.locator("button:has-text('Connect')").first
            if not connect_btn.is_visible(timeout=10000):
                # May need to click "More" first
                more_btn = page.locator("button:has-text('More')").first
                if more_btn.is_visible(timeout=5000):
                    more_btn.click()
                    _random_sleep(1, 2)
                    connect_btn = page.locator("[aria-label*='Connect']").first
                    if not connect_btn.is_visible(timeout=5000):
                        logger.info("No Connect option for %s (may already be connected)", profile_url)
                        return {"status": "SKIPPED", "error": "Connect button not found"}

            connect_btn.click()
            _random_sleep(2, 3)

            if note:
                # Click "Add a note"
                add_note_btn = page.locator("button:has-text('Add a note')").first
                if add_note_btn.is_visible(timeout=5000):
                    add_note_btn.click()
                    _random_sleep(1, 2)

                    # Fill in the note
                    note_field = page.locator("textarea[name='message']").first
                    if not note_field.is_visible(timeout=5000):
                        note_field = page.locator("#custom-message").first
                    note_field.fill(note[:300])  # LinkedIn enforces 300 char limit
                    _random_sleep(2, 3)

            # Send the request
            send_btn = page.locator("button[aria-label*='Send']").first
            if not send_btn.is_visible(timeout=5000):
                send_btn = page.locator("button:has-text('Send')").last
            send_btn.click()
            _random_sleep(5, 10)

            logger.info("Connection request sent to %s", profile_url)
            return {"status": "SENT"}

        except Exception as e:
            logger.error("Failed to send connection request to %s: %s", profile_url, e)
            return {"status": "FAILED", "error": str(e)}

    # ── Direct Messages ─────────────────────────────────────────────

    def send_dm(self, profile_url: str, message: str) -> dict[str, Any]:
        """
        Send a direct message to a LinkedIn connection.

        Returns dict with 'status' (SENT/FAILED).
        """
        page = self._ensure_page()
        try:
            page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
            _random_sleep(3, 6)

            # Click Message button
            msg_btn = page.locator("button:has-text('Message')").first
            if not msg_btn.is_visible(timeout=10000):
                logger.warning("Message button not found for %s", profile_url)
                return {"status": "FAILED", "error": "Message button not found"}

            msg_btn.click()
            _random_sleep(3, 5)

            # Type in the message box
            msg_box = page.locator("div.msg-form__contenteditable[role='textbox']").first
            if not msg_box.is_visible(timeout=10000):
                msg_box = page.locator("[role='textbox']").last
            msg_box.click()
            _random_sleep(1, 2)
            msg_box.fill(message)
            _random_sleep(2, 4)

            # Send
            send_btn = page.locator("button.msg-form__send-button").first
            if not send_btn.is_visible(timeout=5000):
                send_btn = page.locator("button[type='submit']:has-text('Send')").first
            send_btn.click()
            _random_sleep(5, 10)

            logger.info("DM sent to %s", profile_url)
            return {"status": "SENT"}

        except Exception as e:
            logger.error("Failed to send DM to %s: %s", profile_url, e)
            return {"status": "FAILED", "error": str(e)}

    # ── InMail ──────────────────────────────────────────────────────

    def send_inmail(self, profile_url: str, subject: str, message: str) -> dict[str, Any]:
        """
        Send an InMail to a non-connection.

        Returns dict with 'status' (SENT/FAILED/SKIPPED).
        """
        page = self._ensure_page()
        try:
            page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
            _random_sleep(3, 6)

            # Look for InMail / Message button (for non-connections it says "Message" with InMail credits)
            msg_btn = page.locator("button:has-text('Message')").first
            if not msg_btn.is_visible(timeout=10000):
                # Try via More menu
                more_btn = page.locator("button:has-text('More')").first
                if more_btn.is_visible(timeout=5000):
                    more_btn.click()
                    _random_sleep(1, 2)
                    msg_btn = page.locator("[aria-label*='InMail'], [aria-label*='Message']").first

            if not msg_btn.is_visible(timeout=5000):
                logger.warning("InMail/Message button not found for %s", profile_url)
                return {"status": "SKIPPED", "error": "InMail button not found"}

            msg_btn.click()
            _random_sleep(3, 5)

            # Fill subject if the InMail dialog has a subject field
            subject_field = page.locator("input[name='subject'], input[placeholder*='Subject']").first
            if subject_field.is_visible(timeout=3000):
                subject_field.fill(subject)
                _random_sleep(1, 2)

            # Fill message body
            msg_box = page.locator("div.msg-form__contenteditable[role='textbox']").first
            if not msg_box.is_visible(timeout=10000):
                msg_box = page.locator("[role='textbox']").last
            msg_box.click()
            _random_sleep(1, 2)
            msg_box.fill(message)
            _random_sleep(2, 4)

            # Send
            send_btn = page.locator("button.msg-form__send-button").first
            if not send_btn.is_visible(timeout=5000):
                send_btn = page.locator("button[type='submit']:has-text('Send')").first
            send_btn.click()
            _random_sleep(5, 10)

            logger.info("InMail sent to %s", profile_url)
            return {"status": "SENT"}

        except Exception as e:
            logger.error("Failed to send InMail to %s: %s", profile_url, e)
            return {"status": "FAILED", "error": str(e)}
