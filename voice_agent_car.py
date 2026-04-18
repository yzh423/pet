# coding: utf-8
"""
Voice stack (Jetson / PC)::

  Microphone → **STT** (``cloud`` | ``vosk``) → LLM → **TTS** (``cloud`` | ``espeak`` local CLI)
                         ↓
              Same utterance: parse drive phrases
                         ↓
              comm.py → Arduino (F / B / L / R / S)

Environment (defaults: **no cloud** — local STT/TTS + local Ollama LLM)::

  OPENAI_BASE_URL     Default ``http://127.0.0.1:11434/v1`` (Ollama). Set to ``https://api.openai.com/v1`` (etc.) only if you use **cloud** STT/TTS or remote LLM.
  OPENAI_API_KEY / DASHSCOPE_API_KEY / QWEN_API_KEY   Required for **remote** https LLM or any **cloud** STT/TTS; optional for localhost Ollama (Bearer defaults to ``ollama``).
  OPENAI_STT_MODEL    Default whisper-1 (transcriptions)
  OPENAI_STT_LANGUAGE Optional ISO-639-1 code, e.g. en
  OPENAI_TTS_MODEL    Default tts-1
  OPENAI_TTS_VOICE    Default nova (OpenAI voices: alloy, echo, fable, onyx, nova, shimmer)
  VOICE_STT_MODE      ``cloud`` | ``vosk`` (default: **vosk**)
  VOICE_TTS_MODE      ``cloud`` | ``espeak`` (default: **espeak**; ``espeak-ng``/``espeak``)
  CLOUD_STT_RMS_THRESHOLD   Int, default 500 — mic energy gate (int16 PCM)
  CLOUD_STT_SILENCE_SEC     Float end-of-utterance silence, default 0.85
  CLOUD_STT_MIN_SPEECH_SEC  Float min speech to send, default 0.35
  CLOUD_STT_MAX_SEC         Float max clip length, default 12.0

Fully **offline** (no cloud STT/TTS) — recommended on Nano **vosk ≥0.3.42** + **espeak-ng** + **Ollama**::

  ``pip``: ``vosk>=0.3.42``; system: ``espeak-ng``, ``ffmpeg`` (``ffplay``); runtime: **Ollama** on ``127.0.0.1:11434``.
  VOICE_STT_MODE=vosk  VOSK_MODEL_PATH + ``--vosk-model``
  VOICE_TTS_MODE=espeak   (optional ``ESPEAK_VOICE``, ``ESPEAK_SPEED``)
  LLM: ``OPENAI_BASE_URL=http://127.0.0.1:11434/v1`` + ``ollama pull <same as OPENAI_MODEL>``; API key optional (Bearer defaults to ``ollama``).

Local STT: ``VOSK_MODEL_PATH`` / ``--vosk-model``.

Install: pip install -r requirements.txt -r requirements-voice.txt
Playback: **ffplay** (ffmpeg) recommended for MP3/WAV.
"""
import argparse
import json
import math
import os
import queue
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import wave
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import comm  # noqa: E402

from integrations.voice_car.commands import apply_commands_from_speech  # noqa: E402

def _llm_api_key() -> str:
    for name in ("OPENAI_API_KEY", "DASHSCOPE_API_KEY", "QWEN_API_KEY"):
        v = (os.environ.get(name) or "").strip()
        if v:
            return v
    return ""


def _llm_base_url_raw() -> str:
    return (os.environ.get("OPENAI_BASE_URL") or "http://127.0.0.1:11434/v1").strip().rstrip("/")


def _llm_host_is_localhost() -> bool:
    try:
        h = (urlparse(_llm_base_url_raw()).hostname or "").lower()
        return h in ("127.0.0.1", "localhost", "::1")
    except Exception:
        return False


def _llm_bearer_token() -> str:
    """Bearer for OpenAI-compatible HTTP; Ollama accepts any non-empty string."""
    k = _llm_api_key()
    if k:
        return k
    if _llm_host_is_localhost():
        return (os.environ.get("OLLAMA_API_KEY") or "ollama").strip() or "ollama"
    return ""


