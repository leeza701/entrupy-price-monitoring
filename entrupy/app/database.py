"""Database initialization, engine, session management, and schema creation."""
import json
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey,
    Index, UniqueConstraint, create_engine
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.sql import func

from app.config import DATABASE_URL, SYNC_DATABASE_URL

Base = declarative_base()

# Async engine and session
async_engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine for migrations / init
sync_engine = create_engine(SYNC_DATABASE_URL, echo=False)


# ── ORM Models ──────────────────────────────────────────────────────────────

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String, nullable=False)
    source = Column(String, nullable=False)  # 'grailed', 'fashionphile', '1stdibs'
    title = Column(String, nullable=False)
    brand = Column(String, index=True)
    category = Column(String, index=True)
    current_price = Column(Float, nullable=False)
    original_price = Column(Float)
    currency = Column(String, default="USD")
    condition = Column(String)
    description = Column(Text)
    image_url = Column(String)
    url = Column(String)
    metadata_json = Column(Text)  # JSON string for extra source-specific fields
    first_seen_at = Column(DateTime, server_default=func.now())
    last_updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("external_id", "source", name="uq_product_source"),
        Index("idx_products_source", "source"),
        Index("idx_products_price", "current_price"),
    )

    price_history = relationship("PriceHistory", back_populates="product", lazy="selectin")
    price_events = relationship("PriceEvent", back_populates="product", lazy="selectin")

    @property
    def extra_metadata(self):
        if self.metadata_json:
            return json.loads(self.metadata_json)
        return {}


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    price = Column(Float, nullable=False)
    source = Column(String, nullable=False)
    recorded_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_ph_product_id", "product_id"),
        Index("idx_ph_recorded_at", "recorded_at"),
    )

    product = relationship("Product", back_populates="price_history")


class PriceEvent(Base):
    __tablename__ = "price_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    old_price = Column(Float)
    new_price = Column(Float)
    change_pct = Column(Float)
    source = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    delivered = Column(Boolean, default=False)

    __table_args__ = (
        Index("idx_pe_delivered", "delivered"),
    )

    product = relationship("Product", back_populates="price_events")


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class ApiUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    api_key = Column(String, nullable=False)
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    status_code = Column(Integer)
    timestamp = Column(DateTime, server_default=func.now())


# ── Database lifecycle ───────────────────────────────────────────────────────

async def get_session() -> AsyncSession:
    """Dependency that yields a DB session."""
    async with AsyncSessionLocal() as session:
        yield session


def init_db():
    """Create all tables (synchronous, used at startup)."""
    Base.metadata.create_all(bind=sync_engine)


async def init_db_async():
    """Create all tables (async)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
