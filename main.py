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
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": TIMEFRAME, "limit": 300}
    r = requests.get(url, params=params)

    if r.status_code != 200:
        logging.error(f"{symbol} API error: {r.text}")
        return None

    data = r.json()

    if not data or len(data) < 210:
        logging.warning(f"{symbol} not enough data")
        return None

    df = pd.DataFrame(data, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","qav","trades","tbbav","tbqav","ignore"
    ])

    df[["open","high","low","close","volume"]] = \
        df[["open","high","low","close","volume"]].astype(float)

    return df

def detect_signal(df):
    df["ema50"] = ta.trend.ema_indicator(df["close"], window=50)
    df["ema200"] = ta.trend.ema_indicator(df["close"], window=200)
    df["rsi"] = ta.momentum.rsi(df["close"], window=14)
    df["vol_ma"] = df["volume"].rolling(20).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if (
        last["ema50"] > last["ema200"] and
        35 <= last["rsi"] <= 50 and
        last["close"] > prev["high"] and
        last["volume"] > last["vol_ma"]
    ):
        return "LONG"

    if (
        last["ema50"] < last["ema200"] and
        50 <= last["rsi"] <= 65 and
        last["close"] < prev["low"] and
        last["volume"] > last["vol_ma"]
    ):
        return "SHORT"

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

# ================= START BACKGROUND =================
def start_background():
    thread = threading.Thread(target=run_scheduler)
    thread.daemon = True
    thread.start()
    logging.info("Scheduler started")

start_background()
