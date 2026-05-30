# CodeBridge Ringi — Claude Code ガイド

日本企業向けの稟議AIエージェントシステム。申請者が自然文で入力するだけで稟議書草案を自動生成し、承認フローを効率化する。Azure Hackathon 向けプロジェクト。

## 本番環境

| 項目 | 値 |
|---|---|
| 本番URL | https://codebridge-ringi.azurewebsites.net |
| Azureリソースグループ | `codebridge-rg` |
| App Service名 | `codebridge-ringi` |
| App Service Plan | `codebridge-plan2`（West US 2） |
| デプロイ方式 | main push → GitHub Actions（`.github/workflows/deploy.yml`） |

## 技術スタック

- **バックエンド**: FastAPI（`api_main.py`）+ SQLite（`core/auth.py` で管理）
- **AI**: Azure OpenAI o4-mini（`core/ringi_orchestrator.py`）
- **フロントエンド**: シングルページ HTML（`frontend/index.html`）、ダークテーマ
- **認証**: JWT（PyJWT / HS256）、有効期限24時間、ステートレス
- **起動コマンド**: `uvicorn api_main:app --host 0.0.0.0 --port 8000 --workers 1 --timeout-keep-alive 300`

## ファイル構成

```
api_main.py              # FastAPI エントリーポイント、全APIエンドポイント
core/
  auth.py                # ユーザー認証・DB操作（SQLite）
  ringi_orchestrator.py  # Azure OpenAI で稟議書を自動生成
  orchestrator.py        # コード変更パイプライン
  sandbox.py             # コード変更の安全な適用
  azure_client.py        # Azure OpenAI クライアント
frontend/
  index.html             # シングルページフロントエンド（SPA）
.github/workflows/
  deploy.yml             # main push で Azure App Service に自動デプロイ
deploy.sh                # 手動デプロイ用スクリプト（通常は使わない）
```

## テストアカウント（固定）

| ロール | メール | パスワード |
|---|---|---|
| admin | admin@codebridge.ai | Admin1234! |
| manager | manager@codebridge.ai | Manager1234! |
| staff | staff@codebridge.ai | Staff1234! |

## 開発ワークフロー（必ず守ること）

1. **専用ブランチで作業**（`main` へ直接 push しない）
2. **コード変更 → コミット → push → ドラフトPR作成**
3. **「マージしていい？」とユーザーに確認してから** `merge_pull_request` を実行
4. マージ後、GitHub Actions が自動で Azure App Service へデプロイ
5. デプロイ結果（成功/失敗）をユーザーに報告。失敗なら即追加修正PR

## 環境変数

`.env`（ローカル）および Azure App Settings に設定済み：

```
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_DEPLOYMENT=o4-mini
ALLOWED_ORIGINS=*
JWT_SECRET=（任意の長いランダム文字列。未設定なら起動ごとにランダム生成→再起動でセッション無効化）
```

GitHub Secrets に `AZURE_CREDENTIALS`（Azure Service Principal JSON）が設定済み。

> **⚠️ 本番運用**: Azure App Service の「環境変数」に `JWT_SECRET` を設定することで、再起動後もログイン状態が維持される。未設定の場合、アプリ再起動のたびに全ユーザーが再ログイン必要になる。

## 稟議の承認タイプ

| タイプ | 意味 |
|---|---|
| 確認型 | 情報共有・報告 |
| 通知型 | 事後承認でよいもの |
| 判断型 | 上司の判断が必要 |
| 合議型 | 複数人で議論が必要 |

## 将来実装予定の拡張機能

承認後に実際のアクションを自動実行する拡張（`_execute_extension` in `api_main.py`）：
- Amazon 自動購入
- Slack 自動招待

現在は `code_deploy`（コード変更の自動適用）のみ実装済み。
