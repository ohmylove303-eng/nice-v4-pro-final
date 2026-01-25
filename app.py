# ============================================================
# NICE PRO v6.5 Backend - [THE GRAND PRINCIPLE ENGINE]
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

class BithumbScreener:
    @staticmethod
    def get_market_data(ticker):
        try:
            sym = ticker.replace("KRW-", "")
            # 1. Orderbook (Spread/Liquidity)
            url_ob = f"{config.BITHUMB_API_URL}/orderbook/{sym}_KRW"
            res_ob = requests.get(url_ob, timeout=1).json()
            
            # 2. Candles (Technical)
            url_can = f"{config.BITHUMB_API_URL}/candlestick/{sym}_KRW/24h"
            res_can = requests.get(url_can, timeout=1).json()
            
            if res_ob['status']!='0000' or res_can['status']!='0000': return None
            
            # Parse Candles
            df = pd.DataFrame(res_can['data'], columns=['time', 'open', 'close', 'high', 'low', 'volume'])
            df[['open','close','high','low','volume']] = df[['open','close','high','low','volume']].astype(float)
            
            return {
                "df": df.tail(100),
                "orderbook": res_ob['data'],
                "current_price": float(res_ob['data']['bids'][0]['price'])
            }
        except: return None

    @staticmethod
    def get_rankings(category):
        # ... (Existing ranking logic remains same, focus on Analysis logic)
        try:
            url = f"{config.BITHUMB_API_URL}/ticker/ALL_KRW"
            res = requests.get(url, timeout=2).json()
            if res['status'] != '0000': return []
            
            candidates = []
            for sym, coin in res['data'].items():
                if sym=='date': continue
                candidates.append({
                    "symbol": sym, 
                    "price": float(coin['closing_price']),
                    "change": float(coin['fluctate_rate_24H']),
                    "volume": float(coin['acc_trade_value_24H'])
                })
                
            if category == "surge":
                # EVENT DRIVEN: Volume Explosion (>5B KRW) + Price Action (>5%)
                res = [c for c in candidates if c['change']>=5 and c['volume']>5000000000]
                res.sort(key=lambda x: x['change'], reverse=True)
                return res[:15]
            
            elif category == "scalping":
                # LIQUIDITY FIRST: Volume > 20B KRW
                res = [c for c in candidates if c['volume']>20000000000]
                res.sort(key=lambda x: x['volume'], reverse=True)
                return res[:15]
            
            elif category == "majors":
                majors = ["BTC","ETH","XRP","SOL","DOGE","ADA","DOT"]
                res = [c for c in candidates if c['symbol'] in majors]
                res.sort(key=lambda x: x['volume'], reverse=True)
                return res
            
        except: pass
        return []

class ScoreEngine:
    @staticmethod
    def calculate(df, orderbook):
        # 1. Fundamental Power (Volume)
        # Compare last vol to avg vol (20)
        curr_vol = df['volume'].iloc[-1]
        avg_vol = df['volume'].rolling(20).mean().iloc[-1]
        vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0
        
        fund_score = min(30, vol_ratio * 10) # Max 30 pts for Volume Explosion
        
        # 2. Technical Score
        # Trend
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        ma60 = df['close'].rolling(60).mean().iloc[-1]
        trend_score = 30 if ma20 > ma60 else 0
        
        # PSI (Price Stability Index - Spread)
        bid = float(orderbook['bids'][0]['price'])
        ask = float(orderbook['asks'][0]['price'])
        spread_bps = (ask-bid)/bid * 10000
        liq_score = 20 if spread_bps < 30 else (10 if spread_bps < 60 else 0)
        
        # RSI Quality
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1]
        
        rsi_score = 20 if 40 <= rsi_val <= 70 else 10 # Ideal zone
        
        total = fund_score + trend_score + liq_score + rsi_score
        return min(99, int(total)), vol_ratio

@app.route('/api/analyze/<ticker>')
def analyze(ticker):
    try:
        t_code = ticker.replace("KRW-","")
        data = BithumbScreener.get_market_data(t_code)
        
        if not data: return jsonify({"error":"Data Unavailable"})
        
        df = data['df']
        ob = data['orderbook']
        
        # 1. Base Score (The "Basis")
        base_score, vol_power = ScoreEngine.calculate(df, ob)
        
        # 2. AI Review (The "Reasoning")
        ai_res = {
            "score": base_score, 
            "type": "Wait", 
            "kelly": 0, 
            "reasoning": "AI Unavailable"
        }
        
        if model:
            # Prompt reflecting the "Grand Principle"
            prompt = f"""
            ACT AS 'NICE PRO' CHIEF ANALYST.
            
            [Target: {t_code}]
            - Base Score (Tech+Liq): {base_score}/100
            - Vol Power (Event Proxy): {vol_power:.1f}x (Normal=1.0)
            - Trend: {'UP' if base_score > 50 else 'DOWN'}
            
            [The Grand Principle]
            1. Fundametal: Is there a Volume Event? (Vol Power > 2.0 implies News)
            2. Technical: Is Trend supportive?
            3. Risk: Is Spread tight?
            
            [Task]
            Finalize the 'NICE Score' and 'Signal Type'.
            
            [Rules]
            - TYPE A: Score > 80 AND Vol Power > 1.5 (High Confidence)
            - TYPE B: Score > 60 (Standard)
            - TYPE C: Weak/Watch
            
            Output JSON: {{ "final_score": int, "signal_type": "TYPE A/B/C", "kelly_pct": float, "reasoning": "Korean text summary" }}
            """
            try:
                res = model.generate_content(prompt)
                import json
                text = res.text
                if "{" in text:
                    ai_json = json.loads(text[text.find("{"):text.rfind("}")+1])
                    ai_res['score'] = ai_json.get('final_score', base_score)
                    ai_res['type'] = ai_json.get('signal_type', 'TYPE C')
                    ai_res['kelly'] = ai_json.get('kelly_pct', 0)
                    ai_res['reasoning'] = ai_json.get('reasoning', 'Analysis complete.')
            except: pass

        # Technical Structure for UI
        curr = df['close'].iloc[-1]
        high200 = df['high'].max()
        low200 = df['low'].min()
        fib = {
            "0.382": high200 - (high200-low200)*0.382,
            "0.618": high200 - (high200-low200)*0.618
        }
        
        return jsonify({
            "ticker": t_code,
            "score": ai_res['score'],
            "type": ai_res['type'],
            "kelly": ai_res['kelly'],
            "tech": {
                "price": curr,
                "trend": "UPTREND" if ai_res['score'] > 60 else "NEUTRAL/DOWN",
                "rsi": 50.0, # Placeholder or calc
                "fib": fib
            },
            "ai": ai_res
        })
        
    except Exception as e:
        logger.error(str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/api/screener/<category>')
def get_screener(category):
    return jsonify({"category": category, "list": BithumbScreener.get_rankings(category)})

@app.route('/')
@app.route('/app')
def index():
    from flask import render_template
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)