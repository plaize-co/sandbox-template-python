"""
EXAMPLE: 外部 API だけ叩く計算ダッシュボード（DB不使用）。

main.py の中身を以下に置き換えると、為替レート (USD/JPY) と
天気情報を取得してブラウザに表示するダッシュボードになる。

使用する外部 API (無料・APIキー不要):
  - exchangerate-api.com  (レート取得、CORS 対応)
  - api.open-meteo.com    (天気予報、東京)

sandbox.yaml に data セクションは不要:
    name: "外部 API ダッシュボード"
    owner: "..."
    app: "..."
    runtime: "python"
    expires_at: ...
    purpose: "為替レートと天気を表示するダッシュボード"
    # data: ← 書かなくてよい

外部 API を変えたい場合は FETCH_TASKS リストを書き換える。
"""
import datetime
from typing import Annotated

import httpx
from fastapi import FastAPI, Header
from fastapi.responses import HTMLResponse

app = FastAPI()

# 東京の緯度経度
TOKYO_LAT = 35.6762
TOKYO_LON = 139.6503

WMO_CODE = {
    0: "快晴", 1: "概ね晴れ", 2: "部分的に曇り", 3: "曇り",
    45: "霧", 48: "霧氷",
    51: "霧雨（弱）", 53: "霧雨", 55: "霧雨（強）",
    61: "小雨", 63: "雨", 65: "大雨",
    71: "小雪", 73: "雪", 75: "大雪",
    80: "にわか雨（弱）", 81: "にわか雨", 82: "にわか雨（強）",
    95: "雷雨", 99: "激しい雷雨",
}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard(x_auth_request_email: Annotated[str | None, Header()] = None):
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

    # 外部 API を並行取得（両方 httpx で）
    rate_info = _fetch_rate()
    weather_info = _fetch_weather()

    body = f"""
<div class="cards">
  <div class="card">
    <h2>💴 為替レート</h2>
    {rate_info}
  </div>
  <div class="card">
    <h2>🌤️ 東京の天気</h2>
    {weather_info}
  </div>
</div>
<p class="updated">最終更新: {now.strftime("%Y-%m-%d %H:%M")} JST</p>
"""
    return _page(body, x_auth_request_email)


def _fetch_rate() -> str:
    """exchangerate-api.com から USD/JPY と EUR/JPY を取得。"""
    try:
        with httpx.Client(timeout=5) as client:
            r = client.get("https://open.er-api.com/v6/latest/USD")
        if r.status_code != 200:
            return f"<p class='err'>取得失敗 ({r.status_code})</p>"
        data = r.json()
        rates = data.get("rates", {})
        jpy = rates.get("JPY", "—")
        eur_jpy = rates.get("JPY", 0) / rates.get("EUR", 1) if rates.get("EUR") else "—"
        updated = data.get("time_last_update_utc", "")
        return f"""
<table>
  <tr><th>通貨</th><th>レート (円)</th></tr>
  <tr><td>USD → JPY</td><td><strong>{jpy:,.2f}</strong></td></tr>
  <tr><td>EUR → JPY</td><td><strong>{eur_jpy:,.2f}</strong></td></tr>
</table>
<p class="sub">出典: open.er-api.com　{updated[:16]}</p>
"""
    except Exception as e:
        return f"<p class='err'>エラー: {e}</p>"


def _fetch_weather() -> str:
    """open-meteo.com から東京の今日・明日の天気を取得。"""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={TOKYO_LAT}&longitude={TOKYO_LON}"
            f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum"
            f"&timezone=Asia%2FTokyo&forecast_days=3"
        )
        with httpx.Client(timeout=5) as client:
            r = client.get(url)
        if r.status_code != 200:
            return f"<p class='err'>取得失敗 ({r.status_code})</p>"
        d = r.json().get("daily", {})
        dates = d.get("time", [])
        codes = d.get("weather_code", [])
        t_max = d.get("temperature_2m_max", [])
        t_min = d.get("temperature_2m_min", [])
        rain = d.get("precipitation_sum", [])

        rows = ""
        for i, dt in enumerate(dates[:3]):
            code = codes[i] if i < len(codes) else 0
            desc = WMO_CODE.get(code, f"コード{code}")
            hi = f"{t_max[i]:.0f}" if i < len(t_max) else "—"
            lo = f"{t_min[i]:.0f}" if i < len(t_min) else "—"
            mm = f"{rain[i]:.1f}" if i < len(rain) else "—"
            rows += f"<tr><td>{dt}</td><td>{desc}</td><td>{hi}°/{lo}°</td><td>{mm}mm</td></tr>"

        return f"""
<table>
  <tr><th>日付</th><th>天気</th><th>気温</th><th>降水量</th></tr>
  {rows}
</table>
<p class="sub">出典: open-meteo.com (東京)</p>
"""
    except Exception as e:
        return f"<p class='err'>エラー: {e}</p>"


def _page(body: str, email: str | None) -> str:
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>ダッシュボード</title>
<style>
  body {{ font-family: system-ui; margin: 0; padding: 1.5rem 2rem; background: #f0f4f8; }}
  h1 {{ margin-bottom: .2rem; font-size: 1.4rem; }}
  .meta {{ color: #888; font-size: .85rem; margin-bottom: 1.5rem; }}
  .cards {{ display: flex; gap: 1.5rem; flex-wrap: wrap; }}
  .card {{ background: #fff; border-radius: 10px; padding: 1.2rem 1.5rem;
           flex: 1 1 280px; box-shadow: 0 1px 4px rgba(0,0,0,.1); }}
  h2 {{ font-size: 1rem; margin: 0 0 .8rem; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ text-align: left; padding: .4em .6em; border-bottom: 1px solid #eee; font-size: .9rem; }}
  th {{ color: #555; font-weight: 600; }}
  strong {{ font-size: 1.1rem; }}
  .sub {{ color: #aaa; font-size: .75rem; margin-top: .5rem; }}
  .err {{ color: #c00; }}
  .updated {{ color: #aaa; font-size: .8rem; margin-top: 1.5rem; }}
</style>
</head>
<body>
<h1>ダッシュボード</h1>
<p class="meta">ログイン: {email or "(不明)"}</p>
{body}
</body>
</html>"""
