"""
TD-Whisper Extension
Local speech-to-text for TouchDesigner using faster-whisper.

Attach this extension to a Base COMP.
Required custom parameters on the Base COMP:
    - Modelsize (Menu: tiny, base, small, medium, large-v3)
    - Language  (Str: ko, en, ja, etc. Leave empty for auto-detect)
    - Pythonexe (File: path to python executable with faster-whisper installed)
    - Modeldir  (Folder: path to models directory, optional)
    - Text      (Str: read-only, latest transcription result)
    - Status    (Str: read-only, current status)
    - Listening (Toggle: read-only, whether continuous listening is active)
"""

import subprocess
import threading
import json
import os
import tempfile
import struct
import wave
import time


class TDWhisperExt:
    """TD-Whisper Extension class."""

    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        self._worker_process = None
        self._worker_lock = threading.Lock()
        self._result = {"text": "", "segments": [], "language": ""}
        self._listening = False
        self._listen_thread = None
        self._record_thread = None
        self._temp_dir = tempfile.mkdtemp(prefix="tdwhisper_")
        self._status = "idle"
        self._recording_samples = []
        self._recording = False

        self._update_status("idle")

    # -- Properties --

    @property
    def _worker_script(self) -> str:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, "scripts", "whisper_worker.py")

    @property
    def _python_exe(self) -> str:
        par = self.ownerComp.par
        if hasattr(par, 'Pythonexe') and par.Pythonexe.eval():
            return par.Pythonexe.eval()
        return "python"

    @property
    def _model_size(self) -> str:
        par = self.ownerComp.par
        if hasattr(par, 'Modelsize') and par.Modelsize.eval():
            return par.Modelsize.eval()
        return "base"

    @property
    def _language(self) -> str | None:
        par = self.ownerComp.par
        if hasattr(par, 'Language') and par.Language.eval():
            return par.Language.eval()
        return None

    @property
    def _model_dir(self) -> str | None:
        par = self.ownerComp.par
        if hasattr(par, 'Modeldir') and par.Modeldir.eval():
            return par.Modeldir.eval()
        return None

    # -- Status --

    def _update_status(self, status: str):
        self._status = status
        par = self.ownerComp.par
        if hasattr(par, 'Status'):
            par.Status = status

    def _update_text(self, text: str):
        par = self.ownerComp.par
        if hasattr(par, 'Text'):
            par.Text = text

    # -- Public API --

    def GetText(self) -> str:
        """Get the latest transcription text."""
        return self._result.get("text", "")

    def GetResult(self) -> dict:
        """Get the full result dict (text, segments, language, duration)."""
        return dict(self._result)

    def Transcribe(self, audio_path: str, callback: str = None):
        """Transcribe an audio file asynchronously.

        Args:
            audio_path: Path to WAV/MP3/etc audio file.
            callback: Optional — name of a DAT containing an onTranscriptionComplete function.
        """
        def _run():
            self._update_status("transcribing")
            result = self._run_worker_single(audio_path)
            self._result = result
            self._update_text(result.get("text", ""))
            self._update_status("done")

            if callback:
                try:
                    cb_dat = self.ownerComp.op(callback)
                    if cb_dat and hasattr(cb_dat.module, 'onTranscriptionComplete'):
                        run("args[0](args[1], args[2])",
                            cb_dat.module.onTranscriptionComplete, self.ownerComp, result,
                            delayFrames=1)
                except Exception as e:
                    debug(f"TD-Whisper callback error: {e}")

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def TranscribeFromCHOP(self, chop_op, duration_seconds: float = 5.0,
                           sample_rate: int = 16000, callback: str = None):
        """Record audio from an Audio Device In CHOP and transcribe.

        Args:
            chop_op: The CHOP operator (or path string) to read audio from.
            duration_seconds: Seconds of audio to capture from the CHOP.
            sample_rate: Sample rate for the WAV file (Whisper expects 16000).
            callback: Optional callback DAT name.
        """
        if isinstance(chop_op, str):
            chop_op = self.ownerComp.op(chop_op)

        if chop_op is None:
            self._update_status("error: CHOP not found")
            return

        wav_path = os.path.join(self._temp_dir, f"chop_{int(time.time())}.wav")
        self._save_chop_to_wav(chop_op, wav_path, duration_seconds, sample_rate)
        self.Transcribe(wav_path, callback=callback)

    def StartListening(self, chop_op, interval_seconds: float = 3.0,
                       sample_rate: int = 16000, callback: str = None):
        """Start continuous listening mode.

        Records audio in intervals and transcribes each chunk.

        Args:
            chop_op: CHOP operator for audio input.
            interval_seconds: Duration of each recording chunk.
            sample_rate: Sample rate for WAV.
            callback: Optional callback DAT name.
        """
        if self._listening:
            return

        if isinstance(chop_op, str):
            chop_op = self.ownerComp.op(chop_op)

        self._listening = True
        self._update_status("listening")
        par = self.ownerComp.par
        if hasattr(par, 'Listening'):
            par.Listening = True

        # Start persistent worker process
        self._start_persistent_worker()

        def _listen_loop():
            while self._listening:
                wav_path = os.path.join(self._temp_dir, f"listen_{int(time.time())}.wav")
                self._save_chop_to_wav(chop_op, wav_path, interval_seconds, sample_rate)

                result = self._send_to_persistent_worker(wav_path)
                if result:
                    self._result = result
                    self._update_text(result.get("text", ""))

                    if callback:
                        try:
                            cb_dat = self.ownerComp.op(callback)
                            if cb_dat and hasattr(cb_dat.module, 'onTranscriptionComplete'):
                                run("args[0](args[1], args[2])",
                                    cb_dat.module.onTranscriptionComplete,
                                    self.ownerComp, result, delayFrames=1)
                        except Exception:
                            pass

                # Clean up temp file
                try:
                    os.remove(wav_path)
                except OSError:
                    pass

        self._listen_thread = threading.Thread(target=_listen_loop, daemon=True)
        self._listen_thread.start()

    def StopListening(self):
        """Stop continuous listening mode."""
        self._listening = False
        self._stop_persistent_worker()
        self._update_status("idle")
        par = self.ownerComp.par
        if hasattr(par, 'Listening'):
            par.Listening = False

    # -- Worker Management --

    def _run_worker_single(self, audio_path: str) -> dict:
        """Run worker as a one-shot subprocess."""
        cmd = [
            self._python_exe, self._worker_script,
            "--model", self._model_size,
            "--audio", audio_path,
        ]
        if self._language:
            cmd += ["--language", self._language]
        if self._model_dir:
            cmd += ["--model-dir", self._model_dir]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode != 0:
                return {"error": proc.stderr.strip(), "text": "", "segments": []}
            return json.loads(proc.stdout.strip())
        except subprocess.TimeoutExpired:
            return {"error": "Transcription timed out", "text": "", "segments": []}
        except Exception as e:
            return {"error": str(e), "text": "", "segments": []}

    def _start_persistent_worker(self):
        """Start a persistent worker process for continuous listening."""
        with self._worker_lock:
            if self._worker_process and self._worker_process.poll() is None:
                return

            cmd = [
                self._python_exe, self._worker_script,
                "--model", self._model_size,
                "--listen",
            ]
            if self._language:
                cmd += ["--language", self._language]
            if self._model_dir:
                cmd += ["--model-dir", self._model_dir]

            self._worker_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            # Wait for ready signal
            ready_line = self._worker_process.stdout.readline()
            try:
                ready = json.loads(ready_line)
                if ready.get("status") == "ready":
                    self._update_status("listening (model loaded)")
            except (json.JSONDecodeError, ValueError):
                pass

    def _send_to_persistent_worker(self, audio_path: str) -> dict | None:
        """Send a transcription request to the persistent worker."""
        with self._worker_lock:
            if not self._worker_process or self._worker_process.poll() is not None:
                return None

            cmd = {"audio": audio_path}
            if self._language:
                cmd["language"] = self._language

            try:
                self._worker_process.stdin.write(json.dumps(cmd) + "\n")
                self._worker_process.stdin.flush()
                result_line = self._worker_process.stdout.readline()
                return json.loads(result_line)
            except Exception:
                return None

    def _stop_persistent_worker(self):
        """Stop the persistent worker process."""
        with self._worker_lock:
            if self._worker_process and self._worker_process.poll() is None:
                try:
                    self._worker_process.stdin.write('{"quit": true}\n')
                    self._worker_process.stdin.flush()
                    self._worker_process.wait(timeout=5)
                except Exception:
                    self._worker_process.kill()
                self._worker_process = None

    # -- Audio Utilities --

    def _save_chop_to_wav(self, chop_op, wav_path: str, duration_seconds: float,
                          sample_rate: int):
        """Save CHOP audio data to a WAV file."""
        num_samples = int(chop_op.numSamples)
        num_channels = int(chop_op.numChans)

        # Read samples from CHOP
        samples = []
        use_samples = min(num_samples, int(duration_seconds * sample_rate))

        for i in range(use_samples):
            for c in range(num_channels):
                val = chop_op[c][i]
                # Clamp and convert to 16-bit PCM
                val = max(-1.0, min(1.0, float(val)))
                samples.append(int(val * 32767))

        # Write WAV
        with wave.open(wav_path, 'w') as wf:
            wf.setnchannels(min(num_channels, 1))  # Mono for Whisper
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)

            if num_channels > 1:
                # Downmix to mono
                mono_samples = []
                for i in range(0, len(samples), num_channels):
                    chunk = samples[i:i + num_channels]
                    mono_samples.append(int(sum(chunk) / len(chunk)))
                data = struct.pack(f"<{len(mono_samples)}h", *mono_samples)
            else:
                data = struct.pack(f"<{len(samples)}h", *samples)

            wf.writeframes(data)

    def Destroy(self):
        """Clean up on extension destroy."""
        self.StopListening()
        # Clean up temp directory
        try:
            import shutil
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        except Exception:
            pass
