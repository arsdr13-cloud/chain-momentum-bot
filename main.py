import os
import logging
import requests
import matplotlib.pyplot as plt
from flask import Flask
import tweepy
from datetime import datetime, timedelta
import json

# ================= CONFIG =================

CMC_API_KEY = os.getenv("CMC_API_KEY")

TW_BEARER_TOKEN = os.getenv("TW_BEARER_TOKEN")
TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")

COINS = ["BTC","ETH","SOL"]

DATA_FILE = "price_memory.json"
STRUCTURE_FILE = "structure_state.txt"
VALIDATION_FILE = "validation_state.json"
CASE_FILE = "cases_history.json"

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

# ================= STORAGE =================

def save_json(file,data):
    with open(file,"w") as f:
        json.dump(data,f)

def load_json(file):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return {}

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

def get_price_6h_ago():

    memory=load_json(DATA_FILE)

    if not memory:
        return None

    now=datetime.utcnow()

    target=now-timedelta(hours=6)

    closest=None
    diff=999999999

    for t in memory:

        ts=float(t)

        d=abs(ts-target.timestamp())

        if d<diff:
            diff=d
            closest=memory[t]

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

# ================= INTERPRETATION =================

def check_interpretation(rotation):

    last=""

    if os.path.exists(STRUCTURE_FILE):

        with open(STRUCTURE_FILE) as f:
            last=f.read()

    if rotation!=last:

        with open(STRUCTURE_FILE,"w") as f:
            f.write(rotation)

        return f"""Interpretation Update

Structure shift detected.

New rotation:
{rotation}

Watching continuation.
"""

    return None

# ================= VALIDATION =================

def save_validation(data):

    state={
        "time":datetime.utcnow().timestamp(),
        "eth_vs_btc":data
    }

    save_json(VALIDATION_FILE,state)

def evaluate_validation(current):

    state=load_json(VALIDATION_FILE)

    if not state:
        return None

    last_time=state["time"]

    hours_passed=(datetime.utcnow().timestamp()-last_time)/3600

    if hours_passed < 24:
        return None

    delta=current-state["eth_vs_btc"]

    result="Correct" if delta>0 else "Wrong"

    return f"""Validation (24h)

ETH/BTC move {delta:+.2f}%

Call result: {result}
"""

# ================= WEEKLY THREAD =================

def save_case(rotation,eth_vs_btc):

    cases=load_json(CASE_FILE)

    now=str(datetime.utcnow().timestamp())

    cases[now]={
        "rotation":rotation,
        "eth_vs_btc":eth_vs_btc
    }

    save_json(CASE_FILE,cases)

def weekly_thread():

    cases=load_json(CASE_FILE)

    if len(cases)<3:
        return None

    text="Weekly Structure Review\n\n"

    count=0

    for k in list(cases)[-3:]:

        c=cases[k]

        text+=f"""Case {count+1}
Rotation: {c['rotation']}
ETH/BTC {c['eth_vs_btc']:+.2f}%

"""

        count+=1

    text+="Repeated structure > noise."

    return text[:280]

# ================= CHART =================

def generate_chart(btc,eth,sol):

    labels=["BTC","ETH","SOL"]
    values=[btc,eth,sol]

    plt.figure(figsize=(8,5))
    plt.bar(labels,values)
    plt.axhline(0)
    plt.title("6H Liquidity Structure")

    path="market_chart.png"

    plt.savefig(path,dpi=200)
    plt.close()

    return path

# ================= BUILD TWEET =================

def build_tweet(btc,eth,sol,btc_dom):

    eth_vs_btc = relative_strength(btc,eth)
    sol_vs_btc = relative_strength(btc,sol)

    rotation = detect_rotation(btc,eth,sol)

    time = datetime.utcnow().strftime("%H:%M UTC")

    text=f"""6H Liquidity & Positioning Map | {time}

BTC {btc:+.2f}%
ETH {eth:+.2f}%
SOL {sol:+.2f}%

BTC.D {btc_dom:.2f}%

Rotation: {rotation}

ETH/BTC {eth_vs_btc:+.2f}%
SOL/BTC {sol_vs_btc:+.2f}%
"""

    return text[:280],rotation,eth_vs_btc

# ================= POST =================

def post_tweet(message,image=None):

    if not should_tweet(message):
        return

    if image:

        media=api_v1.media_upload(image)

        tweet=client.create_tweet(
            text=message,
            media_ids=[media.media_id]
        )

    else:

        tweet=client.create_tweet(text=message)

    with open(LAST_TWEET_FILE,"w") as f:
        f.write(str(tweet.data["id"]))

    record_tweet()

# ================= SCAN =================

def scan():

    data=fetch_market_data()
    global_data=fetch_global()

    if not data or not global_data:
        return

    update_price_memory(data)

    past=get_price_6h_ago()

    if not past:
        return

    btc_now=data["BTC"]["quote"]["USD"]["price"]
    eth_now=data["ETH"]["quote"]["USD"]["price"]
    sol_now=data["SOL"]["quote"]["USD"]["price"]

    btc_change=((btc_now-past["BTC"])/past["BTC"])*100
    eth_change=((eth_now-past["ETH"])/past["ETH"])*100
    sol_change=((sol_now-past["SOL"])/past["SOL"])*100

    btc_dom=global_data["btc_dominance"]

    tweet,rotation,eth_vs_btc=build_tweet(
        btc_change,
        eth_change,
        sol_change,
        btc_dom
    )

    chart=generate_chart(
        btc_change,
        eth_change,
        sol_change
    )

    interpretation=check_interpretation(rotation)

    if interpretation and can_tweet():
        post_tweet(interpretation)

    validation=evaluate_validation(eth_vs_btc)

    if validation and can_tweet():
        post_tweet(validation)

    if can_tweet():
        post_tweet(tweet,chart)

    save_validation(eth_vs_btc)

    save_case(rotation,eth_vs_btc)

    thread=weekly_thread()

    if thread and can_tweet():
        post_tweet(thread)

# ================= ROUTES =================

@app.route("/")
def home():
    return "DESK GRADE v11 ACTIVE",200

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