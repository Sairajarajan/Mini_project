import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

from ..config import settings
from ..models import ClassificationResult

logger = logging.getLogger("aegis.classifier")

_qwen_tokenizer = None
_qwen_model = None
_qwen_loaded = False
_qwen_load_lock = asyncio.Lock()
_detoxify = None
_detoxify_loaded = False
_detoxify_load_lock = asyncio.Lock()

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
_INTENT_RE = re.compile(r'"intent"\s*:\s*"(\w+)"')
_SCORE_RE = re.compile(r'"risk_score"\s*:\s*([\d.]+)')
_REASON_RE = re.compile(r'"reason"\s*:\s*"((?:[^"\\]|\\.)*)"')

_TOXIC_CLASSES = ["toxicity", "severe_toxicity", "obscene", "threat", "insult", "identity_attack"]

_CASCADE_KEYWORDS = [
    "meet", "alone", "secret", "don't tell", "dont tell", "tell your parents",
    "photo", "pictures", "naked", "undress", "clothes off", "your age",
    "where do you live", "school", "parents", "money", "gift", "buy you",
    "cute", "love you", "private", "you and me", "after school", "hidden",
    "address", "snapchat", "instagram", "send me", "camera", "webcam",
    "kiss", "hug", "boyfriend", "girlfriend", "alone with",
]


def _keyword_hit(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in _CASCADE_KEYWORDS)

_SYSTEM_PROMPT = (
    "You are a child-safety moderator for a chat app used by children. "
    "Analyze the message and the recent conversation history. "
    "Classify the intent as one of: neutral, grooming, exploitation, explicit, bullying, self_harm, spam. "
    "Return ONLY a JSON object with no extra text:\n"
    '{"intent": "<class>", "risk_score": <0-100>, "reason": "<max 8 words>"}\n'
    "Notes:\n"
    "- grooming = trying to befriend/trust-build a child for later abuse (e.g. asking age/photo/secret meetings, complimenting excessively, isolating the child)\n"
    "- exploitation = requesting sexual content, money, or blackmail\n"
    "- explicit = sexual/obscene language\n"
    "- risk_score 0-100 reflects how dangerous the message is.\n"
    "- If unsure, prefer neutral with a low score."
)


class _ToxicBert:
    def __init__(self):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        logger.info("Loading toxic-bert from %s ...", settings.toxic_bert_path)
        self.tokenizer = AutoTokenizer.from_pretrained(
            settings.toxic_bert_path, local_files_only=True
        )
        self.model = AutoModelForSequenceClassification.from_pretrained(
            settings.toxic_bert_path, local_files_only=True
        )
        self.model.eval()
        logger.info("toxic-bert loaded.")

    def predict(self, text: str) -> dict[str, float]:
        import torch

        inputs = self.tokenizer(
            text, return_tensors="pt", truncation=True, max_length=512, padding=True
        )
        with torch.no_grad():
            logits = self.model(**inputs).logits
        probs = torch.sigmoid(logits)[0]
        return {
            cls: float(prob)
            for cls, prob in zip(_TOXIC_CLASSES, probs)
        }


def _load_detoxify_sync() -> Any:
    return _ToxicBert()


async def ensure_detoxify() -> Any:
    global _detoxify, _detoxify_loaded
    if _detoxify_loaded and _detoxify is not None:
        return _detoxify
    async with _detoxify_load_lock:
        if _detoxify_loaded and _detoxify is not None:
            return _detoxify
        try:
            _detoxify = await asyncio.to_thread(_load_detoxify_sync)
            _detoxify_loaded = True
        except Exception as exc:
            logger.error("toxic-bert load failed: %s", exc)
            _detoxify_loaded = True
    return _detoxify


def _load_qwen_sync() -> Any:
    from transformers import AutoModelForCausalLM, AutoTokenizer

    logger.info("Loading Qwen2.5-1.5B-Instruct from %s ...", settings.qwen_model_path)
    tokenizer = AutoTokenizer.from_pretrained(settings.qwen_model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        settings.qwen_model_path,
        local_files_only=True,
        device_map="cpu",
        torch_dtype="auto",
    )
    if settings.use_lora and (settings.lora_adapter_path and Path(settings.lora_adapter_path).exists()):
        from peft import PeftModel

        logger.info("Attaching LoRA adapter: %s", settings.lora_adapter_path)
        model = PeftModel.from_pretrained(model, settings.lora_adapter_path, local_files_only=True)
        logger.info("LoRA attached.")
    model.eval()
    logger.info("Qwen2.5 loaded.")
    return tokenizer, model


