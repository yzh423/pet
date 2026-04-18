# shellcheck shell=bash

if [[ "${SKIP_VOICE:-0}" != "1" ]] && [[ "${SKIP_VOSK_MODEL:-0}" != "1" ]]; then
  cd "$REPO_ROOT"
  if [[ -d "$REPO_ROOT/$VOSK_EXTRACT_NAME" ]]; then
    echo "==> Already present: $REPO_ROOT/$VOSK_EXTRACT_NAME"
  else
    echo "==> Downloading small English Vosk model..."
    wget -nc "$VOSK_MODEL_URL" -O "$REPO_ROOT/$VOSK_MODEL_TAR"
    tar -xzf "$REPO_ROOT/$VOSK_MODEL_TAR" -C "$REPO_ROOT"
  fi
  echo ""
  echo "Before running voice (default: vosk + espeak + local Ollama, no public cloud):"
  echo "  export VOSK_MODEL_PATH=\"$REPO_ROOT/$VOSK_EXTRACT_NAME\""
  echo "  export ROBOT_SERIAL_PORT=/dev/ttyUSB0"
  echo "  ollama pull qwen2.5   # or match OPENAI_MODEL"
  echo "  python3 voice_agent_car.py --vosk-model \"\$VOSK_MODEL_PATH\""
  echo "Optional cloud STT/TTS + remote LLM — see README.md (OPENAI_BASE_URL, OPENAI_API_KEY, VOICE_*=cloud)."
else
  echo "==> Skipping Vosk model download (SKIP_VOICE or SKIP_VOSK_MODEL)"
fi
