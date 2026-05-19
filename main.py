"""
Sandbox app starter — FastAPI.

Edit this file freely. The route handlers below are example patterns;
delete what you don't need and add your own.

The X-Auth-Request-Email header is injected by the sandbox-router (oauth2-proxy)
and tells you who the signed-in user is.
"""
from __future__ import annotations

import os
from typing import Annotated

from fastapi import FastAPI, Header, Request
from fastapi.responses import HTMLResponse

app = FastAPI(title=os.environ.get("APP_NAME", "sandbox app"))


@app.get("/health")
def health() -> dict[str, str]:
    # NOTE: must NOT use /healthz — Cloud Run/Knative edge reserves that path.
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def root(x_auth_request_email: Annotated[str | None, Header()] = None) -> str:
    email = x_auth_request_email or "(unknown)"
    return f"""
<!doctype html>
<meta charset="utf-8">
<title>{app.title}</title>
<style>
  body {{ font-family: system-ui; max-width: 720px; margin: 4rem auto; padding: 0 1rem; }}
  .who {{ color: #555; font-size: 0.9em; }}
</style>
<h1>Hello, sandbox 🐍</h1>
<p>このページが見えていれば、Python サンドボックスは動いています。</p>
<p class="who">signed in as <code>{email}</code></p>
"""


# --- Example data patterns. Uncomment + customize as needed. ---
#
# from sdks.notion_db import client as notion_client
#
# @app.get("/customers")
# def list_customers():
#     n = notion_client()  # reads NOTION_TOKEN from env
#     rows = n.query(os.environ["NOTION_DB_CUSTOMER"])
#     return [{"id": r["id"], "name": r["properties"]["Name"]["title"][0]["plain_text"]} for r in rows]
#
#
# from sdks.sandbox_db import client as fs_client
#
# @app.post("/notes")
# def add_note(text: str):
#     db = fs_client()  # auto-scoped to apps/<owner>--<app>/
#     ref = db.collection("notes").add({"text": text})
#     return {"id": ref[1].id}
