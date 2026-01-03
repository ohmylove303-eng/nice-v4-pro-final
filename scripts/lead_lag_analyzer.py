#!/usr/bin/env python3
"""
Lead-Lag Analyzer
Uses Granger Causality to find predictive relationships between market assets.
"""
import os
import json
import logging
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from statsmodels.tsa.stattools import grangercausalitytests

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
OUTPUT_FILE = os.path.join(DATA_DIR, 'lead_lag_analysis.json')

class LeadLagAnalyzer:
    def __init__(self):
        self.pairs = [
            # Macro vs Indices
            ('^TNX', 'QQQ', '10Y Yield -> Nasdaq'),
            ('DX-Y.NYB', 'GC=F', 'Dollar -> Gold'),
            ('DX-Y.NYB', 'CL=F', 'Dollar -> Oil'),
            ('^VIX', 'SPY', 'VIX -> S&P 500'),
            
            # Sector Leading
            ('SMH', 'QQQ', 'Semiconductors -> Nasdaq'),
            ('XLF', 'SPY', 'Financials -> S&P 500'),
            ('XLE', 'CL=F', 'Energy Stocks -> Oil'), # Sometimes stocks lead commodity
            
            # Crypto Interactions
            ('BTC-USD', 'COIN', 'Bitcoin -> Coinbase'),
            ('BTC-USD', 'MSTR', 'Bitcoin -> MicroStrategy'),
            ('QQQ', 'BTC-USD', 'Nasdaq -> Bitcoin')
        ]
        self.max_lag = 5  # Days

    def fetch_data(self):
        logger.info("Fetching data for Lead-Lag analysis...")
        tickers = set()
        for p in self.pairs:
            tickers.add(p[0])
            tickers.add(p[1])
            
        data = yf.download(list(tickers), period='1y', progress=False)['Close']
        return data

    def run_granger_test(self, data, cause, effect, maxlag=5):
        """Run Granger Causality Test"""
        try:
            df = pd.DataFrame({'x': data[cause], 'y': data[effect]}).dropna()
            if len(df) < 50:
                return None
            
            # Granger test expects [y, x] to test if x causes y
            # We want to test if 'cause' causes 'effect', so input is [effect, cause]
            test_result = grangercausalitytests(df[[effect, cause]], maxlag=maxlag, verbose=False)
            
            best_p = 1.0
            best_lag = 0
            
            for lag, result in test_result.items():
                p_value = result[0]['ssr_chi2test'][1]
                if p_value < best_p:
                    best_p = p_value
                    best_lag = lag
                    
            return {'lag': best_lag, 'p_value': best_p}
            
        except Exception as e:
            logger.error(f"Error testing {cause} -> {effect}: {e}")
            return None

    def analyze(self):
        data = self.fetch_data()
        results = []
        
        for cause, effect, name in self.pairs:
            if cause not in data.columns or effect not in data.columns:
                continue
                
            res = self.run_granger_test(data, cause, effect, self.max_lag)
            if res and res['p_value'] < 0.05:  # Significant result
                logger.info(f"Significant: {name} (Lag: {res['lag']}d, p={res['p_value']:.4f})")
                results.append({
                    'name': name,
                    'cause': cause,
                    'effect': effect,
                    'lag_days': res['lag'],
                    'p_value': round(res['p_value'], 4),
                    'strength': 'High' if res['p_value'] < 0.01 else 'Medium'
                })
        
        # Sort by p-value (significance)
        results.sort(key=lambda x: x['p_value'])
        
        output = {
            'timestamp': datetime.now().isoformat(),
            'analysis': results,
            'summary': f"Found {len(results)} significant lead-lag relationships."
        }
        
        self.save_result(output)
        return output

    def save_result(self, result):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    LeadLagAnalyzer().analyze()
