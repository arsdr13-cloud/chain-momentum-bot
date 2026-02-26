import os
import logging
import requests
import pandas as pd
from flask import Flask
import tweepy
from apscheduler.schedulers.background import BackgroundScheduler

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")

PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

COINGECKO_IDS = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "SOLUSDT": "solana"
}

logging.basicConfig(level=logging.INFO)

# ================= TELEGRAM =================

def send_telegram(text):
    try:
        if not BOT_TOKEN or not CHAT_ID:
            return

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        requests.post(
            url,
            json={"chat_id": CHAT_ID, "text": text},
            timeout=10
        )
    except Exception as e:
        logging.error(f"Telegram error: {e}")

# ================= TWITTER =================

def post_twitter(message):
    try:
        if not TW_API_KEY:
            return

        client = tweepy.Client(
            consumer_key=TW_API_KEY,
            consumer_secret=TW_API_SECRET,
            access_token=TW_ACCESS_TOKEN,
            access_token_secret=TW_ACCESS_SECRET
        )

        client.create_tweet(text=message)
        logging.info("Tweet sent")

    except Exception as e:
        logging.error(f"Twitter error: {e}")

# ================= DATA FETCH =================

def fetch_data(symbol):
    try:
        coin = COINGECKO_IDS.get(symbol)
        if not coin:
            return None

        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"

        params = {
            "vs_currency": "usd",
            "days": "120",
            "interval": "daily"
        }

        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            return None

        data = r.json().get("prices")
        if not data:
            return None

        df = pd.DataFrame(data, columns=["timestamp", "close"])
        df["close"] = df["close"].astype(float)

        df["ema50"] = df["close"].ewm(span=50).mean()
        df["ema200"] = df["close"].ewm(span=200).mean()

        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        rs = gain.rolling(14).mean() / loss.rolling(14).mean()
        df["rsi"] = 100 - (100 / (1 + rs))

        return df

    except Exception as e:
        logging.error(f"{symbol} fetch error: {e}")
        return None

# ================= SCAN =================

def scan():
    logging.info("=== SCANNING MULTI COIN ===")

    full_message = "🚨 MARKET SCAN REPORT 🚨\n"

    for symbol in PAIRS:

        df = fetch_data(symbol)

        if df is None or len(df) < 210:
            logging.warning(f"{symbol} data not ready")
            continue

        price = df["close"].iloc[-1]
        ema50 = df["ema50"].iloc[-1]
        ema200 = df["ema200"].iloc[-1]
        rsi = df["rsi"].iloc[-1]

        signal = "NEUTRAL"

        if ema50 > ema200 and rsi > 50:
            signal = "BUY 🚀"
        elif ema50 < ema200 and rsi < 50:
            signal = "SELL 🔻"

        full_message += f"""
{symbol.replace('USDT','')}
Price : ${price:,.2f}
EMA50 : {ema50:,.2f}
EMA200: {ema200:,.2f}
RSI   : {rsi:.2f}
Signal: {signal}
"""

    full_message += "\n#Crypto"

    send_telegram(full_message)
    post_twitter(full_message)

    logging.info("Scan finished")

# ================= SCHEDULER =================

scheduler = BackgroundScheduler(timezone="Asia/Jakarta")

def start_scheduler():
    scheduler.add_job(
        scan,
        trigger="cron",
        hour="*/4",
        minute=5
    )
    scheduler.start()
    logging.info("Scheduler Started")

# AUTO START (PENTING UNTUK RAILWAY)
if not scheduler.running:
    start_scheduler()

# ================= FLASK =================

app = Flask(__name__)

@app.route("/")
def home():
    return "ELITE BOT RUNNING", 200

# ================= MAIN =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
