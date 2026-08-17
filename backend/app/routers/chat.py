import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from motor.motor_asyncio import AsyncIOMotorCollection

from ..database import db
from ..models import ChatMessage
from ..services.classifier import classify
from ..services.decision import decide
from ..services.email_service import alert_body, send_email

logger = logging.getLogger("aegis.chat")
router = APIRouter(tags=["chat"])

HISTORY_LIMIT = 8

connections: dict[str, WebSocket] = {}


def _coll(name: str) -> AsyncIOMotorCollection:
    return db[name]


async def _history(chat_key: str) -> list[str]:
    cursor = _coll("chat_log").find({"chat_key": chat_key}).sort("sent_at", -1).limit(HISTORY_LIMIT)
    docs = [d async for d in cursor]
    return [d["text"] for d in reversed(docs)]


async def _user_name(user_id: str) -> str:
    doc = await _coll("users").find_one({"_id": user_id}, {"name": 1})
    return doc["name"] if doc else user_id


async def _parent_email(user_id: str):
    doc = await _coll("users").find_one({"_id": user_id}, {"parent_email": 1})
    return doc["parent_email"] if doc else None


async def _guardian_alert(alert_type: str, user_id: str, **ctx) -> None:
    parent = await _parent_email(user_id)
    if not parent:
        logger.warning("No parent email for %s; skipping alert", user_id)
        return
    subject = {
        "received_toxic": "Aegis: Inappropriate message blocked",
        "sent_improper": "Aegis: Your child sent an inappropriate message",
        "app_inactive": "Aegis: App may have been uninstalled",
    }[alert_type]
    await send_email(parent, subject, alert_body(alert_type, **ctx))
    await _coll("alert_records").insert_one(
        {
            "alert_type": alert_type,
            "user_id": user_id,
            "parent_email": parent,
            "message_text": ctx.get("message", ""),
            "sender_name": ctx.get("sender_name", ""),
            "reason": ctx.get("reason", ""),
            "created_at": datetime.now(timezone.utc),
        }
    )


async def _process_message(user_id: str, recipient_id: str, text: str) -> dict:
    chat_key = "|".join(sorted([user_id, recipient_id]))
    history = await _history(chat_key)

    result = await classify(text, history)
    decision = decide(result)

    msg = ChatMessage(
        sender_id=user_id,
        recipient_id=recipient_id,
        text=text,
    )

    if decision.action == "deliver":
        await _coll("chat_log").insert_one(
            {**msg.model_dump(), "chat_key": chat_key, "risk_score": result.risk_score}
        )
        if recipient_id in connections:
            await connections[recipient_id].send_text(
                json.dumps(
                    {
                        "type": "message",
                        "sender_id": user_id,
                        "text": text,
                        "risk_score": result.risk_score,
                    }
                )
            )
    else:
        sender_name = await _user_name(user_id)
        if decision.action == "warn":
            await _coll("chat_log").insert_one(
                {**msg.model_dump(), "chat_key": chat_key, "risk_score": result.risk_score}
            )
            await _guardian_alert(
                "sent_improper",
                user_id,
                child_name=sender_name,
                message=text,
                reason=decision.reason,
            )
        else:
            await _guardian_alert(
                "sent_improper",
                user_id,
                child_name=sender_name,
                message=text,
                reason=decision.reason,
            )

    return {
        "type": "decision",
        "action": decision.action,
        "risk_score": result.risk_score,
        "intent": result.intent,
        "toxicity": result.toxicity,
        "reason": decision.reason,
        "model": result.model,
    }


@router.websocket("/ws/chat")
async def ws_chat(ws: WebSocket, user_id: str):
    await ws.accept()
    connections[user_id] = ws
    logger.info("User %s connected (online=%d)", user_id, len(connections))
    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "detail": "invalid JSON"})
                continue
            if data.get("type") != "message":
                await ws.send_json({"type": "error", "detail": "unsupported type"})
                continue
            text = (data.get("text") or "").strip()
            recipient = data.get("recipient_id")
            if not text or not recipient:
                await ws.send_json({"type": "error", "detail": "text and recipient_id required"})
                continue
            reply = await _process_message(user_id, recipient, text)
            await ws.send_json(reply)
    except WebSocketDisconnect:
        pass
    finally:
        connections.pop(user_id, None)
        logger.info("User %s disconnected", user_id)


@router.get("/chat/history/{user_id}/{other_id}")
async def chat_history(user_id: str, other_id: str):
    chat_key = "|".join(sorted([user_id, other_id]))
    cursor = _coll("chat_log").find({"chat_key": chat_key}).sort("sent_at", 1).limit(100)
    return [d async for d in cursor]