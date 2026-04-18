# coding: utf-8
"""
Try on PC: typed text → LLM → **espeak or cloud TTS** (default **espeak**); or delegate full mic loop to ``voice_agent_car.py``.

Examples::

  # Default: local Ollama + espeak (same env as voice_agent_car)
  python pc_voice_llm_demo.py --text "hello"

  set OPENAI_API_KEY=sk-...
  set VOICE_TTS_MODE=cloud
  python pc_voice_llm_demo.py --text "I'm a bit tired today" --tts-mode cloud

  python pc_voice_llm_demo.py --listen --vosk-model /path/to/vosk-model-small-en-us-0.15
  python pc_voice_llm_demo.py --listen -- --stt-mode cloud --tts-mode cloud
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from voice_agent_car import chat_llm, speak_espeak, speak_openai_tts  # noqa: E402


def run_typed_once(user_text: str, *, tts_mode: str) -> int:
    print("[you] %s" % user_text, flush=True)
    try:
        reply = chat_llm(user_text)
    except RuntimeError as e:
        print("[error] %s" % e, flush=True)
        return 1
    except Exception as e:
        print("[error] LLM request failed: %s" % e, flush=True)
        return 1
    print("[LLM] %s" % reply, flush=True)
    tm = (tts_mode or "espeak").lower()
    if tm == "cloud":
        speak_openai_tts(reply)
    else:
        speak_espeak(reply)
    return 0


def run_interactive(*, tts_mode: str) -> None:
    print(
        "Interactive LLM + TTS. Empty line = quit.\n"
        "Default TTS=espeak; cloud needs OPENAI_API_KEY + remote OPENAI_BASE_URL. LLM: Ollama on 127.0.0.1 or set base URL + key.",
        flush=True,
    )
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("", flush=True)
            break
        if not line:
            break
        run_typed_once(line, tts_mode=tts_mode)


def run_listen(vosk_model: str, argv_tail):
    script = _ROOT / "voice_agent_car.py"
    if not script.is_file():
        print("voice_agent_car.py not found next to this script.", flush=True)
        return 1
    cmd = [sys.executable, str(script)]
    if (vosk_model or "").strip():
        cmd += ["--vosk-model", vosk_model.strip()]
    cmd += list(argv_tail)
    print("[pc_voice_llm_demo] Running:", " ".join(cmd), flush=True)
    return subprocess.call(cmd)


def main() -> None:
    p = argparse.ArgumentParser(description="PC try: LLM + espeak or cloud TTS; optional mic via voice_agent_car")
    p.add_argument("--text", type=str, default="", help="One user line")
    p.add_argument("--listen", action="store_true", help="Run voice_agent_car.py; extra args after --")
    p.add_argument("--vosk-model", type=str, default=os.environ.get("VOSK_MODEL_PATH", ""))
    p.add_argument(
        "--tts-mode",
        type=str,
        default=(os.environ.get("VOICE_TTS_MODE") or "espeak").strip().lower(),
        choices=("cloud", "espeak"),
    )
    args, tail = p.parse_known_args()

    if args.listen:
        raise SystemExit(run_listen(args.vosk_model, tail))

    tts_mode = args.tts_mode

    if args.text.strip():
        raise SystemExit(run_typed_once(args.text.strip(), tts_mode=tts_mode))
    run_interactive(tts_mode=tts_mode)


if __name__ == "__main__":
    main()
