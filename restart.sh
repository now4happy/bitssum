#!/bin/bash
# 무매 V4.1.0 — 봇 재시작
echo "🔄 봇 재시작 중..."
sudo systemctl restart mumae-crypto
sleep 2
sudo systemctl status mumae-crypto --no-pager
echo ""
echo "✅ 봇이 재시작되었습니다!"
