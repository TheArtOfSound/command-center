"""Gmail API setup — run this once to authorize.

Usage:
  python3 gmail_setup.py

This will:
1. Open a browser for Google OAuth consent
2. Save the token to ~/qira/command_center/data/gmail_token.json
3. After that, the command center can read Gmail without user interaction

Prerequisites:
  1. Go to https://console.cloud.google.com/apis/credentials
  2. Create OAuth 2.0 Client ID (Desktop application)
  3. Download the JSON file
  4. Save it as ~/qira/command_center/data/gmail_credentials.json
"""

import os
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

DATA_DIR = Path.home() / "qira" / "command_center" / "data"
CREDS_FILE = DATA_DIR / "gmail_credentials.json"
TOKEN_FILE = DATA_DIR / "gmail_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
]


def authenticate():
    """Run OAuth flow and save token."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_FILE.exists():
                print(f"\nERROR: No credentials file found at {CREDS_FILE}")
                print("\nTo set up Gmail API access:")
                print("1. Go to https://console.cloud.google.com/apis/credentials")
                print("2. Click '+ CREATE CREDENTIALS' → 'OAuth client ID'")
                print("3. Application type: 'Desktop app'")
                print("4. Download the JSON file")
                print(f"5. Save it as: {CREDS_FILE}")
                print("6. Run this script again\n")
                return None

            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=8090)

        TOKEN_FILE.write_text(creds.to_json())
        print(f"Token saved to {TOKEN_FILE}")

    # Test it
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    print(f"\nAuthenticated as: {profile.get('emailAddress')}")
    print(f"Total messages: {profile.get('messagesTotal')}")
    print(f"Total threads: {profile.get('threadsTotal')}")

    return creds


if __name__ == "__main__":
    print("Gmail API Setup for Qira Command Center\n")
    authenticate()
