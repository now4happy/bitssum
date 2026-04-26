"""
bithumb_api.py
빗썸 REST API 래퍼 — V4.1.0
- 공개: 현재가, 호가창
- 개인: 잔고, 시장가매수, 지정가매수, 지정가매도, 주문취소, 미체결조회, 체결내역
"""

import hashlib
import hmac
import time
import requests
import urllib.parse
import os
from dotenv import load_dotenv
from version import VERSION

load_dotenv()

print(f"[bithumb_api.py] V{VERSION} 로드됨")


class BithumbAPI:
    BASE_URL = "https://api.bithumb.com"

    def __init__(self):
        self.api_key    = os.getenv("BITHUMB_API_KEY")
        self.secret_key = os.getenv("BITHUMB_SECRET")

    # ── 서명 / 공통 요청 ──────────────────────────────

    def _nonce(self):
        return str(int(time.time() * 1000))

    def _sign(self, endpoint, params, nonce):
        query = urllib.parse.urlencode(params)
        msg   = f"{endpoint}\x00{query}\x00{nonce}"
        return hmac.new(
            self.secret_key.encode("utf-8"),
            msg.encode("utf-8"),
            hashlib.sha512
        ).hexdigest()

    def _private(self, endpoint, params: dict):
        """인증이 필요한 POST 요청"""
        params["endpoint"] = endpoint
        nonce  = self._nonce()
        sig    = self._sign(endpoint, params, nonce)
        headers = {
            "Api-Key":     self.api_key,
            "Api-Sign":    sig,
            "Api-Nonce":   nonce,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        try:
            r = requests.post(
                self.BASE_URL + endpoint,
                data=params,
                headers=headers,
                timeout=10,
            )
            return r.json()
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    # ── 공개 API ──────────────────────────────────────

    def get_price(self, ticker="BTC") -> float | None:
        """현재가 (closing_price)"""
        try:
            r = requests.get(
                f"{self.BASE_URL}/public/ticker/{ticker}_KRW",
                timeout=5,
            )
            d = r.json()
            if d.get("status") == "0000":
                return float(d["data"]["closing_price"])
        except Exception:
            pass
        return None

    def get_orderbook(self, ticker="BTC") -> dict:
        """호가창"""
        try:
            r = requests.get(
                f"{self.BASE_URL}/public/orderbook/{ticker}_KRW",
                timeout=5,
            )
            return r.json()
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    # ── 잔고 ──────────────────────────────────────────

    def get_balance(self, currency="BTC") -> dict | None:
        """
        반환:
          available_krw  : 주문 가능 KRW
          available_coin : 주문 가능 코인 수량
          total_krw      : 보유 KRW 합계
          total_coin     : 보유 코인 합계
        """
        result = self._private("/info/balance", {"currency": currency})
        if result.get("status") == "0000":
            d = result["data"]
            key = currency.lower()
            return {
                "available_krw":  float(d.get("available_krw",  0)),
                "available_coin": float(d.get(f"available_{key}", 0)),
                "total_krw":      float(d.get("total_krw",       0)),
                "total_coin":     float(d.get(f"total_{key}",    0)),
            }
        return None

    # ── 시장가 주문 ────────────────────────────────────

    def buy_market(self, ticker: str, amount_krw: int) -> dict:
        """시장가 매수 (KRW 금액 기준)"""
        return self._private("/trade/market_buy", {
            "order_currency":   ticker,
            "payment_currency": "KRW",
            "units":            str(amount_krw),
        })

    def sell_market(self, ticker: str, units: float) -> dict:
        """시장가 매도 (코인 수량 기준)"""
        return self._private("/trade/market_sell", {
            "order_currency":   ticker,
            "payment_currency": "KRW",
            "units":            str(round(units, 6)),
        })

    # ── 지정가 주문 ────────────────────────────────────

    def buy_limit(self, ticker: str, price: int, units: float) -> dict:
        """
        지정가 매수
        price : 매수 희망가 (원화, 정수)
        units : 매수 수량 (BTC/ETH 소수점 6자리)
        """
        return self._private("/trade/place", {
            "order_currency":   ticker,
            "payment_currency": "KRW",
            "units":            str(round(units, 6)),
            "price":            str(int(price)),
            "type":             "bid",          # bid = 매수
        })

    def sell_limit(self, ticker: str, price: int, units: float) -> dict:
        """
        지정가 매도
        price : 매도 희망가 (원화, 정수)
        units : 매도 수량
        """
        return self._private("/trade/place", {
            "order_currency":   ticker,
            "payment_currency": "KRW",
            "units":            str(round(units, 6)),
            "price":            str(int(price)),
            "type":             "ask",          # ask = 매도
        })

    # ── 주문 관리 ─────────────────────────────────────

    def cancel_order(self, ticker: str, order_id: str, side: str = "bid") -> dict:
        """
        주문 취소
        side: "bid" (매수) | "ask" (매도)
        """
        return self._private("/trade/cancel", {
            "order_currency":   ticker,
            "payment_currency": "KRW",
            "order_id":         order_id,
            "type":             side,
        })

    def get_open_orders(self, ticker: str, side: str = "bid", count: int = 10) -> list:
        """
        미체결 주문 조회
        반환: [{"order_id", "price", "units", "type", "order_date"}, ...]
        """
        result = self._private("/info/orders", {
            "order_currency":   ticker,
            "payment_currency": "KRW",
            "type":             side,
            "count":            count,
        })
        if result.get("status") == "0000":
            return result.get("data", [])
        return []

    def get_order_detail(self, ticker: str, order_id: str) -> dict | None:
        """주문 상세 조회 — 체결 여부 확인"""
        result = self._private("/info/order_detail", {
            "order_currency":   ticker,
            "payment_currency": "KRW",
            "order_id":         order_id,
        })
        if result.get("status") == "0000":
            return result.get("data")
        return None

    def get_trade_history(self, ticker: str, count: int = 20) -> list:
        """체결 내역 조회"""
        result = self._private("/info/user_transactions", {
            "order_currency":   ticker,
            "payment_currency": "KRW",
            "count":            count,
        })
        if result.get("status") == "0000":
            return result.get("data", {}).get("data", [])
        return []
