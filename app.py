# ============================================================
# NICE PRO v6.0 Backend - [NICE MODEL + BACKTEST ENGINE]
# ============================================================

from flask import Flask, jsonify
from flask_cors import CORS
import logging
import pyupbit 
from datetime import datetime, timedelta
import requests
import config
import google.generativeai as genai
import os
import pandas as pd
import numpy as np
import time

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
# 1. DATA ENGINE (Bithumb)
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
    def get_orderbook(ticker):
        try:
            sym = ticker.replace("KRW-", "")
            url = f"{config.BITHUMB_API_URL}/orderbook/{sym}_KRW"
            res = requests.get(url, timeout=2).json()
            if res['status'] != '0000': return None
            return res['data']
        except: return None

    @staticmethod
    def get_candles(ticker, interval="24h", limit=200):
        try:
            sym = ticker.replace("KRW-", "")
            url = f"{config.BITHUMB_API_URL}/candlestick/{sym}_KRW/{interval}"
            res = requests.get(url, timeout=2).json()
            if res['status'] != '0000': raise Exception("Err")
            
            data = res['data']
            df = pd.DataFrame(data, columns=['time', 'open', 'close', 'high', 'low', 'volume'])
            df[['open','close','high','low','volume']] = df[['open','close','high','low','volume']].astype(float)
            return df.tail(limit)
        except:
            try: return pyupbit.get_ohlcv(ticker, interval="day", count=limit)
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

        if category == "surge":
            res = [c for c in candidates if c['change'] >= 5 and c['volume'] > 5000000000]
            res.sort(key=lambda x: x['change'], reverse=True)
            return res[:15]
        elif category == "scalping":
            res = [c for c in candidates if c['volume'] > 20000000000]
            res.sort(key=lambda x: x['volume'], reverse=True)
            return res[:15]
        elif category == "majors":
            majors = ["BTC", "ETH", "XRP", "SOL", "DOGE", "ADA", "DOT"]
            res = [c for c in candidates if c['symbol'] in majors]
            res.sort(key=lambda x: x['volume'], reverse=True)
            return res
        return []

# ============================================================
# 2. GUARD CHAIN (Phase 1-4)
# ============================================================
class GuardChain:
    @staticmethod
    def verify(ticker, df, orderbook):
        report = {"passed": True, "reason": "All checks passed", "level": "SAFE"}
        
        # Phase 1: Data Integrity
        if df.isnull().values.any():
            return {"passed": False, "reason": "Data Corruption", "level": "CRITICAL"}
            
        # Phase 3: Liquidity & Spread (Orderbook)
        if orderbook:
            bids = orderbook['bids']
            asks = orderbook['asks']
            if not bids or not asks:
                return {"passed": False, "reason": "Empty Orderbook", "level": "CRITICAL"}
                
            best_bid = float(bids[0]['price'])
            best_ask = float(asks[0]['price'])
            
            # Spread Calculation (bps)
            spread = (best_ask - best_bid) / best_bid * 10000
            
            if spread > 100: # > 1% check
                return {"passed": False, "reason": f"Wide Spread ({spread:.0f}bps)", "level": "WARNING"}
        
        # Outlier
        recent = df['close'].tail(20)
        if abs(recent.iloc[-1] - recent.mean()) > (3 * recent.std()):
            report.update({"level": "CAUTION", "reason": "Price Outlier (3-Sigma)"})
            
        return report

# ============================================================
# 3. POSITION MANAGER (Phase 6: Kelly Criterion)
# ============================================================
class PositionManager:
    @staticmethod
    def calculate_size(win_rate=0.65, avg_win=2.0, avg_loss=1.0, balance=1000000):
        """
        Kelly Criterion: f* = (bp - q) / b
        b = odds (win/loss ratio)
        p = win probability
        q = loss probability
        """
        b = avg_win / avg_loss if avg_loss > 0 else 0
        p = win_rate
        q = 1 - p
        
        if b == 0: return 0
        
        kelly_f = (b * p - q) / b
        safe_f = max(0, kelly_f * 0.5) # Half Kelly for Safety
        
        # Cap at 20% of Portfolio for single asset
        allocation = min(safe_f, 0.20) 
        
        return {
            "kelly_pct": round(kelly_f * 100, 1),
            "safe_pct": round(safe_f * 100, 1),
            "allocation_krw": int(balance * allocation)
        }

