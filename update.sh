#!/bin/bash

# 무매 V4.1.0 — 자동 업데이트 스크립트

echo "🔄 무매 V4.1.0 업데이트 시작..."

# 현재 버전 확인
echo "📌 현재 버전 확인..."
if [ -f "version.py" ]; then
    python3 -c "from version import VERSION; print(f'현재 버전: V{VERSION}')"
fi

# 1. 최신 코드 가져오기
echo "📥 GitHub에서 최신 코드 가져오는 중..."
git pull origin main

# 새 버전 확인
echo "📌 새 버전 확인..."
if [ -f "version.py" ]; then
    python3 -c "from version import VERSION, BUILD_DATE; print(f'업데이트 버전: V{VERSION} (빌드: {BUILD_DATE})')"
fi

# 2. 패키지 업데이트 (변경사항 있을 경우)
echo "📦 패키지 확인 중..."
source venv/bin/activate
pip install -r requirements.txt

# 3. 봇 재시작
echo "🔄 봇 재시작 중..."
sudo systemctl restart mumae-crypto

# 4. 상태 확인
sleep 3
STATUS=$(sudo systemctl is-active mumae-crypto)

if [ "$STATUS" = "active" ]; then
    echo ""
    echo "=========================================="
    echo "✅ 업데이트 완료! 봇이 정상 작동 중입니다."
    echo "=========================================="
    echo ""
    sudo systemctl status mumae-crypto --no-pager
    echo ""
    echo "📌 텔레그램에서 /start를 입력해 버전을 확인하세요!"
else
    echo ""
    echo "=========================================="
    echo "❌ 오류 발생! 로그를 확인하세요:"
    echo "=========================================="
    echo ""
    journalctl -u mumae-crypto -n 50 --no-pager
fi
