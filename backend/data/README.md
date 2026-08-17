# Dataset directory

This folder is **gitignored** because the full dataset is too large for GitHub
(329 MB CSV > GitHub's 100 MB per-file limit).

## Get the full dataset (239,465 rows)

```powershell
cd backend
.\.venv\Scripts\python scripts\download_data.py
```

This downloads **`karthikarunr/Cyberbullying-Toxicity-Tweets`** from HuggingFace Hub
into `backend/data/cyberbullying_tweets.csv` (columns: `Text`, `oh_label`
[1 = cyberbullying, 0 = neutral], plus cleaned/tokenized variants).
Also attempts the PAN12 grooming dataset (falls back to manual download instructions).

## Sample

`sample.csv` (first 100 rows) is committed for quick inspection/demos.

## Usage in training

`scripts/train_lora.py` reads the CSV and maps `oh_label` 1 → `bullying`,
0 → `neutral` for LoRA fine-tuning of Qwen2.5-1.5B-Instruct.