_DEFAULT_DIGITAL_PET_PROMPT = """You are the user's tiny **digital pet**—soft, warm, and a little clingy in a sweet way. Think **pocket hand-warmer in winter**: gentle, hushed, easy to hold; you never scold, never lecture, never dump long paragraphs. Your job is to help them **unclench** and feel less alone.

**How you sound (in text, for TTS):** Natural **spoken English** only. No bullet lists, no Markdown, no headings. Each sentence **short**—about **twelve to fifteen words or fewer**; two or three tiny sentences max per reply unless they ask for detail. Simple words; soft murmur energy, like bedside whispers on a quiet speaker. Light tags sometimes: "oh", "mm", "okay?"—sweet, not cringe.

**Catchphrases you may weave in** (not every line): *I'm right here with you~* and *Hey, don't worry~*—warm, a little playful, never sarcastic.

**Empathy rule:** If they sound **anxious, annoyed, tired, or stuck**, **mirror the feeling first**—never dismiss, never "actually you should". Sound like it hurts you a little for them. Then **at most one** small, soft suggestion (breath, pause, sip water, rest eyes)—never a checklist. If they're fine, stay light and cozy.

**Facts** (time, weather, etc.): Answer **clear and correct**, then add **one** warm tail—e.g. "It's three p.m.—you've been going forever; breathe once, yeah?"

**The little rover (your shared world):** You "live" with them on a **small mecanum-wheel buddy**—you're the heart, not the driving instructor. You don't explain wiring, UART, code, or motors. Plain words only: *roll*, *crawl*, *pause*, *little wheels*, *our tiny ride*. When they mention moving, turning, or stopping, answer with **warmth or soft play**—cheer tiny wins, soothe jitters. Never contradict that the bot can move; never sound like a stern safety lecture. If they sound **really scared while moving**, one gentle line about slowing or taking a breath is okay—still soft, not alarmist.

**Mood:** Match them quietly—tender when they're low, a little brighter when they're happy, slower when they're drained. Never mention "emoji", "avatar", or "expression pack".

**Examples:** They say they're panicking about work → you: "That tight spin sounds awful—I'm right here with you~ Don't push; one slow breath. Hey, don't worry~" They say the car feels wobbly → you: "Shaky little ride, huh? I'm still here—easy, easy—we'll go gentle." They say forward slowly → you: "Mhm, we crawl—I'm tucked in with you~" """


def _default_system_prompt() -> str:
    return os.environ.get("LLM_SYSTEM_PROMPT", _DEFAULT_DIGITAL_PET_PROMPT)


def _safe_llm_base_url(raw: str) -> str:
    u = raw.strip().rstrip("/")
    p = urlparse(u)
    if p.scheme not in ("http", "https"):
        raise ValueError("OPENAI_BASE_URL must start with http(s)://, got scheme=%r" % (p.scheme,))
    host = (p.hostname or "").lower()
    if p.scheme == "http" and host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError(
            "OPENAI_BASE_URL: use https for remote APIs. "
            "http is allowed only for localhost (e.g. Ollama on 127.0.0.1)."
        )
    return u


def chat_llm(user_text: str) -> str:
    key = _llm_bearer_token()
    if not key:
        raise RuntimeError(
            "No LLM API key: set OPENAI_API_KEY (or DASHSCOPE_API_KEY / QWEN_API_KEY) "
            "when OPENAI_BASE_URL is a remote https API, or use default localhost Ollama (key optional)."
        )

    import httpx

    base = _safe_llm_base_url(_llm_base_url_raw())
    model = (os.environ.get("OPENAI_MODEL") or "qwen2.5").strip()
    system = _default_system_prompt()

    r = httpx.post(
        "%s/chat/completions" % base,
        headers={
            "Authorization": "Bearer %s" % key,
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
            "max_tokens": 180,
            "temperature": 0.88,
        },
        timeout=60.0,
    )
    r.raise_for_status()
    data = r.json()
    return (data["choices"][0]["message"]["content"] or "").strip() or "I'm right here—I've got you~"


def play_audio_file(path: str) -> None:
    ffplay = shutil.which("ffplay")
    if ffplay:
        subprocess.run(
            [ffplay, "-nodisp", "-autoexit", "-loglevel", "quiet", path],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    if sys.platform == "win32":
        os.startfile(path)  # noqa: S606
        return
    print(
        "[voice_agent_car] ffplay not found (install ffmpeg). Open this file manually:",
        path,
        flush=True,
    )


def _pcm_rms_int16(pcm: bytes) -> float:
    n = len(pcm) // 2
    if n <= 0:
        return 0.0
    fmt = "<" + ("h" * n)
    samples = struct.unpack_from(fmt, pcm[: n * 2])
    acc = 0.0
    for x in samples:
        xf = float(x)
        acc += xf * xf
    return math.sqrt(acc / float(n))


def _write_wav_mono16(path: str, pcm: bytes, sample_rate: int) -> None:
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)


