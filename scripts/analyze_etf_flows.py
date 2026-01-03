#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
US ETF Fund Flow Analysis
Tracks money flows in major ETFs and generates AI insights using Gemini
"""

import os
import json
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ETFFlowAnalyzer:
    """Analyze ETF fund flows to detect institutional money movement"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.output_csv = os.path.join(data_dir, 'us_etf_flows.csv')
        self.output_json = os.path.join(data_dir, 'etf_flow_analysis.json')
        
        # Major ETFs to track
        self.etf_universe = {
            # Market Index ETFs
            'SPY': {'name': 'S&P 500 ETF', 'category': 'Index'},
            'QQQ': {'name': 'Nasdaq 100 ETF', 'category': 'Index'},
            'IWM': {'name': 'Russell 2000 ETF', 'category': 'Index'},
            'DIA': {'name': 'Dow Jones ETF', 'category': 'Index'},
            
            # Sector ETFs
            'XLK': {'name': 'Technology Select', 'category': 'Sector'},
            'XLF': {'name': 'Financial Select', 'category': 'Sector'},
            'XLV': {'name': 'Healthcare Select', 'category': 'Sector'},
            'XLE': {'name': 'Energy Select', 'category': 'Sector'},
            'XLY': {'name': 'Consumer Discretionary', 'category': 'Sector'},
            'XLP': {'name': 'Consumer Staples', 'category': 'Sector'},
            'XLI': {'name': 'Industrial Select', 'category': 'Sector'},
            'XLB': {'name': 'Materials Select', 'category': 'Sector'},
            'XLU': {'name': 'Utilities Select', 'category': 'Sector'},
            'XLRE': {'name': 'Real Estate Select', 'category': 'Sector'},
            'XLC': {'name': 'Communication Services', 'category': 'Sector'},
            
            # Thematic ETFs
            'ARKK': {'name': 'ARK Innovation', 'category': 'Thematic'},
            'SOXX': {'name': 'Semiconductor ETF', 'category': 'Thematic'},
            'SMH': {'name': 'VanEck Semiconductor', 'category': 'Thematic'},
            
            # Commodity ETFs
            'GLD': {'name': 'Gold ETF', 'category': 'Commodity'},
            'SLV': {'name': 'Silver ETF', 'category': 'Commodity'},
            'USO': {'name': 'Oil ETF', 'category': 'Commodity'},
            
            # Bond ETFs
            'TLT': {'name': '20+ Year Treasury', 'category': 'Bond'},
            'HYG': {'name': 'High Yield Corporate', 'category': 'Bond'},
            'LQD': {'name': 'Investment Grade Corp', 'category': 'Bond'},
        }
        
        # Gemini API config
        self.gemini_api_key = os.getenv('GOOGLE_API_KEY')
        self.gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    
    def calculate_flow_proxy(self, df: pd.DataFrame) -> Dict:
        """
        Calculate fund flow proxy using price and volume data
        Since actual flow data requires premium APIs, we use volume-based proxies
        """
        if len(df) < 20:
            return None
        
        df = df.sort_values('Date').reset_index(drop=True)
        
        # Calculate OBV (On-Balance Volume)
        obv = [0]
        for i in range(1, len(df)):
            if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
                obv.append(obv[-1] + df['Volume'].iloc[i])
            elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
                obv.append(obv[-1] - df['Volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        df['OBV'] = obv
        
        # Recent vs previous period comparison
        latest_price = df['Close'].iloc[-1]
        prev_20d_price = df['Close'].iloc[-21] if len(df) > 21 else df['Close'].iloc[0]
        price_change = ((latest_price / prev_20d_price) - 1) * 100
        
        # Volume trend
        vol_5d = df['Volume'].tail(5).mean()
        vol_20d = df['Volume'].tail(20).mean()
        vol_ratio = vol_5d / vol_20d if vol_20d > 0 else 1
        
        # OBV trend
        obv_change = df['OBV'].iloc[-1] - df['OBV'].iloc[-20] if len(df) >= 20 else 0
        obv_direction = "Inflow" if obv_change > 0 else "Outflow"
        
        # Calculate flow score (0-100)
        score = 50
        
        # Price momentum contribution
        if price_change > 5:
            score += 15
        elif price_change > 2:
            score += 10
        elif price_change < -5:
            score -= 15
        elif price_change < -2:
            score -= 10
        
        # Volume trend contribution
        if vol_ratio > 1.5 and price_change > 0:
            score += 15  # High volume with positive price = strong inflow
        elif vol_ratio > 1.2 and price_change > 0:
            score += 10
        elif vol_ratio > 1.5 and price_change < 0:
            score -= 15  # High volume with negative price = strong outflow
        
        # OBV contribution
        if obv_direction == "Inflow":
            score += 10
        else:
            score -= 10
        
        score = max(0, min(100, score))
        
        # Determine flow stage
        if score >= 70:
            stage = "Strong Inflow"
        elif score >= 55:
            stage = "Inflow"
        elif score >= 45:
            stage = "Neutral"
        elif score >= 30:
            stage = "Outflow"
        else:
            stage = "Strong Outflow"
        
        return {
            'current_price': round(latest_price, 2),
            'price_change_20d': round(price_change, 2),
            'volume_ratio': round(vol_ratio, 2),
            'obv_direction': obv_direction,
            'flow_score': round(score, 1),
            'flow_stage': stage
        }
    
    def analyze_all_etfs(self) -> pd.DataFrame:
        """Analyze all ETFs in the universe"""
        logger.info("🚀 Starting ETF Flow Analysis...")
        
        results = []
        
        for ticker, info in tqdm(self.etf_universe.items(), desc="Analyzing ETFs"):
            try:
                etf = yf.Ticker(ticker)
                hist = etf.history(period="3mo")
                
                if hist.empty:
                    continue
                
                hist = hist.reset_index()
                flow_data = self.calculate_flow_proxy(hist)
                
                if flow_data:
                    results.append({
                        'ticker': ticker,
                        'name': info['name'],
                        'category': info['category'],
                        **flow_data
                    })
                    
            except Exception as e:
                logger.debug(f"Error analyzing {ticker}: {e}")
                continue
        
        return pd.DataFrame(results)
    
    def generate_ai_analysis(self, results_df: pd.DataFrame) -> str:
        """Generate AI analysis of ETF flows using Gemini"""
        if not self.gemini_api_key:
            return "API Key not configured. Set GOOGLE_API_KEY in .env file."
        
        # Prepare summary for AI
        inflows = results_df[results_df['flow_stage'].str.contains('Inflow')].nlargest(5, 'flow_score')
        outflows = results_df[results_df['flow_stage'].str.contains('Outflow')].nsmallest(5, 'flow_score')
        
        inflow_summary = "\n".join([
            f"- {row['ticker']} ({row['name']}): Score {row['flow_score']}, Price Δ {row['price_change_20d']}%"
            for _, row in inflows.iterrows()
        ])
        
        outflow_summary = "\n".join([
            f"- {row['ticker']} ({row['name']}): Score {row['flow_score']}, Price Δ {row['price_change_20d']}%"
            for _, row in outflows.iterrows()
        ])
        
        prompt = f"""당신은 미국 주식시장 전문 애널리스트입니다.
        
다음 ETF 자금 흐름 데이터를 분석하고 투자 인사이트를 제공하세요:

**자금 유입 상위 ETF:**
{inflow_summary}

**자금 유출 상위 ETF:**
{outflow_summary}

다음 형식으로 답변하세요 (3-4문장):
1. 현재 시장 자금 흐름 트렌드
2. 유망 섹터/자산군
3. 주의해야 할 섹터
4. 단기 투자 전략 제안

이모지는 사용하지 마세요."""

        try:
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 500}
            }
            
            response = requests.post(
                f"{self.gemini_url}?key={self.gemini_api_key}",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                return f"API Error: {response.status_code}"
                
        except Exception as e:
            return f"Analysis generation failed: {e}"
    
    def run(self) -> Dict:
        """Run complete ETF flow analysis"""
        # Analyze all ETFs
        results_df = self.analyze_all_etfs()
        
        if results_df.empty:
            logger.warning("No ETF data collected")
            return {}
        
        # Save CSV
        results_df.to_csv(self.output_csv, index=False)
        logger.info(f"✅ Saved ETF data to {self.output_csv}")
        
        # Generate AI analysis
        ai_insight = self.generate_ai_analysis(results_df)
        
        # Prepare summary output
        output = {
            'timestamp': datetime.now().isoformat(),
            'etf_count': len(results_df),
            'summary': {
                'strong_inflow': results_df[results_df['flow_stage'] == 'Strong Inflow']['ticker'].tolist(),
                'inflow': results_df[results_df['flow_stage'] == 'Inflow']['ticker'].tolist(),
                'outflow': results_df[results_df['flow_stage'] == 'Outflow']['ticker'].tolist(),
                'strong_outflow': results_df[results_df['flow_stage'] == 'Strong Outflow']['ticker'].tolist(),
            },
            'top_inflows': results_df.nlargest(5, 'flow_score')[['ticker', 'name', 'flow_score', 'price_change_20d']].to_dict('records'),
            'top_outflows': results_df.nsmallest(5, 'flow_score')[['ticker', 'name', 'flow_score', 'price_change_20d']].to_dict('records'),
            'ai_analysis': ai_insight
        }
        
        # Save JSON
        with open(self.output_json, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Saved analysis to {self.output_json}")
        
        # Print summary
        logger.info("\n📊 ETF Flow Summary:")
        logger.info(f"   Strong Inflow: {len(output['summary']['strong_inflow'])} ETFs")
        logger.info(f"   Inflow: {len(output['summary']['inflow'])} ETFs")
        logger.info(f"   Outflow: {len(output['summary']['outflow'])} ETFs")
        logger.info(f"   Strong Outflow: {len(output['summary']['strong_outflow'])} ETFs")
        
        return output


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ETF Fund Flow Analysis')
    parser.add_argument('--dir', default=None, help='Data directory')
    args = parser.parse_args()
    
    analyzer = ETFFlowAnalyzer(data_dir=args.dir)
    result = analyzer.run()
    
    if result:
        print("\n🔥 Top 5 Inflow ETFs:")
        for etf in result.get('top_inflows', []):
            print(f"   {etf['ticker']} ({etf['name']}): Score {etf['flow_score']}")
        
        print("\n❄️ Top 5 Outflow ETFs:")
        for etf in result.get('top_outflows', []):
            print(f"   {etf['ticker']} ({etf['name']}): Score {etf['flow_score']}")
        
        print("\n🤖 AI Analysis:")
        print(result.get('ai_analysis', 'N/A'))


if __name__ == "__main__":
    main()
