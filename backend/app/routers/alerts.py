import logging

from fastapi import APIRouter

from ..database import db

logger = logging.getLogger("aegis.alerts")
router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(limit: int = 50):
    cursor = db.alert_records.find().sort("created_at", -1).limit(limit)
    return [a async for a in cursor]


@router.get("/{user_id}")
async def alerts_for_user(user_id: str, limit: int = 20):
    cursor = db.alert_records.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return [a async for a in cursor]