import logging

from ..config import settings
from ..models import ClassificationResult, Decision

logger = logging.getLogger("aegis.decision")

BLOCKED_INTENTS = {"exploitation", "grooming"}
HIGH_TOXICITY = 0.9


def decide(result: ClassificationResult) -> Decision:
    score = result.risk_score

    if result.intent in BLOCKED_INTENTS:
        return Decision(
            action="block",
            risk_score=score,
            reason=(
                f"Detected {result.intent} intent. {result.reason}".strip()
            ),
        )

    if result.toxicity >= HIGH_TOXICITY:
        return Decision(
            action="block",
            risk_score=max(score, 80.0),
            reason=f"Severe toxicity detected (score {result.toxicity:.2f}). {result.reason}".strip(),
        )

    if score >= settings.risk_threshold_block:
        return Decision(
            action="block",
            risk_score=score,
            reason=result.reason or f"Risk score {score:.0f} exceeds block threshold {settings.risk_threshold_block:.0f}.",
        )

    if score >= settings.risk_threshold_warn:
        return Decision(
            action="warn",
            risk_score=score,
            reason=result.reason or f"Risk score {score:.0f} exceeds warn threshold {settings.risk_threshold_warn:.0f}.",
        )

    return Decision(
        action="deliver",
        risk_score=score,
        reason=result.reason or f"Risk score {score:.0f} below warn threshold {settings.risk_threshold_warn:.0f}.",
    )