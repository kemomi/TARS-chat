# 摄像头与人脸跟踪

TARS-chat 支持两类摄像头,自动探测:

| 摄像头        | 后端         | 备注                          |
|---------------|--------------|-------------------------------|
| Pi Camera v1/v2/v3, HQ Camera | picamera2 | 走 CSI 排线, 推荐         |
| USB UVC 摄像头 | opencv (V4L2) | 即插即用, 800 多万像素以下都行 |

---

## 1. 硬件准备

### CSI 摄像头(推荐)
- 树莓派 4B 有两个相机接口,接 CAM 那个
- 排线注意金属触点方向:Pi 侧朝 HDMI、摄像头侧朝镜头
- `raspi-config` → Interface Options → Camera 启用 (Bookworm 默认已启)

### USB 摄像头
- 直接插 USB,`ls /dev/video*` 看是否有 `/dev/video0`
- 多个摄像头时改 `config.yaml` 里 `device_index: 1` 之类

### 散热
人脸检测吃 CPU,Pi 4 全速跑约 50% 占用。如果没散热片建议加一个,不然降频之后会卡顿。

---

## 2. 安装依赖

### CSI 摄像头
```bash
sudo apt install -y python3-picamera2 python3-libcamera
```

### USB 摄像头
opencv 在树莓派上**强烈推荐 apt 装**,从 pip 装会编译几个小时:
```bash
sudo apt install -y python3-opencv libatlas-base-dev libjasper-dev
```

然后修改 `firmware/requirements.txt`,把 `opencv-python-headless` 那一行注释掉(避免 pip 重新装一遍冲突)。

测试摄像头能否被读到:
```bash
# CSI:
libcamera-hello -t 2000
# USB:
v4l2-ctl --list-devices
ffplay /dev/video0
```

---

## 3. 启用配置

`firmware/config.yaml`:

```yaml
camera:
  enabled: true            # ← 改这里
  width: 640
  height: 480
  fps: 15
  device_index: 0          # USB 用,CSI 摄像头忽略
  tracking:
    enabled: true          # 加载跟踪模块
    autostart: false       # true = 开机就跟踪 / false = Web 端手动开启
    pan_gain: 0.05         # 左右跟踪强度
    tilt_gain: 0.04        # 上下跟踪强度
    deadzone_pct: 0.08     # 中心 ±8% 不动 (防抖)
    lost_timeout: 1.5      # 失去目标 N 秒后回中
    detect_fps: 10         # 检测帧率
    min_face_size: 60      # 小于此像素的脸不识别
```

重启服务:
```bash
sudo systemctl restart tars-chat
```

---

## 4. 使用

启用后,Web 控制台会多出一个"视觉"卡片:

- **预览**:实时 MJPEG 推流,~15 FPS
- **绿色方框**:检测到人脸 + 跟踪开启
- **橙色方框**:检测到人脸,但跟踪未开
- **状态文字**:`SEARCHING` / `LOCKED` / `TRACKING`
- **人脸跟踪开关**:打开后舵机会自动跟着脸转
- **📷 拍照问**:拍一张照片连同问题一起发给 LLM (需要 vision 模型,如 gpt-4o)

---

## 5. 跟踪算法原理

```
摄像头帧 ──► Haar 级联检测 ──► 取最大人脸框 ──► 计算偏移
                                                  │
                                                  ▼
                          err_x = (face_cx - frame_cx) / (frame_cx)
                                                  │
                                       │err_x│ > deadzone?
                                              │ 否 ──► 不动
                                              │ 是
                                              ▼
                          pan_target = current_pan - err_x × gain × 90°
                                                  │
                                                  ▼
                                            servo.set_pan()
```

**为什么是 P-only 而不是 PID?** 摄像头检测有延迟(~70ms),又有积分项会震荡。比例控制 + 死区已经够稳。

**舵机转反了怎么办?** 把 `pan_gain` 或 `tilt_gain` 改成负数即可。

---

## 6. 视觉问答 (LLM with Vision)

`dialogue.py` 中的 `DialogueOrchestrator.chat()` 会自动检测以下关键词:
- 中文:`看到 / 看看 / 看一下 / 你看 / 前面 / 周围 / 环境 / 现在拍`
- 英文:`what do you see / look at / describe`

匹配时自动拍一张照片附加给 LLM。

**前提**: LLM Provider 需要支持视觉:
- ✅ OpenAI: `gpt-4o`, `gpt-4o-mini`, `gpt-4-vision-preview`
- ✅ Anthropic: `claude-haiku-4-5-20251001`, `claude-sonnet-4-6` (任意 Claude 3+ 都行)
- ❌ Ollama: 默认 `qwen2.5` 不支持,需换 `llava` / `qwen2-vl` 等多模态模型

示例对话:
```
你: "你前面有什么东西?"
TARS: "我看到一台笔记本电脑,屏幕上有一些代码,旁边有一杯咖啡。"  (顺便会点头)
```

---

## 7. 故障排查

### Q1: Web 端"视觉"卡片不显示
- 检查 `config.yaml` 中 `camera.enabled: true`
- 日志看是否报错: `journalctl -u tars-chat -n 50 | grep -i camera`

### Q2: 黑屏 / "无法打开摄像头"
- CSI: `libcamera-hello` 测一下,可能是排线松了
- USB: 检查 `/dev/video0` 是否存在;有时插着插着掉线,拔出来重插

### Q3: 人脸检测一闪一闪
- 光线太暗,Haar 算法在弱光下不稳定
- 把 `min_face_size` 调大到 80~100,过滤误检
- 增加 `min_neighbors` (在 face_tracker.py 里改)

### Q4: 舵机跟着人脸狂抖
- `pan_gain / tilt_gain` 太大,改小到 0.03 试试
- `deadzone_pct` 加大到 0.12
- 或者 `detect_fps` 降到 5(检测慢一点,反应不那么激进)

### Q5: 占 CPU 太高
- 降低 `camera.fps` 到 10
- 降低 `tracking.detect_fps` 到 5
- 降低 `camera.width/height` 到 320×240

### Q6: MJPEG 推流卡顿
- Pi 上同时跑 picamera2 + 推流会吃满网络,改用 320×240
- 或者只在需要看时才打开 Web 端 (推流是按需的)
