from motor.motor_asyncio import AsyncIOMotorClient

from .config import settings

_client: AsyncIOMotorClient | None = None
db = None


async def connect_db() -> None:
    global _client, db
    _client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    db = _client[settings.mongodb_db]


async def ping_db() -> bool:
    if db is None:
        return False
    try:
        await db.command("ping")
        return True
    except Exception:
        return False


async def close_db() -> None:
    global _client, db
    if _client is not None:
        _client.close()
    _client = None
    db = None