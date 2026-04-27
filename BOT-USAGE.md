# 무매 V4.1.0 — 봇 실행 완벽 가이드

## 🤖 봇 실행 방법

### 방법 1: 좀비봇 설치 (자동 재시작) ⭐ 권장

**한 번만 설치:**
```bash
cd mumae-crypto-bot
bash install-daemon.sh
```

**특징:**
- ✅ 서버 재부팅 시 자동 시작
- ✅ 크래시 시 10초 후 자동 재시작
- ✅ 30분마다 생존 확인
- ✅ 무제한 재시작 (영구 실행)
- ✅ 백그라운드 실행

---

### 방법 2: 기본 설치 (setup.sh)

```bash
cd mumae-crypto-bot
bash setup.sh
```

**특징:**
- ✅ 자동 시작
- ✅ 백그라운드 실행
- ⚠️ 재시작 횟수 제한 있음

---

### 방법 3: 수동 실행 (테스트용)

```bash
cd mumae-crypto-bot
source venv/bin/activate
python bot.py
```

**특징:**
- ✅ 실시간 로그 확인 가능
- ❌ 터미널 종료 시 봇도 종료
- ❌ 크래시 시 수동 재시작 필요

---

## 🎯 간편 명령어

### 시작/중지/재시작

```bash
# 봇 시작
bash start.sh

# 봇 중지
bash stop.sh

# 봇 재시작
bash restart.sh
```

---

## 📊 모니터링

### 종합 모니터링

```bash
bash monitor.sh
```

**출력:**
```
📊 서비스 상태
✅ 상태: 실행 중
✅ 자동시작: 활성화됨

🔍 프로세스 정보
✅ PID: 12345
메모리: 2.3%, CPU: 0.5%

🔄 최근 24시간 재시작: 0회

⚠️ 최근 에러 로그
(없음)

💾 리소스 사용량
💿 디스크: 2.5GB / 7.5GB (34% 사용)
🧠 메모리: 1.2GB / 1.9GB 사용
```

---

### 실시간 로그 보기

```bash
journalctl -u mumae-crypto -f
```

**Ctrl + C로 중지**

---

### 최근 100줄 로그

```bash
journalctl -u mumae-crypto -n 100 --no-pager
```

---

### 에러 로그만 보기

```bash
journalctl -u mumae-crypto -p err --no-pager
```

---

## 🔧 systemd 명령어

### 상태 확인

```bash
sudo systemctl status mumae-crypto
```

### 시작/중지/재시작

```bash
# 시작
sudo systemctl start mumae-crypto

# 중지
sudo systemctl stop mumae-crypto

# 재시작
sudo systemctl restart mumae-crypto
```

### 자동 시작 설정

```bash
# 활성화 (부팅 시 자동 시작)
sudo systemctl enable mumae-crypto

# 비활성화
sudo systemctl disable mumae-crypto
```

---

## 🚨 문제 해결

### 봇이 계속 죽을 때

**1. 로그 확인:**
```bash
journalctl -u mumae-crypto -n 50 --no-pager
```

**2. 원인 파악:**
- API 키 오류
- 네트워크 문제
- 코드 에러

**3. 재설치:**
```bash
bash install-daemon.sh
```

---

### 좀비 프로세스 제거

```bash
# 모든 봇 프로세스 찾기
ps aux | grep bot.py

# 좀비 프로세스 종료
pkill -f bot.py

# 서비스 재시작
sudo systemctl restart mumae-crypto
```

---

### 서비스 파일 수동 수정

```bash
sudo nano /etc/systemd/system/mumae-crypto.service

# 수정 후
sudo systemctl daemon-reload
sudo systemctl restart mumae-crypto
```

---

## 📋 디버깅 모드

### 수동 실행으로 에러 확인

```bash
# 1. 서비스 중지
sudo systemctl stop mumae-crypto

# 2. 수동 실행
cd mumae-crypto-bot
source venv/bin/activate
python bot.py
```

**에러 메시지 확인 후:**
```bash
# Ctrl + C로 중지
# 서비스 재시작
sudo systemctl start mumae-crypto
```

---

## 🔄 업데이트 후 재시작

```bash
cd mumae-crypto-bot
bash update.sh
```

**자동으로 재시작됩니다!**

---

## 📱 텔레그램에서 확인

### 봇 정상 작동 확인

```
/start
```

**응답:**
```
🌨 [ 무매 V4.1.0 완전판 ]
...
📌 버전: V4.1.0
```

---

## 💡 꿀팁

### 1. 별칭(alias) 설정

```bash
nano ~/.bashrc
```

**추가:**
```bash
alias bot-start='cd ~/mumae-crypto-bot && bash start.sh'
alias bot-stop='cd ~/mumae-crypto-bot && bash stop.sh'
alias bot-restart='cd ~/mumae-crypto-bot && bash restart.sh'
alias bot-status='sudo systemctl status mumae-crypto'
alias bot-log='journalctl -u mumae-crypto -f'
alias bot-monitor='cd ~/mumae-crypto-bot && bash monitor.sh'
```

**적용:**
```bash
source ~/.bashrc
```

**사용:**
```bash
bot-start
bot-status
bot-log
bot-monitor
```

---

### 2. 크론탭으로 정기 모니터링

```bash
crontab -e
```

**추가 (매시간 모니터링):**
```
0 * * * * /home/ubuntu/mumae-crypto-bot/monitor.sh >> /tmp/bot-monitor.log 2>&1
```

---

### 3. 재부팅 시 자동 시작 확인

```bash
# 재부팅
sudo reboot

# 재접속 후
sudo systemctl status mumae-crypto
```

**"active (running)"이면 성공!**

---

## 📊 성능 모니터링

### CPU & 메모리 사용량

```bash
top -p $(pgrep -f bot.py)
```

### 디스크 사용량

```bash
df -h
```

### 로그 파일 크기

```bash
journalctl --disk-usage
```

---

## 🎯 완전 자동화 체크리스트

- [x] 좀비봇 설치 완료 (`install-daemon.sh`)
- [x] 서비스 활성화 (`systemctl enable`)
- [x] 자동 재시작 설정 (`Restart=always`)
- [x] 텔레그램 `/start` 응답 확인
- [x] 재부팅 후 자동 시작 확인

**모두 체크되면 완전 자동화 완성!** 🎉

---

**이제 봇이 영구적으로 실행됩니다!** 🚀
