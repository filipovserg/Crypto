import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import requests  # 🔄 замість telegram
import json
from collections.abc import Mapping

DB_PATH = "crypto_data.db"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1E7ohaRHZfNvHHM9pFrQUW0W_T0ESTmoH6BL1SGG2Kds/edit"
SHEET_NAME = "SMC Signals"
TELEGRAM_TOKEN = "8220944553:AAE8cJhbGdLk95Uo7uHfJFfRXmQZRK5Vuo8"
CHAT_ID = "248171610"

st.set_page_config(layout="wide")
st.title("📊 Crypto SMC Dashboard")

# DB Access
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

# Google Sheets Access
def get_signals():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(json.dumps(dict(st.secrets["gcp_service_account"])))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(GOOGLE_SHEET_URL).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# Telegram Log via requests
def send_test_telegram_message():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"🔔 Ручний запуск перевірки: {now}"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            st.success("✅ Повідомлення надіслано!")
        else:
            st.error(f"❌ Telegram Error: {response.text}")
    except Exception as e:
        st.error(f"❌ Запит не вдалось відправити: {e}")

symbols = ["SOL", "ETH", "XRP"]
selected_symbol = st.sidebar.selectbox("Вибери монету", symbols)

if st.sidebar.button("🔁 Ручний запуск перевірки"):
    send_test_telegram_message()

try:
    df = get_combined_data(selected_symbol)
except Exception as e:
    st.error(f"❌ Помилка підключення до бази: {e}")
    df = pd.DataFrame()

col1, col2 = st.columns([2, 1])
with col1:
    if not df.empty:
        st.subheader(f"📈 RSI, Whale Volume і Price: {selected_symbol}")
        fig, ax1 = plt.subplots(figsize=(12, 5))
        ax1.plot(df["timestamp"], df["rsi"], label="RSI", color="blue")
        ax1.axhline(30, linestyle="--", color="red", label="RSI=30")
        ax1.axhline(70, linestyle="--", color="green", label="RSI=70")
        ax2 = ax1.twinx()
        ax2.bar(df["timestamp"], df["total_volume"], alpha=0.3, color="gray", label="Whale Vol")
        ax1.set_ylabel("RSI")
        ax2.set_ylabel("Whale Volume")
        fig.tight_layout()
        fig.legend(loc="upper left")
        st.pyplot(fig)

        st.line_chart(df.set_index("timestamp")["close"], use_container_width=True, height=200)
    else:
        st.info("📭 Немає даних для відображення")

with col2:
    st.subheader("🧾 Останні SMC сигнали")
    try:
        df_signals = get_signals()
        df_filtered = df_signals[df_signals["Symbol"] == selected_symbol]
        st.dataframe(df_filtered.tail(10), use_container_width=True)
    except Exception as e:
        st.error(f"Помилка завантаження сигналів: {e}")
