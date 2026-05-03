"""
database.py
거래 내역 및 상태 관리 — V5.0
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
                first_buy_done INTEGER DEFAULT 0,
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

        # 졸업 기록
        c.execute("""
            CREATE TABLE IF NOT EXISTS graduation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                profit_krw INTEGER,
                buy_count REAL,
                graduated_at TEXT
            )
        """)

        self.conn.commit()

    # 상태 관리
    def get_state(self, ticker):
        c = self.conn.cursor()
        c.execute("SELECT * FROM state WHERE ticker=?", (ticker,))
        row = c.fetchone()
        if row:
            return {
                "ticker":         row[0],
                "seed":           row[1],
                "remaining_cash": row[2],
                "avg_price":      row[3],
                "total_units":    row[4],
                "buy_count":      row[5],
                "first_buy_done": row[6],
            }
        return None

    def save_state(self, ticker, data):
        c = self.conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO state
            (ticker, seed, remaining_cash, avg_price, total_units, buy_count, first_buy_done, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker,
            data["seed"],
            data.get("remaining_cash", data["seed"]),
            data["avg_price"],
            data["total_units"],
            data["buy_count"],
            data.get("first_buy_done", 0),
            datetime.now().isoformat()
        ))
        self.conn.commit()

    def update_seed(self, ticker, new_seed):
        c = self.conn.cursor()
        c.execute("UPDATE state SET seed=? WHERE ticker=?", (new_seed, ticker))
        self.conn.commit()

    # 거래 로그
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

    # 졸업 기록
    def log_graduation(self, ticker, profit_krw, buy_count):
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO graduation (ticker, profit_krw, buy_count, graduated_at)
            VALUES (?, ?, ?, ?)
        """, (ticker, profit_krw, buy_count, datetime.now().isoformat()))
        self.conn.commit()

    def get_graduation_history(self, limit=10):
        c = self.conn.cursor()
        c.execute("""
            SELECT ticker, profit_krw, buy_count, graduated_at
            FROM graduation ORDER BY graduated_at DESC LIMIT ?
        """, (limit,))
        return c.fetchall()

    def get_total_profit(self):
        c = self.conn.cursor()
        c.execute("SELECT SUM(profit_krw) FROM graduation")
        row = c.fetchone()
        return row[0] or 0
