"""
Integration tests for API endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(test_client: AsyncClient):
    """Test root endpoint returns project info."""
    response = await test_client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "project" in data
    assert "version" in data
    assert "disclaimer" in data


@pytest.mark.asyncio
async def test_list_customers(test_client: AsyncClient):
    """Test listing customers endpoint."""
    response = await test_client.get("/api/v1/customers")

    assert response.status_code == 200
    data = response.json()
    assert "customers" in data
    assert "total" in data
    assert isinstance(data["customers"], list)
    assert isinstance(data["total"], int)
    if data["customers"]:
        customer = data["customers"][0]
        assert "id" in customer
        assert "name" in customer
        assert "email" in customer
        assert "account_type" in customer


@pytest.mark.asyncio
async def test_list_customers_pagination(test_client: AsyncClient):
    """Test customers endpoint with limit and offset."""
    response = await test_client.get("/api/v1/customers?limit=5&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert len(data["customers"]) <= 5


@pytest.mark.asyncio
async def test_health_endpoint(test_client: AsyncClient):
    """Test health check endpoint."""
    response = await test_client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "app_name" in data
    assert "version" in data
    assert "database_connected" in data
    assert "embedding_provider" in data
    assert "mock_mode" in data


@pytest.mark.asyncio
async def test_run_task_invalid_customer(test_client: AsyncClient):
    """Test running task with invalid customer ID."""
    response = await test_client.post(
        "/api/v1/tasks/run",
        json={
            "customer_id": "invalid-uuid",
            "analysis_window_days": 30,
            "anomaly_threshold": 0.8,
        },
    )
    
    # Should fail validation
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_get_task_not_found(test_client: AsyncClient):
    """Test getting non-existent task."""
    response = await test_client.get(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000000"
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_audit_not_found(test_client: AsyncClient):
    """Test getting audit trail for non-existent task."""
    response = await test_client.get(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000000/audit"
    )
    
    assert response.status_code == 404


# Note: Full end-to-end tests require a real database with pgvector
# which is not available in SQLite. These tests provide basic coverage.
