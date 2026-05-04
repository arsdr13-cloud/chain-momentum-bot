import os
import logging
import requests
import matplotlib.pyplot as plt
from flask import Flask, request
import tweepy
from datetime import datetime
import json
import random

# ================= CONFIG =================

CONTRACT = "x95HN3DWvbfCBtTjGm587z8suK3ec6cwQwgZNLbWKyp"

TW_BEARER_TOKEN = os.getenv("TW_BEARER_TOKEN")
TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")

SECRET_KEY = os.getenv("SECRET_KEY")  # 🔒 WAJIB SET DI RAILWAY

DATA_FILE = "price_memory.json"

TWEET_COOLDOWN = 14400  # 4 jam
MIN_RUN_INTERVAL = 60   # minimal 1 menit antar hit endpoint

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# ================= MEMORY (GANTI FILE COOLDOWN) =================

last_tweet_time = 0
last_run_time = 0

# ================= TWITTER =================

client = tweepy.Client(
    bearer_token=TW_BEARER_TOKEN,
    consumer_key=TW_API_KEY,
    consumer_secret=TW_API_SECRET,
    access_token=TW_ACCESS_TOKEN,
    access_token_secret=TW_ACCESS_SECRET,
)

auth_v1 = tweepy.OAuth1UserHandler(
    TW_API_KEY,
    TW_API_SECRET,
    TW_ACCESS_TOKEN,
    TW_ACCESS_SECRET
)

api_v1 = tweepy.API(auth_v1)

# ================= STYLE =================

def human_hook():
    return random.choice([
        "HACHI structure update.",
        "HACHI moving again.",
        "Quick HACHI check.",
        "Watching HACHI closely.",
        "HACHI snapshot."
    ])

def human_closing():
    return random.choice([
        "Watching next move.",
        "Let’s see if momentum builds.",
        "Eyes on liquidity.",
        "Next reaction matters.",
        "Waiting continuation."
    ])

def session_label():
    now = datetime.utcnow()
    hour = now.hour

    if hour < 8:
        session = "Asia session"
    elif hour < 16:
        session = "EU session"
    else:
        session = "US session"

    return f"{session} | {now.strftime('%H:%M UTC')}"

# ================= STORAGE =================

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

def load_json(file):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return {}

# ================= FETCH =================

def fetch_price():
    url = f"https://api.dexscreener.com/latest/dex/tokens/{CONTRACT}"

    try:
        r = requests.get(url, timeout=20)

        if r.status_code != 200:
            logging.info("Dex fetch error")
            return None

        data = r.json()
        pair = data["pairs"][0]
        return float(pair["priceUsd"])

    except Exception as e:
        logging.info(f"Fetch error: {e}")
        return None

# ================= PRICE MEMORY =================

def update_price_memory(price):
    memory = load_json(DATA_FILE)
    now = datetime.utcnow().timestamp()

    memory[str(now)] = {"HACHI": price}
    save_json(DATA_FILE, memory)

def get_price_6h_ago():
    memory = load_json(DATA_FILE)

    if not memory:
        return None

    now = datetime.utcnow().timestamp()
    target = now - 21600

    closest = None
    closest_diff = None

    for t in memory:
        t_float = float(t)
        diff = abs(t_float - target)

        if closest_diff is None or diff < closest_diff:
            closest_diff = diff
            closest = memory[t]

    return closest

# ================= TWEET =================

def build_tweet(change, price):
    hook = human_hook()
    closing = human_closing()
    session = session_label()

    if change > 5:
        signal = "Momentum picking up fast."
    elif change > 0:
        signal = "Holding bullish structure."
    elif change < -5:
        signal = "Heavy selling pressure."
    elif change < 0:
        signal = "Minor pullback."
    else:
        signal = "Sideways movement."

    return f"""{hook}

{signal}

6H Map | {session}

$HACHI ${price:.8f} {change:+.2f}%

{closing}
""".strip()

# ================= CHART =================

def generate_chart(change):
    plt.figure(figsize=(5,4))
    color = "#00C853" if change >= 0 else "#FF1744"

    plt.bar(["HACHI"], [change], color=color)
    plt.axhline(0)
    plt.title("HACHI 6H Performance")
    plt.text(0, change, f"{change:+.2f}%", ha="center")

    plt.savefig("chart.png", dpi=200)
    plt.close()

    return "chart.png"

# ================= GUARD =================

def can_run():
    global last_run_time
    now = datetime.utcnow().timestamp()

    if now - last_run_time < MIN_RUN_INTERVAL:
        return False

    last_run_time = now
    return True

def can_tweet():
    global last_tweet_time
    now = datetime.utcnow().timestamp()

    if now - last_tweet_time < TWEET_COOLDOWN:
        return False

    return True

def record_tweet():
    global last_tweet_time
    last_tweet_time = datetime.utcnow().timestamp()

# ================= POST =================

def post_tweet(message, image=None):
    try:
        if image:
            media = api_v1.media_upload(image)
            client.create_tweet(text=message, media_ids=[media.media_id_string])
        else:
            client.create_tweet(text=message)

        record_tweet()

    except Exception as e:
        logging.info(f"Tweet failed: {e}")

# ================= SCAN =================

def scan():
    price = fetch_price()
    if not price:
        return "NO PRICE"

    update_price_memory(price)

    price_6h = get_price_6h_ago()
    if not price_6h:
        return "WAITING DATA"

    change = ((price - price_6h["HACHI"]) / price_6h["HACHI"]) * 100
    tweet = build_tweet(change, price)

    if can_tweet():
        chart = generate_chart(change)
        post_tweet(tweet, chart)
        logging.info("TWEET SENT")
        return tweet
    else:
        return "COOLDOWN ACTIVE"

# ================= ROUTES =================

@app.route("/")
def home():
    return "HACHI BOT ACTIVE", 200

@app.route("/run-scan")
def run_scan():
    logging.info("RUN SCAN TRIGGERED")

    key = request.args.get("key")
    if key != SECRET_KEY:
        logging.warning("UNAUTHORIZED ACCESS")
        return "Unauthorized", 403

    if not can_run():
        return "Too many requests", 429

    result = scan()
    return result, 200

# ================= START =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    app.run(
        host="0.0.0.0",
        port=port
    )