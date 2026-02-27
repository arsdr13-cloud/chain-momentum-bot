import os
import logging
import requests
import matplotlib.pyplot as plt
from flask import Flask
import tweepy
import xml.etree.ElementTree as ET

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CMC_API_KEY = os.getenv("CMC_API_KEY")

TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")

COINS = ["BTC", "ETH", "SOL"]

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# ================= TELEGRAM =================

def send_telegram_photo(photo_path, caption):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        with open(photo_path, "rb") as img:
            requests.post(
                url,
                data={
                    "chat_id": CHAT_ID,
                    "caption": caption[:1024]  # limit telegram caption
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

        client.create_tweet(text=message[:250], media_ids=[media.media_id])
        logging.info("Tweet sent")

    except Exception as e:
        logging.error(f"Twitter error: {e}")

# ================= COINMARKETCAP =================

def fetch_market_data():
    try:
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

        headers = {
            "X-CMC_PRO_API_KEY": CMC_API_KEY
        }

        params = {
            "symbol": ",".join(COINS),
            "convert": "USD"
        }

        r = requests.get(url, headers=headers, params=params, timeout=20)

        if r.status_code != 200:
            logging.error(f"CMC error: {r.status_code}")
            return None

        return r.json()["data"]

    except Exception as e:
        logging.error(f"CMC fetch error: {e}")
        return None

# ================= RSS NEWS (BTC ETH SOL) =================

def fetch_latest_news():
    try:
        rss_url = "https://www.coindesk.com/arc/outboundfeeds/rss/"
        r = requests.get(rss_url, timeout=20)

        if r.status_code != 200:
            logging.error("RSS fetch failed")
            return ""

        root = ET.fromstring(r.content)

        news_text = "\n📰 LATEST BTC • ETH • SOL NEWS:\n"

        count = 0

        for item in root.iter("item"):
            title = item.find("title").text.upper()

            if any(keyword in title for keyword in COINS):
                news_text += f"• {item.find('title').text}\n"
                count += 1

            if count >= 3:
                break

        return news_text if count > 0 else ""

    except Exception as e:
        logging.error(f"RSS error: {e}")
        return ""

# ================= CHART =================

def generate_price_chart(data):
    plt.style.use("dark_background")

    coins = []
    prices = []

    for coin in COINS:
        price = data[coin]["quote"]["USD"]["price"]
        coins.append(coin)
        prices.append(price)

    plt.figure(figsize=(8, 5))
    plt.bar(coins, prices)

    plt.title("CHAIN MOMENTUM MARKET REPORT")
    plt.ylabel("Price (USD)")
    plt.tight_layout()

    filename = "market_report.png"
    plt.savefig(filename)
    plt.close()

    return filename

# ================= SCAN =================

def scan():
    logging.info("=== CHAIN MOMENTUM SCAN ===")

    data = fetch_market_data()
    if not data:
        return

    message = "━━━━━━━━━━━━━━━━━━\n"
    message += "🚀 CHAIN MOMENTUM\n"
    message += "📊 Premium Market Report\n"
    message += "━━━━━━━━━━━━━━━━━━\n\n"

    for coin in COINS:
        price = data[coin]["quote"]["USD"]["price"]
        change_24h = data[coin]["quote"]["USD"]["percent_change_24h"]

        status = "🟢 Bullish" if change_24h > 0 else "🔴 Bearish"

        message += f"💎 {coin}\n"
        message += f"💰 Price: ${price:,.2f}\n"
        message += f"📊 24H: {change_24h:.2f}% | {status}\n\n"

    message += fetch_latest_news()
    message += "\n━━━━━━━━━━━━━━━━━━\n"
    message += "#Crypto #BTC #ETH #SOL"

    image_path = generate_price_chart(data)

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