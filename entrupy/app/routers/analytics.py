"""Analytics endpoints — aggregate stats by source, category, etc."""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_api_key
from app.database import Product, PriceEvent, get_session
from app.schemas import AnalyticsOut, SourceStats, CategoryStats

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsOut)
async def get_analytics(
    api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_session),
):
    """Get aggregate analytics: totals by source, averages by category, etc."""

 
    total_result = await db.execute(select(func.count(Product.id)))
    total_products = total_result.scalar() or 0

    avg_result = await db.execute(select(func.avg(Product.current_price)))
    overall_avg = round(avg_result.scalar() or 0, 2)

    source_query = select(
        Product.source,
        func.count(Product.id).label("count"),
        func.avg(Product.current_price).label("avg_price"),
        func.min(Product.current_price).label("min_price"),
        func.max(Product.current_price).label("max_price"),
    ).group_by(Product.source)

    source_result = await db.execute(source_query)
    by_source = [
        SourceStats(
            source=row.source,
            count=row.count,
            avg_price=round(row.avg_price, 2),
            min_price=row.min_price,
            max_price=row.max_price,
        )
        for row in source_result.all()
    ]

    cat_query = select(
        Product.category,
        func.count(Product.id).label("count"),
        func.avg(Product.current_price).label("avg_price"),
    ).where(Product.category.isnot(None)).group_by(Product.category)

    cat_result = await db.execute(cat_query)
    by_category = [
        CategoryStats(
            category=row.category,
            count=row.count,
            avg_price=round(row.avg_price, 2),
        )
        for row in cat_result.all()
    ]
    events_result = await db.execute(select(func.count(PriceEvent.id)))
    price_change_events = events_result.scalar() or 0

    return AnalyticsOut(
        total_products=total_products,
        total_sources=len(by_source),
        by_source=by_source,
        by_category=by_category,
        overall_avg_price=overall_avg,
        price_change_events=price_change_events,
    )
