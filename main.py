import os
import time
import logging
import threading
import requests
import schedule
import pandas as pd
import ta
from flask import Flask
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

TIMEFRAME = "4h"
SCAN_INTERVAL_MIN = 1

COINS = ["bitcoin", "ethereum", "solana"]
PAIRS = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","AVAXUSDT","DOTUSDT","LINKUSDT"
]

last_signal = {}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ================= TELEGRAM =================
def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text})
    logging.info(f"TG: {r.status_code}")

def send_telegram_photo(filepath):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(filepath, "rb") as photo:
        requests.post(url, data={"chat_id": CHAT_ID}, files={"photo": photo})

# ================= TWITTER =================
def post_twitter(text):
    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET
        )
        client.create_tweet(text=text[:280])
    except Exception as e:
        logging.error(f"X error: {e}")

# ================= DAILY REPORT =================
def generate_chart(coin):
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
    params = {"vs_currency": "usd", "days": "1"}
    r = requests.get(url, params=params)
    data = r.json()
    prices = [p[1] for p in data["prices"]]

    plt.figure()
    plt.plot(prices)
    plt.title(f"{coin.upper()} 24H Chart")
    filename = f"{coin}.png"
    plt.savefig(filename)
    plt.close()
    return filename

def daily_report():
    logging.info("Daily report running...")
    for coin in COINS:
        file = generate_chart(coin)
        send_telegram_photo(file)
    msg = "📊 Daily Crypto Update is live!"
    send_telegram(msg)
    post_twitter(msg)

def weekly_report():
    msg = "📅 Weekly Crypto Recap is live!"
    send_telegram(msg)
    post_twitter(msg)

# ================= SIGNAL ENGINE =================

def fetch_klines(symbol):
    try:
        url = "https://api.bybit.com/v5/market/kline"

        # mapping timeframe
        tf_map = {
            "1h": "60",
            "4h": "240",
            "1d": "D"
        }

        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": tf_map.get(TIMEFRAME, "240"),
            "limit": 300
        }

        r = requests.get(url, params=params)

        if r.status_code != 200:
            logging.error(f"{symbol} Bybit API error: {r.text}")
            return None

        data = r.json()

        if data["retCode"] != 0:
            logging.error(f"{symbol} Bybit API error: {data}")
            return None

        result = data["result"]["list"]

        if not result:
            logging.warning(f"{symbol} no data returned")
            return None

        # Bybit return reversed order → kita balik
        result.reverse()

        df = pd.DataFrame(result, columns=[
            "open_time","open","high","low","close","volume","turnover"
        ])

        df[["open","high","low","close","volume"]] = \
            df[["open","high","low","close","volume"]].astype(float)

        return df

    except Exception as e:
        logging.error(f"{symbol} fetch error: {e}")
        return None

def scan_market():
    logging.info("Scanning signals...")
    for symbol in PAIRS:
        try:
            df = fetch_klines(symbol)

            if df is None or len(df) < 210:
                continue

            direction = detect_signal(df)

            if not direction:
                continue

            if last_signal.get(symbol) == direction:
                continue

            entry = df.iloc[-1]["close"]
            message = f"🚀 {symbol} {direction} SIGNAL (4H)\nEntry: {entry}"
            send_telegram(message)
            post_twitter(message)
            last_signal[symbol] = direction

        except Exception as e:
            logging.error(f"{symbol} error: {e}")
# ================= SCHEDULER =================
def run_scheduler():
    schedule.every(SCAN_INTERVAL_MIN).minutes.do(scan_market)
    schedule.every().day.at("09:00").do(daily_report)
    schedule.every().monday.at("20:00").do(weekly_report)

    while True:
        schedule.run_pending()
        time.sleep(10)

# ================= FLASK =================
app = Flask(__name__)

@app.route("/")
def health():
    return "Bot Running (Signal + Report)", 200

start_background()

# ================= START BACKGROUND =================
def start_background():
    thread = threading.Thread(target=run_scheduler)
    thread.daemon = True
    thread.start()
    logging.info("Scheduler started")

if __name__ == "__main__":
    start_background()
    app.run(host="0.0.0.0", port=8080)
