import os
import time
import threading
import logging
import requests
import schedule
from flask import Flask

# ==============================
# IMPORTANT FOR SERVER ENV
# ==============================
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from datetime import datetime

# ==============================
# LOGGING SETUP
# ==============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ==============================
# FLASK APP
# ==============================
app = Flask(__name__)

@app.route("/")
def health():
    return "OK", 200


# ==============================
# CONFIG
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

COINS = ["bitcoin", "ethereum", "solana"]


# ==============================
# TELEGRAM SEND FUNCTION
# ==============================
def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
        r = requests.post(url, json=payload, timeout=10)
        logging.info(f"Telegram response: {r.status_code}")
    except Exception as e:
        logging.error(f"Telegram send error: {e}")


# ==============================
# CHART GENERATION
# ==============================
def generate_chart(coin):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": "1"
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            logging.warning(f"{coin} API error {response.status_code}")
            return None

        data = response.json()
        if "prices" not in data:
            return None

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
        filename = generate_chart(coin)

        if filename:
            try:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                with open(filename, "rb") as photo:
                    requests.post(
                        url,
                        data={"chat_id": CHAT_ID},
                        files={"photo": photo},
                        timeout=15
                    )
                logging.info(f"{coin} chart sent")
            except Exception as e:
                logging.error(f"Send photo error: {e}")

    send_telegram_message("📊 Daily Crypto Update selesai.")


# ==============================
# WEEKLY REPORT
# ==============================
def weekly_report():
    logging.info("Running weekly report...")
    send_telegram_message("📅 Weekly market recap is live.")


# ==============================
# SCHEDULER LOOP
# ==============================
def run_scheduler():
    logging.info("Scheduler started")

    schedule.every().day.at("09:00").do(daily_report)
    schedule.every().monday.at("20:00").do(weekly_report)

    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            logging.error(f"Scheduler error: {e}")
        time.sleep(30)


# ==============================
# START BACKGROUND THREAD
# ==============================
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

logging.info("Bot started successfully")
