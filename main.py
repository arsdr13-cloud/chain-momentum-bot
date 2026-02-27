import os
import logging
import requests
import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask
import tweepy
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

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

def send_telegram_photo(photo_path, caption):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        with open(photo_path, "rb") as img:
            requests.post(
                url,
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"photo": img}
            )
    except Exception as e:
        logging.error(f"Telegram error: {e}")

# ================= TWITTER =================

def post_twitter_with_image(message, image_path):
    try:
        auth = tweepy.OAuth1UserHandler(
            TW_API_KEY,
            TW_API_SECRET,
            TW_ACCESS_TOKEN,
            TW_ACCESS_SECRET
        )
        api = tweepy.API(auth)
        media = api.media_upload(image_path)

        client = tweepy.Client(
            consumer_key=TW_API_KEY,
            consumer_secret=TW_API_SECRET,
            access_token=TW_ACCESS_TOKEN,
            access_token_secret=TW_ACCESS_SECRET
        )

        client.create_tweet(text=message, media_ids=[media.media_id])
        logging.info("Tweet with image sent")

    except Exception as e:
        logging.error(f"Twitter error: {e}")

# ================= DATA FETCH =================

def fetch_data(symbol):
    try:
        coin = COINGECKO_IDS.get(symbol)
        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"

        params = {
            "vs_currency": "usd",
            "days": "120",
            "interval": "daily"
        }

        r = requests.get(url, params=params, timeout=15)
        data = r.json().get("prices")

        df = pd.DataFrame(data, columns=["timestamp", "close"])
        df["close"] = df["close"].astype(float)

        df["ema50"] = df["close"].ewm(span=50).mean()
        df["ema200"] = df["close"].ewm(span=200).mean()

        return df

    except:
        return None

# ================= CHART GENERATOR =================

def generate_combined_chart(data_dict):
    plt.style.use("dark_background")
    fig, axes = plt.subplots(3, 1, figsize=(10, 12))

    fig.suptitle("CHAIN MOMENTUM MARKET REPORT", fontsize=16, fontweight="bold")

    for ax, (symbol, df) in zip(axes, data_dict.items()):

        ax.plot(df["close"], label="Price")
        ax.plot(df["ema50"], linestyle="--", label="EMA50")
        ax.plot(df["ema200"], linestyle="--", label="EMA200")

        ax.set_title(symbol.replace("USDT",""))
        ax.legend()

    # Watermark
    fig.text(0.5, 0.02,
             "© Chain Momentum | Crypto Market Intelligence",
             ha="center",
             fontsize=10,
             alpha=0.6)

    filename = "market_report.png"
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

    return filename

# ================= SCAN =================

def scan():
    logging.info("=== PRO MARKET SCAN ===")

    message = "🚨 MARKET SCAN REPORT 🚨\n\n"
    data_dict = {}

    for symbol in PAIRS:
        df = fetch_data(symbol)
        if df is None or len(df) < 50:
            continue

        data_dict[symbol] = df

        price = df["close"].iloc[-1]
        ema50 = df["ema50"].iloc[-1]
        ema200 = df["ema200"].iloc[-1]

        if ema50 > ema200:
            status = "Bullish 🚀"
        elif ema50 < ema200:
            status = "Bearish 🔻"
        else:
            status = "Neutral ⚖️"

        message += f"{symbol.replace('USDT','')} → ${price:,.2f} | {status}\n"

    message += "\n#Crypto #BTC #ETH #SOL"

    if data_dict:
        image_path = generate_combined_chart(data_dict)
        send_telegram_photo(image_path, message)
        post_twitter_with_image(message, image_path)

# ================= FLASK =================

app = Flask(__name__)

# ================= SCHEDULER =================

scheduler = BackgroundScheduler(timezone="Asia/Jakarta")

def start_scheduler():
    if scheduler.get_jobs():
        return

    scheduler.add_job(
        scan,
        trigger="cron",
        hour="*/4",
        minute=5
    )

    scheduler.start()
    logging.info("Scheduler Started")

start_scheduler()

@app.route("/")
def home():
    return "CHAIN MOMENTUM PRO BOT RUNNING", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
