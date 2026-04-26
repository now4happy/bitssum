"""
strategy.py — 무매 V4.1.0 완전판

━━━ 모드 구분 ━━━
일반모드 (NORMAL):  T < (분할수 - 1)
  - 전반전: T < 분할수/2  (별% > 0, 익절)
  - 후반전: T ≥ 분할수/2  (별% < 0, 손절)
리버스모드 (REVERSE): T ≥ (분할수 - 1)  (소진)

━━━ T값 = float ━━━
일반모드: 체결금액 / 예정금액
리버스모드:
  - 매도 시: T × 0.95 (40분할) 또는 × 0.9 (20분할)
  - 매수 시: T + (분할수 - T) × 0.25

━━━ 별지점 ━━━
일반모드: 평단 × (1 + 별%/100)
  - 별% = 20 - STEP × T
  - 40분할: STEP = 1.0
  - 20분할: STEP = 2.0
리버스모드: 직전 5거래일 종가 평균

━━━ 매수금 계산 ━━━
일반모드: 잔금 / (분할수 - T)
리버스모드: 잔금 / 4 (쿼터매수)

━━━ V4.1.0 추가 ━━━
- 빗썸 잔고 자동 체크
- 시드머니와 비교
"""

import os
from database import Database
from version import VERSION

print(f"[strategy.py] V{VERSION} 로드됨")

# 분할수 → STEP 매핑
SPLIT_STEP = {
    20: 2.0,     # T=10 → 0%, T=20 → -20%
    40: 1.0,     # T=20 → 0%, T=40 → -20%
}

# 익절 기준
PROFIT_TARGET = 0.15


