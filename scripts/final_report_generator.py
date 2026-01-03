#!/usr/bin/env python3
"""Final Top 10 Report Generator"""
import os, json, logging
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinalReportGenerator:
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
    def run(self, top_n=10):
        stats_path = os.path.join(self.data_dir, 'smart_money_picks_v2.csv')
        if not os.path.exists(stats_path): 
            logger.warning("No screening data")
            return
        df = pd.read_csv(stats_path)
        
        # --- Live Price Patch (Start) ---
        import yfinance as yf
        tickers = df['ticker'].tolist()
        try:
            # Get last 5 days just to be safe
            live_data = yf.download(tickers, period='5d', progress=False)['Close']
            if isinstance(live_data, pd.Series): live_data = live_data.to_frame()
            live_prices = live_data.iloc[-1].to_dict()
            prev_prices = live_data.iloc[-2].to_dict()
        except Exception as e:
            logger.error(f"Live price fetch failed: {e}")
            live_prices = {}
            prev_prices = {}
        # --- Live Price Patch (End) ---
        
        ai_path = os.path.join(self.data_dir, 'ai_summaries.json')
        ai_data = {}
        if os.path.exists(ai_path):
            with open(ai_path) as f: ai_data = json.load(f)
            
        results = []
        for _, row in df.iterrows():
            ticker = row['ticker']
            summary_info = ai_data.get(ticker, {})
            # Handle string vs dict summary
            if isinstance(summary_info, dict):
                summary = summary_info.get('summary_ko', summary_info.get('summary_en', ''))
            else: # string
                summary = str(summary_info)

            ai_score = 0
            rec = "Hold"
            if "매수" in summary or "Buy" in summary.lower(): 
                ai_score, rec = 10, "Buy"
            if "적극" in summary or "Strong" in summary.lower() or "strong" in summary.lower():
                ai_score, rec = 20, "Strong Buy"
            
            # Use Live Price if available
            price = live_prices.get(ticker, row['current_price'])
            prev = prev_prices.get(ticker, price)
            
            try:
                change_pct = ((price - prev) / prev) * 100 if prev else 0.0
            except: change_pct = 0.0

            final_score = row['composite_score'] * 0.8 + ai_score
            
            results.append({
                'ticker': ticker, 'name': row.get('name', ticker),
                'final_score': round(final_score, 1), 'quant_score': round(row['composite_score'], 1),
                'ai_recommendation': rec, 'current_price': round(price, 2),
                'change_pct': round(change_pct, 2),
                'ai_summary': summary, 'sector': row.get('sector', 'N/A'),
                'avg_vol_m': row.get('avg_vol_m', 0),
                'liq_score': row.get('liq_score', 0),
                'gap_velocity': row.get('gap_velocity', 0),
                'target_upside': row.get('target_upside', 0)
            })
            
        results.sort(key=lambda x: x['final_score'], reverse=True)
        top_picks = results[:top_n]
        for i, p in enumerate(top_picks, 1): p['rank'] = i
        
        with open(os.path.join(self.data_dir, 'final_top10_report.json'), 'w') as f:
            json.dump({'timestamp': datetime.now().isoformat(), 'top_picks': top_picks}, f, indent=2, ensure_ascii=False)
            
        with open(os.path.join(self.data_dir, 'smart_money_current.json'), 'w') as f:
            json.dump({'picks': top_picks}, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Generated Final Report for {len(top_picks)} stocks")
        return top_picks

if __name__ == "__main__":
    FinalReportGenerator().run()
