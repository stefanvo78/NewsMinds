#!/bin/bash
# ============================================================================
# Setup Azure OIDC for GitHub Actions
# ============================================================================
# This script creates an Azure AD App Registration with federated credentials
# for GitHub Actions OIDC authentication.
#
# What it does:
# 1. Creates an Azure AD App Registration
# 2. Creates a Service Principal
# 3. Assigns Contributor role to your subscription
# 4. Configures federated credentials for GitHub Actions
#
# Prerequisites:
# - Azure CLI installed and logged in (az login)
# - Owner or User Access Administrator role on subscription
#
# Usage:
#   ./scripts/setup-azure-oidc.sh <github-username> <repo-name>
#
# Example:
#   ./scripts/setup-azure-oidc.sh myusername NewsMinds
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -ne 2 ]; then
    echo -e "${RED}Usage: $0 <github-username> <repo-name>${NC}"
    echo "Example: $0 myusername NewsMinds"
    exit 1
fi

GITHUB_USERNAME=$1
REPO_NAME=$2
# Convert to lowercase using tr (compatible with macOS Bash 3.x)
APP_NAME="github-actions-$(echo "$REPO_NAME" | tr '[:upper:]' '[:lower:]')"

echo -e "${GREEN}🔧 Setting up Azure OIDC for GitHub Actions${NC}"
echo "   GitHub Repo: ${GITHUB_USERNAME}/${REPO_NAME}"
echo "   App Name: ${APP_NAME}"
echo ""

# Check Azure CLI login
echo -e "${YELLOW}📋 Checking Azure CLI login...${NC}"
if ! az account show &> /dev/null; then
    echo -e "${RED}❌ Not logged into Azure CLI. Run: az login${NC}"
    exit 1
fi

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
echo "   Subscription: ${SUBSCRIPTION_ID}"
echo "   Tenant: ${TENANT_ID}"
echo ""

# Step 1: Create App Registration
echo -e "${YELLOW}📋 Step 1: Creating App Registration...${NC}"
APP_ID=$(az ad app list --display-name "$APP_NAME" --query "[0].appId" -o tsv)

if [ -z "$APP_ID" ] || [ "$APP_ID" == "null" ]; then
    APP_ID=$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)
    echo "   ✅ Created App Registration: ${APP_ID}"
else
    echo "   ⏩ App Registration already exists: ${APP_ID}"
fi
echo ""

# Step 2: Create Service Principal
echo -e "${YELLOW}📋 Step 2: Creating Service Principal...${NC}"
SP_ID=$(az ad sp list --filter "appId eq '${APP_ID}'" --query "[0].id" -o tsv)

if [ -z "$SP_ID" ] || [ "$SP_ID" == "null" ]; then
    SP_ID=$(az ad sp create --id "$APP_ID" --query id -o tsv)
    echo "   ✅ Created Service Principal: ${SP_ID}"
else
    echo "   ⏩ Service Principal already exists: ${SP_ID}"
fi
echo ""

# Step 3: Assign Contributor role
echo -e "${YELLOW}📋 Step 3: Assigning Contributor role to subscription...${NC}"
ROLE_ASSIGNMENT=$(az role assignment list \
    --assignee "$APP_ID" \
    --role "Contributor" \
    --scope "/subscriptions/${SUBSCRIPTION_ID}" \
    --query "[0].id" -o tsv)

if [ -z "$ROLE_ASSIGNMENT" ] || [ "$ROLE_ASSIGNMENT" == "null" ]; then
    az role assignment create \
        --assignee "$APP_ID" \
        --role "Contributor" \
        --scope "/subscriptions/${SUBSCRIPTION_ID}" \
        --output none
    echo "   ✅ Assigned Contributor role"
else
    echo "   ⏩ Role assignment already exists"
fi
echo ""

# Step 4: Create federated credentials for GitHub Actions
echo -e "${YELLOW}📋 Step 4: Creating federated credentials...${NC}"

# Federated credential for 'main' branch
CRED_NAME_MAIN="github-actions-main"
EXISTING_CRED_MAIN=$(az ad app federated-credential list --id "$APP_ID" --query "[?name=='${CRED_NAME_MAIN}'].name" -o tsv)

if [ -z "$EXISTING_CRED_MAIN" ]; then
    az ad app federated-credential create \
        --id "$APP_ID" \
        --parameters "{
            \"name\": \"${CRED_NAME_MAIN}\",
            \"issuer\": \"https://token.actions.githubusercontent.com\",
            \"subject\": \"repo:${GITHUB_USERNAME}/${REPO_NAME}:ref:refs/heads/main\",
            \"description\": \"GitHub Actions - main branch\",
            \"audiences\": [\"api://AzureADTokenExchange\"]
        }" \
        --output none
    echo "   ✅ Created federated credential for 'main' branch"
