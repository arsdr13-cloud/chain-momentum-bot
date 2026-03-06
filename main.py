import os
import logging
import requests
import matplotlib.pyplot as plt
from flask import Flask
import tweepy
from datetime import datetime

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CMC_API_KEY = os.getenv("CMC_API_KEY")

TW_BEARER_TOKEN = os.getenv("TW_BEARER_TOKEN")
TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")

COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

LAST_TWEET_FILE = "last_tweet_id.txt"
STRUCTURE_FILE = "structure_state.txt"
VALIDATION_FILE = "validation_state.txt"
LAST_TWEET_TIME = "last_tweet_time.txt"

TWEET_COOLDOWN = 14400

ETH_ROTATION_THRESHOLD = 0.50
SOL_ROTATION_THRESHOLD = 0.80

MIN_MOVE_FILTER = 0.30

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# ================= TWITTER CLIENT =================

client = tweepy.Client(
    bearer_token=TW_BEARER_TOKEN,
    consumer_key=TW_API_KEY,
    consumer_secret=TW_API_SECRET,
    access_token=TW_ACCESS_TOKEN,
    access_token_secret=TW_ACCESS_SECRET,
    wait_on_rate_limit=True
)

auth_v1 = tweepy.OAuth1UserHandler(
    TW_API_KEY,
    TW_API_SECRET,
    TW_ACCESS_TOKEN,
    TW_ACCESS_SECRET
)

api_v1 = tweepy.API(auth_v1)

# ================= STORAGE =================

def get_last_tweet_id():
    if os.path.exists(LAST_TWEET_FILE):
        with open(LAST_TWEET_FILE,"r") as f:
            return f.read().strip()
    return None

def save_last_tweet_id(tweet_id):
    with open(LAST_TWEET_FILE,"w") as f:
        f.write(str(tweet_id))

# ================= STRUCTURE MEMORY =================

def get_last_structure():
    if os.path.exists(STRUCTURE_FILE):
        with open(STRUCTURE_FILE,"r") as f:
            return f.read().strip()
    return None

def save_structure(state):
    with open(STRUCTURE_FILE,"w") as f:
        f.write(state)

# ================= VALIDATION MEMORY =================

def save_validation_state(value, rotation):
    with open(VALIDATION_FILE,"w") as f:
        f.write(f"{value}|{rotation}")

def get_validation_state():
    if os.path.exists(VALIDATION_FILE):
        with open(VALIDATION_FILE,"r") as f:
            data = f.read().split("|")
            return float(data[0]), data[1]
    return None, None

# ================= COOLDOWN =================

def can_tweet():

    if os.path.exists(LAST_TWEET_TIME):

        with open(LAST_TWEET_TIME,"r") as f:

            last = float(f.read())
            now = datetime.utcnow().timestamp()

            if now - last < TWEET_COOLDOWN:
                return False

    return True

def record_tweet():

    with open(LAST_TWEET_TIME,"w") as f:
        f.write(str(datetime.utcnow().timestamp()))

# ================= TWITTER POST =================

def post_twitter_with_image(message,image_path,thread=False):

    try:

        media = api_v1.media_upload(image_path)

        last_id = get_last_tweet_id()

        if thread and last_id:

            tweet = client.create_tweet(
                text=message,
                media_ids=[media.media_id],
                in_reply_to_tweet_id=last_id
            )

        else:

            tweet = client.create_tweet(
                text=message,
                media_ids=[media.media_id]
            )

        save_last_tweet_id(tweet.data["id"])
        record_tweet()

    except Exception as e:
        logging.error(e)

# ================= BINANCE DATA =================

def fetch_6h_change(symbol):

    url = "https://api.binance.com/api/v3/klines"

    params = {
        "symbol":symbol,
        "interval":"6h",
        "limit":2
    }

    r = requests.get(url,params=params,timeout=20)

    if r.status_code != 200:
        return None,None

    data = r.json()

    open_price = float(data[0][1])
    close_price = float(data[1][4])

    change = ((close_price-open_price)/open_price)*100

    return close_price,change

# ================= BTC DOMINANCE =================

def fetch_btc_dominance():

    url="https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"

    headers={"X-CMC_PRO_API_KEY":CMC_API_KEY}

    r=requests.get(url,headers=headers,timeout=20)

    if r.status_code!=200:
        return None

    return r.json()["data"]["btc_dominance"]

