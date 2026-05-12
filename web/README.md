
# 表情资源目录

将 PNG 序列帧放到对应子目录:

```
assets/faces/
├── neutral/      # 中性
│   ├── 0001.png
│   └── 0002.png  (可选,多帧自动循环作为眨眼)
├── happy/
├── sad/
├── angry/
├── surprised/
└── sleepy/
```

## 规格要求
- 分辨率: 与 `config.yaml` 中 `display.width × display.height` 一致(默认 320×240)
- 格式: PNG(支持透明背景)
- 文件名: 按 `0001.png`、`0002.png` 顺序命名,固件会自动按字典序循环
- 帧率: 固件默认按 10 FPS 播放

## 找不到资源会怎样?
固件会在屏幕上渲染占位文字(例如 `:: happy ::`),不会崩溃。

## 推荐做法
1. 用 Aseprite / Procreate / Photoshop 画 6 套像素风表情
2. 每套表情 2-4 帧形成"呼吸感"
3. 单帧也可,只是静态显示