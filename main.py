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
    print("🔥 SCAN FUNCTION TRIGGERED 🔥")
    logging.info("=== SCANNING MULTI COIN ===")

    message = "🚨 MARKET SCAN REPORT 🚨\n\n"

    for symbol in PAIRS:

        df = fetch_data(symbol)

        if df is None or len(df) < 210:
            message += f"{symbol.replace('USDT','')} → Data Error ❌\n"
            continue

        price = df["close"].iloc[-1]
        ema50 = df["ema50"].iloc[-1]
        ema200 = df["ema200"].iloc[-1]
        rsi = df["rsi"].iloc[-1]

        # ===== STATUS LOGIC =====
        if ema50 > ema200 and rsi > 55:
            status = "Bullish 🚀"
        elif ema50 < ema200 and rsi < 45:
            status = "Bearish 🔻"
        else:
            status = "Neutral ⚖️"

        message += (
            f"{symbol.replace('USDT','')}\n"
            f"Price : ${price:,.2f}\n"
            f"RSI   : {rsi:.2f}\n"
            f"Status: {status}\n\n"
        )

    message += "#Crypto #BTC #ETH #SOL"

    send_telegram(message)
    post_twitter(message)

    logging.info("Market scan sent successfully")

# ================= SCHEDULER =================
# ================= FLASK =================

app = Flask(__name__)

# ================= SCHEDULER =================

scheduler = BackgroundScheduler(timezone="Asia/Jakarta")

def start_scheduler():
    if scheduler.get_jobs():
        return  # cegah dobel

    scheduler.add_job(
        scan,
        trigger="cron",
        hour="*/4",
        minute=5
    )

    scheduler.start()
    logging.info("Scheduler Started")

# START SEKALI SAJA
start_scheduler()

@app.route("/")
def home():
    return "ELITE BOT RUNNING", 200

# ================= MAIN =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