else
    echo "   ⏩ Federated credential for 'main' already exists"
fi

# Federated credential for Pull Requests
CRED_NAME_PR="github-actions-pr"
EXISTING_CRED_PR=$(az ad app federated-credential list --id "$APP_ID" --query "[?name=='${CRED_NAME_PR}'].name" -o tsv)

if [ -z "$EXISTING_CRED_PR" ]; then
    az ad app federated-credential create \
        --id "$APP_ID" \
        --parameters "{
            \"name\": \"${CRED_NAME_PR}\",
            \"issuer\": \"https://token.actions.githubusercontent.com\",
            \"subject\": \"repo:${GITHUB_USERNAME}/${REPO_NAME}:pull_request\",
            \"description\": \"GitHub Actions - Pull Requests\",
            \"audiences\": [\"api://AzureADTokenExchange\"]
        }" \
        --output none
    echo "   ✅ Created federated credential for Pull Requests"
else
    echo "   ⏩ Federated credential for PRs already exists"
fi

# Federated credential for 'dev' environment
CRED_NAME_DEV="github-actions-env-dev"
EXISTING_CRED_DEV=$(az ad app federated-credential list --id "$APP_ID" --query "[?name=='${CRED_NAME_DEV}'].name" -o tsv)

if [ -z "$EXISTING_CRED_DEV" ]; then
    az ad app federated-credential create \
        --id "$APP_ID" \
        --parameters "{
            \"name\": \"${CRED_NAME_DEV}\",
            \"issuer\": \"https://token.actions.githubusercontent.com\",
            \"subject\": \"repo:${GITHUB_USERNAME}/${REPO_NAME}:environment:dev\",
            \"description\": \"GitHub Actions - dev environment\",
            \"audiences\": [\"api://AzureADTokenExchange\"]
        }" \
        --output none
    echo "   ✅ Created federated credential for 'dev' environment"
else
    echo "   ⏩ Federated credential for 'dev' environment already exists"
fi

# Federated credential for 'prod' environment
CRED_NAME_PROD="github-actions-env-prod"
EXISTING_CRED_PROD=$(az ad app federated-credential list --id "$APP_ID" --query "[?name=='${CRED_NAME_PROD}'].name" -o tsv)

if [ -z "$EXISTING_CRED_PROD" ]; then
    az ad app federated-credential create \
        --id "$APP_ID" \
        --parameters "{
            \"name\": \"${CRED_NAME_PROD}\",
            \"issuer\": \"https://token.actions.githubusercontent.com\",
            \"subject\": \"repo:${GITHUB_USERNAME}/${REPO_NAME}:environment:prod\",
            \"description\": \"GitHub Actions - prod environment\",
            \"audiences\": [\"api://AzureADTokenExchange\"]
        }" \
        --output none
    echo "   ✅ Created federated credential for 'prod' environment"
else
    echo "   ⏩ Federated credential for 'prod' environment already exists"
fi

# Federated credential for destroy environment
CRED_NAME_DESTROY="github-actions-env-destroy"
EXISTING_CRED_DESTROY=$(az ad app federated-credential list --id "$APP_ID" --query "[?name=='${CRED_NAME_DESTROY}'].name" -o tsv)

if [ -z "$EXISTING_CRED_DESTROY" ]; then
    az ad app federated-credential create \
        --id "$APP_ID" \
        --parameters "{
            \"name\": \"${CRED_NAME_DESTROY}\",
            \"issuer\": \"https://token.actions.githubusercontent.com\",
            \"subject\": \"repo:${GITHUB_USERNAME}/${REPO_NAME}:environment:dev-destroy\",
            \"description\": \"GitHub Actions - destroy environment\",
            \"audiences\": [\"api://AzureADTokenExchange\"]
        }" \
        --output none
    echo "   ✅ Created federated credential for 'dev-destroy' environment"
else
    echo "   ⏩ Federated credential for 'dev-destroy' already exists"
fi

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}📋 Add these secrets to your GitHub repository:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Go to: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}/settings/secrets/actions"
echo ""
echo "Add the following secrets:"
echo ""
echo "  AZURE_CLIENT_ID:       ${APP_ID}"
echo "  AZURE_TENANT_ID:       ${TENANT_ID}"
echo "  AZURE_SUBSCRIPTION_ID: ${SUBSCRIPTION_ID}"
echo "  POSTGRES_ADMIN_LOGIN:  <your-chosen-username>"
echo "  POSTGRES_ADMIN_PASSWORD: <your-secure-password>"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${YELLOW}📋 Create GitHub Environments (optional but recommended):${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Go to: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}/settings/environments"
echo ""
echo "Create environments:"
echo "  - dev"
echo "  - prod (add required reviewers for protection)"
echo "  - dev-destroy (add required reviewers for protection)"
echo ""
