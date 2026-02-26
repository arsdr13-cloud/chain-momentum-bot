import os
import time
import logging
import requests
import pandas as pd
from flask import Flask
import tweepy
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")

SCAN_INTERVAL = 15
TIMEFRAME = "4H"
RR_RATIO = 2

PAIRS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT"]

last_signal = {}

logging.basicConfig(level=logging.INFO)

# ================= TELEGRAM =================

def send_telegram(text):
    try:
        if not BOT_TOKEN or not CHAT_ID:
            return

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        requests.post(
            url,
            json={"chat_id": CHAT_ID, "text": text},
            timeout=10
        )
    except Exception as e:
        logging.error(f"Telegram error: {e}")

# ================= TWITTER =================

def post_twitter(message):
    try:
        client = tweepy.Client(
            consumer_key=os.getenv("TW_API_KEY"),
            consumer_secret=os.getenv("TW_API_SECRET"),
            access_token=os.getenv("TW_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TW_ACCESS_SECRET")
        )

        response = client.create_tweet(text=message)

        logging.info(f"✅ Tweet sent: {response.data}")

    except Exception as e:
        logging.error(f"❌ Twitter error: {e}")
# ================= DATA FETCH =================

def fetch_data(symbol):
    try:
        coin = symbol.replace("USDT","").lower()

        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"

        params = {
            "vs_currency":"usd",
            "days":"120",
            "interval":"daily"
        }

        r = requests.get(url, params=params, timeout=15)

        if r.status_code != 200:
            return None

        data = r.json().get("prices")
        if not data:
            return None

        df = pd.DataFrame(data, columns=["timestamp","close"])
        df["close"] = df["close"].astype(float)

        df["ema50"] = df["close"].ewm(span=50).mean()
        df["ema200"] = df["close"].ewm(span=200).mean()

        df["tr"] = abs(df["close"] - df["close"].shift())
        df["atr"] = df["tr"].rolling(14).mean()

        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        rs = gain.rolling(14).mean() / loss.rolling(14).mean()
        df["rsi"] = 100 - (100/(1+rs))

        return df

    except Exception as e:
        logging.error(f"{symbol} fetch error: {e}")
        return None

# ================= SIGNAL =================

def detect_signal(df):
    try:
        if len(df) < 210:
            return None

        last = df.iloc[-1]

        trend_up = last["ema50"] > last["ema200"]
        trend_down = last["ema50"] < last["ema200"]

        breakout_up = last["close"] > df["close"].rolling(20).max().iloc[-2]
        breakout_down = last["close"] < df["close"].rolling(20).min().iloc[-2]

        rsi_buy = 45 < last["rsi"] < 65
        rsi_sell = 35 < last["rsi"] < 55

        if trend_up and breakout_up and rsi_buy:
            return "BUY"

        if trend_down and breakout_down and rsi_sell:
            return "SELL"

        return None

    except Exception as e:
        logging.error(f"Signal error: {e}")
        return None

# ================= SCAN =================

def scan():
    logging.info("=== SCANNING MARKET ===")

    for symbol in PAIRS:
        try:
            logging.info(f"Scanning {symbol}...")
            time.sleep(1)

            df = fetch_data(symbol)
            if df is None:
                continue

            signal = detect_signal(df)

            if not signal:
                logging.info(f"No signal for {symbol}")
                continue

            if last_signal.get(symbol) == signal:
                continue

            logging.info(f"Signal detected for {symbol}: {signal}")

            last = df.iloc[-1]
            entry = last["close"]
            atr = last["atr"]

            if pd.isna(atr):
                continue

            if signal == "BUY":
                sl = entry - atr
                tp = entry + (atr * RR_RATIO)
            else:
                sl = entry + atr
                tp = entry - (atr * RR_RATIO)

            message = f"""🔥 ELITE {signal} SIGNAL ({TIMEFRAME})

Pair: {symbol}
Entry: {round(entry,4)}
Stop Loss: {round(sl,4)}
Take Profit: {round(tp,4)}
Risk:Reward 1:{RR_RATIO}
ATR Dynamic SL"""

            send_telegram(message)
            post_twitter(message)

            last_signal[symbol] = signal

        except Exception as e:
            logging.error(f"{symbol} scan error: {e}")


# ================= SUMMARY =================

def daily_summary():
    send_telegram("📊 Daily Market Scan Completed (ELITE BOT)")

# ================= SCHEDULER =================

    logging.info("🚀 ELITE BOT STARTED")
    scheduler.start()
    
    scheduler = BackgroundScheduler(timezone="Asia/Jakarta")
    scheduler.add_job(scan, 'cron', hour='*/4', minute=3)
    scheduler.start()

    logging.info("🚀 ELITE BOT STARTED")
# ================= FLASK =================

app = Flask(__name__)

@app.route("/")
def home():
    return "ELITE BOT RUNNING", 200


    



