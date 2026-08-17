import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import websockets

URI = "ws://localhost:8000/ws/chat"


async def one(ws, ws2, text, expect_block=False):
    t0 = time.time()
    await ws.send(json.dumps({"type": "message", "recipient_id": "u_bob", "text": text}))
    decision = json.loads(await asyncio.wait_for(ws.recv(), timeout=120))
    dt = time.time() - t0
    print(f"[{dt:5.1f}s] {text[:50]:<50} -> {decision['action']:<7} risk={decision['risk_score']:>4} intent={decision['intent']:<12} model={decision['model']}")
    try:
        incoming = json.loads(await asyncio.wait_for(ws2.recv(), timeout=3))
        if expect_block:
            print("  !! expected BLOCK but Bob received:", incoming["text"])
    except asyncio.TimeoutError:
        if not expect_block:
            print("  !! expected DELIVER but Bob got nothing")
    return dt


async def main():
    async with websockets.connect(f"{URI}?user_id=u_bob") as bob, websockets.connect(f"{URI}?user_id=u_alice") as alice:
        await one(alice, bob, "hi")
        await one(alice, bob, "how are you doing today?")
        await one(alice, bob, "that was a funny meme haha")
        await one(alice, bob, "you stupid idiot", expect_block=True)
        await one(alice, bob, "wanna meet at the park after school alone?", expect_block=True)
        await one(alice, bob, "can you send me your photos?", expect_block=True)


asyncio.run(main())