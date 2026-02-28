import os
import logging
import requests
import matplotlib.pyplot as plt
from flask import Flask
import tweepy
import xml.etree.ElementTree as ET
from datetime import datetime

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
                    "caption": caption[:1024]
                },
                files={"photo": img},
                timeout=20
            )
        logging.info("Telegram sent")
    except Exception as e:
        logging.error(f"Telegram error: {e}")


# ==============================
# TWITTER PREMIUM FORMAT
# ==============================

def build_twitter_text(btc_price, btc_change, eth_price, eth_change, sol_price, sol_change):
    news = fetch_latest_news()

    # Safety: kalau news kosong
    if news:
        first_headline = news.split("\n")[0]
    else:
        first_headline = "No major crypto headlines today."

    tweet_text = f"""🚀 CHAIN MOMENTUM UPDATE

BTC: ${btc_price} ({btc_change}%)
ETH: ${eth_price} ({eth_change}%)
SOL: ${sol_price} ({sol_change}%)

📰 {first_headline}

Stay Ahead. Trade Smart.

#Crypto #BTC #ETH #SOL"""

    # Batasi maksimal 280 karakter (safe 275)
    if len(tweet_text) > 275:
        tweet_text = tweet_text[:272] + "..."

    return tweet_text

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

        response = client.create_tweet(
            text=message,
            media_ids=[media.media_id]
        )

        logging.info(f"Tweet sent successfully: {response}")

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

# ================= RSS NEWS =================

def fetch_latest_news():
    try:
        rss_url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        r = requests.get(rss_url, timeout=20)
        logging.info(f"News response: {r.text[:500]}")

        if r.status_code != 200:
            logging.error(f"News status: {r.status_code}")
            return ""

        data = r.json()

        if "Data" not in data:
            logging.error("No 'Data' key in response")
            return ""

        news_text = "\n📰 MARKET HEADLINES\n"
        news_text += "──────────────── \n"
 
        for article in data["Data"][:3]:
            title = article.get("title", "")
            if title:
                news_text += f"• {title}\n"

        return news_text

    except Exception as e:
        logging.error(f"News error: {e}")
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
    plt.title("CHAIN MOMENTUM – MARKET SNAPSHOT")
    plt.ylabel("Price (USD)")
    plt.tight_layout()

    filename = "market_report.png"
    plt.savefig(filename)
    plt.close()

    return filename

# ================= PREMIUM FORMAT =================

def build_premium_message(data):

    now = datetime.utcnow().strftime("%d %b %Y | %H:%M UTC")

    message = "━━━━━━━━━━━━━━━━━━━━━━\n"
    message += "🚀  CHAIN MOMENTUM\n"
    message += "📊  Premium Crypto Intelligence\n"
    message += f"🕒  {now}\n"
    message += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    total_bullish = 0

    for coin in COINS:
        price = data[coin]["quote"]["USD"]["price"]
        change_24h = data[coin]["quote"]["USD"]["percent_change_24h"]
        volume = data[coin]["quote"]["USD"]["volume_24h"]

        status = "🟢 Bullish Momentum" if change_24h > 0 else "🔴 Bearish Pressure"

        if change_24h > 0:
            total_bullish += 1

        message += f"💎 {coin}\n"
        message += f"   💰 Price      : ${price:,.2f}\n"
        message += f"   📊 24H Change : {change_24h:.2f}%\n"
        message += f"   💵 Volume     : ${volume:,.0f}\n"
        message += f"   🔎 Sentiment  : {status}\n\n"

    # Market Summary
    message += "━━━━━━━━━━━━━━━━━━━━━━\n"
    message += "🧠 MARKET SUMMARY\n"

    if total_bullish >= 2:
        message += "Overall Bias: 🟢 Bullish Control\n"
    else:
        message += "Overall Bias: 🔴 Defensive Mode\n"

    message += fetch_latest_news()

    message += "\n━━━━━━━━━━━━━━━━━━━━━━\n"
    message += "#Crypto #BTC #ETH #SOL\n"
    message += "Stay Ahead. Trade Smart."

    return message

# ================= BUILD TWITTER =================

def build_twitter_text(btc_price, btc_change, eth_price, eth_change, sol_price, sol_change):

    news = fetch_latest_news()

    if news and news.strip():
        first_headline = news.strip().split("\n")[0]
    else:
        first_headline = "No major crypto headlines today."

    tweet_text = f"""🚀 CHAIN MOMENTUM UPDATE

BTC: ${btc_price:,.0f} ({btc_change:.2f}%)
ETH: ${eth_price:,.0f} ({eth_change:.2f}%)
SOL: ${sol_price:,.0f} ({sol_change:.2f}%)

📰 {first_headline}

Stay Ahead. Trade Smart.

#Crypto #BTC #ETH #SOL"""

    if len(tweet_text) > 275:
        tweet_text = tweet_text[:272] + "..."

    return tweet_text

# ================= SCAN =================

def scan():
    logging.info("=== CHAIN MOMENTUM SCAN ===")

    data = fetch_market_data()
    if not data:
        logging.error("No market data")
        return

    logging.info("Building messages...")

    telegram_message = build_premium_message(data)

    btc_price = data["BTC"]["quote"]["USD"]["price"]
    btc_change = data["BTC"]["quote"]["USD"]["percent_change_24h"]

    eth_price = data["ETH"]["quote"]["USD"]["price"]
    eth_change = data["ETH"]["quote"]["USD"]["percent_change_24h"]

    sol_price = data["SOL"]["quote"]["USD"]["price"]
    sol_change = data["SOL"]["quote"]["USD"]["percent_change_24h"]
    twitter_message = build_twitter_text(
    btc_price, btc_change,
    eth_price, eth_change,
    sol_price, sol_change
)
        
    image_path = generate_price_chart(data)

    logging.info("Sending Telegram...")
    send_telegram_photo(image_path, telegram_message)

    logging.info("Sending Twitter...")
    post_twitter_with_image(twitter_message, image_path)

    logging.info("SCAN FINISHED")

# ================= ROUTES =================

@app.route("/")
def home():
    return "🚀 CHAIN MOMENTUM BOT ACTIVE", 200


@app.route("/run-scan")
def run_scan():
    try:
        scan()
        return "✅ SCAN EXECUTED", 200
    except Exception as e:
        logging.error(f"Scan route error: {e}")
        return f"Error: {e}", 500
   
  # ================= START =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)