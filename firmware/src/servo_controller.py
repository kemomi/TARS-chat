# -*- coding: utf-8 -*-
"""
舵机控制模块 (Pan / Tilt 二自由度云台)
适配 SG90 / MG90S / MG996R 等 PWM 舵机
默认走 pigpio (硬件 PWM,抖动小),fallback 到 RPi.GPIO (软件 PWM)
"""
import logging
import time
import threading

logger = logging.getLogger("servo")

# ---------- 后端探测 ----------
try:
    import pigpio
    _BACKEND = "pigpio"
except ImportError:
    pigpio = None
    try:
        import RPi.GPIO as GPIO
        _BACKEND = "rpigpio"
    except ImportError:
        GPIO = None
        _BACKEND = "mock"
        logger.warning("未检测到 pigpio 或 RPi.GPIO,使用 Mock 后端(开发用)")


class ServoController:
    """
    PWM 舵机控制器
    angle 单位: 度 (0 ~ 180)
    """

    def __init__(self, pan_pin: int, tilt_pin: int,
                 pan_range=(0, 180), tilt_range=(30, 150), freq: int = 50):
        self.pan_pin = pan_pin
        self.tilt_pin = tilt_pin
        self.pan_range = pan_range
        self.tilt_range = tilt_range
        self.freq = freq
        self._lock = threading.Lock()
        self._pan_angle = 90
        self._tilt_angle = 90

        if _BACKEND == "pigpio":
            self.pi = pigpio.pi()
            if not self.pi.connected:
                raise RuntimeError("无法连接 pigpiod, 请执行: sudo systemctl start pigpiod")
            self.pi.set_mode(pan_pin, pigpio.OUTPUT)
            self.pi.set_mode(tilt_pin, pigpio.OUTPUT)
        elif _BACKEND == "rpigpio":
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pan_pin, GPIO.OUT)
            GPIO.setup(tilt_pin, GPIO.OUT)
            self._pan_pwm = GPIO.PWM(pan_pin, freq)
            self._tilt_pwm = GPIO.PWM(tilt_pin, freq)
            self._pan_pwm.start(0)
            self._tilt_pwm.start(0)
        logger.info(f"舵机初始化完成 (backend={_BACKEND}, pan={pan_pin}, tilt={tilt_pin})")

    # ---------- 角度 -> 脉宽 ----------
    @staticmethod
    def _angle_to_pulsewidth(angle: float) -> int:
        """0~180° -> 500~2500 us"""
        angle = max(0, min(180, angle))
        return int(500 + (angle / 180.0) * 2000)

    @staticmethod
    def _angle_to_duty(angle: float) -> float:
        """0~180° -> 2.5%~12.5% duty"""
        return 2.5 + (angle / 180.0) * 10.0

    # ---------- 底层写入 ----------
    def _write(self, pin: int, angle: float):
        if _BACKEND == "pigpio":
            self.pi.set_servo_pulsewidth(pin, self._angle_to_pulsewidth(angle))
        elif _BACKEND == "rpigpio":
            pwm = self._pan_pwm if pin == self.pan_pin else self._tilt_pwm
            pwm.ChangeDutyCycle(self._angle_to_duty(angle))
            time.sleep(0.02)
            pwm.ChangeDutyCycle(0)  # 防抖
        # mock 模式直接 pass

    # ---------- 公共 API ----------
    def set_pan(self, angle: float):
        angle = max(self.pan_range[0], min(self.pan_range[1], angle))
        with self._lock:
            self._pan_angle = angle
            self._write(self.pan_pin, angle)
        logger.debug(f"pan -> {angle}°")

    def set_tilt(self, angle: float):
        angle = max(self.tilt_range[0], min(self.tilt_range[1], angle))
        with self._lock:
            self._tilt_angle = angle
            self._write(self.tilt_pin, angle)
        logger.debug(f"tilt -> {angle}°")

    def set_both(self, pan: float, tilt: float):
        self.set_pan(pan)
        self.set_tilt(tilt)

    def smooth_to(self, pan: float, tilt: float, duration: float = 0.5, steps: int = 20):
        """平滑过渡,避免突然抽动"""
        p0, t0 = self._pan_angle, self._tilt_angle
        for i in range(1, steps + 1):
            ratio = i / steps
            self.set_pan(p0 + (pan - p0) * ratio)
            self.set_tilt(t0 + (tilt - t0) * ratio)
            time.sleep(duration / steps)

    def center(self):
        """回中"""
        self.smooth_to(90, 90, duration=0.4)

    def nod(self, times: int = 2):
        """点头动作"""
        for _ in range(times):
            self.smooth_to(self._pan_angle, 70, duration=0.2)
            self.smooth_to(self._pan_angle, 110, duration=0.2)
        self.smooth_to(self._pan_angle, 90, duration=0.2)

    def shake(self, times: int = 2):
        """摇头动作"""
        for _ in range(times):
            self.smooth_to(70, self._tilt_angle, duration=0.2)
            self.smooth_to(110, self._tilt_angle, duration=0.2)
        self.smooth_to(90, self._tilt_angle, duration=0.2)

    @property
    def status(self) -> dict:
        return {"pan": self._pan_angle, "tilt": self._tilt_angle, "backend": _BACKEND}

    def cleanup(self):
        try:
            if _BACKEND == "pigpio":
                self.pi.set_servo_pulsewidth(self.pan_pin, 0)
                self.pi.set_servo_pulsewidth(self.tilt_pin, 0)
                self.pi.stop()
            elif _BACKEND == "rpigpio":
                self._pan_pwm.stop()
                self._tilt_pwm.stop()
                GPIO.cleanup()
        except Exception as e:
            logger.error(f"清理舵机失败: {e}")