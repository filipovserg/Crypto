import streamlit as st
import sqlite3
from datetime import datetime

DB_PATH = "crypto.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS indicators (
        timestamp TEXT,
        symbol TEXT,
        rsi REAL,
        PRIMARY KEY (timestamp, symbol)
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS whales (
        timestamp TEXT,
        symbol TEXT,
        total_volume REAL,
        PRIMARY KEY (timestamp, symbol)
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS prices (
        timestamp TEXT,
        symbol TEXT,
        close REAL,
        PRIMARY KEY (timestamp, symbol)
    )""")
    conn.commit()
    conn.close()
    st.success("Таблиці ініціалізовано!")

def insert_test_data():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO indicators (timestamp, symbol, rsi) VALUES (?, 'SOL', 25)", (now,))
    cursor.execute("INSERT OR IGNORE INTO whales (timestamp, symbol, total_volume) VALUES (?, 'SOL', 500000)", (now,))
    cursor.execute("INSERT OR IGNORE INTO prices (timestamp, symbol, close) VALUES (?, 'SOL', 160)", (now,))
    conn.commit()
    conn.close()
    st.success(f"Тестові дані додано! timestamp={now}")

def delete_last_test_record():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for table in ["indicators", "whales", "prices"]:
        cursor.execute(f"DELETE FROM {table} WHERE timestamp = (SELECT MAX(timestamp) FROM {table})")
    conn.commit()
    conn.close()
    st.warning("Останній тестовий запис видалено!")

st.title("⚡ Управління тестовими даними БД")

if st.button("Ініціалізувати таблиці"):
    init_db()

if st.button("Додати тестові дані"):
    insert_test_data()

if st.button("Видалити останній тестовий запис"):
    delete_last_test_record()
