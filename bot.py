"""
bot.py — 무매 V4.0 텔레그램 봇 완전판

명령어:
  /start      시작 및 명령어 목록
  /sync       통합 현황 (별지점, 미체결 주문 포함)
  /targets    별지점 테이블
  /seed       시드머니 관리 (버튼 + 직접입력)
  /settlement 전략 설정 (20/30/40분할)
  /record     거래 장부
  /history    졸업/손절 기록
  /mode       자동매매 ON/OFF

자동매매 로직 (매 3분):
  1. 미체결 주문 체결 여부 확인
  2. 체결됐으면 → 새 주문 등록
  3. 구간 판단 → 해당 구간 주문 유지/재등록
"""

import os
import asyncio
import logging
import threading
import schedule
import time
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)

from bithumb_api import BithumbAPI
from strategy import MumaeStrategy
from database import Database

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

TOKEN          = os.getenv("TELEGRAM_TOKEN")
ALLOWED_CHAT   = int(os.getenv("CHAT_ID", "0"))

api        = BithumbAPI()
db         = Database()
strategies = {
    "BTC": MumaeStrategy(api, "BTC"),
    "ETH": MumaeStrategy(api, "ETH"),
}
auto_on = True   # 자동매매 전역 플래그


# ── 보안 ─────────────────────────────────────────────

def ok(update: Update) -> bool:
    return update.effective_chat.id == ALLOWED_CHAT


# ══════════════════════════════════════════════════════
# UI 헬퍼
# ══════════════════════════════════════════════════════

# ── 시드 ─────────────────────────────────────────────

def seed_text():
    b = strategies["BTC"]
    e = strategies["ETH"]
    return (
        "💵 [ 시드머니 관리 ]\n\n"
        f"💎 BTC  시드: {b.seed:,}원  /  1회: {b.daily_budget:,}원\n"
        f"💎 ETH  시드: {e.seed:,}원  /  1회: {e.daily_budget:,}원"
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

# ── 전략 설정 ─────────────────────────────────────────

def strat_text():
    b = strategies["BTC"]
    e = strategies["ETH"]
    return (
        "⚙️ [ 전략 설정 ]\n\n"
        f"💎 BTC  분할: {b.split}분할  /  STEP: {b.step:.2f}\n"
        f"   별% = (20 - {b.step:.2f} × T)%\n"
        f"   손절 시작: T={int(20/b.step)} 회차부터\n\n"
        f"💎 ETH  분할: {e.split}분할  /  STEP: {e.step:.2f}\n"
        f"   별% = (20 - {e.step:.2f} × T)%\n"
        f"   손절 시작: T={int(20/e.step)} 회차부터\n\n"
        "분할수를 선택하면 즉시 적용됩니다."
    )

def strat_kb():
    b = strategies["BTC"]
    e = strategies["ETH"]

    def split_btn(ticker, n):
        current = strategies[ticker].split
        label   = f"{'✅' if current == n else ''}{n}분할"
        return InlineKeyboardButton(label, callback_data=f"split_{ticker}_{n}")

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("━━━ BTC 분할 선택 ━━━", callback_data="noop")],
        [split_btn("BTC", 20), split_btn("BTC", 30), split_btn("BTC", 40)],
        [InlineKeyboardButton("━━━ ETH 분할 선택 ━━━", callback_data="noop")],
        [split_btn("ETH", 20), split_btn("ETH", 30), split_btn("ETH", 40)],
        [InlineKeyboardButton("🔄 새로고침", callback_data="strat_refresh")],
    ])


# ══════════════════════════════════════════════════════
# 명령어 핸들러
# ══════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    status = "✅ ON" if auto_on else "⛔ OFF"
    await update.message.reply_text(
        f"🌨 [ 무매 V4.0 — 빗썸 크립토 봇 ]\n"
        f"자동매매: {status}\n\n"
        "/sync       📋 통합 현황\n"
        "/targets    📊 별지점 테이블\n"
        "/seed       💵 시드머니 관리\n"
        "/settlement ⚙️ 분할수 설정\n"
        "/record     📒 거래 장부\n"
        "/history    🏆 졸업/손절 기록\n"
        "/mode       🎯 자동매매 ON/OFF\n"
    )


