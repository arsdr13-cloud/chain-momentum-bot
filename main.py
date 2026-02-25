import os
import tweepy
import schedule
import time
from datetime import datetime
from flask import Flask
import threading

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

# ===== SCHEDULE =====
schedule.every().day.at("06:00").do(tweet_crypto)
schedule.every().day.at("12:00").do(tweet_crypto)
schedule.every().day.at("18:00").do(tweet_crypto)
schedule.every().day.at("22:00").do(tweet_crypto)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(30)

threading.Thread(target=run_schedule, daemon=True).start()

# ===== FLASK (MAIN PROCESS) =====
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

if __name__ == "__main__":
    print("Bot started...")
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
