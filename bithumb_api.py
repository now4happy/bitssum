"""
bithumb_api.py
빗썸 REST API 래퍼 — V5.0
소수점 10자리 지원
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

    # 공개 API
    def get_price(self, ticker="BTC") -> float | None:
        """현재가"""
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

    # 잔고
    def get_balance(self, currency="BTC") -> dict | None:
        """잔고 조회"""
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

    # 시장가 주문
    def buy_market(self, ticker: str, amount_krw: int) -> dict:
        """시장가 매수 (KRW 금액)"""
        return self._private("/trade/market_buy", {
            "order_currency":   ticker,
            "payment_currency": "KRW",
            "units":            str(amount_krw),
        })

    def sell_market(self, ticker: str, units: float) -> dict:
        """시장가 매도 (코인 수량) - 소수점 10자리"""
        return self._private("/trade/market_sell", {
            "order_currency":   ticker,
            "payment_currency": "KRW",
            "units":            str(round(units, 10)),
        })

    # 지정가 주문
    def buy_limit(self, ticker: str, price: int, units: float) -> dict:
        """지정가 매수 - 소수점 10자리"""
        return self._private("/trade/place", {
            "order_currency":   ticker,
            "payment_currency": "KRW",
            "units":            str(round(units, 10)),
            "price":            str(int(price)),
            "type":             "bid",
        })

    def sell_limit(self, ticker: str, price: int, units: float) -> dict:
        """지정가 매도 - 소수점 10자리"""
        return self._private("/trade/place", {
            "order_currency":   ticker,
            "payment_currency": "KRW",
            "units":            str(round(units, 10)),
            "price":            str(int(price)),
            "type":             "ask",
        })

    # 주문 관리
    def cancel_order(self, ticker: str, order_id: str, side: str = "bid") -> dict:
        """주문 취소"""
        return self._private("/trade/cancel", {
            "order_currency":   ticker,
            "payment_currency": "KRW",
            "order_id":         order_id,
            "type":             side,
        })

    def get_order_detail(self, ticker: str, order_id: str) -> dict | None:
        """주문 상세 조회"""
        result = self._private("/info/order_detail", {
            "order_currency":   ticker,
            "payment_currency": "KRW",
            "order_id":         order_id,
        })
        if result.get("status") == "0000":
            return result.get("data")
        return None
