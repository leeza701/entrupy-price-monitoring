"""Pydantic schemas for request/response validation."""
from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field



class PriceHistoryOut(BaseModel):
    id: int
    price: float
    source: str
    recorded_at: datetime

    class Config:
        from_attributes = True


class PriceEventOut(BaseModel):
    id: int
    product_id: int
    old_price: Optional[float] = None
    new_price: Optional[float] = None
    change_pct: Optional[float] = None
    source: str
    created_at: datetime
    delivered: bool

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    external_id: str
    source: str
    title: str
    brand: Optional[str] = None
    category: Optional[str] = None
    current_price: float
    original_price: Optional[float] = None
    currency: str = "USD"
    condition: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    url: Optional[str] = None


class ProductOut(ProductBase):
    id: int
    first_seen_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductDetailOut(ProductOut):
    price_history: List[PriceHistoryOut] = []
    price_events: List[PriceEventOut] = []

    class Config:
        from_attributes = True



class ProductListParams(BaseModel):
    source: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class PaginatedProducts(BaseModel):
    items: List[ProductOut]
    total: int
    page: int
    per_page: int
    pages: int



class SourceStats(BaseModel):
    source: str
    count: int
    avg_price: float
    min_price: float
    max_price: float


class CategoryStats(BaseModel):
    category: str
    count: int
    avg_price: float


class AnalyticsOut(BaseModel):
    total_products: int
    total_sources: int
    by_source: List[SourceStats]
    by_category: List[CategoryStats]
    overall_avg_price: float
    price_change_events: int



class WebhookCreate(BaseModel):
    url: str


class WebhookOut(BaseModel):
    id: int
    url: str
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RefreshResult(BaseModel):
    source: str
    products_processed: int
    new_products: int
    price_changes: int
    errors: List[str] = []


class RefreshResponse(BaseModel):
    results: List[RefreshResult]
    total_products_processed: int
    total_price_changes: int

class UsageStats(BaseModel):
    total_requests: int
    by_endpoint: dict
    by_api_key: dict


class HealthResponse(BaseModel):
    status: str
    database: str
    products_count: int
