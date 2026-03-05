# =========================================================
# DESK GRADE v21 — HEDGE FUND FLOW ENGINE
# Institutional Liquidity + Positioning Monitor
# BTC • ETH • SOL
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

CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

REQUEST_TIMEOUT = 10

CYCLE_TIME = 21600  # 6 hours

OI_MEMORY = {}

# ================= TWITTER =================

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
        r = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)

        if r.status_code != 200:
            return None

        return r.json()

    except:
        return None

# ================= PRICE DATA =================

def get_price(symbol):

    headers = {
        "X-CMC_PRO_API_KEY": CMC_API_KEY
    }

    params = {
        "symbol": symbol
    }

    data = safe_request(CMC_URL, headers, params)

    if not data:
        return None, None

    try:

        price = data["data"][symbol]["quote"]["USD"]["price"]
        change = data["data"][symbol]["quote"]["USD"]["percent_change_24h"]

        return price, change

    except:
        return None, None

# ================= OPEN INTEREST =================

def get_open_interest_shift(symbol):

    try:

        url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}USDT"

        data = safe_request(url)

        if not data:
            return 0

        oi_now = float(data["openInterest"])

        oi_prev = OI_MEMORY.get(symbol, oi_now)

        shift = oi_now - oi_prev

        OI_MEMORY[symbol] = oi_now

        return shift

    except:
        return 0

# ================= FUNDING =================

def get_funding(symbol):

    try:

        url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}USDT"

        data = safe_request(url)

        if not data:
            return 0

        return float(data.get("lastFundingRate", 0))

    except:
        return 0

# ================= LIQUIDITY PRESSURE =================

def liquidity_pressure(change, oi_shift):

    if change is None:
        return "No signal"

    if change > 2 and oi_shift > 0:
        return "Long pressure building"

    if change < -2 and oi_shift > 0:
        return "Short pressure building"

    if change > 2 and oi_shift < 0:
        return "Short squeeze"

    if change < -2 and oi_shift < 0:
        return "Long liquidation"

    return "Liquidity compression"

# ================= FLOW SCORE =================

def flow_score(change, oi_shift, funding):

    score = 0

    if change and change > 0:
        score += 1

    if oi_shift > 0:
        score += 1

    if funding > 0:
        score += 1

    return score

# ================= FLOW INTERPRETATION =================

def interpret_flow(score):

    if score == 3:
        return "Aggressive positioning"

    if score == 2:
        return "Position building"

    if score == 1:
        return "Weak flow"

    return "Defensive positioning"

# ================= BUILD TWEET =================

def build_tweet():

    tweet = "6H Liquidity & Positioning Map\n\n"

    for symbol in SYMBOLS:

        price, change = get_price(symbol)

        oi_shift = get_open_interest_shift(symbol)

        funding = get_funding(symbol)

        pressure = liquidity_pressure(change, oi_shift)

        score = flow_score(change, oi_shift, funding)

        interpretation = interpret_flow(score)

        if price is None:
            continue

        tweet += (
            f"{symbol}\n"
            f"Price: {round(price,2)}\n"
            f"24H: {round(change,2)}%\n"
            f"OI Shift: {round(oi_shift,2)}\n"
            f"Funding: {round(funding,4)}\n"
            f"Flow Score: {score}/3\n"
            f"{pressure}\n"
            f"{interpretation}\n\n"
        )

    tweet += (
        "Variable now:\n"
        "watching where liquidity expands next.\n\n"
        "Structure first. Always."
    )

    return tweet[:280]

# ================= POST TWEET =================

def post_tweet():

    tweet = build_tweet()

    try:

        client.create_tweet(text=tweet)

        print("Tweet posted:", datetime.utcnow())

    except Exception as e:

        print("Twitter error:", e)

# ================= BOT LOOP =================

def run_bot():

    while True:

        print("Running Flow Engine:", datetime.utcnow())

        post_tweet()

        time.sleep(CYCLE_TIME)

# ================= START =================

if __name__ == "__main__":

    run_bot()