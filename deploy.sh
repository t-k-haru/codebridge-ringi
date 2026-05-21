#!/bin/bash
# CodeBridge Ringi — Azure App Service デプロイスクリプト
# 実行前に az login を済ませておくこと

RESOURCE_GROUP="codebridge-rg"
LOCATION="westus2"
APP_SERVICE_PLAN="codebridge-plan2"
APP_NAME="codebridge-ringi"
ACR_NAME="codebridgeringiacr"

az group create --name $RESOURCE_GROUP --location $LOCATION

az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

az acr build \
  --registry $ACR_NAME \
  --image codebridge-ringi:latest \
  .

az appservice plan create \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --is-linux \
  --sku B2

ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)

az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --name $APP_NAME \
  --deployment-container-image-name $ACR_LOGIN_SERVER/codebridge-ringi:latest

az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --settings \
    AZURE_OPENAI_API_KEY="$AZURE_OPENAI_API_KEY" \
    AZURE_OPENAI_ENDPOINT="$AZURE_OPENAI_ENDPOINT" \
    AZURE_OPENAI_DEPLOYMENT="o4-mini" \
    WEBSITES_PORT=8000

echo ""
echo "デプロイ完了！"
echo "URL: https://$APP_NAME.azurewebsites.net"
