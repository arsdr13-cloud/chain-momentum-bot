import requests
import matplotlib.pyplot as plt
import tweepy
import schedule
import time
import os
import random
from flask import Flask
import threading

# ==============================
# STORAGE (ANTI DUPLICATE REPLY)
# ==============================

REPLIED_FILE = "replied_ids.txt"

def load_replied_ids():
    if not os.path.exists(REPLIED_FILE):
        return set()
    with open(REPLIED_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_replied_id(tweet_id):
    with open(REPLIED_FILE, "a") as f:
        f.write(f"{tweet_id}\n")

replied_ids = load_replied_ids()

# ==============================
# ENGAGEMENT PROMPT
# ==============================

def engagement_prompt():
    prompts = [
        "Bullish or bearish this week?",
        "Are you positioned or waiting?",
        "What’s your bias right now?",
        "Agree with this structure?"
    ]
    return random.choice(prompts)

# ==============================
# MARKET DATA
# ==============================

def get_market_data():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "bitcoin,ethereum,solana",
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return None
        return response.json()
    except:
        return None

# ==============================
# STRUCTURED INSIGHT
# ==============================

def generate_structured_insight(data):
    btc = data["bitcoin"]["usd"]
    btc_change = data["bitcoin"]["usd_24h_change"]

    if btc_change > 2:
        bias = "Bullish"
        scenario = "Momentum continuation likely if breakout holds."
    elif btc_change < -2:
        bias = "Bearish"
        scenario = "Possible downside continuation if support fails."
    else:
        bias = "Neutral"
        scenario = "Consolidation range before expansion."

    key_level = round(btc * 0.98, 0)
    invalidation = round(btc * 0.95, 0)

    return {
        "bias": bias,
        "key_level": key_level,
        "invalidation": invalidation,
        "scenario": scenario
    }

# ==============================
# CHART GENERATOR
# ==============================

def generate_chart():
    coins = {
        "bitcoin": "BTC",
        "ethereum": "ETH",
        "solana": "SOL"
    }

    plt.figure()

    for coin_id, symbol in coins.items():
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": "1"}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "prices" not in data:
            continue

        prices = [p[1] for p in data["prices"]]
        base = prices[0]
        normalized = [(p/base)*100 for p in prices]

        plt.plot(normalized, label=symbol)

    plt.legend()
    plt.title("24H Performance (%)")
    plt.xlabel("Time")
    plt.ylabel("Performance %")

    filename = "chart.png"
    plt.savefig(filename)
    plt.close()
    return filename

# ==============================
# TWITTER AUTH
# ==============================

client = tweepy.Client(
    consumer_key=os.getenv("API_KEY"),
    consumer_secret=os.getenv("API_SECRET"),
    access_token=os.getenv("ACCESS_TOKEN"),
    access_token_secret=os.getenv("ACCESS_SECRET")
)

auth = tweepy.OAuth1UserHandler(
    os.getenv("API_KEY"),
    os.getenv("API_SECRET"),
    os.getenv("ACCESS_TOKEN"),
    os.getenv("ACCESS_SECRET")
)
api_v1 = tweepy.API(auth)

# ==============================
# POST UPDATE
# ==============================

def post_update():
    print("Running post_update...")
    data = get_market_data()
    if not data:
        print("Market data failed.")
        return

    try:
        btc = data["bitcoin"]["usd"]
        insight = generate_structured_insight(data)
        chart = generate_chart()

        text = (
            f"MARKET STRUCTURE UPDATE\n\n"
            f"BTC Price: ${btc:,.0f}\n"
            f"Bias: {insight['bias']}\n"
            f"Key Level: ${insight['key_level']:,.0f}\n"
            f"Invalidation: ${insight['invalidation']:,.0f}\n\n"
            f"Scenario:\n{insight['scenario']}\n\n"
            f"Manage risk properly."
        )

        if random.random() < 0.3:
            text += "\n\n" + engagement_prompt()

        media = api_v1.media_upload(chart)
        client.create_tweet(text=text, media_ids=[media.media_id])

        print("Tweet posted!")

    except Exception as e:
        print("Post error:", e)

# ==============================
# WEEKLY RECAP THREAD
# ==============================

def weekly_recap_thread():
    data = get_market_data()
    if not data:
        return

    btc = data["bitcoin"]["usd"]
    btc_change = data["bitcoin"]["usd_24h_change"]

    tweets = [
        "WEEKLY CRYPTO RECAP 🧵",
        f"BTC closed at ${btc:,.0f}",
        f"Weekly change: {btc_change:.2f}%",
        "Market structure remains intact unless key levels break.",
        "Position smart. Protect capital."
    ]

    first = client.create_tweet(text=tweets[0])
    reply_id = first.data["id"]

    for t in tweets[1:]:
        r = client.create_tweet(text=t, in_reply_to_tweet_id=reply_id)
        reply_id = r.data["id"]

# ==============================
# DAILY THREAD
# ==============================

def daily_thread():
    data = get_market_data()
    if not data:
        return

    btc = data["bitcoin"]["usd"]
    btc_change = data["bitcoin"]["usd_24h_change"]
    direction = "bullish 🚀" if btc_change > 0 else "bearish ⚠️"

    tweets = [
        f"📊 Daily Crypto Insight\n\nBTC ${btc:.0f} ({btc_change:.2f}%)",
        f"1️⃣ Market sentiment looks {direction}",
        "2️⃣ Watch key resistance & support",
        "3️⃣ Manage risk properly",
        "Follow for structured crypto insight."
    ]

    first = client.create_tweet(text=tweets[0])
    reply_id = first.data["id"]

    for t in tweets[1:]:
        r = client.create_tweet(text=t, in_reply_to_tweet_id=reply_id)
        reply_id = r.data["id"]

# ==============================
# AUTO REPLY
# ==============================

def auto_reply():
    global replied_ids

    me = client.get_me()
    mentions = client.get_users_mentions(id=me.data.id, max_results=5)

    if mentions and mentions.data:
        for tweet in mentions.data:
            if str(tweet.id) in replied_ids:
                continue

            try:
                client.create_tweet(
                    text="Thanks for engaging 🚀",
                    in_reply_to_tweet_id=tweet.id
                )
                replied_ids.add(str(tweet.id))
                save_replied_id(tweet.id)
            except:
                pass

# ==============================
# SMART ENGAGEMENT
# ==============================

def smart_engagement():
    tweets = client.search_recent_tweets(
        query="BTC OR Ethereum OR Solana -is:retweet",
        max_results=5
    )

    if tweets.data:
        for tweet in tweets.data:
            try:
                client.like(tweet.id)
            except:
                pass

# ==============================
# SCHEDULE
# ==============================

schedule.every().sunday.at("20:00").do(weekly_recap_thread)
schedule.every().day.at("06:00").do(post_update)
schedule.every().day.at("09:00").do(daily_thread)
schedule.every().day.at("12:00").do(post_update)
schedule.every().day.at("18:00").do(post_update)
schedule.every().day.at("22:00").do(post_update)

schedule.every(60).minutes.do(auto_reply)

print("Bot started...")

# ==============================
# FLASK KEEP ALIVE
# ==============================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ==============================
# RUN SCHEDULER IN BACKGROUND
# ==============================

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(30)

threading.Thread(target=run_scheduler, daemon=True).start()

# ==============================
# RUN FLASK (MAIN PROCESS)
# ==============================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
