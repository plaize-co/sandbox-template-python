"""
EXAMPLE: Firestore に回答を保存するシンプルな社内アンケート。

main.py の中身を以下に置き換えると:
  GET /     → アンケートフォームを表示
  POST /    → 回答を Firestore に保存
  GET /results → 全回答を一覧表示 (管理者向け)

Firestore のデータ構造:
  apps/{owner}--{app}/responses/{auto-id}
    └ { "email": str, "q1": str, "q2": str, "submitted_at": datetime }

前提:
- sandbox.yaml に `data:\n  firestore: true` を追加する
- 上記を追加した状態で sandbox_new or sandbox_notion_connect を実行すると
  per-app SA に roles/datastore.user が自動付与される

使い方 (sandbox.yaml):
    data:
      firestore: true

質問文は QUESTIONS リストを書き換えてカスタマイズ。
"""
import datetime
from typing import Annotated

from fastapi import FastAPI, Form, Header, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from sdks.sandbox_db import client as db_client

# ← ここを好きな質問に書き換える
QUESTIONS = [
    {"key": "q1", "label": "今週のランチ、どこにしたい？", "type": "radio",
     "options": ["近くのカフェ", "デリバリー", "弁当持参", "まだ決めてない"]},
    {"key": "q2", "label": "来月の社内イベント、参加できますか？", "type": "radio",
     "options": ["参加できる", "たぶん参加できる", "難しい", "未定"]},
    {"key": "q3", "label": "自由コメント（任意）", "type": "textarea"},
]

SURVEY_TITLE = "社内アンケート"

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def form_page(
    request: Request,
    x_auth_request_email: Annotated[str | None, Header()] = None,
):
    submitted = request.query_params.get("ok") == "1"
    already = request.query_params.get("already") == "1"

    # 既回答チェック
    if not submitted and x_auth_request_email:
        db = db_client()
        existing = list(
            db.collection("responses").where("email", "==", x_auth_request_email).limit(1).stream()
        )
        if existing:
            return _already_page(x_auth_request_email)

    if submitted:
        return _thanks_page(x_auth_request_email)

    # フォーム
    fields_html = ""
    for q in QUESTIONS:
        fields_html += f'<fieldset><legend>{q["label"]}</legend>'
        if q["type"] == "radio":
            for opt in q["options"]:
                fields_html += (
                    f'<label><input type="radio" name="{q["key"]}" value="{opt}" required>'
                    f' {opt}</label><br>'
                )
        elif q["type"] == "textarea":
            fields_html += f'<textarea name="{q["key"]}" rows="3"></textarea>'
        fields_html += "</fieldset>"

    return _page(f"""
<form method="post">
  {fields_html}
  <button type="submit">回答を送信</button>
</form>
""", x_auth_request_email)


@app.post("/", response_class=HTMLResponse)
async def submit(
    request: Request,
    x_auth_request_email: Annotated[str | None, Header()] = None,
):
    form = await request.form()
    db = db_client()

    # 既回答チェック (二重送信防止)
    existing = list(
        db.collection("responses").where("email", "==", x_auth_request_email or "").limit(1).stream()
    )
    if existing:
        return RedirectResponse("/?already=1", status_code=302)

    data = {
        "email": x_auth_request_email or "unknown",
        "submitted_at": datetime.datetime.now(datetime.timezone.utc),
    }
    for q in QUESTIONS:
        data[q["key"]] = form.get(q["key"], "")

    db.collection("responses").add(data)
    return RedirectResponse("/?ok=1", status_code=302)


@app.get("/results", response_class=HTMLResponse)
def results(x_auth_request_email: Annotated[str | None, Header()] = None):
    db = db_client()
    docs = list(db.collection("responses").order_by("submitted_at").stream())

    if not docs:
        return _page("<p>まだ回答がありません。</p>", x_auth_request_email, title="回答一覧")

    rows_html = ""
    for doc in docs:
        d = doc.to_dict()
        ts = d.get("submitted_at")
        ts_str = ts.strftime("%m/%d %H:%M") if ts and hasattr(ts, "strftime") else str(ts or "")
        answers = "　".join(f"{q['label'][:10]}…: {d.get(q['key'], '')}" for q in QUESTIONS)
        rows_html += f"<tr><td>{d.get('email','')}</td><td>{ts_str}</td><td>{answers}</td></tr>\n"

    table = f"""
<p>{len(docs)} 件の回答</p>
<table>
<thead><tr><th>メール</th><th>送信日時</th><th>回答</th></tr></thead>
<tbody>{rows_html}</tbody>
</table>
"""
    return _page(table, x_auth_request_email, title="回答一覧")


def _page(body: str, email: str | None, title: str = SURVEY_TITLE) -> str:
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ font-family: system-ui; max-width: 620px; margin: 3rem auto; padding: 0 1rem; }}
  h1 {{ margin-bottom: .3rem; }}
  .meta {{ color: #888; font-size: .85rem; margin-bottom: 1.5rem; }}
  fieldset {{ border: 1px solid #ddd; border-radius: 6px; margin: 1em 0; padding: .8em 1em; }}
  legend {{ font-weight: bold; padding: 0 .4em; }}
  label {{ display: block; margin: .4em 0; }}
  textarea {{ width: 100%; padding: .5em; font-size: 1em; }}
  button {{ margin-top: 1.5em; padding: .7em 1.5em; font-size: 1em; background: #0066cc;
           color: #fff; border: none; border-radius: 4px; cursor: pointer; }}
  button:hover {{ background: #0055aa; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #e0e0e0; padding: .5em .8em; font-size: .85rem; }}
  th {{ background: #f5f5f5; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="meta">ログイン: {email or "(不明)"}　<a href="/results">回答一覧</a></p>
{body}
</body>
</html>"""


def _thanks_page(email: str | None) -> str:
    return _page("<p>✅ 回答を受け付けました。ありがとうございました！</p>", email)


def _already_page(email: str | None) -> str:
    return _page("<p>⚠️ すでに回答済みです。</p>", email)
