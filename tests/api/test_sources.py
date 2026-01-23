"""Tests for sources endpoints."""

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
async def test_create_source(
    client: AsyncClient, test_user_data: dict, test_source_data: dict
):
    """Test creating a news source."""
    token = await get_auth_token(client, test_user_data)

    response = await client.post(
        "/api/v1/sources/",
        json=test_source_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == test_source_data["name"]
    assert data["url"] == test_source_data["url"]
    assert "id" in data


@pytest.mark.asyncio
async def test_create_source_unauthorized(client: AsyncClient, test_source_data: dict):
    """Test that creating source requires authentication."""
    response = await client.post("/api/v1/sources/", json=test_source_data)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_sources(
    client: AsyncClient, test_user_data: dict, test_source_data: dict
):
    """Test listing sources."""
    token = await get_auth_token(client, test_user_data)

    # Create a source first
    await client.post(
        "/api/v1/sources/",
        json=test_source_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    # List sources
    response = await client.get(
        "/api/v1/sources/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == test_source_data["name"]


@pytest.mark.asyncio
async def test_get_source_by_id(
    client: AsyncClient, test_user_data: dict, test_source_data: dict
):
    """Test getting a specific source by ID."""
    token = await get_auth_token(client, test_user_data)

    # Create a source
    create_response = await client.post(
        "/api/v1/sources/",
        json=test_source_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    source_id = create_response.json()["id"]

    # Get the source
    response = await client.get(
        f"/api/v1/sources/{source_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == source_id
    assert data["name"] == test_source_data["name"]


@pytest.mark.asyncio
async def test_get_nonexistent_source(client: AsyncClient, test_user_data: dict):
    """Test getting a source that doesn't exist."""
    token = await get_auth_token(client, test_user_data)

    response = await client.get(
        "/api/v1/sources/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_source(
    client: AsyncClient, test_user_data: dict, test_source_data: dict
):
    """Test deleting a source."""
    token = await get_auth_token(client, test_user_data)

    # Create a source
    create_response = await client.post(
        "/api/v1/sources/",
        json=test_source_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    source_id = create_response.json()["id"]

    # Delete the source
    response = await client.delete(
        f"/api/v1/sources/{source_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    # Verify it's deleted
    get_response = await client.get(
        f"/api/v1/sources/{source_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_create_duplicate_source_name(
    client: AsyncClient, test_user_data: dict, test_source_data: dict
):
    """Test creating source with duplicate name fails."""
    token = await get_auth_token(client, test_user_data)

    # Create first source
    await client.post(
        "/api/v1/sources/",
        json=test_source_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Try to create duplicate
    response = await client.post(
        "/api/v1/sources/",
        json=test_source_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_source(
    client: AsyncClient, test_user_data: dict, test_source_data: dict
):
    """Test updating a source."""
    token = await get_auth_token(client, test_user_data)

    # Create a source
    create_response = await client.post(
        "/api/v1/sources/",
        json=test_source_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    source_id = create_response.json()["id"]

    # Update the source
    update_data = {
        "name": "Updated Source Name",
        "description": "Updated description",
    }
    response = await client.patch(
        f"/api/v1/sources/{source_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Source Name"
    assert data["description"] == "Updated description"
    # Original URL should be preserved
    assert data["url"] == test_source_data["url"]


@pytest.mark.asyncio
async def test_update_source_unauthorized(
    client: AsyncClient, test_user_data: dict, test_source_data: dict
):
    """Test that updating source requires authentication."""
    token = await get_auth_token(client, test_user_data)

    # Create a source
    create_response = await client.post(
        "/api/v1/sources/",
        json=test_source_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    source_id = create_response.json()["id"]

    # Try to update without auth
    response = await client.patch(
        f"/api/v1/sources/{source_id}",
        json={"name": "Should Fail"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_nonexistent_source(client: AsyncClient, test_user_data: dict):
    """Test updating a source that doesn't exist."""
    token = await get_auth_token(client, test_user_data)

    response = await client.patch(
        "/api/v1/sources/00000000-0000-0000-0000-000000000000",
        json={"name": "Should Fail"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_source_unauthorized(
    client: AsyncClient, test_user_data: dict, test_source_data: dict
):
    """Test that deleting source requires authentication."""
    token = await get_auth_token(client, test_user_data)

    # Create a source
    create_response = await client.post(
        "/api/v1/sources/",
        json=test_source_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    source_id = create_response.json()["id"]

    # Try to delete without auth
    response = await client.delete(f"/api/v1/sources/{source_id}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_nonexistent_source(client: AsyncClient, test_user_data: dict):
    """Test deleting a source that doesn't exist."""
    token = await get_auth_token(client, test_user_data)

    response = await client.delete(
        "/api/v1/sources/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_sources_pagination(client: AsyncClient, test_user_data: dict):
    """Test listing sources with pagination parameters."""
    token = await get_auth_token(client, test_user_data)

    # Create multiple sources
    for i in range(3):
        await client.post(
            "/api/v1/sources/",
            json={
                "name": f"Source {i}",
                "url": f"https://example{i}.com",
                "source_type": "rss",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    # Test pagination
    response = await client.get("/api/v1/sources/?skip=1&limit=2")

    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 2


@pytest.mark.asyncio
async def test_list_sources_active_only(
    client: AsyncClient, test_user_data: dict, test_source_data: dict
):
    """Test filtering sources by active status."""
    token = await get_auth_token(client, test_user_data)

    # Create an active source
    await client.post(
        "/api/v1/sources/",
        json=test_source_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Test active_only filter
    response = await client.get("/api/v1/sources/?active_only=true")

    assert response.status_code == 200
    data = response.json()
    # All returned sources should be active
    assert all(source["is_active"] for source in data)
