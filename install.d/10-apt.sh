# shellcheck shell=bash

if [[ "${SKIP_APT:-0}" != "1" ]]; then
  echo "==> Installing system packages (sudo required)..."
  sudo apt-get update
  sudo apt-get install -y \
    python3-pip python3-venv libopenblas-dev \
    build-essential cmake pkg-config git \
    libjpeg-dev libpng-dev libtiff-dev \
    libavcodec-dev libavformat-dev libswscale-dev \
    libv4l-dev v4l-utils \
    libglib2.0-0 libgomp1 libgl1-mesa-glx
  if [[ "${SKIP_VOICE:-0}" != "1" ]]; then
    sudo apt-get install -y ffmpeg espeak-ng \
      libportaudio2 portaudio19-dev libasound2-dev
  fi
else
  echo "==> SKIP_APT=1: skipping apt-get"
fi

echo "==> Adding user to dialout (Arduino serial); log out and back in for this to take effect"
sudo usermod -aG dialout "$USER" 2>/dev/null || true
