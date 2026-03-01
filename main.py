import os
import logging
import requests
import matplotlib.pyplot as plt
from flask import Flask
import tweepy
from datetime import datetime
import numpy as np
from matplotlib.patches import FancyBboxPatch

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CMC_API_KEY = os.getenv("CMC_API_KEY")

TW_BEARER_TOKEN = os.getenv("TW_BEARER_TOKEN")
TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")

COINS = ["BTC", "ETH", "SOL"]

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

# ================= TELEGRAM =================

def send_telegram_photo(photo_path, caption):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        with open(photo_path, "rb") as img:
            requests.post(
                url,
                data={"chat_id": CHAT_ID, "caption": caption[:1024]},
                files={"photo": img},
                timeout=20
            )
        logging.info("Telegram sent")
    except Exception as e:
        logging.error(f"Telegram error: {e}")

# ================= ULTRA CLEAN DIAL =================

def draw_fear_greed_dial(ax, value):
    ax.set_facecolor("#0b0f1a")
    ax.axis("off")

    theta = np.linspace(np.pi, 2*np.pi, 400)

    # Base arc
    ax.plot(np.cos(theta), np.sin(theta),
            lw=12, color="#1e293b",
            solid_capstyle="round")

    # Active arc
    active_theta = np.linspace(
        np.pi,
        np.pi + (value/100)*np.pi,
        300
    )

    ax.plot(np.cos(active_theta),
            np.sin(active_theta),
            lw=12,
            color="#22c55e",
            solid_capstyle="round")

    # Pointer
    angle = np.pi + (value/100)*np.pi
    ax.plot([0, 0.85*np.cos(angle)],
            [0, 0.85*np.sin(angle)],
            lw=2,
            color="white")

    ax.add_artist(plt.Circle((0, 0), 0.06, color="white"))

    ax.text(0, -0.12,
            f"{int(value)}",
            ha="center",
            va="center",
            fontsize=26,
            color="white",
            fontweight="bold")

    ax.text(0, -0.28,
            "Fear & Greed Index",
            ha="center",
            va="center",
            fontsize=9,
            color="#94a3b8")

    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.1, 0.25)

# ================= MARKET DATA =================

def fetch_market_data():
    try:
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
        params = {"symbol": ",".join(COINS), "convert": "USD"}

        r = requests.get(url, headers=headers, params=params, timeout=20)
        if r.status_code != 200:
            return None

        return r.json()["data"]

    except:
        return None

# ================= SENTIMENT =================

def detect_market_sentiment(avg_change):
    if avg_change < -5:
        return "🔴 Extreme Fear"
    elif avg_change < -2:
        return "🟠 Risk-Off"
    elif avg_change < 0:
        return "🟡 Neutral-Bearish"
    elif avg_change < 3:
        return "🟢 Neutral-Bullish"
    else:
        return "🚀 Strong Risk-On"

# ================= CHART =================

def generate_chart(btc_change, eth_change, sol_change):

    coins = ["BTC", "ETH", "SOL"]
    changes = [btc_change, eth_change, sol_change]

    avg_change = sum(changes) / 3

    # convert to 0-100 clean scale
    gauge_value = max(min((avg_change + 10) * 5, 100), 0)

    fig = plt.figure(figsize=(10,6), facecolor="#0b0f1a")

    # ========= MAIN BAR AXIS =========
    ax = fig.add_axes([0.08, 0.12, 0.55, 0.7])
    ax.set_facecolor("#0b0f1a")

    for i, value in enumerate(changes):

        color = "#22c55e" if value >= 0 else "#ef4444"

        bar = FancyBboxPatch(
            (i-0.3, 0),
            0.6,
            value,
            boxstyle="round,pad=0.02",
            linewidth=0,
            facecolor=color
        )
        ax.add_patch(bar)

        arrow = "↑" if value >= 0 else "↓"

        ax.text(
            i,
            value + (0.5 if value >= 0 else -0.5),
            f"{arrow} {value:.2f}%",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=11,
            fontweight="bold",
            color="white"
        )

    ax.set_xticks(range(len(coins)))
    ax.set_xticklabels(coins, color="white", fontsize=11)
    ax.axhline(0, color="white", alpha=0.2)
    ax.set_yticks([])
    ax.set_xlim(-1,2)
    ax.set_ylim(-10,15)

    # ========= TITLE =========
    fig.text(
        0.5, 0.92,
        "CHAIN MOMENTUM | MARKET INTELLIGENCE",
        ha="center",
        fontsize=14,
        color="white",
        fontweight="bold"
    )

    # ========= ULTRA CLEAN DIAL =========
    ax_dial = fig.add_axes([0.68, 0.55, 0.28, 0.35])
    draw_fear_greed_dial(ax_dial, gauge_value)

    filename = "market_chart.png"
    plt.savefig(filename, facecolor="#0b0f1a")
    plt.close()

    return filename

# ================= SCAN =================

def scan():

    data = fetch_market_data()
    if not data:
        return

    btc_change = data["BTC"]["quote"]["USD"]["percent_change_24h"]
    eth_change = data["ETH"]["quote"]["USD"]["percent_change_24h"]
    sol_change = data["SOL"]["quote"]["USD"]["percent_change_24h"]

    image_path = generate_chart(btc_change, eth_change, sol_change)

    send_telegram_photo(image_path, "🚀 Chain Momentum Update")
    logging.info("SCAN FINISHED")

# ================= ROUTES =================

@app.route("/")
def home():
    return "🚀 CHAIN MOMENTUM BOT ACTIVE", 200

@app.route("/run-scan")
def run_scan_route():
    scan()
    return "✅ SCAN EXECUTED", 200

# ================= START =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)