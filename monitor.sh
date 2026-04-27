#!/bin/bash

# 무매 V4.1.0 — 봇 모니터링 스크립트

echo "=========================================="
echo "무매 V4.1.0 봇 모니터링"
echo "=========================================="

# 1. 서비스 상태
echo ""
echo "📊 [1/5] 서비스 상태"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
STATUS=$(sudo systemctl is-active mumae-crypto)
if [ "$STATUS" = "active" ]; then
    echo "✅ 상태: 실행 중"
else
    echo "❌ 상태: 중지됨"
fi

ENABLED=$(sudo systemctl is-enabled mumae-crypto)
if [ "$ENABLED" = "enabled" ]; then
    echo "✅ 자동시작: 활성화됨"
else
    echo "⚠️ 자동시작: 비활성화됨"
fi

# 2. 프로세스 정보
echo ""
echo "🔍 [2/5] 프로세스 정보"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
PID=$(pgrep -f "python.*bot.py" | head -1)
if [ -n "$PID" ]; then
    echo "✅ PID: $PID"
    ps -p $PID -o pid,ppid,cmd,%mem,%cpu,etime
else
    echo "❌ 프로세스 없음"
fi

# 3. 재시작 횟수
echo ""
echo "🔄 [3/5] 재시작 이력"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
RESTARTS=$(journalctl -u mumae-crypto --since "24 hours ago" | grep -c "Started Mumae" || echo "0")
echo "📊 최근 24시간 재시작: ${RESTARTS}회"

# 4. 최근 로그 (에러만)
echo ""
echo "⚠️ [4/5] 최근 에러 로그 (최근 10개)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
journalctl -u mumae-crypto --since "1 hour ago" -p err --no-pager | tail -10

# 5. 디스크 & 메모리
echo ""
echo "💾 [5/5] 리소스 사용량"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
df -h / | awk 'NR==2 {print "💿 디스크: " $3 " / " $2 " (" $5 " 사용)"}'
free -h | awk 'NR==2 {print "🧠 메모리: " $3 " / " $2 " 사용"}'

echo ""
echo "=========================================="
echo "✅ 모니터링 완료"
echo "=========================================="
echo ""
echo "📌 실시간 로그 보기:"
echo "   journalctl -u mumae-crypto -f"
echo ""
