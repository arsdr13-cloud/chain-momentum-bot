import os
import logging
import requests
import matplotlib.pyplot as plt
from flask import Flask
import tweepy
from datetime import datetime

================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CMC_API_KEY = os.getenv("CMC_API_KEY")

TW_BEARER_TOKEN = os.getenv("TW_BEARER_TOKEN")
TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")

COINS = ["BTC", "ETH", "SOL"]

ROTATION_STRENGTH_THRESHOLD = 0.40
ROTATION_THREAD_THRESHOLD = 1.00

LAST_TWEET_FILE = "last_tweet_id.txt"
ROTATION_STATE_FILE = "rotation_state.txt"

STRUCTURE_FILE = "structure_state.txt"
LAST_TWEET_TIME = "last_tweet_time.txt"
VALIDATION_FILE = "validation_state.txt"

===== DESK GRADE v8 ADDITIONS =====

MIN_MOVE_FILTER = 0.30
SOL_ROTATION_THRESHOLD = 0.80
ETH_ROTATION_THRESHOLD = 0.50

STRONG_ROTATION_LEVEL = 1.50
MOMENTUM_CONFIRM_LEVEL = 2.50

VOLATILITY_FILTER = 0.25
REGIME_ROTATION_LEVEL = 1.20
REGIME_TREND_LEVEL = 2.80

===== DESK GRADE v9 ADDITIONS =====

PRESSURE_IMBALANCE_LEVEL = 2.00
ALT_EXPANSION_LEVEL = 3.50
BTC_DEFENSIVE_LEVEL = -2.50

TWEET_COOLDOWN = 14400

logging.basicConfig(level=logging.INFO)
app = Flask(name)

================= TWITTER CLIENT =================

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

================= STORAGE =================

def get_last_tweet_id():
try:
if os.path.exists(LAST_TWEET_FILE):
with open(LAST_TWEET_FILE, "r") as f:
return f.read().strip()
except:
pass
return None

def save_last_tweet_id(tweet_id):
try:
with open(LAST_TWEET_FILE, "w") as f:
f.write(str(tweet_id))
except:
pass

================= VALIDATION MEMORY =================

def save_validation_state(eth_vs_btc, rotation):
try:
with open(VALIDATION_FILE, "w") as f:
f.write(f"{eth_vs_btc}|{rotation}")
except:
pass

def get_validation_state():
try:
if os.path.exists(VALIDATION_FILE):
with open(VALIDATION_FILE, "r") as f:
data = f.read().strip().split("|")
return float(data[0]), data[1]
except:
pass
return None, None

================= STRUCTURE MEMORY =================

def get_last_structure():
try:
if os.path.exists(STRUCTURE_FILE):
with open(STRUCTURE_FILE, "r") as f:
return f.read().strip()
except:
pass
return None

def save_structure(state):
try:
with open(STRUCTURE_FILE, "w") as f:
f.write(state)
except:
pass

================= TWEET COOLDOWN =================

def can_tweet():
try:
if os.path.exists(LAST_TWEET_TIME):
with open(LAST_TWEET_TIME, "r") as f:
last_time = float(f.read().strip())
now = datetime.utcnow().timestamp()

if now - last_time < TWEET_COOLDOWN:  
                return False  
except:  
    pass  

return True

def record_tweet():
try:
with open(LAST_TWEET_TIME, "w") as f:
f.write(str(datetime.utcnow().timestamp()))
except:
pass

================= TWITTER POST =================

def post_twitter_with_image(message, image_path, thread=False):

try:  

    media = api_v1.media_upload(image_path)  

    last_tweet_id = get_last_tweet_id()  

    if thread and last_tweet_id:  

        tweet = client.create_tweet(  
            text=message,  
            media_ids=[media.media_id],  
            in_reply_to_tweet_id=last_tweet_id  
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

================= MARKET DATA =================

def fetch_market_data():

try:  

    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"  

    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}  

    params = {  
        "symbol": ",".join(COINS),  
        "convert": "USD"  
    }  

    r = requests.get(url, headers=headers, params=params, timeout=20)  

    if r.status_code != 200:  
        return None  

    return r.json()["data"]  

except:  
    return None

def fetch_global_metrics():

try:  

    url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"  

    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}  

    r = requests.get(url, headers=headers, timeout=20)  

    if r.status_code != 200:  
        return None  

    return r.json()["data"]  

except:  
    return None

================= RELATIVE STRENGTH =================

def calculate_relative_strength(base, compare):
return round(compare - base, 2)

================= MARKET REGIME ENGINE =================

def detect_market_regime(btc_change, eth_change, sol_change):

biggest_move = max(abs(btc_change), abs(eth_change), abs(sol_change))  

if biggest_move > REGIME_TREND_LEVEL:  
    return "Trending Market"  

if biggest_move > REGIME_ROTATION_LEVEL:  
    return "Rotation Market"  

return "Range Market"

================= MOMENTUM ENGINE =================

def detect_momentum_strength(btc_change, eth_change, sol_change):

if btc_change > MOMENTUM_CONFIRM_LEVEL:  
    return "BTC Momentum"  

if eth_change > MOMENTUM_CONFIRM_LEVEL:  
    return "ETH Momentum"  

