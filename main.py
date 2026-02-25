import os
import tweepy
import schedule
import time
from datetime import datetime

# ===== TWITTER SETUP V2 =====
api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
access_secret = os.getenv("ACCESS_SECRET")

client = tweepy.Client(
    consumer_key=api_key,
    consumer_secret=api_secret,
    access_token=access_token,
    access_token_secret=access_secret
)

def tweet_crypto():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    message = f"🚀 Chain_Momentum Update\n\nBTC | ETH | SOL\nTime: {now}\n\n#Crypto #BTC #ETH #SOL"
    
    client.create_tweet(text=message)
    print("Tweet sent!")

schedule.every().day.at("06:00").do(tweet_crypto)
schedule.every().day.at("12:00").do(tweet_crypto)
schedule.every().day.at("18:00").do(tweet_crypto)
schedule.every().day.at("22:00").do(tweet_crypto)
print("Bot started...")

while True:
    schedule.run_pending()
    time.sleep(30)
