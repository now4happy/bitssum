"""
strategy.py — 무매 V4.0 별지점 전략 완전판

━━━ 핵심 공식 ━━━
  별% = (20 - STEP × T)%
  별지점 = 평단 × (1 + 별% / 100)

  현재가 < 별지점  →  매수 구간  →  별지점에 지정가 매수
  현재가 > 별지점  →  매도 구간  →  별지점에 지정가 매도

━━━ 분할별 STEP ━━━
  20분할: STEP = 2.0   별% = 20 - 2.0×T   (T=10 → 0%,  T=20 → -20% 손절)
  30분할: STEP = 1.33  별% = 20 - 1.33×T  (T=15 → 0%,  T=30 → -20% 손절)
  40분할: STEP = 1.0   별% = 20 - 1.0×T   (T=20 → 0%,  T=40 → -20% 손절)

━━━ 매수 방식 ━━━
  1회 (새출발) : 시장가 즉시 매수
  2회 이후     : 별지점 가격에 지정가 매수 주문 등록
               → 평단 변경 시 기존 주문 취소 후 재등록

━━━ 매도 방식 ━━━
  매수 체결 후 항상 별지점에 지정가 매도 주문 등록
  → T가 올라갈수록 별% 감소 → 별지점이 평단에 가까워짐
  → T > 분할/2 이후 별% 마이너스 → 손절 모드
"""

import os
from database import Database

# 분할수 → STEP 매핑
SPLIT_STEP = {
    20: 2.0,
    30: 20 / 29,   # T=29 → 약 -20%
    40: 1.0,
}


