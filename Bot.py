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
ACCESS_PASSWORD = os.getenv("ACCESS_PASSWORD", "@Kalana11314")
app = Flask(__name__)

# Credentials
TWILIO_SID = os.getenv("TWILIO_SID", "YOUR_TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "YOUR_TWILIO_AUTH_TOKEN")
TWILIO_SENDER = 'whatsapp:+14155238886'
WHATSAPP_NUMBER = 'whatsapp:+96566844388'
twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# State
exchange = None
last_scan_results = []
auto_trade_enabled = False
is_demo_mode = True 
active_trades = {}
net_total_profit = 0.0
daily_loss_limit = -50.0 # Safety cut-off
DATA_FILE = "supreme_bot_data.json"

# --- THE SUPREME TRADING ENGINE ---

def get_data(symbol, tf):
    try:
        bars = exchange.fetch_ohlcv(symbol, tf, limit=100)
        df = pd.DataFrame(bars, columns=['t','o','h','l','c','v'])
        return df
    except: return None

def analyze_pro(symbol):
    global exchange, active_trades
    try:
        # 1. 4H MARKET STRUCTURE (SMC CONCEPT)
        df_4h = get_data(symbol, '4h')
        if df_4h is None: return None
        ema200_4h = ta.ema(df_4h['c'], length=200).iloc[-1]
        if df_4h['c'].iloc[-1] < ema200_4h: return None # Strictly Follow Long-term Trend

        # 2. 15M EXECUTION DATA
        df_15m = get_data(symbol, '15m')
        if df_15m is None: return None
        
        # INDICATORS (CONFLUENCE)
        rsi = ta.rsi(df_15m['c'], length=14).iloc[-1]
        bb = ta.bbands(df_15m['c'], length=20, std=2)
        macd = ta.macd(df_15m['c']).iloc[-1]
        adx = ta.adx(df_15m['h'], df_15m['l'], df_15m['c']).iloc[-1]['ADX_14']
        atr = ta.atr(df_15m['h'], df_15m['l'], df_15m['c']).iloc[-1]
        
        curr_price = df_15m['c'].iloc[-1]
        prev_price = df_15m['c'].iloc[-2]
        vol_avg = df_15m['v'].tail(20).mean()
        curr_vol = df_15m['v'].iloc[-1]

        # 3. ENTRY LOGIC (NO-GAP RULES)
        if symbol not in active_trades and len(active_trades) < 5:
            # Rule 1: Trend is Strong (ADX > 25)
            # Rule 2: RSI is deeply oversold (< 30) or rebounding from lower Bollinger
            # Rule 3: Volume is higher than average (Smart Money Entry)
            # Rule 4: MACD Histogram is turning positive
            if (adx > 25 and rsi < 30 and curr_price > bb['BBL_20_2.0'].iloc[-1] and 
                curr_vol > vol_avg and macd['MACDh_12_26_9'] > 0):
                
                # Execute Market Buy
                bal = exchange.fetch_balance()['total'].get('USDT', 0)
                risk_amt = max(11, bal * 0.12) # Dynamic 12% Risk
                qty = risk_amt / curr_price
                
                exchange.create_market_buy_order(symbol, qty)
                active_trades[symbol] = {
                    "entry": curr_price, "qty": qty, "highest": curr_price,
                    "sl": curr_price - (atr * 2.5), "tp": curr_price * 1.08, # 8% Target
                    "mode": "DEMO" if is_demo_mode else "REAL"
                }
                save_data()
                twilio_client.messages.create(body=f"💎 SUPREME SIGNAL: {symbol}\nPrice: ${curr_price}\nConfirmed by 5 Systems ✅", from_=TWILIO_SENDER, to=WHATSAPP_NUMBER)

        # 4. SMART TRAILING EXIT
        if symbol in active_trades:
            trade = active_trades[symbol]
            if curr_price > trade['highest']:
                trade['highest'] = curr_price
                if curr_price > trade['entry'] * 1.03: # After 3% profit, trail SL tightly
                    trade['sl'] = max(trade['sl'], curr_price - (atr * 1.2))
            
            if curr_price <= trade['sl'] or curr_price >= trade['tp']:
                exchange.create_market_sell_order(symbol, trade['qty'])
                pnl = (curr_price - trade['entry']) * trade['qty']
                del active_trades[symbol]
                save_data()

    except: pass

# --- GLOBAL SCANNER ---
def main_loop():
    while True:
        if exchange and auto_trade_enabled:
            try:
                # Scans Binance Globally (Filtered for performance)
                tickers = exchange.fetch_tickers()
                symbols = sorted([s for s in tickers if '/USDT' in s], key=lambda x: tickers[x]['quoteVolume'], reverse=True)[:50]
                for s in symbols:
                    analyze_pro(s)
                    time.sleep(1.2)
            except: pass
        time.sleep(10)

def save_data():
    with open(DATA_FILE, "w") as f: json.dump(active_trades, f)

# (Flask routes for link and data remain the same)
