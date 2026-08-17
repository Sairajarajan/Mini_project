import logging
from datetime import datetime, timezone

from bson import ObjectId

from fastapi import APIRouter

from .. import database

logger = logging.getLogger("aegis.alerts")
router = APIRouter(prefix="/alerts", tags=["alerts"])


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    if isinstance(doc.get("_id"), ObjectId):
        doc["_id"] = str(doc["_id"])
    for key, value in doc.items():
        if isinstance(value, datetime) and value.tzinfo is None:
            doc[key] = value.replace(tzinfo=timezone.utc)
    return doc


@router.get("")
async def list_alerts(limit: int = 50):
    cursor = database.db.alert_records.find().sort("created_at", -1).limit(limit)
    return [_clean(a) async for a in cursor]


@router.get("/{user_id}")
async def alerts_for_user(user_id: str, limit: int = 20):
    cursor = database.db.alert_records.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return [_clean(a) async for a in cursor]