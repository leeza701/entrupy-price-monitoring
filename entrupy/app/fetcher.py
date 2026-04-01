"""Async data fetcher with retry logic and marketplace normalization."""
import asyncio
import json
import logging
import os
import random
from typing import List, Dict, Any, Optional

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import (
    DATA_DIR, FETCH_CONCURRENCY, FETCH_RETRY_ATTEMPTS, FETCH_RETRY_BASE_DELAY,
)
from app.database import Product, PriceHistory, PriceEvent, AsyncSessionLocal

logger = logging.getLogger(__name__)




def normalize_grailed(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a Grailed listing to the common product schema."""
    return {
        "external_id": str(item["id"]),
        "source": "grailed",
        "title": item["title"],
        "brand": item.get("designer"),
        "category": item.get("category"),
        "current_price": float(item["price"]),
        "original_price": None,
        "currency": item.get("currency", "USD"),
        "condition": item.get("condition"),
        "description": item.get("description"),
        "image_url": item.get("image_url"),
        "url": item.get("url"),
        "metadata_json": json.dumps({
            "seller": item.get("seller"),
            "size": item.get("size"),
            "listed_at": item.get("listed_at"),
        }),
    }


def normalize_fashionphile(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a Fashionphile listing to the common product schema."""
    return {
        "external_id": str(item["item_id"]),
        "source": "fashionphile",
        "title": item["name"],
        "brand": item.get("brand"),
        "category": item.get("category"),
        "current_price": float(item["price"]),
        "original_price": item.get("original_retail_price"),
        "currency": item.get("currency", "USD"),
        "condition": item.get("condition_grade"),
        "description": item.get("description"),
        "image_url": item.get("image_url"),
        "url": item.get("url"),
        "metadata_json": json.dumps({
            "material": item.get("material"),
            "color": item.get("color"),
        }),
    }


def normalize_firstdibs(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a 1stDibs listing to the common product schema."""
    return {
        "external_id": str(item["id"]),
        "source": "1stdibs",
        "title": item["title"],
        "brand": item.get("creator"),
        "category": item.get("category"),
        "current_price": float(item["price"]),
        "original_price": None,
        "currency": item.get("currency", "USD"),
        "condition": None,
        "description": item.get("description"),
        "image_url": item.get("image_url"),
        "url": item.get("url"),
        "metadata_json": json.dumps({
            "period": item.get("period"),
            "materials": item.get("materials"),
            "dimensions": item.get("dimensions"),
            "dealer": item.get("dealer"),
        }),
    }


NORMALIZERS = {
    "grailed": normalize_grailed,
    "fashionphile": normalize_fashionphile,
    "1stdibs": normalize_firstdibs,
}

SOURCE_FILES = {
    "grailed": "grailed.json",
    "fashionphile": "fashionphile.json",
    "1stdibs": "firstdibs.json",
}




async def fetch_with_retry(
    source: str,
    session: Optional[aiohttp.ClientSession] = None,
) -> List[Dict[str, Any]]:
    """Fetch data for a marketplace source with exponential-backoff retry.

    In this demo, we read from local JSON files but simulate network latency
    and occasional failures so the retry logic is exercised.
    """
    filepath = os.path.join(DATA_DIR, SOURCE_FILES[source])

    for attempt in range(1, FETCH_RETRY_ATTEMPTS + 1):
        try:
           
            await asyncio.sleep(random.uniform(0.05, 0.2))

            with open(filepath, "r") as f:
                data = json.load(f)

            logger.info("Fetched %d items from %s (attempt %d)", len(data), source, attempt)
            return data

        except Exception as exc:
            delay = FETCH_RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(
                "Fetch attempt %d/%d for %s failed: %s — retrying in %.1fs",
                attempt, FETCH_RETRY_ATTEMPTS, source, exc, delay,
            )
            if attempt == FETCH_RETRY_ATTEMPTS:
                raise
            await asyncio.sleep(delay)

    return []  




async def upsert_product(
    db: AsyncSession, normalized: Dict[str, Any]
) -> Dict[str, Any]:
    """Insert or update a product; detect price changes.

    Returns a dict with keys:
      - is_new: bool
      - price_changed: bool
      - old_price: float | None
    """
    result = await db.execute(
        select(Product).where(
            Product.external_id == normalized["external_id"],
            Product.source == normalized["source"],
        )
    )
    existing = result.scalars().first()

    if existing is None:
       
        product = Product(**normalized)
        db.add(product)
        await db.flush()

        
        db.add(PriceHistory(
            product_id=product.id,
            price=product.current_price,
            source=product.source,
        ))

        return {"is_new": True, "price_changed": False, "old_price": None, "product": product}

    
    old_price = existing.current_price
    new_price = normalized["current_price"]
    price_changed = abs(old_price - new_price) > 0.01

    
    for key, value in normalized.items():
        if key != "metadata_json" or value:
            setattr(existing, key, value)

    if price_changed:
      
        db.add(PriceHistory(
            product_id=existing.id,
            price=new_price,
            source=existing.source,
        ))

        
        change_pct = ((new_price - old_price) / old_price * 100) if old_price else 0
        db.add(PriceEvent(
            product_id=existing.id,
            old_price=old_price,
            new_price=new_price,
            change_pct=round(change_pct, 2),
            source=existing.source,
        ))

    return {"is_new": False, "price_changed": price_changed, "old_price": old_price, "product": existing}




async def refresh_source(source: str) -> Dict[str, Any]:
    """Refresh data from a single marketplace source.

    Returns stats: products_processed, new_products, price_changes, errors.
    """
    stats = {"source": source, "products_processed": 0, "new_products": 0, "price_changes": 0, "errors": []}

    try:
        raw_data = await fetch_with_retry(source)
    except Exception as exc:
        stats["errors"].append(f"Failed to fetch {source}: {exc}")
        return stats

    normalizer = NORMALIZERS[source]

    async with AsyncSessionLocal() as db:
        for item in raw_data:
            try:
                normalized = normalizer(item)
                result = await upsert_product(db, normalized)
                stats["products_processed"] += 1
                if result["is_new"]:
                    stats["new_products"] += 1
                if result["price_changed"]:
                    stats["price_changes"] += 1
            except Exception as exc:
                stats["errors"].append(f"Error processing {item.get('id', item.get('item_id', '?'))}: {exc}")
                logger.error("Error processing item from %s: %s", source, exc, exc_info=True)

        await db.commit()

    return stats


async def refresh_all_sources() -> List[Dict[str, Any]]:
    """Refresh data from all marketplace sources concurrently."""
    semaphore = asyncio.Semaphore(FETCH_CONCURRENCY)

    async def _bounded(source: str):
        async with semaphore:
            return await refresh_source(source)

    tasks = [_bounded(source) for source in SOURCE_FILES]
    return await asyncio.gather(*tasks)
