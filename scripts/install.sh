#!/usr/bin/env bash
# =============================================================================
# TARS-chat 一键安装脚本
# 适用: Raspberry Pi OS (Bookworm / Bullseye)
# =============================================================================
set -e

GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
NC="\033[0m"

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERR ]${NC} $1"; exit 1; }

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"
info "工作目录: $REPO_DIR"

# ---- 1. 检查环境 ----
if [[ ! -f /etc/os-release ]] || ! grep -qi "raspbian\|debian" /etc/os-release; then
    warn "未检测到 Raspberry Pi OS / Debian, 脚本可能无法正常工作"
fi

# ---- 2. APT 依赖 ----
info "安装系统依赖..."
sudo apt update
sudo apt install -y \
    python3-pip python3-venv python3-dev \
    pigpio python3-pigpio \
    libsdl2-dev libsdl2-image-dev libsdl2-ttf-dev libsdl2-mixer-dev \
    libportaudio2 portaudio19-dev \
    mpg123 espeak-ng

# ---- 3. 启动 pigpiod ----
info "启动 pigpio 守护进程..."
sudo systemctl enable --now pigpiod

# ---- 4. Python 虚拟环境 ----
info "创建 Python 虚拟环境..."
cd "$REPO_DIR/firmware"
if [[ ! -d venv ]]; then
    python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# ---- 5. 日志目录 ----
info "创建日志文件..."
sudo touch /var/log/tars-chat.log
sudo chown "$USER":"$USER" /var/log/tars-chat.log

# ---- 6. systemd 服务 ----
info "安装 systemd 服务..."
SERVICE_SRC="$REPO_DIR/systemd/tars-chat.service"
SERVICE_DST="/etc/systemd/system/tars-chat.service"
# 替换占位符为实际路径和用户
sudo sed -e "s|__USER__|$USER|g" \
         -e "s|__REPO_DIR__|$REPO_DIR|g" \
         "$SERVICE_SRC" | sudo tee "$SERVICE_DST" > /dev/null

sudo systemctl daemon-reload

# ---- 7. 自检 ----
info "运行硬件自检..."
cd "$REPO_DIR/firmware"
python3 -c "
import sys
try:
    import pigpio
    pi = pigpio.pi()
    if pi.connected:
        print('  ✓ pigpio 连接成功')
        pi.stop()
    else:
        print('  ✗ pigpio 未连接')
        sys.exit(1)
except Exception as e:
    print(f'  ✗ pigpio 测试失败: {e}')
"

# ---- 8. 完成 ----
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  TARS-chat 安装完成!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "启动服务:"
echo "  sudo systemctl enable --now tars-chat"
echo ""
echo "查看日志:"
echo "  journalctl -u tars-chat -f"
echo ""
echo "前台调试 (推荐先用这个):"
echo "  cd firmware && source venv/bin/activate && python main.py"
echo ""
echo "Web 控制台:"
IP=$(hostname -I | awk '{print $1}')
echo "  http://${IP}:8080"
echo ""