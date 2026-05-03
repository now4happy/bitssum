"""
strategy.py — 무매 V5.0

무한매수법 4.0 전략
- 첫 매수 시장가 자동 진입
- 소수점 10자리 수량 처리
- 시드 50만원 ~ 5천만원
"""

import os
from database import Database
from version import VERSION

print(f"[strategy.py] V{VERSION} 로드됨")

# 시드머니 범위
MIN_SEED = 500000      # 50만원
MAX_SEED = 50000000    # 5천만원
MIN_BUY_AMOUNT = 10000  # 최소 매수금 1만원

# 무매 4.0 설정
SPLIT = 40
STEP = 1.0
PROFIT_TARGET = 0.15  # 15% 익절


class MumaeStrategy:

    def __init__(self, api, ticker: str):
        self.api    = api
        self.ticker = ticker
        self.db     = Database()

        # 미체결 주문
        self.open_buy_id  = None
        self.open_sell_id = None

        self._load_state()

    def _load_state(self):
        """상태 로드 또는 초기화"""
        state = self.db.get_state(self.ticker)
        if state:
            self.seed           = state["seed"]
            self.remaining_cash = state["remaining_cash"]
            self.avg_price      = state["avg_price"]
            self.total_units    = state["total_units"]
            self.buy_count      = state["buy_count"]
            self.first_buy_done = state["first_buy_done"]
        else:
            # 초기 설정
            seed_key = f"SEED_{self.ticker}"
            self.seed = int(os.getenv(seed_key, "530000"))
            
            # 시드 범위 검증
            if self.seed < MIN_SEED or self.seed > MAX_SEED:
                raise ValueError(
                    f"시드머니는 {MIN_SEED:,}원 ~ {MAX_SEED:,}원 사이여야 합니다. "
                    f"현재: {self.seed:,}원"
                )
            
            self.remaining_cash = self.seed
            self.avg_price      = 0.0
            self.total_units    = 0.0
            self.buy_count      = 0.0
            self.first_buy_done = 0
            self._save_state()

    def _save_state(self):
        """상태 저장"""
        self.db.save_state(self.ticker, {
            "seed":           self.seed,
            "remaining_cash": self.remaining_cash,
            "avg_price":      self.avg_price,
            "total_units":    self.total_units,
            "buy_count":      self.buy_count,
            "first_buy_done": self.first_buy_done,
        })

    @property
    def T(self):
        """현재 회차"""
        return self.buy_count

    def star_pct(self):
        """별% = 20 - STEP × T"""
        return 20 - STEP * self.T

    def star_point(self):
        """별지점 = 평단 × (1 + 별%/100)"""
        if self.avg_price == 0:
            return 0
        return self.avg_price * (1 + self.star_pct() / 100)

    def get_buy_budget(self):
        """1회 매수금 = 잔금 / (분할수 - T)"""
        divisor = max(1, SPLIT - self.T)
        return self.remaining_cash / divisor

    def is_first_half(self):
        """전반전 여부"""
        return self.T < (SPLIT / 2)

    # 첫 매수 (자동 진입)
    def auto_first_buy(self):
        """
        첫 매수 시장가 자동 진입
        - 최소 1만원
        - 시드 / 40
        """
        if self.first_buy_done:
            return None, "이미 첫 매수 완료"

        price = self.api.get_price(self.ticker)
        if not price:
            return None, "가격 조회 실패"

        # 첫 매수 금액
        amount = max(MIN_BUY_AMOUNT, self.seed / SPLIT)
        amount = min(amount, self.remaining_cash)

        if amount < MIN_BUY_AMOUNT:
            return None, f"잔금 부족 (최소 {MIN_BUY_AMOUNT:,}원 필요)"

        # 시장가 매수
        result = self.api.buy_market(self.ticker, int(amount))

        if result.get("status") != "0000":
            return None, f"매수 실패: {result.get('message')}"

        # 체결 확인 (시장가는 즉시 체결)
        units = round(amount / price, 10)

        # 상태 업데이트
        self.avg_price      = price
        self.total_units    = units
        self.buy_count      = amount / (self.seed / SPLIT)
        self.remaining_cash = self.seed - amount
        self.first_buy_done = 1
        self._save_state()

        # 거래 로그
        self.db.log_trade(self.ticker, "BUY", price, units, amount)

        return result, (
            f"✅ [{self.ticker}] 첫 매수 완료! (V{VERSION})\n"
            f"  방식: 시장가 자동 진입\n"
            f"  체결가: {price:,.0f}원\n"
            f"  수량: {units:.10f}개\n"
            f"  금액: {amount:,.0f}원\n"
            f"  T값: {self.T:.4f}\n"
            f"  평단: {self.avg_price:,.0f}원\n"
            f"  잔금: {self.remaining_cash:,.0f}원\n"
            f"  다음 매수금: {self.get_buy_budget():,.0f}원\n"
            f"  별지점: {self.star_point():,.0f}원"
        )

    # 구간 판단
    def get_zone(self):
        """매수/매도 구간 판단"""
        if not self.first_buy_done:
            return "FIRST", "첫 매수 필요"

        if self.T >= (SPLIT - 1):
            return "FULL", f"분할 소진 (T={self.T:.2f})"

        price = self.api.get_price(self.ticker)
        if not price:
            return "WAIT", "가격 조회 실패"

        sp = self.star_point()

        if price < sp:
            return "BUY", (
                f"💎 매수 구간\n"
                f"  별지점: {sp:,.0f}원\n"
                f"  현재가: {price:,.0f}원\n"
                f"  별%: {self.star_pct():+.1f}%  T={self.T:.2f}"
            )
        else:
            # 익절 조건 확인
            profit_line = self.avg_price * (1 + PROFIT_TARGET)
            if price > profit_line:
                return "SELL", (
                    f"📈 매도 구간 (익절)\n"
                    f"  별지점: {sp:,.0f}원\n"
                    f"  현재가: {price:,.0f}원\n"
                    f"  익절선: {profit_line:,.0f}원\n"
                    f"  T={self.T:.2f}"
                )
            else:
                return "WAIT", "별지점 위 대기"

    # 매수 주문
    def place_buy_order(self):
        """지정가 매수"""
        sp = self.star_point()
        budget = max(MIN_BUY_AMOUNT, self.get_buy_budget())

        if budget < MIN_BUY_AMOUNT:
            return None, "잔금 부족"

        buy_price = round(sp - 1)
        units = round(budget / buy_price, 10)

        result = self.api.buy_limit(self.ticker, buy_price, units)

        if result.get("status") == "0000":
            self.open_buy_id = result.get("data", {}).get("order_id")
            return result, (
                f"🔵 [{self.ticker}] 지정가 매수 등록\n"
                f"  가격: {buy_price:,.0f}원\n"
                f"  수량: {units:.10f}개\n"
                f"  금액: {budget:,.0f}원\n"
                f"  T={self.T:.2f}"
            )

        return None, "매수 주문 실패"

    # 매도 주문
    def place_sell_order(self):
        """지정가 매도 (전량)"""
        if self.total_units == 0:
            return None, "보유 수량 없음"

        sp = self.star_point()
        profit_line = round(self.avg_price * (1 + PROFIT_TARGET))

        result = self.api.sell_limit(self.ticker, profit_line, self.total_units)

        if result.get("status") == "0000":
            self.open_sell_id = result.get("data", {}).get("order_id")
            return result, (
                f"🔴 [{self.ticker}] 지정가 매도 등록\n"
                f"  가격: {profit_line:,.0f}원\n"
                f"  수량: {self.total_units:.10f}개\n"
                f"  T={self.T:.2f}"
            )

        return None, "매도 주문 실패"

    # 체결 확인
    def check_orders_filled(self):
        """주문 체결 확인"""
        # 매수 체결
        if self.open_buy_id:
            detail = self.api.get_order_detail(self.ticker, self.open_buy_id)
            if detail and detail.get("order_status") == "Completed":
                price  = float(detail.get("price", 0))
                units  = float(detail.get("units_traded", 0))
                amount = int(price * units)

                # 평단 업데이트
                total_cost = self.avg_price * self.total_units + amount
                self.total_units += units
                self.avg_price = total_cost / self.total_units

                # T값 업데이트
                expected = self.seed / SPLIT
                self.buy_count += amount / expected

                self.remaining_cash -= amount
                self._save_state()

                self.db.log_trade(self.ticker, "BUY", price, units, amount)

                self.open_buy_id = None

                return "BUY_FILLED", (
                    f"✅ [{self.ticker}] 매수 체결!\n"
                    f"  가격: {price:,.0f}원\n"
                    f"  수량: {units:.10f}개\n"
                    f"  T={self.T:.4f}\n"
                    f"  평단: {self.avg_price:,.0f}원"
                )

        # 매도 체결
        if self.open_sell_id:
            detail = self.api.get_order_detail(self.ticker, self.open_sell_id)
            if detail and detail.get("order_status") == "Completed":
                price  = float(detail.get("price", 0))
                units  = float(detail.get("units_traded", 0))
                amount = int(price * units)
                profit = round(amount - (self.avg_price * units))

                self.db.log_trade(self.ticker, "SELL", price, units, amount)
                self.db.log_graduation(self.ticker, profit, self.buy_count)

                msg = (
                    f"🎓 [{self.ticker}] 졸업!\n"
                    f"  매도가: {price:,.0f}원\n"
                    f"  수량: {units:.10f}개\n"
                    f"  손익: {profit:+,}원\n"
                    f"  T값: {self.T:.2f}"
                )

                # 리셋
                self.total_units    = 0.0
                self.avg_price      = 0.0
                self.buy_count      = 0.0
                self.remaining_cash = self.seed
                self.first_buy_done = 0
                self._save_state()

                self.open_sell_id = None

                return "SELL_FILLED", msg

        return None, None

    # 상태 텍스트
    def get_status_text(self):
        """현재 상태"""
        price = self.api.get_price(self.ticker) or 0
        sp = self.star_point()

        if not self.first_buy_done:
            return (
                f"💎 [{self.ticker}] 새 출발\n"
                f"  시드: {self.seed:,}원\n"
                f"  현재가: {price:,.0f}원\n"
                f"  상태: 첫 매수 대기 중"
            )

        pnl_pct = ((price - self.avg_price) / self.avg_price * 100
                   if self.avg_price > 0 else 0)
        pnl_krw = round((price - self.avg_price) * self.total_units)

        return (
            f"💎 [{self.ticker}] {SPLIT}분할\n"
            f"  진행: T={self.T:.2f}/{SPLIT}\n"
            f"  시드: {self.seed:,}원\n"
            f"  잔금: {self.remaining_cash:,.0f}원\n"
            f"  현재가: {price:,.0f}원\n"
            f"  평단: {self.avg_price:,.0f}원 ({self.total_units:.10f}개)\n"
            f"  별지점: {sp:,.0f}원 (별% {self.star_pct():+.1f}%)\n"
            f"  수익: {pnl_pct:+.2f}% ({pnl_krw:+,}원)"
        )
