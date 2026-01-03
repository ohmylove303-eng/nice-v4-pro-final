#!/usr/bin/env python3
"""
Corporate News & Earnings Fetcher
Fetches 'Authoritative' data: Confirmed Earnings Dates & Major News Headlines
"""
import os, json, logging
import pandas as pd
import yfinance as yf
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CorporateIntelligence:
    def __init__(self):
        self.data_dir = os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        os.makedirs(self.data_dir, exist_ok=True)
        self.output_file = os.path.join(self.data_dir, 'news_events.json')
        self.portfolio_file = os.path.join(self.data_dir, 'us_portfolio.csv')

    def load_portfolio(self):
        if not os.path.exists(self.portfolio_file):
            return ['NVDA', 'AAPL', 'MSFT', 'TSLA'] # Default fallback
        try:
            df = pd.read_csv(self.portfolio_file)
            df.columns = [c.strip() for c in df.columns]
            return df['Ticker'].tolist()
        except:
            return []

    def fetch_data(self):
        tickers = self.load_portfolio()
        logger.info(f"Fetching intelligence for: {tickers}")
        
        earnings_data = []
        news_feed = []

        now = datetime.now()

        for ticker_symbol in tickers:
            try:
                ticker = yf.Ticker(ticker_symbol)
                
                # 1. Get Next Earnings Date
                # yfinance calendar returns a dictionary or dataframe. 
                # We try 'calendar' property which usually contains 'Earnings Date'
                earnings_date = "N/A"
                days_left = 999
                
                try:
                    cal = ticker.calendar
                    # Cal structure varies by version, handling common dict/df patterns
                    if cal and isinstance(cal, dict) and 'Earnings Date' in cal:
                        # usually a list of dates
                        dates = cal['Earnings Date']
                        if dates:
                            next_date = dates[0]
                            earnings_date = next_date.strftime("%Y-%m-%d")
                            days_left = (next_date - now.date()).days
                except Exception as e:
                    pass

                if earnings_date != "N/A":
                    earnings_data.append({
                        'ticker': ticker_symbol,
                        'date': earnings_date,
                        'days_left': days_left
                    })

                # 2. Get News
                news = ticker.news
                if news:
                    # Take top 2 relevant news
                    for n in news[:2]:
                        # Filter for timestamps to ensure freshness (optional, yf usually sends latest)
                        pub_time = datetime.fromtimestamp(n.get('providerPublishTime', 0))
                        news_feed.append({
                            'ticker': ticker_symbol,
                            'title': n.get('title'),
                            'publisher': n.get('publisher'),
                            'link': n.get('link'),
                            'time': pub_time.strftime("%Y-%m-%d %H:%M"),
                            'timestamp': n.get('providerPublishTime', 0)
                        })
            except Exception as e:
                logger.error(f"Error fetching data for {ticker_symbol}: {e}")

        # Sort earnings by nearest date
        earnings_data.sort(key=lambda x: x['days_left'])
        
        # Sort news by latest time
        news_feed.sort(key=lambda x: x['timestamp'], reverse=True)

        result = {
            'timestamp': now.isoformat(),
            'earnings': earnings_data,
            'news': news_feed[:20] # Top 20 latest news across portfolio
        }

        with open(self.output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Saved corporate intelligence to {self.output_file}")
        return result

if __name__ == "__main__":
    CorporateIntelligence().fetch_data()
