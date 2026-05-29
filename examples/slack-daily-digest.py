"""
EXAMPLE: 毎朝 Slack に投稿する cron アプリ。

main.py の中身を以下に置き換えると：
  - GET /  → 直近の投稿予定をブラウザで確認できるダッシュボード
  - cron で /jobs/daily を叩くと #aiの里 に「今日のひとこと」を投稿する

前提:
- sandbox.yaml に `data.slack: true` を書く → SLACK_BOT_TOKEN が自動で env に入る
- sandbox.yaml の cron セクションを書いて、毎朝の起動をスケジュールする

使い方 (sandbox.yaml):
    data:
      slack: true
    cron:
      - schedule: "0 9 * * MON-FRI"   # 平日朝 9:00 JST
        command: "curl -fsS http://localhost:8080/jobs/daily"
        # ※ cron は Phase 3 で Cloud Scheduler 経由になります

bot は plaize-assistant を共有で使います。投稿したいチャンネルに
事前に bot を invite してください（Slack UI → チャンネル → "+ Add apps"）。

CHANNEL と GREETINGS を書き換えればすぐ動きます。
"""
import datetime
import random
from typing import Annotated

from fastapi import FastAPI, Header
from fastapi.responses import HTMLResponse

from sdks.slack import client as slack_client

# ← 投稿先（bot を事前に invite しておくこと）
CHANNEL = "#aiの里"

# ← 投稿内容のテンプレ
GREETINGS = [
    "おはようございます！今日もよろしくお願いします ☀️",
    "今日のひとこと: シンプルさは究極の洗練である",
    "今日のひとこと: 完璧を目指すよりまず終わらせろ",
    "おはようございます！コーヒー飲んで頑張りましょう ☕",
    "今日のひとこと: 早起きは三文の徳",
]

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard(x_auth_request_email: Annotated[str | None, Header()] = None):
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>Slack Daily Digest</title>
<style>
  body {{ font-family: system-ui; max-width: 640px; margin: 3rem auto; padding: 0 1rem; }}
  h1 {{ font-size: 1.4rem; }}
  .card {{ background: #f5f5f5; border-radius: 8px; padding: 1.2rem; margin: 1rem 0; }}
  code {{ background: #eee; padding: 2px 6px; border-radius: 3px; font-size: .9rem; }}
  ul {{ line-height: 1.7; }}
</style>
</head>
<body>
<h1>📣 Slack Daily Digest</h1>
<p>ログイン: {x_auth_request_email or "(不明)"}</p>

<div class="card">
  <strong>投稿先:</strong> {CHANNEL}<br>
  <strong>スケジュール:</strong> sandbox.yaml の cron セクションを参照
</div>

<h2>投稿候補</h2>
<ul>
  {"".join(f"<li>{g}</li>" for g in GREETINGS)}
</ul>

<h2>手動トリガー</h2>
<p>テスト投稿: <code>curl https://&lt;このアプリのURL&gt;/jobs/daily</code></p>
<p>※ 実運用では Cloud Scheduler から叩かれます。</p>
</body>
</html>"""


@app.get("/jobs/daily")
def post_daily():
    """毎朝の Slack 投稿。cron から叩かれる前提。"""
    s = slack_client()
    text = random.choice(GREETINGS)
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d (%a)")
    result = s.post(CHANNEL, f"*{today}*\n{text}")
    return {"posted": True, "channel": CHANNEL, "text": text, "ts": result.get("ts")}
