# shellcheck shell=bash

if [[ "${SKIP_MODEL:-0}" != "1" ]]; then
  mkdir -p "$PYSOT_MODEL_DIR"
  if [[ -f "$PYSOT_MODEL_PATH" ]]; then
    echo "==> Found $PYSOT_MODEL_PATH — skipping download"
  else
    echo "==> Attempting to download PySOT weights to $PYSOT_MODEL_PATH ..."
    pip install -q gdown || pip install gdown
    if gdown --id "$PYSOT_MODEL_ID" -O "$PYSOT_MODEL_PATH" 2>/dev/null; then
      echo "==> model.pth download finished"
    else
      echo "Warning: gdown failed (network or quota). Download manually from $PYSOT_ROOT/MODEL_ZOO.md to:"
      echo "         $PYSOT_MODEL_PATH"
    fi
  fi
else
  echo "==> SKIP_MODEL=1: skipping model.pth download"
fi
