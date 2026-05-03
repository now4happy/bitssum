"""
bot.py — 무매 V5.0 텔레그램 봇

간소화된 UI
- 첫 매수 자동 진입
- BTC/ETH 전용
- 불필요한 요소 제거
"""

import os
import asyncio
import logging
import threading
import schedule
import time
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)

from bithumb_api import BithumbAPI
from strategy import MumaeStrategy
from database import Database
from version import VERSION, VERSION_NAME

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

TOKEN        = os.getenv("TELEGRAM_TOKEN")
ALLOWED_CHAT = int(os.getenv("CHAT_ID", "0"))

api        = BithumbAPI()
db         = Database()
strategies = {
    "BTC": MumaeStrategy(api, "BTC"),
    "ETH": MumaeStrategy(api, "ETH"),
}
auto_on = True

logger.info(f"🚀 {VERSION_NAME} 시작!")


def ok(update: Update) -> bool:
    return update.effective_chat.id == ALLOWED_CHAT


# ══════════════════════════════════════════════════════
# /start
# ══════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    status = "✅ ON" if auto_on else "⛔ OFF"
    
    await update.message.reply_text(
        f"🌟 [ {VERSION_NAME} ]\n"
        f"무한매수법 4.0 자동매매 시스템\n\n"
        f"💎 투자대상: BTC / ETH\n"
        f"📊 전략: 40분할 무매\n"
        f"💰 시드: 50만원 ~ 5천만원\n\n"
        f"🔧 [ 명령어 ]\n"
        f"▶️ /status : 현재 상태\n"
        f"▶️ /start_auto : 첫 매수 & 자동매매 시작\n"
        f"▶️ /seed : 시드머니 관리\n"
        f"▶️ /history : 졸업 기록\n"
        f"▶️ /mode : 자동매매 ON/OFF\n\n"
        f"🤖 자동매매: {status}\n"
        f"📌 버전: V{VERSION}"
    )


# ══════════════════════════════════════════════════════
# /status
# ══════════════════════════════════════════════════════

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    
    for ticker, strat in strategies.items():
        msg = strat.get_status_text()
        await update.message.reply_text(msg)
    
    total_profit = db.get_total_profit()
    await update.message.reply_text(
        f"💰 총 누적 손익: {total_profit:,}원\n"
        f"🤖 자동매매: {'✅ ON' if auto_on else '⛔ OFF'}"
    )


# ══════════════════════════════════════════════════════
# /start_auto - 첫 매수 & 자동매매 시작
# ══════════════════════════════════════════════════════

async def cmd_start_auto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    
    await update.message.reply_text("🚀 자동매매 시작 중...\n첫 매수를 진행합니다.")
    
    for ticker, strat in strategies.items():
        if not strat.first_buy_done:
            result, msg = strat.auto_first_buy()
            await update.message.reply_text(msg)
            if not result:
                continue
    
    global auto_on
    auto_on = True
    
    await update.message.reply_text(
        "✅ 자동매매 시작 완료!\n"
        "3분마다 시장을 분석하고 자동으로 거래합니다."
    )


# ══════════════════════════════════════════════════════
# /seed
# ══════════════════════════════════════════════════════

def seed_text():
    b = strategies["BTC"]
    e = strategies["ETH"]
    return (
        f"💵 [ 시드머니 관리 ] — V{VERSION}\n\n"
        f"💎 BTC: {b.seed:,}원 (잔금: {b.remaining_cash:,.0f}원)\n"
        f"💎 ETH: {e.seed:,}원 (잔금: {e.remaining_cash:,.0f}원)\n\n"
        f"⚠️ 범위: 500,000원 ~ 50,000,000원"
    )

def seed_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("━━━ BTC ━━━", callback_data="noop")],
        [
            InlineKeyboardButton("➕10만", callback_data="seed_BTC_add_100000"),
            InlineKeyboardButton("➕50만", callback_data="seed_BTC_add_500000"),
            InlineKeyboardButton("➖10만", callback_data="seed_BTC_sub_100000"),
        ],
        [InlineKeyboardButton("━━━ ETH ━━━", callback_data="noop")],
        [
            InlineKeyboardButton("➕10만", callback_data="seed_ETH_add_100000"),
            InlineKeyboardButton("➕50만", callback_data="seed_ETH_add_500000"),
            InlineKeyboardButton("➖10만", callback_data="seed_ETH_sub_100000"),
        ],
        [InlineKeyboardButton("🔄 새로고침", callback_data="seed_refresh")],
    ])

