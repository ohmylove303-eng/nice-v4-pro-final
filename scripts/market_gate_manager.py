#!/usr/bin/env python3
"""
Market Gate Manager
Analyzes overall market health to determine Risk On/Off status.
Inputs: SPY/QQQ trends, VIX, Market Breadth (Net Highs/Lows)
Output: Market Gate Status (GREEN/YELLOW/RED)
"""
import os
import json
import logging
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
GATE_FILE = os.path.join(DATA_DIR, 'market_gate.json')

class MarketGateManager:
    def __init__(self):
        self.tickers = {
            'SPY': 'SPY',
            'QQQ': 'QQQ',
            'IWM': 'IWM', # Russell 2000
            'VIX': '^VIX'
        }
    
    def fetch_data(self):
        """Fetch necessary market data"""
        logger.info("Fetching market data for Gate analysis...")
        data = {}
        try:
            # Download 1 year of data to calculate 200MA safely
            df = yf.download(list(self.tickers.values()), period='1y', progress=False)
            
            # Accessing MultiIndex columns correctly
            closes = df['Close']
            
            for name, ticker in self.tickers.items():
                if ticker in closes.columns:
                    data[name] = closes[ticker].dropna()
                else:
                    logger.warning(f"Ticker {ticker} not found in downloaded data")
            
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            
        return data

    def calculate_ma(self, series, windows=[20, 50, 200]):
        """Calculate Moving Averages"""
        ma = {}
        for w in windows:
            ma[f'MA{w}'] = series.rolling(window=w).mean().iloc[-1]
        return ma

    def analyze_trend(self, price, ma):
        """Analyze trend based on Price vs MAs"""
        # Stage 2 Criteria (simplified):
        # 1. Price > MA200
        # 2. MA50 > MA150 (not calculated here, using MA50 > MA200 as proxy)
        # 3. Price > MA50
        
        score = 0
        reasons = []
        
        current_price = price.iloc[-1]
        
        if current_price > ma['MA200']:
            score += 30
            reasons.append("Price > MA200 (Long-term Uptrend)")
        else:
            reasons.append("Price < MA200 (Long-term Downtrend)")
            
        if ma['MA50'] > ma['MA200']:
            score += 20
            reasons.append("MA50 > MA200 (Golden Cross Alignment)")
            
        if current_price > ma['MA50']:
            score += 20
            reasons.append("Price > MA50 (Mid-term Uptrend)")
            
        if current_price > ma['MA20']:
            score += 10
            reasons.append("Price > MA20 (Short-term Momentum)")
            
        return score, reasons

    def analyze_vix(self, vix_series):
        """Analyze VIX level and trend"""
        current_vix = vix_series.iloc[-1]
        ma20_vix = vix_series.rolling(window=20).mean().iloc[-1]
        
        score = 0
        reasons = []
        
        if current_vix < 20:
            score += 10
            reasons.append(f"VIX is Low ({current_vix:.2f} < 20)")
        elif current_vix > 30:
            score -= 20
            reasons.append(f"VIX is High ({current_vix:.2f} > 30)")
            
        if current_vix < ma20_vix:
            score += 10
            reasons.append("VIX is falling (Below MA20)")
        else:
            reasons.append("VIX is rising (Above MA20)")
            
        return score, reasons

    def run_analysis(self):
        data = self.fetch_data()
        if not data:
            logger.error("No data available for analysis")
            return
        
        total_score = 0
        all_reasons = []
        
        # 1. Analyze SPY (S&P 500) - Weight 40%
        if 'SPY' in data:
            spy_ma = self.calculate_ma(data['SPY'])
            spy_score, spy_reasons = self.analyze_trend(data['SPY'], spy_ma)
            # Normalize SPY score (max 80) to 40 points
            total_score += (spy_score / 80) * 40
            all_reasons.extend([f"[SPY] {r}" for r in spy_reasons])
            
        # 2. Analyze QQQ (Nasdaq) - Weight 30%
        if 'QQQ' in data:
            qqq_ma = self.calculate_ma(data['QQQ'])
            qqq_score, qqq_reasons = self.analyze_trend(data['QQQ'], qqq_ma)
            # Normalize QQQ score (max 80) to 30 points
            total_score += (qqq_score / 80) * 30
            all_reasons.extend([f"[QQQ] {r}" for r in qqq_reasons])
            
        # 3. Analyze VIX - Weight 20%
        if 'VIX' in data:
            vix_score, vix_reasons = self.analyze_vix(data['VIX'])
            # Normalize VIX score (max 20) to 20 points
            # Ensure not negative contribution to sum, but VIX logic is separate
            # Here VIX score is max 20, min -20
            # If score is 20 -> add 20. If 0 -> add 0.
            total_score += max(0, vix_score)
            all_reasons.extend([f"[VIX] {r}" for r in vix_reasons])
            
        # 4. Market Breadth / IWM - Weight 10%
        if 'IWM' in data:
            iwm_ma = self.calculate_ma(data['IWM'])
            iwm_score, _ = self.analyze_trend(data['IWM'], iwm_ma)
            total_score += (iwm_score / 80) * 10
        
        # Determine Gate Status
        # Green: > 70
        # Yellow: 40 - 70
        # Red: < 40
        
        final_score = round(total_score)
        
        if final_score >= 75:
            gate_status = "GREEN"
            action = "Aggressive Long / Leverage OK"
        elif final_score >= 40:
            gate_status = "YELLOW"
            action = "Cautious / Quality Only / No Leverage"
        else:
            gate_status = "RED"
            action = "Cash is King / Short / Hedging"
            
        result = {
            "gate": gate_status,
            "score": final_score,
            "action": action,
            "reasons": all_reasons,
            "timestamp": datetime.now().isoformat(),
            "indices": {
                "SPY": round(data['SPY'].iloc[-1], 2) if 'SPY' in data else 0,
                "QQQ": round(data['QQQ'].iloc[-1], 2) if 'QQQ' in data else 0,
                "VIX": round(data['VIX'].iloc[-1], 2) if 'VIX' in data else 0
            }
        }
        
        self.save_result(result)
        logger.info(f"Market Gate Analysis Complete: {gate_status} (Score: {final_score})")
        return result

    def save_result(self, result):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(GATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    MarketGateManager().run_analysis()
