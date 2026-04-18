# 基于视觉与语音的人机交互系统（Jetson Nano + Arduino Mega2560）

[English Version](English%20Version.md)

![system picture](https://github.com/lilelife0/an-interactive-system-based-on-voice-and-vision/blob/master/car.jpg)<br><p align="center">
  实物图
</p>

## 0. 背景

麦克纳姆轮小车：**Jetson Nano** 用 **USB 1080p 摄像头** 跑 **PySOT** 跟踪；语音在 Jetson 上使用本仓库 **`voice_agent_car.py`**：**麦克风 → Vosk（默认）或云 STT → 本机 Ollama 或兼容 LLM → espeak（默认）或云 TTS → 音箱**。默认 **不上公网**：**`vosk` + `espeak-ng` + `OPENAI_BASE_URL=http://127.0.0.1:11434/v1`（Ollama）**，`OPENAI_MODEL` 默认 **`qwen2.5`**（请 `ollama pull` 同名模型）。可选 **`--stt-mode cloud` / `VOICE_STT_MODE=cloud`** 等走云端。并解析英文车控词调用 **`comm.py`**。**Arduino Mega2560** 负责电机执行。视觉跟踪使用仓库内 **`pysot-master/`**（与上游 **[STVIR/pysot](https://github.com/STVIR/pysot)** 同源的新版树）；`jetson_follow_track.py` **优先**使用该目录。若旁路另有官方克隆 **`pysot/`**，在无 `pysot-master` 时使用它。

## 1. 硬件

| 部件 | 说明 |
|------|------|
| Jetson Nano（**4GB** 版推荐） | Python、PyTorch、OpenCV、PySOT；内存紧张时请配 **swap**（见 `ENVIRONMENT_SETUP_ORDER.md`） |
| Arduino Mega 2560 | 串口单字节指令，麦克纳姆电机桥 |
| **USB 摄像头（推荐 1080p）** | `jetson_follow_track.py` 默认请求 1920×1080 |
| **麦克风 / 音箱** | 用于 **`voice_agent_car.py`**（英文对话 + 车控） |

串口优先级：`ROBOT_SERIAL_PORT` → `ARDUINO_SERIAL_PORT` → `STM32_SERIAL_PORT`；Linux 默认 `/dev/ttyUSB0`（`ttyACM0` 时请自行 export）。

**环境与兼容性（本仓库主路径）：** **Ubuntu 18.04**（JetPack 4.6.x / L4T R32.x 官方 Nano 镜像常见）、系统 **`python3` 3.6.9**、**64GB microSD**（容量足够；仍建议预留空闲空间）、**aarch64**。语音依赖里 **`httpx`** 版本范围为 **`>=0.21,<0.23`**（0.23 起需 Python ≥3.7）。**2GB Nano** 亦可尝试，但视觉 + 语音同时跑会更吃紧，务必加 swap 并降低分辨率/模型。

## 2. 下位机串口协议（Arduino）

`comm.py` 发送 **1 字节 ASCII**（Mega `Serial.read()` 解析）：

| 字节 | 含义 |
|------|------|
| `F` | 前进 |
| `B` | 后退 |
| `L` | 左转 |
| `R` | 右转 |
| `S` | 停止 |

波特率 **115200**。协议与 `comm.py` 中 `CMD_*` 一致。

## 3. 本仓库脚本

Jetson 环境见 **`JETSON_NANO_SETUP.md`**；视觉跟随见 **`VISUAL_TRACKING_JETSON.md`**。

| 文件 | 作用 |
|------|------|
| `comm.py` | Nano ↔ Arduino，视觉与语音共用 |
| `jetson_follow_track.py` | PySOT + USB 摄像头 + 串口 |
| `voice_agent_car.py` | **英文**：默认 Vosk + espeak + 本机 Ollama；可选云 STT/TTS + 远程 LLM → `comm.py` |
| `integrations/voice_car/commands.py` | 英文短语 → `comm` |

## 4. Jetson 上依赖概要

1. **PyTorch**：Nano 使用 [NVIDIA Jetson wheel](https://developer.nvidia.com/embedded/jetson-linux)。  
2. **PySOT**：在 **`pysot-master/`** 下按 `INSTALL.md` 执行 **`python setup.py build_ext --inplace`**（或由 `bash install-environment.txt` 在 `$PYSOT_ROOT` 上编译）。无自带树时可 `git clone https://github.com/STVIR/pysot.git pysot`。  
3. **权重**：`pysot-master/MODEL_ZOO.md`（与上游 [MODEL_ZOO.md](https://github.com/STVIR/pysot/blob/master/MODEL_ZOO.md) 一致），Nano 建议 MobileNetV2。

**视觉跟踪示例：**

```bash
python3 jetson_follow_track.py --device 0 \
  --snapshot pysot-master/experiments/siamrpn_mobilev2_l234_dwxcorr/model.pth
```

无显示器时加 **`--no-display`** 与 **`--init-bbox`**，见 **`VISUAL_TRACKING_JETSON.md`**。

## 5. 语音：`voice_agent_car.py`

- **默认 LLM 人设**：内置 **英文**「软萌电子宠物」系统提示（温柔、轻声安抚、共情焦虑与疲惫；口头禅风格 *I'm right here with you~* / *Hey, don't worry~*；短句适配 TTS）。可用 **`LLM_SYSTEM_PROMPT`** 整段覆盖为任意语言/人设。  
- **车控**：**英文短语**（`integrations/voice_car/commands.py`），与英文识别常见搭配一致。  
- **默认（无公网语音）**：**`--stt-mode vosk`**（须 **`VOSK_MODEL_PATH` / `--vosk-model`**）、**`--tts-mode espeak`**（须 **`espeak-ng`** + **`ffplay`**）。**`OPENAI_BASE_URL`** 未设置时默认为 **`http://127.0.0.1:11434/v1`**（Ollama）；**`OPENAI_MODEL`** 未设置时默认为 **`qwen2.5`**。  
- **可选云端 STT/TTS**：设 **`VOICE_STT_MODE=cloud`** / **`VOICE_TTS_MODE=cloud`**，并设 **`OPENAI_BASE_URL`** 为提供 **`/v1/audio/transcriptions`** 与 **`/v1/audio/speech`** 的地址，且配置 **`OPENAI_API_KEY`**（或兼容 Key）。麦克风端点可调：**`CLOUD_STT_RMS_THRESHOLD`**、**`CLOUD_STT_SILENCE_SEC`** 等。  
- **espeak 调参**：**`ESPEAK_VOICE`**（如 `en`、`zh`）、**`ESPEAK_SPEED`**（默认 175）。中文请把 **`LLM_SYSTEM_PROMPT`** 写成中文。  
- **依赖**：**`vosk>=0.3.42`**（`requirements-voice.txt`）；**`httpx`** 用于 **`OPENAI_BASE_URL`** 上的 **LLM**（默认本机 Ollama）及可选 **云 STT/TTS**；远程 **https** API 须配有效 Key。

**车控英文短语**（不区分大小写，每句最多执行一条，优先级：停 > 退 > 进 > 左转 > 右转）：

| 意图 | 示例关键词 / 短语 |
|------|-------------------|
| 停止 | stop, halt, brake, hold it, full stop, stay, freeze |
| 后退 | backward, backwards, reverse, go back, go backward, … |
| 前进 | forward, go ahead, go forward, move forward, drive forward |
| 左转 | turn left, left turn, steer left, bear left |
| 右转 | turn right, right turn, steer right, bear right |

```bash
pip install -r requirements.txt -r requirements-voice.txt
sudo apt-get install -y espeak-ng ffmpeg   # 若未装
export VOSK_MODEL_PATH=/path/to/vosk-model-small-en-us-0.15
export ROBOT_SERIAL_PORT=/dev/ttyUSB0
ollama pull qwen2.5
# 默认已是 vosk + espeak + 本机 Ollama，可省略 VOICE_*：
python3 voice_agent_car.py --vosk-model "$VOSK_MODEL_PATH"

# 改用云端 STT+TTS + 远程 LLM 时示例：
# export OPENAI_BASE_URL=https://api.openai.com/v1
# export OPENAI_API_KEY=sk-...
# export OPENAI_MODEL=gpt-4o-mini
# export VOICE_STT_MODE=cloud
# export VOICE_TTS_MODE=cloud
# python3 voice_agent_car.py --stt-mode cloud --tts-mode cloud

```

- **本机 Ollama（LLM）**：安装 [Ollama](https://ollama.com/) 并 **`ollama pull`** 与 **`OPENAI_MODEL`**（默认 **`qwen2.5`**）同名的模型；默认 **`OPENAI_BASE_URL`** 即本机 Ollama 时可**不设** **`OPENAI_API_KEY`**。**注意**：若 **`OPENAI_BASE_URL`** 指向 Ollama，却将 **`VOICE_STT_MODE`/`VOICE_TTS_MODE`** 设为 **`cloud`**，转写/语音请求会发到 Ollama 并失败——用云语音时请把 **`OPENAI_BASE_URL`** 设为真正的云端 API 基址。  
- **通义千问（阿里云 DashScope，OpenAI 兼容）**：控制台申请 **`sk-` API Key**（新用户常有**免费试用额度**，以阿里云/百炼页面为准，非无限免费）。本脚本已支持 **`DASHSCOPE_API_KEY`** 或 **`QWEN_API_KEY`**（与 `OPENAI_API_KEY` 三选一，效果相同）。示例：

```bash
export OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export DASHSCOPE_API_KEY=sk-你的DashScope密钥
export OPENAI_MODEL=qwen-turbo
export VOSK_MODEL_PATH=/path/to/vosk-model-small-en-us-0.15
# 默认仍为 Vosk 本地 STT，须 `--vosk-model`；若网关提供兼容云转写且要用云 STT，请加 `--stt-mode cloud`（并确认 `/v1/audio/transcriptions` 等）。
python3 voice_agent_car.py --vosk-model "$VOSK_MODEL_PATH"
```

  **不要用浏览器去「打开」`OPENAI_BASE_URL` 根路径**：`…/compatible-mode/v1` 是 **API 基址**（程序发 `POST …/chat/completions` 等），**没有**给人看的首页，地址栏访问常会显示「找不到网页」，**属正常现象**。  
  地域 **`BASE_URL`**（与 [阿里云国际站：OpenAI 兼容调用](https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope) 一致，以文档最新为准）：**中国内地（北京）** `https://dashscope.aliyuncs.com/compatible-mode/v1`；**国际（新加坡）** `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`；**美国（弗吉尼亚）** `https://dashscope-us.aliyuncs.com/compatible-mode/v1`；**中国香港** `https://cn-hongkong.dashscope.aliyuncs.com/compatible-mode/v1`。在香港可优先试 **香港** 或 **新加坡** 基址。  
  具体 **`OPENAI_MODEL` 可选名称** 以 [阿里云 Model Studio / 千问文档](https://help.aliyun.com/zh/model-studio/) 当前说明为准。**云转写/云语音**是否可用以该兼容网关实际提供的 API 为准。  

- **仅识别 + 车控、不调 LLM**：`--no-llm`  
- **不播放 TTS**：`--no-tts`  
- 可选 **ffmpeg（ffplay）** 播放 **MP3/WAV**（espeak 合成 WAV、云 TTS 的 MP3）；人设 **`LLM_SYSTEM_PROMPT`** 可整段覆盖；模式 **`--stt-mode` / `--tts-mode`** 与 **`VOICE_*`**、**`ESPEAK_*`**、**`OPENAI_TTS_*`** 见上文。  
- **勿**与 `jetson_follow_track.py` **同时**占用同一串口。

**参考（Nano 上麦克风/扬声器配置）：** [CSDN 文章](https://blog.csdn.net/weixin_42471823/article/details/156427429)（社区笔记，非本仓库源码）。

## 6. 应用设想

* **自动跟随行李箱**：PySOT + 摄像头锁定目标，串口驱动底盘跟随。  
* **家庭护理 / 看护辅助**：视觉关注与移动辅助；需结合实际场景做安全边界与人工监护。  
* **大语言模型即时语音交互**：`voice_agent_car.py` 默认 **英文** 软萌电子宠物 + **Vosk + espeak + 本机 Ollama**；**性格**用 **`LLM_SYSTEM_PROMPT`** 覆盖；改用云端时用 **`VOICE_STT_MODE` / `VOICE_TTS_MODE`** 与 **`OPENAI_BASE_URL`**。

## 7. 其它说明

* **YOLO**：可作首帧检测再接 PySOT；需自行改 `jetson_follow_track.py`。  
* **语音与视觉并行**时避免**多进程同开串口**；可先 **stop** 再独占串口。  
* **安全**：威胁模型与注意事项见 **`SECURITY.md`**。

如有问题欢迎联系原项目作者：lilelife@mail.dlut.edu.cn  
