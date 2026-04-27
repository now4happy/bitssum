#!/bin/bash
# 무매 V4.1.0 — 봇 시작
echo "🚀 봇 시작 중..."
sudo systemctl start mumae-crypto
sleep 2
sudo systemctl status mumae-crypto --no-pager
echo ""
echo "✅ 봇이 시작되었습니다!"
echo "📊 실시간 로그: journalctl -u mumae-crypto -f"
