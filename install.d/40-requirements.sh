# shellcheck shell=bash

echo "==> Installing requirements.txt ..."
pip install -r "$REPO_ROOT/requirements.txt"

if [[ "${SKIP_VOICE:-0}" != "1" ]]; then
  echo "==> Installing voice dependencies (requirements-voice.txt) ..."
  pip install -r "$REPO_ROOT/requirements-voice.txt"
  if ! command -v ffplay >/dev/null 2>&1; then
    echo "Warning: ffplay not found; TTS playback (cloud/espeak WAV) needs ffmpeg (if SKIP_APT=1, run: sudo apt install ffmpeg)"
  fi
else
  echo "==> SKIP_VOICE=1: skipping voice pip packages, ffmpeg, espeak-ng, and PortAudio apt packages"
fi
