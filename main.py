import requests
import matplotlib.pyplot as plt
import tweepy
import schedule
import time
import os
import random

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
# AI CAPTION
# ==============================

def generate_caption(data):
    btc_change = data["bitcoin"]["usd_24h_change"]

    if btc_change > 3:
        tone = "Strong bullish momentum 🚀"
    elif btc_change < -3:
        tone = "Market correction phase ⚠️"
    else:
        tone = "Sideways consolidation 📊"

    templates = [
        f"{tone}\nTrade smart.",
        f"{tone}\nRisk management first.",
        f"{tone}\nWatch key levels."
    ]

    return random.choice(templates)

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
        print("Market data failed. Skipping post.")
        return

    try:
        btc = data["bitcoin"]["usd"]
        eth = data["ethereum"]["usd"]
        sol = data["solana"]["usd"]

        btc_change = data["bitcoin"]["usd_24h_change"]
        eth_change = data["ethereum"]["usd_24h_change"]
        sol_change = data["solana"]["usd_24h_change"]

        def arrow(change):
            return "🟢" if change >= 0 else "🔴"

        caption = generate_caption(data)
        chart = generate_chart()

        text = f"""
📊 Market Snapshot

BTC ${btc:,.0f} {arrow(btc_change)} {btc_change:.2f}%
ETH ${eth:,.0f} {arrow(eth_change)} {eth_change:.2f}%
SOL ${sol:,.0f} {arrow(sol_change)} {sol_change:.2f}%

24H Insight:
{caption}

#Crypto #Bitcoin #Ethereum #Solana
"""

        media = api_v1.media_upload(chart)
        client.create_tweet(text=text, media_ids=[media.media_id])

        print("Tweet posted successfully!")

    except Exception as e:
        print("Error in post_update:", e)
        
# ==============================
# AUTO REPLY
# ==============================

def auto_reply():
    me = client.get_me()
    mentions = client.get_users_mentions(id=me.data.id, max_results=5)

    if mentions.data:
        for tweet in mentions.data:
            client.create_tweet(
                text="Thanks for engaging 🚀",
                in_reply_to_tweet_id=tweet.id
            )

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
# DAILY THREAD
# ==============================

def daily_thread():
    data = get_market_data()

    # SAFETY CHECK
    if not data:
        print("Market data failed. Skipping thread.")
        return

    btc = data["bitcoin"]["usd"]
    btc_change = data["bitcoin"]["usd_24h_change"]
    direction = "bullish 🚀" if btc_change > 0 else "bearish ⚠️"

    tweets = [
        f"📊 Daily Crypto Insight\n\nBTC currently ${btc:.0f} ({btc_change:.2f}%)",
        f"1️⃣ Market sentiment looks {direction}",
        "2️⃣ Watch key resistance & support levels",
        "3️⃣ Manage risk properly in volatile sessions",
        "Follow for consistent crypto analysis 🔥"
    ]

    first = client.create_tweet(text=tweets[0])
    reply_id = first.data["id"]

    for t in tweets[1:]:
        r = client.create_tweet(text=t, in_reply_to_tweet_id=reply_id)
        reply_id = r.data["id"]

# ==============================
# SCHEDULE
# ==============================

schedule.every().day.at("06:00").do(post_update)
schedule.every().day.at("09:00").do(daily_thread)   # ← TAMBAH INI
schedule.every().day.at("12:00").do(post_update)
schedule.every().day.at("18:00").do(post_update)
schedule.every().day.at("22:00").do(post_update)

schedule.every(60).minutes.do(auto_reply)
schedule.every(30).minutes.do(smart_engagement)

print("Bot started...")

while True:
    schedule.run_pending()
    time.sleep(30)
