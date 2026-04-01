"""Refresh, events, webhooks, and usage endpoints."""
import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_api_key
from app.database import PriceEvent, Webhook, get_session
from app.schemas import (
    RefreshResponse, RefreshResult,
    PriceEventOut, WebhookCreate, WebhookOut, UsageStats,
)
from app.fetcher import refresh_all_sources
from app.notifications import process_undelivered_events

router = APIRouter(prefix="/api", tags=["operations"])


@router.post("/refresh", response_model=RefreshResponse)
async def trigger_refresh(
    api_key: str = Depends(require_api_key),
):
    """Trigger a data refresh from all marketplace sources.

    After fetching, kicks off a non-blocking notification delivery.
    """
    results = await refresh_all_sources()

   
    asyncio.create_task(process_undelivered_events())

    total_processed = sum(r["products_processed"] for r in results)
    total_changes = sum(r["price_changes"] for r in results)

    return RefreshResponse(
        results=[RefreshResult(**r) for r in results],
        total_products_processed=total_processed,
        total_price_changes=total_changes,
    )


@router.get("/events", response_model=List[PriceEventOut])
async def list_events(
    limit: int = Query(50, ge=1, le=200),
    undelivered_only: bool = Query(False),
    api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_session),
):
    """List price change events (polling endpoint)."""
    query = select(PriceEvent)
    if undelivered_only:
        query = query.where(PriceEvent.delivered == False)
    query = query.order_by(PriceEvent.created_at.desc()).limit(limit)

    result = await db.execute(query)
    events = result.scalars().all()
    return [PriceEventOut.model_validate(e) for e in events]


@router.post("/webhooks", response_model=WebhookOut, status_code=201)
async def register_webhook(
    webhook: WebhookCreate,
    api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_session),
):
    """Register a new webhook URL for price change notifications."""
    if not webhook.url or not webhook.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid webhook URL. Must start with http:// or https://")

    new_webhook = Webhook(url=webhook.url)
    db.add(new_webhook)
    await db.commit()
    await db.refresh(new_webhook)
    return WebhookOut.model_validate(new_webhook)


@router.get("/webhooks", response_model=List[WebhookOut])
async def list_webhooks(
    api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_session),
):
    """List all registered webhooks."""
    result = await db.execute(select(Webhook).order_by(Webhook.created_at.desc()))
    return [WebhookOut.model_validate(w) for w in result.scalars().all()]


@router.get("/usage", response_model=UsageStats)
async def get_usage(
    api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_session),
):
    """Get API usage statistics."""
   
    total_result = await db.execute(text("SELECT COUNT(*) FROM api_usage"))
    total = total_result.scalar() or 0

    
    ep_result = await db.execute(
        text("SELECT endpoint, COUNT(*) as cnt FROM api_usage GROUP BY endpoint ORDER BY cnt DESC")
    )
    by_endpoint = {row[0]: row[1] for row in ep_result.all()}

    
    key_result = await db.execute(
        text("SELECT api_key, COUNT(*) as cnt FROM api_usage GROUP BY api_key ORDER BY cnt DESC")
    )
    by_api_key = {row[0]: row[1] for row in key_result.all()}

    return UsageStats(
        total_requests=total,
        by_endpoint=by_endpoint,
        by_api_key=by_api_key,
    )
