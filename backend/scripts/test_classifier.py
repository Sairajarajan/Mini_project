import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.classifier import classify


async def main():
    samples = [
        ("Hi, how are you doing today?", []),
        ("That was a funny meme haha", ["do you play roblox?", "yes i play roblox"]),
        ("You look cute in your photos, can you send me more?", []),
        ("Can you keep a secret? Don't tell your parents, I'll buy you a phone", []),
        ("Tell me where you live and your school name", []),
        ("You stupid idiot, everyone hates you", []),
        ("I'll send you money if you take your clothes off on camera", []),
        ("Wanna meet at the park after school, just you and me, alone?", ["i have a new bike", "nice, meet me behind the old school"]),
    ]
    for text, history in samples:
        t0 = time.time()
        res = await classify(text, history)
        print(f"\nMSG: {text[:60]}")
        print(f"  -> risk={res.risk_score} intent={res.intent} tox={res.toxicity:.2f} "
              f"model={res.model} ({time.time()-t0:.1f}s)")
        print(f"     reason: {res.reason}")


asyncio.run(main())