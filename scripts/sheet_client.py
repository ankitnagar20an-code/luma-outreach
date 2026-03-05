"""Google Sheets client for reading prospects/targets/inbound and writing activities."""

from __future__ import annotations

import json
import os
import base64
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

TAB_PROSPECTS = "Prospects"
TAB_TARGETS = "Targets"
TAB_INBOUND = "Inbound"
TAB_ACTIVITIES = "Activities"

PROSPECT_COLUMNS = [
    "name", "company", "title", "linkedin_url", "email", "status", "notes",
    "icp", "sequence_stage", "last_email_date", "reply_status", "dnc",
]
TARGET_COLUMNS = ["post_url", "topic", "priority", "status"]
INBOUND_COLUMNS = [
    "sender_name", "sender_url", "message_text", "received_at", "status",
    "prospect_email", "reply_text",
]
ACTIVITY_COLUMNS = [
    "timestamp_utc", "channel", "activity_type", "prospect_name",
    "status", "sent_at", "draft_text", "evidence_snippets",
]


def _get_credentials() -> Credentials:
    """Load Google credentials from file or base64 env var."""
    b64 = os.environ.get("GOOGLE_CREDENTIALS_B64")
    if b64:
        raw = base64.b64decode(b64)
        info = json.loads(raw)
        return Credentials.from_service_account_info(info, scopes=SCOPES)

    cred_path = Path("google_credentials.json")
    if cred_path.exists():
        return Credentials.from_service_account_file(str(cred_path), scopes=SCOPES)

    raise FileNotFoundError(
        "No Google credentials found. Set GOOGLE_CREDENTIALS_B64 or place google_credentials.json in project root."
    )


