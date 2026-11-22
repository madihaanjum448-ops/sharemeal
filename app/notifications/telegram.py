"""Alert senders (Member 2). A sender returns True only if it delivered.

Telegram is used only when TELEGRAM_BOT_TOKEN is set and the receiver has a
row in receiver_telegram_links. The token is never logged: failures are
recorded by exception type only (see deliver_to_receiver).
"""
import os
from typing import Any, Dict, List

import httpx

from app.notifications.service import Channel

TELEGRAM_API = "https://api.telegram.org"


def make_telegram_sender(client: Any, token: str, base_url: str = ""):
    def send(receiver: Dict[str, Any], payload: Dict[str, Any]) -> bool:
        rows = (
            client.table("receiver_telegram_links")
            .select("chat_id")
            .eq("receiver_id", receiver.get("id"))
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            return False                          # not linked: fall through to the next channel
        text = "%s\n%s" % (payload["title"], payload["body"])
        if base_url:
            text += "\n" + base_url.rstrip("/") + payload["url"]
        response = httpx.post(
            "%s/bot%s/sendMessage" % (TELEGRAM_API, token),
            json={"chat_id": rows[0]["chat_id"], "text": text},
            timeout=5.0,
        )
        return response.status_code == 200

    return send


def in_app_sender(receiver: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    """Record-only channel: the alert is stored and read by GET /receivers/me/alerts."""
    return True


def build_channels(client: Any) -> List[Channel]:
    channels: List[Channel] = []
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if token:
        channels.append(("telegram", make_telegram_sender(client, token, os.getenv("APP_BASE_URL", "").strip())))
    channels.append(("in_app", in_app_sender))
    return channels
