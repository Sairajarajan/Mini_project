"""Download the Aegis ML models into backend/models/ (offline-friendly).

The model weights are too large for GitHub (100 MB per-file limit), so they
must be fetched from HuggingFace Hub before first run:

  python scripts/download_models.py

This is equivalent to:

  hf download Qwen/Qwen2.5-1.5B-Instruct --local-dir models/Qwen2.5-1.5B-Instruct
  hf download unitary/toxic-bert          --local-dir models/toxic-bert

Models:
  1. Qwen/Qwen2.5-1.5B-Instruct  (~3.2 GB) - LLM context classifier
  2. unitary/toxic-bert          (~1.3 GB) - fast toxicity check (toxic-bert)
"""
from pathlib import Path
from huggingface_hub import snapshot_download

MODELS = {
    "Qwen/Qwen2.5-1.5B-Instruct": "models/Qwen2.5-1.5B-Instruct",
    "unitary/toxic-bert": "models/toxic-bert",
}

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    for repo_id, local_dir in MODELS.items():
        target = ROOT / local_dir
        print(f"\n==> Downloading {repo_id} -> {target}")
        snapshot_download(repo_id=repo_id, local_dir=str(target), local_dir_use_symlinks=False)
        print(f"    done: {target}")


if __name__ == "__main__":
    main()