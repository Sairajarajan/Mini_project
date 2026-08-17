"""Aegis WebSocket end-to-end test against a RUNNING server.

Prereq: backend running (uvicorn app.main:app --port 8000) + models downloaded.

Run:  python scripts/tests/test_e2e_ws.py
"""
import asyncio
import json
import sys
from pathlib import Path

import websockets

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

URI = "ws://localhost:8000/ws/chat"
API = "http://localhost:8000"
TEST_SENDER = "e2e_alice"
TEST_RECIPIENT = "e2e_bob"
PASS = 0
FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} {detail}")


async def main():
    import httpx

    async with httpx.AsyncClient() as client:
        for uid, name in ((TEST_SENDER, "E2E Alice"), (TEST_RECIPIENT, "E2E Bob")):
            await client.post(
                f"{API}/users/upsert",
                json={
                    "google_id": uid,
                    "email": f"{uid}@test.com",
                    "name": name,
                    "parent_email": f"parent.{uid}@test.com",
                },
            )

    print("1) safe message delivered")
    async with websockets.connect(f"{URI}?user_id={TEST_SENDER}") as ws:
        await ws.send(json.dumps({"type": "message", "recipient_id": TEST_RECIPIENT, "text": "hi"}))
        d = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
        check("delivered with low risk", d["action"] == "deliver" and d["risk_score"] < 45, d)

    print("2) grooming message blocked + alerts on BOTH parents")
    async with websockets.connect(f"{URI}?user_id={TEST_SENDER}") as ws:
        await ws.send(
            json.dumps({"type": "message", "recipient_id": TEST_RECIPIENT, "text": "wanna meet at the park after school alone?"})
        )
        d = json.loads(await asyncio.wait_for(ws.recv(), timeout=120))
        check("action is block", d["action"] == "block", d)
        check("risk >= 75", d["risk_score"] >= 75, d)

    async with httpx.AsyncClient() as client:
        alerts_sender = (await client.get(f"{API}/alerts/{TEST_SENDER}")).json()
        alerts_recipient = (await client.get(f"{API}/alerts/{TEST_RECIPIENT}")).json()
        check(
            "sender's parent alerted (sent_improper)",
            any(a["alert_type"] == "sent_improper" for a in alerts_sender),
        )
        check(
            "recipient's parent alerted (received_toxic)",
            any(a["alert_type"] == "received_toxic" for a in alerts_recipient),
        )

    async with httpx.AsyncClient() as client:
        for uid in (TEST_SENDER, TEST_RECIPIENT):
            await client.delete(f"{API}/users/{uid}")


if __name__ == "__main__":
    asyncio.run(main())
    print(f"\nE2E RESULT: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)