# ============================================================
# NICE PRO v7.0 Backend - [UNIVERSAL ANALYSIS ENGINE]
# ============================================================

from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
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
    # Fallback or strict error handling? For now, None.
    model = None

app = Flask(__name__)
CORS(app)

# ============================================================
# 1. CORE ENGINES
# ============================================================

class BithumbScreener:
    @staticmethod
    def get_market_data(ticker):
        try:
            sym = ticker.replace("KRW-", "")
            # Orderbook
            url_ob = f"{config.BITHUMB_API_URL}/orderbook/{sym}_KRW"
            res_ob = requests.get(url_ob, timeout=1).json()
            
            # Candles
            url_can = f"{config.BITHUMB_API_URL}/candlestick/{sym}_KRW/24h"
            res_can = requests.get(url_can, timeout=1).json()
            
            if res_ob['status']!='0000' or res_can['status']!='0000': return None
            
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
                
            # UNIVERSAL CATEGORY LOGIC
            if category == "surge":
                # Volume > 5B + Chg > 5% (The "Event")
                res = [c for c in candidates if c['change']>=5 and c['volume']>5000000000]
                res.sort(key=lambda x: x['change'], reverse=True)
                return res[:20]
            
            elif category == "scalping":
                # High Liquidity > 30B
                res = [c for c in candidates if c['volume']>30000000000]
                res.sort(key=lambda x: x['volume'], reverse=True)
                return res[:20]
            
            elif category == "majors":
                # Fixed Major List
                majors = ["BTC","ETH","XRP","SOL","DOGE","ADA","DOT","LINK","AVAX","SHIB"]
                res = [c for c in candidates if c['symbol'] in majors]
                res.sort(key=lambda x: x['volume'], reverse=True)
                return res
            
        except: pass
        return []

class TechnicalAnalyst:
    @staticmethod
    def analyze_wave(df):
        # Elliot Wave Approximation (Simplified)
        # Using 20/60/120 MA alignment + RSI
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        ma60 = df['close'].rolling(60).mean().iloc[-1]
        ma120 = df['close'].rolling(120).mean().iloc[-1]
        rsi = TechnicalAnalyst.calc_rsi(df)
        
        if ma20 > ma60 > ma120:
            if rsi > 70: return "Wave 3 (Impulse)"
            if rsi > 50: return "Wave 5 (Extension)"
            return "Wave 1 (Start)"
        elif ma20 < ma60:
            return "Correction (ABC)"
        else:
            return "Consolidation"

    @staticmethod
    def calc_rsi(df):
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        return (100 - (100 / (1 + rs))).iloc[-1]

class ScoreEngine:
    @staticmethod
    def calculate(df, orderbook):
        # 1. Fundamental (Volume) - Strict
        curr_vol = df['volume'].iloc[-1]
        avg_vol = df['volume'].rolling(20).mean().iloc[-1]
        vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0
        
        # Only give points if Volume is truly Exploding (>2x)
        fund_score = 0
        if vol_ratio > 3.0: fund_score = 30
        elif vol_ratio > 2.0: fund_score = 20
        elif vol_ratio > 1.5: fund_score = 10
        
        # 2. Technical (Trend) - Strict
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        ma60 = df['close'].rolling(60).mean().iloc[-1]
        price = df['close'].iloc[-1]
        
        trend_score = 0
        if ma20 > ma60: 
            trend_score += 10
            if price > ma20: trend_score += 20 # Only true uptrend
            
        # 3. Liquidity (Spread)
        bid = float(orderbook['bids'][0]['price'])
        ask = float(orderbook['asks'][0]['price'])
        spread_bps = (ask-bid)/bid * 10000
        liq_score = 20 if spread_bps < 20 else 0
        
        # 4. RSI
        rsi = TechnicalAnalyst.calc_rsi(df)
        rsi_score = 20 if 45 <= rsi <= 65 else 0 # Ideal entry zone
        
        total = fund_score + trend_score + liq_score + rsi_score
        return min(99, int(total)), vol_ratio

# ============================================================
# 2. API ENDPOINTS
# ============================================================

@app.route('/api/analyze/<ticker>')
def analyze(ticker):
    try:
        t_code = ticker.replace("KRW-","")
        t_code = t_code.upper() # Safety
        
        data = BithumbScreener.get_market_data(t_code)
        if not data: return jsonify({"error":"Data Unavailable"})
        
        df = data['df']
        ob = data['orderbook']
        
        # 1. SCORE
        base_score, vol_power = ScoreEngine.calculate(df, ob)
        
        # 2. WAVE & TECH
        wave_status = TechnicalAnalyst.analyze_wave(df)
        rsi_val = TechnicalAnalyst.calc_rsi(df)
        
        curr = df['close'].iloc[-1]
        h = df['high'].max()
        l = df['low'].min()
        fib = {
            "0.382": h - (h-l)*0.382,
            "0.5": h - (h-l)*0.5,
            "0.618": h - (h-l)*0.618
        }
        
        # 3. AI (If available)
        ai_res = {
            "score": base_score,
            "type": "Wait (D)",
            "kelly": 0,
            "reasoning": "AI inactive."
        }
        
        if model:
            prompt = f"""
            [TARGET: {t_code}]
            - Score: {base_score} (VolPower: {vol_power:.1f}x)
            - Wave: {wave_status}
            - RSI: {rsi_val:.1f}
            
            [TASK]
            Assign Signal Type (A=Strong Buy, B=Buy, C=Watch, D=Wait).
            Calculate Kelly % (Safe bet size).
            Summarize reasoning in Korean (1 sentence).
            
            Output JSON: {{ "signal_type": "...", "kelly_pct": float, "reasoning": "..." }}
            """
            try:
                res = model.generate_content(prompt)
                import json
                txt = res.text
                if "{" in txt:
                    js = json.loads(txt[txt.find("{"):txt.rfind("}")+1])
                    ai_res["type"] = js.get("signal_type", "Wait")
                    ai_res["kelly"] = js.get("kelly_pct", 0)
                    ai_res["reasoning"] = js.get("reasoning", "Analysis done.")
            except: pass

        return jsonify({
            "ticker": t_code,
            "score": base_score, # REAL SCORE
            "type": ai_res["type"],
            "kelly": ai_res["kelly"],
            "tech": {
                "price": curr,
                "trend": wave_status, # Use Wave as Trend
                "rsi": rsi_val,
                "fib": fib
            },
            "ai": ai_res
        })

    except Exception as e:
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