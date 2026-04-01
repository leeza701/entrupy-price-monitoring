"""Tests for API endpoints."""
import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Health endpoint should return 200 without auth."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "products_count" in data


@pytest.mark.asyncio
async def test_auth_required_without_key(client: AsyncClient):
    """Endpoints should return 401 without API key."""
    resp = await client.get("/api/products")
    assert resp.status_code == 401
    assert "Missing API key" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_auth_required_invalid_key(client: AsyncClient):
    """Endpoints should return 401 with invalid API key."""
    resp = await client.get("/api/products", headers={"X-API-Key": "bad-key"})
    assert resp.status_code == 401
    assert "Invalid API key" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_list_products_empty(client: AsyncClient, api_headers):
    """List products should return empty list when no data."""
    resp = await client.get("/api/products", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["pages"] == 0


@pytest.mark.asyncio
async def test_list_products_with_data(client: AsyncClient, api_headers, sample_product):
    """List products should return inserted products."""
    resp = await client.get("/api/products", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Test Gucci Bag"
    assert data["items"][0]["source"] == "grailed"


@pytest.mark.asyncio
async def test_list_products_filter_by_source(client: AsyncClient, api_headers, sample_product):
    """Filter by source should only return matching products."""
   
    resp = await client.get("/api/products?source=grailed", headers=api_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

  
    resp = await client.get("/api/products?source=fashionphile", headers=api_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_products_filter_by_price_range(client: AsyncClient, api_headers, sample_product):
    """Filter by price range should work correctly."""
    # Product has price 1500
    resp = await client.get("/api/products?min_price=1000&max_price=2000", headers=api_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    resp = await client.get("/api/products?min_price=2000", headers=api_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_product_detail_found(client: AsyncClient, api_headers, sample_product):
    """Product detail should return full info with price history."""
    resp = await client.get(f"/api/products/{sample_product.id}", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Gucci Bag"
    assert data["current_price"] == 1500.0
    assert len(data["price_history"]) >= 1


@pytest.mark.asyncio
async def test_product_detail_not_found(client: AsyncClient, api_headers):
    """Product detail should 404 for non-existent ID."""
    resp = await client.get("/api/products/99999", headers=api_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_analytics_endpoint(client: AsyncClient, api_headers, sample_product):
    """Analytics endpoint should return aggregate data."""
    resp = await client.get("/api/analytics", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_products"] == 1
    assert data["total_sources"] >= 1
    assert len(data["by_source"]) >= 1
    assert data["overall_avg_price"] == 1500.0


@pytest.mark.asyncio
async def test_webhook_registration(client: AsyncClient, api_headers):
    """Should be able to register a webhook."""
    resp = await client.post(
        "/api/webhooks",
        json={"url": "https://example.com/webhook"},
        headers=api_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"] == "https://example.com/webhook"
    assert data["active"] is True


@pytest.mark.asyncio
async def test_webhook_invalid_url(client: AsyncClient, api_headers):
    """Should reject invalid webhook URLs."""
    resp = await client.post(
        "/api/webhooks",
        json={"url": "not-a-url"},
        headers=api_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_events_endpoint(client: AsyncClient, api_headers):
    """Events endpoint should return list (empty initially)."""
    resp = await client.get("/api/events", headers=api_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