async def cmd_seed(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    await update.message.reply_text(seed_text(), reply_markup=seed_kb())


# ══════════════════════════════════════════════════════
# /history
# ══════════════════════════════════════════════════════

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    records = db.get_graduation_history(20)
    total   = db.get_total_profit()
    
    if not records:
        await update.message.reply_text("🏆 아직 졸업 기록이 없습니다.")
        return
    
    lines = [f"🏆 [ 졸업 기록 ] — V{VERSION}\n"]
    for i, (ticker, profit, buy_cnt, dt) in enumerate(records, 1):
        icon = "🎓" if profit >= 0 else "🔻"
        lines.append(
            f"{i}. {icon} {ticker}  {profit:+,}원  "
            f"T={buy_cnt:.2f}  {dt[:10]}"
        )
    
    lines.append(f"\n💰 총 누적 손익: {total:,}원")
    await update.message.reply_text("\n".join(lines))


# ══════════════════════════════════════════════════════
# /mode
# ══════════════════════════════════════════════════════

async def cmd_mode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    
    msg = (
        f"🤖 [ 자동매매 제어 ] — V{VERSION}\n\n"
        f"현재 상태: {'✅ ON (작동 중)' if auto_on else '⛔ OFF (대기 중)'}\n\n"
        f"ON: 3분마다 자동 매매\n"
        f"OFF: 수동 제어"
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚪ OFF", callback_data="mode_off"),
            InlineKeyboardButton("🎯 ON", callback_data="mode_on"),
        ]
    ])
    
    await update.message.reply_text(msg, reply_markup=kb)


# ══════════════════════════════════════════════════════
# 버튼 콜백
# ══════════════════════════════════════════════════════

async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global auto_on
    q = update.callback_query
    await q.answer()
    d = q.data

    if d == "noop":
        return

    if d == "mode_on":
        auto_on = True
        await q.edit_message_text(f"✅ 자동매매 ON (V{VERSION})")
        return
    if d == "mode_off":
        auto_on = False
        await q.edit_message_text(f"⛔ 자동매매 OFF (V{VERSION})")
        return

    if d.startswith("seed_"):
        parts  = d.split("_")
        ticker = parts[1]
        action = parts[2]
        strat  = strategies[ticker]

        if action in ("add", "sub"):
            delta = int(parts[3])
            new_seed = strat.seed + (delta if action == "add" else -delta)
            
            # 범위 검증
            if new_seed < 500000:
                await q.edit_message_text(
                    "❌ 최소 시드는 500,000원입니다.",
                    reply_markup=seed_kb()
                )
                return
            if new_seed > 50000000:
                await q.edit_message_text(
                    "❌ 최대 시드는 50,000,000원입니다.",
                    reply_markup=seed_kb()
                )
                return
            
            strat.seed = new_seed
            db.update_seed(ticker, new_seed)
            await q.edit_message_text(seed_text(), reply_markup=seed_kb())

        elif action == "refresh":
            await q.edit_message_text(seed_text(), reply_markup=seed_kb())


# ══════════════════════════════════════════════════════
# 자동매매 루프
# ══════════════════════════════════════════════════════

def run_auto(app):
    def job():
        if not auto_on:
            return

        for ticker, strat in strategies.items():
            try:
                # 첫 매수 확인
                if not strat.first_buy_done:
                    continue

                # 체결 확인
                event, msg = strat.check_orders_filled()
                if event and msg:
                    asyncio.run(app.bot.send_message(ALLOWED_CHAT, msg))

                # 구간 판단
                zone, reason = strat.get_zone()

                if zone == "BUY":
                    _, msg = strat.place_buy_order()
                    if msg and "대기" not in msg:
                        asyncio.run(app.bot.send_message(ALLOWED_CHAT, msg))
                
                elif zone == "SELL":
                    _, msg = strat.place_sell_order()
                    if msg and "대기" not in msg:
                        asyncio.run(app.bot.send_message(ALLOWED_CHAT, msg))

            except Exception as e:
                logger.error(f"자동매매 오류 [{ticker}]: {e}")

    def morning():
        lines = [f"☀️ [ 일일 정산 ] — V{VERSION}\n"]
        for ticker, strat in strategies.items():
            lines.append(strat.get_status_text())
        asyncio.run(app.bot.send_message(ALLOWED_CHAT, "\n".join(lines)))

    schedule.every(3).minutes.do(job)
    schedule.every().day.at("09:01").do(morning)

    while True:
        schedule.run_pending()
        time.sleep(20)


# ══════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("status",     cmd_status))
    app.add_handler(CommandHandler("start_auto", cmd_start_auto))
    app.add_handler(CommandHandler("seed",       cmd_seed))
    app.add_handler(CommandHandler("history",    cmd_history))
    app.add_handler(CommandHandler("mode",       cmd_mode))
    app.add_handler(CallbackQueryHandler(on_button))

    t = threading.Thread(target=run_auto, args=(app,), daemon=True)
    t.start()

    logger.info(f"🤖 {VERSION_NAME} 봇 시작!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
