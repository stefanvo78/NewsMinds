"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, test_user_data: dict):
    """Test user registration."""
    response = await client.post("/api/v1/auth/register", json=test_user_data)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert "id" in data
    assert "password" not in data  # Password should not be returned
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user_data: dict):
    """Test that registering with duplicate email fails."""
    # Register first user
    await client.post("/api/v1/auth/register", json=test_user_data)

    # Try to register again with same email
    response = await client.post("/api/v1/auth/register", json=test_user_data)

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user_data: dict):
    """Test successful login."""
    # Register user first
    await client.post("/api/v1/auth/register", json=test_user_data)

    # Login with form data (OAuth2 spec)
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user_data: dict):
    """Test login with wrong password."""
    # Register user first
    await client.post("/api/v1/auth/register", json=test_user_data)

    # Try to login with wrong password
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user_data["email"],
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with nonexistent user."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "nonexistent@example.com",
            "password": "anypassword",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, test_user_data: dict):
    """Test getting current user info with valid token."""
    # Register and login
    await client.post("/api/v1/auth/register", json=test_user_data)
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )
    token = login_response.json()["access_token"]

    # Get current user
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user_data["email"]


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    """Test that protected endpoints require authentication."""
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_invalid_token(client: AsyncClient):
    """Test that invalid tokens are rejected."""
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid-token-here"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_with_full_name(client: AsyncClient):
    """Test registration with optional full_name field."""
    user_data = {
        "email": "fullname@example.com",
        "password": "SecurePass123!",
        "full_name": "John Doe",
    }
    response = await client.post("/api/v1/auth/register", json=user_data)

    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "John Doe"


@pytest.mark.asyncio
async def test_register_without_full_name(client: AsyncClient):
    """Test registration without optional full_name field."""
    user_data = {
        "email": "nofullname@example.com",
        "password": "SecurePass123!",
    }
    response = await client.post("/api/v1/auth/register", json=user_data)

    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] is None


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    """Test registration with invalid email format."""
    user_data = {
        "email": "not-an-email",
        "password": "SecurePass123!",
    }
    response = await client.post("/api/v1/auth/register", json=user_data)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    """Test registration with too short password."""
    user_data = {
        "email": "shortpass@example.com",
        "password": "short",  # Less than 8 chars
    }
    response = await client.post("/api/v1/auth/register", json=user_data)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_token_contains_user_info(client: AsyncClient, test_user_data: dict):
    """Test that the JWT token can be used to get user info."""
    # Register
    register_response = await client.post(
        "/api/v1/auth/register", json=test_user_data
    )
    user_id = register_response.json()["id"]

    # Login
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )
    token = login_response.json()["access_token"]

    # Use token to get user info
    me_response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["id"] == user_id
