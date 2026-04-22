#!/bin/bash
# ================================================
# 무매 크립토 봇 - 서버 자동 설치 스크립트
# AWS EC2 Ubuntu 22.04 기준
# 사용법: bash setup.sh
# ================================================

echo "======================================"
echo "  무매 크립토 봇 설치 시작"
echo "======================================"

# 1. 시스템 업데이트
echo "[1/6] 시스템 업데이트 중..."
sudo apt update -y && sudo apt upgrade -y

# 2. Python 및 pip 설치
echo "[2/6] Python 환경 설치 중..."
sudo apt install -y python3 python3-pip python3-venv git

# 3. 가상환경 생성
echo "[3/6] 가상환경 생성 중..."
python3 -m venv venv
source venv/bin/activate

# 4. 패키지 설치
echo "[4/6] 패키지 설치 중..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. .env 파일 확인
echo "[5/6] 환경변수 확인..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env 파일이 없습니다!"
    echo "    .env.template 을 참고해서 .env 파일을 만들어주세요."
    echo "    명령어: cp .env.template .env && nano .env"
    exit 1
else
    echo "✅ .env 파일 확인 완료"
fi

# 6. systemd 서비스 등록 (재부팅 시 자동 시작)
echo "[6/6] 서비스 등록 중..."

WORK_DIR=$(pwd)
USER_NAME=$(whoami)
PYTHON_PATH="$WORK_DIR/venv/bin/python"

sudo bash -c "cat > /etc/systemd/system/mumae-crypto.service << EOF
[Unit]
Description=Mumae Crypto Trading Bot
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=$WORK_DIR
ExecStart=$PYTHON_PATH bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable mumae-crypto
sudo systemctl start mumae-crypto

echo ""
echo "======================================"
echo "  ✅ 설치 완료!"
echo "======================================"
echo ""
echo "📌 유용한 명령어:"
echo "  봇 상태 확인:  sudo systemctl status mumae-crypto"
echo "  봇 로그 보기:  journalctl -u mumae-crypto -f"
echo "  봇 재시작:     sudo systemctl restart mumae-crypto"
echo "  봇 중지:       sudo systemctl stop mumae-crypto"
echo ""
echo "텔레그램에서 /start 를 입력해보세요! 🚀"
