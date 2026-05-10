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

app = Flask(__name__)

@app.route('/')
def index():
    return "<h1>Supreme Trading Bot is Running Live</h1>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
