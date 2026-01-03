#!/usr/bin/env python3
"""Historical Returns Analyzer"""
import os, json, logging
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HistoricalReturnsAnalyzer:
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.output_file = os.path.join(self.data_dir, 'historical_returns.json')

    def load_portfolio(self):
        """Load portfolio from CSV"""
        csv_path = os.path.join(self.data_dir, 'us_portfolio.csv')
        if not os.path.exists(csv_path):
            return None, None
        
        try:
            df = pd.read_csv(csv_path)
            df.columns = [c.strip() for c in df.columns]
            if 'Ticker' not in df.columns: return None, None
            tickers = df['Ticker'].tolist()
            shares = df['Shares'].tolist() if 'Shares' in df.columns else [1] * len(tickers)
            return tickers, shares
        except:
            return None, None

    def analyze_returns(self, tickers=None):
        try:
            shares = None
            if tickers is None:
                tickers, shares = self.load_portfolio()
                if tickers is None: # Default list
                    tickers = ['NVDA', 'MSFT', 'AAPL', 'GOOGL', 'AMZN', 'TSLA', 'AMD', 'META']
                    shares = [1] * len(tickers)

            logger.info(f"Fetching historical data for: {tickers}")
            # Fetch 5 years of data
            data = yf.download(tickers, period='5y', interval='1mo', progress=False)['Close']
            
            if data.empty:
                return {}

            if isinstance(data, pd.Series):
                data = data.to_frame()
            
            data = data.ffill().bfill()
            
            # --- Weighted Portfolio Index Calculation ---
            # Instead of simple equal weight, simulate holding 'shares' amount of each stock
            # Normalized Method: Assume we held these shares constant over 5 years (Simplified Backtest)
            
            total_value_series = pd.Series(0, index=data.index)
            
            # Create share map
            share_map = {t: s for t, s in zip(tickers, shares)}
            
            valid_tickers = [t for t in tickers if t in data.columns]
            
            for ticker in valid_tickers:
                # Value = Price * Shares
                total_value_series += data[ticker] * share_map.get(ticker, 1)
            
            # Calculate Monthly Returns of the Total Portfolio Value
            monthly_returns = total_value_series.pct_change()
            
            # Normalize index for stats if needed, but returns calculation is key
            portfolio_index = total_value_series
            
            # Prepare Grid Data: Year x Month
            years = sorted(list(set(monthly_returns.index.year)), reverse=True)
            heatmap_data = []
            
            months_map = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 
                          7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
            
            stats_by_year = {}

            # Sanitize function
            def clean_float(val):
                if pd.isna(val) or np.isinf(val):
                    return 0.0
                return round(float(val), 2)

            for year in years:
                year_data = monthly_returns[monthly_returns.index.year == year]
                row = {'name': str(year), 'data': []}
                
                yr_returns = []
                for month_num in range(1, 13):
                    if month_num in year_data.index.month:
                        mask = (year_data.index.month == month_num)
                        if mask.any():
                            val = year_data[mask].iloc[0] * 100
                            cleaned_val = clean_float(val)
                            row['data'].append({'x': months_map[month_num], 'y': cleaned_val})
                            yr_returns.append(cleaned_val)
                        else:
                            row['data'].append({'x': months_map[month_num], 'y': 0.0})
                    else:
                        row['data'].append({'x': months_map[month_num], 'y': 0.0})
                
                heatmap_data.append(row)
                
                # Yearly Stats
                if yr_returns:
                    # Calculate Total Return for the Year accurately
                    vals = portfolio_index[portfolio_index.index.year == year]
                    if not vals.empty:
                        start_val = vals.iloc[0]
                        end_val = vals.iloc[-1]
                        total_return = (end_val / start_val) - 1 if start_val != 0 else 0
                    else:
                        total_return = 0

                    stats_by_year[year] = {
                        'total_return': clean_float(total_return * 100),
                        'best_month': clean_float(max(yr_returns)),
                        'worst_month': clean_float(min(yr_returns)),
                        'positive_months': len([r for r in yr_returns if r > 0])
                    }

            result = {
                'timestamp': datetime.now().isoformat(),
                'heatmap_series': heatmap_data,
                'yearly_stats': stats_by_year
            }
            
            with open(self.output_file, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"Saved historical returns to {self.output_file}")
            return result
            
        except Exception as e:
            logger.error(f"Error in historical returns: {e}")
            import traceback
            traceback.print_exc()
            return {}

if __name__ == "__main__":
    HistoricalReturnsAnalyzer().analyze_returns()
