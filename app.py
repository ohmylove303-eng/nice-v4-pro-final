# ============================================================
# NICE MPC v44.3 Backend - [PROFESSIONAL LOGIC UPGRADE]
# ============================================================

from flask import Flask, jsonify, render_template
from flask_cors import CORS
import logging
import pyupbit 
from datetime import datetime
import pytz
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

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_market_metrics():
    """
    PROFESSIONAL MARKET ANALYSIS
    - Trend: MA Divergence (Bull/Bear Regime)
    - Momentum: RSI + Stochastic Proxy
    - Volume: Volume Oscillator
    """
    try:
        # Get extended data for calculation
        df = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=200)
        btc_price = pyupbit.get_current_price("KRW-BTC")
        
        if df is None or df.empty:
            raise Exception("No Data")

        # 1. Trend Analysis (MA Divergence)
        ma20 = df['close'].rolling(window=20).mean()
        ma60 = df['close'].rolling(window=60).mean()
        
        # Bull Market if Short MA > Long MA
        trend_score = 0
        if ma20.iloc[-1] > ma60.iloc[-1]:
            trend_score = 100
            # Bonus if price is above MA20 (Strong Trend)
            if df['close'].iloc[-1] > ma20.iloc[-1]:
                trend_score += 20 # Can exceed 100 temporarily, capped later
        else:
            trend_score = 20 # Bearish
            
        # 2. RSI Calculation
        df['rsi'] = calculate_rsi(df['close'])
        current_rsi = df['rsi'].iloc[-1]
        
        # 3. Volume Analysis (Volume Oscillator)
        # Short Vol MA (5) vs Long Vol MA (10)
        vol_ma5 = df['volume'].rolling(5).mean()
        vol_ma10 = df['volume'].rolling(10).mean()
        vol_osc = ((vol_ma5 - vol_ma10) / vol_ma10) * 100
        
        # Volume Score: Positive Osc means volume is increasing (good for moves)
        vol_score = 50 + float(vol_osc.iloc[-1]) # Base 50
        
        return {
            "btc_price": btc_price,
            "rsi": current_rsi,
            "trend_score": min(100, max(0, trend_score)),
            "volume_score": min(100, max(0, int(vol_score))),
            "vol_osc": vol_osc.iloc[-1]
        }
    except Exception as e:
        logger.error(f"Market Metrics Error: {e}")
        return {"btc_price": 0, "rsi": 50, "trend_score": 50, "volume_score": 50, "vol_osc": 0}

def get_coin_price(ticker):
    try:
        return pyupbit.get_current_price(ticker)
    except:
        return 0

def get_bithumb_data():
    """빗썸 주요 코인 시세 및 김프 계산"""
    try:
        url = f"{config.BITHUMB_API_URL}/ticker/ALL_KRW"
        res = requests.get(url, timeout=2).json()
        
        if res['status'] != '0000': return []
        
        data = res['data']
        result = []
        
        try:
            binance_btc = float(requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=1).json()['price'])
        except:
            binance_btc = 0
            
        for sym, coin in data.items():
            if sym == 'date': continue
            if 'closing_price' not in coin: continue
            
            price = float(coin['closing_price'])
            chg_rate = float(coin['fluctate_rate_24H'])
            vol = float(coin['acc_trade_value_24H'])
            
            if vol < 500000000: continue # 5억 미만 필터링
            
            kimp_txt = "-"
            if sym == 'BTC' and binance_btc > 0:
                kimp = ((price / (binance_btc * config.KRW_RATE)) - 1) * 100
                kimp_txt = f"{kimp:.1f}%"
                
            result.append({
                "symbol": sym,
                "price": price,
                "chg": chg_rate,
                "vol": vol,
                "kimp": kimp_txt
            })
            
        result.sort(key=lambda x: x['chg'], reverse=True)
        return result
    except Exception as e:
        logger.error(f"Bithumb API Error: {e}")
        return []

