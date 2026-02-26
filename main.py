import os
import time
import threading
import logging
import requests
import schedule
from flask import Flask

# ==============================
# SERVER SAFE BACKEND
# ==============================
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ==============================
# LOGGING
# ==============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ==============================
# FLASK APP (HEALTH CHECK)
# ==============================
app = Flask(__name__)

@app.route("/")
def health():
    return "Bot is running", 200


# ==============================
# ENV VARIABLES
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

COINS = ["bitcoin", "ethereum", "solana"]


# ==============================
# TELEGRAM
# ==============================
def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": text,
        }
        r = requests.post(url, json=payload, timeout=10)
        logging.info(f"Telegram text status: {r.status_code}")
    except Exception as e:
        logging.error(f"Telegram error: {e}")


def send_telegram_photo(filepath):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        with open(filepath, "rb") as photo:
            r = requests.post(
                url,
                data={"chat_id": CHAT_ID},
                files={"photo": photo},
                timeout=15
            )
        logging.info(f"Telegram photo status: {r.status_code}")
    except Exception as e:
        logging.error(f"Telegram photo error: {e}")


# ==============================
# TWITTER (X)
# ==============================
def post_to_twitter(text):
    try:
        import tweepy

        auth = tweepy.OAuth1UserHandler(
            TWITTER_API_KEY,
            TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_SECRET
        )

        api = tweepy.API(auth)
        api.update_status(text)
        logging.info("Tweet posted successfully")

    except Exception as e:
        logging.error(f"Twitter error: {e}")


# ==============================
# CHART GENERATION
# ==============================
def generate_chart(coin):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
        params = {"vs_currency": "usd", "days": "1"}

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        prices = [p[1] for p in data["prices"]]

        plt.figure()
        plt.plot(prices)
        plt.title(f"{coin.upper()} 24H Chart")
        plt.xlabel("Time")
        plt.ylabel("Price")
        filename = f"{coin}.png"
        plt.savefig(filename)
        plt.close()

        return filename

    except Exception as e:
        logging.error(f"Chart error {coin}: {e}")
        return None


# ==============================
# DAILY REPORT
# ==============================
def daily_report():
    logging.info("Running daily report...")

    for coin in COINS:
        file = generate_chart(coin)
        if file:
            send_telegram_photo(file)

    message = "📊 Daily Crypto Update (BTC, ETH, SOL) is live!"
    send_telegram_message(message)
    post_to_twitter(message)


# ==============================
# WEEKLY REPORT
# ==============================
def weekly_report():
    message = "📅 Weekly Crypto Recap is live. Stay sharp!"
    send_telegram_message(message)
    post_to_twitter(message)


# ==============================
# SCHEDULER
# ==============================
def run_scheduler():
    logging.info("Scheduler started")

    schedule.every().day.at("09:00").do(daily_report)
    schedule.every().monday.at("20:00").do(weekly_report)

    while True:
        schedule.run_pending()
        time.sleep(30)


# ==============================
# START EVERYTHING
# ==============================
def start_background():
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logging.info("Bot started successfully")

start_background()


# ==============================
# RUN FLASK (Railway compatible)
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
