"""
TD-Whisper Model Downloader
Downloads faster-whisper (CTranslate2) models from HuggingFace.

Usage:
    python download_model.py --model base
    python download_model.py --model base --output ../models
    python download_model.py --list
"""

import argparse
import os
import sys

MODELS = {
    "tiny":     "Systran/faster-whisper-tiny",
    "base":     "Systran/faster-whisper-base",
    "small":    "Systran/faster-whisper-small",
    "medium":   "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
}

MODEL_INFO = {
    "tiny":     {"size_mb": 75,   "vram_mb": 400,  "note": "Fastest, lowest accuracy"},
    "base":     {"size_mb": 145,  "vram_mb": 500,  "note": "Good balance for real-time"},
    "small":    {"size_mb": 488,  "vram_mb": 1000, "note": "Better accuracy"},
    "medium":   {"size_mb": 1530, "vram_mb": 2600, "note": "High accuracy"},
    "large-v3": {"size_mb": 3100, "vram_mb": 5000, "note": "Best accuracy, slowest"},
}


def list_models():
    print("\nAvailable faster-whisper models:\n")
    print(f"{'Model':<12} {'Size':<10} {'VRAM':<10} {'Note'}")
    print("-" * 60)
    for name, info in MODEL_INFO.items():
        print(f"{name:<12} {info['size_mb']:>5} MB   {info['vram_mb']:>5} MB   {info['note']}")
    print()


def download_model(model_name: str, output_dir: str):
    if model_name not in MODELS:
        print(f"Error: Unknown model '{model_name}'")
        print(f"Available: {', '.join(MODELS.keys())}")
        sys.exit(1)

    repo_id = MODELS[model_name]
    target_dir = os.path.join(output_dir, model_name)

    print(f"Downloading {model_name} from {repo_id}...")
    print(f"Target: {target_dir}")

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("\nError: huggingface_hub not installed.")
        print("Install it with: pip install huggingface_hub")
        sys.exit(1)

    os.makedirs(target_dir, exist_ok=True)

    snapshot_download(
        repo_id=repo_id,
        local_dir=target_dir,
        local_dir_use_symlinks=False,
    )

    print(f"\nDone! Model saved to: {target_dir}")
    print(f"Set model_dir in TD-Whisper to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Download faster-whisper models")
    parser.add_argument("--model", default="base",
                        choices=list(MODELS.keys()),
                        help="Model to download (default: base)")
    parser.add_argument("--output", default=None,
                        help="Output directory (default: ../models relative to this script)")
    parser.add_argument("--list", action="store_true",
                        help="List available models")

    args = parser.parse_args()

    if args.list:
        list_models()
        return

    if args.output is None:
        args.output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")

    download_model(args.model, args.output)


if __name__ == "__main__":
    main()
