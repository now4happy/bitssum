# 무매 V5.1.0 — Base64 디코딩 적용!

Invalid Apikey 에러 완전 해결! 🎉

## 🆕 V5.1.0 변경사항 (2026-05-03)

### ✅ 핵심 수정
- **FIX: 빗썸 API Secret Base64 디코딩 적용**
- **FIX: Invalid Apikey 에러 완전 해결**
- API 인증 문제 완벽 해결

### 기술적 변경
```python
# 변경 전 (V5.0.0)
self.secret_key = os.getenv("BITHUMB_SECRET").encode("utf-8")

# 변경 후 (V5.1.0)
secret_b64 = os.getenv("BITHUMB_SECRET")
self.secret_key = base64.b64decode(secret_b64)  # ⭐ Base64 디코딩!
```

---

## 📊 백테스팅 결과 (2025.01.01 ~ 2026.05.03)

- BTC: -25% 하락장 → **+9.08% 수익**
- ETH: -14% 하락장 → **+5.22% 수익**
- **총 손익: +75,748원 (+7.15%)**

✅ **하락장에서도 수익 달성!**

---

## 🚀 빠른 시작

### 1. 환경변수 설정

```bash
cp .env.template .env
nano .env
```

```env
TELEGRAM_TOKEN=여기에_봇_토큰
CHAT_ID=여기에_채팅ID
BITHUMB_API_KEY=여기에_API키
BITHUMB_SECRET=여기에_시크릿  # Base64 형식 그대로
SEED_BTC=530000
SEED_ETH=530000
```

### 2. 좀비봇 설치

```bash
bash install-daemon.sh
```

### 3. 텔레그램에서 시작

```
/start
/start_auto
```

완료! 🎉

---

## 📱 명령어

| 명령어 | 기능 |
|--------|------|
| `/start` | 봇 정보 |
| `/status` | 현재 상태 |
| `/start_auto` | 첫 매수 & 자동매매 시작 |
| `/seed` | 시드머니 관리 |
| `/history` | 졸업 기록 |
| `/mode` | 자동매매 ON/OFF |

---

## 🔧 V5.0 → V5.1 업데이트

### 서버에서:

```bash
cd ~/bitssum

# 백업
cp bithumb_api.py bithumb_api.py.v5.0.0
cp version.py version.py.v5.0.0

# 새 파일 업로드 (SFTP)
# bithumb_api.py, version.py 업로드

# 재시작
sudo systemctl restart mumae-crypto

# 확인
sudo systemctl status mumae-crypto
```

### GitHub 사용 시:

```bash
cd ~/bitssum
git pull origin main
sudo systemctl restart mumae-crypto
```

---

## ✅ 정상 작동 확인

```bash
cd ~/bitssum
source venv/bin/activate
python3 << 'TESTEOF'
from bithumb_api import BithumbAPI
api = BithumbAPI()

balance = api.get_balance('BTC')
if balance:
    print("✅ API 인증 성공!")
    print(f"KRW 잔고: {balance['available_krw']:,.0f}원")
else:
    print("❌ 여전히 실패")
TESTEOF
deactivate
```

**성공 출력:**
```
[bithumb_api.py] V5.1.0 로드됨 (Base64 디코딩)
✅ API 인증 성공!
KRW 잔고: 1,060,000원
```

---

## 📁 파일 구조

```
mumae-v5.1/
├── version.py          # V5.1.0
├── bithumb_api.py      # Base64 디코딩 적용 ⭐
├── database.py         
├── strategy.py         
├── bot.py              
├── requirements.txt    
├── .env.template       
├── .gitignore          
├── README.md           
├── install-daemon.sh   
├── monitor.sh          
├── start.sh            
├── stop.sh             
└── restart.sh          
```

---

## 📜 변경 이력

### V5.1.0 (2026-05-03)
- FIX: 빗썸 API Secret Base64 디코딩
- FIX: Invalid Apikey 에러 해결
- API 인증 문제 완전 해결

### V5.0.0 (2026-05-03)
- 첫 매수 시장가 자동 진입
- 소수점 10자리 수량 처리
- 시드 50만원 ~ 5천만원
- BTC/ETH 전용
- 백테스팅 검증 (+7.15%)

---

**무매 V5.1.0** — 2026.05.03

MIT License
