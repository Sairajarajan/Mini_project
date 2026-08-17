import asyncio
import logging
from datetime import datetime, timezone

from ..config import settings
from ..database import db
from ..services.email_service import alert_body, send_email

logger = logging.getLogger("aegis.heartbeat")


async def heartbeat_monitor():
    while True:
        try:
            cursor = db.users.find(
                {
                    "last_heartbeat": {"$ne": None},
                    "alert_email_sent_for_inactive": {"$ne": True},
                }
            )
            async for user in cursor:
                last = user["last_heartbeat"]
                if last is None:
                    continue
                if isinstance(last, str):
                    last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                else:
                    last_dt = last
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                age_hours = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
                if age_hours >= settings.heartbeat_inactive_hours:
                    parent = user.get("parent_email")
                    if parent:
                        await send_email(
                            parent,
                            "Aegis: App may have been uninstalled",
                            alert_body(
                                "app_inactive",
                                child_name=user.get("name", user["_id"]),
                                last_seen=last_dt.isoformat(),
                            ),
                        )
                        await db.alert_records.insert_one(
                            {
                                "alert_type": "app_inactive",
                                "user_id": user["_id"],
                                "parent_email": parent,
                                "message_text": "",
                                "sender_name": "",
                                "reason": f"Inactive for over {settings.heartbeat_inactive_hours}h",
                                "created_at": datetime.now(timezone.utc),
                            }
                        )
                    await db.users.update_one(
                        {"_id": user["_id"]},
                        {"$set": {"alert_email_sent_for_inactive": True}},
                    )
                    logger.info("Inactivity alert sent for %s", user["_id"])
        except Exception as exc:
            logger.error("heartbeat_monitor error: %s", exc)
        await asyncio.sleep(settings.heartbeat_check_interval_hours * 3600)