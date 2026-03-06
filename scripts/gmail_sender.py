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

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]
DEFAULT_DAILY_CAP = 20


def _plain_to_html(text: str) -> str:
    """Convert plain text email to clean HTML with proper paragraph spacing."""
    import html as html_module
    text = html_module.escape(text)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    body_html = ""
    for p in paragraphs:
        # Preserve single line breaks within a paragraph (e.g., sign-off block)
        p = p.replace("\n", "<br>")
        body_html += f'<p style="margin:0 0 16px 0;line-height:1.5">{p}</p>\n'
    return f"""<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#333">{body_html}</div>"""


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

        # Convert plain text to HTML for proper formatting
        html_body = _plain_to_html(body)
        msg = MIMEText(html_body, "html")
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

    def get_replies(self, prospect_emails: list[str], since_hours: int = 48) -> list[dict]:
        """
        Check inbox for replies from prospect emails.

        Returns list of dicts: {from_email, subject, body, message_id, date}
        Only returns emails received in the last `since_hours` hours.
        """
        from datetime import datetime, timedelta, timezone
        import email.utils

        cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        replies: list[dict] = []

        for prospect_email in prospect_emails:
            try:
                result = self.service.users().messages().list(
                    userId="me",
                    q=f"from:{prospect_email} is:inbox",
                    maxResults=5,
                ).execute()

                for msg_meta in result.get("messages", []):
                    msg = self.service.users().messages().get(
                        userId="me", id=msg_meta["id"], format="full",
                    ).execute()
                    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}

                    # Check date
                    date_str = headers.get("Date", "")
                    if date_str:
                        parsed = email.utils.parsedate_to_datetime(date_str)
                        if parsed.tzinfo is None:
                            parsed = parsed.replace(tzinfo=timezone.utc)
                        if parsed < cutoff:
                            continue

                    # Extract plain text body
                    body = self._extract_body(msg["payload"])

                    # Strip quoted reply (everything after "On ... wrote:")
                    clean_body = self._strip_quoted_reply(body)

                    replies.append({
                        "from_email": prospect_email,
                        "subject": headers.get("Subject", ""),
                        "body": clean_body.strip(),
                        "message_id": msg_meta["id"],
                        "date": date_str,
                    })

            except Exception as e:
                logger.error("Failed to check replies from %s: %s", prospect_email, e)

        return replies

    @staticmethod
    def _extract_body(payload: dict) -> str:
        """Extract plain text body from Gmail message payload."""
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                    return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        elif "body" in payload and "data" in payload["body"]:
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        return ""

    @staticmethod
    def _strip_quoted_reply(text: str) -> str:
        """Remove quoted original email from a reply (everything after 'On ... wrote:')."""
        import re
        # Match "On <date>, <email> wrote:" pattern
        match = re.search(r"\nOn .+wrote:\s*$", text, re.MULTILINE | re.DOTALL)
        if match:
            return text[:match.start()]
        return text
