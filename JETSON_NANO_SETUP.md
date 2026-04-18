# Jetson Nano 安装与运行说明（Ubuntu 18.04 / JetPack 4.6.x）

本文档说明在本仓库 **「USB 1080p 摄像头 + PySOT 跟随 + Arduino 串口」** 路径下，在 **NVIDIA Jetson Nano**（官方镜像多为 **Ubuntu 18.04 + L4T**）上的具体操作步骤。  
语音栈（默认 **Vosk + espeak + 本机 Ollama**；可选云 STT/TTS）见主 **README.md** 的 **`voice_agent_car.py`** 与 **`requirements-voice.txt`**。

---

## 1. 硬件与软件前提

| 项目 | 说明 |
|------|------|
| Jetson Nano | 建议 4GB 版配合 swap 使用 |
| 电源 | **5V 4A** 级别，保证 USB 摄像头与串口稳定 |
| microSD | ≥32GB，烧录 **Jetson Nano 专用 JetPack 4.6.x** 镜像 |
| USB 摄像头（1080p） | 建议接 USB 3.0；`jetson_follow_track.py` 默认请求 1920×1080 |
| Arduino Mega2560 | USB 连接；下位机实现 README 中单字节 `F/B/L/R/S` 协议，115200 |

---

## 2. 确认系统与 JetPack（决定 PyTorch wheel 目录）

在 Nano 终端执行：

```bash
cat /etc/nv_tegra_release
head -n 1 /etc/os-release
python3 --version
```

- **R32.7.x** 一般对应 **JetPack 4.6.1**，本文 **第 9 节** 使用官方目录 `jp/v461/pytorch` 中的示例 wheel（**cp36**，与 Ubuntu 18.04 默认 `python3` 常见版本一致）。
- 若 `nv_tegra_release` 不同：在浏览器打开  
  `https://developer.download.nvidia.com/compute/redist/jp/`  
  进入与你 JetPack 匹配的 **`vXXX/pytorch/`**，**以该目录下列出的 `.whl` 实际文件名为准**。

---

## 3. 系统包与编译依赖

```bash
sudo apt-get update
sudo apt-get install -y \
  python3-pip python3-venv libopenblas-dev \
  build-essential cmake pkg-config git \
  libjpeg-dev libpng-dev libtiff-dev \
  libavcodec-dev libavformat-dev libswscale-dev \
  libv4l-dev v4l-utils
```

---

## 4. 串口权限（Arduino）

```bash
sudo usermod -aG dialout $USER
```

**注销并重新登录**（或重启）后执行 `groups`，应包含 `dialout`。

---

## 5. 性能模式与交换分区

```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

**swap 示例（8GB）**（SD 空间紧张可改为 `4G`）：

```bash
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 6. 放置本仓库

将仓库拷贝或克隆到 Nano，例如：

```text
/home/<用户名>/nano-jetson-car
```

下文以 **`~/nano-jetson-car`** 表示该路径。

---

## 7. Python 虚拟环境

Ubuntu 18.04 上 **`python3` 多为 3.6**，与 JetPack **4.6.1** 官方 `v461` 目录中常见的 **`cp36`** PyTorch wheel 一致，建议优先使用该解释器建 venv：

```bash
python3 -m venv ~/venv-car
source ~/venv-car/bin/activate
python -m pip install -U pip setuptools wheel
```

若必须使用 Python 3.8+，需在 NVIDIA **兼容性表**中选取对应 **cp38/cp39** 的 wheel，且勿使用 PC 的 `pip install torch` 默认包。

---

## 8. NumPy（在 PyTorch 之前安装）

```bash
pip install "numpy>=1.19,<1.23"
```

---

## 9. 安装 NVIDIA 官方 PyTorch（JetPack 4.6.1 + Python 3.6 示例）

在已激活 `~/venv-car` 的前提下：

```bash
cd ~
wget https://developer.download.nvidia.com/compute/redist/jp/v461/pytorch/torch-1.11.0a0+17540c5+nv22.01-cp36-cp36m-linux_aarch64.whl
pip install --no-cache-dir ./torch-1.11.0a0+17540c5+nv22.01-cp36-cp36m-linux_aarch64.whl
```

验证：

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

说明：本仓库主脚本 **`jetson_follow_track.py`** 与 **PySOT** 推理路径**不强制依赖 torchvision**；若其他代码需要，请按 NVIDIA 文档安装与当前 **torch / JetPack** 匹配的 **torchvision**，避免版本冲突。

---

## 10. `import torch` 若报缺库（按需）

部分 JetPack 4.x 环境需补充：

```bash
export LD_LIBRARY_PATH=/usr/lib/llvm-8/lib:${LD_LIBRARY_PATH}
```

可将上述 `export` 写入 `~/.bashrc`（放在 `source ~/venv-car/bin/activate` 之后），避免每次手动设置。

---

## 11. 安装仓库 `requirements.txt`

```bash
cd ~/nano-jetson-car
source ~/venv-car/bin/activate
pip install -r requirements.txt
```

---

## 12. 编译 PySOT

