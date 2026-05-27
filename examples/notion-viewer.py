"""
EXAMPLE: Notion DB をブラウザで閲覧できる表形式ビューアー。

main.py の中身を以下に置き換えると、`/` で Notion DB の内容を
HTML テーブルとして表示する。表のカラムはプロパティを自動検出。

前提:
- sandbox.yaml の data.notion に対象 DB の id を入れる
- Notion 側で Integration を該当 DB に Connect する
- sandbox_notion_connect MCP ツールで token を Secret Manager に登録する

使い方 (sandbox.yaml):
    data:
      notion:
        - id: "YOUR-DB-ID-HERE"
          access: "read"
    # NOTION_DB_ID 環境変数でデフォルトを上書き可
"""
import os
from typing import Annotated

from fastapi import FastAPI, Header, Query
from fastapi.responses import HTMLResponse

from sdks.notion_db import client as notion_client

DB_ID = os.environ.get("NOTION_DB_ID", "REPLACE-ME-WITH-DB-ID")

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def viewer(
    x_auth_request_email: Annotated[str | None, Header()] = None,
    sort: str = Query(default=""),
):
    n = notion_client()

    # クエリ: 最新200件 (ページネーションは省略)
    rows = n.query(DB_ID, page_size=200)

    if not rows:
        return _page("(データなし)", x_auth_request_email, "<p>レコードがありません。</p>")

    # 全プロパティ名を収集 (最初のページが持つプロパティを基準に)
    all_props: list[str] = list(rows[0].get("properties", {}).keys()) if rows else []

    def _cell(prop: dict) -> str:
        """Notion プロパティ dict から表示用文字列を返す。"""
        ptype = prop.get("type", "")
        if ptype == "title":
            return "".join(t["plain_text"] for t in prop.get("title", []))
        if ptype == "rich_text":
            return "".join(t["plain_text"] for t in prop.get("rich_text", []))
        if ptype == "number":
            v = prop.get("number")
            return f"{v:,}" if v is not None else ""
        if ptype == "select":
            s = prop.get("select")
            return s["name"] if s else ""
        if ptype == "multi_select":
            return ", ".join(s["name"] for s in prop.get("multi_select", []))
        if ptype == "date":
            d = prop.get("date")
            return d["start"] if d else ""
        if ptype == "checkbox":
            return "✔" if prop.get("checkbox") else ""
        if ptype == "url":
            url = prop.get("url") or ""
            return f'<a href="{url}" target="_blank">{url}</a>' if url else ""
        if ptype == "email":
            return prop.get("email") or ""
        if ptype == "phone_number":
            return prop.get("phone_number") or ""
        if ptype == "formula":
            f = prop.get("formula", {})
            return str(f.get("string") or f.get("number") or f.get("boolean") or "")
        if ptype == "status":
            s = prop.get("status")
            return s["name"] if s else ""
        return ""

    # ソート (クエリパラメータ ?sort=プロパティ名)
    sort_prop = sort if sort in all_props else ""
    if sort_prop:
        rows = sorted(rows, key=lambda r: _cell(r["properties"].get(sort_prop, {})))

    # テーブル HTML
    header_cells = "".join(
        f'<th><a href="?sort={p}">{p}</a></th>' for p in all_props
    )
    body_rows = ""
    for row in rows:
        props = row.get("properties", {})
        cells = "".join(f"<td>{_cell(props.get(p, {}))}</td>" for p in all_props)
        notion_url = row.get("url", "#")
        cells = f'<td><a href="{notion_url}" target="_blank">↗</a></td>' + cells
        body_rows += f"<tr>{cells}</tr>\n"

    table = f"""
<table>
  <thead><tr><th>Notion</th>{header_cells}</tr></thead>
  <tbody>{body_rows}</tbody>
</table>
"""
    return _page(f"{len(rows)} 件", x_auth_request_email, table)


def _page(subtitle: str, email: str | None, body: str) -> str:
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Notion Viewer</title>
<style>
  body {{ font-family: system-ui; margin: 0; padding: 1rem 2rem; background: #fafafa; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.2rem; }}
  .meta {{ color: #888; font-size: .85rem; margin-bottom: 1rem; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; }}
  th, td {{ border: 1px solid #e0e0e0; padding: .45em .7em; font-size: .9rem; white-space: nowrap; }}
  th {{ background: #f5f5f5; position: sticky; top: 0; }}
  th a {{ color: inherit; text-decoration: none; }}
  th a:hover {{ text-decoration: underline; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  tr:hover {{ background: #fff3cd; }}
</style>
</head>
<body>
<h1>Notion Viewer</h1>
<p class="meta">{subtitle}　ログイン: {email or "(不明)"}　<a href="/">↺ 再読込</a></p>
{body}
</body>
</html>"""
