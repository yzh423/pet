# shellcheck shell=bash

if [[ "${SKIP_PYTORCH_WHEEL:-0}" != "1" ]] && [[ "$ARCH" == "aarch64" ]]; then
  if python -c "import torch" 2>/dev/null; then
    echo "==> torch already present; skipping wheel (pip uninstall torch first if you need a reinstall)"
  else
    if [[ "$PYVER" != "36" ]]; then
      echo "Warning: Python is not 3.6; the default wheel may not install."
      echo "         Pick a matching wheel from https://developer.download.nvidia.com/compute/redist/jp/"
      echo "         pip install it, then rerun with SKIP_PYTORCH_WHEEL=1."
      ans="n"
      if [[ -t 0 ]]; then
        read -r -p "Still try downloading the default cp36 wheel? [y/N] " ans || true
      else
        echo "(Non-interactive terminal: not downloading cp36 wheel by default)"
      fi
      if [[ ! "${ans:-}" =~ ^[yY]$ ]]; then
        echo "PyTorch wheel step skipped."
      else
        cd "$HOME"
        wget -nc "$JP_TORCH_WHEEL_URL" -O "$JP_TORCH_WHEEL_FILE" || true
        pip install --no-cache-dir "./$JP_TORCH_WHEEL_FILE"
        cd "$REPO_ROOT"
      fi
    else
      echo "==> Downloading and installing NVIDIA Jetson PyTorch wheel..."
      cd "$HOME"
      wget -nc "$JP_TORCH_WHEEL_URL" -O "$JP_TORCH_WHEEL_FILE"
      pip install --no-cache-dir "./$JP_TORCH_WHEEL_FILE"
      cd "$REPO_ROOT"
    fi
  fi
elif [[ "${SKIP_PYTORCH_WHEEL:-0}" == "1" ]]; then
  echo "==> SKIP_PYTORCH_WHEEL=1: skipping Jetson PyTorch wheel"
else
  echo "==> Not aarch64: skipping NVIDIA Jetson PyTorch wheel (install a matching torch on this machine yourself)"
fi

if python -c "import torch" 2>/dev/null; then
  python -c "import torch; print('torch:', torch.__version__, 'cuda:', torch.cuda.is_available())" || true
fi
