"""Tests for AI service and summarization endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def get_auth_token(client: AsyncClient, user_data: dict) -> str:
    """Helper to register a user and get auth token."""
    await client.post("/api/v1/auth/register", json=user_data)
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": user_data["email"],
            "password": user_data["password"],
        },
    )
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_summarize_article_ai_not_configured(
    client: AsyncClient,
    test_user_data: dict,
    test_source_data: dict,
    test_article_data: dict,
):
    """Test that summarize returns 503 when AI is not configured."""
    token = await get_auth_token(client, test_user_data)

    # Create source and article
    source_resp = await client.post(
        "/api/v1/sources/",
        json=test_source_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    source_id = source_resp.json()["id"]

    article_data = {**test_article_data, "source_id": source_id}
    article_resp = await client.post(
        "/api/v1/articles/",
        json=article_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    article_id = article_resp.json()["id"]

    # Try to summarize - should fail because AI is not configured
    response = await client.post(
        f"/api/v1/articles/{article_id}/summarize",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_summarize_nonexistent_article(
    client: AsyncClient,
    test_user_data: dict,
):
    """Test that summarize returns 404 for nonexistent article."""
    token = await get_auth_token(client, test_user_data)

    # Mock AI service as available
    with patch("src.api.routers.articles.ai_service") as mock_ai:
        mock_ai.is_available = True

        response = await client.post(
            "/api/v1/articles/00000000-0000-0000-0000-000000000000/summarize",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_summarize_article_success(
    client: AsyncClient,
    test_user_data: dict,
    test_source_data: dict,
    test_article_data: dict,
):
    """Test successful article summarization with mocked AI."""
    token = await get_auth_token(client, test_user_data)

    # Create source and article
    source_resp = await client.post(
        "/api/v1/sources/",
        json=test_source_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    source_id = source_resp.json()["id"]

    article_data = {**test_article_data, "source_id": source_id}
    article_resp = await client.post(
        "/api/v1/articles/",
        json=article_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    article_id = article_resp.json()["id"]

    # Mock the AI service
    with patch("src.api.routers.articles.ai_service") as mock_ai:
        mock_ai.is_available = True
        mock_ai.summarize_article = AsyncMock(
            return_value="This is a test summary of the article."
        )

        response = await client.post(
            f"/api/v1/articles/{article_id}/summarize",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["article_id"] == article_id
    assert data["summary"] == "This is a test summary of the article."


@pytest.mark.asyncio
async def test_summarize_requires_auth(
    client: AsyncClient,
):
    """Test that summarize endpoint requires authentication."""
    response = await client.post(
        "/api/v1/articles/00000000-0000-0000-0000-000000000000/summarize"
    )

    assert response.status_code == 401
