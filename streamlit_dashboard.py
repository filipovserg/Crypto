import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from google.oauth2 import service_account
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.auth.transport.requests import Request
from datetime import datetime
import requests
import json

DB_PATH = "crypto_data.db"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1E7ohaRHZfNvHHM9pFrQUW0W_T0ESTmoH6BL1SGG2Kds/edit"
SHEET_NAME = "SMC Signals"
TELEGRAM_TOKEN = "8220944553:AAE8cJhbGdLk95Uo7uHfJFfRXmQZRK5Vuo8"
CHAT_ID = "248171610"

st.set_page_config(layout="wide")
st.title("📊 Crypto SMC Dashboard")

if "gcp_service_account" not in st.secrets:
    st.error("❌ gcp_service_account не знайдено в secrets")
else:
    st.success("🔑 Ключ Google знайдено!")

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

def get_signals():
    creds_dict = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ])
    client = gspread.authorize(credentials)
    sheet = client.open_by_url(GOOGLE_SHEET_URL).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def append_signal_to_sheet(new_signal):
    creds_dict = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ])
    client = gspread.authorize(credentials)
    sheet = client.open_by_url(GOOGLE_SHEET_URL).worksheet(SHEET_NAME)
    df = get_as_dataframe(sheet, evaluate_formulas=True).dropna(how='all')
    updated_df = pd.concat([df, pd.DataFrame([new_signal])], ignore_index=True)
    sheet.clear()
    set_with_dataframe(sheet, updated_df)

def send_signal_to_telegram(signal):
    msg = f"📉 {signal['Symbol']} {signal['Direction']} {signal['Leverage']}\n\n"
    msg += f"📣 Точка входу: {signal['Entry Zone']}\n"
    msg += f"✅ Тейк-профіт: {signal['Take Profit']}\n"
    msg += f"🤚 Стоп-лосс: {signal['Stop Loss']}\n\n"
    msg += f"✍️ {signal['Notes']}"

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        response = requests.post(url, data=payload)
        return response.status_code == 200
    except Exception as e:
        return False

def check_for_smc_conditions(df, symbol):
    if df.empty:
        return None
    latest = df.iloc[-1]
    if latest['rsi'] < 30 and latest['total_volume'] > df['total_volume'].rolling(20).mean().iloc[-1] * 1.5:
        return {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Symbol": symbol,
            "Direction": "Long",
            "Leverage": "20x",
            "Entry Zone": f"{latest['close'] * 0.98:.3f} - {latest['close']:.3f}",
            "Take Profit": f"{latest['close'] * 1.01:.3f}, {latest['close'] * 1.03:.3f}, {latest['close'] * 1.05:.3f}",
            "Stop Loss": f"{latest['close'] * 0.965:.3f}",
            "HTF Context": "RSI + Whale Spike",
            "LTF Confirmation": "Auto Signal",
            "Liquidity Target": "Mean Reversion",
            "Notes": "Автоматичний сигнал: RSI < 30 та spike по whale volume"
        }
    return None

symbols = ["SOL", "ETH", "XRP", "RNDR"]
selected_symbol = st.sidebar.selectbox("Вибери монету", symbols)

if st.sidebar.button("🔁 Ручний запуск перевірки"):
    df = get_combined_data(selected_symbol)
    auto_signal = check_for_smc_conditions(df, selected_symbol)
    if auto_signal:
        append_signal_to_sheet(auto_signal)
        if send_signal_to_telegram(auto_signal):
            st.success("📬 Авто-сигнал надіслано в Telegram і додано до таблиці!")
        else:
            st.error("❌ Не вдалося надіслати авто-сигнал у Telegram")
    else:
        st.info("ℹ️ Умови SMC не виконані — сигнал не сформовано")

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
