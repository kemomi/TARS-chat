
# TARS-chat

[![Build TARS-chat Firmware](https://github.com/kemomi/TARS-chat/actions/workflows/build.yml/badge.svg)](https://github.com/kemomi/TARS-chat/actions/workflows/build.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Join_Server-5865F2?logo=discord&logoColor=white)](https://discord.gg/eGhd9adnBm)

> A super cute mini desktop robot powered by **Python** and embedded with **Raspberry Pi 4B**.
> Displays expressions, rotates its head, chats, and is remotely controlled via手机/browser.

![TARSchat](./docs/images/TARS.gif)

---

## ✨ Features

- 😄 **Rich Expressions**: Neutral / Happy / Sad / Angry / Surprised / Sleepy. Supports custom PNG frame sequences.
- 🎮 **Remote Joystick**: Real-time control of the Pan/Tilt 2-DOF gimbal via web drag (Low-latency WebSocket).
- 🗣️ **Voice Chat**: Built-in TTS (Offline pyttsx3 / Online edge-tts). STT is extensible.
- 🧠 **LLM Brain**: Supports OpenAI / Anthropic / Local Ollama. Automatically links expressions and movements during conversation.
- 👁️ **Visual Tracking**: Camera face detection + Servo auto-tracking + Visual Q&A ("What do you see?").
- 🌐 **Cross-platform Control**: Accessible via any browser or mobile phone, no App installation required.
- 🔧 **Modular Design**: Decoupled servo, display, Web, voice, LLM, and vision modules for easy二次开发.
- 📦 **One-click Deployment**: Fully automated installation with `bash scripts/install.sh`.

## 🗂 Repository Structure

```bash
TARS-chat/
├── firmware/          # Raspberry Pi Firmware (Python)
│   ├── main.py        # Entry point
│   ├── src/           # Core modules
│   ├── config.yaml    # Configuration file
│   ├── assets/faces/  # Expression resources (PNG sequences)
│   └── requirements.txt
├── web/               # Web Console (HTML + Socket.IO)
├── schematics/        # Circuit wiring and schematics
├── stls/              # 3D Printing STL files list
├── case/              # Enclosure design source files
├── scripts/           # Installation/testing scripts
├── systemd/           #开机自启 services
├── docs/              # Documentation and images
```

## 🚀 Quick Start

### Hardware Preparation
1. Check [`schematics/README.md`](./schematics/README.md) for the Bill of Materials (BOM) and wiring instructions.
2. Check [`stls/README.md`](./stls/README.md) to print the 3D structural components.
3. Assemble the robot.

### Flashing the Firmware
```bash
git clone https://github.com/kemomi/TARS-chat.git
cd TARS-chat
bash scripts/install.sh
```

Refer to [`firmware/README.md`](./firmware/README.md) for detailed steps.

### Getting Started
```bash
sudo systemctl enable --now tars-chat
```
Open your browser and navigate to `http://<Raspberry_Pi_IP>:8080` to access the control console.

## 🛠 Development Workflow

```bash
cd firmware
source venv/bin/activate
python ../scripts/test_servo.py   # Servo self-check
python main.py                    # Foreground debugging
```

After modifying any files under `src/`:
```bash
sudo systemctl restart tars-chat
```

## 📡 Communication Protocol

| Type      | Path                     | Description                                      |
|-----------|--------------------------|--------------------------------------------------|
| HTTP POST | `/api/face`              | `{expression:"happy"}`                           |
| HTTP POST | `/api/servo`             | `{action:"set",pan:90,tilt:80}` or `nod`/`shake`/`center` |
| HTTP POST | `/api/speak`             | `{text:"Hello"}`                                 |
| HTTP POST | `/api/chat`              | `{text:"...", vision: false}` — LLM Chat         |
| HTTP POST | `/api/chat/reset`        | Clear chat history                               |
| HTTP POST | `/api/tracker`           | `{enabled: true/false}` Face tracking toggle     |
| HTTP GET  | `/api/camera/snapshot`   | Take a JPEG snapshot                             |
| HTTP GET  | `/api/camera/stream`     | MJPEG stream                                     |
| HTTP GET  | `/api/status`            | Query current status                             |
| WebSocket | `servo_stream`           | Real-time joystick stream (Low latency)          |
| WebSocket | `dialogue_event`         | Multi-terminal chat synchronization              |
| WebSocket | `tracker_changed`        | Tracking status broadcast                        |

See [`docs/API.md`](./docs/API.md) for detailed fields.
For LLM integration, see [`docs/LLM.md`](./docs/LLM.md). For camera and visual Q&A, see [`docs/CAMERA.md`](./docs/CAMERA.md).

## 🗺 Roadmap

See [`docs/ROADMAP.md`](./docs/ROADMAP.md).

## 🤝 Contributing

Welcome to submit Issues and PRs! See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for how to participate.

## 📄 License

[Apache 2.0](./LICENSE)
```

---

