"""Aegis unit tests — decision engine + classification pipeline.

Run:  .\.venv\Scripts\python -m pytest scripts\tests -q
(LLM is mocked here for speed; the WS E2E test uses the real server + models.)
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.models import ClassificationResult
from app.services.decision import decide


# ---------- decision engine ----------

@pytest.mark.parametrize(
    "risk,intent,toxicity,expected",
    [
        (5.0, "neutral", 0.01, "deliver"),
        (10.0, "neutral", 0.05, "deliver"),
        (50.0, "neutral", 0.1, "warn"),
        (80.0, "neutral", 0.1, "block"),
        (95.0, "grooming", 0.0, "block"),      # intent gating, even at low toxicity
        (95.0, "exploitation", 0.0, "block"),  # intent gating
        (30.0, "neutral", 0.95, "block"),      # severe toxicity gates
        (0.0, "unknown", 0.0, "deliver"),
    ],
)
def test_decide_actions(risk, intent, toxicity, expected):
    result = ClassificationResult(
        risk_score=risk, intent=intent, toxicity=toxicity, model="test"
    )
    assert decide(result).action == expected


def test_decide_block_reason_contains_intent():
    result = ClassificationResult(risk_score=60.0, intent="grooming", toxicity=0.1)
    d = decide(result)
    assert d.action == "block"
    assert "grooming" in d.reason


# ---------- classifier pipeline (fast path, real toxic-bert) ----------

@pytest.mark.asyncio
async def test_classifier_cascade_fast_path():
    from app.services.classifier import classify

    res = await classify("hi, how are you doing today?", [])
    assert res.model.endswith("cascade") or "cascade" in res.model
    assert res.risk_score < 45
    assert res.intent == "neutral"


@pytest.mark.asyncio
async def test_classifier_toxic_message_high_toxicity():
    from app.services.classifier import classify
    from app.services.decision import decide

    res = await classify("you stupid idiot", [])
    assert res.toxicity > 0.5
    assert decide(res).action == "block"
    assert res.risk_score >= 75


@pytest.mark.asyncio
async def test_classifier_grooming_pattern_detected():
    from app.services.classifier import classify

    res = await classify("can you send me your photos?", [])
    assert res.risk_score >= 75 or res.intent in ("grooming", "exploitation")


# ---------- full pipeline: classification -> decision ----------

@pytest.mark.asyncio
async def test_pipeline_blocks_grooming():
    from app.services.classifier import classify

    res = await classify("wanna meet at the park after school, just you and me, alone?", [])
    assert decide(res).action in ("warn", "block")


@pytest.mark.asyncio
async def test_pipeline_delivers_normal_chat():
    from app.services.classifier import classify

    res = await classify("that was a funny meme haha", ["do you play roblox?", "yes"])
    assert decide(res).action == "deliver"