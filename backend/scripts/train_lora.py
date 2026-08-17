"""LoRA fine-tune Qwen2.5-1.5B-Instruct on grooming/cyberbullying data.

Usage:
    python scripts/download_data.py              # first: get data
    python scripts/train_lora.py --samples 2000  # train (CPU-friendly default)

Train loop (CPU, 1.5B model): ~2000 samples x 1 epoch ≈ 30-60 min.
The trained adapter is saved to models/lora-aegis and is picked up
automatically by the classifier when USE_LORA=true (see app/config.py).

Intent labels used:
    neutral, grooming, exploitation, explicit, bullying, self_harm, spam
"""
import argparse
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402

INSTRUCT = (
    "You are a child-safety moderator. Classify the chat message intent into one of: "
    "neutral, grooming, exploitation, explicit, bullying, self_harm, spam. "
    "Reply with only the single label word."
)


def build_samples(path: Path) -> list[tuple[str, str]]:
    import pandas as pd

    df = pd.read_csv(path)
    label_col = "cyberbullying_type" if "cyberbullying_type" in df.columns else df.columns[-1]
    text_col = "tweet_text" if "tweet_text" in df.columns else df.columns[0]
    labels = {
        "not_cyberbullying": "neutral",
        "gender": "bullying",
        "religion": "bullying",
        "other_cyberbullying": "bullying",
        "age": "bullying",
        "ethnicity": "bullying",
    }
    samples = []
    for _, row in df.iterrows():
        raw = str(row[label_col]).strip().lower()
        label = labels.get(raw, "neutral")
        samples.append((str(row[text_col])[:512], label))
    return samples


def build_pan12_samples() -> list[tuple[str, str]]:
    samples: list[tuple[str, str]] = []
    pan_dir = ROOT / "data" / "pan12_grooming"
    if not pan_dir.exists():
        return samples
    for csv in pan_dir.rglob("*.csv"):
        import pandas as pd

        df = pd.read_csv(csv)
        if {"text", "label"}.issubset(df.columns):
            for _, r in df.iterrows():
                samples.append((str(r["text"])[:512], str(r["label"]).strip().lower()))
    return samples


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=2000, help="max training samples")
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--batch-size", type=int, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--output", type=str, default=str(ROOT / "models" / "lora-aegis"))
    args = ap.parse_args()

    csv = ROOT / "data" / "cyberbullying_tweets.csv"
    if not csv.exists():
        print("Dataset missing. Run: python scripts/download_data.py")
        sys.exit(1)

    samples = build_samples(csv) + build_pan12_samples()
    samples = samples[: args.samples]
    print(f"Training samples: {len(samples)}")
    if not samples:
        sys.exit("No samples found.")

    from peft import LoraConfig, get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForSeq2Seq,
        Trainer,
        TrainingArguments,
    )

    tokenizer = AutoTokenizer.from_pretrained(settings.qwen_model_path, local_files_only=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def tokenize(text: str, label: str):
        prompt = tokenizer.apply_chat_template(
            [
                {"role": "system", "content": INSTRUCT},
                {"role": "user", "content": text},
            ],
            tokenize=False,
            add_generation_prompt=True,
        ) + f"{label}{tokenizer.eos_token}"
        return tokenizer(prompt, truncation=True, max_length=512, padding=False)

    tokenized = [tokenize(t, l) for t, l in samples]

    model = AutoModelForCausalLM.from_pretrained(
        settings.qwen_model_path, local_files_only=True, torch_dtype=torch.float32
    )
    lora = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    training_args = TrainingArguments(
        output_dir=str(ROOT / "models" / "lora-checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        learning_rate=args.lr,
        logging_steps=20,
        save_strategy="no",
        report_to=[],
        use_cpu=True,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=DataCollatorForSeq2Seq(tokenizer, padding=True),
    )
    trainer.train()
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    print(f"\nAdapter saved to {args.output}")
    print("Enable it in the classifier: set USE_LORA=true in .env")


if __name__ == "__main__":
    main()