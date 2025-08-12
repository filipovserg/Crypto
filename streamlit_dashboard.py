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


def check_smc_conditions(df):
    if len(df) < 20:
        return None

    latest = df.iloc[-1]
    rsi = latest["rsi"]
    volume = latest["total_volume"]
    price = latest["close"]
    avg_volume = df["total_volume"].tail(20).mean()

    rsi_cond = rsi < 30 or rsi > 70
    volume_cond = volume > avg_volume * 1.5
    recent_lows = df["close"].tail(20).min()
    recent_highs = df["close"].tail(20).max()
    support_break = price < recent_lows * 0.995
    resistance_break = price > recent_highs * 1.005

    if rsi_cond and volume_cond and (support_break or resistance_break):
        direction = "Short" if rsi > 70 else "Long"
        atr = df["close"].tail(14).std() * 1.5
        tp = f"{price + (-1 if direction == 'Short' else 1) * atr:.3f}"
        sl = f"{price - (-1 if direction == 'Short' else 1) * atr:.3f}"
        signal = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Symbol": selected_symbol,
            "Direction": direction,
            "Leverage": "25x",
            "Entry Zone": f"{price:.3f}",
            "Take Profit": tp,
            "Stop Loss": sl,
            "HTF Context": "RSI + Whale Vol + Breakout",
            "LTF Confirmation": "",
            "Liquidity Target": "",
            "Notes": f"Автоформований SMC сигнал. RSI: {rsi:.1f}, Whale vol: {volume:.0f}, Ціна: {price:.3f}"
        }
        return signal
    return None


symbols = ["SOL", "ETH", "XRP", "BTC", "GRT", "RENDER", "ICP", "SUI", "APT", "INJ"]
selected_symbol = st.sidebar.selectbox("Вибери монету", symbols)

INSERT INTO indicators (timestamp, symbol, rsi) VALUES ('2025-08-12 13:00:00', 'SOL', 25);
INSERT INTO whales (timestamp, symbol, total_volume) VALUES ('2025-08-12 13:00:00', 'SOL', 500000);
INSERT INTO prices (timestamp, symbol, close) VALUES ('2025-08-12 13:00:00', 'SOL', 160);

if st.sidebar.button("🔁 Ручний запуск перевірки"):
    df_check = get_combined_data(selected_symbol)
    signal = check_smc_conditions(df_check)
    if signal:
        append_signal_to_sheet(signal)
        if send_signal_to_telegram(signal):
            st.success("📬 Сигнал сформовано, надіслано в Telegram і додано до таблиці!")
        else:
            st.warning("⚠️ Сигнал збережено, але Telegram не спрацював")
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
