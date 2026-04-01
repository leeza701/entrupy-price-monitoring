"""Shared test fixtures."""
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["SYNC_DATABASE_URL"] = "sqlite://"

from app.database import Base, get_session, Product, PriceHistory, PriceEvent
from app.main import app


@pytest_asyncio.fixture
async def db_session():
    """Provide a clean in-memory database session for each test."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """Provide an async test client with overridden DB dependency."""
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def api_headers():
    """Default API headers with valid key."""
    return {"X-API-Key": "demo-key-1"}


@pytest_asyncio.fixture
async def sample_product(db_session):
    """Insert a sample product and return it."""
    product = Product(
        external_id="test-001",
        source="grailed",
        title="Test Gucci Bag",
        brand="Gucci",
        category="Bags",
        current_price=1500.00,
        original_price=2000.00,
        currency="USD",
        condition="excellent",
        description="A test product",
    )
    db_session.add(product)
    await db_session.flush()

    db_session.add(PriceHistory(
        product_id=product.id,
        price=1500.00,
        source="grailed",
    ))
    await db_session.commit()
    await db_session.refresh(product)
    return product