def get_global_metrics():
    try:
        url = f"{config.COINMARKETCAP_API_URL}/global-metrics/quotes/latest"
        headers = {'X-CMC_PRO_API_KEY': config.COINMARKETCAP_API_KEY}
        res = requests.get(url, headers=headers, timeout=3).json()
        
        data = res['data']
        # Dominance & Sentiment
        btc_d = data['btc_dominance']
        mcap_chg = data['quote']['USD']['total_market_cap_yesterday_percentage_change']
        
        return {
            "btc_dominance": f"{btc_d:.1f}%",
            "market_change": f"{mcap_chg:.2f}%",
            "status": "ACCUMULATE" if mcap_chg > -1 and mcap_chg < 1 else ("BULL RUN" if mcap_chg >= 1 else "CORRECTION")
        }
    except:
        return {"btc_dominance": "-", "market_change": "-", "status": "NEUTRAL"}

def calculate_technical_indicators(df):
    try:
        close = df['close']
        
        # 1. RSI
        rsi = calculate_rsi(close).iloc[-1]
        
        # 2. Bollinger Bands
        ma20 = close.rolling(window=20).mean()
        std20 = close.rolling(window=20).std()
        upper = ma20 + (std20 * 2)
        lower = ma20 - (std20 * 2)
        bandwidth = (upper - lower) / ma20
        
        # 3. MA Alignment
        ma60 = close.rolling(window=60).mean().iloc[-1]
        
        return {
            "rsi": rsi,
            "bb_upper": upper.iloc[-1],
            "bb_lower": lower.iloc[-1],
            "bb_width": bandwidth.iloc[-1],
            "ma20": ma20.iloc[-1],
            "ma60": ma60,
            "close": close.iloc[-1]
        }
    except:
        return None

def get_ai_insight(ticker, df, tech):
    try:
        if not model: return {"summary": "AI Disconnected", "score": 50}
        
        curr = df['close'].iloc[-1]
        prompt = f"""
        Analyze {ticker} (Crypto). Price: {curr}.
        Indicators: RSI {tech['rsi']:.1f}, BB Width {tech['bb_width']:.3f}.
        Trend: {'Bullish' if tech['ma20'] > tech['ma60'] else 'Bearish'}.
        
        Provide:
        1. "score": 0-100 (Investment attractiveness)
        2. "summary": One concise strategic sentence.
        Output purely JSON.
        """
        
        res = model.generate_content(prompt)
        txt = res.text
        import json
        if "{" in txt:
            json_str = txt[txt.find("{"):txt.rfind("}")+1]
            return json.loads(json_str)
        return {"summary": "Analysis Pending...", "score": 60}
    except:
        return {"summary": "AI Error", "score": 50}

def calculate_precision_layers(tech, vol_24h):
    """
    PROFESSIONAL SCORING LAYERS (5-Factors)
    """
    if not tech: return None
    
    # L1: Technical Momentum (RSI + Position)
    # RSI 40-60 in uptrend is best. >70 is risky. <30 is oversold.
    l1 = 50
    rsi = tech['rsi']
    if 40 <= rsi <= 65: l1 = 80 # Sweet spot
    elif rsi > 70: l1 = 40 # Overbought caution
    elif rsi < 30: l1 = 70 # Oversold bounce play
    else: l1 = 50
    
    # L2: Liquidity (RVOL Proxy)
    # Simple proxy: if 24h vol is super high > 100B KRW -> High score
    l2 = 90 if vol_24h > 100_000_000_000 else (60 if vol_24h > 30_000_000_000 else 30)
    
    # L3: Trend (MA Alignment)
    l3 = 90 if tech['ma20'] > tech['ma60'] else 30
    
    # L5: Volatility (Squeeze)
    # BB Width < 0.1 means squeeze (Explosive potential)
    l5 = 85 if tech['bb_width'] < 0.1 else 50
    if tech['bb_width'] > 0.3: l5 = 40 # Too volatile/expanded
    
    # L4: Macro (Inherit Trend for now)
    l4 = l3 
    
    total = int((l1 * 0.3) + (l2 * 0.2) + (l3 * 0.2) + (l5 * 0.3))
    
    return {
        "L1_Tech": int(l1), "L2_Liquidity": int(l2), "L3_Trend": int(l3),
        "L4_Macro": int(l4), "L5_Vol": int(l5),
        "Total_Score": total
    }

