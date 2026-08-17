"""Aegis performance metrics — latency + accuracy report.

Measures the full classification pipeline (toxic-bert fast path and the
Qwen LLM path) on a labeled sample set, then prints a summary report.

Run:  python scripts/metrics.py
"""
import asyncio
import sys
import time
from pathlib import Path
from statistics import mean, median

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.classifier import classify
from app.services.decision import decide

# (message, expected) — expected = "safe" | "unsafe"
SAMPLES = [
    ("hi, how are you?", "safe"),
    ("how was your day at school?", "safe"),
    ("that was a funny meme haha", "safe"),
    ("want to play roblox together?", "safe"),
    ("do you have homework today?", "safe"),
    ("i like your new haircut", "safe"),
    ("you stupid idiot, everyone hates you", "unsafe"),
    ("i will kill you", "unsafe"),
    ("fuck you", "unsafe"),
    ("shut up you ugly piece of shit", "unsafe"),
    ("wanna meet at the park after school, just you and me, alone?", "unsafe"),
    ("can you send me your photos?", "unsafe"),
    ("don't tell your parents about us, it's our secret", "unsafe"),
    ("i'll buy you a phone if you keep it a secret", "unsafe"),
    ("tell me where you live and your school name", "unsafe"),
    ("i love you, you're so mature for your age", "unsafe"),
]


async def main():
    print("Running metrics on %d samples...\n" % len(SAMPLES))
    rows = []
    for text, expected in SAMPLES:
        t0 = time.time()
        res = await classify(text, [])
        dt = time.time() - t0
        action = decide(res).action
        flagged = action in ("warn", "block")
        ok = flagged == (expected == "unsafe")
        rows.append((text, expected, res, dt, action, ok))
        print("  [%s] %-1.2fs %-7s risk=%-5s intent=%-11s %s" % (
            "OK " if ok else "XX ",
            dt,
            action,
            res.risk_score,
            res.intent,
            text[:45],
        ))

    n = len(rows)
    acc = sum(1 for r in rows if r[5]) / n
    lat_all = [r[3] for r in rows]
    lat_llm = [r[3] for r in rows if "qwen" in r[2].model]
    lat_fast = [r[3] for r in rows if "cascade" in r[2].model]
    tp = sum(1 for r in rows if r[1] == "unsafe" and r[5] and r[4] in ("warn", "block"))
    fn = sum(1 for r in rows if r[1] == "unsafe" and not (r[5] and r[4] in ("warn", "block")))
    fp = sum(1 for r in rows if r[1] == "safe" and r[4] in ("warn", "block"))

    print("\n================ AEGIS METRICS ================")
    print("Accuracy:            %.1f%%  (%d/%d)" % (acc * 100, round(acc * n), n))
    print("Unsafe detected (TP): %d   Missed (FN): %d   False alerts (FP): %d" % (tp, fn, fp))
    print()
    print("Latency  mean/median (all):   %.2f / %.2f s" % (mean(lat_all), median(lat_all)))
    if lat_llm:
        print("Latency  mean/median (LLM):   %.2f / %.2f s" % (mean(lat_llm), median(lat_llm)))
    if lat_fast:
        print("Latency  mean/median (fast):  %.2f / %.2f s" % (mean(lat_fast), median(lat_fast)))
    print("===============================================")


if __name__ == "__main__":
    asyncio.run(main())