# ================= RELATIVE STRENGTH =================

def relative_strength(base,compare):
    return round(compare-base,2)

# ================= ROTATION ENGINE =================

def detect_rotation(btc,eth,sol,btc_dom):

    eth_vs_btc=relative_strength(btc,eth)
    sol_vs_btc=relative_strength(btc,sol)

    if btc_dom>58 and btc>eth:
        return "BTC Leadership"

    if eth_vs_btc>ETH_ROTATION_THRESHOLD:

        if sol_vs_btc>SOL_ROTATION_THRESHOLD:
            return "Broad Alt Rotation"

        return "ETH Relative Strength"

    if sol_vs_btc>SOL_ROTATION_THRESHOLD:
        return "High Beta Expansion"

    return "Balanced Structure"

# ================= INTERPRETATION ENGINE =================

def detect_interpretation(btc,eth,sol):

    biggest=max(abs(btc),abs(eth),abs(sol))

    if biggest>2.5:
        return "Momentum expansion building"

    if biggest>1.5:
        return "Rotation pressure increasing"

    return None

# ================= VALIDATION =================

def evaluate_validation(current):

    last,last_rotation=get_validation_state()

    if last is None:
        return None

    delta=current-last

    if abs(delta)<MIN_MOVE_FILTER:
        return None

    if last_rotation=="ETH Relative Strength":

        result="Correct" if delta>0 else "Wrong"

    elif last_rotation=="BTC Leadership":

        result="Correct" if delta<0 else "Wrong"

    else:
        return None

    return f"""Validation

ETH/BTC move {delta:+.2f}%

Call result: {result}"""

# ================= CHART =================

def generate_chart(btc,eth,sol):

    labels=["BTC","ETH","SOL"]
    values=[btc,eth,sol]

    plt.figure()

    plt.bar(labels,values)

    plt.title("6H Change")

    plt.savefig("market_chart.png")

    plt.close()

# ================= BUILD TWEET =================

def build_tweet(btc_price,btc_change,eth_price,eth_change,sol_price,sol_change,btc_dom):

    rotation=detect_rotation(btc_change,eth_change,sol_change,btc_dom)

    interpretation=detect_interpretation(btc_change,eth_change,sol_change)

    eth_vs_btc=relative_strength(btc_change,eth_change)
    sol_vs_btc=relative_strength(btc_change,sol_change)

    tweet=f"""6H Structure Map

BTC {btc_change:+.2f}%
ETH {eth_change:+.2f}%
SOL {sol_change:+.2f}%

BTC.D {btc_dom:.2f}%

Rotation: {rotation}

ETH/BTC {eth_vs_btc:+.2f}%
SOL/BTC {sol_vs_btc:+.2f}%"""

    if interpretation:
        tweet+=f"\nInterpretation: {interpretation}"

    last=get_last_structure()

    structure_changed=rotation!=last

    save_structure(rotation)

    save_validation_state(eth_vs_btc,rotation)

    return tweet[:280],structure_changed,eth_vs_btc

# ================= SCAN =================

def scan():

    btc_price,btc_change=fetch_6h_change("BTCUSDT")
    eth_price,eth_change=fetch_6h_change("ETHUSDT")
    sol_price,sol_change=fetch_6h_change("SOLUSDT")

    btc_dom=fetch_btc_dominance()

    if None in [btc_price,eth_price,sol_price,btc_dom]:
        return

    generate_chart(btc_change,eth_change,sol_change)

    tweet,structure_changed,eth_vs_btc=build_tweet(
        btc_price,btc_change,
        eth_price,eth_change,
        sol_price,sol_change,
        btc_dom
    )

    validation=evaluate_validation(eth_vs_btc)

    if validation:
        post_twitter_with_image(validation,"market_chart.png",thread=True)

    if structure_changed and can_tweet():
        post_twitter_with_image(tweet,"market_chart.png")

# ================= ROUTES =================

@app.route("/")
def home():
    return "DESK GRADE v10 ACTIVE",200

@app.route("/run-scan")
def run():
    scan()
    return "SCAN DONE",200

# ================= START =================

if __name__=="__main__":

    port=int(os.environ.get("PORT",8080))

    app.run(
        host="0.0.0.0",
        port=port
    )