#!/usr/bin/env python3
"""Insider Trading Tracker"""
import os, json, logging
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InsiderTracker:
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.output_file = os.path.join(data_dir, 'insider_moves.json')
        
    def get_insider_activity(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            df = stock.insider_transactions
            if df is None or df.empty: return []
            
            cutoff = pd.Timestamp.now() - pd.Timedelta(days=180)
            recent = []
            for date, row in df.sort_index(ascending=False).iterrows():
                if isinstance(date, pd.Timestamp) and date < cutoff: continue
                text = str(row.get('Text', '')).lower()
                if 'purchase' in text or 'buy' in text:
                    txn_type = 'Buy'
                elif 'sale' in text or 'sell' in text:
                    txn_type = 'Sell'
                else: continue
                recent.append({
                    'date': str(date.date()) if hasattr(date, 'date') else str(date),
                    'insider': row.get('Insider', 'N/A'),
                    'type': txn_type,
                    'value': float(row.get('Value', 0) or 0)
                })
            return recent[:10]
        except: return []

    def run(self, tickers=None):
        logger.info("Tracking insider activity...")
        if tickers is None:
            tickers = ['AAPL','NVDA','TSLA','MSFT','AMZN','META','GOOGL','JPM','GS','BAC']
        
        results = {}
        for t in tickers:
            acts = self.get_insider_activity(t)
            if acts:
                buys = [a for a in acts if a['type']=='Buy']
                sells = [a for a in acts if a['type']=='Sell']
                results[t] = {'buy_count': len(buys), 'sell_count': len(sells), 'transactions': acts[:5]}
        
        output = {'timestamp': datetime.now().isoformat(), 'details': results}
        with open(self.output_file, 'w') as f: json.dump(output, f, indent=2)
        logger.info(f"Saved to {self.output_file}")
        return output

if __name__ == "__main__":
    InsiderTracker().run()
