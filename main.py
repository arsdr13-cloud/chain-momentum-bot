import os
import requests
import tweepy
import logging
from datetime import datetime
import matplotlib.pyplot as plt
from flask import Flask

# ================= FLASK KEEP ALIVE =================

app = Flask(__name__)

@app.route("/")
def home():
    return "Desk Grade v22 Running"

# ================= CONFIG =================

CMC_API_KEY = os.getenv("CMC_API_KEY")

TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")
TW_BEARER_TOKEN = os.getenv("TW_BEARER_TOKEN")

logging.basicConfig(level=logging.INFO)

# ================= TWITTER AUTH =================

client = tweepy.Client(
    bearer_token=TW_BEARER_TOKEN,
    consumer_key=TW_API_KEY,
    consumer_secret=TW_API_SECRET,
    access_token=TW_ACCESS_TOKEN,
    access_token_secret=TW_ACCESS_SECRET
)

# ================= DATA SOURCES =================

def get_price(symbol):

    try:

        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

        headers = {
            "X-CMC_PRO_API_KEY": CMC_API_KEY
        }

        params = {
            "symbol": symbol,
            "convert": "USD"
        }

        r = requests.get(url, headers=headers, params=params, timeout=10)

        data = r.json()

        price = data["data"][symbol]["quote"]["USD"]["price"]

        return float(price)

    except Exception as e:

        logging.error(f"CMC price error {symbol}: {e}")
        return None


def get_bybit_oi(symbol):

    try:

        url = "https://api.bybit.com/v5/market/open-interest"

        params = {
            "category": "linear",
            "symbol": f"{symbol}USDT",
            "intervalTime": "5min"
        }

        r = requests.get(url, params=params, timeout=10)

        data = r.json()

        oi = float(data["result"]["list"][0]["openInterest"])

        return oi

    except Exception as e:

        logging.error(f"Bybit OI error {symbol}: {e}")
        return None


def get_okx_funding(symbol):

    try:

        url = f"https://www.okx.com/api/v5/public/funding-rate?instId={symbol}-USDT-SWAP"

        r = requests.get(url, timeout=10)

        data = r.json()

        funding = float(data["data"][0]["fundingRate"])

        return funding

    except Exception as e:

        logging.error(f"OKX funding error {symbol}: {e}")
        return None


# ================= FORMAT HELPERS =================

def format_price(price):

    if price is None:
        return "N/A"

    return f"{price:,.0f}"


def format_funding(funding):

    if funding is None:
        return "N/A"

    return f"{funding*100:.4f}%"


def format_oi(oi):

    if oi is None:
        return "N/A"

    if oi > 1_000_000_000:
        return f"{oi/1_000_000_000:.2f}B"

    if oi > 1_000_000:
        return f"{oi/1_000_000:.2f}M"

    return f"{oi:,.0f}"


# ================= CHART =================

def generate_chart(prices):

    try:

        coins = list(prices.keys())
        values = list(prices.values())

        plt.figure(figsize=(6,4))
        plt.bar(coins, values)

        plt.title("Desk Grade Liquidity Snapshot")

        filename = "market_map.png"

        plt.savefig(filename, bbox_inches="tight")
        plt.close()

        return filename

    except Exception as e:

        logging.error(f"Chart error: {e}")
        return None


# ================= TWEET =================

def post_tweet(text, image=None):

    try:

        if image:

            auth = tweepy.OAuth1UserHandler(
                TW_API_KEY,
                TW_API_SECRET,
                TW_ACCESS_TOKEN,
                TW_ACCESS_SECRET
            )

            api = tweepy.API(auth)

            media = api.media_upload(image)

            client.create_tweet(
                text=text,
                media_ids=[media.media_id]
            )

        else:

            client.create_tweet(text=text)

        logging.info("Tweet posted")

    except Exception as e:

        logging.error(f"Tweet error: {e}")


# ================= ENGINE =================

def run_engine():

    symbols = ["BTC", "ETH", "SOL"]

    prices = {}

    report = []

    for s in symbols:

        price = get_price(s)
        oi = get_bybit_oi(s)
        funding = get_okx_funding(s)

        if price is not None:
            prices[s] = price

        report.append(
            f"{s}\n"
            f"Price: {format_price(price)}\n"
            f"OI: {format_oi(oi)}\n"
            f"Funding: {format_funding(funding)}\n"
        )

    chart = generate_chart(prices)

    tweet_text = (
        "6H Liquidity & Positioning Map\n\n"
        + "\n".join(report)
        + "\nStructure first. Always."
    )

    post_tweet(tweet_text, chart)


# ================= START BOT =================

def start_bot():

    try:

        logging.info("Desk Grade v22 running")

        run_engine()

    except Exception as e:

        logging.error(f"ENGINE CRASH: {e}")


start_bot()


# ================= RAILWAY SERVER =================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8080))

    app.run(host="0.0.0.0", port=port)