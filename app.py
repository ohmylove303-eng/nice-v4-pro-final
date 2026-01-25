# ============================================================
# NICE PRO v8.5 Backend - [COMPLETE SYSTEM SYNC]
# ============================================================

from flask import Flask, jsonify, request
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
from services.portfolio_manager import PortfolioManager

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
portfolio_mgr = PortfolioManager()

# Global Async Loop Helper
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res = loop.run_until_complete(coro)
    loop.close()
    return res

class MarketData:
    @staticmethod
    def fetch(ticker, timeframe="24h", count=100):
        api_tf = "24h"
        if timeframe == "scalp": api_tf = "30m"
        elif timeframe == "short": api_tf = "1h"
        
        try:
            sym = ticker.replace("KRW-","")
            url = f"{config.BITHUMB_API_URL}/candlestick/{sym}_KRW/{api_tf}"
            res = requests.get(url, timeout=1).json()
            if res['status'] != '0000': return None, None
            
            df = pd.DataFrame(res['data'], columns=['time','open','close','high','low','vol'])
            df[['open','close','high','low','vol']] = df[['open','close','high','low','vol']].astype(float)
            df.rename(columns={'vol':'volume'}, inplace=True)
            
            url_ob = f"{config.BITHUMB_API_URL}/orderbook/{sym}_KRW"
            ob = requests.get(url_ob, timeout=1).json()
            
            return df.tail(count), ob['data']
        except: return None, None

@app.route('/api/analyze/<ticker>')
def analyze(ticker):
    tf_mode = request.args.get('timeframe', 'day')
    t_code = ticker.replace("KRW-","").upper()
    df, ob = MarketData.fetch(t_code, timeframe=tf_mode)
    
    if df is None: return jsonify({"error": "Data Unavailable"}), 500
    
    signals = signal_agg.get_all_signals(df)
    bid = float(ob['bids'][0]['price'])
    guard_res = run_async(guard_chain.execute_all(t_code, "BUY", 1.0, bid))
    llm_res = llm_master.synthesize(f"{t_code} ({tf_mode.upper()})", signals['agent_scores'], signals['weighted_score'])
    kelly_res = pos_sizer.calculate(t_code, "BUY", portfolio_mgr.balance)
    
    return jsonify({
        "ticker": t_code,
        "mode": tf_mode,
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
    df, _ = MarketData.fetch(t_code, timeframe="24h", count=200)
    if df is None: return jsonify({"error": "Data Unavailable"}), 500
    return jsonify(backtester.run(t_code, df))

@app.route('/api/screener/<category>')
def get_screener(category):
    if category == "scalp":
        try:
            list_data = run_async(BithumbScreener.get_realtime_momentum())
            formatted = []
            for c in list_data:
                formatted.append({
                    "symbol": c['symbol'],
                    "change": round(c['momentum'], 2),
                    "volume": c['vol'],
                    "price": c['price']
                })
            return jsonify({"category": "scalp", "list": formatted})
        except Exception as e: return jsonify({"error": str(e)}), 500
    
    # Standard logic (Surge/Volume) implementation omitted for brevity but assumed present from previous
    try:
        url = f"{config.BITHUMB_API_URL}/ticker/ALL_KRW"
        res = requests.get(url, timeout=1).json()
        data = []
        for k, v in res['data'].items():
            if k == 'date': continue
            data.append({
                "symbol": k,
                "price": float(v['closing_price']),
                "change": float(v['fluctate_rate_24H']),
                "volume": float(v['acc_trade_value_24H'])
            })
        if category == "volume":
            data.sort(key=lambda x: x['volume'], reverse=True)
            data = data[:20]
        else:
            data.sort(key=lambda x: x['change'], reverse=True)
            data = [d for d in data if d['volume'] > 1000000000][:20]
        return jsonify({"category": category, "list": data})
    except: return jsonify({"list": []})

@app.route('/api/portfolio/metrics')
def get_portfolio():
    return jsonify(portfolio_mgr.get_metrics())

@app.route('/api/positions')
def get_positions():
    return jsonify(portfolio_mgr.get_positions())

@app.route('/')
@app.route('/app')
def index():
    from flask import render_template
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)