```bash
cd ~/nano-jetson-car/pysot-master
pip install pyyaml yacs tqdm colorama matplotlib cython tensorboardX
python setup.py build_ext --inplace
```

`jetson_follow_track.py` 会将 **`pysot-master/`**（仓库内新版 PySOT，与 [STVIR/pysot](https://github.com/STVIR/pysot) 同源，**优先**）或旁的 **`pysot/`** 加入 `sys.path`；也可用 **`PYSOT_HOME`** 指向任意 checkout。一般无需再设 `PYTHONPATH`。

---

## 13. 下载跟踪权重 `model.pth`

1. 阅读 **`pysot-master/MODEL_ZOO.md`**（与 [上游 MODEL_ZOO](https://github.com/STVIR/pysot/blob/master/MODEL_ZOO.md) 一致），下载 **`model.pth`**。  
2. Nano 上建议使用 **MobileNetV2** 等轻量配置以减轻算力。  
3. 示例路径（与仓库默认 `--config` 一致）：

```text
~/nano-jetson-car/pysot-master/experiments/siamrpn_mobilev2_l234_dwxcorr/model.pth
```

---

## 14. 检查摄像头与串口

```bash
v4l2-ctl --list-devices
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

- 摄像头在 OpenCV 中多为 **`--device 0`**。  
- Arduino 常见为 **`/dev/ttyUSB0`** 或 **`/dev/ttyACM0`**。

---

## 15. 运行视觉跟随（USB 摄像头）

### 15.1 有显示器（首次用手动框选目标）

```bash
cd ~/nano-jetson-car
source ~/venv-car/bin/activate
export ROBOT_SERIAL_PORT=/dev/ttyUSB0
python jetson_follow_track.py --device 0 \
  --snapshot pysot-master/experiments/siamrpn_mobilev2_l234_dwxcorr/model.pth
```

串口为 **`ttyACM0`** 时：

```bash
export ROBOT_SERIAL_PORT=/dev/ttyACM0
```

或使用脚本参数（等价于设置 `ROBOT_SERIAL_PORT`）：

```bash
python jetson_follow_track.py --device 0 \
  --serial-port /dev/ttyACM0 \
  --snapshot pysot-master/experiments/siamrpn_mobilev2_l234_dwxcorr/model.pth
```

窗口内框选目标；按 **`q`** 退出。退出时脚本会 **`comm.stop()`** 并关闭串口。

### 15.2 无显示器（无头，必须提供初始框）

`--init-bbox` 的 `x,y,w,h` 为 **经 `--max-width` 缩放后的跟踪分辨率**下的坐标（默认 **`--max-width 640`**）：

```bash
python jetson_follow_track.py --device 0 \
  --snapshot pysot-master/experiments/siamrpn_mobilev2_l234_dwxcorr/model.pth \
  --init-bbox 200,180,80,120
```

若 **无图形界面（无 `DISPLAY`，例如纯 SSH）**，请加 **`--no-display`**（仍需 **`--init-bbox`**），否则 `cv2.imshow` 会失败：

```bash
python jetson_follow_track.py --device 0 --no-display \
  --snapshot pysot-master/experiments/siamrpn_mobilev2_l234_dwxcorr/model.pth \
  --init-bbox 200,180,80,120
```

可选 **`--log-every N`**（默认 30）在无界面模式下每 N 帧打印 bbox/指令；**`0`** 关闭。用 **`Ctrl+C`** 结束。

### 15.3 性能相关参数（可选）

| 参数 | 含义 |
|------|------|
| `--cap-width` / `--cap-height` | 摄像头采集分辨率（默认请求 1920×1080） |
| `--max-width` | 送入跟踪的缩放宽度（默认 640，越大越慢） |
| `--deadband` | 中心死区像素（默认 40） |

帧率低时可试：

```bash
python jetson_follow_track.py --device 0 \
  --cap-width 1280 --cap-height 720 \
  --snapshot pysot-master/experiments/siamrpn_mobilev2_l234_dwxcorr/model.pth
```

---

## 16. 串口环境变量说明（与 `comm.py` 一致）

优先级：**`ROBOT_SERIAL_PORT`** → **`ARDUINO_SERIAL_PORT`** → **`STM32_SERIAL_PORT`**；均未设置时 Linux 默认为 **`/dev/ttyUSB0`**。

---

## 17. 官方参考链接

- [Installing PyTorch for Jetson Platform](https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/index.html)  
- [PyTorch for Jetson — Release notes / Compatibility](https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform-release-notes/pytorch-jetson-rel.html)  
- NVIDIA wheel 索引：`https://developer.download.nvidia.com/compute/redist/jp/`

---

## 18. 核对信息（便于排错）

若安装失败，请保存并对比以下输出：

```bash
cat /etc/nv_tegra_release
python3 --version
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

---

*文档与仓库 `README.md` 一致处：视觉为 **USB 摄像头**（默认 1080p 请求）；PyTorch 须用 NVIDIA Jetson wheel；PySOT 编译与 `MODEL_ZOO.md` 权重路径。*
