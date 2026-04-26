# 무매 V4.1.0 완전판 — 빗썸 크립토 자동매매봇

별지점 전략 기반 BTC/ETH 자동매매 시스템

## 🆕 V4.1.0 변경사항

- ✅ **버전 번호 시스템** 도입 (V4.1.0)
- ✅ **/balance 명령어** 추가 (빗썸 잔고 자동 체크)
- ✅ **시드머니 관리 개선** (증감 버튼)
- ✅ **버전 충돌 방지** (모든 파일에 버전 명시)
- ✅ **모든 응답에 버전 표시**

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
- `/balance` - 빗썸 잔고 확인 ⭐ 신규
- `/register` - 1차 매수 수동 등록
- `/seed` - 시드머니 관리
- `/settlement` - 분할수 설정
- `/record` - 거래 장부
- `/history` - 졸업/손절 기록
- `/mode` - 자동매매 ON/OFF

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

### 4. 자동 설치
```bash
bash setup.sh
```

### 5. 봇 확인
텔레그램에서 `/start` 입력

## 🔄 업데이트 방법

```bash
cd mumae-crypto-bot
bash update.sh
```

자동으로:
1. 최신 코드 pull
2. 패키지 업데이트
3. 봇 재시작
4. 버전 확인

## 📋 파일 구조

```
mumae-crypto-bot/
├── version.py          # 버전 관리 ⭐ 신규
├── bithumb_api.py      # 빗썸 API 래퍼
├── strategy.py         # 무매 V4.1.0 전략 엔진
├── bot.py              # 텔레그램 봇
├── database.py         # SQLite 장부
├── requirements.txt    # 패키지
├── .env.template       # 환경변수 템플릿
├── setup.sh            # 자동 설치 스크립트
├── update.sh           # 업데이트 스크립트
└── README.md           # 이 문서
```

## 🔧 관리 명령어

```bash
# 상태 확인
sudo systemctl status mumae-crypto

# 로그 보기
journalctl -u mumae-crypto -f

# 재시작
sudo systemctl restart mumae-crypto

# 중지
sudo systemctl stop mumae-crypto

# 시작
sudo systemctl start mumae-crypto
```

## 📊 전략 상세

### 일반모드
- **전반전** (T < 20): 별% > 0, 익절
  - 매수: 1/2은 별지점, 1/2은 평단
- **후반전** (20 ≤ T < 39): 별% < 0, 손절
  - 매수: 전액 별지점

### 리버스모드 (T ≥ 39)
- **첫날**: 보유/20 MOC 무조건 매도, 매수 없음
- **둘째날 이후**:
  - 별지점 = 직전 5일 종가 평균
  - 매수: 잔금/4 (쿼터매수)
  - 매도: 보유/20 (무한매도)
- **종료**: 종가 > 평단 × 1.15 → 일반모드 복귀

### T값 계산
- **일반모드**: 체결금액 / 예정금액 (소수점)
- **리버스모드**:
  - 매도 시: T × 0.95
  - 매수 시: T + (40-T) × 0.25

## ⚠️ 주의사항

1. **API 키 보안**: `.env` 파일 절대 공유 금지
2. **시드머니**: 손실 감당 가능한 금액만 투자
3. **1차 매수**: 반드시 `/register`로 수동 등록
4. **분할수 변경**: 진행 중엔 불가능 (졸업 후 가능)
5. **리버스모드**: 규칙 준수 필수

## 🆕 V4.1.0 신기능 사용법

### 빗썸 잔고 체크
```
/balance
```

**응답 예시:**
```
💰 [BTC] 잔고 확인
  빗썸 잔고: 514,983원
  봇 잔금:   514,983원
  차이:      0원 (0.0%)
  보유 코인: 0.000130개 (봇: 0.000130개)
```

**차이가 10% 이상이면:**
```
⚠️ 경고: 잔고 차이가 15.2%로 10% 초과합니다!
```

### 버전 확인
```
/start
```

**응답에 버전 표시:**
```
📌 버전: V4.1.0
```

## 📞 문의

GitHub Issues 활용

## 📜 라이선스

MIT License

---

**무매 V4.1.0 완전판** — 2026.04.26
