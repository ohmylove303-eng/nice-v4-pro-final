#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Options Flow Analyzer
Tracks options volume and unusual activity for major stocks
"""

import os
import json
import logging
import yfinance as yf
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OptionsFlowAnalyzer:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.output_file = os.path.join(data_dir, 'options_flow.json')
        
        # Major stocks to track options
        self.watchlist = [
            'AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN', 'META', 'GOOGL', 
            'SPY', 'QQQ', 'AMD', 'NFLX', 'BA', 'DIS', 'JPM', 'GS'
        ]
    
    def get_options_summary(self, ticker: str) -> Dict:
        """Get options summary for a single ticker"""
        try:
            stock = yf.Ticker(ticker)
            exps = stock.options
            
            if not exps:
                return {'ticker': ticker, 'error': 'No options available'}
            
            # Get nearest expiration
            opt = stock.option_chain(exps[0])
            calls, puts = opt.calls, opt.puts
            
            # Volume metrics
            call_vol = calls['volume'].sum() if 'volume' in calls.columns else 0
            put_vol = puts['volume'].sum() if 'volume' in puts.columns else 0
            call_oi = calls['openInterest'].sum() if 'openInterest' in calls.columns else 0
            put_oi = puts['openInterest'].sum() if 'openInterest' in puts.columns else 0
            
            # Put/Call Ratio
            pc_ratio = put_vol / call_vol if call_vol > 0 else 0
            
            # Unusual activity detection (volume > 3x average)
            avg_call_vol = calls['volume'].mean() if 'volume' in calls.columns else 0
            avg_put_vol = puts['volume'].mean() if 'volume' in puts.columns else 0
            
            unusual_calls = len(calls[calls['volume'] > avg_call_vol * 3]) if avg_call_vol > 0 else 0
            unusual_puts = len(puts[puts['volume'] > avg_put_vol * 3]) if avg_put_vol > 0 else 0
            
            # Sentiment
            if pc_ratio < 0.7:
                sentiment = "Bullish"
            elif pc_ratio > 1.0:
                sentiment = "Bearish"
            else:
                sentiment = "Neutral"
            
            # Score calculation
            score = 50
            if pc_ratio < 0.5:
                score += 20
            elif pc_ratio < 0.7:
                score += 10
            elif pc_ratio > 1.5:
                score -= 20
            elif pc_ratio > 1.0:
                score -= 10
            
            if unusual_calls > unusual_puts:
                score += 10
            elif unusual_puts > unusual_calls:
                score -= 10
            
            score = max(0, min(100, score))
            
            # Get current price
            try:
                hist = stock.history(period='1d')
                current_price = round(float(hist['Close'].iloc[-1]), 2) if not hist.empty else 0
            except:
                current_price = 0

            # Implied Volatility (Average of ITM calls)
            try:
                # Filter for some liquidity
                liquid_calls = calls[calls['volume'] > 0]
                if not liquid_calls.empty:
                    avg_iv = liquid_calls['impliedVolatility'].mean() * 100
                else:
                    avg_iv = 0
            except:
                avg_iv = 0

            return {
                'ticker': ticker,
                'current_price': current_price,
                'signal': {
                    'sentiment': sentiment,
                    'sentiment_score': score
                },
                'metrics': {
                    'pc_volume_ratio': round(pc_ratio, 2),
                    'call_iv': round(avg_iv, 1),
                    'call_volume': int(call_vol),
                    'put_volume': int(put_vol),
                    'total_volume': int(call_vol + put_vol)
                },
                'expiration': exps[0],
                'unusual_activity': {
                    'unusual_calls': unusual_calls,
                    'unusual_puts': unusual_puts,
                    'has_unusual': unusual_calls > 0 or unusual_puts > 0
                }
            }
            
        except Exception as e:
            logger.debug(f"Error fetching options for {ticker}: {e}")
            return {'ticker': ticker, 'error': str(e)}

    def analyze_watchlist(self) -> Dict:
        """Analyze options for all stocks in watchlist"""
        logger.info("🔍 Analyzing options flow...")
        
        results = []
        bullish = []
        bearish = []
        unusual = []
        
        for ticker in self.watchlist:
            res = self.get_options_summary(ticker)
            
            if 'error' not in res:
                results.append(res)
                
                # Update path to sentiment
                sentiment = res.get('signal', {}).get('sentiment', 'Neutral')
                if sentiment == 'Bullish':
                    bullish.append(ticker)
                elif sentiment == 'Bearish':
                    bearish.append(ticker)
                
                if res['unusual_activity']['has_unusual']:
                    unusual.append({
                        'ticker': ticker,
                        'unusual_calls': res['unusual_activity']['unusual_calls'],
                        'unusual_puts': res['unusual_activity']['unusual_puts']
                    })
        
        # Sort by options score (descending)
        results.sort(key=lambda x: x.get('signal', {}).get('sentiment_score', 0), reverse=True)
        
        output = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_analyzed': len(results),
                'bullish_count': len(bullish),
                'bearish_count': len(bearish),
                'unusual_count': len(unusual)
            },
            'bullish_stocks': bullish,
            'bearish_stocks': bearish,
            'unusual_activity': unusual,
            'options_flow': results
        }
        
        # Save to file
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Saved options flow to {self.output_file}")
        
        return output


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', default=None)
    args = parser.parse_args()
    
    analyzer = OptionsFlowAnalyzer(data_dir=args.dir)
    result = analyzer.analyze_watchlist()
    
    print(f"\n📊 Options Flow Summary:")
    print(f"   Bullish: {result['summary']['bullish_count']} stocks")
    print(f"   Bearish: {result['summary']['bearish_count']} stocks")
    print(f"   Unusual Activity: {result['summary']['unusual_count']} stocks")
    
    if result['bullish_stocks']:
        print(f"\n📈 Bullish: {', '.join(result['bullish_stocks'])}")
    if result['bearish_stocks']:
        print(f"📉 Bearish: {', '.join(result['bearish_stocks'])}")
    if result['unusual_activity']:
        print(f"\n⚡ Unusual Activity:")
        for item in result['unusual_activity']:
            print(f"   {item['ticker']}: {item['unusual_calls']} calls, {item['unusual_puts']} puts")


if __name__ == "__main__":
    main()
