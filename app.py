# ============================================================
# NICE PRO v5 Backend - [GRAND PRINCIPLE ARCHITECTURE]
# ============================================================

from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import pyupbit 
from datetime import datetime
import requests
import config
import google.generativeai as genai
import os
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gemini Setup
GEMINI_KEY = os.getenv('GOOGLE_API_KEY')
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None

app = Flask(__name__)
CORS(app)

# ============================================================
# 1. TECHNICAL ANALYST ENGINE (The "Calculator")
# ============================================================
class TechnicalAnalyst:
    @staticmethod
    def get_fibonacci_levels(high, low):
        diff = high - low
        return {
            "0.236": high - diff * 0.236,
            "0.382": high - diff * 0.382,
            "0.5": high - diff * 0.5,
            "0.618": high - diff * 0.618,
            "0.786": high - diff * 0.786
        }

    @staticmethod
    def analyze_trend(df):
        # Moving Averages
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        ma60 = df['close'].rolling(60).mean().iloc[-1]
        ma120 = df['close'].rolling(120).mean().iloc[-1]
        
        # Trend Determination
        if ma20 > ma60 > ma120: trend = "STRONG_UPTREND"
        elif ma20 > ma60: trend = "UPTREND"
        elif ma20 < ma60 < ma120: trend = "STRONG_DOWNTREND"
        else: trend = "NEUTRAL/CHOPPY"
        
        return trend

    @staticmethod
    def analyze(ticker, df):
        curr = df['close'].iloc[-1]
        high_200 = df['high'].max()
        low_200 = df['low'].min()
        
        # 1. Fibonacci
        fib = TechnicalAnalyst.get_fibonacci_levels(high_200, low_200)
        
        # 2. Trend
        trend = TechnicalAnalyst.analyze_trend(df)
        
        # 3. RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return {
            "price": curr,
            "trend": trend,
            "fib": fib,
            "rsi": rsi.iloc[-1],
            "high_200": high_200,
            "low_200": low_200
        }

# ============================================================
# 2. BITHUMB DYNAMIC SCREENER (The "Ranker")
# ============================================================
class BithumbScreener:
    @staticmethod
    def fetch_all_tickers():
        try:
            url = f"{config.BITHUMB_API_URL}/ticker/ALL_KRW"
            res = requests.get(url, timeout=2).json()
            if res['status'] != '0000': return []
            return res['data']
        except:
             return {}

    @staticmethod
    def get_rankings(category):
        data = BithumbScreener.fetch_all_tickers()
        candidates = []
        
        for sym, coin in data.items():
            if sym == 'date': continue
            try:
                price = float(coin['closing_price'])
                chg = float(coin['fluctate_rate_24H'])
                vol = float(coin['acc_trade_value_24H']) # 24h Transaction Amount in KRW
                
                candidates.append({
                    "symbol": sym,
                    "price": price,
                    "change": chg,
                    "volume": vol
                })
            except: continue

        # Filter Logic based on User Categories
        results = []
        
        if category == "surge": # 초급등 (Super Surge)
            # Logic: Change > 5%, Volume > 10 Billion KRW
            results = [c for c in candidates if c['change'] >= 5 and c['volume'] > 10000000000]
            results.sort(key=lambda x: x['change'], reverse=True) # Highest Change first
            
        elif category == "scalping": # 단타 (Scalping)
            # Logic: Top Volume (Liquidity is King for Scalping), Change -3% ~ +10%
            results = [c for c in candidates if c['volume'] > 30000000000]
            results.sort(key=lambda x: x['volume'], reverse=True) # Highest Volume first
            
        elif category == "majors": # 메이저 (Majors)
            # Static List for reliability
            majors = ["BTC", "ETH", "XRP", "SOL", "DOGE", "ADA", "DOT", "AVAX", "LINK", "TRX"]
            results = [c for c in candidates if c['symbol'] in majors]
            results.sort(key=lambda x: x['volume'], reverse=True)
            
        else: # Default: Top Gainers
             results = sorted(candidates, key=lambda x: x['change'], reverse=True)

        return results[:10] # Top 10 only

