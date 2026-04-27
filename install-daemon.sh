#!/bin/bash

# 무매 V4.1.0 — 좀비봇 설치 (자동 재시작 데몬)

echo "=========================================="
echo "무매 V4.1.0 좀비봇 설치"
echo "=========================================="

WORK_DIR=$(pwd)
VENV_PYTHON="$WORK_DIR/venv/bin/python"

# 1. 기존 서비스 중지
echo "[1/5] 기존 서비스 중지..."
sudo systemctl stop mumae-crypto 2>/dev/null || true

# 2. 강화된 systemd 서비스 파일 생성
echo "[2/5] 좀비봇 서비스 파일 생성..."
sudo tee /etc/systemd/system/mumae-crypto.service > /dev/null <<EOF
[Unit]
Description=Mumae V4.1.0 Crypto Trading Bot (Zombie Daemon)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$WORK_DIR
ExecStart=$VENV_PYTHON bot.py

# 자동 재시작 설정 (좀비봇 핵심)
Restart=always
RestartSec=10

# 크래시 시 최대 재시작 횟수 (무제한)
StartLimitInterval=0

# 프로세스 우선순위
Nice=-5

# 환경변수
Environment="PYTHONUNBUFFERED=1"

# 로그 설정
StandardOutput=journal
StandardError=journal

# 보안 설정
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# 3. watchdog 타이머 추가 (30분마다 체크)
echo "[3/5] Watchdog 설정..."
sudo tee -a /etc/systemd/system/mumae-crypto.service > /dev/null <<EOF

# Watchdog: 30분마다 봇 생존 확인
WatchdogSec=1800
EOF

# 4. 서비스 등록 및 시작
echo "[4/5] 서비스 활성화..."
sudo systemctl daemon-reload
sudo systemctl enable mumae-crypto
sudo systemctl start mumae-crypto

# 5. 상태 확인
echo "[5/5] 좀비봇 설치 완료! 상태 확인..."
sleep 3
sudo systemctl status mumae-crypto --no-pager

echo ""
echo "=========================================="
echo "✅ 좀비봇 설치 완료!"
echo "=========================================="
echo ""
echo "📌 특징:"
echo "  • 서버 재부팅 시 자동 시작"
echo "  • 크래시 시 10초 후 자동 재시작"
echo "  • 30분마다 생존 확인"
echo "  • 무제한 재시작 (영구 실행)"
echo ""
echo "📌 관리 명령어:"
echo "  sudo systemctl status mumae-crypto     # 상태 확인"
echo "  sudo systemctl restart mumae-crypto    # 재시작"
echo "  sudo systemctl stop mumae-crypto       # 중지"
echo "  journalctl -u mumae-crypto -f          # 실시간 로그"
echo ""
