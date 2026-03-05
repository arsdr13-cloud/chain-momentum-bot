# =========================================================
# DESK GRADE v20 — LIQUIDITY MAP ENGINE
# Institutional Flow Desk Bot
# BTC • ETH • SOL Liquidity + Positioning Map
# =========================================================

import os
import requests
import tweepy
import time
from datetime import datetime

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

# ================= PRICE DATA =================

def get_price(symbol):

    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

    headers = {
        "X-CMC_PRO_API_KEY": CMC_API_KEY
    }

    params = {
        "symbol": symbol
    }

    r = requests.get(url, headers=headers, params=params)
    data = r.json()

    price = data["data"][symbol]["quote"]["USD"]["price"]
    change = data["data"][symbol]["quote"]["USD"]["percent_change_24h"]

    return price, change

# ================= OPEN INTEREST =================

def get_open_interest(symbol):

    try:
        url = f"https://fapi.binance.com/futures/data/openInterestHist?symbol={symbol}USDT&period=5m&limit=2"
        r = requests.get(url)
        data = r.json()

        oi_now = float(data[-1]["sumOpenInterest"])
        oi_prev = float(data[-2]["sumOpenInterest"])

        shift = oi_now - oi_prev

        return shift

    except:
        return 0

# ================= FUNDING RATE =================

def get_funding(symbol):

    try:
        url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}USDT"
        r = requests.get(url)
        data = r.json()

        funding = float(data["lastFundingRate"])

        return funding

    except:
        return 0

# ================= LIQUIDITY PRESSURE =================

def liquidity_pressure(change, oi_shift):

    if change > 2 and oi_shift > 0:
        return "Long pressure building"

    elif change < -2 and oi_shift > 0:
        return "Short pressure building"

    elif change > 2 and oi_shift < 0:
        return "Short squeeze"

    elif change < -2 and oi_shift < 0:
        return "Long liquidation"

    else:
        return "Liquidity compression"

# ================= FLOW SCORE =================

def flow_score(change, oi_shift, funding):

    score = 0

    if change > 0:
        score += 1

    if oi_shift > 0:
        score += 1

    if funding > 0:
        score += 1

    return score

# ================= TWEET BUILDER =================

def build_tweet():

    tweet = "6H Liquidity & Positioning Map\n\n"

    for symbol in SYMBOLS:

        price, change = get_price(symbol)
        oi = get_open_interest(symbol)
        funding = get_funding(symbol)

        pressure = liquidity_pressure(change, oi)
        score = flow_score(change, oi, funding)

        tweet += (
            f"{symbol}\n"
            f"Price: {round(price,2)}\n"
            f"24H: {round(change,2)}%\n"
            f"OI Shift: {round(oi,2)}\n"
            f"Funding: {round(funding,4)}\n"
            f"Flow Score: {score}/3\n"
            f"{pressure}\n\n"
        )

    tweet += (
        "Variable now:\n"
        "watching where liquidity expands next.\n\n"
        "Structure first. Always."
    )

    return tweet

# ================= POST TWEET =================

def post_tweet():

    tweet = build_tweet()

    try:
        client.create_tweet(text=tweet)
        print("Tweet posted")

    except Exception as e:
        print("Twitter error:", e)

# ================= MAIN LOOP =================

def run_bot():

    while True:

        print("Running Liquidity Map Engine:", datetime.now())

        post_tweet()

        time.sleep(21600)  # 6H cycle

# ================= START =================

if __name__ == "__main__":
    run_bot()