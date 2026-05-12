'''
Author: fbee3157 fbee3157@outlook.com
Date: 2026-05-12 16:46:53
LastEditors: fbee3157 fbee3157@outlook.com
LastEditTime: 2026-05-12 16:46:59
FilePath: \TARS-chat\docs\test_servo.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
#!/usr/bin/env python3
"""
舵机自检脚本
独立运行,不依赖 Flask 等组件,用于上电后第一次验证舵机接线
用法:
  cd firmware
  source venv/bin/activate
  python ../scripts/test_servo.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "firmware"))

from firmware.src.servo_controller import ServoController

print("舵机自检开始...")
servo = ServoController(pan_pin=18, tilt_pin=13)

print("1) 回中")
servo.center()
time.sleep(1)

print("2) 左右扫")
for _ in range(2):
    servo.smooth_to(30, 90, duration=0.6)
    servo.smooth_to(150, 90, duration=0.6)
servo.smooth_to(90, 90, duration=0.4)

print("3) 上下扫")
for _ in range(2):
    servo.smooth_to(90, 60, duration=0.5)
    servo.smooth_to(90, 130, duration=0.5)
servo.smooth_to(90, 90, duration=0.4)

print("4) 画圆")
import math
for i in range(36):
    rad = math.radians(i * 10)
    p = 90 + 30 * math.cos(rad)
    t = 90 + 30 * math.sin(rad)
    servo.set_both(p, t)
    time.sleep(0.05)

servo.center()
servo.cleanup()
print("✓ 自检完成")