async def cmd_sync(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    lines = ["📋 [ 통합 현황 ]\n"]
    for ticker, strat in strategies.items():
        lines.append(strat.get_status_text())
        zone, reason = strat.get_zone()
        lines.append(f"  상태: {reason}\n")

    lines.append(f"🤖 자동매매: {'✅ ON' if auto_on else '⛔ OFF'}")
    lines.append(f"💰 누적손익: {db.get_total_profit():,}원")
    await update.message.reply_text("\n".join(lines))


async def cmd_targets(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    lines = ["📊 [ 별지점 테이블 ]\n"]
    for ticker, strat in strategies.items():
        lines.append(strat.get_star_table(around=8))
        lines.append("")
    await update.message.reply_text("\n".join(lines))


async def cmd_seed(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    await update.message.reply_text(seed_text(), reply_markup=seed_kb())


async def cmd_settlement(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    await update.message.reply_text(strat_text(), reply_markup=strat_kb())


async def cmd_record(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    lines = ["📒 [ 거래 장부 — 최근 5건 ]\n"]
    for ticker in ["BTC", "ETH"]:
        trades = db.get_trades(ticker, 5)
        lines.append(f"── {ticker} ──")
        if not trades:
            lines.append("  거래 없음")
        for side, price, units, amt, dt in trades:
            emoji = "🟢" if side == "BUY" else "🔴"
            lines.append(
                f"  {emoji} {side}  {price:,.0f}원  "
                f"{units:.5f}개  {int(amt):,}원  {dt[5:16]}"
            )
        lines.append("")
    await update.message.reply_text("\n".join(lines))


async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    records = db.get_graduation_history(20)
    total   = db.get_total_profit()
    if not records:
        await update.message.reply_text("🏆 아직 졸업/손절 기록 없음")
        return
    lines = ["🏆 [ 졸업/손절 기록 ]\n"]
    for i, (ticker, profit, buy_cnt, stage, dt) in enumerate(records, 1):
        icon = "🎓" if profit >= 0 else "🔻"
        lines.append(
            f"{i}. {icon} {ticker} {stage}무매  "
            f"{profit:+,}원  {buy_cnt}회  {dt[:10]}"
        )
    lines.append(f"\n💰 누적손익: {total:,}원")
    await update.message.reply_text("\n".join(lines))


async def cmd_mode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    current = "✅ ON" if auto_on else "⛔ OFF"
    await update.message.reply_text(
        f"🎯 자동매매  현재: {current}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ ON",  callback_data="mode_on"),
            InlineKeyboardButton("⛔ OFF", callback_data="mode_off"),
        ]]),
    )


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

    # ── 자동매매 토글
    if d == "mode_on":
        auto_on = True
        await q.edit_message_text("✅ 자동매매 ON — 3분마다 체크 중")
        return
    if d == "mode_off":
        auto_on = False
        await q.edit_message_text("⛔ 자동매매 OFF")
        return

    # ── 시드 버튼   seed_BTC_add_100000
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

    # ── 분할수 버튼   split_BTC_40
    if d.startswith("split_"):
        _, ticker, n = d.split("_")
        n = int(n)
        strat = strategies[ticker]
        if strat.buy_count > 0:
            await q.edit_message_text(
                f"⚠️ {ticker}가 진행 중({strat.T}회차)이라 분할수를 변경할 수 없습니다.\n"
                f"졸업/손절 후 변경해주세요.",
                reply_markup=strat_kb()
            )
            return
        strat.set_split(n)
        await q.edit_message_text(
            f"✅ {ticker} {n}분할로 변경!\n"
            f"1회 매수금: {strat.daily_budget:,}원",
            reply_markup=strat_kb()
        )
        return

    if d == "strat_refresh":
        await q.edit_message_text(strat_text(), reply_markup=strat_kb())


# ══════════════════════════════════════════════════════
# 텍스트 입력 (직접입력 처리)
# ══════════════════════════════════════════════════════

async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    waiting = ctx.user_data.get("waiting")
    if not waiting:
        return

    text = update.message.text.replace(",", "").replace("원", "").strip()
    ctx.user_data["waiting"] = None

    if waiting.startswith("seed_"):
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
                f"✅ {ticker} 시드: {amount:,}원\n1회 매수: {strat.daily_budget:,}원"
            )
            await update.message.reply_text(seed_text(), reply_markup=seed_kb())
        except ValueError:
            await update.message.reply_text("❌ 숫자만 입력하세요")


