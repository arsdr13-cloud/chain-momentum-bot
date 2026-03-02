import os
import logging
import requests
import threading
import time
from flask import Flask
import tweepy
from datetime import datetime, timedelta, timezone

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CMC_API_KEY = os.getenv("CMC_API_KEY")

TW_BEARER_TOKEN = os.getenv("TW_BEARER_TOKEN")
TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")

COINS = ["BTC", "ETH", "SOL"]

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# ================= WIB 6H SCHEDULER =================

WIB = timezone(timedelta(hours=7))
LAST_RUN = None

def is_6h_wib_time():
    global LAST_RUN

    now = datetime.now(WIB)

    if now.hour % 6 == 0 and now.minute == 0:
        if LAST_RUN != now.hour:
            LAST_RUN = now.hour
            return True

    return False

# ================= TWITTER CLIENT =================

client = tweepy.Client(
    bearer_token=TW_BEARER_TOKEN,
    consumer_key=TW_API_KEY,
    consumer_secret=TW_API_SECRET,
    access_token=TW_ACCESS_TOKEN,
    access_token_secret=TW_ACCESS_SECRET,
    wait_on_rate_limit=True
)

auth_v1 = tweepy.OAuth1UserHandler(
    TW_API_KEY,
    TW_API_SECRET,
    TW_ACCESS_TOKEN,
    TW_ACCESS_SECRET
)
api_v1 = tweepy.API(auth_v1)

# ================= TELEGRAM =================

def send_telegram_photo(photo_path, caption):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        with open(photo_path, "rb") as img:
            requests.post(
                url,
                data={
                    "chat_id": CHAT_ID,
                    "caption": caption[:1024],
                    "parse_mode": "HTML"
                },
                files={"photo": img},
                timeout=20
            )
        logging.info("Telegram sent")
    except Exception as e:
        logging.error(f"Telegram error: {e}")

# ================= TWITTER =================

def post_twitter_with_image(message, image_path):
    try:
        media = api_v1.media_upload(image_path)

        client.create_tweet(
            text=message,
            media_ids=[media.media_id]
        )

        logging.info("Tweet posted successfully")

    except Exception as e:
        logging.error(f"Twitter error: {e}")

# ================= MARKET DATA =================

def fetch_market_data():
    try:
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
        params = {"symbol": ",".join(COINS), "convert": "USD"}

        r = requests.get(url, headers=headers, params=params, timeout=20)

        if r.status_code != 200:
            logging.error(f"CMC error: {r.status_code}")
            return None

        return r.json()["data"]

    except Exception as e:
        logging.error(f"CMC fetch error: {e}")
        return None

# ================= MESSAGE BUILDER =================

def build_message(data):

    btc_price = data["BTC"]["quote"]["USD"]["price"]
    btc_change = data["BTC"]["quote"]["USD"]["percent_change_24h"]

    eth_price = data["ETH"]["quote"]["USD"]["price"]
    eth_change = data["ETH"]["quote"]["USD"]["percent_change_24h"]

    sol_price = data["SOL"]["quote"]["USD"]["price"]
    sol_change = data["SOL"]["quote"]["USD"]["percent_change_24h"]

    message = f"""
🚀 CHAIN MOMENTUM | 6H REPORT

🕒 {datetime.now(WIB).strftime('%d %b %Y | %H:%M WIB')}

BTC  ${btc_price:,.0f}  ({btc_change:.2f}%)
ETH  ${eth_price:,.0f}  ({eth_change:.2f}%)
SOL  ${sol_price:,.0f}  ({sol_change:.2f}%)

Stay Ahead. Trade Smart.
"""

    return message

# ================= SCAN =================

def scan():

    logging.info("=== 6H SCAN CHECK ===")

    if not is_6h_wib_time():
        return

    logging.info("=== EXECUTING 6H POST ===")

    data = fetch_market_data()
    if not data:
        return

    message = build_message(data)

    image_path = "market_chart.png"

    send_telegram_photo(image_path, message)
    post_twitter_with_image(message, image_path)

    logging.info("=== 6H POST COMPLETE ===")

# ================= AUTO LOOP =================

def scheduler_loop():
    while True:
        scan()
        time.sleep(60)

threading.Thread(target=scheduler_loop, daemon=True).start()

# ================= ROUTES =================

@app.route("/")
def home():
    return "🚀 CHAIN MOMENTUM BOT ACTIVE - 6H WIB MODE", 200

# ================= START =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)