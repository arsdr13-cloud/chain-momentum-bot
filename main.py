import os
import time
import logging
import threading
import requests
import schedule
import pandas as pd
from flask import Flask
import tweepy

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")

SCAN_INTERVAL = 15
TIMEFRAME = "4H"
RR_RATIO = 2  # Risk Reward 1:2

PAIRS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT"]

last_signal = {}

logging.basicConfig(level=logging.INFO)

# ================= TELEGRAM =================

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

# ================= TWITTER =================

def post_twitter(text):
    try:
        auth = tweepy.OAuth1UserHandler(
            TW_API_KEY,
            TW_API_SECRET,
            TW_ACCESS_TOKEN,
            TW_ACCESS_SECRET
        )
        api = tweepy.API(auth)
        api.update_status(text[:280])
    except Exception as e:
        logging.error(f"Twitter error: {e}")

# ================= DATA FETCH =================

def fetch_data(symbol):
    try:
        coin = symbol.replace("USDT","").lower()
        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
        params = {"vs_currency":"usd","days":"120","interval":"daily"}

        r = requests.get(url, params=params)

        if r.status_code == 429:
            time.sleep(30)
            return None

        data = r.json()["prices"]

        df = pd.DataFrame(data, columns=["timestamp","close"])
        df["close"] = df["close"].astype(float)

        df["ema50"] = df["close"].ewm(span=50).mean()
        df["ema200"] = df["close"].ewm(span=200).mean()

        df["tr"] = abs(df["close"] - df["close"].shift())
        df["atr"] = df["tr"].rolling(14).mean()

        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        rs = gain.rolling(14).mean() / loss.rolling(14).mean()
        df["rsi"] = 100 - (100/(1+rs))

        return df

    except:
        return None

# ================= SIGNAL =================

def detect_signal(df):
    if len(df) < 210:
        return None

    last = df.iloc[-1]

    trend_up = last["ema50"] > last["ema200"]
    trend_down = last["ema50"] < last["ema200"]

    breakout_up = last["close"] > df["close"].rolling(20).max().iloc[-2]
    breakout_down = last["close"] < df["close"].rolling(20).min().iloc[-2]

    rsi_ok_buy = 45 < last["rsi"] < 65
    rsi_ok_sell = 35 < last["rsi"] < 55

    if trend_up and breakout_up and rsi_ok_buy:
        return "BUY"

    if trend_down and breakout_down and rsi_ok_sell:
        return "SELL"

    return None

# ================= SCANNER =================

def scan():
    for symbol in PAIRS:
        time.sleep(2)

        df = fetch_data(symbol)
        if df is None:
            continue

        signal = detect_signal(df)
        if not signal:
            continue

        if last_signal.get(symbol) == signal:
            continue

        last = df.iloc[-1]
        entry = last["close"]
        atr = last["atr"]

        if signal == "BUY":
            sl = entry - atr
            tp = entry + (atr * RR_RATIO)
        else:
            sl = entry + atr
            tp = entry - (atr * RR_RATIO)

        msg = f"""
🔥 ELITE {signal} SIGNAL ({TIMEFRAME})

Pair: {symbol}
Entry: {round(entry,4)}
Stop Loss: {round(sl,4)}
Take Profit: {round(tp,4)}
Risk:Reward 1:{RR_RATIO}
ATR Based Dynamic SL
"""

        send_telegram(msg)
        post_twitter(msg)

        last_signal[symbol] = signal

# ================= DAILY SUMMARY =================

def daily_summary():
    text = "📊 Daily Market Scan Completed (ELITE BOT)"
    send_telegram(text)

# ================= SCHEDULER =================

def scheduler():
    schedule.every(SCAN_INTERVAL).minutes.do(scan)
    schedule.every().day.at("23:00").do(daily_summary)

    while True:
        schedule.run_pending()
        time.sleep(5)

# ================= FLASK =================

app = Flask(__name__)

@app.route("/")
def home():
    return "ELITE BOT RUNNING", 200

def start():
    thread = threading.Thread(target=scheduler)
    thread.daemon = True
    thread.start()

start()

send_telegram("🚀 ELITE Crypto Signal Bot ACTIVE")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
