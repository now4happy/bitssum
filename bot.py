
import os
import sys
import time
import logging
import subprocess
import hashlib
import hmac
import base64
import requests
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 기존 사용자 파일 임포트
from strategy import MumaeStrategy
from database import Database

# 1. 환경 설정 로드
load_dotenv()
API_KEY = os.getenv("BITHUMB_API_KEY")
API_SECRET = os.getenv("BITHUMB_SECRET_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
try:
    ADMIN_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
except (TypeError, ValueError):
    ADMIN_ID = 0

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

# ----------------------------------------------------------------
# 2. 빗썸 API 인증 및 통신 (API 1.0 기준 5100 에러 방지용)
# ----------------------------------------------------------------
class BithumbAPI:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.bithumb.com"

    def _get_signature(self, endpoint, params, nonce):
        str_to_sign = endpoint + chr(0) + params + chr(0) + nonce
        h = hmac.new(self.api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha512)
        return base64.b64encode(h.hexdigest().encode('utf-8')).decode('utf-8')

    def xcoin_api_call(self, endpoint, params):
        nonce = str(int(time.time() * 1000))
        params['endpoint'] = endpoint
        url_params = requests.compat.urlencode(params)
        
        headers = {
            "Api-Key": self.api_key,
            "Api-Sign": self._get_signature(endpoint, url_params, nonce),
            "Api-Nonce": nonce
        }
        
        try:
            response = requests.post(self.base_url + endpoint, data=params, headers=headers)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_current_price(self, ticker):
        res = requests.get(f"{self.base_url}/public/ticker/{ticker}_KRW")
        data = res.json()
        if data['status'] == '0000':
            return float(data['data']['closing_price'])
        return None

# ----------------------------------------------------------------
# 3. 텔레그램 핸들러
# ----------------------------------------------------------------

# /update : 깃허브에서 코드 가져오기 및 재시작
async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ 권한이 없습니다.")
        return

    await update.message.reply_text("🔄 깃허브에서 최신 코드를 다운로드 중...")
    
    try:
        # git pull 실행
        pull_result = subprocess.check_output(["git", "pull"], stderr=subprocess.STDOUT).decode('utf-8')
        await update.message.reply_text(f"✅ Git Pull 완료:\n```{pull_result}```", parse_mode="Markdown")
        
        await update.message.reply_text("🚀 시스템을 재시작합니다. 잠시 후 /status로 확인하세요.")
        
        # 프로세스 종료 -> systemd가 자동으로 재시작
        os._exit(0)
    except Exception as e:
        await update.message.reply_text(f"❌ 업데이트 중 오류 발생:\n{str(e)}")

# /status : 현재 계좌 및 전략 상태 확인
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    # 예시: BTC 상태 출력 (실제 루프 로직과 연동 필요)
    await update.message.reply_text("📊 무한매수 봇 가동 중...\n실시간 데이터 분석 기능을 구현 중입니다.")

# ----------------------------------------------------------------
# 4. 메인 실행 루프 (무한매수 로직 실행)
# ----------------------------------------------------------------
async def trading_job(context: ContextTypes.DEFAULT_TYPE):
    # 여기에 주기적으로 실행될 매매 로직을 작성합니다.
    # 1. 현재가 조회
    # 2. strategy.py의 get_zone() 호출
    # 3. 주문 실행 (BithumbAPI 활용)
    pass

if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN이 설정되지 않았습니다.")
        sys.exit(1)

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # 명령어 등록
    app.add_handler(CommandHandler("update", update_command))
    app.add_handler(CommandHandler("status", status_command))

    # 주기적 작업 등록 (예: 1분마다 실행)
    # job_queue = app.job_queue
    # job_queue.run_repeating(trading_job, interval=60, first=10)

    logger.info("=== 무매 크립토 봇 시작됨 ===")
    app.run_polling()
