"""
EXAMPLE: Notion DB に書き込むシンプルなフォーム。

main.py の中身を以下に置き換えると、`/form` で HTML フォームが見えて、
POST すると Notion の Invoice DB に新規ページを作る。

前提:
- sandbox.yaml の data.notion に Invoice DB の id を入れる
- Notion 側で Integration を該当 DB に Connect する
- Secret Manager に app--<owner>--<app>--notion-token を入れる
"""
import os
from typing import Annotated

from fastapi import FastAPI, Form, Header
from fastapi.responses import HTMLResponse, RedirectResponse

from sdks.notion_db import client as notion_client

INVOICE_DB_ID = os.environ.get("NOTION_DB_INVOICE", "REPLACE-ME-WITH-INVOICE-DB-ID")

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def form_page(x_auth_request_email: Annotated[str | None, Header()] = None):
    return f"""
<!doctype html>
<title>請求書フォーム</title>
<style>
  body {{ font-family: system-ui; max-width: 480px; margin: 3rem auto; padding: 0 1rem; }}
  label {{ display: block; margin: 1em 0 0.3em; font-weight: bold; }}
  input, textarea {{ width: 100%; padding: .5em; font-size: 1em; }}
  button {{ margin-top: 1.5em; padding: .7em 1.5em; font-size: 1em; }}
</style>
<h1>請求書を作成</h1>
<p style="color:#666">作成者: {x_auth_request_email}</p>
<form method="post" action="/submit">
  <label>顧客名</label>
  <input name="customer" required>
  <label>金額（円）</label>
  <input name="amount" type="number" required>
  <label>メモ</label>
  <textarea name="memo" rows="3"></textarea>
  <button type="submit">作成</button>
</form>
"""


@app.post("/submit")
def submit(
    customer: Annotated[str, Form()],
    amount: Annotated[int, Form()],
    memo: Annotated[str, Form()] = "",
    x_auth_request_email: Annotated[str | None, Header()] = None,
):
    n = notion_client()
    n.create_page(
        INVOICE_DB_ID,
        {
            "Customer": {"title": [{"text": {"content": customer}}]},
            "Amount": {"number": amount},
            "Memo": {"rich_text": [{"text": {"content": memo}}]},
            "Created by": {"rich_text": [{"text": {"content": x_auth_request_email or ""}}]},
            "Status": {"select": {"name": "Ready to send"}},
        },
    )
    return RedirectResponse("/?ok=1", status_code=302)
