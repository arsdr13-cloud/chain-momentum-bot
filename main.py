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

TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")
print("TW_API_KEY:", TW_API_KEY)
print("TW_ACCESS_TOKEN:", TW_ACCESS_TOKEN)
print("TW_API_SECRET:", TW_API_SECRET)
print("TW_ACCESS_SECRET:", TW_ACCESS_SECRET)
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
                data={"chat_id": CHAT_ID, "caption": caption[:1024]},
                files={"photo": img},
                timeout=20
            )
        logging.info("Telegram sent")
    except Exception as e:
        logging.error(f"Telegram error: {e}")

# ================= TWITTER (CLEAN - NO AUTO LIKE) =================

# ================= TWITTER (CLEAN - WORKING) =================

def post_twitter_with_image(message, image_path):
    try:
        auth = tweepy.OAuth1UserHandler(
            TW_API_KEY,
            TW_API_SECRET,
            TW_ACCESS_TOKEN,
            TW_ACCESS_SECRET
        )

        api_v1 = tweepy.API(auth)

        media = api_v1.media_upload(image_path)

        client = tweepy.Client(
            consumer_key=TW_API_KEY,
            consumer_secret=TW_API_SECRET,
            access_token=TW_ACCESS_TOKEN,
            access_token_secret=TW_ACCESS_SECRET
        )

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

# ================= NEWS =================

def fetch_latest_news():
    try:
        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        r = requests.get(url, timeout=20)

        if r.status_code != 200:
            return "No major crypto headlines today."

        data = r.json()
        for article in data.get("Data", []):
            title = article.get("title", "")
            if title:
                return title

        return "No major crypto headlines today."
    except:
        return "No major crypto headlines today."

# ================= TWITTER TEXT (INSTITUTIONAL + CTA) =================

def build_twitter_text(btc_price, btc_change, eth_price, eth_change, sol_price, sol_change):

    headline = fetch_latest_news()
    avg_change = (btc_change + eth_change + sol_change) / 3

    if avg_change < -3:
        market_status = "⚠️ High Volatility | Defensive Mode"
    elif avg_change < 0:
        market_status = "📉 Risk-Off Sentiment"
    else:
        market_status = "📈 Risk-On Momentum"

    tweet_text = f"""🚀 CHAIN MOMENTUM | Market Pulse

BTC ${btc_price:,.0f} ({btc_change:.2f}%)
ETH ${eth_price:,.0f} ({eth_change:.2f}%)
SOL ${sol_price:,.0f} ({sol_change:.2f}%)

📰 {headline}

{market_status}

Are institutions accumulating or distributing?
On-chain flows in focus.

#Crypto #BTC #ETH #SOL

💬 Follow for daily institutional insights  
🔁 Retweet to share market intelligence  
❤️ Like if you trade smart
"""

    return tweet_text[:280]

# ================= TELEGRAM MESSAGE (HEDGE FUND STYLE) =================

def build_telegram_message(data):

    now = datetime.utcnow().strftime("%d %b %Y | %H:%M UTC")

    btc_price = data["BTC"]["quote"]["USD"]["price"]
    btc_change = data["BTC"]["quote"]["USD"]["percent_change_24h"]

    eth_price = data["ETH"]["quote"]["USD"]["price"]
    eth_change = data["ETH"]["quote"]["USD"]["percent_change_24h"]

    sol_price = data["SOL"]["quote"]["USD"]["price"]
    sol_change = data["SOL"]["quote"]["USD"]["percent_change_24h"]

    avg_change = (btc_change + eth_change + sol_change) / 3

    if avg_change < -3:
        risk_level = "HIGH"
        strategy = "Capital Preservation"
        volatility = "Elevated"
    elif avg_change < 0:
        risk_level = "MODERATE"
        strategy = "Reduce Leverage"
        volatility = "Medium"
    else:
        risk_level = "LOW"
        strategy = "Trend Following"
        volatility = "Stable"

    # Institutional Insight
    if avg_change < -5:
        insight = "Broad market distribution phase detected."
    elif avg_change < -2:
        insight = "Sell pressure increasing across majors."
    elif avg_change < 0:
        insight = "Short-term corrective structure."
    else:
        insight = "Momentum expansion phase."

    headline = fetch_latest_news()

    message = f"""🚀 CHAIN MOMENTUM REPORT
🕒 {now}

📊 MARKET SNAPSHOT
BTC : ${btc_price:,.0f} ({btc_change:.2f}%)
ETH : ${eth_price:,.0f} ({eth_change:.2f}%)
SOL : ${sol_price:,.0f} ({sol_change:.2f}%)

📈 Risk Level : {risk_level}
📊 Volatility Index : {volatility}
🛡 Suggested Strategy : {strategy}

🧠 Market Insight :
{insight}

📰 Top Headline
{headline}

Stay Ahead. Trade Smart.
"""

    return message

# ================= PREMIUM DARK CHART =================

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
            color="white",
            fontweight="bold"
        )

    plt.axhline(0, color="white", linewidth=1)

    plt.title("CHAIN MOMENTUM | 24H CHANGE", color="white", fontweight="bold")
    plt.ylabel("24H %", color="white")
    plt.xticks(color="white")
    plt.yticks(color="white")

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

    btc_price = data["BTC"]["quote"]["USD"]["price"]
    btc_change = data["BTC"]["quote"]["USD"]["percent_change_24h"]

    eth_price = data["ETH"]["quote"]["USD"]["price"]
    eth_change = data["ETH"]["quote"]["USD"]["percent_change_24h"]

    sol_price = data["SOL"]["quote"]["USD"]["price"]
    sol_change = data["SOL"]["quote"]["USD"]["percent_change_24h"]

    telegram_message = build_telegram_message(data)
    twitter_message = build_twitter_text(
        btc_price, btc_change,
        eth_price, eth_change,
        sol_price, sol_change
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
def run_scan():
    scan()
    return "✅ SCAN EXECUTED", 200

# ================= START =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)