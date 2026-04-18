# An Interactive System Based on Voice and Vision

![system picture](https://github.com/lilelife0/an-interactive-system-based-on-voice-and-vision/blob/master/car.jpg)<br><p align="center">
  the car itself
</p>

## 0. Background

Undergraduate innovation project: a small Mecanum vehicle. **Jetson Nano** runs **PySOT** tracking from a **USB 1080p webcam** and optional voice via **`voice_agent_car.py`**: **mic → Vosk or cloud STT → OpenAI-compatible LLM (default local Ollama) → espeak or cloud TTS → speaker** (defaults **Vosk + espeak + Ollama** on `127.0.0.1:11434`, no public cloud for STT/TTS; **cloud** modes optional), plus **English drive phrases** → **`comm.py`** → **Arduino Mega 2560**. Default LLM persona is an **English** soft “digital pet” (override with `LLM_SYSTEM_PROMPT`). **Local TTS** uses **espeak-ng** (system package).

**PySOT (tracking):** bundled `pysot-master/` (same lineage as [STVIR/pysot](https://github.com/STVIR/pysot)); optional extra clone in `pysot/`.

## 1. Components

* **Compute / MCU:** Jetson Nano, Arduino Mega 2560  
* **Sensors / I/O:** USB HD webcam, microphone, speaker  

## 2. Repository layout

| Path | Role |
|:-----|:-----|
| `comm.py` | UART: `F` forward, `B` backward, `L` / `R` turn, `S` stop. Env: `ROBOT_SERIAL_PORT`, etc.; default Linux `/dev/ttyUSB0`. |
| `jetson_follow_track.py` | PySOT follow + USB webcam + serial. |
| `voice_agent_car.py` | **English** pipeline: Vosk/cloud STT + LLM + espeak/cloud TTS + drive commands → `comm.py`. |
| `integrations/voice_car/commands.py` | English phrases → `comm`. |
| `pysot-master/` | [STVIR/pysot](https://github.com/STVIR/pysot)-line tree; build + NVIDIA PyTorch on Jetson (`pysot/` used if master absent). |
| `requirements.txt` | Base pip deps. |
| `requirements-voice.txt` | sounddevice, httpx; optional Vosk for local STT; espeak-ng via apt for local TTS. |

## 3. Third-party libraries

| Topic | Link |
|:------|:-----|
| Tracking | [pysot](https://github.com/STVIR/pysot) |
| ASR | [Vosk](https://alphacephei.com/vosk/) |
| TTS (offline) | [eSpeak NG](https://github.com/espeak-ng/espeak-ng) |

## 4. Algorithms (this repo)

* **Follow:** PySOT bbox center vs. image center → steer toward target; MobileNetV2 recommended on Nano.  
* **Voice:** transcript (Vosk or cloud) → keyword car control + parallel LLM reply → TTS playback (espeak or cloud).  

**Community note (Nano audio hardware):** [CSDN article](https://blog.csdn.net/weixin_42471823/article/details/156427429) — not part of this repo.

## 5. Quick start

**Vision**

1. Install Jetson PyTorch + build `pysot-master` (`python setup.py build_ext --inplace`); download `model.pth` from `MODEL_ZOO.md`.  
2. `pip install -r requirements.txt`  
3. `python3 jetson_follow_track.py --device 0 --snapshot pysot-master/experiments/siamrpn_mobilev2_l234_dwxcorr/model.pth`  

**Voice (English)** — default path is **local-first** (no public cloud for STT/TTS)

1. `pip install -r requirements.txt -r requirements-voice.txt`  
2. Install **Vosk** model path, **`espeak-ng`**, and **`ffmpeg`** (`ffplay`).  
3. `ollama pull qwen2.5` (or match `OPENAI_MODEL`; default base is `http://127.0.0.1:11434/v1`).  
4. `export ROBOT_SERIAL_PORT=/dev/ttyUSB0` and `export VOSK_MODEL_PATH=…`  
5. `python3 voice_agent_car.py --vosk-model "$VOSK_MODEL_PATH"`  

**Optional cloud STT/TTS + remote LLM:** set `OPENAI_BASE_URL` (e.g. `https://api.openai.com/v1`), `OPENAI_API_KEY`, and `VOICE_STT_MODE=cloud` / `VOICE_TTS_MODE=cloud`; the base must expose **`/v1/audio/transcriptions`** and **`/v1/audio/speech`** for those modes. **One `OPENAI_BASE_URL` is used for LLM + cloud STT + cloud TTS**—do not point it at Ollama while `VOICE_STT_MODE`/`VOICE_TTS_MODE` stay `cloud`. Optional `ESPEAK_VOICE` / `ESPEAK_SPEED` for local TTS.

Use `--no-llm` for STT + car only; `--no-tts` to skip playback. Install **ffmpeg** (`ffplay`) for reliable playback. Do **not** share the serial port with `jetson_follow_track.py` at the same time.

**Alibaba Tongyi Qwen (DashScope, OpenAI-compatible):** set `OPENAI_BASE_URL` to a regional **API base** (not a website you open in a browser—the root URL has no HTML page, so the browser may show “page not found”; that is normal). Examples from [Alibaba Cloud Model Studio docs](https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope): **China (Beijing)** `https://dashscope.aliyuncs.com/compatible-mode/v1`; **International (Singapore)** `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`; **US (Virginia)** `https://dashscope-us.aliyuncs.com/compatible-mode/v1`; **Hong Kong (China)** `https://cn-hongkong.dashscope.aliyuncs.com/compatible-mode/v1`. Then set **`DASHSCOPE_API_KEY`** or **`QWEN_API_KEY`** (or `OPENAI_API_KEY`) to your `sk-…` key, and `OPENAI_MODEL` per current docs. New accounts often get **free trial credits** (not unlimited). **Whether DashScope implements the same audio endpoints as OpenAI** varies by product—check current docs. **Fully offline LLM + voice:** Ollama + local base URL **only** when STT/TTS are local (`vosk` + `espeak`); see README default / local stack.

## 6. Applications

* **Auto-following luggage** — PySOT + webcam target lock, UART drive base.  
* **Home care / monitoring assistance** — visual attention and mobility aid; always add safety limits and human supervision for real deployments.  
* **Real-time LLM voice chat** — `voice_agent_car.py` for low-latency spoken dialogue; **adjustable persona / tone** via **`LLM_SYSTEM_PROMPT`**; **`VOICE_STT_MODE` / `VOICE_TTS_MODE`** and **`ESPEAK_*`** tune how speech is recognized and played back.

---

Email: lilelife@mail.dlut.edu.cn
