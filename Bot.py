import ccxt
import pandas as pd
import pandas_ta as ta
import time
import threading
import json
import os
from flask import Flask, render_template, jsonify, request
from twilio.rest import Client
import datetime

# --- CONFIGURATION ---
# Access password for the dashboard
ACCESS_PASSWORD = os.getenv("ACCESS_PASSWORD", "@Kalana11314")
app = Flask(__name__)

# Credentials (Fetched from Render Environment Variables)
TWILIO_SID = os.getenv("TWILIO_SID", "YOUR_TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "YOUR_TWILIO_AUTH_TOKEN")
TWILIO_SENDER = 'whatsapp:+14155238886'
WHATSAPP_NUMBER = 'whatsapp:+96566844388'

# Initialize Twilio Client
try:
    twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
except:
    twilio_client = None

# Binance Connection (Public data access)
exchange = ccxt.binance({
    'enableRateLimit': True,
})

# State Management
last_scan_results = []
auto_trade_enabled = False
is_demo_mode = True 
active_trades = {}
DATA_FILE = "supreme_bot_data.json"

# --- THE SUPREME TRADING ENGINE ---

def get_data(symbol, tf):
    try:
        bars = exchange.fetch_ohlcv(symbol, tf, limit=100)
        df = pd.DataFrame(bars, columns=['t','o','h','l','c','v'])
        return df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

def analyze_pro(symbol):
    global active_trades
    try:
        # 1. Market Structure Check (4H Trend)
        df_4h = get_data(symbol, '4h')
        if df_4h is None or len(df_4h) < 50: return
        
        ema200_4h = ta.ema(df_4h['c'], length=50).iloc[-1]
        if df_4h['c'].iloc[-1] < ema200_4h: return 

        # 2. Execution Data (15M)
        df_15m = get_data(symbol, '15m')
        if df_15m is None or len(df_15m) < 30: return
        
        rsi = ta.rsi(df_15m['c'], length=14).iloc[-1]
        bb = ta.bbands(df_15m['c'], length=20, std=2)
        macd = ta.macd(df_15m['c']).iloc[-1]
        adx = ta.adx(df_15m['h'], df_15m['l'], df_15m['c']).iloc[-1]['ADX_14']
        
        curr_price = df_15m['c'].iloc[-1]

        # 3. Entry Logic
        if symbol not in active_trades and len(active_trades) < 5:
            if adx > 25 and rsi < 30:
                print(f"💎 Signal Found for {symbol}")
                active_trades[symbol] = {
                    "entry": curr_price,
                    "time": datetime.datetime.now().strftime("%H:%M:%S"),
                    "status": "BUY_CONFIRMED"
                }
                if twilio_client:
                    try:
                        twilio_client.messages.create(
                            body=f"💎 SUPREME SIGNAL: {symbol}\nPrice: ${curr_price}",
                            from_=TWILIO_SENDER, to=WHATSAPP_NUMBER
                        )
                    except: pass
    except Exception as e:
        print(f"Analysis error: {e}")

def main_loop():
    while True:
        if auto_trade_enabled:
            try:
                # Top Coins Scan
                symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT']
                for s in symbols:
                    analyze_pro(s)
                    time.sleep(2)
            except: pass
        time.sleep(30)

# --- FLASK ROUTES ---

@app.route('/')
def index():
    return "<h1>Supreme Trading Bot is Running Live</h1><p>Status: Active</p>"

@app.route('/status')
def status():
    return jsonify({
        "auto_trade": auto_trade_enabled,
        "active_trades": active_trades,
        "server_time": datetime.datetime.now().isoformat()
    })

# Start Bot Thread
threading.Thread(target=main_loop, daemon=True).start()

if __name__ == "__main__":
    # Ensure Port is compatible with Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