@app.route('/api/analyze/<ticker>')
def analyze_coin(ticker):
    # Same logic but uses new functions
    try:
        if not ticker.startswith("KRW-"): ticker = f"KRW-{ticker}"
        df = pyupbit.get_ohlcv(ticker, interval="day", count=200)
        
        curr_info = pyupbit.get_current_price(ticker, verbose=True)
        vol_24h = curr_info.get('acc_trade_price_24h', 0) if curr_info else 0
        
        tech = calculate_technical_indicators(df)
        ai = get_ai_insight(ticker, df, tech)
        precision = calculate_precision_layers(tech, vol_24h)
        
        return jsonify({
            "ticker": ticker,
            "current_price": float(df['close'].iloc[-1]),
            "ai_insight": ai,
            "precision_report": precision
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/mpc-data', methods=['GET'])
def get_mpc_data():
    # 1. Professional Market Metrics
    metrics = get_market_metrics()
    
    # 2. Layer Scoring (L0-L5)
    # L0: Macro Trend (Bull/Bear)
    l0_score = metrics['trend_score']
    l0_desc = "Bullish Trend" if l0_score > 60 else "Bearish/Neutral"
    
    # L1: Volume Pressure
    l1_score = metrics['volume_score']
    l1_desc = f"Oscillator {metrics['vol_osc']:.1f}%"
    
    # L2: Liquidity (Fixed High for Majors)
    l2_score = 80 # Majors always liquid
    
    # L3: Momentum (RSI)
    l3_score = int(metrics['rsi'])
    l3_desc = "Neutral"
    if l3_score > 70: l3_desc = "Overbought"
    elif l3_score < 30: l3_desc = "Oversold"
    
    # Calculate WRS (Weighted Radar Score)
    # Weights: Trend(30%), Vol(20%), Mom(30%), Liq(20%)
    wrs_avg = (l0_score * 0.3) + (l1_score * 0.2) + (l3_score * 0.3) + (l2_score * 0.2)
    wrs_avg = round(wrs_avg, 1)
    
    # Tier Calculation
    tier = "TIER 3 (WAIT)"
    if wrs_avg >= 75: tier = "TIER 1 (STRONG BUY)"
    elif wrs_avg >= 55: tier = "TIER 2 (BUY)"
    
    # 3. Get Prices
    btc_p = metrics['btc_price']
    xrp_p = get_coin_price("KRW-XRP")
    eth_p = get_coin_price("KRW-ETH")
    sol_p = get_coin_price("KRW-SOL")
    doge_p = get_coin_price("KRW-DOGE")
    
    bithumb_data = get_bithumb_data()

    response_data = {
        "current_snapshot": {
            "wrs": wrs_avg,
            "tier": tier,
            "time": datetime.now(pytz.timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M:%S")
        },
        "layer_scores": [
            {"id": "L0", "name": "L0 MACRO TREND", "score": l0_score, "desc": l0_desc},
            {"id": "L1", "name": "L1 VOLUME OSC", "score": l1_score, "desc": l1_desc},
            {"id": "L2", "name": "L2 LIQUIDITY", "score": l2_score, "desc": "Major Assets Focus"},
            {"id": "L3", "name": "L3 MOMENTUM", "score": l3_score, "desc": f"RSI {l3_score}"},
            {"id": "L5", "name": "L5 VOLATILITY", "score": 75, "desc": "Expansion Phase"}
        ],
        "recommendations": {
             "scalping": {
                "title": "SCALPING", "mode": "AGGRESSIVE",
                "coins": [
                    {"symbol": "BTC", "label": "Bitcoin", "entry": f"{btc_p:,.0f}", "tp": "Open", "sl": "-0.5%"},
                    {"symbol": "SOL", "label": "Solana", "entry": f"{sol_p:,.0f}", "tp": "+3%", "sl": "-1.5%"}
                ]
            },
            "short": {
                "title": "SWING", "mode": "TREND",
                "coins": [
                    {"symbol": "ETH", "label": "Ethereum", "entry": f"{eth_p:,.0f}", "tp": "+8%", "sl": "-3%"},
                    {"symbol": "XRP", "label": "Ripple", "entry": f"{xrp_p:,.0f}", "tp": "+12%", "sl": "-5%"}
                ]
            },
            "medium": { 
                "title": "LONG", "mode": "HODL", 
                "coins": [
                    {"symbol": "DOGE", "label": "Dogecoin", "entry": f"{doge_p:,.0f}", "tp": "Moon", "sl": "-10%"}
                ] 
            }
        },
        "bithumb_list": bithumb_data
    }
    
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)