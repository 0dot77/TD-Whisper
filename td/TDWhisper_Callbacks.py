"""
TD-Whisper Callbacks
Place this in an Execute DAT or use as a module for callback handling.

Setup:
    1. Create a Text DAT, paste this code.
    2. Reference it as the callback parameter in Transcribe() or StartListening().
    3. Customize onTranscriptionComplete() for your project.
"""


def onTranscriptionComplete(comp, result):
    """Called when a transcription finishes.

    Args:
        comp: The TDWhisper Base COMP that owns the extension.
        result: Dict with keys:
            - text (str): Full transcription text.
            - segments (list): List of {start, end, text} dicts.
            - language (str): Detected language code.
            - language_probability (float): Confidence of language detection.
            - duration (float): Audio duration in seconds.
            - error (str, optional): Error message if something went wrong.
    """
    text = result.get("text", "")
    error = result.get("error", "")

    if error:
        debug(f"TD-Whisper error: {error}")
        return

    if not text:
        return

    # Example: Output to a Text DAT named 'text_output'
    text_dat = comp.op("text_output")
    if text_dat:
        text_dat.text = text

    # Example: Log segments with timestamps
    for seg in result.get("segments", []):
        debug(f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")

    # Example: Send to another operator via custom parameter
    # op('llm_input').par.Prompt = text

    debug(f"TD-Whisper: '{text}' (lang={result.get('language', '?')})")


def onTimerComplete(timerOp, segment, interrupt):
    """Timer CHOP callback for continuous listening intervals.

    Setup:
        1. Create a Timer CHOP with your desired interval.
        2. Set this DAT as the Timer's callback DAT.
        3. In onTimerComplete, trigger a new recording cycle.

    This is an alternative to StartListening() for more control.
    """
    whisper_comp = timerOp.op("../TDWhisper")
    if whisper_comp is None:
        return

    ext = whisper_comp.ext.TDWhisperExt
    audio_chop = timerOp.op("../audiodevin1")

    if ext and audio_chop:
        ext.TranscribeFromCHOP(
            audio_chop,
            duration_seconds=float(timerOp.par.Length),
            callback="TDWhisper_Callbacks",
        )
