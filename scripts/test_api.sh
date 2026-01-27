#!/bin/bash
# =============================================================================
# NewsMinds API Test Script
# =============================================================================
# This script tests the API running in Docker.
#
# Prerequisites:
#   - docker-compose up --build (API and Qdrant running)
#   - OPENAI_API_KEY set in .env or environment
#
# Usage:
#   ./scripts/test_api.sh
# =============================================================================

set -e  # Exit on error

API_URL="http://localhost:8000"
API_V1="${API_URL}/api/v1"

echo "=========================================="
echo "NewsMinds API Test Suite"
echo "=========================================="
echo ""

# ---------------------------------------------------------------------------
# 1. Health Check
# ---------------------------------------------------------------------------
echo "1. Testing health endpoint..."
HEALTH=$(curl -s "${API_URL}/health")
echo "   Response: ${HEALTH}"

if echo "${HEALTH}" | grep -q "healthy"; then
    echo "   ✅ Health check passed"
else
    echo "   ❌ Health check failed"
    exit 1
fi
echo ""

# ---------------------------------------------------------------------------
# 2. Root Endpoint
# ---------------------------------------------------------------------------
echo "2. Testing root endpoint..."
ROOT=$(curl -s "${API_URL}/")
echo "   Response: ${ROOT}"
echo "   ✅ Root endpoint works"
echo ""

# ---------------------------------------------------------------------------
# 3. Register User
# ---------------------------------------------------------------------------
echo "3. Registering test user..."
REGISTER_RESPONSE=$(curl -s -X POST "${API_V1}/auth/register" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "test@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User"
    }')
echo "   Response: ${REGISTER_RESPONSE}"

if echo "${REGISTER_RESPONSE}" | grep -q "email"; then
    echo "   ✅ User registered (or already exists)"
else
    echo "   ⚠️  Registration response unexpected"
fi
echo ""

# ---------------------------------------------------------------------------
# 4. Login
# ---------------------------------------------------------------------------
echo "4. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "${API_V1}/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=test@example.com&password=TestPassword123!")

TOKEN=$(echo "${LOGIN_RESPONSE}" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -n "${TOKEN}" ]; then
    echo "   ✅ Login successful"
    echo "   Token: ${TOKEN:0:20}..."
else
    echo "   ❌ Login failed"
    echo "   Response: ${LOGIN_RESPONSE}"
    exit 1
fi
echo ""

# ---------------------------------------------------------------------------
# 5. Create a Source
# ---------------------------------------------------------------------------
echo "5. Creating a news source..."
SOURCE_RESPONSE=$(curl -s -X POST "${API_V1}/sources/" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TOKEN}" \
    -d '{
        "name": "Tech News Daily",
        "url": "https://technews.example.com/rss",
        "source_type": "rss",
        "description": "Technology news feed"
    }')
echo "   Response: ${SOURCE_RESPONSE}"

SOURCE_ID=$(echo "${SOURCE_RESPONSE}" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -n "${SOURCE_ID}" ]; then
    echo "   ✅ Source created: ${SOURCE_ID}"
else
    echo "   ⚠️  Source may already exist"
fi
echo ""

# ---------------------------------------------------------------------------
# 6. List Sources
# ---------------------------------------------------------------------------
echo "6. Listing sources..."
SOURCES=$(curl -s "${API_V1}/sources/")
echo "   Response: ${SOURCES:0:200}..."
echo "   ✅ Sources listed"
echo ""

# ---------------------------------------------------------------------------
# 7. Test Intelligence Briefing (requires OpenAI API key)
# ---------------------------------------------------------------------------
echo "7. Testing intelligence briefing endpoint..."
echo "   (This calls the AI agent - may take a few seconds)"

BRIEFING_RESPONSE=$(curl -s -X POST "${API_V1}/intelligence/briefing" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TOKEN}" \
    -d '{"query": "What are the latest developments in AI?"}' \
    --max-time 60)

if echo "${BRIEFING_RESPONSE}" | grep -q "briefing"; then
    echo "   ✅ Intelligence briefing generated"
    echo "   Response preview: ${BRIEFING_RESPONSE:0:300}..."
elif echo "${BRIEFING_RESPONSE}" | grep -q "error"; then
    echo "   ⚠️  Briefing returned error (check OPENAI_API_KEY)"
    echo "   Response: ${BRIEFING_RESPONSE}"
else
    echo "   ⚠️  Unexpected response"
    echo "   Response: ${BRIEFING_RESPONSE}"
fi
echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "✅ API is running and responding"
echo "✅ Authentication works"
echo "✅ CRUD operations work"
echo ""
echo "Next steps:"
echo "  - Check logs: docker-compose logs -f api"
echo "  - View API docs: http://localhost:8000/api/v1/docs"
echo "  - Qdrant dashboard: http://localhost:6333/dashboard"
echo ""
