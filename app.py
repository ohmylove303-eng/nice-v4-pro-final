# ============================================================
# NICE PRO v8.3 Backend - [REAL-TIME SCREENER]
# ============================================================

from flask import Flask, jsonify
from flask_cors import CORS
import logging
import requests
import pandas as pd
import config
import asyncio

# Services
from services.signal_agents import SignalAggregator
from services.guard_chain import GuardChain
from services.llm_orchestrator import LLMOrchestrator
from services.position_sizer import PositionSizer
from services.backtester import Backtester
from services.screener import BithumbScreener

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize Services
signal_agg = SignalAggregator()
guard_chain = GuardChain()
llm_master = LLMOrchestrator()
pos_sizer = PositionSizer()
backtester = Backtester()

class MarketData:
    @staticmethod
    def fetch(ticker, count=200):
        try:
            sym = ticker.replace("KRW-","")
            # 1. Candles
            url = f"{config.BITHUMB_API_URL}/candlestick/{sym}_KRW/24h"
            res = requests.get(url, timeout=1).json()
            if res['status'] != '0000': return None, None
            
            df = pd.DataFrame(res['data'], columns=['time','open','close','high','low','vol'])
            df[['open','close','high','low','vol']] = df[['open','close','high','low','vol']].astype(float)
            df.rename(columns={'vol':'volume'}, inplace=True)
            
            # 2. Orderbook
            url_ob = f"{config.BITHUMB_API_URL}/orderbook/{sym}_KRW"
            ob = requests.get(url_ob, timeout=1).json()
            
            return df.tail(count), ob['data']
        except: return None, None

def asyncio_run(future):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res = loop.run_until_complete(future)
    loop.close()
    return res

@app.route('/api/analyze/<ticker>')
def analyze(ticker):
    t_code = ticker.replace("KRW-","").upper()
    df, ob = MarketData.fetch(t_code, count=100)
    
    if df is None: return jsonify({"error": "Data Unavailable"}), 500
        
    # 1. 5-AGENTS
    signals = signal_agg.get_all_signals(df)
    
    # 2. GUARD
    bid = float(ob['bids'][0]['price'])
    guard_res = asyncio_run(guard_chain.execute_all(t_code, "BUY", 1.0, bid))
    
    # 3. LLM
    llm_res = llm_master.synthesize(t_code, signals['agent_scores'], signals['weighted_score'])
    
    # 4. KELLY
    kelly_res = pos_sizer.calculate(t_code, "BUY", 10000000)
    
    return jsonify({
        "ticker": t_code,
        "score": signals['weighted_score'],
        "type": llm_res.get('signal', 'TYPE C'),
        "kelly": kelly_res['kelly_pct'],
        "agents": signals['agent_scores'],
        "guards": guard_res['phase_results'],
        "ai_reasoning": llm_res.get('reasoning', "Analysis Complete"),
        "tech": {
            "trend": "UP" if signals['weighted_score'] > 55 else "DOWN",
            "rsi": signals['agent_scores']['technical']
        }
    })

@app.route('/api/backtest/<ticker>')
def backtest(ticker):
    t_code = ticker.replace("KRW-","").upper()
    df, _ = MarketData.fetch(t_code, count=200)
    if df is None: return jsonify({"error": "Data Unavailable"}), 500
    return jsonify(backtester.run(t_code, df))

@app.route('/api/screener/<category>')
def get_screener(category):
    # Retrieve Real-time Rankings from Bithumb
    data = BithumbScreener.get_rankings(category)
    return jsonify({"category": category, "list": data})

@app.route('/')
@app.route('/app')
def index():
    from flask import render_template
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)