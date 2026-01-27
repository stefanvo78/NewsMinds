"""Tests for articles endpoints."""

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


async def create_source(client: AsyncClient, token: str, source_data: dict) -> dict:
    """Helper to create a source and return the response data."""
    response = await client.post(
        "/api/v1/sources/",
        json=source_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    return response.json()



@pytest.mark.asyncio
async def test_create_article(
    client: AsyncClient,
    test_user_data: dict,
    test_source_data: dict,
    test_article_data: dict,
):
    """Test creating a new article."""
    token = await get_auth_token(client, test_user_data)
    source = await create_source(client, token, test_source_data)

    # Add source_id to article data
    article_data = {**test_article_data, "source_id": source["id"]}

    response = await client.post(
        "/api/v1/articles/",
        json=article_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == test_article_data["title"]
    assert data["url"] == test_article_data["url"]
    assert data["source_id"] == source["id"]
    assert "id" in data


@pytest.mark.asyncio
async def test_create_article_unauthorized(
    client: AsyncClient,
    test_article_data: dict,
):
    """Test that creating article requires authentication."""
    article_data = {
        **test_article_data,
        "source_id": "00000000-0000-0000-0000-000000000000",
    }
    response = await client.post("/api/v1/articles/", json=article_data)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_article_nonexistent_source(
    client: AsyncClient,
    test_user_data: dict,
    test_article_data: dict,
):
    """Test creating article with nonexistent source fails."""
    token = await get_auth_token(client, test_user_data)

    article_data = {
        **test_article_data,
        "source_id": "00000000-0000-0000-0000-000000000000",
    }

    response = await client.post(
        "/api/v1/articles/",
        json=article_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "source not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_article_duplicate_url(
    client: AsyncClient,
    test_user_data: dict,
    test_source_data: dict,
    test_article_data: dict,
):
    """Test creating article with duplicate URL fails."""
    token = await get_auth_token(client, test_user_data)
    source = await create_source(client, token, test_source_data)

    article_data = {**test_article_data, "source_id": source["id"]}

    # Create first article
    await client.post(
        "/api/v1/articles/",
        json=article_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Try to create duplicate
    response = await client.post(
        "/api/v1/articles/",
        json=article_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_articles(
    client: AsyncClient,
    test_user_data: dict,
    test_source_data: dict,
    test_article_data: dict,
):
    """Test listing articles with pagination."""
    token = await get_auth_token(client, test_user_data)
    source = await create_source(client, token, test_source_data)

    # Create an article
    article_data = {**test_article_data, "source_id": source["id"]}
    await client.post(
        "/api/v1/articles/",
        json=article_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    # List articles (no auth required for listing)
    response = await client.get("/api/v1/articles/")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["title"] == test_article_data["title"]


@pytest.mark.asyncio
async def test_list_articles_filter_by_source(
    client: AsyncClient,
    test_user_data: dict,
    test_source_data: dict,
    test_article_data: dict,
):
    """Test filtering articles by source_id."""
    token = await get_auth_token(client, test_user_data)
    source = await create_source(client, token, test_source_data)

    # Create an article
    article_data = {**test_article_data, "source_id": source["id"]}
    await client.post(
        "/api/v1/articles/",
        json=article_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    # List articles filtered by source
    response = await client.get(f"/api/v1/articles/?source_id={source['id']}")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    assert all(item["source_id"] == source["id"] for item in data["items"])


@pytest.mark.asyncio
async def test_get_article_by_id(
    client: AsyncClient,
    test_user_data: dict,
    test_source_data: dict,
    test_article_data: dict,
):
    """Test getting a specific article by ID."""
    token = await get_auth_token(client, test_user_data)
    source = await create_source(client, token, test_source_data)

    # Create an article
    article_data = {**test_article_data, "source_id": source["id"]}
    create_response = await client.post(
        "/api/v1/articles/",
        json=article_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    article_id = create_response.json()["id"]

    # Get the article
    response = await client.get(f"/api/v1/articles/{article_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == article_id
    assert data["title"] == test_article_data["title"]


@pytest.mark.asyncio
async def test_get_nonexistent_article(client: AsyncClient):
    """Test getting an article that doesn't exist."""
    response = await client.get("/api/v1/articles/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_article(
    client: AsyncClient,
    test_user_data: dict,
    test_source_data: dict,
    test_article_data: dict,
):
    """Test updating an article."""
    token = await get_auth_token(client, test_user_data)
    source = await create_source(client, token, test_source_data)

    # Create an article
    article_data = {**test_article_data, "source_id": source["id"]}
    create_response = await client.post(
        "/api/v1/articles/",
        json=article_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    article_id = create_response.json()["id"]

    # Update the article
    update_data = {
        "title": "Updated Title",
        "summary": "Updated summary with AI analysis.",
    }
    response = await client.patch(
        f"/api/v1/articles/{article_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["summary"] == "Updated summary with AI analysis."
    # Original fields should be preserved
    assert data["url"] == test_article_data["url"]


@pytest.mark.asyncio
async def test_update_article_unauthorized(
    client: AsyncClient,
    test_user_data: dict,
    test_source_data: dict,
    test_article_data: dict,
):
    """Test that updating article requires authentication."""
    token = await get_auth_token(client, test_user_data)
    source = await create_source(client, token, test_source_data)

    # Create an article
    article_data = {**test_article_data, "source_id": source["id"]}
    create_response = await client.post(
        "/api/v1/articles/",
        json=article_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    article_id = create_response.json()["id"]

    # Try to update without auth
    response = await client.patch(
        f"/api/v1/articles/{article_id}",
        json={"title": "Should Fail"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_nonexistent_article(
    client: AsyncClient,
    test_user_data: dict,
):
    """Test updating an article that doesn't exist."""
    token = await get_auth_token(client, test_user_data)

    response = await client.patch(
        "/api/v1/articles/00000000-0000-0000-0000-000000000000",
        json={"title": "Should Fail"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_article(
    client: AsyncClient,
    test_user_data: dict,
    test_source_data: dict,
    test_article_data: dict,
):
    """Test deleting an article."""
    token = await get_auth_token(client, test_user_data)
    source = await create_source(client, token, test_source_data)

    # Create an article
    article_data = {**test_article_data, "source_id": source["id"]}
    create_response = await client.post(
        "/api/v1/articles/",
        json=article_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    article_id = create_response.json()["id"]

    # Delete the article
    response = await client.delete(
        f"/api/v1/articles/{article_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    # Verify it's deleted
    get_response = await client.get(f"/api/v1/articles/{article_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_article_unauthorized(
    client: AsyncClient,
    test_user_data: dict,
    test_source_data: dict,
    test_article_data: dict,
):
    """Test that deleting article requires authentication."""
    token = await get_auth_token(client, test_user_data)
    source = await create_source(client, token, test_source_data)

    # Create an article
    article_data = {**test_article_data, "source_id": source["id"]}
    create_response = await client.post(
        "/api/v1/articles/",
        json=article_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    article_id = create_response.json()["id"]

    # Try to delete without auth
    response = await client.delete(f"/api/v1/articles/{article_id}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_nonexistent_article(
    client: AsyncClient,
    test_user_data: dict,
):
    """Test deleting an article that doesn't exist."""
    token = await get_auth_token(client, test_user_data)

    response = await client.delete(
        "/api/v1/articles/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
