import os
import time
import logging
import requests
import pandas as pd
from flask import Flask
import tweepy
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")

SCAN_INTERVAL = 15
TIMEFRAME = "4H"
RR_RATIO = 2

PAIRS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT"]

last_signal = {}

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
        client = tweepy.Client(
            consumer_key=os.getenv("TW_API_KEY"),
            consumer_secret=os.getenv("TW_API_SECRET"),
            access_token=os.getenv("TW_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TW_ACCESS_SECRET")
        )

        response = client.create_tweet(text=message)

        logging.info(f"✅ Tweet sent: {response.data}")

    except Exception as e:
        logging.error(f"❌ Twitter error: {e}")
# ================= DATA FETCH =================

def fetch_data(symbol):
    try:
        coin = symbol.replace("USDT","").lower()

        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"

        params = {
            "vs_currency":"usd",
            "days":"120",
            "interval":"daily"
        }

        r = requests.get(url, params=params, timeout=15)

        if r.status_code != 200:
            return None

        data = r.json().get("prices")
        if not data:
            return None

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

    except Exception as e:
        logging.error(f"{symbol} fetch error: {e}")
        return None

# ================= SIGNAL =================

def detect_signal(df):
    try:
        if len(df) < 210:
            return None

        last = df.iloc[-1]

        trend_up = last["ema50"] > last["ema200"]
        trend_down = last["ema50"] < last["ema200"]

        breakout_up = last["close"] > df["close"].rolling(20).max().iloc[-2]
        breakout_down = last["close"] < df["close"].rolling(20).min().iloc[-2]

        rsi_buy = 45 < last["rsi"] < 65
        rsi_sell = 35 < last["rsi"] < 55

        if trend_up and breakout_up and rsi_buy:
            return "BUY"

        if trend_down and breakout_down and rsi_sell:
            return "SELL"

        return None

    except Exception as e:
        logging.error(f"Signal error: {e}")
        return None

# ================= SCAN =================

def scan():
    logging.info("=== SCANNING MULTI COIN ===")

    coins = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    full_message = "🚨 MARKET SCAN REPORT 🚨\n"

    try:
        for symbol in coins:
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

        full_message += "\n#Crypto #BTC #ETH #SOL"

        send_telegram(full_message)
        post_twitter(full_message)

        logging.info("Multi coin message sent successfully")

    except Exception as e:
        logging.error(f"SCAN ERROR: {e}")


# ================= SUMMARY =================

def daily_summary():
    send_telegram("📊 Daily Market Scan Completed (ELITE BOT)")

# ================= SCHEDULER =================

from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler(timezone="Asia/Jakarta")

def start_scheduler():
    scheduler.add_job(
        scan,
        trigger="cron",
        hour="*/4",
        minute=5
    )

    scheduler.start()
    logging.info("Scheduler Multi Coin Started")


# ================= FLASK =================

app = Flask(__name__)

@app.route("/")
def home():
    return "ELITE BOT RUNNING", 200


# ================== MAIN ==================
if __name__ == "__main__":
    start_scheduler()   # ✅ PANGGIL DI SINI
    app.run(host="0.0.0.0", port=8080)
