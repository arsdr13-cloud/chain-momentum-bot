import os
import logging
import requests
import matplotlib.pyplot as plt
from flask import Flask
import tweepy
from datetime import datetime

# ================= CONFIG =================

CMC_API_KEY = os.getenv("CMC_API_KEY")

TW_BEARER_TOKEN = os.getenv("TW_BEARER_TOKEN")
TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")

COINS = ["BTC","ETH","SOL"]

# ================= LOGGING =================

logging.basicConfig(level=logging.INFO)

# ================= FLASK =================

app = Flask(__name__)

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

# ================= MARKET DATA =================

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

        r = requests.get(url, headers=headers, params=params)

        if r.status_code != 200:
            return None

        return r.json()["data"]

    except Exception as e:

        logging.error(e)
        return None

# ================= GLOBAL DATA =================

def fetch_global():

    try:

        url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"

        headers = {
            "X-CMC_PRO_API_KEY": CMC_API_KEY
        }

        r = requests.get(url, headers=headers)

        if r.status_code != 200:
            return None

        return r.json()["data"]

    except:

        return None

# ================= RELATIVE STRENGTH =================

def relative_strength(base, compare):

    return round(compare - base,2)

# ================= STRUCTURE ENGINE =================

def structure_engine(btc_change):

    if btc_change > 3:

        return "Bullish Expansion"

    if btc_change < -3:

        return "Bearish Expansion"

    return "Range Structure"

# ================= ROTATION ENGINE =================

def rotation_engine(btc,eth,sol):

    eth_vs_btc = relative_strength(btc,eth)
    sol_vs_btc = relative_strength(btc,sol)

    if eth_vs_btc > 0.5 and sol_vs_btc > 1:

        return "Broad Alt Rotation"

    if eth_vs_btc > 0.5:

        return "ETH Leadership"

    if sol_vs_btc > 1:

        return "High Beta Expansion"

    return "BTC Dominance"

# ================= MOMENTUM ENGINE =================

def momentum_engine(btc,eth,sol):

    biggest = max(abs(btc),abs(eth),abs(sol))

    if biggest > 4:

        return "Strong Momentum"

    if biggest > 2:

        return "Momentum Building"

    return "Low Momentum"

# ================= FLOW ENGINE =================

def flow_engine(btc,eth,sol):

    alt_pressure = (eth + sol)/2 - btc

    if alt_pressure > 3:

        return "Aggressive Alt Expansion"

    if alt_pressure > 1.5:

        return "Alt Pressure Building"

    if btc > eth:

        return "BTC Defensive Flow"

    return "Balanced Flow"

# ================= INTENT ENGINE =================

def intent_engine(btc):

    if btc > 4:

        return "Breakout Intent"

    if btc < -4:

        return "Capitulation"

    return "Liquidity Testing"

# ================= CHART =================

def generate_chart(btc,eth,sol):

    labels = ["BTC","ETH","SOL"]
    values = [btc,eth,sol]

    plt.figure()

    plt.bar(labels,values)

    plt.title("24H Market Structure")

    path = "market_chart.png"

    plt.savefig(path)

    plt.close()

    return path

# ================= BUILD TEXT =================

def build_text(btc_change,eth_change,sol_change,btc_dom):

    structure = structure_engine(btc_change)

    rotation = rotation_engine(
        btc_change,
        eth_change,
        sol_change
    )

    momentum = momentum_engine(
        btc_change,
        eth_change,
        sol_change
    )

    flow = flow_engine(
        btc_change,
        eth_change,
        sol_change
    )

    intent = intent_engine(btc_change)

    eth_vs_btc = relative_strength(
        btc_change,
        eth_change
    )

    sol_vs_btc = relative_strength(
        btc_change,
        sol_change
    )

    tweet = f"""
6H Structure Map

BTC {btc_change:+.2f}%
ETH {eth_change:+.2f}%
SOL {sol_change:+.2f}%

BTC.D {btc_dom:.2f}%

Structure: {structure}

Rotation: {rotation}

Momentum: {momentum}

Flow: {flow}

Intent: {intent}

Relative Strength

ETH/BTC {eth_vs_btc:+.2f}%
SOL/BTC {sol_vs_btc:+.2f}%

Structure first. Always.
"""

    return tweet[:280]

# ================= TWITTER POST =================

def post_twitter(message,image):

    try:

        media = api_v1.media_upload(image)

        client.create_tweet(
            text=message,
            media_ids=[media.media_id]
        )

    except Exception as e:

        logging.error(e)

# ================= SCAN =================

def scan():

    data = fetch_market_data()
    global_data = fetch_global()

    if not data or not global_data:
        return

    btc_change = data["BTC"]["quote"]["USD"]["percent_change_24h"]
    eth_change = data["ETH"]["quote"]["USD"]["percent_change_24h"]
    sol_change = data["SOL"]["quote"]["USD"]["percent_change_24h"]

    btc_dom = global_data["btc_dominance"]

    tweet = build_text(
        btc_change,
        eth_change,
        sol_change,
        btc_dom
    )

    image = generate_chart(
        btc_change,
        eth_change,
        sol_change
    )

    post_twitter(
        tweet,
        image
    )

# ================= ROUTES =================

@app.route("/")
def home():

    return "DESK GRADE v14 ACTIVE"

@app.route("/run")

def run():

    scan()

    return "SCAN COMPLETE"

# ================= START =================

if __name__ == "__main__":

    port = int(os.environ.get("PORT",8080))

    app.run(
        host="0.0.0.0",
        port=port
    )