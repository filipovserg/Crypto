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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO indicators (timestamp, symbol, rsi) VALUES ('2025-08-12 13:00:00', 'SOL', 25)")
    cursor.execute("INSERT INTO whales (timestamp, symbol, total_volume) VALUES ('2025-08-12 13:00:00', 'SOL', 500000)")
    cursor.execute("INSERT INTO prices (timestamp, symbol, close) VALUES ('2025-08-12 13:00:00', 'SOL', 160)")
    conn.commit()
    conn.close()
    st.success("✅ Тестові дані додано в базу!")
