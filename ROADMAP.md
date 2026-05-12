# 路线图

## v0.1 (MVP) ✅
- [x] Pan/Tilt 舵机基础控制
- [x] 6 种表情显示
- [x] Web 控制台 (HTTP + WebSocket)
- [x] systemd 开机自启

## v0.2 ✅
- [x] LLM 集成:接入 OpenAI / Anthropic / 本地 Ollama
- [x] 对话联动:LLM 输出自动驱动表情 + 动作 + TTS
- [x] Web 端聊天界面 + 多端同步

## v0.3 (规划中)
- [ ] 摄像头模块:人脸跟踪、视觉问答 (LLM with vision)
- [ ] LLM 流式输出:边说边动,降低首字延迟
- [ ] 触摸交互:头顶触摸传感器(电容式)
- [ ] OTA 升级:Web 端一键更新固件
- [ ] STT:Whisper / Vosk 让机器人能听

## v1.0
- [ ] 完整的角色性格系统(JSON 配置)
- [ ] 第三方插件 API
- [ ] HomeAssistant / Matter 接入
- [ ] 移动 App (React Native)
- [ ] 多机器人组网(MQTT broker)
- [ ] M5Stack 版本固件分支