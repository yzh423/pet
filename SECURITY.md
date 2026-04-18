# 安全说明（Security）

本文档概括本仓库**自有脚本**（`jetson_follow_track.py`、`voice_agent_car.py`、`comm.py`、`integrations/voice_car/`）的主要风险与缓解；**第三方 PySOT 目录 `pysot-master/`（与 [STVIR/pysot](https://github.com/STVIR/pysot) 同源）或旁路 `pysot/`** 未做完整审计，训练/评测脚本不在默认运行路径内。

---

## 1. 已加固项（代码层面）

| 风险 | 说明 | 缓解 |
|------|------|------|
| **恶意 `model.pth`（PyTorch pickle）** | `torch.load` 默认可执行任意 pickle，不可信权重可导致 RCE。 | `jetson_follow_track.py` 在支持 **`weights_only=True`** 的 PyTorch 上优先使用该参数；旧版无此参数时回退为传统 `torch.load`。**仍只应加载你信任的权重文件。** |
| **`OPENAI_BASE_URL` 指向恶意站点** | 若环境变量被篡改，API Key 可能随请求发往攻击者。 | `voice_agent_car.py` 校验：仅允许 **`https://`**；**`http://`** 仅允许 **`localhost` / `127.0.0.1` / `::1`**（本机 Ollama）。 |
| **超长 TTS 文本** | LLM 异常输出可导致过大请求或播放卡顿。 | `speak_espeak` / 云 TTS 路径对文本做 **4000 字符** 截断。 |

---

## 2. 仍需自行注意的风险

### 2.1 物理与串口（`comm.py`）

- 串口无认证；任何能改 **`ROBOT_SERIAL_PORT`** 或 **`--serial-port`** 的进程可向底盘发 **`F/B/L/R/S`**。  
- **勿**把串口设备权限暴露给不可信用户；生产环境建议专用 Unix 用户、最小权限。

### 2.2 语音链路（`voice_agent_car.py`）

- **API Key** 经环境变量传入，进程内可见；共享机器上注意 `ps` / `/proc` 与日志勿打印 Key。  
- **提示词注入（Prompt injection）**：用户语音经 **Vosk 或云 STT** 转写后进入 LLM，恶意话术可能诱导模型偏离车控或泄露系统提示；**无硬防**，依赖模型与系统提示设计。  
- **隐私**：默认 **Vosk** 在本地转写；若使用 **`VOICE_STT_MODE=cloud`**，麦克风 **WAV** 会上传到 **`OPENAI_BASE_URL`** 的转写接口。LLM 与 **云 TTS** 请求内容发往所选 API；**espeak** 为本地合成（仍注意麦克风与日志）。  
- **本机 Ollama 若监听 `0.0.0.0`**：注意局域网访问面；脚本仅允许本机 loopback 的 **http**。

### 2.3 视觉脚本（`jetson_follow_track.py`）

- **`--config` YAML**：若来源不可信，理论上存在解析风险；请只用仓库内或你自行校验的配置。  
- **摄像头索引 `--device`**：错误设备号仅影响采集，一般不构成跨权限读。  
- **无网络服务**：默认不监听端口，攻击面主要在本地进程与串口。

### 2.4 依赖与供应链

- **`pip install`** 的包与 **`pysot-master/`** 上游代码需自行信任；建议在隔离环境构建并在 Jetson 上固定版本。  
- 定期关注 **PyTorch / OpenCV / httpx** 等 CVE 通告。

---

## 3. 报告漏洞

若你认为发现可利用的安全问题，请通过项目 README 中的作者邮箱**私下**说明复现步骤与影响范围（勿在公开 issue 中粘贴 API Key）。

---

*最后更新：与仓库内 `jetson_follow_track.py`、`voice_agent_car.py` 的校验逻辑一致；若行为与本文冲突以代码为准。*
