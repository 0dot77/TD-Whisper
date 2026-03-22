"""
TD-Whisper Worker Process
Runs faster-whisper transcription as a subprocess, communicating via JSON over stdin/stdout.

Usage:
    python whisper_worker.py --model base --language ko --audio path/to/audio.wav
    python whisper_worker.py --model base --listen  (stdin mode for continuous input)
"""

import argparse
import json
import sys
import os
import time


def load_model(model_size: str, device: str = "auto", compute_type: str = "auto",
               model_dir: str | None = None):
    """Load faster-whisper model."""
    from faster_whisper import WhisperModel

    if model_dir and os.path.isdir(os.path.join(model_dir, model_size)):
        model_path = os.path.join(model_dir, model_size)
    else:
        model_path = model_size

    model = WhisperModel(model_path, device=device, compute_type=compute_type)
    return model


def transcribe_file(model, audio_path: str, language: str | None = None,
                    beam_size: int = 5, vad_filter: bool = True) -> dict:
    """Transcribe an audio file and return results as dict."""
    if not os.path.isfile(audio_path):
        return {"error": f"File not found: {audio_path}", "text": "", "segments": []}

    try:
        segments_iter, info = model.transcribe(
            audio_path,
            language=language if language else None,
            beam_size=beam_size,
            vad_filter=vad_filter,
        )

        segments = []
        full_text_parts = []
        for seg in segments_iter:
            segments.append({
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
            })
            full_text_parts.append(seg.text.strip())

        return {
            "text": " ".join(full_text_parts),
            "segments": segments,
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "duration": round(info.duration, 3),
        }

    except Exception as e:
        return {"error": str(e), "text": "", "segments": []}


def run_single(args):
    """Single file transcription mode."""
    model = load_model(args.model, device=args.device, compute_type=args.compute_type,
                       model_dir=args.model_dir)
    result = transcribe_file(model, args.audio, language=args.language,
                             beam_size=args.beam_size, vad_filter=args.vad_filter)
    print(json.dumps(result, ensure_ascii=False))


def run_listen(args):
    """Continuous listening mode — reads JSON commands from stdin, one per line.

    Input format:  {"audio": "/path/to/file.wav", "language": "ko"}
    Output format: JSON result per line on stdout.
    Send {"quit": true} to exit.
    """
    model = load_model(args.model, device=args.device, compute_type=args.compute_type,
                       model_dir=args.model_dir)

    # Signal ready
    print(json.dumps({"status": "ready", "model": args.model}), flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            cmd = json.loads(line)
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON"}), flush=True)
            continue

        if cmd.get("quit"):
            break

        audio_path = cmd.get("audio", "")
        language = cmd.get("language", args.language)
        result = transcribe_file(model, audio_path, language=language,
                                 beam_size=args.beam_size, vad_filter=args.vad_filter)
        result["timestamp"] = time.time()
        print(json.dumps(result, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description="TD-Whisper transcription worker")
    parser.add_argument("--model", default="base",
                        choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper model size (default: base)")
    parser.add_argument("--language", default=None,
                        help="Language code (e.g. ko, en, ja). None for auto-detect.")
    parser.add_argument("--device", default="auto",
                        help="Device: auto, cpu, or cuda")
    parser.add_argument("--compute-type", default="auto", dest="compute_type",
                        help="Compute type: auto, int8, float16, float32")
    parser.add_argument("--beam-size", type=int, default=5, dest="beam_size")
    parser.add_argument("--no-vad", action="store_true",
                        help="Disable VAD filter")
    parser.add_argument("--model-dir", default=None, dest="model_dir",
                        help="Directory containing downloaded models")
    parser.add_argument("--audio", default=None,
                        help="Path to audio file (single transcription mode)")
    parser.add_argument("--listen", action="store_true",
                        help="Continuous listening mode (reads commands from stdin)")

    args = parser.parse_args()
    args.vad_filter = not args.no_vad

    if args.listen:
        run_listen(args)
    elif args.audio:
        run_single(args)
    else:
        parser.error("Specify --audio FILE or --listen")


if __name__ == "__main__":
    main()