async def ensure_qwen() -> tuple[Any, Any]:
    global _qwen_tokenizer, _qwen_model, _qwen_loaded
    if _qwen_loaded and _qwen_model is not None:
        return _qwen_tokenizer, _qwen_model
    async with _qwen_load_lock:
        if _qwen_loaded and _qwen_model is not None:
            return _qwen_tokenizer, _qwen_model
        try:
            _qwen_tokenizer, _qwen_model = await asyncio.to_thread(_load_qwen_sync)
        except Exception as exc:
            logger.error("Qwen load failed: %s", exc)
        _qwen_loaded = True
    return _qwen_tokenizer, _qwen_model


async def _qwen_score(message: str, history: list[str]) -> dict:
    tokenizer, model = await ensure_qwen()
    if model is None or tokenizer is None:
        return {"intent": "unknown", "risk_score": 0.0, "reason": "LLM unavailable"}

    history_txt = "\n".join(f"- {h}" for h in history[-6:]) or "(no prior messages)"
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Recent conversation:\n{history_txt}\n\n"
            f"Message to classify: \"{message}\"",
        },
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=settings.qwen_max_input_tokens)

    import torch

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=settings.qwen_max_new_tokens,
            do_sample=False,
            temperature=None,
            top_p=None,
        )
    answer = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    logger.info("Qwen answer: %s", answer)

    match = _JSON_RE.search(answer)
    if match:
        try:
            data = json.loads(match.group(0))
            score = float(data.get("risk_score", 0.0))
            return {
                "intent": str(data.get("intent", "neutral")),
                "risk_score": max(0.0, min(100.0, score)),
                "reason": str(data.get("reason", "")),
            }
        except (ValueError, TypeError):
            pass

    mi = _INTENT_RE.search(answer)
    ms = _SCORE_RE.search(answer)
    mr = _REASON_RE.search(answer)
    if mi:
        score = float(ms.group(1)) if ms else 0.0
        return {
            "intent": mi.group(1),
            "risk_score": max(0.0, min(100.0, score)),
            "reason": mr.group(1) if mr else "truncated LLM output",
        }

    logger.error("Qwen JSON parse error; raw: %s", answer)
    return {"intent": "unknown", "risk_score": 0.0, "reason": "unparseable LLM output"}


async def preload() -> None:
    """Warm up models at server startup (best-effort, non-blocking)."""
    try:
        await ensure_detoxify()
        if settings.use_llm:
            await ensure_qwen()
    except Exception as exc:
        logger.error("preload failed: %s", exc)


async def classify(message: str, history: list[str] | None = None) -> ClassificationResult:
    history = history or []
    toxicity = 0.0
    toxicity_label = "neutral"
    intent = "neutral"
    risk = 0.0
    reason = ""
    model_used = ""

    det = await ensure_detoxify()
    if det is not None:
        try:
            res = await asyncio.to_thread(det.predict, message)
            toxicity = float(res.get("toxicity", 0.0))
            toxicity_label = "toxic" if toxicity >= 0.5 else "neutral"
            model_used = "toxic-bert"
        except Exception as exc:
            logger.error("toxic-bert predict failed: %s", exc)

    qwen_out: dict = {}
    needs_llm = settings.use_llm and (
        not settings.cascade
        or toxicity >= settings.llm_trigger_toxicity
        or _keyword_hit(message)
    )
    if needs_llm:
        qwen_out = await _qwen_score(message, history)
        model_used = f"{model_used}+qwen2.5" if model_used else "qwen2.5"
    else:
        model_used = f"{model_used}+cascade" if model_used else "cascade"

    if qwen_out:
        intent = qwen_out["intent"]
        reason = qwen_out["reason"]
    elif not needs_llm:
        reason = "Fast check passed (low toxicity, no risk patterns)."
    else:
        reason = "LLM triggered but output unparseable - escalated for manual review."

    if qwen_out and qwen_out["risk_score"] > 0:
        risk = qwen_out["risk_score"]
    elif needs_llm:
        risk = max(toxicity * 100.0, settings.risk_threshold_warn)
    else:
        risk = min(100.0, toxicity * 100.0)

    high_tox = toxicity >= 0.5
    low_llm = qwen_out and qwen_out["risk_score"] < 10
    if high_tox and low_llm:
        risk = max(risk, toxicity * 70.0)

    return ClassificationResult(
        toxicity=round(toxicity, 4),
        toxicity_label=toxicity_label,
        intent=intent,
        risk_score=round(risk, 1),
        reason=reason,
        model=model_used,
    )