"""Tests for sources endpoints."""

import pytest
from httpx import AsyncClient


async def get_auth_token(client: AsyncClient, user_data: dict) -> str:
    """Helper to register a user and get auth token."""
    await client.post("/api/v1/auth/register", json=user_data)
    response = await client.post(
        "/api/v1/auth/token",
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
        "/api/v1/sources/99999",
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
