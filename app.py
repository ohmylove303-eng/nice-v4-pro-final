# ============================================================
# NICE PRO v8.2 Backend - [DEEP LOGIC + BACKTEST]
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
            # 1. Candles (Fetch 200 for Backtest + Deep MA)
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

@app.route('/api/analyze/<ticker>')
def analyze(ticker):
    t_code = ticker.replace("KRW-","").upper()
    df, ob = MarketData.fetch(t_code, count=100)
    
    if df is None:
        return jsonify({"error": "Data Unavailable"}), 500
        
    # 1. 5-AGENTS (Deep Math)
    signals = signal_agg.get_all_signals(df)
    
    # 2. GUARD CHAIN
    bid = float(ob['bids'][0]['price'])
    guard_res = asyncio_run(guard_chain.execute_all(t_code, "BUY", 1.0, bid))
    
    # 3. LLM (Optimization)
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
        "ai_reasoning": llm_res.get('reasoning', "AI Analysis Complete"),
        # Config Data
        "v8_version": "8.2.0"
    })

@app.route('/api/backtest/<ticker>')
def backtest(ticker):
    t_code = ticker.replace("KRW-","").upper()
    df, _ = MarketData.fetch(t_code, count=200) # Need more history
    
    if df is None: return jsonify({"error": "Data Unavailable"}), 500
    
    res = backtester.run(t_code, df)
    return jsonify(res)

@app.route('/api/screener/<category>')
def get_screener(category):
    # Quick proxy to existing ranking
    return jsonify({"category": category, "list": []}) # Should implement real screener call if needed

# Async Helper
def asyncio_run(future):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res = loop.run_until_complete(future)
    loop.close()
    return res

@app.route('/')
@app.route('/app')
def index():
    from flask import render_template
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)