"""
bot.py — 무매 V4.1.1 텔레그램 봇 완전판

V4.1.1 변경사항:
- FIX: /register 명령어 충돌 문제 해결
- CommandHandler 제거, 텍스트 핸들러로 통합
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
auto_on       = True
reverse_first = {"BTC": False, "ETH": False}

logger.info(f"🚀 {VERSION_NAME} 시작!")


def ok(update: Update) -> bool:
    return update.effective_chat.id == ALLOWED_CHAT


# ══════════════════════════════════════════════════════
# /start
# ══════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    status = "✅ ON" if auto_on else "⛔ OFF"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    await update.message.reply_text(
        f"🌨 [ {VERSION_NAME} ]\n"
        f"💎 BTC / ETH 자동매매 시스템\n\n"
        f"⏰ [ 운영 스케줄 ]\n"
        f"🔹 매 3분: 시장 분석 & 체결 확인\n"
        f"🔹 09:00: 일일 정산 리포트\n"
        f"🔹 실시간: 별지점 자동 계산\n\n"
        f"🔧 [ 주요 명령어 ]\n"
        f"▶️ /sync : 통합 지시서\n"
        f"▶️ /balance : 빗썸 잔고 확인\n"
        f"▶️ /register : 1차 수동 등록\n"
        f"▶️ /seed : 시드머니 관리\n"
        f"▶️ /settlement : 분할수 설정\n"
        f"▶️ /record : 거래 장부\n"
        f"▶️ /history : 졸업 기록\n"
        f"▶️ /mode : 자동매매 ON/OFF\n\n"
        f"🤖 자동매매: {status}\n"
        f"⏰ 현재: {now}\n"
        f"📌 버전: V{VERSION}"
    )


# ══════════════════════════════════════════════════════
# /sync
# ══════════════════════════════════════════════════════

async def cmd_sync(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    
    for ticker, strat in strategies.items():
        price = api.get_price(ticker) or 0
        sp = strat.get_star_point()
        zone, _ = strat.get_zone()
        
        if strat.mode == "REVERSE":
            mode_label = "🔄 리버스"
        elif strat.is_loss_mode():
            mode_label = "🔻 후반전"
        else:
            mode_label = "💎 전반전" if strat.is_first_half() else "💎 후반전"
        
        pnl_pct = ((price - strat.avg_price) / strat.avg_price * 100
                   if strat.avg_price > 0 else 0)
        pnl_krw = round((price - strat.avg_price) * strat.total_units)
        
        next_budget = strat.get_buy_budget()
        sp_pct = strat.star_pct() if strat.mode == "NORMAL" else 0
        
        now_time = datetime.now().strftime("%H:%M")
        msg = (
            f"📊 [ 통합 지시서 ({mode_label}) — V{VERSION} ]\n\n"
            f"⏰ 현재: {now_time}\n"
            f"💵 종목가능금액: {strat.remaining_cash:,}원\n"
            f"🏦 RP 투자권장: {strat.seed:,}원\n"
            f"{'─' * 30}\n\n"
            f"💎 [{ticker}] 부매4 (LOC)\n"
            f"📍 진행: {strat.T:.4f}T / {strat.split}분할\n"
            f"💵 총 시드: {strat.seed:,}원\n"
            f"📅 당일 예산: {next_budget:,}원\n"
            f"💰 현재 {price:,.0f}원 / 평단 {strat.avg_price:,.0f}원 ({strat.total_units:.6f}개)\n"
            f"📈 금일 고가: {price * 1.03:,.0f}원 (+3%)\n"
            f"📉 금일 저가: {price * 0.97:,.0f}원 (-3%)\n"
            f"🔺 수익: {pnl_pct:+.2f}% ({pnl_krw:+,}원)\n\n"
            f"⚙️ 10.0% | ⭐ {sp_pct:+.1f}% | 🎯 감시: {'ON' if auto_on else 'OFF'}\n"
            f"📋 [주문 계획 - 🌙 {mode_label}]\n"
        )
        
        if zone == "BUY":
            if strat.mode == "REVERSE":
                buy_price = sp - 1
                units = round(next_budget / buy_price, 6)
                msg += f"🔵 ⚓쿼터매수: {buy_price:,.0f}원 x {units:.6f}개 (LOC)\n"
            elif strat.is_first_half():
                half = round(next_budget / 2)
                sp_price = sp - 1
                avg_price = round(strat.avg_price)
                units_sp = round(half / sp_price, 6)
                units_avg = round(half / avg_price, 6)
                msg += f"🔴 ⚓평단매수: {avg_price:,.0f}원 x {units_avg:.6f}개 (LOC)\n"
                msg += f"🔵 💫별값매수: {sp_price:,.0f}원 x {units_sp:.6f}개 (LOC)\n"
            else:
                sp_price = sp - 1
                units = round(next_budget / sp_price, 6)
                msg += f"🔵 💫별값매수: {sp_price:,.0f}원 x {units:.6f}개 (LOC)\n"
        
        elif zone == "SELL":
            if strat.mode == "REVERSE":
                divisor = 20 if strat.split == 40 else 10
                units = round(strat.total_units / divisor, 6)
                msg += f"🔵 💫별값매도: {sp:,.0f}원 x {units:.6f}개 (LOC)\n"
            else:
                quarter = round(strat.total_units / 4, 6)
                three_q = round(strat.total_units - quarter, 6)
                profit_line = round(strat.avg_price * 1.15)
                msg += f"🔵 💫별값매도: {sp:,.0f}원 x {quarter:.6f}개 (LOC)\n"
                msg += f"🔴 🎯목표매도: {profit_line:,.0f}원 x {three_q:.6f}개\n"
        
        msg += f"\n📊 [{ticker}] 자율주행 ({'ON' if auto_on else 'OFF'})"
        
        await update.message.reply_text(msg)
    
    total_profit = db.get_total_profit()
    await update.message.reply_text(
        f"💰 누적손익: {total_profit:,}원\n"
        f"🤖 자동매매: {'✅ ON' if auto_on else '⛔ OFF'}"
    )


# ══════════════════════════════════════════════════════
# /balance
# ══════════════════════════════════════════════════════

async def cmd_balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    
    for ticker, strat in strategies.items():
        ok_flag, msg = strat.check_balance_sync()
        await update.message.reply_text(msg)


# ══════════════════════════════════════════════════════
# /targets
# ══════════════════════════════════════════════════════

async def cmd_targets(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    for ticker, strat in strategies.items():
        msg = strat.get_star_table(around=8)
        await update.message.reply_text(msg)


# ══════════════════════════════════════════════════════
# /seed
# ══════════════════════════════════════════════════════

def seed_text():
    b = strategies["BTC"]
    e = strategies["ETH"]
    return (
        f"💵 [ 종목별 시드머니 관리 ] — V{VERSION}\n\n"
        f"💎 BTC  시드: {b.seed:,}원  /  잔금: {b.remaining_cash:,}원\n"
        f"💎 ETH  시드: {e.seed:,}원  /  잔금: {e.remaining_cash:,}원"
    )

def seed_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("━━━ BTC ━━━", callback_data="noop")],
        [
            InlineKeyboardButton("➕10만", callback_data="seed_BTC_add_100000"),
            InlineKeyboardButton("➕50만", callback_data="seed_BTC_add_500000"),
            InlineKeyboardButton("➖10만", callback_data="seed_BTC_sub_100000"),
            InlineKeyboardButton("➖50만", callback_data="seed_BTC_sub_500000"),
        ],
        [InlineKeyboardButton("✏️ BTC 직접입력", callback_data="seed_BTC_direct")],
        [InlineKeyboardButton("━━━ ETH ━━━", callback_data="noop")],
        [
            InlineKeyboardButton("➕10만", callback_data="seed_ETH_add_100000"),
            InlineKeyboardButton("➕50만", callback_data="seed_ETH_add_500000"),
            InlineKeyboardButton("➖10만", callback_data="seed_ETH_sub_100000"),
            InlineKeyboardButton("➖50만", callback_data="seed_ETH_sub_500000"),
        ],
        [InlineKeyboardButton("✏️ ETH 직접입력", callback_data="seed_ETH_direct")],
        [InlineKeyboardButton("🔄 새로고침", callback_data="seed_refresh")],
    ])

async def cmd_seed(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    await update.message.reply_text(seed_text(), reply_markup=seed_kb())


# ══════════════════════════════════════════════════════
# /settlement
# ══════════════════════════════════════════════════════

def strat_text():
    b = strategies["BTC"]
    e = strategies["ETH"]
    return (
        f"⚙️ [ 현재 설정 및 복리 상태 ] — V{VERSION}\n\n"
        f"💎 BTC (부매4 LOC 모드)\n"
        f"▪ 분할: {b.split}회\n"
        f"▪ 목표: 10.0%\n"
        f"▪ 자동복리: 70.0%\n"
        f"▪ 증권사 수수료: 0.25%\n"
        f"▪ 집행: ↘ LOC 단일 타겟\n\n"
        f"💎 ETH (부매4 LOC 모드)\n"
        f"▪ 분할: {e.split}회\n"
        f"▪ 목표: 10.0%\n"
        f"▪ 자동복리: 70.0%\n"
        f"▪ 증권사 수수료: 0.25%\n"
        f"▪ 집행: ↘ LOC 단일 타겟\n\n"
        "분할수를 선택하면 즉시 적용됩니다."
    )

def strat_kb():
    def split_btn(ticker, n):
        current = strategies[ticker].split
        label   = f"{'✅' if current == n else ''}{n}분할"
        return InlineKeyboardButton(label, callback_data=f"split_{ticker}_{n}")

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("━━━ BTC 분할 선택 ━━━", callback_data="noop")],
        [split_btn("BTC", 20), split_btn("BTC", 40)],
        [InlineKeyboardButton("━━━ ETH 분할 선택 ━━━", callback_data="noop")],
        [split_btn("ETH", 20), split_btn("ETH", 40)],
        [InlineKeyboardButton("🔄 새로고침", callback_data="strat_refresh")],
    ])

async def cmd_settlement(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    await update.message.reply_text(strat_text(), reply_markup=strat_kb())


# ══════════════════════════════════════════════════════
# /record
# ══════════════════════════════════════════════════════

async def cmd_record(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    
    for ticker, strat in strategies.items():
        trades = db.get_trades(ticker, 2)
        
        msg = f"📒 [ {ticker} 일자별 매매 (통합 변동분) (총 2일) ]\n\n"
        msg += f"No.  일자    구분  평균단가    수량\n"
        msg += f"{'─' * 40}\n"
        
        if not trades:
            msg += "  거래 없음\n"
        else:
            for i, (side, price, units, amt, dt) in enumerate(trades, 1):
                emoji = "🔴매수" if side == "BUY" else "🔵매도"
                date_str = dt[:10].replace("-", ".")
                msg += f"{i}    {date_str}  {emoji}  {price:>8,.0f}원  {units:.6f}개\n"
        
        msg += f"{'─' * 40}\n"
        msg += f"📊 [ 현재 진행 상황 요약 ]\n"
        msg += f"▪ 현재 T값: {strat.T:.4f}T ({strat.split}분할)\n"
        msg += f"▪ 보유 수량: {strat.total_units:.6f}개 (평단 {strat.avg_price:,.0f}원)\n"
        msg += f"▪ 사용 금액: {strat.seed - strat.remaining_cash:,}원\n"
        
        await update.message.reply_text(msg)


# ══════════════════════════════════════════════════════
# /history
# ══════════════════════════════════════════════════════

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    records = db.get_graduation_history(20)
    total   = db.get_total_profit()
    
    if not records:
        await update.message.reply_text("🏆 명예의 전당 (졸업 기록)이 비어있습니다.")
        return
    
    lines = [f"🏆 [ 명예의 전당 (졸업 기록) ] — V{VERSION}\n"]
    for i, (ticker, profit, buy_cnt, stage, dt) in enumerate(records, 1):
        icon = "🎓" if profit >= 0 else "🔻"
        lines.append(
            f"{i}. {icon} {ticker} {stage}무매  "
            f"{profit:+,}원  T={buy_cnt:.2f}  {dt[:10]}"
        )
    
    lines.append(f"\n💰 누적손익: {total:,}원")
    await update.message.reply_text("\n".join(lines))


# ══════════════════════════════════════════════════════
# /mode
# ══════════════════════════════════════════════════════

async def cmd_mode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    
    msg = (
        f"📊 [ 자율주행 변동성 마스터 ] — V{VERSION}\n\n"
        "[⏰ 지수 범위 벌레 (ON/OFF 권장)]\n"
        "❄️ ~ 15.00 : 극저변동성 (OFF)\n"
        "🟢 15.00 ~ 20.00 : 정상 궤도 (OFF)\n"
        "🟡 20.00 ~ 25.00 : 변동성 확대 (ON)\n"
        "🔴 25.00 이상 : 패닉 셀링 (ON)\n\n"
        "🎯 [ 수동 상방 스나이퍼 독립 제어 ]\n"
        f"▪ 현재 상태: {'ON' if auto_on else 'OFF (대기중)'}"
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
            strat.seed = max(10000, strat.seed + (delta if action == "add" else -delta))
            db.update_seed(ticker, strat.seed)
            await q.edit_message_text(seed_text(), reply_markup=seed_kb())

        elif action == "direct":
            ctx.user_data["waiting"] = f"seed_{ticker}"
            await q.edit_message_text(
                f"✏️ {ticker} 시드 금액 입력 (현재: {strat.seed:,}원)\n"
                f"예: 500000"
            )

        elif action == "refresh":
            await q.edit_message_text(seed_text(), reply_markup=seed_kb())
        return

    if d.startswith("split_"):
        _, ticker, n = d.split("_")
        n = int(n)
        strat = strategies[ticker]
        if strat.buy_count > 0:
            await q.edit_message_text(
                f"⚠️ {ticker}가 진행 중(T={strat.T:.2f})이라 분할수를 변경할 수 없습니다.\n"
                f"졸업/손절 후 변경해주세요.",
                reply_markup=strat_kb()
            )
            return
        strat.set_split(n)
        await q.edit_message_text(
            f"✅ {ticker} {n}분할로 변경!\n"
            f"1회 매수금: {strat.get_buy_budget():,}원",
            reply_markup=strat_kb()
        )
        return

    if d == "strat_refresh":
        await q.edit_message_text(strat_text(), reply_markup=strat_kb())


# ══════════════════════════════════════════════════════
# 텍스트 입력 (여기서 /register 처리!) ⭐ 중요
# ══════════════════════════════════════════════════════

async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    text = update.message.text.strip()

    # /register 처리 ⭐ 핵심
    if text.startswith("/register"):
        parts = text.split()
        
        # 사용법 안내
        if len(parts) == 1:
            await update.message.reply_text(
                f"⭐ [ 1차 매수 수동 등록 ] — V{VERSION}\n\n"
                "형식: /register <ticker> <체결가> <수량> <사용금액>\n\n"
                "예시:\n"
                "  /register BTC 115666000 0.0001296 15017\n"
                "  /register ETH 3455000 0.1537 530000\n\n"
                "⚠️ 주의사항:\n"
                "  • 띄어쓰기로만 구분\n"
                "  • 쉼표(,) 사용 금지\n"
                "  • 단위(원, 개) 사용 금지\n"
                "  • 숫자만 입력"
            )
            return
        
        # 실제 등록 처리
        if len(parts) != 5:
            await update.message.reply_text(
                "❌ 형식 오류\n\n"
                "올바른 형식:\n"
                "/register <ticker> <체결가> <수량> <사용금액>\n\n"
                "예: /register BTC 115666000 0.0001296 15017"
            )
            return

        ticker     = parts[1].upper()
        try:
            price      = float(parts[2])
            units      = float(parts[3])
            amount_krw = int(parts[4])
        except ValueError:
            await update.message.reply_text("❌ 숫자 입력 오류")
            return

        if ticker not in strategies:
            await update.message.reply_text(f"❌ {ticker}는 지원하지 않습니다 (BTC / ETH만 가능)")
            return

        strat = strategies[ticker]
        msg = strat.register_first_buy(price, units, amount_krw)
        await update.message.reply_text(msg)
        return

    # 시드 직접입력
    waiting = ctx.user_data.get("waiting")
    if waiting and waiting.startswith("seed_"):
        text = text.replace(",", "").replace("원", "").strip()
        ctx.user_data["waiting"] = None

        ticker = waiting.split("_")[1]
        strat  = strategies[ticker]
        try:
            amount = int(text)
            if amount < 10000:
                await update.message.reply_text("❌ 최소 10,000원 이상")
                return
            strat.seed = amount
            db.update_seed(ticker, amount)
            await update.message.reply_text(
                f"✅ {ticker} 시드: {amount:,}원\n1회 매수: {strat.get_buy_budget():,}원"
            )
            await update.message.reply_text(seed_text(), reply_markup=seed_kb())
        except ValueError:
            await update.message.reply_text("❌ 숫자만 입력하세요")


# ══════════════════════════════════════════════════════
# 자동매매 루프
# ══════════════════════════════════════════════════════

def run_auto(app):
    def job():
        global reverse_first
        if not auto_on:
            return

        for ticker, strat in strategies.items():
            try:
                strat.update_price_history()

                transition = strat.check_mode_transition()
                if transition:
                    asyncio.run(app.bot.send_message(ALLOWED_CHAT, f"[{ticker}] {transition}"))
                    if "리버스모드 전환" in transition:
                        reverse_first[ticker] = True

                event, msg = strat.check_orders_filled()
                if event and msg:
                    asyncio.run(app.bot.send_message(ALLOWED_CHAT, msg))

                zone, reason = strat.get_zone()

                if zone == "NEW":
                    pass

                elif strat.mode == "REVERSE":
                    if reverse_first.get(ticker, False):
                        _, msg = strat.place_sell_order_reverse_first()
                        if msg:
                            asyncio.run(app.bot.send_message(ALLOWED_CHAT, msg))
                        reverse_first[ticker] = False
                    else:
                        if zone == "BUY":
                            _, msg = strat.place_buy_order_reverse()
                            if msg and "대기" not in msg:
                                asyncio.run(app.bot.send_message(ALLOWED_CHAT, msg))
                        elif zone == "SELL":
                            _, msg = strat.place_sell_order_reverse()
                            if msg and "대기" not in msg:
                                asyncio.run(app.bot.send_message(ALLOWED_CHAT, msg))

                else:
                    if zone == "BUY":
                        _, msg = strat.place_buy_order_normal()
                        if msg and "대기" not in msg:
                            asyncio.run(app.bot.send_message(ALLOWED_CHAT, msg))
                    elif zone == "SELL":
                        _, msg = strat.place_sell_order_normal()
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
# 메인 ⭐ /register CommandHandler 제거됨!
# ══════════════════════════════════════════════════════

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("sync",        cmd_sync))
    app.add_handler(CommandHandler("balance",     cmd_balance))
    app.add_handler(CommandHandler("targets",     cmd_targets))
    # ⭐ /register CommandHandler 제거 (on_text에서 처리)
    app.add_handler(CommandHandler("seed",        cmd_seed))
    app.add_handler(CommandHandler("settlement",  cmd_settlement))
    app.add_handler(CommandHandler("record",      cmd_record))
    app.add_handler(CommandHandler("history",     cmd_history))
    app.add_handler(CommandHandler("mode",        cmd_mode))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    t = threading.Thread(target=run_auto, args=(app,), daemon=True)
    t.start()

    logger.info(f"🤖 {VERSION_NAME} 봇 시작!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
