#!/bin/bash

# 무매 V4.1.0 자동 설치 스크립트

echo "=========================================="
echo "무매 V4.1.0 자동 설치 시작"
echo "=========================================="

# 1. Python 버전 확인
echo "[1/7] Python 버전 확인..."
python3 --version

# 2. 가상환경 생성
echo "[2/7] 가상환경 생성..."
python3 -m venv venv

# 3. 가상환경 활성화 & 패키지 설치
echo "[3/7] 패키지 설치..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. .env 파일 확인
echo "[4/7] 환경변수 파일 확인..."
if [ ! -f .env ]; then
    echo "⚠️ .env 파일이 없습니다!"
    echo "   .env.template을 복사해서 .env로 만들고"
    echo "   필요한 정보를 입력해주세요:"
    echo ""
    echo "   cp .env.template .env"
    echo "   nano .env"
    echo ""
    exit 1
fi

# 5. systemd 서비스 파일 생성
echo "[5/7] systemd 서비스 등록..."
WORK_DIR=$(pwd)
VENV_PYTHON="$WORK_DIR/venv/bin/python"

sudo tee /etc/systemd/system/mumae-crypto.service > /dev/null <<EOF
[Unit]
Description=Mumae V4.1.0 Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$WORK_DIR
ExecStart=$VENV_PYTHON bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 6. 서비스 활성화
echo "[6/7] 서비스 활성화..."
sudo systemctl daemon-reload
sudo systemctl enable mumae-crypto
sudo systemctl start mumae-crypto

# 7. 상태 확인
echo "[7/7] 설치 완료! 상태 확인 중..."
sleep 3
sudo systemctl status mumae-crypto --no-pager

echo ""
echo "=========================================="
echo "✅ 무매 V4.1.0 설치 완료!"
echo "=========================================="
echo ""
echo "📌 다음 명령어로 상태 확인:"
echo "   sudo systemctl status mumae-crypto"
echo ""
echo "📌 실시간 로그 보기:"
echo "   journalctl -u mumae-crypto -f"
echo ""
echo "📌 텔레그램에서 /start 명령어를 입력해보세요!"
echo ""
