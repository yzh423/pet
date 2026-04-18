# 环境安装顺序与具体指令（脚本内 / 脚本外）

下文 **`<REPO>`** 表示本仓库在 Jetson 上的路径（示例：`~/nano-jetson-car`）。请把命令里的路径换成你的实际目录。

---

## 一、脚本之前（无法由 `install-environment.txt` / `install.d/` 代劳）

### 1. 硬件与镜像

- 自备：Jetson Nano、电源、≥32GB microSD、USB 摄像头、Arduino Mega2560、USB 线等。
- 在 PC 上用 **NVIDIA SDK Manager 或官方工具** 烧录 **Jetson Nano + JetPack 4.6.x**（文档常见为 Ubuntu 18.04 / L4T R32.7.x）。烧录无单一 shell 指令，按 NVIDIA 官方步骤操作。

### 2. 将仓库放到 Jetson 上

若使用 git（将 URL 换成你的远程地址）：

```bash
cd ~
git clone https://github.com/<your-org-or-user>/<your-repo>.git nano-jetson-car
cd ~/nano-jetson-car
```

若从 U 盘/网盘拷贝，解压后同样 `cd` 到仓库根目录（根目录下应能看到 `install-environment.txt`、`install.d/`、`requirements.txt`）。

### 3. 核对系统与 Python（决定 PyTorch wheel）

```bash
cat /etc/nv_tegra_release
head -n 1 /etc/os-release
python3 --version
uname -m
```

- **R32.7.x** 多对应 JetPack 4.6.1；脚本默认 wheel 为 **Python 3.6（cp36）+ aarch64**。
- 若版本不一致，在浏览器打开索引目录自选 wheel：  
  https://developer.download.nvidia.com/compute/redist/jp/  
  下载对应 `jp/vXXX/pytorch/` 下的 `.whl` 后，可手动安装（见下文「手动安装 PyTorch」），再运行安装脚本时带上 `SKIP_PYTORCH_WHEEL=1`。

### 4.（可选）性能模式与交换分区

```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

**8GB swap 示例**（SD 紧张可改为 `4G`）：

```bash
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 二、运行一键安装脚本

进入**仓库根目录**（与 `install-environment.txt` 同级）：

```bash
cd <REPO>
bash install-environment.txt
```

**仅视觉、不要语音依赖与 Vosk 模型下载**时：

```bash
cd <REPO>
SKIP_VOICE=1 bash install-environment.txt
```

**系统包已装好，跳过 apt**：

```bash
cd <REPO>
SKIP_APT=1 bash install-environment.txt
```

**已自行安装好 Jetson 版 PyTorch**：

```bash
cd <REPO>
SKIP_PYTORCH_WHEEL=1 bash install-environment.txt
```

**自定义虚拟环境路径**：

```bash
cd <REPO>
VENV_DIR="$HOME/my-car-venv" bash install-environment.txt
```

**组合示例**（跳过 apt + 已有 torch + 不要语音）：

```bash
cd <REPO>
SKIP_APT=1 SKIP_PYTORCH_WHEEL=1 SKIP_VOICE=1 bash install-environment.txt
```

---

## 三、脚本内部执行顺序（等价的具体指令）

下列与 `install-environment.txt`（依次 `source` 的 `install.d/[0-9][0-9]-*.sh`）逻辑一致；若你**不用脚本**、想手工逐步做，可按顺序执行（注意：`SKIP_APT=1` 时以下 `apt` 需自己判断是否已安装）。

### 1. 系统包（`SKIP_APT` 未设置时）

```bash
sudo apt-get update
sudo apt-get install -y \
  python3-pip python3-venv libopenblas-dev \
  build-essential cmake pkg-config git \
  libjpeg-dev libpng-dev libtiff-dev \
  libavcodec-dev libavformat-dev libswscale-dev \
  libv4l-dev v4l-utils \
  libglib2.0-0 libgomp1 libgl1-mesa-glx
```

**未设置 `SKIP_VOICE` 时**还会安装：

```bash
sudo apt-get install -y ffmpeg espeak-ng \
  libportaudio2 portaudio19-dev libasound2-dev
```

### 2. 串口用户组（脚本内会执行；生效需注销重登）

