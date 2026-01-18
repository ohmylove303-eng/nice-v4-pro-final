# US Stocks Data Collection
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List
import pytz

class USStocksDataCollector:
    """미국 주식 데이터 수집"""
    
    def __init__(self):
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        self.finnhub_key = os.getenv("FINNHUB_API_KEY")
        self.est = pytz.timezone('US/Eastern')
        
        # 모니터링 종목 (S&P 500 상위)
        self.monitored_tickers = [
            "NVDA", "TSLA", "MSFT", "AAPL", "GOOGL", "AMZN",
            "META", "NFLX", "CRM", "ADBE", "PYPL", "UBER",
            "SPOT", "SNPS", "CDNS", "MSTR", "SQ", "PLTR"
        ]
    
    def get_daily_ohlcv(self, ticker: str, days_ago: int = 0) -> Dict:
        """일일 OHLCV"""
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': ticker,
            'outputsize': 'compact',
            'apikey': self.alpha_vantage_key
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if 'Time Series (Daily)' in data:
                ts = data['Time Series (Daily)']
                dates = list(ts.keys())
                
                if len(dates) > days_ago:
                    date_key = dates[days_ago]
                    return {
                        'date': date_key,
                        'open': float(ts[date_key]['1. open']),
                        'high': float(ts[date_key]['2. high']),
                        'low': float(ts[date_key]['3. low']),
                        'close': float(ts[date_key]['4. close']),
                        'volume': int(ts[date_key]['5. volume'])
                    }
        except Exception as e:
            print(f"Error {ticker}: {e}")
        
        return None
    
    def get_company_info(self, ticker: str) -> Dict:
        """기업 정보"""
        url = "https://finnhub.io/api/v1/stock/profile2"
        params = {
            'symbol': ticker,
            'token': self.finnhub_key
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            return {
                'company': data.get('name', ticker),
                'sector': data.get('finnhubIndustry', 'Unknown'),
                'market_cap': data.get('marketCapitalization', 0)
            }
        except Exception as e:
            print(f"Error {ticker}: {e}")
            return {'company': ticker, 'sector': 'Unknown', 'market_cap': 0}
    
    def get_news(self, ticker: str, hours: int = 24) -> List[Dict]:
        """최신 뉴스"""
        url = "https://finnhub.io/api/v1/company-news"
        from_date = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d')
        
        params = {
            'symbol': ticker,
            'from': from_date,
            'to': datetime.now().strftime('%Y-%m-%d'),
            'token': self.finnhub_key
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            return [
                {
                    'headline': item['headline'],
                    'source': item['source']
                }
                for item in data[:3]
            ]
        except Exception as e:
            print(f"News error {ticker}: {e}")
            return []
    
    def get_moving_averages(self, ticker: str) -> Dict:
        """이동평균선"""
        url = "https://www.alphavantage.co/query"
        
        try:
            # MA20
            params = {
                'function': 'SMA',
                'symbol': ticker,
                'interval': 'daily',
                'time_period': 20,
                'series_type': 'close',
                'apikey': self.alpha_vantage_key
            }
            resp = requests.get(url, params=params, timeout=10)
            ma20_data = resp.json()
            ma20 = 0
            
            if 'Technical Analysis: SMA' in ma20_data:
                ma20 = float(
                    list(ma20_data['Technical Analysis: SMA'].values())[0]['SMA']
                )
            
            # MA60
            params['time_period'] = 60
            resp = requests.get(url, params=params, timeout=10)
            ma60_data = resp.json()
            ma60 = 0
            
            if 'Technical Analysis: SMA' in ma60_data:
                ma60 = float(
                    list(ma60_data['Technical Analysis: SMA'].values())[0]['SMA']
                )
            
            return {'ma20': ma20, 'ma60': ma60}
        except Exception as e:
            print(f"MA error {ticker}: {e}")
            return {'ma20': 0, 'ma60': 0}
    
    def get_monthly_high(self, ticker: str) -> float:
        """월간 고점"""
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'TIME_SERIES_MONTHLY',
            'symbol': ticker,
            'apikey': self.alpha_vantage_key
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if 'Monthly Time Series' in data:
                ts = data['Monthly Time Series']
                highs = [float(v['2. high']) for v in ts.values()]
                return max(highs) if highs else 0
        except Exception as e:
            print(f"Monthly high error {ticker}: {e}")
        
        return 0
