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

_TOXIC_CLASSES = ["toxicity", "severe_toxicity", "obscene", "threat", "insult", "identity_attack"]

_SYSTEM_PROMPT = (
    "You are a child-safety moderator for a chat app used by children. "
    "Analyze the message and the recent conversation history. "
    "Classify the intent as one of: neutral, grooming, exploitation, explicit, bullying, self_harm, spam. "
    "Return ONLY a JSON object with no extra text:\n"
    '{"intent": "<class>", "risk_score": <0-100>, "reason": "<short explanation>"}\n'
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
    inputs = tokenizer(text, return_tensors="pt")

    import torch

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=64,
            do_sample=False,
            temperature=None,
            top_p=None,
        )
    answer = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    logger.info("Qwen answer: %s", answer)

    match = _JSON_RE.search(answer)
    if not match:
        return {"intent": "unknown", "risk_score": 0.0, "reason": "unparseable LLM output"}
    try:
        data = json.loads(match.group(0))
        score = float(data.get("risk_score", 0.0))
        return {
            "intent": str(data.get("intent", "neutral")),
            "risk_score": max(0.0, min(100.0, score)),
            "reason": str(data.get("reason", "")),
        }
    except (ValueError, TypeError) as exc:
        logger.error("Qwen JSON parse error: %s", exc)
        return {"intent": "unknown", "risk_score": 0.0, "reason": "LLM output parse error"}


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
    if settings.use_llm:
        qwen_out = await _qwen_score(message, history)
        model_used = f"{model_used}+qwen2.5" if model_used else "qwen2.5"

    if qwen_out:
        intent = qwen_out["intent"]
        reason = qwen_out["reason"]

    if qwen_out and qwen_out["risk_score"] > 0:
        risk = qwen_out["risk_score"]
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