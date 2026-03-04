"""Gmail API client for sending outreach emails."""

from __future__ import annotations

import base64
import json
import logging
import os
from email.mime.text import MIMEText
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
DEFAULT_DAILY_CAP = 20


def _get_gmail_credentials() -> Credentials:
    """Load Gmail OAuth credentials from file or base64 env var."""
    b64 = os.environ.get("GMAIL_TOKEN_B64")
    if b64:
        raw = base64.b64decode(b64)
        info = json.loads(raw)
        creds = Credentials.from_authorized_user_info(info, SCOPES)
    else:
        token_path = Path("gmail_token.json")
        if not token_path.exists():
            raise FileNotFoundError(
                "No Gmail token found. Set GMAIL_TOKEN_B64 or place gmail_token.json in project root."
            )
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return creds


class GmailSender:
    """Send emails via Gmail API with daily cap enforcement."""

    def __init__(self, sender_email: str | None = None, daily_cap: int = DEFAULT_DAILY_CAP):
        self.sender_email = sender_email or os.environ.get("GMAIL_SENDER_EMAIL", "")
        if not self.sender_email:
            raise ValueError("GMAIL_SENDER_EMAIL is required.")
        self.daily_cap = daily_cap
        self._sent_count = 0
        creds = _get_gmail_credentials()
        self.service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    @property
    def can_send(self) -> bool:
        """Check if we're under the daily send cap."""
        return self._sent_count < self.daily_cap

    @property
    def sent_count(self) -> int:
        return self._sent_count

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
    ) -> dict:
        """
        Send an email via Gmail API.

        Returns a dict with 'status' (SENT/FAILED) and 'message_id' or 'error'.
        """
        if not self.can_send:
            logger.warning("Daily email cap (%d) reached. Skipping send to %s.", self.daily_cap, to_email)
            return {"status": "SKIPPED", "error": f"Daily cap of {self.daily_cap} reached"}

        msg = MIMEText(body, "plain")
        msg["to"] = to_email
        msg["from"] = self.sender_email
        msg["subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

        try:
            result = self.service.users().messages().send(
                userId="me",
                body={"raw": raw},
            ).execute()

            self._sent_count += 1
            message_id = result.get("id", "")
            logger.info("Email sent to %s (id: %s). Count: %d/%d", to_email, message_id, self._sent_count, self.daily_cap)
            return {"status": "SENT", "message_id": message_id}

        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, e)
            return {"status": "FAILED", "error": str(e)}
