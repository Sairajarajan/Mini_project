import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection

from .. import database
from ..models import User

logger = logging.getLogger("aegis.users")
router = APIRouter(prefix="/users", tags=["users"])


def _coll() -> AsyncIOMotorCollection:
    return database.db.users


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    for key, value in doc.items():
        if isinstance(value, datetime) and value.tzinfo is None:
            doc[key] = value.replace(tzinfo=timezone.utc)
    return doc


@router.post("/upsert")
async def upsert_user(user: User):
    coll = _coll()
    doc = user.model_dump()
    doc["_id"] = user.google_id
    await coll.replace_one({"_id": user.google_id}, doc, upsert=True)
    return {"ok": True, "user_id": user.google_id}


@router.get("/{user_id}")
async def get_user(user_id: str):
    doc = await _coll().find_one({"_id": user_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _clean(doc)


@router.get("")
async def list_users():
    cursor = _coll().find({}, {"_id": 1, "name": 1, "email": 1})
    return [{"user_id": u["_id"], "name": u.get("name", u["_id"]), "email": u.get("email", "")} async for u in cursor]


@router.delete("/{user_id}")
async def delete_user(user_id: str):
    res = await _coll().delete_one({"_id": user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    await database.db.chat_log.delete_many({"sender_id": user_id, "recipient_id": user_id})
    await database.db.alert_records.delete_many({"user_id": user_id})
    return {"ok": True, "user_id": user_id}


@router.post("/heartbeat")
async def heartbeat(user_id: str):
    now = datetime.now(timezone.utc)
    res = await _coll().update_one(
        {"_id": user_id},
        {"$set": {"last_heartbeat": now}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True, "last_heartbeat": now.isoformat()}


async def users_stale(hours: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cursor = _coll().find(
        {
            "last_heartbeat": {"$lt": cutoff},
            "alert_email_sent_for_inactive": {"$ne": True},
        }
    )
    return [u async for u in cursor]


async def mark_inactive_alerted(user_id: str) -> None:
    await _coll().update_one({"_id": user_id}, {"$set": {"alert_email_sent_for_inactive": True}})