# ══════════════════════════════════════════════════════
# 자동매매 루프 (별도 스레드)
# ══════════════════════════════════════════════════════

def run_auto(app):
    """
    매 3분:
      1. 미체결 주문 체결 여부 확인
      2. 체결됐으면 새 주문 등록
      3. 구간 판단 → 주문 유지/재등록
    """
    def job():
        if not auto_on:
            return

        for ticker, strat in strategies.items():
            try:
                # ── 1. 체결 여부 확인
                event, msg = strat.check_orders_filled()
                if event and msg:
                    asyncio.run(app.bot.send_message(ALLOWED_CHAT, msg))

                # ── 2. 새출발 여부
                zone, reason = strat.get_zone()

                if zone == "NEW":
                    _, msg = strat.execute_first_buy()
                    if msg:
                        asyncio.run(app.bot.send_message(ALLOWED_CHAT, msg))
                    # 새출발 후 즉시 매도 지정가 등록
                    _, msg = strat.place_sell_order()
                    if msg:
                        asyncio.run(app.bot.send_message(ALLOWED_CHAT, msg))

                elif zone == "BUY":
                    # 매수 구간 → 지정가 매수 주문 유지/등록
                    # 기존 매도 주문이 있으면 취소
                    if strat.open_sell_id:
                        api.cancel_order(ticker, strat.open_sell_id, "ask")
                        strat.open_sell_id    = None
                        strat.open_sell_price = None
                    _, msg = strat.place_buy_order()
                    # 같은 가격이면 msg만 있고 result None → 알림 안 보냄
                    if msg and "대기" not in msg:
                        asyncio.run(app.bot.send_message(ALLOWED_CHAT, msg))

                elif zone == "SELL":
                    # 매도 구간 → 지정가 매도 주문 유지/등록
                    # 기존 매수 주문이 있으면 취소
                    if strat.open_buy_id:
                        api.cancel_order(ticker, strat.open_buy_id, "bid")
                        strat.open_buy_id    = None
                        strat.open_buy_price = None
                    _, msg = strat.place_sell_order()
                    if msg and "대기" not in msg:
                        asyncio.run(app.bot.send_message(ALLOWED_CHAT, msg))

                elif zone == "DONE":
                    asyncio.run(app.bot.send_message(
                        ALLOWED_CHAT,
                        f"⚠️ [{ticker}] 전 회차 소진!\n손절 처리가 필요합니다."
                    ))

            except Exception as e:
                logger.error(f"자동매매 오류 [{ticker}]: {e}")

    def morning():
        lines = ["☀️ [ 일일 정산 ]\n"]
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

    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("sync",        cmd_sync))
    app.add_handler(CommandHandler("targets",     cmd_targets))
    app.add_handler(CommandHandler("seed",        cmd_seed))
    app.add_handler(CommandHandler("settlement",  cmd_settlement))
    app.add_handler(CommandHandler("record",      cmd_record))
    app.add_handler(CommandHandler("history",     cmd_history))
    app.add_handler(CommandHandler("mode",        cmd_mode))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    t = threading.Thread(target=run_auto, args=(app,), daemon=True)
    t.start()

    logger.info("🤖 무매 V4.0 봇 시작!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