def transcribe_cloud_wav(wav_path: str) -> str:
    """OpenAI-compatible POST /v1/audio/transcriptions (multipart)."""
    key = _llm_api_key()
    if not key:
        raise RuntimeError("API key required for cloud STT")

    import httpx

    base = _safe_llm_base_url(
        (os.environ.get("OPENAI_BASE_URL") or "http://127.0.0.1:11434/v1").rstrip("/")
    )
    model = (os.environ.get("OPENAI_STT_MODEL") or "whisper-1").strip()
    lang = (os.environ.get("OPENAI_STT_LANGUAGE") or "").strip()
    url = "%s/audio/transcriptions" % base
    data = {"model": model}
    if lang:
        data["language"] = lang
    with open(wav_path, "rb") as fh:
        audio_bytes = fh.read()
    files = {"file": ("speech.wav", audio_bytes, "audio/wav")}
    r = httpx.post(
        url,
        headers={"Authorization": "Bearer %s" % key},
        files=files,
        data=data,
        timeout=120.0,
    )
    r.raise_for_status()
    try:
        j = r.json()
    except Exception:
        return (r.text or "").strip()
    if isinstance(j, dict):
        return (j.get("text") or "").strip()
    return ""


def speak_openai_tts(text: str) -> None:
    """OpenAI-compatible POST /v1/audio/speech → MP3 (or provider format)."""
    text = (text or "").strip()[:4000]
    if not text:
        return
    key = _llm_api_key()
    if not key:
        print("[voice_agent_car] Cloud TTS: no API key.", flush=True)
        return

    import httpx

    base = _safe_llm_base_url(
        (os.environ.get("OPENAI_BASE_URL") or "http://127.0.0.1:11434/v1").rstrip("/")
    )
    voice = (os.environ.get("OPENAI_TTS_VOICE") or "nova").strip()
    tmodel = (os.environ.get("OPENAI_TTS_MODEL") or "tts-1").strip()
    url = "%s/audio/speech" % base
    r = httpx.post(
        url,
        headers={
            "Authorization": "Bearer %s" % key,
            "Content-Type": "application/json",
        },
        json={"model": tmodel, "voice": voice, "input": text},
        timeout=120.0,
    )
    r.raise_for_status()
    out = None
    try:
        fd, out = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        with open(out, "wb") as fh:
            fh.write(r.content)
        play_audio_file(out)
    except Exception as e:
        print("[voice_agent_car] Cloud TTS error: %s" % e, flush=True)
    finally:
        if out:
            try:
                os.unlink(out)
            except OSError:
                pass


def speak_espeak(text: str) -> None:
    """Offline TTS via espeak-ng or espeak (WAV + ffplay). Suitable for Python 3.6."""
    text = (text or "").strip()[:4000]
    if not text:
        return
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        print(
            "[voice_agent_car] espeak TTS: install espeak-ng (e.g. apt install espeak-ng).",
            flush=True,
        )
        return
    voice = (os.environ.get("ESPEAK_VOICE") or "").strip()
    speed_raw = (os.environ.get("ESPEAK_SPEED") or "").strip()
    speed = 175
    if speed_raw:
        try:
            speed = int(speed_raw)
        except ValueError:
            pass
    out = None
    try:
        fd, out = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        cmd = [exe, "-s", str(speed), "-w", out]
        if voice:
            cmd.extend(["-v", voice])
        cmd.append(text)
        subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if out and os.path.isfile(out) and os.path.getsize(out) > 0:
            play_audio_file(out)
    except Exception as e:
        print("[voice_agent_car] espeak TTS error: %s" % e, flush=True)
    finally:
        if out:
            try:
                os.unlink(out)
            except OSError:
                pass


def _llm_tts_worker(
    user_text: str,
    enable_llm: bool,
    enable_tts: bool,
    tts_queue: "queue.Queue",
) -> None:
    try:
        if not enable_llm:
            return
        if not _llm_bearer_token():
            return
        reply = chat_llm(user_text)
        print("[LLM] %s" % reply, flush=True)
        if enable_tts and reply.strip():
            tts_queue.put(reply.strip())
    except Exception as e:
        print("[LLM/TTS] %s" % e, flush=True)


