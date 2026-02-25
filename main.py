import os
import tweepy
import schedule
import time
from datetime import datetime
import threading
from flask import Flask

# ===== TWITTER SETUP =====
api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
access_secret = os.getenv("ACCESS_SECRET")

auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
api = tweepy.API(auth)

def tweet_crypto():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    message = f"🚀 Chain_Momentum Update\n\nBTC | ETH | SOL\nTime: {now}\n\n#Crypto #BTC #ETH #SOL"
    api.update_status(message)
    print("Tweet sent!")

schedule.every().minute.do(tweet_crypto)

# ===== WEB SERVER (WAJIB UNTUK RAILWAY) =====
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_bot():
    print("Bot started...")
    while True:
        schedule.run_pending()
        time.sleep(30)

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_bot).start()
run_web()
