# LLM 对话集成

TARS-chat 支持三种 LLM 后端,在 `firmware/config.yaml` 里改一行即可切换。

## 架构

```
用户输入 ──► /api/chat ──► DialogueOrchestrator
                                   │
                                   ├──► LLM Provider (OpenAI/Anthropic/Ollama)
                                   │         │
                                   │         ▼
                                   │    返回 JSON: {say, expression, motion}
                                   │
                                   ├──► FaceDisplay.show(expression)   # 表情切换
                                   ├──► ServoController.nod()/shake()  # 头部动作
                                   └──► VoiceModule.speak(say)         # TTS 播报
```

三路并发,用户感觉是"机器人一边点头一边说话"。

---

## 方案 A: OpenAI(最快上手)

### 1. 准备 API Key
- 注册 https://platform.openai.com,创建 API key
- 或用任何 OpenAI 兼容服务(DeepSeek、Moonshot、SiliconFlow 等)

### 2. 修改 `firmware/config.yaml`
```yaml
llm:
  enabled: true
  provider: "openai"
  api_key: "sk-xxxxxxxxxxxx"        # 或留空,从环境变量读
  model: "gpt-4o-mini"
  base_url: "https://api.openai.com/v1"
```

### 3. (推荐) 用环境变量保管 Key
不要把 key 提交到 git。改 systemd 服务:

```ini
# /etc/systemd/system/tars-chat.service
[Service]
Environment="OPENAI_API_KEY=sk-xxxxxxxxxxxx"
```

然后 `config.yaml` 里把 `api_key` 留空字符串即可。

### 4. 重启
```bash
sudo systemctl restart tars-chat
```

---

## 方案 B: Anthropic Claude

```yaml
llm:
  enabled: true
  provider: "anthropic"
  api_key: ""                                  # 留空读 ANTHROPIC_API_KEY
  model: "claude-haiku-4-5-20251001"           # 性价比之选;或 claude-sonnet-4-6
```

---

## 方案 C: Ollama 本地(无需联网)

### 1. 安装 Ollama

**在树莓派上跑(性能有限,适合 0.5B-3B 小模型)**:
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:0.5b      # 0.5B 模型, Pi4 上勉强能用
# 或
ollama pull qwen2.5:3b        # 3B, 推荐 Pi5 或外置服务器
```

**外接电脑/服务器上跑(推荐)**:
让 Ollama 监听局域网:
```bash
# 编辑 /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl edit ollama
```
添加:
```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```
然后:
```bash
sudo systemctl restart ollama
```

### 2. 配置 TARS-chat
```yaml
llm:
  enabled: true
  provider: "ollama"
  model: "qwen2.5:3b"
  base_url: "http://localhost:11434"           # 远程改成: http://192.168.x.x:11434
```

### 3. 推荐模型(中文)
| 模型              | 体积   | 适合设备           | 备注                |
|-------------------|--------|--------------------|---------------------|
| `qwen2.5:0.5b`    | ~400MB | 树莓派 4B          | 慢但能跑            |
| `qwen2.5:3b`      | ~1.9GB | 树莓派 5 / Mac/PC  | 推荐起步            |
| `qwen2.5:7b`      | ~4.4GB | 外置服务器         | 效果接近 GPT-3.5    |
| `llama3.2:3b`     | ~2GB   | Mac/PC             | 英文为主            |

---

## 自定义性格(System Prompt)

在 `config.yaml` 的 `llm.system_prompt` 字段改:

```yaml
llm:
  system_prompt: |
    你是 TARS-chat,一只懒洋洋的猫型机器人。说话总带"喵"。
    回答时必须输出 JSON,不要任何代码块标记:
    {
      "say": "回答(简短,30字内)",
      "expression": "happy | sad | angry | surprised | sleepy | neutral",
      "motion": "nod | shake | center | none"
    }
```

**重点**: 一定要保留 JSON 输出格式说明,否则编排器无法解析。

---

## API 端点

### `POST /api/chat`
```json
// 请求
{ "text": "今天北京天气怎么样" }

// 响应
{
  "ok": true,
  "response": {
    "say": "我没法上网查天气哦,你可以打开窗看看~",
    "expression": "neutral",
    "motion": "shake"
  }
}
```

### `POST /api/chat/reset`
清空对话历史,机器人忘记之前聊过的内容。
```json
{}
```

---

## 故障排查

### Q1: Web 控制台一直显示"LLM 未启用"?
- 检查 `config.yaml` 中 `llm.enabled: true`
- 重启服务 `sudo systemctl restart tars-chat`
- 看日志 `journalctl -u tars-chat -n 50`

### Q2: 输入消息后一直显示"思考中..."不出来?
- OpenAI: 检查 key 是否有余额,网络是否能访问 api.openai.com
- Ollama: `curl http://localhost:11434/api/tags` 看模型是否加载
- 看后端日志看具体错误

### Q3: 机器人输出乱七八糟不是 JSON?
- 小模型(0.5B/1B)经常不遵守 JSON 输出格式
- 编排器有 fallback,会把整段当作 say,只是没有动作和表情
- 解决: 换大一点的模型,或在 prompt 里加更强约束

### Q4: 想让机器人主动开口(不等用户输入)?
- 在 `dialogue.py` 加个定时器,周期性调用 `dialogue.chat("说点什么")`
- 或加一个 "wakeword" 模块(需要 STT)

### Q5: 想流式输出(边说边动)?
- 当前是一句一句来的,LLM 全部生成完才执行动作
- 流式输出需要改 `LLMProvider._chat` 返回迭代器,然后 `DialogueOrchestrator` 做缓冲分句
- 这是下一步可以做的优化,先把基础链路跑通
