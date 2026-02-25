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
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin,ethereum,solana",
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }
    return requests.get(url, params=params).json()

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
        data = requests.get(url, params=params).json()
        prices = [p[1] for p in data["prices"]]
        plt.plot(prices, label=symbol)

    plt.legend()
    plt.title("24H Crypto Price Chart")
    plt.xlabel("Time")
    plt.ylabel("Price USD")

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
    data = get_market_data()

    btc = data["bitcoin"]["usd"]
    eth = data["ethereum"]["usd"]
    sol = data["solana"]["usd"]

    caption = generate_caption(data)
    chart = generate_chart()

    text = f"""
🚀 Chain Momentum Update

BTC: ${btc:.2f}
ETH: ${eth:.2f}
SOL: ${sol:.2f}

{caption}

#Crypto #BTC #ETH #SOL
"""

    media = api_v1.media_upload(chart)
    client.create_tweet(text=text, media_ids=[media.media_id])

    print("Tweet posted!")

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
# SCHEDULE
# ==============================

schedule.every().day.at("06:00").do(post_update)
schedule.every().day.at("12:00").do(post_update)
schedule.every().day.at("18:00").do(post_update)
schedule.every().day.at("22:00").do(post_update)

schedule.every(60).minutes.do(auto_reply)

print("Bot started...")

while True:
    schedule.run_pending()
    time.sleep(30)
