# shellcheck shell=bash

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 not found"
  exit 1
fi

PYVER="$(python3 -c 'import sys; print("%d%d"%sys.version_info[:2])' 2>/dev/null || echo "00")"
echo "==> python3 version tag (xy): $PYVER (cp36 corresponds to 36)"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "==> Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
fi
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
python -m pip install -U pip setuptools wheel

echo "==> Installing NumPy (before PyTorch, per project docs)..."
pip install "numpy>=1.19,<1.23"
