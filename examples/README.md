# Examples

`main.py` の置き換えサンプル集です。Claude に「このファイルを参考に main.py を書いて」と伝えるか、そのままコピーして使ってください。

## ファイル一覧

| ファイル | 説明 | 必要な data |
|---|---|---|
| [`notion-form.py`](notion-form.py) | Notion DB に行を追加するフォーム（請求書入力など） | `data.notion` |
| [`notion-viewer.py`](notion-viewer.py) | Notion DB の内容をブラウザで閲覧できるビューアー | `data.notion` |
| [`firestore-survey.py`](firestore-survey.py) | 回答を Firestore に保存する社内アンケート | `data.firestore: true` |
| [`external-api.py`](external-api.py) | 外部 API（為替・天気）を叩くダッシュボード | 不要 |
| [`slack-daily-digest.py`](slack-daily-digest.py) | 毎朝 Slack チャンネルに自動投稿する cron アプリ | `data.slack: true` |

## 使い方

### 1. examples のどれかを `main.py` にコピーする

```bash
cp examples/notion-viewer.py main.py
```

### 2. `sandbox.yaml` の `data:` セクションを設定する

**Notion を使う場合 (`notion-form.py` / `notion-viewer.py`):**
```yaml
data:
  notion:
    - id: "YOUR-NOTION-DB-ID"
      access: "read-write"   # read-only なら "read"
```
→ Claude に `sandbox_notion_connect` ツールを使わせて Notion Integration token を登録する

**Firestore を使う場合 (`firestore-survey.py`):**
```yaml
data:
  firestore: true
```
→ `sandbox_new` または `sandbox_notion_connect` 実行時に SA へ自動でアクセス権が付与される

**外部 API のみ (`external-api.py`):**
```yaml
# data: セクション不要
```

**Slack に投稿する場合 (`slack-daily-digest.py`):**
```yaml
data:
  slack: true   # 共有 bot (plaize-sandbox-bot) のトークンを env に注入
cron:
  - schedule: "0 9 * * MON-FRI"
    command: "curl -fsS http://localhost:8080/jobs/daily"
```
→ 投稿したいチャンネルに事前に bot を invite すること（Slack UI → チャンネル → `+ Add apps` → plaize-sandbox-bot）

### 3. requirements.txt に必要なパッケージを追記する

| example | 追加パッケージ |
|---|---|
| notion-form / notion-viewer | 不要（`httpx` は既に入っている） |
| firestore-survey | `google-cloud-firestore>=2.16` |
| external-api | 不要（`httpx` は既に入っている） |
| slack-daily-digest | 不要（`httpx` は既に入っている） |

### 4. push → CI が自動デプロイ

```bash
git add main.py sandbox.yaml requirements.txt
git commit -m "..."
git push
```

## データ選択フローチャート

```
このアプリは...
├─ 既存の Notion DB を読み書きする → data.notion: [...]
│    └─ 例: notion-form.py, notion-viewer.py
│
├─ アプリ固有データを保持したい → data.firestore: true
│    └─ 例: firestore-survey.py
│
├─ Slack に投稿したい（cron / Webhook 受信） → data.slack: true
│    └─ 例: slack-daily-digest.py
│
└─ 外部 API を叩くだけ / 計算機 → data: 不要
     └─ 例: external-api.py
```

> **複数併用OK**: `notion:` / `firestore: true` / `slack: true` を同時に書いても問題ない。