```bash
sudo usermod -aG dialout "$USER"
```

### 3. 虚拟环境与 pip

```bash
python3 -m venv ~/venv-car
source ~/venv-car/bin/activate
python -m pip install -U pip setuptools wheel
```

（若使用 `VENV_DIR`，把 `~/venv-car` 换成你的路径。）

### 4. NumPy（在 PyTorch 之前）

```bash
pip install "numpy>=1.19,<1.23"
```

### 5. Jetson 官方 PyTorch wheel（aarch64 + 未跳过 + 尚未安装 torch）

**JetPack 4.6.1 + Python 3.6 示例**（与脚本默认相同）：

```bash
cd ~
wget -nc https://developer.download.nvidia.com/compute/redist/jp/v461/pytorch/torch-1.11.0a0+17540c5+nv22.01-cp36-cp36m-linux_aarch64.whl
source ~/venv-car/bin/activate
pip install --no-cache-dir ./torch-1.11.0a0+17540c5+nv22.01-cp36-cp36m-linux_aarch64.whl
cd <REPO>
```

验证：

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

### 6. 项目 pip 依赖

```bash
cd <REPO>
source ~/venv-car/bin/activate
pip install -r requirements.txt
```

语音栈（与未设置 `SKIP_VOICE` 时一致）：

```bash
pip install -r requirements-voice.txt
```

### 7. 编译 PySOT

```bash
cd <REPO>
source ~/venv-car/bin/activate
pip install pyyaml yacs tqdm colorama matplotlib cython tensorboardX
cd <REPO>/pysot-master
python setup.py build_ext --inplace
cd <REPO>
```

### 8. 下载跟踪权重 `model.pth`（与脚本默认路径一致）

脚本使用 `gdown`。手工等价示例：

```bash
cd <REPO>
source ~/venv-car/bin/activate
pip install gdown
mkdir -p pysot-master/experiments/siamrpn_mobilev2_l234_dwxcorr
gdown --id 1JB94pZTvB1ZByU-qSJn4ZAIfjLWE5EBJ \
  -O pysot-master/experiments/siamrpn_mobilev2_l234_dwxcorr/model.pth
```

