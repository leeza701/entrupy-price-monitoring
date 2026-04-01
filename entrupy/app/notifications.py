"""Notification system — event log + webhook delivery with retry."""
import asyncio
import json
import logging
from typing import List

import aiohttp
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import WEBHOOK_RETRY_ATTEMPTS, WEBHOOK_RETRY_BASE_DELAY
from app.database import PriceEvent, Webhook, AsyncSessionLocal

logger = logging.getLogger(__name__)


async def deliver_webhook(
    webhook_url: str,
    payload: dict,
    max_retries: int = WEBHOOK_RETRY_ATTEMPTS,
    base_delay: float = WEBHOOK_RETRY_BASE_DELAY,
) -> bool:
    """Deliver a payload to a webhook URL with exponential backoff retry.

    Returns True if delivery succeeded, False otherwise.
    """
    for attempt in range(1, max_retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if 200 <= resp.status < 300:
                        logger.info("Webhook delivered to %s (attempt %d)", webhook_url, attempt)
                        return True
                    else:
                        logger.warning(
                            "Webhook %s returned %d (attempt %d/%d)",
                            webhook_url, resp.status, attempt, max_retries,
                        )
        except Exception as exc:
            logger.warning(
                "Webhook delivery to %s failed (attempt %d/%d): %s",
                webhook_url, attempt, max_retries, exc,
            )

        if attempt < max_retries:
            delay = base_delay * (2 ** (attempt - 1))
            await asyncio.sleep(delay)

    return False


async def process_undelivered_events():
    """Background task: find undelivered price events and send them to webhooks.

    - Events are persisted *before* delivery is attempted (no lost events).
    - Delivery is retried with exponential backoff.
    - Non-blocking: runs as a background asyncio task.
    """
    async with AsyncSessionLocal() as db:
       
        result = await db.execute(select(Webhook).where(Webhook.active == True))
        webhooks = result.scalars().all()

        if not webhooks:
            return

        
        result = await db.execute(
            select(PriceEvent).where(PriceEvent.delivered == False).limit(100)
        )
        events = result.scalars().all()

        if not events:
            return

        logger.info("Processing %d undelivered events to %d webhooks", len(events), len(webhooks))

        for event in events:
            payload = {
                "event_type": "price_change",
                "event_id": event.id,
                "product_id": event.product_id,
                "old_price": event.old_price,
                "new_price": event.new_price,
                "change_pct": event.change_pct,
                "source": event.source,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }

            
            all_delivered = True
            for webhook in webhooks:
                success = await deliver_webhook(webhook.url, payload)
                if not success:
                    all_delivered = False
                    logger.error(
                        "Failed to deliver event %d to webhook %s after %d retries",
                        event.id, webhook.url, WEBHOOK_RETRY_ATTEMPTS,
                    )

            
            if all_delivered:
                await db.execute(
                    update(PriceEvent).where(PriceEvent.id == event.id).values(delivered=True)
                )

        await db.commit()


async def start_notification_worker(interval: float = 10.0):
    """Start a background loop that processes undelivered events periodically."""
    while True:
        try:
            await process_undelivered_events()
        except Exception as exc:
            logger.error("Notification worker error: %s", exc, exc_info=True)
        await asyncio.sleep(interval)
