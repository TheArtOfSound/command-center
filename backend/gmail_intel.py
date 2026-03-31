"""Gmail intelligence — read, search, and analyze Bryan's emails."""

import base64
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

DATA_DIR = Path.home() / "qira" / "command_center" / "data"
TOKEN_FILE = DATA_DIR / "gmail_token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _get_service():
    """Get authenticated Gmail service."""
    if not TOKEN_FILE.exists():
        return None

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())

    if not creds or not creds.valid:
        return None

    return build("gmail", "v1", credentials=creds)


def _decode_body(payload):
    """Extract text body from email payload."""
    body = ""
    if payload.get("body", {}).get("data"):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    elif payload.get("parts"):
        for part in payload["parts"]:
            mime = part.get("mimeType", "")
            if mime == "text/plain" and part.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                break
            elif mime == "text/html" and not body and part.get("body", {}).get("data"):
                raw = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                body = re.sub(r"<[^>]+>", " ", raw)  # Strip HTML
            elif part.get("parts"):
                body = _decode_body(part)
                if body:
                    break
    return body.strip()


def _parse_headers(headers):
    """Extract useful headers."""
    result = {}
    for h in headers:
        name = h.get("name", "").lower()
        if name in ("from", "to", "subject", "date", "cc", "reply-to"):
            result[name] = h.get("value", "")
    return result


def get_profile():
    """Get Gmail profile info."""
    svc = _get_service()
    if not svc:
        return {"error": "Gmail not connected. Run: python3 backend/gmail_setup.py"}
    try:
        return svc.users().getProfile(userId="me").execute()
    except Exception as e:
        return {"error": str(e)}


def get_labels():
    """Get all labels."""
    svc = _get_service()
    if not svc:
        return []
    try:
        result = svc.users().labels().list(userId="me").execute()
        return result.get("labels", [])
    except:
        return []


def search_emails(query: str, max_results: int = 20):
    """Search Gmail with any Gmail search query."""
    svc = _get_service()
    if not svc:
        return {"error": "Gmail not connected", "messages": []}

    try:
        result = svc.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = []
        for msg_ref in result.get("messages", []):
            msg = svc.users().messages().get(
                userId="me", id=msg_ref["id"], format="full"
            ).execute()

            headers = _parse_headers(msg.get("payload", {}).get("headers", []))
            body = _decode_body(msg.get("payload", {}))

            messages.append({
                "id": msg["id"],
                "thread_id": msg.get("threadId", ""),
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "subject": headers.get("subject", ""),
                "date": headers.get("date", ""),
                "snippet": msg.get("snippet", ""),
                "body_preview": body[:500] if body else "",
                "labels": msg.get("labelIds", []),
                "is_unread": "UNREAD" in msg.get("labelIds", []),
            })

        return {
            "query": query,
            "total_results": result.get("resultSizeEstimate", 0),
            "messages": messages,
        }
    except Exception as e:
        return {"error": str(e), "messages": []}


def get_recent_emails(max_results: int = 20):
    """Get most recent emails."""
    return search_emails("", max_results)


def get_unread_count():
    """Get unread email count."""
    svc = _get_service()
    if not svc:
        return {"error": "Gmail not connected", "unread": 0}

    try:
        result = svc.users().messages().list(
            userId="me", q="is:unread", maxResults=1
        ).execute()
        return {"unread": result.get("resultSizeEstimate", 0)}
    except Exception as e:
        return {"error": str(e), "unread": 0}


def get_email_by_id(msg_id: str):
    """Get full email by ID."""
    svc = _get_service()
    if not svc:
        return {"error": "Gmail not connected"}

    try:
        msg = svc.users().messages().get(
            userId="me", id=msg_id, format="full"
        ).execute()

        headers = _parse_headers(msg.get("payload", {}).get("headers", []))
        body = _decode_body(msg.get("payload", {}))

        return {
            "id": msg["id"],
            "thread_id": msg.get("threadId", ""),
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "cc": headers.get("cc", ""),
            "subject": headers.get("subject", ""),
            "date": headers.get("date", ""),
            "body": body,
            "snippet": msg.get("snippet", ""),
            "labels": msg.get("labelIds", []),
        }
    except Exception as e:
        return {"error": str(e)}


def get_emails_from(sender: str, max_results: int = 10):
    """Get emails from a specific sender."""
    return search_emails(f"from:{sender}", max_results)


def get_emails_about(topic: str, max_results: int = 10):
    """Search emails about a topic."""
    return search_emails(topic, max_results)


def analyze_inbox_summary():
    """Generate a summary of the inbox state."""
    svc = _get_service()
    if not svc:
        return {"error": "Gmail not connected"}

    try:
        # Unread count
        unread = svc.users().messages().list(
            userId="me", q="is:unread", maxResults=1
        ).execute().get("resultSizeEstimate", 0)

        # Today's emails
        today = datetime.now().strftime("%Y/%m/%d")
        today_msgs = svc.users().messages().list(
            userId="me", q=f"after:{today}", maxResults=50
        ).execute()
        today_count = today_msgs.get("resultSizeEstimate", 0)

        # Important / starred
        starred = svc.users().messages().list(
            userId="me", q="is:starred", maxResults=1
        ).execute().get("resultSizeEstimate", 0)

        # Recent important senders
        recent = svc.users().messages().list(
            userId="me", q="is:unread", maxResults=10
        ).execute()

        unread_subjects = []
        senders = []
        for msg_ref in recent.get("messages", []):
            msg = svc.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "Subject"]
            ).execute()
            headers = _parse_headers(msg.get("payload", {}).get("headers", []))
            unread_subjects.append(headers.get("subject", ""))
            senders.append(headers.get("from", ""))

        # Check for Aronson
        aronson_emails = svc.users().messages().list(
            userId="me", q="from:aronson OR subject:aronson", maxResults=5
        ).execute()
        has_aronson = aronson_emails.get("resultSizeEstimate", 0) > 0

        return {
            "unread": unread,
            "today": today_count,
            "starred": starred,
            "unread_subjects": unread_subjects[:10],
            "recent_senders": list(set(senders[:10])),
            "has_aronson_email": has_aronson,
            "aronson_count": aronson_emails.get("resultSizeEstimate", 0),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}
