"""
Lightweight Notion API client. No external dep beyond httpx.

Usage:
    from sdks.notion_db import client
    n = client()                                  # reads NOTION_TOKEN from env
    rows = n.query(os.environ["NOTION_DB_CUSTOMER"])
    n.create_page(db_id, {
        "Name": {"title": [{"text": {"content": "Alice"}}]},
        "Status": {"select": {"name": "Active"}},
    })

The NOTION_TOKEN env var is wired by the deploy workflow if your sandbox.yaml
declares `data.notion` and the corresponding Notion Integration's token is
stored in Secret Manager as `app--<owner>--<app>--notion-token`.

You also need to share the Notion DB with the Integration (Notion UI → DB →
"... menu" → "+ Add connections" → select the Integration).
"""
from __future__ import annotations

import os
from typing import Any

import httpx

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionDB:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.environ.get("NOTION_TOKEN")
        if not self.token:
            raise RuntimeError(
                "NOTION_TOKEN env var or token arg required. "
                "Add `data.notion` to sandbox.yaml and store the Integration "
                "token in Secret Manager as app--<owner>--<app>--notion-token."
            )
        self._client = httpx.Client(
            base_url=NOTION_API_BASE,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            timeout=15,
        )

    def query(
        self,
        db_id: str,
        *,
        filter: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """Query a Notion database. Returns the list of pages (rows)."""
        body: dict[str, Any] = {"page_size": min(page_size, 100)}
        if filter:
            body["filter"] = filter
        if sorts:
            body["sorts"] = sorts
        resp = self._client.post(f"/databases/{db_id}/query", json=body)
        resp.raise_for_status()
        return resp.json().get("results", [])

    def create_page(self, db_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Create a new page (row) in the given database."""
        resp = self._client.post(
            "/pages",
            json={
                "parent": {"database_id": db_id},
                "properties": properties,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def update_page(self, page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Update properties on an existing page."""
        resp = self._client.patch(f"/pages/{page_id}", json={"properties": properties})
        resp.raise_for_status()
        return resp.json()

    def get_database(self, db_id: str) -> dict[str, Any]:
        """Fetch DB schema (for inferring property names/types)."""
        resp = self._client.get(f"/databases/{db_id}")
        resp.raise_for_status()
        return resp.json()


def client(token: str | None = None) -> NotionDB:
    return NotionDB(token=token)