if sol_change > MOMENTUM_CONFIRM_LEVEL:  
    return "SOL Momentum"  

return None

================= MARKET PRESSURE ENGINE v9 =================

def detect_market_pressure(btc_change, eth_change, sol_change):

alt_pressure = (eth_change + sol_change) / 2 - btc_change  

if alt_pressure > ALT_EXPANSION_LEVEL:  
    return "Aggressive Alt Expansion"  

if alt_pressure > PRESSURE_IMBALANCE_LEVEL:  
    return "Alt Pressure Building"  

if btc_change < BTC_DEFENSIVE_LEVEL:  
    return "Defensive BTC Flow"  

return None

================= ROTATION ENGINE =================

def detect_rotation(btc_change, eth_change, sol_change, btc_dom):

eth_vs_btc = calculate_relative_strength(btc_change, eth_change)  
sol_vs_btc = calculate_relative_strength(btc_change, sol_change)  

if btc_dom > 58 and btc_change > eth_change:  
    return "BTC Leadership"  

if eth_vs_btc > ETH_ROTATION_THRESHOLD:  

    if sol_vs_btc > SOL_ROTATION_THRESHOLD:  
        return "Broad Alt Rotation"  

    return "ETH Relative Strength"  

if sol_vs_btc > SOL_ROTATION_THRESHOLD:  
    return "High Beta Expansion"  

return "Balanced Structure"

================= VALIDATION ENGINE =================

def evaluate_validation(current_eth_vs_btc):

last_value, last_rotation = get_validation_state()  

if last_value is None:  
    return None  

delta = current_eth_vs_btc - last_value  

if abs(delta) < MIN_MOVE_FILTER:  
    return None  

if last_rotation == "ETH Relative Strength":  

    result = "Correct" if delta > 0 else "Wrong"  

elif last_rotation == "BTC Leadership":  

    result = "Correct" if delta < 0 else "Wrong"  

else:  
    return None  

return f"""Validation

ETH/BTC move {delta:+.2f}%

Call result: {result}"""

================= BUILD TWITTER TEXT =================

def build_twitter_text(
btc_price, btc_change,
eth_price, eth_change,
sol_price, sol_change,
btc_dom
):

regime = detect_market_regime(  
    btc_change,  
    eth_change,  
    sol_change  
)  

rotation_signal = detect_rotation(  
    btc_change,  
    eth_change,  
    sol_change,  
    btc_dom  
)  

momentum = detect_momentum_strength(  
    btc_change,  
    eth_change,  
    sol_change  
)  

pressure = detect_market_pressure(  
    btc_change,  
    eth_change,  
    sol_change  
)  

eth_vs_btc = calculate_relative_strength(  
    btc_change,  
    eth_change  
)  

sol_vs_btc = calculate_relative_strength(  
    btc_change,  
    sol_change  
)  

tweet_text = f"""6H Structure Map

BTC {btc_change:+.2f}%
ETH {eth_change:+.2f}%
SOL {sol_change:+.2f}%

BTC.D {btc_dom:.2f}%

Market Regime: {regime}

Rotation: {rotation_signal}

Relative Strength

ETH/BTC {eth_vs_btc:+.2f}%
SOL/BTC {sol_vs_btc:+.2f}%"""

if momentum:  
    tweet_text += f"\nMomentum: {momentum}"  

if pressure:  
    tweet_text += f"\nFlow: {pressure}"  

last_structure = get_last_structure()  

structure_changed = rotation_signal != last_structure  

save_structure(rotation_signal)  

save_validation_state(  
    eth_vs_btc,  
    rotation_signal  
)  

return tweet_text[:280], structure_changed, eth_vs_btc

================= SCAN =================

def scan():

data = fetch_market_data()  
global_data = fetch_global_metrics()  

if not data or not global_data:  
    return  

btc_price = data["BTC"]["quote"]["USD"]["price"]  
btc_change = data["BTC"]["quote"]["USD"]["percent_change_24h"]  

eth_price = data["ETH"]["quote"]["USD"]["price"]  
eth_change = data["ETH"]["quote"]["USD"]["percent_change_24h"]  

sol_price = data["SOL"]["quote"]["USD"]["price"]  
sol_change = data["SOL"]["quote"]["USD"]["percent_change_24h"]  

btc_dom = global_data["btc_dominance"]  

twitter_message, structure_changed, eth_vs_btc = build_twitter_text(  
    btc_price, btc_change,  
    eth_price, eth_change,  
    sol_price, sol_change,  
    btc_dom  
)  

validation = evaluate_validation(eth_vs_btc)  

image_path = "market_chart.png"  

if validation:  

    post_twitter_with_image(  
        validation,  
        image_path,  
        thread=True  
    )  

if structure_changed and can_tweet():  

    post_twitter_with_image(  
        twitter_message,  
        image_path  
    )

================= ROUTES =================

@app.route("/")
def home():
return "CHAIN MOMENTUM BOT v9 ACTIVE", 200

@app.route("/run-scan")
def run_scan_route():
scan()
return "SCAN EXECUTED", 200

================= START =================

if name == "main":

port = int(os.environ.get("PORT", 8080))  

app.run(  
    host="0.0.0.0",  
    port=port  
)