# ============================================================
# 4. TECH ANALYST
# ============================================================
class TechnicalAnalyst:
    @staticmethod
    def analyze(ticker, df):
        curr = df['close'].iloc[-1]
        high_200 = df['high'].max()
        low_200 = df['low'].min()
        diff = high_200 - low_200
        
        fib = {
            "0.236": high_200 - diff * 0.236,
            "0.382": high_200 - diff * 0.382,
            "0.5": high_200 - diff * 0.5,
            "0.618": high_200 - diff * 0.618
        }
        
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        ma60 = df['close'].rolling(60).mean().iloc[-1]
        trend = "UPTREND" if ma20 > ma60 else "DOWNTREND"
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return { "price": curr, "trend": trend, "fib": fib, "rsi": rsi.iloc[-1] }

# ============================================================
# 5. BACKTEST ENGINE
# ============================================================
class Backtester:
    @staticmethod
    def run(ticker):
        df = BithumbScreener.get_candles(ticker, limit=200)
        if df is None or len(df) < 60: return {"error": "Insufficient Data"}
        
        # Logic: Trend Following with RSI Dip Buy
        # Buy: Trend UP (MA20 > MA60) AND RSI < 40
        # Sell: RSI > 70 or Trend Reversal
        
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        balance = 100000000
        position = 0
        trade_log = []
        wins = 0
        total_trades = 0
        
        for i in range(60, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i-1]
            price = row['close']
            date = str(row['time']) # Assuming time check
            
            # SIGNAL
            is_uptrend = row['ma20'] > row['ma60']
            is_oversold = row['rsi'] < 40
            is_overbought = row['rsi'] > 70
            
            # BUY
            if position == 0 and is_uptrend and is_oversold:
                position = balance / price
                balance = 0
                trade_log.append({"type": "BUY", "price": price, "date": date})
            
            # SELL
            elif position > 0 and (is_overbought or not is_uptrend):
                new_bal = position * price
                profit = new_bal - 100000000 if total_trades == 0 else new_bal - (trade_log[-1]['price'] * position)
                
                if profit > 0: wins += 1
                total_trades += 1
                
                balance = new_bal
                position = 0
                trade_log.append({"type": "SELL", "price": price, "date": date, "pnl": round(profit,0)})
                
        # Final Value
        final_val = balance + (position * df.iloc[-1]['close'])
        ret = (final_val - 100000000) / 100000000 * 100
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "initial_balance": 100000000,
            "final_balance": final_val,
            "return_pct": round(ret, 2),
            "win_rate": round(win_rate, 1),
            "trades_count": total_trades,
            "log": trade_log[-5:] # Show last 5
        }

# ============================================================
# API ENDPOINTS
# ============================================================
@app.route('/api/screener/<category>')
def get_screener(category):
    return jsonify({"category": category, "list": BithumbScreener.get_rankings(category)})

@app.route('/api/analyze/<ticker>')
def analyze_coin(ticker):
    try:
        t_raw = ticker.replace("KRW-","")
        t_code = f"KRW-{t_raw}"
        
        df = BithumbScreener.get_candles(t_code)
        ob = BithumbScreener.get_orderbook(t_code)
        
        guard = GuardChain.verify(t_code, df, ob)
        if not guard['passed']:
             return jsonify({ "error": "GUARD FAIL", "guard": guard, "tech": None, "ai": None })
             
        tech = TechnicalAnalyst.analyze(t_code, df)
        
        # Phase 6: Kelly Sizing
        # Assume generic 60% win rate for non-backtested assets or use backtest result later
        pos = PositionManager.calculate_size(win_rate=0.6, avg_win=1.5, avg_loss=1.0)
        
        ai_res = {"action": "WAIT", "reasoning": "AI Off"}
        if model:
            prompt = f"""
            [NICE PROTOCOL v6]
            Ticker: {t_code} | Price: {tech['price']} | RSI: {tech['rsi']:.1f}
            Trend: {tech['trend']} | Pivot: {tech['fib']['0.382']:.0f}
            Pos Sizing (Kelly): {pos['safe_pct']}% of capital.
            
            Action: BUY/SELL/WAIT.
            Reasoning: Clear strategy based on levels.
            output JSON.
            """
            try:
                res = model.generate_content(prompt)
                import json
                txt = res.text
                if "{" in txt: ai_res = json.loads(txt[txt.find("{"):txt.rfind("}")+1])
            except: pass
            
        return jsonify({
            "ticker": t_code,
            "guard": guard,
            "tech": tech,
            "position": pos,
            "ai": ai_res
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/backtest/<ticker>')
def run_backtest(ticker):
    try:
        t_code = f"KRW-{ticker.replace('KRW-','')}"
        res = Backtester.run(t_code)
        return jsonify(res)
    except Exception as e:
         return jsonify({"error": str(e)}), 500

@app.route('/')
@app.route('/app')
def index():
    from flask import render_template
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)