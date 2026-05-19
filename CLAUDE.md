# CLAUDE.md — sandbox-template-python

plaize Sandbox 基盤の Python (FastAPI) アプリテンプレ。

## このリポでやってよいこと

- `main.py` の編集・拡張
- `requirements.txt` に依存追加
- `sdks/notion_db.py` / `sdks/sandbox_db.py` を import して使う
- 新規 Python ファイル追加（`utils.py` 等）
- `sandbox.yaml` の `name` / `purpose` / `expires_at` 編集

## やってはいけないこと

- `owner` / `app` の変更（リポ作成時に決定済み）
- `lifetime: permanent` を勝手に追加（Urara レビュー必須）
- API トークン・パスワード・顧客情報を生でコード/コミットに含める
- ローカル開発で本番 Notion DB に書き込む（コピーを作って試す）

## SDK の使い方

### Notion API

```python
from sdks.notion_db import client
n = client()  # NOTION_TOKEN 環境変数から自動取得
rows = n.query("a1b2c3...db-id")
n.create_page("a1b2c3...", {"Name": {"title": [{"text": {"content": "Alice"}}]}})
```

`NOTION_TOKEN` は deploy workflow が自動で Secret Manager から注入する。
sandbox.yaml に `data.notion` を書くこと + Secret Manager に token を入れることが前提（README 参照）。

### Firestore (sandbox_db)

```python
from sdks.sandbox_db import client
db = client()
db.collection("notes").add({"text": "hello"})  # → apps/<owner>--<app>/notes
```

`SANDBOX_OWNER` / `SANDBOX_APP` env vars は deploy workflow が自動で注入。
collection は自動で `apps/<owner>--<app>/` prefix が付くので、他のアプリのデータは見えない。

## 認証ヘッダ

router (oauth2-proxy) が以下のヘッダを注入する。アプリ側で読める：

- `X-Auth-Request-Email`: ログイン中のユーザー email（例: `urara@plaize.co`）
- `X-Auth-Request-User`: 同上の user 部分

FastAPI で読む例：
```python
from fastapi import Header
from typing import Annotated

@app.get("/")
def root(x_auth_request_email: Annotated[str | None, Header()] = None):
    return f"hello {x_auth_request_email}"
```

## デプロイ

`git push origin main` → GitHub Actions が動く。失敗したら Claude に「Actions の失敗ログ見せて」と頼む。

## 参考

- [sandbox-template-python README](README.md) — フル仕様
- [全体プラン](/Users/ularanishitani/.claude/plans/https-zenn-dev-aircloset-articles-65efe9-lovely-glacier.md)
- ルーター: `plaize-co/sandbox-platform`
- MCP サーバ: `plaize-co/sandbox-mcp`
