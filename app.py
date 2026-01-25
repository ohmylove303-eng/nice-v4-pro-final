# ============================================================
# NICE PRO v8.1 Backend - [TOKEN EFFICIENT]
# ============================================================

from flask import Flask, jsonify
from flask_cors import CORS
import logging
import requests
import pandas as pd
import config
from services.signal_agents import SignalAggregator
from services.guard_chain import GuardChain
from services.llm_orchestrator import LLMOrchestrator
from services.position_sizer import PositionSizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Services
signal_agg = SignalAggregator()
guard_chain = GuardChain()
llm_master = LLMOrchestrator()
pos_sizer = PositionSizer()

class MarketData:
    @staticmethod
    def fetch(ticker):
        try:
            sym = ticker.replace("KRW-","")
            # 1. Candles (For Agents)
            url = f"{config.BITHUMB_API_URL}/candlestick/{sym}_KRW/24h"
            res = requests.get(url, timeout=1).json()
            df = pd.DataFrame(res['data'], columns=['time','open','close','high','low','vol'])
            df[['open','close','high','low','vol']] = df[['open','close','high','low','vol']].astype(float)
            df.rename(columns={'vol':'volume'}, inplace=True)
            
            # 2. Orderbook (For Guard)
            url_ob = f"{config.BITHUMB_API_URL}/orderbook/{sym}_KRW"
            ob = requests.get(url_ob, timeout=1).json()
            
            return df, ob['data']
        except: return None, None

@app.route('/api/analyze/<ticker>')
def analyze(ticker):
    t_code = ticker.replace("KRW-","").upper()
    df, ob = MarketData.fetch(t_code)
    
    if df is None:
        return jsonify({"error": "Data Unavailable"}), 500
        
    # 1. 5-AGENTS (Real Math on DF)
    signals = signal_agg.get_all_signals(df)
    
    # 2. GUARD CHAIN (Real Orderbook Check)
    # Extract bid/ask for guard phase
    bid = float(ob['bids'][0]['price'])
    ask = float(ob['asks'][0]['price'])
    # Simulate quantity logic or pass raw
    guard_res = asyncio_run(guard_chain.execute_all(t_code, "BUY", 1.0, bid))
    
    # 3. LLM (Token Optimized Prompt)
    llm_res = llm_master.synthesize(
        t_code, 
        signals['agent_scores'], 
        signals['weighted_score']
    )
    
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
        # Legacy for Chart
        "tech": {
            "trend": "UP" if signals['weighted_score'] > 55 else "DOWN",
            "rsi": signals['agent_scores']['technical']
        }
    })

# Helper for async running in Flask
def asyncio_run(future):
    import asyncio
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