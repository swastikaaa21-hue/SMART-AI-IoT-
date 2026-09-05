"""
Tests for API endpoints.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthEndpoint:
    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "services" in data

    async def test_root_endpoint(self, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "SMART AI IoT Backend"
        assert "api" in data


@pytest.mark.asyncio
class TestAuthEndpoints:
    async def test_register_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "securepass123",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {
            "email": "dup@example.com",
            "password": "securepass123",
        }
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409

    async def test_login_success(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "login@example.com", "password": "mypassword1"},
        )
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "login@example.com", "password": "mypassword1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_password(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "bad@example.com", "password": "correctpass1"},
        )
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "bad@example.com", "password": "wrongpass"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestDeviceEndpoints:
    async def test_list_devices_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/devices")
        assert response.status_code == 401  # Missing auth header