class SheetClient:
    """Read and write to the Luma Outreach Google Sheet."""

    def __init__(self, sheet_id: str | None = None):
        self.sheet_id = sheet_id or os.environ["GOOGLE_SHEET_ID"]
        creds = _get_credentials()
        service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        self.sheets = service.spreadsheets()

    def _read_tab(self, tab: str, columns: list[str]) -> list[dict[str, str]]:
        """Read all rows from a tab and return as list of dicts."""
        result = self.sheets.values().get(
            spreadsheetId=self.sheet_id,
            range=f"{tab}!A2:Z",  # skip header row
        ).execute()
        rows = result.get("values", [])
        records = []
        for row in rows:
            # Pad short rows with empty strings
            padded = row + [""] * (len(columns) - len(row))
            records.append(dict(zip(columns, padded[:len(columns)])))
        return records

    def get_prospects(self, status_filter: str = "active") -> list[dict[str, str]]:
        """Get prospects filtered by status."""
        all_prospects = self._read_tab(TAB_PROSPECTS, PROSPECT_COLUMNS)
        if status_filter:
            return [p for p in all_prospects if p.get("status", "").lower() == status_filter.lower()]
        return all_prospects

    def get_targets(self, status_filter: str = "active") -> list[dict[str, str]]:
        """Get target posts/topics filtered by status."""
        all_targets = self._read_tab(TAB_TARGETS, TARGET_COLUMNS)
        if status_filter:
            return [t for t in all_targets if t.get("status", "").lower() == status_filter.lower()]
        return all_targets

    def get_inbound(self, status_filter: str = "new") -> list[dict[str, str]]:
        """Get inbound messages filtered by status."""
        all_inbound = self._read_tab(TAB_INBOUND, INBOUND_COLUMNS)
        if status_filter:
            return [i for i in all_inbound if i.get("status", "").lower() == status_filter.lower()]
        return all_inbound

    def log_activity(
        self,
        channel: str,
        activity_type: str,
        prospect_name: str,
        status: str,
        draft_text: str,
        evidence_snippets: list[str] | None = None,
    ) -> None:
        """Append a row to the Activities tab."""
        now = datetime.now(timezone.utc)
        row = [
            now.isoformat(),                           # timestamp_utc
            channel,                                    # channel
            activity_type,                              # activity_type
            prospect_name,                              # prospect_name
            status,                                     # status (SENT/FAILED/SKIPPED)
            now.isoformat() if status == "SENT" else "",  # sent_at
            draft_text,                                 # draft_text
            json.dumps(evidence_snippets or []),        # evidence_snippets
        ]
        self.sheets.values().append(
            spreadsheetId=self.sheet_id,
            range=f"{TAB_ACTIVITIES}!A:H",
            valueInputOption="RAW",
            body={"values": [row]},
        ).execute()
        logger.info("Logged activity: %s / %s / %s -> %s", channel, activity_type, prospect_name, status)

    def update_cell(self, tab: str, row_index: int, col_index: int, value: str) -> None:
        """Update a single cell. row_index and col_index are 0-based (data area, not header)."""
        # Convert to A1 notation: row_index+2 because row 1 is header
        col_letter = chr(ord("A") + col_index)
        cell = f"{tab}!{col_letter}{row_index + 2}"
        self.sheets.values().update(
            spreadsheetId=self.sheet_id,
            range=cell,
            valueInputOption="RAW",
            body={"values": [[value]]},
        ).execute()

    def update_prospect_sequence(
        self,
        prospect_email: str,
        sequence_stage: int,
        last_email_date: str,
        reply_status: str | None = None,
        dnc: str | None = None,
    ) -> bool:
        """Update sequence tracking columns for a prospect identified by email."""
        result = self.sheets.values().get(
            spreadsheetId=self.sheet_id,
            range=f"{TAB_PROSPECTS}!A2:L",
        ).execute()
        rows = result.get("values", [])

        for idx, row in enumerate(rows):
            padded = row + [""] * (12 - len(row))
            if padded[4].strip().lower() == prospect_email.strip().lower():
                sheet_row = idx + 2
                updates = [
                    {"range": f"{TAB_PROSPECTS}!I{sheet_row}", "values": [[str(sequence_stage)]]},
                    {"range": f"{TAB_PROSPECTS}!J{sheet_row}", "values": [[last_email_date]]},
                ]
                if reply_status is not None:
                    updates.append({"range": f"{TAB_PROSPECTS}!K{sheet_row}", "values": [[reply_status]]})
                if dnc is not None:
                    updates.append({"range": f"{TAB_PROSPECTS}!L{sheet_row}", "values": [[dnc]]})

                self.sheets.values().batchUpdate(
                    spreadsheetId=self.sheet_id,
                    body={"valueInputOption": "RAW", "data": updates},
                ).execute()
                logger.info("Updated sequence for %s: stage=%d, date=%s", prospect_email, sequence_stage, last_email_date)
                return True

        logger.warning("Prospect with email %s not found in sheet", prospect_email)
        return False

    def update_prospect_reply_status(
        self,
        prospect_email: str,
        reply_status: str,
        dnc: str = "",
    ) -> bool:
        """Update reply_status and optional dnc flag for a prospect."""
        result = self.sheets.values().get(
            spreadsheetId=self.sheet_id,
            range=f"{TAB_PROSPECTS}!A2:L",
        ).execute()
        rows = result.get("values", [])

        for idx, row in enumerate(rows):
            padded = row + [""] * (12 - len(row))
            if padded[4].strip().lower() == prospect_email.strip().lower():
                sheet_row = idx + 2
                updates = [{"range": f"{TAB_PROSPECTS}!K{sheet_row}", "values": [[reply_status]]}]
                if dnc:
                    updates.append({"range": f"{TAB_PROSPECTS}!L{sheet_row}", "values": [[dnc]]})
                self.sheets.values().batchUpdate(
                    spreadsheetId=self.sheet_id,
                    body={"valueInputOption": "RAW", "data": updates},
                ).execute()
                logger.info("Updated reply_status for %s: %s (dnc=%s)", prospect_email, reply_status, dnc)
                return True

        logger.warning("Prospect with email %s not found for reply update", prospect_email)
        return False

    def get_inbound_replies(self) -> list[dict[str, str]]:
        """Get unprocessed inbound email replies (rows with prospect_email + reply_text)."""
        all_inbound = self._read_tab(TAB_INBOUND, INBOUND_COLUMNS)
        return [
            row for row in all_inbound
            if row.get("prospect_email")
            and row.get("reply_text")
            and row.get("status", "").lower() != "processed"
        ]

    def mark_inbound_processed(self, prospect_email: str) -> None:
        """Mark an inbound reply row as processed by prospect_email match."""
        result = self.sheets.values().get(
            spreadsheetId=self.sheet_id,
            range=f"{TAB_INBOUND}!A2:G",
        ).execute()
        rows = result.get("values", [])
        email_col_idx = INBOUND_COLUMNS.index("prospect_email")
        status_col_letter = chr(ord("A") + INBOUND_COLUMNS.index("status"))

        for idx, row in enumerate(rows):
            padded = row + [""] * (len(INBOUND_COLUMNS) - len(row))
            if padded[email_col_idx].strip().lower() == prospect_email.strip().lower():
                sheet_row = idx + 2
                self.sheets.values().update(
                    spreadsheetId=self.sheet_id,
                    range=f"{TAB_INBOUND}!{status_col_letter}{sheet_row}",
                    valueInputOption="RAW",
                    body={"values": [["processed"]]},
                ).execute()
                return
