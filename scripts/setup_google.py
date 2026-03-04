"""
Google API Setup Helper

Automates the Gmail OAuth flow and verifies Google Sheets access.
Run this once after placing your google_credentials.json in the project root.
"""

import json
import os
from pathlib import Path

from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

PROJECT_ROOT = Path(__file__).parent.parent
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def setup_sheets():
    """Verify Google Sheets service account access."""
    cred_path = PROJECT_ROOT / "google_credentials.json"
    if not cred_path.exists():
        print("\n[SHEETS] google_credentials.json not found in project root.")
        print("Steps to create it:")
        print("  1. Go to https://console.cloud.google.com/")
        print("  2. Create a new project (or select existing)")
        print("  3. Enable 'Google Sheets API' (search in API Library)")
        print("  4. Go to IAM & Admin > Service Accounts")
        print("  5. Create Service Account > Create Key (JSON)")
        print("  6. Save the downloaded file as 'google_credentials.json' here:")
        print(f"     {PROJECT_ROOT}")
        return False

    creds = ServiceAccountCredentials.from_service_account_file(
        str(cred_path), scopes=SHEETS_SCOPES
    )
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)

    print(f"\n[SHEETS] Service account email: {creds.service_account_email}")
    print("[SHEETS] Share your Google Sheet with this email address!")

    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
    if sheet_id:
        try:
            result = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            print(f"[SHEETS] Connected to: {result['properties']['title']}")
            return True
        except Exception as e:
            print(f"[SHEETS] ERROR accessing sheet: {e}")
            print("[SHEETS] Make sure you shared the sheet with the service account email above.")
            return False
    else:
        print("[SHEETS] Set GOOGLE_SHEET_ID env var to test sheet access.")
        return True


def setup_gmail():
    """Run Gmail OAuth flow to generate gmail_token.json."""
    token_path = PROJECT_ROOT / "gmail_token.json"
    oauth_creds_path = PROJECT_ROOT / "gmail_oauth_credentials.json"

    # Check if token already exists
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), GMAIL_SCOPES)
        if creds and creds.valid:
            print("\n[GMAIL] gmail_token.json exists and is valid.")
            return True
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json(), encoding="utf-8")
            print("\n[GMAIL] Token refreshed successfully.")
            return True

    if not oauth_creds_path.exists():
        print("\n[GMAIL] gmail_oauth_credentials.json not found.")
        print("Steps to create it:")
        print("  1. Go to https://console.cloud.google.com/")
        print("  2. Same project as Sheets — enable 'Gmail API'")
        print("  3. Go to APIs & Services > Credentials")
        print("  4. Create Credentials > OAuth client ID")
        print("  5. Application type: Desktop app")
        print("  6. Download the JSON and save as 'gmail_oauth_credentials.json' here:")
        print(f"     {PROJECT_ROOT}")
        return False

    print("\n[GMAIL] Starting OAuth flow... A browser will open.")
    print("Grant permission to send emails on your behalf.")

    flow = InstalledAppFlow.from_client_secrets_file(str(oauth_creds_path), GMAIL_SCOPES)
    creds = flow.run_local_server(port=0)

    token_path.write_text(creds.to_json(), encoding="utf-8")
    print(f"[GMAIL] Token saved to: {token_path}")

    # Verify
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    profile = service.users().getProfile(userId="me").execute()
    print(f"[GMAIL] Authenticated as: {profile['emailAddress']}")
    return True


def create_sheet_structure():
    """Create the 4-tab structure in a new or existing Google Sheet."""
    cred_path = PROJECT_ROOT / "google_credentials.json"
    if not cred_path.exists():
        print("\n[SHEET SETUP] Need google_credentials.json first.")
        return

    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
    if not sheet_id:
        print("\n[SHEET SETUP] Set GOOGLE_SHEET_ID env var first.")
        return

    creds = ServiceAccountCredentials.from_service_account_file(
        str(cred_path), scopes=SHEETS_SCOPES
    )
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    sheets = service.spreadsheets()

    # Define tab structures
    tabs = {
        "Prospects": ["name", "company", "title", "linkedin_url", "email", "status", "notes"],
        "Targets": ["post_url", "topic", "priority", "status"],
        "Inbound": ["sender_name", "sender_url", "message_text", "received_at", "status"],
        "Activities": ["timestamp_utc", "channel", "activity_type", "prospect_name", "status", "sent_at", "draft_text", "evidence_snippets"],
    }

    # Get existing tabs
    try:
        spreadsheet = sheets.get(spreadsheetId=sheet_id).execute()
    except Exception as e:
        print(f"\n[SHEET SETUP] Cannot access sheet: {e}")
        return

    existing_tabs = {s["properties"]["title"] for s in spreadsheet["sheets"]}

    # Create missing tabs
    requests_list = []
    for tab_name in tabs:
        if tab_name not in existing_tabs:
            requests_list.append({
                "addSheet": {"properties": {"title": tab_name}}
            })

    if requests_list:
        sheets.batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": requests_list},
        ).execute()
        print(f"\n[SHEET SETUP] Created tabs: {[r['addSheet']['properties']['title'] for r in requests_list]}")

    # Write headers
    for tab_name, headers in tabs.items():
        sheets.values().update(
            spreadsheetId=sheet_id,
            range=f"{tab_name}!A1:{chr(64 + len(headers))}1",
            valueInputOption="RAW",
            body={"values": [headers]},
        ).execute()

    print("[SHEET SETUP] All tabs created with headers!")
    print(f"[SHEET SETUP] Sheet URL: https://docs.google.com/spreadsheets/d/{sheet_id}/edit")


def main():
    print("=" * 50)
    print("Google API Setup Helper")
    print("=" * 50)

    sheets_ok = setup_sheets()
    gmail_ok = setup_gmail()

    if sheets_ok and os.environ.get("GOOGLE_SHEET_ID"):
        print("\n--- Setting up Sheet structure ---")
        create_sheet_structure()

    print("\n" + "=" * 50)
    print("Summary:")
    print(f"  Sheets: {'OK' if sheets_ok else 'NEEDS SETUP'}")
    print(f"  Gmail:  {'OK' if gmail_ok else 'NEEDS SETUP'}")
    print("=" * 50)


if __name__ == "__main__":
    main()
