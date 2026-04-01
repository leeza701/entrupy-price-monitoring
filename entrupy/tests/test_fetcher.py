"""Tests for data fetcher and normalization."""
import json
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Product, PriceHistory, PriceEvent
from app.fetcher import (
    normalize_grailed, normalize_fashionphile, normalize_firstdibs,
    upsert_product,
)


class TestNormalization:
    """Test marketplace data normalization."""

    def test_normalize_grailed(self):
        """Grailed items should normalize to common schema."""
        item = {
            "id": "g-100",
            "title": "Gucci Belt",
            "designer": "Gucci",
            "category": "Accessories",
            "size": "34",
            "condition": "Excellent",
            "price": 350.0,
            "currency": "USD",
            "description": "A belt",
            "image_url": "https://img.jpg",
            "url": "https://grailed.com/123",
            "seller": "user1",
            "listed_at": "2025-01-01T00:00:00Z",
        }
        result = normalize_grailed(item)
        assert result["external_id"] == "g-100"
        assert result["source"] == "grailed"
        assert result["brand"] == "Gucci"
        assert result["current_price"] == 350.0

        
        meta = json.loads(result["metadata_json"])
        assert meta["seller"] == "user1"
        assert meta["size"] == "34"

    def test_normalize_fashionphile(self):
        """Fashionphile items should normalize correctly."""
        item = {
            "item_id": "fp-200",
            "name": "Chanel Flap",
            "brand": "Chanel",
            "category": "Handbags",
            "condition_grade": "Very Good",
            "price": 5500.0,
            "original_retail_price": 8800.0,
            "currency": "USD",
            "material": "Lambskin",
            "color": "Black",
            "description": "Classic flap",
            "image_url": "https://img2.jpg",
            "url": "https://fashionphile.com/456",
        }
        result = normalize_fashionphile(item)
        assert result["external_id"] == "fp-200"
        assert result["source"] == "fashionphile"
        assert result["title"] == "Chanel Flap"
        assert result["original_price"] == 8800.0
        assert result["condition"] == "Very Good"

        meta = json.loads(result["metadata_json"])
        assert meta["material"] == "Lambskin"

    def test_normalize_firstdibs(self):
        """1stDibs items should normalize correctly."""
        item = {
            "id": "1d-300",
            "title": "Art Deco Ring",
            "creator": "Tiffany",
            "category": "Jewelry",
            "period": "Art Deco",
            "materials": ["Platinum", "Diamond"],
            "dimensions": "Size 6",
            "price": 9000.0,
            "currency": "USD",
            "description": "A ring",
            "image_url": "https://img3.jpg",
            "url": "https://1stdibs.com/789",
            "dealer": "Gallery X",
        }
        result = normalize_firstdibs(item)
        assert result["external_id"] == "1d-300"
        assert result["source"] == "1stdibs"
        assert result["brand"] == "Tiffany"

        meta = json.loads(result["metadata_json"])
        assert meta["dealer"] == "Gallery X"
        assert "Platinum" in meta["materials"]


class TestUpsert:
    """Test product upsert and price change detection."""

    @pytest.mark.asyncio
    async def test_insert_new_product(self, db_session: AsyncSession):
        """Upserting a new product should mark it as new."""
        normalized = {
            "external_id": "new-001",
            "source": "grailed",
            "title": "New Product",
            "brand": "TestBrand",
            "category": "Shoes",
            "current_price": 500.0,
            "original_price": None,
            "currency": "USD",
            "condition": "New",
            "description": "test",
            "image_url": None,
            "url": None,
            "metadata_json": "{}",
        }
        result = await upsert_product(db_session, normalized)
        await db_session.commit()

        assert result["is_new"] is True
        assert result["price_changed"] is False

        
        db_result = await db_session.execute(
            select(Product).where(Product.external_id == "new-001")
        )
        product = db_result.scalars().first()
        assert product is not None
        assert product.current_price == 500.0

        
        ph_result = await db_session.execute(
            select(PriceHistory).where(PriceHistory.product_id == product.id)
        )
        entries = ph_result.scalars().all()
        assert len(entries) == 1
        assert entries[0].price == 500.0

    @pytest.mark.asyncio
    async def test_price_change_detection(self, db_session: AsyncSession):
        """Upserting with a different price should detect the change."""
       
        normalized = {
            "external_id": "pc-001",
            "source": "fashionphile",
            "title": "Price Test",
            "brand": "TestBrand",
            "category": "Bags",
            "current_price": 1000.0,
            "original_price": None,
            "currency": "USD",
            "condition": None,
            "description": None,
            "image_url": None,
            "url": None,
            "metadata_json": "{}",
        }
        await upsert_product(db_session, normalized)
        await db_session.commit()

        
        normalized["current_price"] = 850.0
        result = await upsert_product(db_session, normalized)
        await db_session.commit()

        assert result["is_new"] is False
        assert result["price_changed"] is True
        assert result["old_price"] == 1000.0

        
        pe_result = await db_session.execute(
            select(PriceEvent).where(PriceEvent.source == "fashionphile")
        )
        events = pe_result.scalars().all()
        assert len(events) == 1
        assert events[0].old_price == 1000.0
        assert events[0].new_price == 850.0
        assert events[0].change_pct == -15.0  # (850-1000)/1000 * 100

    @pytest.mark.asyncio
    async def test_no_change_same_price(self, db_session: AsyncSession):
        """Upserting with the same price should not trigger a price change."""
        normalized = {
            "external_id": "nc-001",
            "source": "1stdibs",
            "title": "No Change Product",
            "brand": "TestBrand",
            "category": "Jewelry",
            "current_price": 2000.0,
            "original_price": None,
            "currency": "USD",
            "condition": None,
            "description": None,
            "image_url": None,
            "url": None,
            "metadata_json": "{}",
        }
        await upsert_product(db_session, normalized)
        await db_session.commit()

       
        result = await upsert_product(db_session, normalized)
        await db_session.commit()

        assert result["is_new"] is False
        assert result["price_changed"] is False
