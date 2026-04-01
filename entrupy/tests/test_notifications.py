"""Tests for the notification system."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import PriceEvent
from app.notifications import deliver_webhook


class TestWebhookDelivery:
    """Test webhook delivery with retry logic."""

    @pytest.mark.asyncio
    async def test_successful_delivery(self):
        """Webhook delivery should return True on 200 response."""
       
        mock_response = MagicMock()
        mock_response.status = 200

        
        async def mock_post(*args, **kwargs):
            return mock_response

        
        with patch("app.notifications.aiohttp") as mock_aiohttp:
           
            mock_aiohttp.ClientTimeout = MagicMock

           
            mock_session_instance = MagicMock()

            
            post_cm = MagicMock()
            post_cm.__aenter__ = AsyncMock(return_value=mock_response)
            post_cm.__aexit__ = AsyncMock(return_value=False)
            mock_session_instance.post = MagicMock(return_value=post_cm)

           
            session_cm = MagicMock()
            session_cm.__aenter__ = AsyncMock(return_value=mock_session_instance)
            session_cm.__aexit__ = AsyncMock(return_value=False)
            mock_aiohttp.ClientSession = MagicMock(return_value=session_cm)

            result = await deliver_webhook(
                "https://example.com/webhook",
                {"event": "test"},
                max_retries=1,
                base_delay=0.01,
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_failed_delivery_exhausts_retries(self):
        """Webhook delivery should return False after exhausting retries."""
        mock_response = MagicMock()
        mock_response.status = 500

        with patch("app.notifications.aiohttp") as mock_aiohttp:
            mock_aiohttp.ClientTimeout = MagicMock

            mock_session_instance = MagicMock()

            post_cm = MagicMock()
            post_cm.__aenter__ = AsyncMock(return_value=mock_response)
            post_cm.__aexit__ = AsyncMock(return_value=False)
            mock_session_instance.post = MagicMock(return_value=post_cm)

            session_cm = MagicMock()
            session_cm.__aenter__ = AsyncMock(return_value=mock_session_instance)
            session_cm.__aexit__ = AsyncMock(return_value=False)
            mock_aiohttp.ClientSession = MagicMock(return_value=session_cm)

            result = await deliver_webhook(
                "https://example.com/webhook",
                {"event": "test"},
                max_retries=2,
                base_delay=0.01,
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_delivery_retries_on_exception(self):
        """Webhook delivery should retry on network exceptions."""
        with patch("app.notifications.aiohttp") as mock_aiohttp:
            mock_aiohttp.ClientTimeout = MagicMock

            session_cm = MagicMock()
            session_cm.__aenter__ = AsyncMock(side_effect=ConnectionError("Network error"))
            session_cm.__aexit__ = AsyncMock(return_value=False)
            mock_aiohttp.ClientSession = MagicMock(return_value=session_cm)

            result = await deliver_webhook(
                "https://example.com/webhook",
                {"event": "test"},
                max_retries=2,
                base_delay=0.01,
            )
            assert result is False


class TestPriceEvents:
    """Test price event creation and storage."""

    @pytest.mark.asyncio
    async def test_event_stored_correctly(self, db_session: AsyncSession):
        """Price events should be stored with correct data."""
        from app.database import Product

        product = Product(
            external_id="evt-001",
            source="grailed",
            title="Event Test Product",
            brand="TestBrand",
            category="Bags",
            current_price=1000.0,
        )
        db_session.add(product)
        await db_session.flush()

        event = PriceEvent(
            product_id=product.id,
            old_price=1200.0,
            new_price=1000.0,
            change_pct=-16.67,
            source="grailed",
            delivered=False,
        )
        db_session.add(event)
        await db_session.commit()

        result = await db_session.execute(
            select(PriceEvent).where(PriceEvent.product_id == product.id)
        )
        stored_event = result.scalars().first()
        assert stored_event is not None
        assert stored_event.old_price == 1200.0
        assert stored_event.new_price == 1000.0
        assert stored_event.delivered is False
