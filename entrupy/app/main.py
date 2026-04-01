"""FastAPI application entry point."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import init_db, Product, async_engine
from app.middleware import UsageTrackingMiddleware
from app.notifications import start_notification_worker
from app.routers import products, analytics, refresh
from app.schemas import HealthResponse
from sqlalchemy import select, func
from app.database import AsyncSessionLocal, get_session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: init DB on startup, cleanup on shutdown."""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database ready.")
    notification_task = asyncio.create_task(start_notification_worker(interval=30.0))

    yield
    notification_task.cancel()
    try:
        await notification_task
    except asyncio.CancelledError:
        pass
    await async_engine.dispose()


app = FastAPI(
    title="Product Price Monitor",
    description="Collects product data from luxury marketplaces, tracks price changes, "
                "and notifies consumers via webhooks and event polling.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(UsageTrackingMiddleware)
app.include_router(products.router)
app.include_router(analytics.router)
app.include_router(refresh.router)

import os
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
async def health_check(db: AsyncSession = Depends(get_session)):
    """Health check endpoint (no auth required)."""
    try:
        result = await db.execute(select(func.count(Product.id)))
        count = result.scalar() or 0
        return HealthResponse(status="ok", database="connected", products_count=count)
    except Exception as e:
        return HealthResponse(status="error", database=str(e), products_count=0)

@app.get("/", include_in_schema=False)
async def serve_dashboard():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/products", include_in_schema=False)
async def serve_products_page():
    return FileResponse(os.path.join(STATIC_DIR, "products.html"))


@app.get("/product/{product_id}", include_in_schema=False)
async def serve_product_detail(product_id: int):
    return FileResponse(os.path.join(STATIC_DIR, "product.html"))

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
