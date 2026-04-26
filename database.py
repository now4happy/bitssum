"""
database.py
거래 내역, 상태, 졸업 기록을 SQLite에 저장 — V4.1.0
"""

import sqlite3
import os
import json
from datetime import datetime
from version import VERSION

print(f"[database.py] V{VERSION} 로드됨")

DB_PATH = os.path.join(os.path.dirname(__file__), "mumae.db")


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        c = self.conn.cursor()

        # 현재 전략 상태
        c.execute("""
            CREATE TABLE IF NOT EXISTS state (
                ticker TEXT PRIMARY KEY,
                seed INTEGER,
                remaining_cash REAL,
                avg_price REAL,
                total_units REAL,
                buy_count REAL,
                stage INTEGER,
                split INTEGER,
                mode TEXT,
                price_history TEXT,
                updated_at TEXT
            )
        """)

        # 거래 내역
        c.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                side TEXT,
                price REAL,
                units REAL,
                amount_krw REAL,
                created_at TEXT
            )
        """)

        # 졸업(익절) 명예의 전당
        c.execute("""
            CREATE TABLE IF NOT EXISTS graduation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                profit_krw INTEGER,
                buy_count REAL,
                stage INTEGER,
                graduated_at TEXT
            )
        """)

        self.conn.commit()

    # ── 상태 관리 ──────────────────────────────────────

    def get_state(self, ticker):
        c = self.conn.cursor()
        c.execute("SELECT * FROM state WHERE ticker=?", (ticker,))
        row = c.fetchone()
        if row:
            price_hist = json.loads(row[9]) if row[9] else []
            return {
                "ticker":         row[0],
                "seed":           row[1],
                "remaining_cash": row[2],
                "avg_price":      row[3],
                "total_units":    row[4],
                "buy_count":      row[5],
                "stage":          row[6],
                "split":          row[7],
                "mode":           row[8] or "NORMAL",
                "price_history":  price_hist,
            }
        return None

    def save_state(self, ticker, data):
        c = self.conn.cursor()
        price_hist_json = json.dumps(data.get("price_history", []))
        c.execute("""
            INSERT OR REPLACE INTO state
            (ticker, seed, remaining_cash, avg_price, total_units, buy_count, stage, split, mode, price_history, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker,
            data["seed"],
            data.get("remaining_cash", data["seed"]),
            data["avg_price"],
            data["total_units"],
            data["buy_count"],
            data["stage"],
            data.get("split", 40),
            data.get("mode", "NORMAL"),
            price_hist_json,
            datetime.now().isoformat()
        ))
        self.conn.commit()

    def update_seed(self, ticker, new_seed):
        c = self.conn.cursor()
        c.execute("UPDATE state SET seed=? WHERE ticker=?", (new_seed, ticker))
        self.conn.commit()

    # ── 거래 로그 ──────────────────────────────────────

    def log_trade(self, ticker, side, price, units, amount_krw):
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO trades (ticker, side, price, units, amount_krw, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ticker, side, price, units, amount_krw, datetime.now().isoformat()))
        self.conn.commit()

    def get_trades(self, ticker, limit=20):
        c = self.conn.cursor()
        c.execute("""
            SELECT side, price, units, amount_krw, created_at
            FROM trades WHERE ticker=?
            ORDER BY created_at DESC LIMIT ?
        """, (ticker, limit))
        return c.fetchall()

    # ── 졸업 기록 ──────────────────────────────────────

    def log_graduation(self, ticker, profit_krw, buy_count):
        state = self.get_state(ticker)
        stage = state["stage"] if state else 1
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO graduation (ticker, profit_krw, buy_count, stage, graduated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (ticker, profit_krw, buy_count, stage, datetime.now().isoformat()))
        self.conn.commit()

    def get_graduation_history(self, limit=10):
        c = self.conn.cursor()
        c.execute("""
            SELECT ticker, profit_krw, buy_count, stage, graduated_at
            FROM graduation ORDER BY graduated_at DESC LIMIT ?
        """, (limit,))
        return c.fetchall()

    def get_total_profit(self):
        c = self.conn.cursor()
        c.execute("SELECT SUM(profit_krw) FROM graduation")
        row = c.fetchone()
        return row[0] or 0
