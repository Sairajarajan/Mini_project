"""Download training datasets for Aegis (grooming/cyberbullying).

Usage:
    python scripts/download_data.py            # download all
    python scripts/download_data.py --pan12    # only PAN12 attempt
    python scripts/download_data.py --cyberbullying

Outputs land in backend/data/:
  data/cyberbullying_tweets.csv   - labeled cyberbullying/not (HF: Zahra98/cyberbullying_tweets)
  data/pan12_grooming/            - PAN12 grooming dataset (manual, see below)

PAN12 note: the official PAN12 dataset requires a web request at
https://pan.webis.de/clef12/pan12-web/author-identification.html
This script first tries an unofficial HuggingFace mirror; if that fails it
prints instructions and expects you to place files in data/pan12_grooming/.
"""
import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

CYBERBULLYING_REPO = "Zahra98/cyberbullying_tweets"
PAN12_MIRRORS = [
    # unofficial HF mirrors (may or may not exist over time)
    "wajidlinux99/grooming-dataset-pan12",
]


def download_cyberbullying() -> Path:
    from datasets import load_dataset

    print(f"==> Loading HF dataset: {CYBERBULLYING_REPO}")
    ds = load_dataset(CYBERBULLYING_REPO, split="train")
    out = DATA / "cyberbullying_tweets.csv"
    DATA.mkdir(exist_ok=True)
    ds.to_csv(str(out))
    print(f"    saved {len(ds)} rows -> {out}")
    return out


def try_pan12_mirror() -> bool:
    from huggingface_hub import snapshot_download

    for repo in PAN12_MIRRORS:
        try:
            print(f"==> Trying PAN12 mirror: {repo}")
            target = DATA / "pan12_grooming"
            snapshot_download(repo_id=repo, local_dir=str(target))
            print(f"    saved -> {target}")
            return True
        except Exception as exc:
            print(f"    failed ({exc.__class__.__name__})")
    return False


def pan12_instructions() -> None:
    print(
        "\nPAN12 not downloaded automatically.\n"
        "1. Go to https://pan.webis.de/clef12/pan12-web/author-identification.html\n"
        "2. Fill the request form for the 'Grooming' dataset (PAN12)\n"
        "3. Unpack it into: backend/data/pan12_grooming/\n"
        "   Expected files: training-corpus.tsv / truth-file etc.\n"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cyberbullying", action="store_true", help="only cyberbullying dataset")
    ap.add_argument("--pan12", action="store_true", help="only PAN12 dataset")
    args = ap.parse_args()

    DATA.mkdir(exist_ok=True)
    if args.pan12:
        if not try_pan12_mirror():
            pan12_instructions()
    elif args.cyberbullying:
        download_cyberbullying()
    else:
        download_cyberbullying()
        if not try_pan12_mirror():
            pan12_instructions()

    print("\nDone. Next step: python scripts/train_lora.py")


if __name__ == "__main__":
    main()