若失败，从 `pysot-master/MODEL_ZOO.md`（上游 [STVIR/pysot](https://github.com/STVIR/pysot/blob/master/MODEL_ZOO.md)）手动下载到上述路径。若权重放在旁路克隆 `pysot/` 下，把路径中的 `pysot-master` 换成 `pysot`。

### 9. 下载并解压英语 Vosk 小模型（未 `SKIP_VOICE` / `SKIP_VOSK_MODEL` 时；**默认 `--stt-mode vosk` 需要**）

默认 **`voice_agent_car.py`** 为 **本地 Vosk STT**，一般应下载并解压模型；仅当你打算 **`--stt-mode cloud`** 且全程不用 Vosk 时，才可跳过（`SKIP_VOSK_MODEL=1`）。

```bash
cd <REPO>
wget -nc https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.tar.gz
tar -xzf vosk-model-small-en-us-0.15.tar.gz -C .
```

---

## 四、脚本之后（仍需手动）

### 1. 使 `dialout` 生效并检查

注销并重新登录（或重启），然后：

```bash
groups
```

输出中应包含 `dialout`。

### 2. `import torch` 缺库时（按需）

当前会话临时生效：

```bash
export LD_LIBRARY_PATH=/usr/lib/llvm-8/lib:${LD_LIBRARY_PATH}
```

写入 `~/.bashrc`（建议放在 `source ~/venv-car/bin/activate` 那一行**之后**）：

```bash
grep -q 'llvm-8/lib' ~/.bashrc || echo 'export LD_LIBRARY_PATH=/usr/lib/llvm-8/lib:${LD_LIBRARY_PATH}' >> ~/.bashrc
source ~/.bashrc
```

### 3. 检查摄像头与串口

```bash
v4l2-ctl --list-devices
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

### 4. 运行视觉跟随（有显示器，首次手动画框）

```bash
cd <REPO>
source ~/venv-car/bin/activate
export ROBOT_SERIAL_PORT=/dev/ttyUSB0
python3 jetson_follow_track.py --device 0 \
  --snapshot pysot-master/experiments/siamrpn_mobilev2_l234_dwxcorr/model.pth
```

串口为 `ttyACM0` 时：

```bash
export ROBOT_SERIAL_PORT=/dev/ttyACM0
```

或：

```bash
python3 jetson_follow_track.py --device 0 \
  --serial-port /dev/ttyACM0 \
  --snapshot pysot-master/experiments/siamrpn_mobilev2_l234_dwxcorr/model.pth
```

**无显示器、纯 SSH**（必须带初始框与 `--no-display`）：

```bash
cd <REPO>
source ~/venv-car/bin/activate
export ROBOT_SERIAL_PORT=/dev/ttyUSB0
python3 jetson_follow_track.py --device 0 --no-display \
  --snapshot pysot-master/experiments/siamrpn_mobilev2_l234_dwxcorr/model.pth \
  --init-bbox 200,180,80,120
```

**降低分辨率以减轻负载（可选）**：

```bash
python3 jetson_follow_track.py --device 0 \
  --cap-width 1280 --cap-height 720 \
  --snapshot pysot-master/experiments/siamrpn_mobilev2_l234_dwxcorr/model.pth
```

### 5. 运行语音 `voice_agent_car.py`

默认 **`VOICE_STT_MODE=vosk`**、**`VOICE_TTS_MODE=espeak`**、**`OPENAI_BASE_URL=http://127.0.0.1:11434/v1`**（Ollama）、**`OPENAI_MODEL=qwen2.5`**（须 **`ollama pull`** 同名）；**可不设** **`OPENAI_API_KEY`**。须 **`VOSK_MODEL_PATH`** 与 **`espeak-ng`**、**`ffplay`**。

**默认（本机，无公网语音）**：

```bash
cd <REPO>
source ~/venv-car/bin/activate
pip install -r requirements.txt -r requirements-voice.txt
sudo apt-get install -y espeak-ng ffmpeg   # 若尚未安装
export VOSK_MODEL_PATH="<REPO>/vosk-model-small-en-us-0.15"
export ROBOT_SERIAL_PORT=/dev/ttyUSB0
ollama pull qwen2.5
python3 voice_agent_car.py --vosk-model "$VOSK_MODEL_PATH"
```

**可选：OpenAI 兼容（云 STT + 云 TTS + 远程 LLM）**：

```bash
cd <REPO>
source ~/venv-car/bin/activate
export OPENAI_BASE_URL=https://api.openai.com/v1
export OPENAI_API_KEY="sk-你的密钥"
export OPENAI_MODEL=gpt-4o-mini
export ROBOT_SERIAL_PORT=/dev/ttyUSB0
export VOICE_STT_MODE=cloud
export VOICE_TTS_MODE=cloud
python3 voice_agent_car.py --stt-mode cloud --tts-mode cloud
```

**本机 Ollama**：脚本里 **`OPENAI_BASE_URL`** 同时用于 **LLM、云 STT、云 TTS**，不能填 Ollama 地址却继续用 **cloud** 识别/播报（会请求失败）。要用 Ollama 作对话模型且**完全不上云端 STT/TTS**，请用上一段 **「默认（本机，无公网语音）」**。

**阿里云 DashScope（示例）**：

```bash
cd <REPO>
source ~/venv-car/bin/activate
export OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export DASHSCOPE_API_KEY="sk-你的DashScope密钥"
export OPENAI_MODEL=qwen-turbo
export ROBOT_SERIAL_PORT=/dev/ttyUSB0
export VOICE_STT_MODE=cloud
export VOICE_TTS_MODE=cloud
python3 voice_agent_car.py
```

`OPENAI_BASE_URL` 为 **API 基址**，用浏览器打开根路径常无页面（非故障）。香港可改用 `https://cn-hongkong.dashscope.aliyuncs.com/compatible-mode/v1`，国际新加坡用 `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`（以 [阿里云国际站说明](https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope) 为准）。

**仅识别 + 车控、不调 LLM**：

```bash
python3 voice_agent_car.py --no-llm
```

**不播放 TTS**：

```bash
python3 voice_agent_car.py --no-tts
```

### 6. Arduino

在 Arduino IDE 中烧录你的下位机程序：**115200 波特**，单字节 `F` / `B` / `L` / `R` / `S` 协议（与 `README.md` 一致）。无统一 shell 指令。

---

## 附录 A：`pip install opencv-python` / `import cv2` 常见问题（含具体指令）

先确认报错阶段：**安装失败**（pip 红字）还是 **导入失败**（`import cv2` 报缺 `.so`）。

### A1. 导入时报 `libGL.so.1` / `cannot open shared object file`（Jetson / Ubuntu 常见）

`opencv-python` 默认带 GUI 依赖，系统缺 OpenGL 相关库时会失败。在 Jetson 上执行：

```bash
sudo apt-get update
sudo apt-get install -y libglib2.0-0 libgomp1 libgl1-mesa-glx
```

若提示找不到 `libgl1-mesa-glx`（较新 Ubuntu 常见），可试：

```bash
sudo apt-get install -y libgl1
```

然后重新验证：

```bash
source ~/venv-car/bin/activate
python3 -c "import cv2; print(cv2.__version__)"
```

（`install.d/10-apt.sh` 已尽量把上述包列入 `apt-get`，若你当时用了 `SKIP_APT=1`，请自行补装。）

### A2. pip 安装阶段：版本解析很慢或拉到过新版本、无对应 wheel（尤其 Python 3.6 + aarch64）

先升级 pip，再**固定一段较稳妥的版本号**安装（可按需微调上下界）：

```bash
source ~/venv-car/bin/activate
python3 -m pip install -U pip setuptools wheel
pip install "opencv-python>=4.5.5,<4.8"
```

仍失败时，查看 pip 实际在拉哪个文件、是否去**源码编译**（会极慢且易失败）：

```bash
pip install -v opencv-python==4.5.5.64 2>&1 | tail -n 40
```

### A3. 仅 SSH、永远 `--no-display`（不需要窗口）

可改用无 GUI 轮子，减轻对 `libGL` 的依赖（**有显示器且要用鼠标画框时不要用这个**）：

```bash
source ~/venv-car/bin/activate
pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless opencv-contrib-python-headless 2>/dev/null || true
pip install "opencv-python-headless>=4.5.5,<4.8"
python3 -c "import cv2; print(cv2.__version__)"
```

### A4. 在 **Windows** 本机装依赖（非 Jetson）

常见是 pip 过旧或走源码编译失败。在项目目录下：

```powershell
python -m pip install -U pip setuptools wheel
pip install -r requirements.txt
```

若提示缺少 **Microsoft Visual C++** 或编译 OpenCV，优先保证装的是 **官方 64 位 Python**，并升级 pip 让 PyPI 提供 **Windows wheel**；仍失败可把完整 `pip install -v ...` 末尾几十行和 `python --version` 一并发出来排查。

### A5. 仍无法解决

请把下面三条命令的**完整输出**（可打码路径）发出来：

```bash
python3 --version
uname -m
source ~/venv-car/bin/activate
pip install -v opencv-python 2>&1 | tail -n 60
```

---

## 五、对照表

| 内容 | 是否在安装脚本内（`install-environment.txt` → `install.d/`） |
|------|-------------------------------------|
| 烧录 SD / 选镜像 | 否 |
| `git clone` / 拷贝仓库 | 否 |
| `nvpmodel`、`jetson_clocks`、swap | 否（文档有指令，见第一节） |
| `apt-get` 安装开发库、ffmpeg、PortAudio | 是 |
| `usermod -aG dialout` | 是（注销重登否） |
| venv、`pip`、`numpy`、Jetson torch wheel | 是 |
| `requirements.txt` / `requirements-voice.txt` | 是 |
| PySOT `build_ext --inplace` | 是 |
| `gdown` 下载默认 `model.pth` | 是（可能失败需手动） |
| wget 解压默认英语 Vosk | 是（可 `SKIP_VOSK_MODEL`；仅计划 **`--stt-mode cloud`** 时可不下） |
| API Key、Ollama 服务、Arduino 固件 | 否 |
| 实际运行 `jetson_follow_track.py` / `voice_agent_car.py` | 否（见第四节） |

更细的 Jetson 说明见 **`JETSON_NANO_SETUP.md`**；语音与 LLM 选项见 **`README.md`**。
