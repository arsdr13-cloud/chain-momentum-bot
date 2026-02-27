import os
import logging
import requests
import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask
import tweepy

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CRYPTO_PANIC_API = os.getenv("CRYPTO_PANIC_API")

TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")

PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# ================= TELEGRAM =================

def send_telegram_photo(photo_path, caption):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        with open(photo_path, "rb") as img:
            requests.post(
                url,
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"photo": img},
                timeout=20
            )
        logging.info("Telegram sent")
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
        logging.info("Tweet sent")

    except Exception as e:
        logging.error(f"Twitter error: {e}")

# ================= DATA FETCH =================

import requests
import pandas as pd

def fetch_data(symbol="BTCUSDT", interval="1h", limit=100):
    url = "https://data-api.binance.vision/api/v3/klines"

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, params=params, headers=headers, timeout=10)

    if response.status_code != 200:
        print(f"{symbol} Binance error: {response.status_code}")
        return None

    data = response.json()

    df = pd.DataFrame(data, columns=[
        "timestamp","open","high","low","close","volume",
        "close_time","qav","num_trades",
        "taker_base_vol","taker_quote_vol","ignore"
    ])

    df["close"] = df["close"].astype(float)
    return df

# ================= NEWS FETCH =================

def fetch_latest_news():
    try:
        if not CRYPTO_PANIC_API:
            return ""

        url = "https://CRYPTO_PANIC_API/api/v1/posts/"
        params = {
            "auth_token": CRYPTO_PANIC_API,
            "currencies": "BTC,ETH,SOL",
            "kind": "news",
            "public": "true"
        }

        r = requests.get(url, params=params, timeout=20)

        if r.status_code != 200:
            logging.error(f"News API error: {r.status_code}")
            return ""

        results = r.json().get("results", [])[:3]

        news_text = "\n📰 LATEST CRYPTO NEWS:\n"
        for item in results:
            news_text += f"• {item['title']}\n"

        return news_text

    except Exception as e:
        logging.error(f"News error: {e}")
        return ""

# ================= CHART =================

def generate_combined_chart(data_dict):
    plt.style.use("dark_background")

    rows = len(data_dict)
    fig, axes = plt.subplots(rows, 1, figsize=(10, 4*rows))

    if rows == 1:
        axes = [axes]

    fig.suptitle("CHAIN MOMENTUM MARKET REPORT", fontsize=16)

    for ax, (symbol, df) in zip(axes, data_dict.items()):
        ax.plot(df["close"], label="Price")
        ax.plot(df["ema50"], linestyle="--", label="EMA50")
        ax.plot(df["ema200"], linestyle="--", label="EMA200")
        ax.set_title(symbol.replace("USDT",""))
        ax.legend()

    fig.text(0.5, 0.02,
             "© Chain Momentum | Crypto Intelligence",
             ha="center",
             fontsize=9,
             alpha=0.6)

    filename = "market_report.png"
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

    return filename

# ================= SCAN =================

def scan():
    logging.info("=== MARKET SCAN TRIGGERED ===")

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

        status = "Bullish 🚀" if ema50 > ema200 else "Bearish 🔻" if ema50 < ema200 else "Neutral ⚖️"

        message += f"{symbol.replace('USDT','')} → ${price:,.2f} | {status}\n"

    message += fetch_latest_news()
    message += "\n#Crypto #BTC #ETH #SOL"

    if data_dict:
        image_path = generate_combined_chart(data_dict)
        send_telegram_photo(image_path, message)
        post_twitter_with_image(message, image_path)

# ================= ROUTES =================

@app.route("/")
def home():
    return "CHAIN MOMENTUM BOT ACTIVE", 200

@app.route("/run-scan")
def run_scan():
    scan()
    return "SCAN EXECUTED", 200

# ================= START =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)