class MumaeStrategy:

    def __init__(self, api, ticker: str):
        self.api    = api
        self.ticker = ticker
        self.db     = Database()

        # 미체결 주문 추적
        self.open_buy_id     = None
        self.open_sell_id    = None
        self.open_buy_price  = None
        self.open_sell_price = None

        self._load_state()

    # ── 상태 저장/로드 ────────────────────────────────

    def _load_state(self):
        state = self.db.get_state(self.ticker)
        if state:
            self.seed           = state["seed"]
            self.remaining_cash = state["remaining_cash"]
            self.avg_price      = state["avg_price"]
            self.total_units    = state["total_units"]
            self.buy_count      = state["buy_count"]   # float!
            self.stage          = state["stage"]
            self.split          = state.get("split", 40)
            self.mode           = state.get("mode", "NORMAL")
            self.price_history  = state.get("price_history", [])
        else:
            self.seed           = int(os.getenv(f"SEED_{self.ticker}", "500000"))
            self.remaining_cash = self.seed
            self.avg_price      = 0.0
            self.total_units    = 0.0
            self.buy_count      = 0.0   # float
            self.stage          = 1
            self.split          = 40
            self.mode           = "NORMAL"
            self.price_history  = []
            self._save_state()

    def _save_state(self):
        self.db.save_state(self.ticker, {
            "seed":           self.seed,
            "remaining_cash": self.remaining_cash,
            "avg_price":      self.avg_price,
            "total_units":    self.total_units,
            "buy_count":      self.buy_count,
            "stage":          self.stage,
            "split":          self.split,
            "mode":           self.mode,
            "price_history":  self.price_history,
        })

    # ── 핵심 계산 ─────────────────────────────────────

    @property
    def T(self):
        """현재 회차 (float)"""
        return self.buy_count

    @property
    def step(self):
        return SPLIT_STEP.get(self.split, 1.0)

    def star_pct(self, t=None):
        """별% = 20 - STEP × T (일반모드 전용)"""
        t = t if t is not None else self.T
        return 20 - self.step * t

    def star_point_normal(self):
        """일반모드 별지점 = 평단 × (1 + 별%/100)"""
        if self.avg_price == 0:
            return 0
        return round(self.avg_price * (1 + self.star_pct() / 100))

    def star_point_reverse(self):
        """리버스모드 별지점 = 직전 5일 종가 평균"""
        if len(self.price_history) == 0:
            price = self.api.get_price(self.ticker) or 0
            return price
        recent_5 = self.price_history[-5:]
        return round(sum(recent_5) / len(recent_5))

    def get_star_point(self):
        """모드에 따라 별지점 계산"""
        if self.mode == "REVERSE":
            return self.star_point_reverse()
        return self.star_point_normal()

    def get_buy_budget(self):
        """1회 매수금 계산"""
        if self.mode == "REVERSE":
            # 쿼터매수: 잔금 / 4
            return round(self.remaining_cash / 4)
        # 일반모드: 잔금 / (분할수 - T)
        divisor = max(1, self.split - self.T)
        return round(self.remaining_cash / divisor)

    def is_first_half(self):
        """전반전 여부"""
        return self.T < (self.split / 2)

    def is_loss_mode(self):
        """후반전 (손절모드) 여부"""
        return not self.is_first_half() and self.mode == "NORMAL"

    def update_price_history(self):
        """5일 종가 히스토리 업데이트"""
        price = self.api.get_price(self.ticker)
        if price:
            self.price_history.append(price)
            # 최대 10일 보관 (넉넉하게)
            if len(self.price_history) > 10:
                self.price_history = self.price_history[-10:]
            self._save_state()

    # ── 빗썸 잔고 체크 (V4.1.0 신규) ──────────────────

    def check_balance_sync(self):
        """
        빗썸 실제 잔고와 시드머니 비교
        차이가 크면 경고 반환
        """
        balance = self.api.get_balance(self.ticker)
        if not balance:
            return None, "⚠️ 빗썸 API 잔고 조회 실패"

        bithumb_krw  = balance["available_krw"]
        bithumb_coin = balance["available_coin"]
        
        # 시드 vs 실제 잔고 비교
        diff_pct = abs(bithumb_krw - self.remaining_cash) / max(self.seed, 1) * 100

        msg = (
            f"💰 [{self.ticker}] 잔고 확인\n"
            f"  빗썸 잔고: {bithumb_krw:,.0f}원\n"
            f"  봇 잔금:   {self.remaining_cash:,.0f}원\n"
            f"  차이:      {abs(bithumb_krw - self.remaining_cash):,.0f}원 ({diff_pct:.1f}%)\n"
            f"  보유 코인: {bithumb_coin:.6f}개 (봇: {self.total_units:.6f}개)\n"
        )

        if diff_pct > 10:
            msg += f"\n⚠️ 경고: 잔고 차이가 {diff_pct:.1f}%로 10% 초과합니다!"
            return False, msg
        
        return True, msg

    # ── 모드 판단 & 전환 ──────────────────────────────

    def check_mode_transition(self):
        """모드 전환 체크"""
        # 일반모드 → 리버스모드
        if self.mode == "NORMAL" and self.T >= (self.split - 1):
            self.mode = "REVERSE"
            self._save_state()
            return "일반모드 → 리버스모드 전환 (소진 발생)"

        # 리버스모드 → 일반모드
        if self.mode == "REVERSE":
            price = self.api.get_price(self.ticker)
            if price and self.avg_price > 0:
                profit_pct = (price - self.avg_price) / self.avg_price
                if profit_pct > PROFIT_TARGET:
                    self.mode = "NORMAL"
                    self._save_state()
                    return f"리버스모드 → 일반모드 복귀 (익절선 {PROFIT_TARGET*100:.0f}% 돌파)"
        return None

    def get_zone(self):
        """
        구간 판단
        반환: (zone: str, 설명: str)
        """
        if self.T == 0:
            return "NEW", "새출발 — 수동 등록 필요 (/register 사용)"

        price = self.api.get_price(self.ticker)
        if not price:
            return "WAIT", "가격 조회 실패"

        sp = self.get_star_point()

        # 리버스모드
        if self.mode == "REVERSE":
            if price < sp:
                return "BUY", (
                    f"🔄 리버스 매수 구간\n"
                    f"  별지점(5일평균): {sp:,.0f}원\n"
                    f"  현재가: {price:,.0f}원\n"
                    f"  T={self.T:.2f}"
                )
            else:
                return "SELL", (
                    f"🔄 리버스 매도 구간\n"
                    f"  별지점(5일평균): {sp:,.0f}원\n"
                    f"  현재가: {price:,.0f}원\n"
                    f"  T={self.T:.2f}"
                )

        # 일반모드
        sp_pct = self.star_pct()
        diff   = (price - sp) / sp * 100 if sp > 0 else 0

        if price < sp:
            phase = "전반전" if self.is_first_half() else "후반전"
            return "BUY", (
                f"💎 매수 구간 ({phase})\n"
                f"  별지점: {sp:,.0f}원\n"
                f"  현재가: {price:,.0f}원  ({diff:+.2f}%)\n"
                f"  별%:    {sp_pct:+.2f}%  T={self.T:.2f}"
            )
        else:
            label = "🔻 손절 구간" if self.is_loss_mode() else "📈 매도 구간"
            phase = "전반전" if self.is_first_half() else "후반전"
            return "SELL", (
                f"{label} ({phase})\n"
                f"  별지점: {sp:,.0f}원\n"
                f"  현재가: {price:,.0f}원  ({diff:+.2f}%)\n"
                f"  별%:    {sp_pct:+.2f}%  T={self.T:.2f}"
            )

    # ── 수동 등록 (1차 매수) ──────────────────────────

    def register_first_buy(self, price: float, units: float, amount_krw: int):
        """
        사용자가 직접 1차 매수 후 등록
        T값 = 실제 사용금액 / 예정 매수금
        """
        expected_budget = round(self.seed / self.split)
        t_value = amount_krw / expected_budget

        self.avg_price      = price
        self.total_units    = units
        self.buy_count      = t_value
        self.remaining_cash = self.seed - amount_krw
        self._save_state()
        self.db.log_trade(self.ticker, "BUY", price, units, amount_krw)

        return (
            f"✅ [{self.ticker}] 1차 매수 등록 완료! (V{VERSION})\n"
            f"  체결가:  {price:,.0f}원\n"
            f"  수량:    {units:.6f}개\n"
            f"  사용금:  {amount_krw:,}원\n"
            f"  T값:     {t_value:.4f}\n"
            f"  평단:    {self.avg_price:,.0f}원\n"
            f"  잔금:    {self.remaining_cash:,}원\n"
            f"  다음 매수금: {self.get_buy_budget():,}원\n"
            f"  별지점:  {self.get_star_point():,.0f}원"
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 일반모드 매수/매도
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def place_buy_order_normal(self):
        """
        일반모드 지정가 매수
        - 전반전: 1/2은 별지점-1, 1/2은 평단
        - 후반전: 전액을 별지점-1
        """
        sp     = self.get_star_point()
        budget = self.get_buy_budget()

        if self.is_first_half():
            # 전반전: 절반씩
            buy_at_star = round(sp - 1)
            buy_at_avg  = round(self.avg_price)
            units_star  = round((budget / 2) / buy_at_star, 6)
            units_avg   = round((budget / 2) / buy_at_avg, 6)

            # 별지점 매수
            r1 = self.api.buy_limit(self.ticker, buy_at_star, units_star)
            # 평단 매수
            r2 = self.api.buy_limit(self.ticker, buy_at_avg, units_avg)

            if r1.get("status") == "0000" and r2.get("status") == "0000":
                self.open_buy_id = [
                    r1.get("data", {}).get("order_id"),
                    r2.get("data", {}).get("order_id"),
                ]
                return r1, (
                    f"🔵 [{self.ticker}] 전반전 지정가 매수 등록\n"
                    f"  별지점: {buy_at_star:,.0f}원 × {units_star:.6f}개\n"
                    f"  평단:   {buy_at_avg:,.0f}원 × {units_avg:.6f}개\n"
                    f"  합계:   {budget:,}원\n"
                    f"  T={self.T:.2f}"
                )
        else:
            # 후반전: 전액 별지점
            buy_at_star = round(sp - 1)
            units       = round(budget / buy_at_star, 6)
            result      = self.api.buy_limit(self.ticker, buy_at_star, units)

            if result.get("status") == "0000":
                self.open_buy_id = result.get("data", {}).get("order_id")
                return result, (
                    f"🔵 [{self.ticker}] 후반전 지정가 매수 등록\n"
                    f"  별지점: {buy_at_star:,.0f}원\n"
                    f"  수량:   {units:.6f}개  ({budget:,}원)\n"
                    f"  T={self.T:.2f}"
                )

        return None, "❌ 지정가 매수 실패"

    def place_sell_order_normal(self):
        """
        일반모드 지정가 매도
        - 1/4: 별지점에 LOC (쿼터매도)
        - 3/4: 평단 × 1.15 지정가
        """
        if self.total_units == 0:
            return None, "보유 수량 없음"

        sp          = self.get_star_point()
        quarter     = round(self.total_units / 4, 6)
        three_quarter = round(self.total_units - quarter, 6)
        profit_line = round(self.avg_price * (1 + PROFIT_TARGET))

        # 1/4 별지점
        r1 = self.api.sell_limit(self.ticker, sp, quarter)
        # 3/4 익절선
        r2 = self.api.sell_limit(self.ticker, profit_line, three_quarter)

        if r1.get("status") == "0000" and r2.get("status") == "0000":
            self.open_sell_id = [
                r1.get("data", {}).get("order_id"),
                r2.get("data", {}).get("order_id"),
            ]
            mode = "손절" if self.is_loss_mode() else "익절"
            return r1, (
                f"🔴 [{self.ticker}] 쿼터매도 등록 ({mode})\n"
                f"  별지점:  {sp:,.0f}원 × {quarter:.6f}개 (1/4)\n"
                f"  익절선:  {profit_line:,.0f}원 × {three_quarter:.6f}개 (3/4)\n"
                f"  T={self.T:.2f}"
            )

        return None, "❌ 지정가 매도 실패"

    def on_buy_filled_normal(self, price: float, units: float, amount_krw: int):
        """일반모드 매수 체결 처리"""
        expected_budget = self.get_buy_budget()
        t_delta = amount_krw / expected_budget

        total_cost       = self.avg_price * self.total_units + amount_krw
        self.total_units += units
        self.avg_price    = total_cost / self.total_units
        self.buy_count   += t_delta
        self.remaining_cash -= amount_krw
        self._save_state()
        self.db.log_trade(self.ticker, "BUY", price, units, amount_krw)

    def on_sell_filled_normal(self, price: float, units: float, amount_krw: int):
        """일반모드 매도 체결 처리 — 부분매도 가능"""
        self.total_units    -= units
        self.remaining_cash += amount_krw
        self.db.log_trade(self.ticker, "SELL", price, units, amount_krw)

        # 전량 매도 → 졸업
        if self.total_units < 0.0001:
            profit = round(amount_krw - (self.avg_price * units))
            self.db.log_graduation(self.ticker, profit, self.buy_count)

            msg = (
                f"🎓 [{self.ticker}] 졸업!\n"
                f"  매도가:  {price:,.0f}원\n"
                f"  손익:    {profit:+,}원\n"
                f"  회차:    T={self.buy_count:.2f}/{self.split}\n"
                f"  다음단계: {self.stage+1}무매"
            )

            # 초기화
            self.avg_price      = 0.0
            self.total_units    = 0.0
            self.buy_count      = 0.0
            self.remaining_cash = self.seed
            self.stage         += 1
            self.mode           = "NORMAL"
            self._save_state()
            return msg

        # 부분 매도
        self._save_state()
        return (
            f"✅ [{self.ticker}] 부분 매도 체결\n"
            f"  매도가: {price:,.0f}원\n"
            f"  수량:   {units:.6f}개\n"
            f"  잔여:   {self.total_units:.6f}개"
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 리버스모드 매수/매도
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def place_sell_order_reverse_first(self):
        """리버스 첫날 MOC 무조건 매도"""
        if self.total_units == 0:
            return None, "보유 수량 없음"

        divisor = 20 if self.split == 40 else 10
        units   = round(self.total_units / divisor, 6)
        result  = self.api.sell_market(self.ticker, units)

        if result.get("status") == "0000":
            # T값 갱신: × 0.95 (40분할) or × 0.9 (20분할)
            decay = 0.95 if self.split == 40 else 0.9
            self.buy_count *= decay
            self._save_state()

            return result, (
                f"🔄 [{self.ticker}] 리버스 첫날 무조건 매도\n"
                f"  수량: {units:.6f}개 (보유/{divisor})\n"
                f"  T값 갱신: {self.T:.4f}"
            )

        return None, "❌ 리버스 첫날 매도 실패"

    def place_buy_order_reverse(self):
        """리버스 쿼터매수: 잔금/4를 별지점-1에"""
        sp     = self.get_star_point()
        budget = self.get_buy_budget()
        buy_at = round(sp - 1)
        units  = round(budget / buy_at, 6)
        result = self.api.buy_limit(self.ticker, buy_at, units)

        if result.get("status") == "0000":
            self.open_buy_id = result.get("data", {}).get("order_id")
            return result, (
                f"🔵 [{self.ticker}] 리버스 쿼터매수\n"
                f"  별지점: {buy_at:,.0f}원\n"
                f"  수량:   {units:.6f}개  ({budget:,}원)\n"
                f"  T={self.T:.4f}"
            )

        return None, "❌ 리버스 매수 실패"

    def place_sell_order_reverse(self):
        """리버스 무한매도: 보유/20 (또는 /10)을 별지점에"""
        if self.total_units == 0:
            return None, "보유 수량 없음"

        sp      = self.get_star_point()
        divisor = 20 if self.split == 40 else 10
        units   = round(self.total_units / divisor, 6)
        result  = self.api.sell_limit(self.ticker, sp, units)

        if result.get("status") == "0000":
            self.open_sell_id = result.get("data", {}).get("order_id")
            return result, (
                f"🔴 [{self.ticker}] 리버스 무한매도\n"
                f"  별지점: {sp:,.0f}원\n"
                f"  수량:   {units:.6f}개  (보유/{divisor})\n"
                f"  T={self.T:.4f}"
            )

        return None, "❌ 리버스 매도 실패"

    def on_buy_filled_reverse(self, price: float, units: float, amount_krw: int):
        """리버스 매수 체결: T += (분할수 - T) × 0.25"""
        total_cost       = self.avg_price * self.total_units + amount_krw
        self.total_units += units
        self.avg_price    = total_cost / self.total_units
        self.remaining_cash -= amount_krw

        # T값 갱신
        self.buy_count += (self.split - self.buy_count) * 0.25
        self._save_state()
        self.db.log_trade(self.ticker, "BUY", price, units, amount_krw)

    def on_sell_filled_reverse(self, price: float, units: float, amount_krw: int):
        """리버스 매도 체결: T × 0.95 (또는 × 0.9)"""
        self.total_units    -= units
        self.remaining_cash += amount_krw
        self.db.log_trade(self.ticker, "SELL", price, units, amount_krw)

        # T값 갱신
        decay = 0.95 if self.split == 40 else 0.9
        self.buy_count *= decay
        self._save_state()

        return (
            f"✅ [{self.ticker}] 리버스 매도 체결\n"
            f"  매도가: {price:,.0f}원\n"
            f"  수량:   {units:.6f}개\n"
            f"  T값 갱신: {self.T:.4f}"
        )

    # ── 주문 체결 확인 (통합) ─────────────────────────

    def check_orders_filled(self):
        """미체결 주문 체결 여부 확인"""
        # 매수 체결
        if self.open_buy_id:
            # 리스트인 경우 (전반전 2개)
            if isinstance(self.open_buy_id, list):
                for oid in self.open_buy_id:
                    detail = self.api.get_order_detail(self.ticker, oid)
                    if detail and detail.get("order_status") == "Completed":
                        price  = float(detail.get("price", 0))
                        units  = float(detail.get("units_traded", 0))
                        amount = int(price * units)

                        if self.mode == "REVERSE":
                            self.on_buy_filled_reverse(price, units, amount)
                        else:
                            self.on_buy_filled_normal(price, units, amount)

                        return "BUY_FILLED", (
                            f"✅ [{self.ticker}] 매수 체결!\n"
                            f"  체결가: {price:,.0f}원\n"
                            f"  수량:   {units:.6f}개\n"
                            f"  T={self.T:.4f}"
                        )
            else:
                detail = self.api.get_order_detail(self.ticker, self.open_buy_id)
                if detail and detail.get("order_status") == "Completed":
                    price  = float(detail.get("price", 0))
                    units  = float(detail.get("units_traded", 0))
                    amount = int(price * units)

                    if self.mode == "REVERSE":
                        self.on_buy_filled_reverse(price, units, amount)
                    else:
                        self.on_buy_filled_normal(price, units, amount)

                    return "BUY_FILLED", (
                        f"✅ [{self.ticker}] 매수 체결!\n"
                        f"  체결가: {price:,.0f}원\n"
                        f"  수량:   {units:.6f}개\n"
                        f"  T={self.T:.4f}"
                    )

        # 매도 체결
        if self.open_sell_id:
            # 리스트인 경우 (쿼터매도 2개)
            if isinstance(self.open_sell_id, list):
                for oid in self.open_sell_id:
                    detail = self.api.get_order_detail(self.ticker, oid)
                    if detail and detail.get("order_status") == "Completed":
                        price  = float(detail.get("price", 0))
                        units  = float(detail.get("units_traded", 0))
                        amount = int(price * units)

                        if self.mode == "REVERSE":
                            msg = self.on_sell_filled_reverse(price, units, amount)
                        else:
                            msg = self.on_sell_filled_normal(price, units, amount)

                        return "SELL_FILLED", msg
            else:
                detail = self.api.get_order_detail(self.ticker, self.open_sell_id)
                if detail and detail.get("order_status") == "Completed":
                    price  = float(detail.get("price", 0))
                    units  = float(detail.get("units_traded", 0))
                    amount = int(price * units)

                    if self.mode == "REVERSE":
                        msg = self.on_sell_filled_reverse(price, units, amount)
                    else:
                        msg = self.on_sell_filled_normal(price, units, amount)

                    return "SELL_FILLED", msg

        return None, None

    # ── 설정 ─────────────────────────────────────────

    def set_split(self, split: int) -> bool:
        if split not in SPLIT_STEP:
            return False
        self.split = split
        self._save_state()
        return True

    # ── 상태 텍스트 ───────────────────────────────────

    def get_status_text(self):
        price = self.api.get_price(self.ticker) or 0
        sp    = self.get_star_point()
        pnl_pct = ((price - self.avg_price) / self.avg_price * 100
                   if self.avg_price > 0 else 0)
        pnl_krw = round((price - self.avg_price) * self.total_units
                        if self.avg_price > 0 else 0)

        mode_label = ""
        if self.mode == "REVERSE":
            mode_label = "🔄리버스"
        elif self.is_loss_mode():
            mode_label = "🔻후반전"

        sp_desc = "별지점" if self.mode == "NORMAL" else "별지점(5일평균)"

        return (
            f"💎 [{self.ticker}] {self.stage}무매 {self.split}분할 {mode_label}\n"
            f"  진행:      T={self.T:.2f}/{self.split}\n"
            f"  시드:      {self.seed:,}원\n"
            f"  잔금:      {self.remaining_cash:,}원\n"
            f"  현재가:    {price:,.0f}원\n"
            f"  평단:      {self.avg_price:,.0f}원  ({self.total_units:.6f}개)\n"
            f"  {sp_desc}: {sp:,.0f}원\n"
            f"  수익:      {pnl_pct:+.2f}%  ({pnl_krw:+,}원)\n"
        )

    def get_star_table(self, around: int = 5):
        """별지점 테이블 (일반모드 전용)"""
        if self.mode == "REVERSE":
            return f"[{self.ticker}] 리버스모드 — 별지점은 5일 평균으로 계산됩니다\n"

        if self.avg_price == 0:
            return f"[{self.ticker}] 새출발 전 — 별지점 없음\n"

        lines = [f"📊 [{self.ticker}] 별지점 테이블\n"]
        start = max(0, int(self.T) - 2)
        end   = min(self.split + 1, int(self.T) + around)

        for t in range(start, end):
            sp_pct = self.star_pct(t)
            sp     = round(self.avg_price * (1 + sp_pct / 100))

            if t < self.T:
                icon = "✅"
            elif t == int(self.T):
                icon = "▶️"
            else:
                icon = "⬜"

            mode = " 손절" if sp_pct < 0 else ""
            lines.append(
                f"  {icon} T={t:02d}: {sp:>13,.0f}원  (별% {sp_pct:+.1f}%{mode})"
            )

        return "\n".join(lines)
