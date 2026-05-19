# sandbox-template-python

plaize Sandbox 基盤の **Python (FastAPI) アプリ向けテンプレート**。
データ保存（Notion / Firestore）や API 呼び出し等が必要なアプリで使う。

> 静的 HTML だけで足りる場合は `sandbox-template-static` を使ってください。

## 含まれているもの

| ファイル | 役割 |
|---|---|
| `main.py` | FastAPI アプリ本体（Hello world）。ここを書き換えていく |
| `requirements.txt` | 依存ライブラリ |
| `Dockerfile` | Cloud Run 用イメージ定義 |
| `sandbox.yaml` | アプリのメタデータ（必須） |
| `sdks/notion_db.py` | Notion API クライアント（軽量） |
| `sdks/sandbox_db.py` | Firestore ラッパ（apps/{owner}--{app}/... に自動 prefix） |
| `build/validate-sandbox.py` | CI で sandbox.yaml を検証 |
| `.github/workflows/deploy.yml` | push → Cloud Run 自動デプロイ |

## 使い方

1. Claude Desktop で `sandbox_new` ツールに「Python テンプレで作って」と頼む
2. テンプレが clone され、`sandbox.yaml` に owner / app / name / purpose が入る
3. `main.py` を Claude に書いてもらう
4. `git push` → 2分後に `https://<owner>--<app>.sandbox.plaize.co` で開ける

## データ層の使い方

### Notion を使う場合

1. `sandbox.yaml` に追記：
   ```yaml
   data:
     notion:
       - id: "<Notion DB の ID>"
         access: "read-write"  # or "read"
   ```
2. **Notion 側で Integration を作って DB に Connect**（Phase 2 で自動化予定、当面手動）
3. Integration の token を Secret Manager に保管：
   ```bash
   echo -n "<secret_xxx>" | gcloud secrets create \
     app--<owner>--<app>--notion-token --data-file=- \
     --project=plaize-sandbox-prod
   # 自分の per-app SA に読み取り権限：
   gcloud secrets add-iam-policy-binding \
     app--<owner>--<app>--notion-token \
     --member="serviceAccount:app-<owner>-<app>@plaize-sandbox-prod.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```
4. `main.py` で使う：
   ```python
   from sdks.notion_db import client
   n = client()  # NOTION_TOKEN env から自動取得
   rows = n.query(os.environ["NOTION_DB_CUSTOMER"])
   ```

### Firestore を使う場合

1. `sandbox.yaml` に追記：
   ```yaml
   data:
     firestore: true
   ```
2. `requirements.txt` で `google-cloud-firestore==2.18.0` のコメント外し
3. `main.py` で使う：
   ```python
   from sdks.sandbox_db import client
   db = client()  # apps/<owner>--<app>/... に自動 prefix
   db.collection("notes").add({"text": "hello"})
   ```
4. ⚠️ Phase 2 では Firestore named DB `sandbox` と per-app SA の IAM condition で
   別アプリのデータが見えないよう保護される予定。**まだ Phase 2 セットアップ前は
   Firestore は本格的に使わないこと**

## ローカル動作確認

```bash
pip install -r requirements.txt
SANDBOX_OWNER=urara SANDBOX_APP=hello-py uvicorn main:app --reload --port 8080
```

→ http://localhost:8080 で Hello ページが見える（ただし sandbox-router の認証は通らない）

## デプロイ

`git push origin main` → GitHub Actions が走り、約2分で Cloud Run に反映。

`https://<owner>--<app>.sandbox.plaize.co` で動作確認。

## オーナー

`sandbox.yaml` の `owner` フィールドが自分自身のとき、このアプリのコードを編集する権利がある（CODEOWNERS と PR レビューで担保予定）。
