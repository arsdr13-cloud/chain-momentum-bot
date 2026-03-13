import os
import logging
import requests
import matplotlib.pyplot as plt
from flask import Flask
import tweepy
from datetime import datetime, timedelta
import json
import random

# ================= CONFIG =================

CMC_API_KEY = os.getenv("CMC_API_KEY")

TW_BEARER_TOKEN = os.getenv("TW_BEARER_TOKEN")
TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")

COINS = ["BTC","ETH","SOL"]

DATA_FILE = "price_memory.json"
BASELINE_FILE = "baseline.json"

STRUCTURE_FILE = "structure_state.txt"

LAST_TWEET_FILE = "last_tweet_id.txt"
LAST_TWEET_TIME = "last_tweet_time.txt"
LAST_TWEET_TEXT = "last_tweet_text.txt"

TWEET_COOLDOWN = 14400

ETH_ROTATION_THRESHOLD = 0.5
SOL_ROTATION_THRESHOLD = 0.8

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

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

# ================= HUMAN STYLE ENGINE =================

def human_hook():
    hooks = [
        "Market structure update.",
        "Quick liquidity check.",
        "Small structure shift worth watching.",
        "Short market snapshot.",
        "Current rotation view."
    ]
    return random.choice(hooks)

def human_closing():
    endings = [
        "Watching for continuation.",
        "Curious if this rotation holds.",
        "Market reaction from here matters.",
        "Liquidity will decide the next move.",
        "Now watching where bids appear."
    ]
    return random.choice(endings)

def session_label():

    hour = datetime.utcnow().hour

    if hour < 8:
        return "Asia session"

    if hour < 16:
        return "EU session"

    return "US session"

# ================= MAP FOLLOW ENGINE =================

def map_follow_line():

    lines = [
        "Following the 6H structure closely.",
        "Tracking this rotation on the next maps.",
        "Monitoring how this structure develops.",
        "Watching if this rotation expands further.",
        "Tracking liquidity flow into the next cycle."
    ]

    return random.choice(lines)

# ================= STORAGE =================

def save_json(file,data):
    with open(file,"w") as f:
        json.dump(data,f)

def load_json(file):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return {}

# ================= BASELINE SYSTEM =================

def load_baseline():

    if os.path.exists(BASELINE_FILE):

        with open(BASELINE_FILE,"r") as f:
            return json.load(f)

    return None


def save_baseline(btc,eth,sol):

    data={
        "btc":btc,
        "eth":eth,
        "sol":sol
    }

    with open(BASELINE_FILE,"w") as f:
        json.dump(data,f)

# ================= STRUCTURE MEMORY =================

def get_last_structure():

    if os.path.exists(STRUCTURE_FILE):

        with open(STRUCTURE_FILE) as f:
            return f.read().strip()

    return None

def save_structure(rotation):

    with open(STRUCTURE_FILE,"w") as f:
        f.write(rotation)

# ================= THREAD ENGINE =================

def get_last_tweet_id():

    if os.path.exists(LAST_TWEET_FILE):
        with open(LAST_TWEET_FILE) as f:
            return f.read().strip()

    return None

# ================= DUPLICATE CHECK =================

def should_tweet(new_text):

    if os.path.exists(LAST_TWEET_TEXT):

        with open(LAST_TWEET_TEXT) as f:
            last=f.read()

        if last==new_text:
            return False

    with open(LAST_TWEET_TEXT,"w") as f:
        f.write(new_text)

    return True

# ================= TWEET COOLDOWN =================

def can_tweet():

    if os.path.exists(LAST_TWEET_TIME):

        with open(LAST_TWEET_TIME) as f:
            last=float(f.read())

        now=datetime.utcnow().timestamp()

        if now-last < TWEET_COOLDOWN:
            return False

    return True

def record_tweet():

    with open(LAST_TWEET_TIME,"w") as f:
        f.write(str(datetime.utcnow().timestamp()))

# ================= MARKET DATA =================

def fetch_market_data():

    url="https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

    headers={"X-CMC_PRO_API_KEY":CMC_API_KEY}

    params={
        "symbol":",".join(COINS),
        "convert":"USD"
    }

    r=requests.get(url,headers=headers,params=params,timeout=20)

    if r.status_code!=200:
        return None

    return r.json()["data"]

def fetch_global():

    url="https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"

    headers={"X-CMC_PRO_API_KEY":CMC_API_KEY}

    r=requests.get(url,headers=headers,timeout=20)

    if r.status_code!=200:
        return None

    return r.json()["data"]

# ================= PRICE MEMORY =================

def update_price_memory(data):

    memory=load_json(DATA_FILE)

    now=datetime.utcnow().timestamp()

    memory[str(now)]={
        "BTC":data["BTC"]["quote"]["USD"]["price"],
        "ETH":data["ETH"]["quote"]["USD"]["price"],
        "SOL":data["SOL"]["quote"]["USD"]["price"]
    }

    save_json(DATA_FILE,memory)

# ================= PRICE 6H AGO =================

def get_price_6h_ago():

    memory = load_json(DATA_FILE)

    if not memory:
        return None

    now = datetime.utcnow().timestamp()
    target = now - 21600   # 6 jam = 21600 detik

    closest = None
    closest_time = None

    for t in memory:

        t_float = float(t)

        if t_float <= target:

            if closest_time is None or t_float > closest_time:
                closest_time = t_float
                closest = memory[t]

    return closest

