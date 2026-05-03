#!/bin/bash

# 무매 V5.0 자동 설치 스크립트

echo "=========================================="
echo "무매 V5.0 자동 설치 시작"
echo "=========================================="

# 1. Python 버전 확인
echo "[1/6] Python 버전 확인..."
python3 --version

# 2. 가상환경 생성
echo "[2/6] 가상환경 생성..."
python3 -m venv venv

# 3. 패키지 설치
echo "[3/6] 패키지 설치..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. .env 파일 확인
echo "[4/6] 환경변수 파일 확인..."
if [ ! -f .env ]; then
    echo "⚠️ .env 파일이 없습니다!"
    echo "   cp .env.template .env"
    echo "   nano .env"
    echo "   위 명령어로 환경변수를 설정해주세요."
    exit 1
fi

# 5. 코드 검증
echo "[5/6] 코드 검증..."
python3 -c "from version import VERSION; print(f'버전: V{VERSION}')"

# 6. 완료
echo "[6/6] 설치 완료!"
echo ""
echo "=========================================="
echo "✅ 무매 V5.0 설치 완료!"
echo "=========================================="
echo ""
echo "📌 다음 단계:"
echo "   1. bash install-daemon.sh  (좀비봇 설치)"
echo "   2. 텔레그램에서 /start_auto (첫 매수 & 시작)"
echo ""
