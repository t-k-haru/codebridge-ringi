#!/bin/bash
# =========================================================
# CodeBridge AI — Azure App Service デプロイスクリプト
# 実行前に az login を済ませておくこと
# =========================================================

# ── 変数（ここだけ自分の値に変える） ──────────────────────
RESOURCE_GROUP="codebridge-rg"
LOCATION="japaneast"
APP_SERVICE_PLAN="codebridge-plan"
APP_NAME="codebridge-ai"          # 世界一意の名前にすること
ACR_NAME="codebridgeacr"          # Azure Container Registry

# ── リソースグループ作成 ───────────────────────────────────
az group create --name $RESOURCE_GROUP --location $LOCATION

# ── Container Registry 作成 ───────────────────────────────
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

# ── Docker イメージのビルド & プッシュ ─────────────────────
az acr build \
  --registry $ACR_NAME \
  --image codebridge:latest \
  .

# ── App Service Plan 作成（Linux + Docker） ───────────────
az appservice plan create \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --is-linux \
  --sku B2

# ── Web App 作成 ───────────────────────────────────────────
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)

az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --name $APP_NAME \
  --deployment-container-image-name $ACR_LOGIN_SERVER/codebridge:latest

# ── 環境変数の設定 ─────────────────────────────────────────
# .env ファイルの値を参照して設定する
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --settings \
    AZURE_OPENAI_API_KEY="$AZURE_OPENAI_API_KEY" \
    AZURE_OPENAI_ENDPOINT="$AZURE_OPENAI_ENDPOINT" \
    AZURE_OPENAI_DEPLOYMENT="o4-mini" \
    ENGINEER_PASSWORD="$ENGINEER_PASSWORD" \
    WEBSITES_PORT=8000

echo ""
echo "✅ デプロイ完了！"
echo "🌐 URL: https://$APP_NAME.azurewebsites.net"
