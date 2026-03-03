import os
import logging
import requests
import matplotlib.pyplot as plt
from flask import Flask
import tweepy
from datetime import datetime

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
                data={"chat_id": CHAT_ID, "caption": caption[:1024]},
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

# ================= GLOBAL METRICS =================

def fetch_global_metrics():
    try:
        url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}

        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            return None

        return r.json()["data"]

    except:
        return None

# ================= ROTATION ENGINE =================

def detect_rotation(btc_change, eth_change, sol_change, btc_dom):

    if btc_dom > 58 and btc_change >= eth_change:
        return "BTC Leadership"
    elif eth_change > btc_change:
        return "ETH Relative Strength"
    elif sol_change > eth_change:
        return "High Beta Expansion (SOL)"
    else:
        return "Balanced Structure"

def calculate_relative_strength(base, compare):
    return round(compare - base, 2)

# ================= BUILD TWITTER TEXT =================

def build_twitter_text(
    btc_price, btc_change,
    eth_price, eth_change,
    sol_price, sol_change,
    btc_dom
):

    rotation_signal = detect_rotation(
        btc_change, eth_change, sol_change, btc_dom
    )

    eth_vs_btc = calculate_relative_strength(btc_change, eth_change)
    sol_vs_btc = calculate_relative_strength(btc_change, sol_change)

    tweet_text = f"""6H Positioning Brief

BTC ${btc_price:,.0f} | {btc_change:.2f}%
ETH ${eth_price:,.0f} | {eth_change:.2f}%
SOL ${sol_price:,.0f} | {sol_change:.2f}%

BTC.D: {btc_dom:.2f}%

Rotation: {rotation_signal}

ETH vs BTC: {eth_vs_btc:+.2f}%
SOL vs BTC: {sol_vs_btc:+.2f}%

Structure controlled.
Monitoring expansion.
"""

    return tweet_text[:280]

# ================= BUILD TELEGRAM MESSAGE =================

def build_telegram_message(data, global_data):

    now = datetime.utcnow().strftime("%d %b %Y | %H:%M UTC")

    btc_price = data["BTC"]["quote"]["USD"]["price"]
    btc_change = data["BTC"]["quote"]["USD"]["percent_change_24h"]

    eth_price = data["ETH"]["quote"]["USD"]["price"]
    eth_change = data["ETH"]["quote"]["USD"]["percent_change_24h"]

    sol_price = data["SOL"]["quote"]["USD"]["price"]
    sol_change = data["SOL"]["quote"]["USD"]["percent_change_24h"]

    btc_dom = global_data["btc_dominance"]

    rotation_signal = detect_rotation(
        btc_change, eth_change, sol_change, btc_dom
    )

    message = f"""CHAIN MOMENTUM | POSITIONING REPORT
━━━━━━━━━━━━━━━━━━
Time: {now}

BTC  ${btc_price:,.0f} | {btc_change:.2f}%
ETH  ${eth_price:,.0f} | {eth_change:.2f}%
SOL  ${sol_price:,.0f} | {sol_change:.2f}%

BTC Dominance: {btc_dom:.2f}%

Rotation Signal:
{rotation_signal}

Relative Strength:
ETH vs BTC: {eth_change - btc_change:+.2f}%
SOL vs BTC: {sol_change - btc_change:+.2f}%

Positioning monitored.
Next scan: 6H.
"""

    return message

# ================= CHART =================

def generate_chart(btc_change, eth_change, sol_change):

    coins = ["BTC", "ETH", "SOL"]
    changes = [btc_change, eth_change, sol_change]

    plt.figure(figsize=(8,5))
    bars = plt.bar(coins, changes)

    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width()/2,
            height,
            f"{height:.2f}%",
            ha="center",
            va="bottom"
        )

    plt.axhline(0, linewidth=1)
    plt.title("6H Relative Change")

    plt.tight_layout()
    filename = "market_chart.png"
    plt.savefig(filename)
    plt.close()

    return filename

# ================= SCAN =================

def scan():

    logging.info("=== CHAIN MOMENTUM SCAN ===")

    data = fetch_market_data()
    global_data = fetch_global_metrics()

    if not data or not global_data:
        return

    btc_price = data["BTC"]["quote"]["USD"]["price"]
    btc_change = data["BTC"]["quote"]["USD"]["percent_change_24h"]

    eth_price = data["ETH"]["quote"]["USD"]["price"]
    eth_change = data["ETH"]["quote"]["USD"]["percent_change_24h"]

    sol_price = data["SOL"]["quote"]["USD"]["price"]
    sol_change = data["SOL"]["quote"]["USD"]["percent_change_24h"]

    btc_dom = global_data["btc_dominance"]

    telegram_message = build_telegram_message(data, global_data)

    twitter_message = build_twitter_text(
        btc_price, btc_change,
        eth_price, eth_change,
        sol_price, sol_change,
        btc_dom
    )

    image_path = generate_chart(btc_change, eth_change, sol_change)

    send_telegram_photo(image_path, telegram_message)
    post_twitter_with_image(twitter_message, image_path)

    logging.info("SCAN FINISHED")

# ================= ROUTES =================

@app.route("/")
def home():
    return "CHAIN MOMENTUM BOT ACTIVE", 200

@app.route("/run-scan")
def run_scan_route():
    scan()
    return "SCAN EXECUTED", 200

# ================= START =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)