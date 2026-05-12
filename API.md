# API 参考

固件提供两套通信接口:**HTTP REST** 用于命令式控制,**WebSocket (Socket.IO)** 用于实时数据流。

Base URL: `http://<树莓派IP>:8080`

---

## HTTP REST API

### `GET /api/status`
查询当前所有状态。

**响应**
```json
{
  "ok": true,
  "servo": {"pan": 90, "tilt": 90, "backend": "pigpio"},
  "face": {
    "current": "neutral",
    "available": ["neutral", "happy", "sad", "angry", "surprised", "sleepy"]
  },
  "voice_enabled": false
}
```

### `POST /api/face`
切换表情。

**请求**
```json
{ "expression": "happy" }
```

**响应**
```json
{ "ok": true, "expression": "happy" }
```

### `POST /api/servo`
舵机控制。

**请求(set)**
```json
{ "action": "set", "pan": 120, "tilt": 80 }
```

**请求(其他动作)**
```json
{ "action": "center" }      // 回中
{ "action": "nod", "times": 2 }    // 点头
{ "action": "shake", "times": 3 }  // 摇头
```

**响应**
```json
{ "ok": true, "status": {"pan": 120, "tilt": 80, "backend": "pigpio"} }
```

### `POST /api/speak`
TTS 播报(需启用 voice)。

**请求**
```json
{ "text": "你好,我是 TARS。" }
```

### `POST /api/chat`
LLM 对话(需启用 llm,详见 [`LLM.md`](./LLM.md))。机器人会自动联动表情、动作和 TTS。

**请求**
```json
{ "text": "今天北京天气怎么样" }
```

**响应**
```json
{
  "ok": true,
  "response": {
    "say": "我没法查天气,你打开窗看看吧",
    "expression": "neutral",
    "motion": "shake"
  }
}
```

### `POST /api/chat/reset`
清空对话上下文,机器人会"忘记"之前的内容。
```json
{ "ok": true }
```

---

## WebSocket (Socket.IO)

### 客户端 → 服务端

#### `servo_stream`
摇杆实时推流,建议节流到 20~50ms 一次。

```js
socket.emit("servo_stream", { pan: 110, tilt: 95 });
```

### 服务端 → 客户端

#### `hello`
连接建立时推送。
```json
{ "msg": "TARS-chat ready" }
```

#### `face_changed`
任意端切换表情后广播,用于多端同步。
```json
{ "expression": "sad" }
```

#### `dialogue_event`
任意端发起 LLM 对话后广播。
```json
{
  "user": "你好",
  "response": {"say":"嗨!","expression":"happy","motion":"nod"}
}
```

---

## 第三方调用示例

### curl
```bash
curl -X POST http://192.168.1.10:8080/api/face \
     -H "Content-Type: application/json" \
     -d '{"expression":"happy"}'
```

### Python
```python
import requests
requests.post("http://192.168.1.10:8080/api/servo",
              json={"action": "set", "pan": 60, "tilt": 90})
```

### Home Assistant (REST command)
```yaml
rest_command:
  tars_happy:
    url: "http://192.168.1.10:8080/api/face"
    method: POST
    headers: { Content-Type: "application/json" }
    payload: '{"expression":"happy"}'
```