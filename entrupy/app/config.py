"""Application configuration."""
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./price_monitor.db")
SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "sqlite:///./price_monitor.db")

API_KEYS = os.getenv("API_KEYS", "demo-key-1,demo-key-2").split(",")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

FETCH_CONCURRENCY = int(os.getenv("FETCH_CONCURRENCY", "5"))
FETCH_RETRY_ATTEMPTS = int(os.getenv("FETCH_RETRY_ATTEMPTS", "3"))
FETCH_RETRY_BASE_DELAY = float(os.getenv("FETCH_RETRY_BASE_DELAY", "1.0"))

WEBHOOK_RETRY_ATTEMPTS = int(os.getenv("WEBHOOK_RETRY_ATTEMPTS", "3"))
WEBHOOK_RETRY_BASE_DELAY = float(os.getenv("WEBHOOK_RETRY_BASE_DELAY", "2.0"))
