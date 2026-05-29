"""
Lightweight Slack Web API client. No external dep beyond httpx.

Usage:
    from sdks.slack import client
    s = client()                                  # reads SLACK_BOT_TOKEN from env
    s.post("#aiの里", "おはようございます")
    s.dm("urara@plaize.co", "今日のタスクは 3件です")

The SLACK_BOT_TOKEN env var is wired by the deploy workflow if your sandbox.yaml
declares `data.slack: true`. The shared `plaize-assistant` token in Secret
Manager (`sandbox-slack-bot-token`) is mounted into the container.

The bot name / avatar is shared across all sandbox apps. If you need a custom
bot name per app, create a separate Slack App in admin UI and store its token
under `app--<owner>--<app>--slack-token` (then ask Urara to wire it).

The bot needs to be invited to the target channel first (Slack UI → channel →
"+ Add apps" → plaize-assistant).
"""
from __future__ import annotations

import os
from typing import Any

import httpx

SLACK_API_BASE = "https://slack.com/api"


class Slack:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.environ.get("SLACK_BOT_TOKEN")
        if not self.token:
            raise RuntimeError(
                "SLACK_BOT_TOKEN env var or token arg required. "
                "Add `data.slack: true` to sandbox.yaml so the deploy workflow "
                "mounts the shared plaize-assistant token."
            )
        self._client = httpx.Client(
            base_url=SLACK_API_BASE,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=15,
        )

    def post(self, channel: str, text: str, **kwargs: Any) -> dict[str, Any]:
        """Post a message to a channel.

        channel: channel name with `#` prefix (e.g. "#aiの里") or channel ID (e.g. "C0AHU8T239C").
        kwargs: any extra Slack chat.postMessage parameters (blocks, thread_ts, etc.).
        """
        payload = {"channel": channel, "text": text, **kwargs}
        resp = self._client.post("/chat.postMessage", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack post failed: {data.get('error')}")
        return data

    def dm(self, email: str, text: str, **kwargs: Any) -> dict[str, Any]:
        """Send a direct message to a user identified by their email.

        Requires the `users:read.email` scope on the bot.
        """
        lookup = self._client.get("/users.lookupByEmail", params={"email": email})
        lookup.raise_for_status()
        data = lookup.json()
        if not data.get("ok"):
            raise RuntimeError(f"users.lookupByEmail failed for {email}: {data.get('error')}")
        user_id = data["user"]["id"]

        opened = self._client.post("/conversations.open", json={"users": user_id})
        opened.raise_for_status()
        odata = opened.json()
        if not odata.get("ok"):
            raise RuntimeError(f"conversations.open failed: {odata.get('error')}")
        channel_id = odata["channel"]["id"]

        return self.post(channel_id, text, **kwargs)


def client(token: str | None = None) -> Slack:
    return Slack(token=token)
