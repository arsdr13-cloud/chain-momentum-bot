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
            return None

        return r.json()["data"]

    except:
        return None

# ================= BTC DOMINANCE =================

def fetch_btc_dominance():
    try:
        url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
        r = requests.get(url, headers=headers, timeout=20)

        if r.status_code != 200:
            return 0

        data = r.json()
        return data["data"]["btc_dominance"]
    except:
        return 0

# ================= SENTIMENT ENGINE =================

def detect_market_sentiment(avg_change):
    if avg_change < -5:
        return "🔴 Extreme Fear", "Distribution phase intensifying. Liquidity risk rising."
    elif avg_change < -2:
        return "🟠 Risk-Off", "Defensive positioning dominates. Institutions cautious."
    elif avg_change < 0:
        return "🟡 Neutral-Bearish", "Mild correction. Monitoring structure."
    elif avg_change < 3:
        return "🟢 Neutral-Bullish", "Controlled momentum building."
    else:
        return "🚀 Strong Risk-On", "Expansion phase active. Breakout watch."

# ================= BUILD TWITTER TEXT =================

def build_twitter_text(btc_price, btc_change, eth_price, eth_change, sol_price, sol_change, btc_dominance):

    avg_change = (btc_change + eth_change + sol_change) / 3
    sentiment, insight = detect_market_sentiment(avg_change)

    tweet_text = f"""🚨 Market Update

BTC ${btc_price:,.0f} ({btc_change:.2f}%)
ETH ${eth_price:,.0f} ({eth_change:.2f}%)
SOL ${sol_price:,.0f} ({sol_change:.2f}%)

BTC Dominance: {btc_dominance:.2f}%

{sentiment}
{insight}

Are smart money accumulating — or distributing?

❤️ Like | 🔁 Repost | ➕ Follow Chain_Momentum

#Crypto #BTC #ETH #SOL
"""

    return tweet_text[:280]

# ================= BUILD TELEGRAM MESSAGE =================

def build_telegram_message(data, btc_dominance):

    now = datetime.utcnow().strftime("%d %b %Y | %H:%M UTC")

    btc_price = data["BTC"]["quote"]["USD"]["price"]
    btc_change = data["BTC"]["quote"]["USD"]["percent_change_24h"]

    eth_price = data["ETH"]["quote"]["USD"]["price"]
    eth_change = data["ETH"]["quote"]["USD"]["percent_change_24h"]

    sol_price = data["SOL"]["quote"]["USD"]["price"]
    sol_change = data["SOL"]["quote"]["USD"]["percent_change_24h"]

    avg_change = (btc_change + eth_change + sol_change) / 3
    sentiment, insight = detect_market_sentiment(avg_change)

    message = f"""🚀 CHAIN MOMENTUM REPORT
━━━━━━━━━━━━━━━━━━
🕒 {now}

💰 BTC : ${btc_price:,.0f} ({btc_change:.2f}%)
💰 ETH : ${eth_price:,.0f} ({eth_change:.2f}%)
💰 SOL : ${sol_price:,.0f} ({sol_change:.2f}%)

━━━━━━━━━━━━━━━━━━
📊 BTC Dominance : {btc_dominance:.2f}%
📈 Market Sentiment : {sentiment}

🧠 Insight :
{insight}

━━━━━━━━━━━━━━━━━━
Stay Ahead. Trade Smart.
"""

    return message

# ================= CHART =================

def generate_chart(btc_change, eth_change, sol_change):

    coins = ["BTC", "ETH", "SOL"]
    changes = [btc_change, eth_change, sol_change]
    colors = ["#00C853" if c >= 0 else "#D50000" for c in changes]

    plt.figure(figsize=(8,5), facecolor="#111111")
    ax = plt.gca()
    ax.set_facecolor("#111111")

    bars = plt.bar(coins, changes, color=colors)

    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width()/2,
            height,
            f"{height:.2f}%",
            ha="center",
            va="bottom",
            color="white"
        )

    plt.axhline(0, color="white", linewidth=1)
    plt.title("CHAIN MOMENTUM | 24H CHANGE", color="white")

    # ===== WATERMARK =====
    plt.text(
        0.95, 0.05,
        "ChainMomentum",
        transform=ax.transAxes,
        fontsize=10,
        color="white",
        alpha=0.4,
        ha="right",
        va="bottom"
    )

    plt.tight_layout()
    filename = "market_chart.png"
    plt.savefig(filename, facecolor="#111111")
    plt.close()

    return filename

# ================= SCAN =================

def scan():

    logging.info("=== CHAIN MOMENTUM SCAN ===")

    data = fetch_market_data()
    if not data:
        return

    btc_dominance = fetch_btc_dominance()

    btc_price = data["BTC"]["quote"]["USD"]["price"]
    btc_change = data["BTC"]["quote"]["USD"]["percent_change_24h"]

    eth_price = data["ETH"]["quote"]["USD"]["price"]
    eth_change = data["ETH"]["quote"]["USD"]["percent_change_24h"]

    sol_price = data["SOL"]["quote"]["USD"]["price"]
    sol_change = data["SOL"]["quote"]["USD"]["percent_change_24h"]

    telegram_message = build_telegram_message(data, btc_dominance)
    twitter_message = build_twitter_text(
        btc_price, btc_change,
        eth_price, eth_change,
        sol_price, sol_change,
        btc_dominance
    )

    image_path = generate_chart(btc_change, eth_change, sol_change)

    send_telegram_photo(image_path, telegram_message)
    post_twitter_with_image(twitter_message, image_path)

    logging.info("SCAN FINISHED")

# ================= ROUTES =================

@app.route("/")
def home():
    return "🚀 CHAIN MOMENTUM BOT ACTIVE", 200

@app.route("/run-scan")
def run_scan_route():
    scan()
    return "✅ SCAN EXECUTED", 200

# ================= START =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)