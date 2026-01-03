#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sector Performance Heatmap Data Collector
"""

import os
import json
import pandas as pd
import yfinance as yf
from datetime import datetime
from typing import Dict, List
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SectorHeatmapCollector:
    """Collect sector ETF performance data for heatmap visualization"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Sector ETFs with full names
        self.sector_etfs = {
            'XLK': {'name': 'Technology', 'color': '#4A90A4'},
            'XLF': {'name': 'Financials', 'color': '#6B8E23'},
            'XLV': {'name': 'Healthcare', 'color': '#FF69B4'},
            'XLE': {'name': 'Energy', 'color': '#FF6347'},
            'XLY': {'name': 'Consumer Disc.', 'color': '#FFD700'},
            'XLP': {'name': 'Consumer Staples', 'color': '#98D8C8'},
            'XLI': {'name': 'Industrials', 'color': '#DDA0DD'},
            'XLB': {'name': 'Materials', 'color': '#F0E68C'},
            'XLU': {'name': 'Utilities', 'color': '#87CEEB'},
            'XLRE': {'name': 'Real Estate', 'color': '#CD853F'},
            'XLC': {'name': 'Comm. Services', 'color': '#9370DB'},
        }
        
        # Sector stocks for detail map
        self.sector_stocks = {
            'Technology': ['AAPL', 'MSFT', 'NVDA', 'AVGO', 'ORCL', 'CRM', 'AMD', 'ADBE'],
            'Financials': ['BRK-B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS'],
            'Healthcare': ['UNH', 'JNJ', 'LLY', 'PFE', 'ABBV', 'MRK', 'TMO', 'ABT'],
            'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO'],
            'Consumer Disc.': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'TJX', 'LOW'],
            'Consumer Staples': ['PG', 'KO', 'PEP', 'COST', 'WMT', 'PM', 'MO', 'CL'],
            'Industrials': ['CAT', 'BA', 'HON', 'UNP', 'RTX', 'DE', 'GE', 'MMM'],
            'Materials': ['LIN', 'APD', 'SHW', 'FCX', 'NEM', 'NUE', 'DOW', 'DD'],
            'Utilities': ['NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'XEL'],
            'Real Estate': ['AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'SPG', 'O', 'WELL'],
            'Comm. Services': ['META', 'GOOGL', 'NFLX', 'DIS', 'CMCSA', 'T', 'VZ', 'CHTR'],
        }
    
    def get_sector_etf_performance(self, period: str = '5d') -> Dict:
        """Get sector ETF performance data"""
        logger.info(f"📊 Fetching sector ETF data ({period})...")
        
        tickers = list(self.sector_etfs.keys())
        
        try:
            data = yf.download(tickers, period=period, progress=False)
            
            if data.empty:
                return {'error': 'No data'}
            
            results = []
            
            for ticker, info in self.sector_etfs.items():
                try:
                    if ticker not in data['Close'].columns:
                        continue
                    
                    prices = data['Close'][ticker].dropna()
                    if len(prices) < 2:
                        continue
                    
                    current = prices.iloc[-1]
                    prev = prices.iloc[-2]
                    first = prices.iloc[0]
                    
                    change_1d = ((current / prev) - 1) * 100
                    change_period = ((current / first) - 1) * 100
                    
                    results.append({
                        'ticker': ticker,
                        'name': info['name'],
                        'color': info['color'],
                        'price': round(current, 2),
                        'change_1d': round(change_1d, 2),
                        'change_period': round(change_period, 2)
                    })
                except Exception as e:
                    logger.debug(f"Error processing {ticker}: {e}")
                    continue
            
            # Sort by change
            results.sort(key=lambda x: x['change_1d'], reverse=True)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'period': period,
                'sectors': results
            }
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return {'error': str(e)}
    
    def get_full_market_map(self, period: str = '5d') -> Dict:
        """Get full market map data (Sectors -> Stocks) for Treemap"""
        logger.info(f"📊 Fetching full market map data ({period})...")
        
        all_tickers = []
        ticker_to_sector = {}
        for sector, stocks in self.sector_stocks.items():
            all_tickers.extend(stocks)
            for stock in stocks:
                ticker_to_sector[stock] = sector
                
        try:
            data = yf.download(all_tickers, period=period, progress=False)
            
            if data.empty:
                return {'error': 'No data'}
            
            market_map = {name: [] for name in self.sector_stocks.keys()}
            
            for ticker in all_tickers:
                try:
                    if ticker not in data['Close'].columns:
                        continue
                    prices = data['Close'][ticker].dropna()
                    if len(prices) < 2:
                        continue
                    
                    current = prices.iloc[-1]
                    prev = prices.iloc[-2]
                    change = ((current / prev) - 1) * 100
                    
                    # Weight by Volume * Price (Activity proxy)
                    vol = data['Volume'][ticker].iloc[-1] if 'Volume' in data.columns else 100000
                    weight = current * vol
                    
                    sector = ticker_to_sector.get(ticker, 'Unknown')
                    if sector in market_map:
                        market_map[sector].append({
                            'x': ticker,
                            'y': round(weight, 0),
                            'price': round(current, 2),
                            'change': round(change, 2),
                            'color': self._get_color(change)
                        })
                except:
                    pass
            
            series = []
            for sector_name, stocks in market_map.items():
                if stocks:
                    stocks.sort(key=lambda x: x['y'], reverse=True)
                    series.append({'name': sector_name, 'data': stocks})
            
            series.sort(key=lambda s: sum(i['y'] for i in s['data']), reverse=True)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'period': period,
                'series': series
            }
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return {'error': str(e)}
            
    def _get_color(self, change: float) -> str:
        if change >= 3:
            return '#00C853'
        elif change >= 1:
            return '#4CAF50'
        elif change >= 0:
            return '#81C784'
        elif change >= -1:
            return '#EF9A9A'
        elif change >= -3:
            return '#F44336'
        else:
            return '#B71C1C'

    def save_data(self, output_dir: str = None):
        if output_dir is None:
            output_dir = self.data_dir
            
        # Sector ETF Performance
        etf_data = self.get_sector_etf_performance('5d')
        etf_file = os.path.join(output_dir, 'sector_heatmap.json')
        with open(etf_file, 'w', encoding='utf-8') as f:
            json.dump(etf_data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Saved sector ETF data to {etf_file}")
        
        # Full Market Map
        map_data = self.get_full_market_map('5d')
        map_file = os.path.join(output_dir, 'market_treemap.json')
        with open(map_file, 'w', encoding='utf-8') as f:
            json.dump(map_data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Saved market map to {map_file}")
        
        return etf_data, map_data


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', default=None)
    args = parser.parse_args()
    
    collector = SectorHeatmapCollector(data_dir=args.dir)
    etf_data, map_data = collector.save_data()
    
    if 'sectors' in etf_data:
        print("\n📊 Sector Performance (1D Change):")
        for sector in etf_data['sectors']:
            emoji = "📈" if sector['change_1d'] > 0 else "📉"
            print(f"   {emoji} {sector['name']}: {sector['change_1d']:+.2f}%")


if __name__ == "__main__":
    main()
