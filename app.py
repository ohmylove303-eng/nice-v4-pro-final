# ============================================================
# NICE PRO v5.5 Backend - [NICE MODEL PROTOCOL INTEGRATED]
# ============================================================

from flask import Flask, jsonify
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

GEMINI_KEY = os.getenv('GOOGLE_API_KEY')
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None

app = Flask(__name__)
CORS(app)

# ============================================================
# NICE PROTOCOL: GUARD CHAIN SYSTEM
# ============================================================
class GuardChain:
    """
    Implements the 7-Phase Guard Chain Rules (Simplified for this MVP)
    Phase 1: Data Verification (Null, Outlier)
    Phase 3: Liquidity Verification (Volume, Spread)
    """
    @staticmethod
    def verify(ticker, df, vol_24h):
        report = {"passed": True, "reason": "All checks passed", "level": "SAFE"}
        
        # 1. Null Check
        if df.isnull().values.any():
            return {"passed": False, "reason": "Data Corruption Deteced (Null Values)", "level": "CRITICAL"}
        
        # 2. Staleness Check
        last_time = df.index[-1] # Assuming standard pandas datetime index if available, or list
        # We skip exact timestamp check here as we fetched 'days' data usually, 
        # but for real-time we'd check if last candle is < 1s old.
        
        # 3. Liquidity Guard (Phase 3)
        # Rule: Volume > 100M KRW for safe entry
        if vol_24h < 100_000_000:
            return {"passed": False, "reason": "Insufficient Liquidity (<100M KRW)", "level": "WARNING"}
            
        # 4. Outlier Detection (Phase 1.3)
        # 3-sigma check on Price
        recent_closes = df['close'].tail(20)
        mean = recent_closes.mean()
        std = recent_closes.std()
        curr = recent_closes.iloc[-1]
        
        if abs(curr - mean) > (3 * std):
            report["level"] = "CAUTION"
            report["reason"] = "Price Anomaly Detected (3-Sigma Outlier)"
            # We don't fail, but warn
            
        return report

# ============================================================
# TECHNICAL ANALYST
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
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        ma60 = df['close'].rolling(60).mean().iloc[-1]
        ma120 = df['close'].rolling(120).mean().iloc[-1]
        
        if ma20 > ma60 > ma120: trend = "STRONG_UPTREND"
        elif ma20 > ma60: trend = "UPTREND"
        elif ma20 < ma60 < ma120: trend = "STRONG_DOWNTREND"
        else: trend = "NEUTRAL"
        return trend

    @staticmethod
    def analyze(ticker, df):
        curr = df['close'].iloc[-1]
        high_200 = df['high'].max()
        low_200 = df['low'].min()
        
        fib = TechnicalAnalyst.get_fibonacci_levels(high_200, low_200)
        trend = TechnicalAnalyst.analyze_trend(df)
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return {
            "price": curr,
            "trend": trend,
            "fib": fib,
            "rsi": rsi.iloc[-1]
        }

# ============================================================
# BITHUMB DATA ENGINE
# ============================================================
class BithumbScreener:
    @staticmethod
    def fetch_all_tickers():
        try:
            url = f"{config.BITHUMB_API_URL}/ticker/ALL_KRW"
            res = requests.get(url, timeout=2).json()
            if res['status'] != '0000': return {}
            return res['data']
        except: return {}

    @staticmethod
    def get_candles(ticker, interval="24h"):
        try:
            sym = ticker.replace("KRW-", "")
            url = f"{config.BITHUMB_API_URL}/candlestick/{sym}_KRW/{interval}"
            res = requests.get(url, timeout=2).json()
            if res['status'] != '0000': raise Exception("Err")
            
            data = res['data']
            df = pd.DataFrame(data, columns=['time', 'open', 'close', 'high', 'low', 'volume'])
            df[['open','close','high','low','volume']] = df[['open','close','high','low','volume']].astype(float)
            return df.tail(200)
        except:
            try: return pyupbit.get_ohlcv(ticker, interval="day", count=200)
            except: return None

    @staticmethod
    def get_rankings(category):
        data = BithumbScreener.fetch_all_tickers()
        candidates = []
        for sym, coin in data.items():
            if sym == 'date': continue
            try:
                candidates.append({
                    "symbol": sym,
                    "price": float(coin['closing_price']),
                    "change": float(coin['fluctate_rate_24H']),
                    "volume": float(coin['acc_trade_value_24H'])
                })
            except: continue

        results = []
        if category == "surge":
            results = [c for c in candidates if c['change'] >= 5 and c['volume'] > 5000000000]
            results.sort(key=lambda x: x['change'], reverse=True)
        elif category == "scalping":
            results = [c for c in candidates if c['volume'] > 20000000000]
            results.sort(key=lambda x: x['volume'], reverse=True)
        elif category == "majors":
            majors = ["BTC", "ETH", "XRP", "SOL", "DOGE", "ADA", "DOT", "LINK"]
            results = [c for c in candidates if c['symbol'] in majors]
            results.sort(key=lambda x: x['volume'], reverse=True)
            
        return results[:15]

# ============================================================
# API ENDPOINTS
# ============================================================

@app.route('/api/screener/<category>')
def get_screener(category):
    return jsonify({"category": category, "list": BithumbScreener.get_rankings(category)})

@app.route('/api/analyze/<ticker>')
def analyze_coin(ticker):
    try:
        if not ticker.startswith("KRW-"): ticker = f"KRW-{ticker}"
        
        # 1. Data Collection (Performance: ~100ms)
        df = BithumbScreener.get_candles(ticker, interval="24h")
        if df is None: return jsonify({"error": "No Data"}), 404
        
        # 2. Guard Chain Verification (NICE Protocol)
        # Need Volume for Guard Phase 3
        # Estimate daily volume from last candle
        vol_24h = df['volume'].iloc[-1] * df['close'].iloc[-1] 
        guard = GuardChain.verify(ticker, df, vol_24h)
        
        if not guard['passed']:
            return jsonify({
                "ticker": ticker,
                "error": "Guard Chain Failed",
                "guard_report": guard,
                "tech": None,
                "ai": {"action": "SKIP", "reasoning": guard['reason']}
            })

        # 3. Technical Calculation
        tech = TechnicalAnalyst.analyze(ticker, df)
        
        # 4. LLM Synthesis
        ai_res = {"action": "WAIT", "reasoning": "AI Model Not Ready"}
        if model:
            prompt = f"""
            [NICE PROTOCOL: ULTRATHINK MODE]
            Asset: {ticker} | Price: {tech['price']} | Trend: {tech['trend']} | RSI: {tech['rsi']:.0f}
            Structure: Pivot {tech['fib']['0.382']:.0f}, Support {tech['fib']['0.618']:.0f}
            
            Task: Assess 3-Factor Confluence (Trend + Level + Momentum).
            Return JSON: {{ "action": "BUY/SELL/WAIT", "entry_price": "...", "stop_loss": "...", "reasoning": "Analysis..." }}
            """
            try:
                res = model.generate_content(prompt)
                import json
                txt = res.text
                if "{" in txt: ai_res = json.loads(txt[txt.find("{"):txt.rfind("}")+1])
            except: pass
            
        return jsonify({
            "ticker": ticker,
            "guard_report": guard, # Frontend displays this
            "tech": tech,
            "ai": ai_res
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
@app.route('/app')
def index():
    from flask import render_template
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)