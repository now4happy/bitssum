# 무매 V4.1.1 완전판 — 빗썸 크립토 자동매매봇

별지점 전략 기반 BTC/ETH 자동매매 시스템

## 🆕 V4.1.1 변경사항 (2026-04-27)

- ✅ **FIX: /register 명령어 충돌 해결** ⭐ 중요
- ✅ **CommandHandler 제거, 텍스트 핸들러 통합**
- ✅ **모든 /register 명령어 정상 작동 보장**

## 🐛 V4.1.0에서 발견된 문제

**증상:**
```
/register BTC 115729615 0.00012962 15001
→ 사용법만 출력, 등록 안 됨
```

**원인:**
- CommandHandler가 `/register`를 가로채서 사용법만 출력
- 실제 등록 처리 함수까지 도달 못 함

**해결:**
- CommandHandler 완전 제거
- on_text() 함수에서 통합 처리
- V4.1.1에서 100% 정상 작동

---

## 🌟 주요 기능

### 📊 전략 시스템
- **T값 소수점 계산**: 실제 체결금/예정금으로 정확한 회차 추적
- **일반모드** (전반전/후반전): 별지점 = 평단 기반
- **리버스모드** (소진 이후): 별지점 = 5일 종가 평균
- **쿼터매수/매도**: 1/4 별지점, 3/4 익절선
- **자동 모드 전환**: 일반 ↔ 리버스

### 📱 텔레그램 봇
- `/start` - 봇 정보 & 버전 확인
- `/sync` - 통합 지시서 조회
- `/balance` - 빗썸 잔고 확인
- `/register` - 1차 매수 수동 등록 ✅ 수정됨
- `/seed` - 시드머니 관리
- `/settlement` - 분할수 설정
- `/record` - 거래 장부
- `/history` - 졸업/손절 기록
- `/mode` - 자동매매 ON/OFF

---

## 🚀 빠른 시작

### 1. 서버 준비 (AWS EC2 Ubuntu 22.04)

### 2. Git 클론
```bash
git clone https://github.com/YOUR_USERNAME/mumae-crypto-bot.git
cd mumae-crypto-bot
```

### 3. 환경변수 설정
```bash
cp .env.template .env
nano .env
```

내용 입력:
```env
TELEGRAM_TOKEN=여기에_봇_토큰
CHAT_ID=여기에_채팅ID
BITHUMB_API_KEY=여기에_API키
BITHUMB_SECRET=여기에_시크릿
SEED_BTC=530000
SEED_ETH=530000
```

### 4. 좀비봇 설치 (영구 실행)
```bash
bash install-daemon.sh
```

### 5. 봇 확인
텔레그램에서 `/start` 입력

---

## 🔄 V4.1.0 → V4.1.1 업데이트 방법

### GitHub 사용 시:

```bash
cd mumae-crypto-bot
git pull origin main
bash update.sh
```

### 직접 업로드 시:

```bash
# 기존 봇 중지
sudo systemctl stop mumae-crypto

# 파일 백업
cp bot.py bot.py.backup
cp version.py version.py.backup

# 새 파일 업로드 (bot.py, version.py)

# 재시작
sudo systemctl restart mumae-crypto

# 확인
sudo systemctl status mumae-crypto
```

---

## ✅ V4.1.1 정상 작동 확인

### 텔레그램에서:

```
/register BTC 115729615 0.00012962 15001
```

**정상 응답:**
```
✅ [BTC] 1차 매수 등록 완료! (V4.1.1)
  체결가:  115,729,615원
  수량:    0.000130개
  사용금:  15,001원
  T값:     1.1335
  평단:    115,729,615원
  잔금:    514,999원
  ...
```

**버전 확인:**
```
/start
→ 📌 버전: V4.1.1
```

---

## 📋 파일 구조

```
mumae-crypto-bot/
├── version.py          # V4.1.1 버전 관리
├── bithumb_api.py      # 빗썸 API 래퍼
├── strategy.py         # 무매 V4.1.1 전략 엔진
├── bot.py              # 텔레그램 봇 ✅ /register 수정
├── database.py         # SQLite 장부
├── requirements.txt    # 패키지
├── .env.template       # 환경변수 템플릿
├── setup.sh            # 기본 설치
├── install-daemon.sh   # 좀비봇 설치
├── update.sh           # 업데이트 스크립트
├── monitor.sh          # 모니터링
├── start.sh            # 시작
├── stop.sh             # 중지
├── restart.sh          # 재시작
└── README.md           # 이 문서
```

---

## 🔧 관리 명령어

```bash
# 상태 확인
sudo systemctl status mumae-crypto

# 로그 보기
journalctl -u mumae-crypto -f

# 재시작
sudo systemctl restart mumae-crypto

# 모니터링
bash monitor.sh
```

---

## 📊 전략 상세

### 일반모드
- **전반전** (T < 20): 별% > 0, 익절
  - 매수: 1/2은 별지점, 1/2은 평단
- **후반전** (20 ≤ T < 39): 별% < 0, 손절
  - 매수: 전액 별지점

### 리버스모드 (T ≥ 39)
- **첫날**: 보유/20 MOC 무조건 매도
- **둘째날 이후**:
  - 별지점 = 직전 5일 종가 평균
  - 매수: 잔금/4 (쿼터매수)
  - 매도: 보유/20 (무한매도)

---

## 📜 변경 이력

### V4.1.1 (2026-04-27)
- FIX: /register 명령어 충돌 해결
- CommandHandler 제거, on_text로 통합
- 모든 /register 명령어 정상 작동 보장

### V4.1.0 (2026-04-26)
- 버전 관리 시스템 도입
- /balance 명령어 추가
- 좀비봇 지원
- 시드머니 관리 개선

---

## ⚠️ 주의사항

1. **API 키 보안**: `.env` 파일 절대 공유 금지
2. **시드머니**: 손실 감당 가능한 금액만 투자
3. **1차 매수**: 반드시 `/register`로 수동 등록
4. **분할수 변경**: 진행 중엔 불가능 (졸업 후 가능)

---

## 📞 문의

GitHub Issues 활용

## 📜 라이선스

MIT License

---

**무매 V4.1.1 완전판** — 2026.04.27
