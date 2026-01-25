# ============================================================
# NICE PRO v8.0 Backend - [ULTRATHINK ARCHITECTURE]
# ============================================================

from flask import Flask, jsonify
from flask_cors import CORS
import logging
import os
import asyncio
# Import New Services
from services.signal_agents import SignalAggregator
from services.guard_chain import GuardChain
from services.llm_orchestrator import LLMOrchestrator
from services.position_sizer import PositionSizer
from services.signal_agents import TechnicalAgent # Fallback or direct use

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize Services
signal_agg = SignalAggregator()
guard_chain = GuardChain()
llm_master = LLMOrchestrator()
pos_sizer = PositionSizer()

@app.route('/api/analyze/<ticker>')
def analyze(ticker):
    try:
        t_code = ticker.replace("KRW-","").upper()
        
        # 1. RUN 5-AGENTS (Signal Layer)
        # In Flask (sync), we run this. In production, use async proper.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        signals = loop.run_until_complete(signal_agg.get_all_signals(t_code))
        
        # 2. RUN GUARD CHAIN (Defense Layer)
        guard_res = loop.run_until_complete(guard_chain.execute_all(t_code, "BUY", 1.0, 0))
        
        # 3. RUN LLM (Orchestration Layer)
        llm_res = llm_master.synthesize(
            t_code, 
            signals['agent_scores'], 
            signals['weighted_score']
        )
        
        # 4. RUN POSITION SIZER (Money Management Layer)
        kelly_res = pos_sizer.calculate(
            t_code, "BUY", 10000000, win_rate=0.6, rr_ratio=2.0
        )
        loop.close()
        
        # Construct Final Response for Dashboard
        return jsonify({
            "ticker": t_code,
            "v8_data": True,
            "score": signals['weighted_score'],
            "type": llm_res.get('signal', 'TYPE C'),
            "kelly": kelly_res['kelly_pct'],
            
            # 5 Agents Detail
            "agents": signals['agent_scores'],
            
            # Guard Detail
            "guards": guard_res['phase_results'],
            
            # AI Logic
            "ai_reasoning": llm_res.get('reasoning', 'Analysis Complete'),
            
            # Legacy fields for chart compatibility
            "tech": {
                "price": 0, # Frontend handles fetching price for chart usually, or we add it here
                "trend": "UP" if signals['weighted_score'] > 60 else "DOWN",
                "rsi": signals['agent_scores']['technical'] # Using Tech Agent score as proxy
            }
        })
        
    except Exception as e:
        logger.error(str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/')
@app.route('/app')
def index():
    from flask import render_template
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)