# ============================================================
# 3. API ENDPOINTS
# ============================================================

    @staticmethod
    def get_candles(ticker, interval="24h"):
        # ULTRATHINK: Bithumb Native Chart Data Support
        # Fallback to PyUpbit only if Bithumb fails, or use Bithumb primarily since we are scanning Bithumb.
        # Bithumb Public API: /public/candlestick/{currency}_{payment_currency}/{interval}
        try:
            # Ticker format "KRW-BTC" -> "BTC_KRW"
            sym = ticker.replace("KRW-", "")
            url = f"{config.BITHUMB_API_URL}/candlestick/{sym}_KRW/{interval}"
            res = requests.get(url, timeout=2).json()
            
            if res['status'] != '0000': raise Exception("Bithumb API Error")
            
            # Parse Bithumb Data [time, open, close, high, low, volume]
            data = res['data']
            df = pd.DataFrame(data, columns=['time', 'open', 'close', 'high', 'low', 'volume'])
            df['close'] = df['close'].astype(float)
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            return df.tail(200) # Last 200 candles
        except:
            # Fallback to Upbit if Bithumb fails (for Majors)
            try:
                return pyupbit.get_ohlcv(ticker, interval="day", count=200)
            except:
                return None

@app.route('/api/screener/<category>')
def get_screener(category):
    """
    Returns list of coins for the requested category
    """
    data = BithumbScreener.get_rankings(category)
    return jsonify({"category": category, "list": data})

@app.route('/api/analyze/<ticker>')
def analyze_coin(ticker):
    """
    DEEP ANALYSIS ENDPOINT
    1. Chart Data (Bithumb Native + Upbit Fallback)
    2. Technical Calculation (Fib/Trend)
    3. AI Synthesis (Strategy Generation)
    """
    try:
        if not ticker.startswith("KRW-"): ticker = f"KRW-{ticker}"
        
        # 1. Fetch Chart (ULTRATHINK: Robust Data Source)
        df = BithumbScreener.get_candles(ticker, interval="24h")
        
        if df is None or df.empty:
             return jsonify({"error": "Chart Data Unavailable for " + ticker}), 404
        
        # 2. Technical Math
        tech = TechnicalAnalyst.analyze(ticker, df)
        
        # 3. AI Analysis
        if model:
            prompt = f"""
            ACT AS A SENIOR CRYPTO TRADER (ULTRATHINK MODE).
            
            [Target Asset]
            - Symbol: {ticker}
            - Current Price: {tech['price']}
            - Trend: {tech['trend']}
            - RSI: {tech['rsi']:.1f}
            
            [Fibonacci Pivot Structure]
            - Resistance (0.236): {tech['fib']['0.236']:.0f}
            - Critical Pivot (0.382): {tech['fib']['0.382']:.0f}
            - Primary Support (0.5): {tech['fib']['0.5']:.0f}
            - Last Stand (0.618): {tech['fib']['0.618']:.0f}
            
            [Objective]
            Analyze the market structure. Is the trend supported by the levels?
            Generate a high-precision trade setup.
            
            [Output JSON Only]
            {{
                "action": "BUY" | "SELL" | "WAIT" | "SCALPING_ONLY",
                "entry_price": "(Specific Price)",
                "target_price": "(Specific Price)",
                "stop_loss": "(Specific Price)",
                "reasoning": "Compact, sharp analysis citing specific levels."
            }}
            """
            try:
                res = model.generate_content(prompt)
                import json
                txt = res.text
                if "{" in txt:
                    ai_res = json.loads(txt[txt.find("{"):txt.rfind("}")+1])
                else:
                    ai_res = {"action": "HOLD", "reasoning": "AI Parsing Error"}
            except Exception as e:
                ai_res = {"action": "ERROR", "reasoning": str(e)}
        else:
            ai_res = {"action": "NO_AI", "reasoning": "API Key Missing"}

        return jsonify({
            "ticker": ticker,
            "tech": tech,
            "ai": ai_res
        })
        
    except Exception as e:
        logger.error(f"Analysis Failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
@app.route('/app')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)