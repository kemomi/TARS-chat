
# TARS-chat 项目架构

## 一、目录结构

```
TARS-chat/
├── firmware/                      # 🎯 核心固件 (运行在树莓派)
│   ├── main.py                    # 启动入口,按序初始化各模块
│   ├── config.yaml                # 全局配置 (所有功能开关都在这)
│   ├── requirements.txt           # Python 依赖
│   ├── README.md                  # 固件安装指南
│   ├── assets/faces/              # 表情 PNG 帧序列
│   │   └── README.md
│   └── src/                       # 模块化代码
│       ├── __init__.py
│       ├── servo_controller.py    # 🦾 舵机控制 (Pan/Tilt 云台)
│       ├── face_display.py        # 😊 表情显示 (Pygame 渲染)
│       ├── voice_module.py        # 🗣️ TTS 语音播报
│       ├── camera_module.py       # 📷 摄像头采集
│       ├── face_tracker.py        # 👁️ 人脸检测 + 跟踪
│       ├── llm_provider.py        # 🧠 LLM 抽象层 (OpenAI/Anthropic/Ollama)
│       ├── dialogue.py            # 🎭 对话编排器 (整合 LLM/动作/语音/视觉)
│       └── web_server.py          # 🌐 Flask + Socket.IO 服务
│
├── web/                           # 🌐 Web 控制台 (前端)
│   └── web_control.html           # 单页应用 (表情/摇杆/对话/摄像头)
│
├── docs/                          # 📚 文档
│   ├── API.md                     # HTTP/WebSocket 接口
│   ├── LLM.md                     # 三种 LLM 后端接入指南
│   ├── CAMERA.md                  # 摄像头与视觉问答指南
│   └── ROADMAP.md                 # 版本规划
│
├── schematics/                    # ⚡ 电路设计
│   └── README.md                  # BOM + 接线表 + ASCII 接线图
│
├── stls/                          # 🖨️ 3D 打印件
│   └── README.md                  # 结构件清单 + 打印参数
│
├── case/                          # 📦 外壳源文件
│   └── README.md
│
├── scripts/                       # 🔧 工具脚本
│   ├── install.sh                 # 一键安装 (apt + pip + systemd)
│   └── test_servo.py              # 舵机自检
│
├── systemd/                       # 🚀 开机自启
│   └── tars-chat.service          # systemd unit
│
├── .github/workflows/
│   └── build.yml                  # CI: 语法检查 + 导入冒烟测试
│
├── README.md                      # 项目主页
├── CONTRIBUTING.md
├── LICENSE                        # Apache 2.0
└── .gitignore
```

## 二、分层架构

整个系统分四层,自顶向下:

![alt text](tars_chat_architecture-1.svg)