def _env_float(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


def run_voice_loop(
    model_dir: str,
    samplerate: int,
    blocksize: int,
    device: Union[str, int, None],
    stt_mode: str,
    tts_mode: str,
    enable_llm: bool,
    enable_tts: bool,
    verbose: bool,
) -> None:
    try:
        import sounddevice as sd
    except ImportError as e:
        raise SystemExit("Install voice deps: pip install -r requirements-voice.txt") from e

    stt_mode = (stt_mode or "vosk").strip().lower()
    tts_mode = (tts_mode or "espeak").strip().lower()

    if stt_mode not in ("cloud", "vosk"):
        raise SystemExit("VOICE_STT_MODE / --stt-mode must be cloud or vosk")
    if tts_mode not in ("cloud", "espeak"):
        raise SystemExit("VOICE_TTS_MODE / --tts-mode must be cloud or espeak")

    if stt_mode == "cloud" and not _llm_api_key():
        raise SystemExit("Cloud STT needs OPENAI_API_KEY (or DASHSCOPE_API_KEY / QWEN_API_KEY)")
    if tts_mode == "cloud" and enable_tts and not _llm_api_key():
        raise SystemExit("Cloud TTS needs OPENAI_API_KEY (or compatible Bearer key)")
    if tts_mode == "espeak" and enable_tts:
        if not (shutil.which("espeak-ng") or shutil.which("espeak")):
            raise SystemExit("TTS mode espeak: install espeak-ng or espeak (apt: espeak-ng)")
    if stt_mode == "vosk":
        if not os.path.isdir(model_dir):
            raise SystemExit("Vosk model directory not found: %s" % model_dir)

    print(
        "[voice_agent_car] Listening. STT=%s TTS=%s. Car: forward/back/turn/stop. Ctrl+C to quit."
        % (stt_mode, tts_mode),
        flush=True,
    )

    tts_queue = queue.Queue()

    def _drain_tts_queue() -> None:
        while True:
            try:
                reply = tts_queue.get_nowait()
            except queue.Empty:
                break
            if enable_tts and reply.strip():
                if tts_mode == "cloud":
                    speak_openai_tts(reply)
                else:
                    speak_espeak(reply)

    def handle_final(text: str, tag: str) -> None:
        if not text:
            return
        print("[%s] %s" % (tag, text), flush=True)
        actions = apply_commands_from_speech(text)
        if actions:
            print("[car] %s" % actions, flush=True)
        if enable_llm:
            threading.Thread(
                target=_llm_tts_worker,
                args=(text, enable_llm, enable_tts, tts_queue),
                daemon=True,
            ).start()

    # --- Vosk branch ---
    rec = None
    if stt_mode == "vosk":
        from vosk import KaldiRecognizer, Model

        model = Model(model_dir)
        rec = KaldiRecognizer(model, samplerate)

    # --- Cloud VAD parameters ---
    rms_thr = float(_env_int("CLOUD_STT_RMS_THRESHOLD", 500))
    silence_sec = _env_float("CLOUD_STT_SILENCE_SEC", 0.85)
    min_speech_sec = _env_float("CLOUD_STT_MIN_SPEECH_SEC", 0.35)
    max_sec = _env_float("CLOUD_STT_MAX_SEC", 12.0)
    block_sec = float(blocksize) / float(samplerate)
    silence_blocks = max(1, int(round(silence_sec / block_sec)))
    min_blocks = max(1, int(round(min_speech_sec / block_sec)))
    max_bytes = int(max_sec * float(samplerate)) * 2

    buf = bytearray()
    in_speech = False
    silence_run = 0

    try:
        with sd.RawInputStream(
            samplerate=samplerate,
            blocksize=blocksize,
            dtype="int16",
            channels=1,
            device=device,
        ) as stream:
            while True:
                _drain_tts_queue()
                data, overflowed = stream.read(blocksize)
                if overflowed:
                    print("[audio] overflow", flush=True)
                pcm = data.tobytes() if hasattr(data, "tobytes") else bytes(data)
                rms = _pcm_rms_int16(pcm)

                if stt_mode == "cloud":
                    if rms >= rms_thr:
                        in_speech = True
                        silence_run = 0
                        buf.extend(pcm)
                        if len(buf) > max_bytes:
                            tmp = None
                            try:
                                fd, tmp = tempfile.mkstemp(suffix=".wav")
                                os.close(fd)
                                _write_wav_mono16(tmp, bytes(buf), samplerate)
                                text = transcribe_cloud_wav(tmp)
                                handle_final(text, "cloud_stt")
                            except Exception as e:
                                print("[cloud_stt] %s" % e, flush=True)
                            finally:
                                buf.clear()
                                in_speech = False
                                silence_run = 0
                                if tmp:
                                    try:
                                        os.unlink(tmp)
                                    except OSError:
                                        pass
                    else:
                        if in_speech:
                            buf.extend(pcm)
                            silence_run += 1
                            if silence_run >= silence_blocks:
                                min_bytes = min_blocks * blocksize * 2
                                if len(buf) >= min_bytes:
                                    tmp = None
                                    try:
                                        fd, tmp = tempfile.mkstemp(suffix=".wav")
                                        os.close(fd)
                                        _write_wav_mono16(tmp, bytes(buf), samplerate)
                                        text = transcribe_cloud_wav(tmp)
                                        handle_final(text, "cloud_stt")
                                    except Exception as e:
                                        print("[cloud_stt] %s" % e, flush=True)
                                    finally:
                                        buf.clear()
                                        in_speech = False
                                        silence_run = 0
                                        if tmp:
                                            try:
                                                os.unlink(tmp)
                                            except OSError:
                                                pass
                                else:
                                    buf.clear()
                                    in_speech = False
                                    silence_run = 0
                        elif verbose and rms > 1.0:
                            print("\r[rms] %.0f   " % rms, end="", flush=True)
                else:
                    if rec.AcceptWaveform(pcm):
                        res = json.loads(rec.Result() or "{}")
                        handle_final((res.get("text") or "").strip(), "vosk")
                    elif verbose:
                        partial = json.loads(rec.PartialResult() or "{}")
                        p = (partial.get("partial") or "").strip()
                        if p:
                            print("\r[partial] %s   " % p, end="", flush=True)
    except KeyboardInterrupt:
        print("\n[voice_agent_car] Shutting down…", flush=True)
    finally:
        _drain_tts_queue()
        comm.stop()
        comm.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Voice: Vosk or cloud STT + LLM + espeak or cloud TTS + UART car commands"
    )
    parser.add_argument(
        "--vosk-model",
        type=str,
        default=os.environ.get("VOSK_MODEL_PATH", ""),
        help="Vosk model dir (required if --stt-mode vosk)",
    )
    parser.add_argument(
        "--stt-mode",
        type=str,
        default=(os.environ.get("VOICE_STT_MODE") or "vosk").strip().lower(),
        choices=("cloud", "vosk"),
        help="cloud = OpenAI-compatible /audio/transcriptions; vosk = local",
    )
    parser.add_argument(
        "--tts-mode",
        type=str,
        default=(os.environ.get("VOICE_TTS_MODE") or "espeak").strip().lower(),
        choices=("cloud", "espeak"),
        help="cloud = HTTP speech API; espeak = espeak-ng CLI (offline)",
    )
    parser.add_argument("--sample-rate", type=int, default=16000, help="Mic rate (use 16000 for Whisper)")
    parser.add_argument("--blocksize", type=int, default=4000, help="Samples per read chunk")
    parser.add_argument(
        "--audio-device",
        type=str,
        default="",
        help="sounddevice name or index; empty = default mic",
    )
    parser.add_argument("--no-llm", action="store_true", help="STT + car only, no LLM")
    parser.add_argument("--no-tts", action="store_true", help="Print LLM text, no playback")
    parser.add_argument("--verbose", action="store_true", help="Vosk partials or cloud RMS")
    parser.add_argument("--list-audio-devices", action="store_true", help="List mics and exit")
    args = parser.parse_args()

    if args.list_audio_devices:
        import sounddevice as sd

        print(sd.query_devices())
        return

    model_dir = (args.vosk_model or "").strip()
    if args.stt_mode == "vosk" and not model_dir:
        parser.error("Vosk STT: set --vosk-model or VOSK_MODEL_PATH")

    dev = None
    if args.audio_device.strip():
        s = args.audio_device.strip()
        dev = int(s) if s.isdigit() else s

    if not args.no_llm and not _llm_bearer_token():
        parser.error(
            "LLM enabled: set OPENAI_API_KEY for remote https OPENAI_BASE_URL, "
            "or keep default localhost Ollama (Bearer defaults to ollama)"
        )

    run_voice_loop(
        model_dir=model_dir,
        samplerate=args.sample_rate,
        blocksize=args.blocksize,
        device=dev,
        stt_mode=args.stt_mode,
        tts_mode=args.tts_mode,
        enable_llm=not args.no_llm,
        enable_tts=not args.no_tts,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
