# CodeBridge

> 非エンジニアが自然言語でシステムを変更できる、AIエージェント型コード変更プラットフォーム

## 概要

1. **リクエスト** — 非エンジニアが日本語で変更内容を入力
2. **生成・検証** — Azure OpenAI (o4-mini) がコードを生成し、サンドボックスで自己デバッグ
3. **レビュー** — エンジニアが変更差分・AIレポートを確認
4. **承認・反映** — ワンクリックで本番環境へデプロイ。拒否して再指示も可能

## セットアップ

```bash
git clone https://github.com/t-k-haru/codebridge-ai.git
cd codebridge-ai
pip install -r requirements.txt
cp .env.example .env
# .env にAzure OpenAIのAPIキーを記入
streamlit run app.py
```

## 環境変数

`.env` に以下を設定してください：

```
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=o4-mini
ENGINEER_PASSWORD=your_password
```

## 技術スタック

- **フロントエンド**: Streamlit (Python)
- **AIモデル**: Azure OpenAI Service / o4-mini
- **実行基盤**: Azure App Service
- **サンドボックス**: subprocess による隔離実行
- **自動デプロイ**: GitHub Actions

## デモ

https://codebridge-t-k-haru.azurewebsites.net

エンジニアレビュー画面のパスワードは別途お問い合わせください。

## ライセンス

MIT
