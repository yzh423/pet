# shellcheck shell=bash
# Paths (after 05-pysot-clone so pysot/ may exist).

VENV_DIR="${VENV_DIR:-$HOME/venv-car}"

JP_TORCH_WHEEL_URL="${JP_TORCH_WHEEL_URL:-https://developer.download.nvidia.com/compute/redist/jp/v461/pytorch/torch-1.11.0a0+17540c5+nv22.01-cp36-cp36m-linux_aarch64.whl}"
JP_TORCH_WHEEL_FILE="${JP_TORCH_WHEEL_FILE:-torch-1.11.0a0+17540c5+nv22.01-cp36-cp36m-linux_aarch64.whl}"

# Bundled pysot-master/ preferred over sibling pysot/.
if [[ -d "$REPO_ROOT/pysot-master/pysot" ]] && [[ -f "$REPO_ROOT/pysot-master/setup.py" ]]; then
  PYSOT_ROOT="$REPO_ROOT/pysot-master"
elif [[ -d "$REPO_ROOT/pysot/pysot" ]] && [[ -f "$REPO_ROOT/pysot/setup.py" ]]; then
  PYSOT_ROOT="$REPO_ROOT/pysot"
else
  PYSOT_ROOT="$REPO_ROOT/pysot-master"
fi
export PYSOT_ROOT
echo "==> PySOT root: $PYSOT_ROOT"

PYSOT_MODEL_ID="${PYSOT_MODEL_ID:-1JB94pZTvB1ZByU-qSJn4ZAIfjLWE5EBJ}"
PYSOT_MODEL_DIR="$PYSOT_ROOT/experiments/siamrpn_mobilev2_l234_dwxcorr"
PYSOT_MODEL_PATH="$PYSOT_MODEL_DIR/model.pth"

VOSK_MODEL_URL="${VOSK_MODEL_URL:-https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.tar.gz}"
VOSK_MODEL_TAR="$(basename "$VOSK_MODEL_URL")"
VOSK_EXTRACT_NAME="vosk-model-small-en-us-0.15"

echo "==> Repository root: $REPO_ROOT"
echo "==> Virtualenv: $VENV_DIR"

ARCH="$(uname -m || true)"
echo "==> Architecture: $ARCH"
