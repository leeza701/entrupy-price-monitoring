"""Product endpoints — list, filter, detail with price history."""
import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_api_key
from app.database import Product, PriceHistory, PriceEvent, get_session
from app.schemas import (
    ProductOut, ProductDetailOut, PaginatedProducts,
    PriceHistoryOut, PriceEventOut,
)
router = APIRouter(prefix="/api/products", tags=["products"])

@router.get("", response_model=PaginatedProducts)
async def list_products(
    source: str = Query(None, description="Filter by marketplace source"),
    category: str = Query(None, description="Filter by category"),
    brand: str = Query(None, description="Filter by brand"),
    min_price: float = Query(None, ge=0, description="Minimum price"),
    max_price: float = Query(None, ge=0, description="Maximum price"),
    search: str = Query(None, description="Search in title/description"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_session),
):
    """Browse and filter products with pagination."""
    query = select(Product)
    count_query = select(func.count(Product.id))

    if source:
        query = query.where(Product.source == source)
        count_query = count_query.where(Product.source == source)
    if category:
        query = query.where(Product.category == category)
        count_query = count_query.where(Product.category == category)
    if brand:
        query = query.where(Product.brand.ilike(f"%{brand}%"))
        count_query = count_query.where(Product.brand.ilike(f"%{brand}%"))
    if min_price is not None:
        query = query.where(Product.current_price >= min_price)
        count_query = count_query.where(Product.current_price >= min_price)
    if max_price is not None:
        query = query.where(Product.current_price <= max_price)
        count_query = count_query.where(Product.current_price <= max_price)
    if search:
        search_filter = or_(
            Product.title.ilike(f"%{search}%"),
            Product.description.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.order_by(Product.last_updated_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    products = result.scalars().all()

    return PaginatedProducts(
        items=[ProductOut.model_validate(p) for p in products],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.get("/{product_id}", response_model=ProductDetailOut)
async def get_product(
    product_id: int,
    api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_session),
):
    """Get a single product's details including full price history."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalars().first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    ph_result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.recorded_at.asc())
    )
    price_history = ph_result.scalars().all()

    pe_result = await db.execute(
        select(PriceEvent)
        .where(PriceEvent.product_id == product_id)
        .order_by(PriceEvent.created_at.desc())
    )
    price_events = pe_result.scalars().all()

    product_data = ProductDetailOut.model_validate(product)
    product_data.price_history = [PriceHistoryOut.model_validate(ph) for ph in price_history]
    product_data.price_events = [PriceEventOut.model_validate(pe) for pe in price_events]

    return product_data
