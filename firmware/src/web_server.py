# -*- coding: utf-8 -*-
"""
# 🌐 Flask + Socket.IO 服务
Web 服务器 (Flask + Socket.IO)
==================================
- HTTP API : /api/face, /api/servo, /api/speak, /api/status
- WebSocket: 用于摇杆实时拖动 (低延迟)
"""
import logging
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO

logger = logging.getLogger("web")

WEB_ROOT = Path(__file__).parent.parent.parent / "web"


def create_app(servo, face, voice, config, dialogue=None,
               camera=None, tracker=None):
    app = Flask(
        __name__,
        static_folder=str(WEB_ROOT),
        static_url_path="",
    )
    CORS(app)
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

    # ---------- 静态页面 ----------
    @app.route("/")
    def index():
        return send_from_directory(str(WEB_ROOT), "web_control.html")

    # ---------- 状态 ----------
    @app.route("/api/status")
    def api_status():
        return jsonify({
            "ok": True,
            "servo": servo.status,
            "face": {
                "current": face.current,
                "available": face.available,
            },
            "voice_enabled": voice is not None,
            "llm_enabled": dialogue is not None and dialogue.available,
            "camera_enabled": camera is not None,
            "camera_backend": camera.backend if camera else None,
            "tracker": tracker.stats if tracker else None,
        })

    # ---------- 表情 ----------
    @app.route("/api/face", methods=["POST"])
    def api_face():
        data = request.get_json(force=True, silent=True) or {}
        emo = data.get("expression", "neutral")
        face.show(emo)
        socketio.emit("face_changed", {"expression": emo})
        return jsonify({"ok": True, "expression": emo})

    # ---------- 舵机 (HTTP, 单次) ----------
    @app.route("/api/servo", methods=["POST"])
    def api_servo():
        data = request.get_json(force=True, silent=True) or {}
        action = data.get("action")
        try:
            if action == "set":
                pan = float(data.get("pan", servo.status["pan"]))
                tilt = float(data.get("tilt", servo.status["tilt"]))
                servo.set_both(pan, tilt)
            elif action == "center":
                servo.center()
            elif action == "nod":
                servo.nod(int(data.get("times", 2)))
            elif action == "shake":
                servo.shake(int(data.get("times", 2)))
            else:
                return jsonify({"ok": False, "error": "unknown action"}), 400
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
        return jsonify({"ok": True, "status": servo.status})

    # ---------- 语音 ----------
    @app.route("/api/speak", methods=["POST"])
    def api_speak():
        if not voice:
            return jsonify({"ok": False, "error": "voice disabled"}), 400
        data = request.get_json(force=True, silent=True) or {}
        text = (data.get("text") or "").strip()
        if not text:
            return jsonify({"ok": False, "error": "empty text"}), 400
        voice.speak(text, blocking=False)
        return jsonify({"ok": True})

    # ---------- LLM 对话 ----------
    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        if not (dialogue and dialogue.available):
            return jsonify({"ok": False, "error": "LLM 未启用,请在 config.yaml 中设置 llm.enabled=true"}), 400
        data = request.get_json(force=True, silent=True) or {}
        text = (data.get("text") or "").strip()
        force_vision = bool(data.get("vision", False))
        if not text:
            return jsonify({"ok": False, "error": "empty text"}), 400
        result = dialogue.chat(text, force_vision=force_vision)
        socketio.emit("dialogue_event", {"user": text, "response": result})
        return jsonify({"ok": True, "response": result})

    @app.route("/api/chat/reset", methods=["POST"])
    def api_chat_reset():
        if dialogue:
            dialogue.reset()
        return jsonify({"ok": True})

    # ---------- 摄像头 ----------
    @app.route("/api/camera/snapshot")
    def api_snapshot():
        if not camera:
            return jsonify({"ok": False, "error": "无摄像头"}), 400
        from flask import Response
        b = camera.jpeg(quality=85)
        if not b:
            return jsonify({"ok": False, "error": "采集失败"}), 500
        return Response(b, mimetype="image/jpeg")

    @app.route("/api/camera/stream")
    def api_stream():
        """MJPEG 推流: multipart/x-mixed-replace"""
        if not camera:
            return jsonify({"ok": False, "error": "无摄像头"}), 400
        from flask import Response
        import time as _time
        try:
            import cv2 as _cv2
        except ImportError:
            _cv2 = None

        def generate():
            boundary = b"--frame"
            while True:
                frame = camera.read()
                if frame is None:
                    _time.sleep(0.05)
                    continue
                # 若开启跟踪, 在帧上画框
                if tracker and _cv2 is not None:
                    box = tracker.last_box
                    if hasattr(tracker, "detector"):
                        tracker.detector.draw(frame, box, tracking=tracker.enabled)
                if _cv2 is None:
                    _time.sleep(0.1); continue
                ok, buf = _cv2.imencode(".jpg", frame, [_cv2.IMWRITE_JPEG_QUALITY, 70])
                if not ok:
                    continue
                yield boundary + b"\r\n" + \
                      b"Content-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
                _time.sleep(1.0 / 15)  # 限制为 15fps
        return Response(generate(),
                        mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.route("/api/tracker", methods=["POST"])
    def api_tracker():
        if not tracker:
            return jsonify({"ok": False, "error": "跟踪器未启用"}), 400
        data = request.get_json(force=True, silent=True) or {}
        if "enabled" in data:
            tracker.enable(bool(data["enabled"]))
        socketio.emit("tracker_changed", tracker.stats)
        return jsonify({"ok": True, "stats": tracker.stats})

    # ---------- WebSocket: 实时摇杆 ----------
    @socketio.on("connect")
    def on_connect():
        logger.info(f"客户端连接: {request.sid}")
        socketio.emit("hello", {"msg": "TARS-chat ready"})

    @socketio.on("disconnect")
    def on_disconnect():
        logger.info(f"客户端断开: {request.sid}")

    @socketio.on("servo_stream")
    def on_servo_stream(data):
        """data = {pan: 0-180, tilt: 0-180}"""
        try:
            pan = float(data.get("pan", 90))
            tilt = float(data.get("tilt", 90))
            servo.set_pan(pan)
            servo.set_tilt(tilt)
        except Exception as e:
            logger.error(f"servo_stream 错误: {e}")

    return app, socketio


def run_server(app, socketio, host: str = "0.0.0.0", port: int = 8080):
    logger.info(f"Web 服务启动: http://{host}:{port}")
    socketio.run(app, host=host, port=port, allow_unsafe_werkzeug=True)
