import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import websockets

URI = "ws://localhost:8000/ws/chat"


async def main():
    async with websockets.connect(f"{URI}?user_id=u_bob") as bob, websockets.connect(f"{URI}?user_id=u_alice") as alice:
        for text in ["Hi Bob, how are you?", "Wanna meet at the park after school, just you and me, alone?"]:
            await alice.send(json.dumps({"type": "message", "recipient_id": "u_bob", "text": text}))
            print(f"SENT: {text}")
            decision = json.loads(await asyncio.wait_for(alice.recv(), timeout=180))
            print(f"ALICE DECISION: {decision['action']} risk={decision['risk_score']} intent={decision['intent']} ({decision['model']})")
            try:
                incoming = json.loads(await asyncio.wait_for(bob.recv(), timeout=5))
                print(f"BOB RECEIVED: {incoming['text']} risk={incoming.get('risk_score')}")
            except asyncio.TimeoutError:
                print("BOB RECEIVED: nothing (blocked by Aegis)")


asyncio.run(main())