# ================= RELATIVE STRENGTH =================

def relative_strength(base,compare):
    return round(compare-base,2)

# ================= ROTATION ENGINE =================

def detect_rotation(btc,eth,sol):

    eth_vs_btc=relative_strength(btc,eth)
    sol_vs_btc=relative_strength(btc,sol)

    if eth_vs_btc>ETH_ROTATION_THRESHOLD:

        if sol_vs_btc>SOL_ROTATION_THRESHOLD:
            return "Broad Alt Rotation"

        return "ETH Relative Strength"

    if sol_vs_btc>SOL_ROTATION_THRESHOLD:
        return "High Beta Expansion"

    if btc>eth and btc>sol:
        return "BTC Leadership"

    return "Balanced Structure"

# ================= BUILD TWEET =================

def build_tweet(btc,eth,sol,btc_dom,btc_price,eth_price,sol_price):

    eth_vs_btc = relative_strength(btc,eth)
    sol_vs_btc = relative_strength(btc,sol)

    rotation = detect_rotation(btc,eth,sol)

    time = datetime.utcnow().strftime("%H:%M UTC")
    session = session_label()
   
    hook = human_hook()
    close = human_closing()
    follow = map_follow_line()
    
    signal_line = f"{rotation} forming across  majors."

    text=f"""{hook}

{signal_line}

6H Liquidity & Positioning Map | {session} | {time}

BTC ${btc_price:,.0f}  {btc:+.2f}%
ETH ${eth_price:,.0f}  {eth:+.2f}%
SOL ${sol_price:,.1f}  {sol:+.2f}%

BTC.D {btc_dom:.2f}%

Rotation: {rotation}

ETH/BTC {eth_vs_btc:+.2f}%
SOL/BTC {sol_vs_btc:+.2f}%

{follow}

{close}
"""

    return text[:280],rotation,eth_vs_btc

# ================= GENERATE CHART =================

def generate_chart(btc,eth,sol):

    coins = ["BTC","ETH","SOL"]
    values = [btc,eth,sol]

    # warna style trading terminal
    green = "#00C853"
    red = "#FF1744"

    colors = [green if v >= 0 else red for v in values]

    plt.figure(figsize=(6,4))

    bars = plt.bar(coins,values,color=colors)

    plt.axhline(0,linewidth=1)

    plt.grid(axis="y",linestyle="--",alpha=0.3)

    plt.title("6H Relative Performance")

    for bar,value in zip(bars,values):

        plt.text(
            bar.get_x()+bar.get_width()/2,
            value,
            f"{value:+.2f}%",
            ha="center",
            va="bottom" if value>=0 else "top"
        )

    filename="chart.png"

    plt.tight_layout()

    plt.savefig(filename,dpi=200)

    plt.close()

    return filename

# ================= POST =================

def post_tweet(message, image=None):

    if not should_tweet(message):
        return

    try:

        if image:

            media = api_v1.media_upload(image)
            media_id = media.media_id_string

            tweet = client.create_tweet(
                text=message,
                media_ids=[media_id]
            )

        else:

            tweet = client.create_tweet(
                text=message
            )

        with open(LAST_TWEET_FILE, "w") as f:
            f.write(str(tweet.data["id"]))

        record_tweet()

    except Exception as e:
        logging.info(f"Tweet failed: {e}")

# ================= SCAN =================

def scan():

    data=fetch_market_data()
    global_data=fetch_global()

    if not data or not global_data:
        return

    btc_now=data["BTC"]["quote"]["USD"]["price"]
    eth_now=data["ETH"]["quote"]["USD"]["price"]
    sol_now=data["SOL"]["quote"]["USD"]["price"]

    update_price_memory(data)

    # ===== BASELINE CHECK =====

    baseline = load_baseline()

    if baseline is None:

        save_baseline(btc_now,eth_now,sol_now)

        logging.info("Baseline created. Waiting next cycle.")

        return

    price_6h = get_price_6h_ago()

    if not price_6h:
        logging.info("Not enough data for 6H      calculation yet.")
        return

    btc_change=((btc_now-price_6h["BTC"])/ price_6h["BTC"])*100
    eth_change=((eth_now-price_6h["ETH"])/price_6h["ETH"])*100
    sol_change=((sol_now-price_6h["SOL"])/price_6h["SOL"])*100

    btc_dom=global_data["btc_dominance"]

    tweet,rotation,eth_vs_btc=build_tweet(
    btc_change,
    eth_change,
    sol_change,
    btc_dom,
    btc_now,
    eth_now,
    sol_now
    )

    last_structure = get_last_structure()

    if rotation == last_structure:
        logging.info("Structure unchanged.  Skipping tweet.")
        return

    chart=generate_chart(
        btc_change,
        eth_change,
        sol_change
    )

    if can_tweet():

        post_tweet(tweet,chart)

        save_structure(rotation)

        save_baseline(btc_now,eth_now,sol_now)

# ================= ROUTES =================

@app.route("/")
def home():
    return "DESK GRADE BOT ACTIVE",200

@app.route("/run-scan")
def run_scan():

    scan()

    return "SCAN COMPLETE",200

# ================= START =================

if __name__ == "__main__":

    port=int(os.environ.get("PORT",8080))

    app.run(
        host="0.0.0.0",
        port=port
    )