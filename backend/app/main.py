import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import close_db, connect_db, ping_db
from .routers import alerts, chat, users
from .services.heartbeat import heartbeat_monitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("aegis")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    if await ping_db():
        logger.info("MongoDB connected: %s", settings.mongodb_db)
    else:
        logger.warning("MongoDB NOT reachable - running without persistence")
    monitor = asyncio.create_task(heartbeat_monitor())
    yield
    monitor.cancel()
    await close_db()


app = FastAPI(title="Aegis Guardian API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(alerts.router)
app.include_router(chat.router)


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
        "use_llm": settings.use_llm,
        "qwen_model": settings.qwen_model_path,
        "toxic_bert": settings.toxic_bert_path,
    }