class MumaeStrategy:

    def __init__(self, api, ticker: str):
        self.api    = api
        self.ticker = ticker
        self.db     = Database()

        # 미체결 주문 추적
        self.open_buy_id    = None   # 지정가 매수 주문 ID
        self.open_sell_id   = None   # 지정가 매도 주문 ID
        self.open_buy_price = None   # 현재 등록된 매수 지정가
        self.open_sell_price= None   # 현재 등록된 매도 지정가

        self._load_state()

    # ── 상태 저장/로드 ────────────────────────────────

    def _load_state(self):
        state = self.db.get_state(self.ticker)
        if state:
            self.seed        = state["seed"]
            self.avg_price   = state["avg_price"]
            self.total_units = state["total_units"]
            self.buy_count   = state["buy_count"]
            self.stage       = state["stage"]
            self.split       = state.get("split", 40)
        else:
            self.seed        = int(os.getenv(f"SEED_{self.ticker}", "500000"))
            self.avg_price   = 0.0
            self.total_units = 0.0
            self.buy_count   = 0
            self.stage       = 1
            self.split       = 40
            self._save_state()

    def _save_state(self):
        self.db.save_state(self.ticker, {
            "seed":        self.seed,
            "avg_price":   self.avg_price,
            "total_units": self.total_units,
            "buy_count":   self.buy_count,
            "stage":       self.stage,
            "split":       self.split,
        })

    # ── 핵심 계산 ─────────────────────────────────────

    @property
    def T(self):
        """현재 회차"""
        return self.buy_count

    @property
    def step(self):
        return SPLIT_STEP.get(self.split, 1.0)

    def star_pct(self, t=None):
        """별% = 20 - STEP × T"""
        t = t if t is not None else self.T
        return 20 - self.step * t

    def star_point(self, t=None):
        """별지점 = 평단 × (1 + 별%/100)"""
        if self.avg_price == 0:
            return 0
        return round(self.avg_price * (1 + self.star_pct(t) / 100))

    @property
    def daily_budget(self):
        return round(self.seed / self.split)

    def is_loss_mode(self):
        """별% < 0 → 손절 모드"""
        return self.star_pct() < 0

    # ── 매수/매도 구간 판단 ───────────────────────────

    def get_zone(self):
        """
        반환: (zone: str, 설명: str)
        zone = "NEW" | "BUY" | "SELL" | "DONE" | "WAIT"
        """
        # 새출발
        if self.buy_count == 0:
            return "NEW", "새출발 — 시장가 매수"

        # 소진
        if self.buy_count >= self.split:
            return "DONE", f"전 회차 소진 ({self.split}/{self.split})"

        price = self.api.get_price(self.ticker)
        if price is None:
            return "WAIT", "가격 조회 실패"

        sp    = self.star_point()
        sp_pct = self.star_pct()
        diff  = (price - sp) / sp * 100

        if price < sp:
            return "BUY", (
                f"매수 구간\n"
                f"  별지점: {sp:,.0f}원\n"
                f"  현재가: {price:,.0f}원  ({diff:+.2f}%)\n"
                f"  별%:    {sp_pct:+.2f}%  T={self.T}"
            )
        else:
            label = "🔻 손절 구간" if self.is_loss_mode() else "📈 매도 구간"
            return "SELL", (
                f"{label}\n"
                f"  별지점: {sp:,.0f}원\n"
                f"  현재가: {price:,.0f}원  ({diff:+.2f}%)\n"
                f"  별%:    {sp_pct:+.2f}%  T={self.T}"
            )

    # ── 1회 새출발 (시장가) ───────────────────────────

    def execute_first_buy(self):
        price = self.api.get_price(self.ticker)
        if not price:
            return None, "❌ 가격 조회 실패"

        budget = self.daily_budget
        units  = budget / price
        result = self.api.buy_market(self.ticker, budget)

        if result and result.get("status") == "0000":
            self.avg_price   = price
            self.total_units = units
            self.buy_count   = 1
            self._save_state()
            self.db.log_trade(self.ticker, "BUY", price, units, budget)

            sp = self.star_point()
            return result, (
                f"✨ [{self.ticker}] 새출발!\n"
                f"  체결가:  {price:,.0f}원\n"
                f"  매수금:  {budget:,}원\n"
                f"  수량:    {units:.6f}개\n"
                f"  평단:    {self.avg_price:,.0f}원\n"
                f"  별%:     {self.star_pct():+.2f}%\n"
                f"  별지점:  {sp:,.0f}원  ← 매도 지정가 등록 예정"
            )
        return None, f"❌ 새출발 매수 실패: {result}"

    # ── 지정가 매수 등록 ──────────────────────────────

    def place_buy_order(self):
        """
        다음 회차 별지점에 지정가 매수 등록
        - 이미 같은 가격 주문 있으면 스킵
        - 별지점이 바뀌었으면 기존 취소 후 재등록
        """
        sp     = self.star_point()
        budget = self.daily_budget
        units  = round(budget / sp, 6)

        # 같은 가격 주문 이미 있음
        if self.open_buy_id and self.open_buy_price == sp:
            return None, f"⏳ 매수 대기 중: {sp:,.0f}원"

        # 기존 주문 가격 다름 → 취소
        if self.open_buy_id:
            self.api.cancel_order(self.ticker, self.open_buy_id, "bid")
            self.open_buy_id    = None
            self.open_buy_price = None

        result = self.api.buy_limit(self.ticker, sp, units)

        if result and result.get("status") == "0000":
            self.open_buy_id    = result.get("data", {}).get("order_id", "unknown")
            self.open_buy_price = sp
            return result, (
                f"🔵 [{self.ticker}] {self.T+1}회차 지정가 매수 등록\n"
                f"  주문가:  {sp:,.0f}원\n"
                f"  수량:    {units:.6f}개  ({budget:,}원)\n"
                f"  별%:     {self.star_pct():+.2f}%  (T={self.T})"
            )
        return None, f"❌ 지정가 매수 실패: {result}"

    def on_buy_filled(self, price: float, units: float, amount_krw: int):
        """매수 체결 처리 — 평단/T 업데이트"""
        self.open_buy_id    = None
        self.open_buy_price = None

        total_cost       = self.avg_price * self.total_units + amount_krw
        self.total_units += units
        self.avg_price    = total_cost / self.total_units
        self.buy_count   += 1
        self._save_state()
        self.db.log_trade(self.ticker, "BUY", price, units, amount_krw)

    # ── 지정가 매도 등록 ──────────────────────────────

    def place_sell_order(self):
        """
        별지점에 지정가 매도 등록
        - 같은 가격 주문 있으면 스킵
        - 별지점 바뀌면 기존 취소 후 재등록
        """
        if self.total_units == 0:
            return None, "보유 수량 없음"

        sp    = self.star_point()
        units = round(self.total_units, 6)

        # 같은 가격 주문 이미 있음
        if self.open_sell_id and self.open_sell_price == sp:
            return None, f"⏳ 매도 대기 중: {sp:,.0f}원"

        # 기존 주문 취소
        if self.open_sell_id:
            self.api.cancel_order(self.ticker, self.open_sell_id, "ask")
            self.open_sell_id    = None
            self.open_sell_price = None

        result = self.api.sell_limit(self.ticker, sp, units)

        if result and result.get("status") == "0000":
            self.open_sell_id    = result.get("data", {}).get("order_id", "unknown")
            self.open_sell_price = sp
            pnl = (sp - self.avg_price) / self.avg_price * 100
            mode = "손절" if self.is_loss_mode() else "익절"
            return result, (
                f"🔴 [{self.ticker}] 지정가 {mode} 주문 등록\n"
                f"  매도가:  {sp:,.0f}원\n"
                f"  수량:    {units:.6f}개\n"
                f"  평단:    {self.avg_price:,.0f}원\n"
                f"  예상손익: {pnl:+.2f}%\n"
                f"  별%:     {self.star_pct():+.2f}%  (T={self.T})"
            )
        return None, f"❌ 지정가 매도 실패: {result}"

    def on_sell_filled(self, price: float, units: float, amount_krw: int) -> str:
        """매도 체결 처리 — 졸업/손절 후 초기화"""
        self.open_sell_id    = None
        self.open_sell_price = None

        profit = round((price - self.avg_price) * units)
        self.db.log_trade(self.ticker, "SELL", price, units, amount_krw)
        self.db.log_graduation(self.ticker, profit, self.buy_count)

        mode = "손절" if profit < 0 else "🎓 졸업"
        msg  = (
            f"{mode} [{self.ticker}]\n"
            f"  매도가:   {price:,.0f}원\n"
            f"  손익:     {profit:+,}원\n"
            f"  진행회차: {self.buy_count}/{self.split}\n"
            f"  다음단계: {self.stage + 1}무매"
        )
        # 초기화
        self.avg_price   = 0.0
        self.total_units = 0.0
        self.buy_count   = 0
        self.stage      += 1
        self._save_state()
        return msg

    # ── 미체결 주문 체결 여부 확인 ────────────────────

    def check_orders_filled(self):
        """
        미체결 주문이 체결됐는지 확인
        반환: ("BUY_FILLED" | "SELL_FILLED" | None, 메시지)
        """
        # 매수 체결 확인
        if self.open_buy_id:
            detail = self.api.get_order_detail(self.ticker, self.open_buy_id)
            if detail and detail.get("order_status") == "Completed":
                price  = float(detail.get("price", 0))
                units  = float(detail.get("units_traded", 0))
                amount = price * units
                self.on_buy_filled(price, units, int(amount))
                return "BUY_FILLED", (
                    f"✅ [{self.ticker}] {self.T}회차 매수 체결!\n"
                    f"  체결가: {price:,.0f}원\n"
                    f"  수량:   {units:.6f}개\n"
                    f"  평단:   {self.avg_price:,.0f}원\n"
                    f"  새 별지점: {self.star_point():,.0f}원"
                )

        # 매도 체결 확인
        if self.open_sell_id:
            detail = self.api.get_order_detail(self.ticker, self.open_sell_id)
            if detail and detail.get("order_status") == "Completed":
                price  = float(detail.get("price", 0))
                units  = float(detail.get("units_traded", 0))
                amount = price * units
                msg = self.on_sell_filled(price, units, int(amount))
                return "SELL_FILLED", msg

        return None, None

    # ── 분할수 변경 ───────────────────────────────────

    def set_split(self, split: int) -> bool:
        if split not in SPLIT_STEP:
            return False
        self.split = split
        self._save_state()
        return True

    # ── 상태 텍스트 ───────────────────────────────────

    def get_status_text(self):
        price   = self.api.get_price(self.ticker) or 0
        sp      = self.star_point()
        sp_pct  = self.star_pct()
        pnl_pct = ((price - self.avg_price) / self.avg_price * 100
                   if self.avg_price > 0 else 0)
        pnl_krw = round((price - self.avg_price) * self.total_units
                        if self.avg_price > 0 else 0)
        mode    = "🔻손절모드" if self.is_loss_mode() else ""

        buy_order  = f"{self.open_buy_price:,.0f}원" if self.open_buy_price  else "없음"
        sell_order = f"{self.open_sell_price:,.0f}원" if self.open_sell_price else "없음"

        return (
            f"💎 [{self.ticker}] {self.stage}무매 {self.split}분할 {mode}\n"
            f"  진행:      {self.T}/{self.split}회차\n"
            f"  시드:      {self.seed:,}원  (1회 {self.daily_budget:,}원)\n"
            f"  현재가:    {price:,.0f}원\n"
            f"  평단:      {self.avg_price:,.0f}원  ({self.total_units:.6f}개)\n"
            f"  별%:       {sp_pct:+.2f}%\n"
            f"  별지점:    {sp:,.0f}원\n"
            f"  수익:      {pnl_pct:+.2f}%  ({pnl_krw:+,}원)\n"
            f"  매수주문:  {buy_order}\n"
            f"  매도주문:  {sell_order}\n"
        )

    def get_star_table(self, around: int = 5):
        """현재 T 주변 별지점 테이블"""
        if self.avg_price == 0:
            return f"[{self.ticker}] 새출발 전 — 별지점 없음\n"

        lines = [f"📊 [{self.ticker}] 별지점 테이블\n"]
        start = max(0, self.T - 2)
        end   = min(self.split + 1, self.T + around)

        for t in range(start, end):
            sp   = round(self.avg_price * (1 + self.star_pct(t) / 100))
            pct  = self.star_pct(t)
            if t < self.T:
                icon = "✅"
            elif t == self.T:
                icon = "▶️"
            else:
                icon = "⬜"
            mode = " 손절" if pct < 0 else ""
            lines.append(
                f"  {icon} T={t:02d}: {sp:>13,.0f}원  (별% {pct:+.1f}%{mode})"
            )
        return "\n".join(lines)
