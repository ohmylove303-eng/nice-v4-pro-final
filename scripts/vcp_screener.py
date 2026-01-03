#!/usr/bin/env python3
"""
VCP Screener (Volatility Contraction Pattern)
Identifies stocks setting up for a potential breakout.
Logic:
1. Strong Trend (Above MA200, MA50)
2. Contraction Patterns (Lower Highs, Decreasing Volatility)
3. Volume Dry Up (Low volume during consolidation)
"""
import os
import json
import logging
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
OUTPUT_FILE = os.path.join(DATA_DIR, 'vcp_candidates.json')

class VCPScreener:
    def __init__(self):
        # Top 50 most active/liquid stocks for demo purposes
        # In production, this should screen a larger universe (e.g., S&P 500)
        self.tickers = [
            'NVDA', 'AMD', 'TSLA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'NFLX',
            'PLTR', 'COIN', 'MSTR', 'SMCI', 'ARM', 'AVGO', 'ORCL', 'CRM', 'ADBE',
            'NET', 'CRWD', 'PANW', 'SNOW', 'DDOG', 'ZS', 'TTD', 'DKNG', 'UBER',
            'SHOP', 'SQ', 'PYPL', 'AFRM', 'SOFI', 'MARA', 'RIOT', 'CLSK',
            'LLY', 'NVO', 'VRTX', 'REGN', 'ISRG', 'CAT', 'DE', 'URI', 'GME'
        ]

    def fetch_data(self, ticker):
        try:
            df = yf.download(ticker, period='1y', progress=False)
            if df.empty: return None
            return df
        except:
            return None

    def check_trend_template(self, df):
        """
        Stage 2 Trend Template (Minervini)
        1. Price > MA150 and MA200
        2. MA150 > MA200
        3. MA200 trending up (at least 1 month)
        4. MA50 > MA150 and MA200
        5. Price > MA50
        6. Price > 25% above 52-week low
        7. Price within 25% of 52-week high
        """
        try:
            # Flatten MultiIndex if necessary
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            close = df['Close']
            
            ma50 = close.rolling(window=50).mean().iloc[-1]
            ma150 = close.rolling(window=150).mean().iloc[-1]
            ma200 = close.rolling(window=200).mean().iloc[-1]
            ma200_20days_ago = close.rolling(window=200).mean().iloc[-20]
            
            current_price = close.iloc[-1]
            low_52w = close.min()
            high_52w = close.max()
            
            # Condition 1: Price > MA150 and MA200
            if current_price < ma150 or current_price < ma200: return False
            
            # Condition 2: MA150 > MA200
            if ma150 < ma200: return False
            
            # Condition 3: MA200 rising
            if ma200 < ma200_20days_ago: return False
            
            # Condition 4: MA50 > MA150 & MA200
            if ma50 < ma150 or ma50 < ma200: return False
            
            # Condition 5: Price > MA50 (Momentum) - Optional but good
            if current_price < ma50: return False
            
            # Condition 6: Price > 30% above 52w low
            if current_price < (low_52w * 1.3): return False
            
            # Condition 7: Within 25% of 52w High
            if current_price < (high_52w * 0.75): return False
            
            return True
        except Exception as e:
            # logger.error(f"Trend Check Error: {e}")
            return False

    def detect_vcp(self, df):
        """
        Detect Volatility Contraction Pattern
        Looking for decreasing volatility (tightening)
        """
        # Simplified Logic for Demo:
        # Check standard deviation of last 10 days vs previous 10-20 days
        # If volatility is shrinking, it's a candidate
        
        try:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            close = df['Close']
            vol = df['Volume']
            
            # Volatility (Std Dev of % returns)
            returns = close.pct_change()
            
            vol_recent = returns.tail(5).std()
            vol_prev = returns.iloc[-20:-5].std()
            
            # Contraction: Recent volatility should be significantly lower than previous
            is_contracting = vol_recent < (vol_prev * 0.7)
            
            # Volume Dry Up: Recent average volume < 50-day average volume
            vol_ma50 = vol.rolling(window=50).mean().iloc[-1]
            recent_vol_avg = vol.tail(5).mean()
            
            is_volume_dry = recent_vol_avg < (vol_ma50 * 0.8)
            
            return is_contracting and is_volume_dry
            
        except Exception:
            return False

    def run(self):
        logger.info(f"Screening {len(self.tickers)} stocks for VCP setups...")
        candidates = []
        
        for ticker in self.tickers:
            df = self.fetch_data(ticker)
            if df is None: continue
            
            if self.check_trend_template(df):
                if self.detect_vcp(df):
                    logger.info(f"Found VCP Candidate: {ticker}")
                    
                    # Prepare info
                    price = df['Close'].iloc[-1]
                    high_52w = df['Close'].max()
                    from_high = (price - high_52w) / high_52w * 100
                    
                    candidates.append({
                        'ticker': ticker,
                        'price': round(float(price), 2),
                        'from_52w_high': round(float(from_high), 2),
                        'pattern': 'VCP (Tightening)',
                        'stage': '2 (Uptrend)'
                    })
        
        output = {
            'timestamp': datetime.now().isoformat(),
            'candidates': candidates,
            'count': len(candidates)
        }
        
        self.save_result(output)
        return output

    def save_result(self, result):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    VCPScreener().run()
