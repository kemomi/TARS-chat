# -*- coding: utf-8 -*-
"""
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


def create_app(servo, face, voice, config, dialogue=None):
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
        if not text:
            return jsonify({"ok": False, "error": "empty text"}), 400
        result = dialogue.chat(text)
        # 广播给所有客户端 (多端同步)
        socketio.emit("dialogue_event", {"user": text, "response": result})
        return jsonify({"ok": True, "response": result})

    @app.route("/api/chat/reset", methods=["POST"])
    def api_chat_reset():
        if dialogue:
            dialogue.reset()
        return jsonify({"ok": True})

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