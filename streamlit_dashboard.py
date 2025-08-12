import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from google.oauth2 import service_account
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from datetime import datetime
import requests

DB_PATH = "crypto_data.db"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1E7ohaRHZfNvHHM9pFrQUW0W_T0ESTmoH6BL1SGG2Kds/edit"
SHEET_NAME = "SMC Signals"
TELEGRAM_TOKEN = "8220944553:AAE8cJhbGdLk95Uo7uHfJFfRXmQZRK5Vuo8"
CHAT_ID = "248171610"

st.set_page_config(layout="wide")
st.title("📊 Crypto SMC Dashboard")

def get_combined_data(symbol):
    conn = sqlite3.connect(DB_PATH)
    rsi = pd.read_sql_query(f"SELECT timestamp, rsi FROM indicators WHERE symbol='{symbol}'", conn)
    whales = pd.read_sql_query(f"SELECT timestamp, total_volume FROM whales WHERE symbol='{symbol}'", conn)
    prices = pd.read_sql_query(f"SELECT timestamp, close FROM prices WHERE symbol='{symbol}'", conn)
    conn.close()
    df = pd.merge(rsi, whales, on="timestamp")
    df = pd.merge(df, prices, on="timestamp")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp")

# Тестова кнопка для вставки даних
if st.sidebar.button("🧪 Додати тестові дані SOL"):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # уникаємо дубля timestamp
        # Використовуємо INSERT OR IGNORE, щоб не падати на унікальних ключах
        cursor.execute("INSERT OR IGNORE INTO indicators (timestamp, symbol, rsi) VALUES (?, ?, ?)", (ts, 'SOL', 25))
        cursor.execute("INSERT OR IGNORE INTO whales (timestamp, symbol, total_volume) VALUES (?, ?, ?)", (ts, 'SOL', 500000))
        cursor.execute("INSERT OR IGNORE INTO prices (timestamp, symbol, close) VALUES (?, ?, ?)", (ts, 'SOL', 160))
        conn.commit()
        st.success(f"✅ Тестові дані додано в базу! timestamp={ts}")
    except sqlite3.IntegrityError as e:
        st.warning("⚠️ Дані з таким (timestamp, symbol) вже існують. Додаю з новим timestamp.")
    except Exception as e:
        st.error(f"❌ Помилка вставки: {e}")
    finally:
        try:
            conn.close()
        except:
            pass
