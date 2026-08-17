import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import close_db, connect_db, ping_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("aegis")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    if await ping_db():
        logger.info("MongoDB connected: %s", settings.mongodb_db)
    else:
        logger.warning("MongoDB NOT reachable - running without persistence")
    yield
    await close_db()


app = FastAPI(title="Aegis Guardian API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "db": await ping_db()}


@app.get("/config")
async def config_view():
    return {
        "email_mode": settings.email_mode,
        "heartbeat_inactive_hours": settings.heartbeat_inactive_hours,
        "risk_threshold_warn": settings.risk_threshold_warn,
        "risk_threshold_block": settings.risk_threshold_block,
    }