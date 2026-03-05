# =========================================================
# DESK GRADE v21 — HEDGE FUND FLOW ENGINE
# Railway Stable Version
# =========================================================

import os
import requests
import tweepy
import time
from datetime import datetime
from flask import Flask
import threading

# ================= WEB SERVER (RAILWAY FIX) =================

app = Flask(__name__)

@app.route("/")
def home():
    return "Desk Grade v21 running"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ================= CONFIG =================

CMC_API_KEY = os.getenv("CMC_API_KEY")

TW_BEARER_TOKEN = os.getenv("TW_BEARER_TOKEN")
TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")

SYMBOLS = ["BTC", "ETH", "SOL"]

# ================= TWITTER AUTH =================

client = tweepy.Client(
    bearer_token=TW_BEARER_TOKEN,
    consumer_key=TW_API_KEY,
    consumer_secret=TW_API_SECRET,
    access_token=TW_ACCESS_TOKEN,
    access_token_secret=TW_ACCESS_SECRET
)

# ================= SAFE REQUEST =================

def safe_request(url, headers=None, params=None):

    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)

        if r.status_code == 200:
            return r.json()

        return None

    except Exception as e:
        print("Request error:", e)
        return None


# ================= PRICE =================

def get_price(symbol):

    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}

    params = {"symbol": symbol}

    data = safe_request(url, headers=headers, params=params)

    if not data:
        return 0, 0

    try:
        price = data["data"][symbol]["quote"]["USD"]["price"]
        change = data["data"][symbol]["quote"]["USD"]["percent_change_24h"]

        return price, change

    except:
        return 0, 0


# ================= OPEN INTEREST =================

def get_open_interest(symbol):

    url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}USDT"

    data = safe_request(url)

    if not data:
        return 0

    try:
        return float(data["openInterest"])

    except:
        return 0


# ================= FUNDING =================

def get_funding(symbol):

    url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}USDT"

    data = safe_request(url)

    if not data:
        return 0

    try:
        return float(data["lastFundingRate"])

    except:
        return 0


# ================= PRESSURE =================

def liquidity_pressure(change, funding):

    if change > 2 and funding > 0:
        return "Long pressure building"

    elif change < -2 and funding < 0:
        return "Short pressure building"

    elif change > 2 and funding < 0:
        return "Short squeeze"

    elif change < -2 and funding > 0:
        return "Long liquidation"

    return "Liquidity compression"


# ================= FLOW SCORE =================

def flow_score(change, funding):

    score = 0

    if change > 0:
        score += 1

    if funding > 0:
        score += 1

    if abs(change) > 2:
        score += 1

    return score


# ================= BUILD TWEET =================

def build_tweet():

    tweet = "6H Liquidity & Positioning Map\n\n"

    for symbol in SYMBOLS:

        price, change = get_price(symbol)
        oi = get_open_interest(symbol)
        funding = get_funding(symbol)

        pressure = liquidity_pressure(change, funding)
        score = flow_score(change, funding)

        tweet += (
            f"{symbol}\n"
            f"P {round(price,2)}\n"
            f"24H {round(change,2)}%\n"
            f"OI {round(oi,2)}\n"
            f"F {round(funding,4)}\n"
            f"Score {score}/3\n"
            f"{pressure}\n\n"
        )

    tweet += "Structure first. Always."

    if len(tweet) > 275:
        tweet = tweet[:275]

    return tweet


# ================= POST =================

def post_tweet():

    tweet = build_tweet()

    try:

        client.create_tweet(text=tweet)

        print("Tweet posted")
        print(tweet)

    except Exception as e:

        print("Twitter error:", e)


# ================= BOT LOOP =================

def run_bot():

    while True:

        print("Running:", datetime.now())

        post_tweet()

        time.sleep(21600)


# ================= START =================

if __name__ == "__main__":

    threading.Thread(target=run_bot).start()

    run_web()