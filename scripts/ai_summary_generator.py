#!/usr/bin/env python3
"""AI Stock Summary Generator using Gemini"""
import os, json, logging, time, requests
import pandas as pd
import yfinance as yf
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiGenerator:
    def __init__(self):
        self.key = os.getenv('GOOGLE_API_KEY')
        self.url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        
    def generate(self, ticker, data, lang='ko'):
        if not self.key: return "No API Key"
        score_info = f"Score: {data.get('composite_score')}/100, Grade: {data.get('grade')}"
        prompt = f"종목: {ticker}\n정보: {score_info}\n요청: 2-3문장 투자 의견." if lang == 'ko' else f"Stock: {ticker}\nInfo: {score_info}\nReq: 2-3 sentence opinion."
        try:
            resp = requests.post(f"{self.url}?key={self.key}", json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
            if resp.status_code == 200:
                return resp.json()['candidates'][0]['content']['parts'][0]['text']
        except: pass
        return "Analysis Failed"

class AIStockAnalyzer:
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.output_file = os.path.join(data_dir, 'ai_summaries.json') # Renamed output to output_file
        self.gen = GeminiGenerator()
        self.api_key = self.gen.key # Added api_key attribute
        self.url = self.gen.url # Added url attribute
        
    def load_portfolio(self):
        """Load portfolio from CSV"""
        csv_path = os.path.join(self.data_dir, 'us_portfolio.csv')
        if not os.path.exists(csv_path):
            return ['NVDA', 'AAPL', 'MSFT', 'TSLA'] # Fallback
        try:
            df = pd.read_csv(csv_path)
            df.columns = [c.strip() for c in df.columns]
            return df['Ticker'].tolist()
        except:
            return []

    def generate_summaries(self):
        tickers = self.load_portfolio()
        logger.info(f"Generating Advanced AI summaries for: {tickers}")
        
        # Load Corporate Intelligence (News & Earnings)
        news_data = {}
        try:
            with open(os.path.join(self.data_dir, 'news_events.json'), 'r') as f:
                news_json = json.load(f)
                # Index by ticker for faster lookup
                for n in news_json.get('news', []):
                    t = n['ticker']
                    if t not in news_data: news_data[t] = []
                    news_data[t].append(f"- {n['time']}: {n['title']}")
                
                earnings_map = {e['ticker']: e for e in news_json.get('earnings', [])}
        except:
            earnings_map = {}

        data = yf.download(tickers, period='1y', progress=False)['Close']
        if isinstance(data, pd.Series): data = data.to_frame()
        data = data.ffill().bfill()

        summaries = {}
        
        for ticker in tickers:
            try:
                # 1. Prepare Context Data
                if ticker not in data.columns: continue
                
                prices = data[ticker].dropna()
                current_price = prices.iloc[-1]
                chg_1m = ((current_price / prices.iloc[-20]) - 1) * 100
                
                # Earnings Context
                earn_info = earnings_map.get(ticker)
                earn_str = f"Earnings D-{earn_info['days_left']} ({earn_info['date']})" if earn_info else "Earnings date unknown"
                
                # News Context (Top 2 headlines)
                headlines = "\n".join(news_data.get(ticker, [])[:2])
                
                # 2. The Genius Prompt with Fractal & Validation
                prompt = f"""
                Role: World-Class Hedge Fund Manager & Technical Analyst (Elliott Wave & Fractal Expert).
                Target: {ticker} (Current: ${current_price:.2f}, 1M Chg: {chg_1m:.1f}%)
                Catalyst: {earn_str}
                Recent News:
                {headlines}

                [The Genius Questioning Process]
                1. **Fractal Verification:** Does the current price action resemble any historical crash or rally patterns (e.g., 2000 Dot-com, 2008 Crisis, or 2020 Covid Rebound)?
                2. **Catalyst Check:** How will the upcoming earnings ({earn_str}) impact the price based on recent sentiment?
                3. **Price Prediction:** Based on Volatility (ATR) and Fractals, what is the expected price range for the next week?

                [Output Requirement - Korean]
                Provide a structured analysis in Korean Markdown:
                - **🤖 AI 투자의견:** (Strong Buy / Buy / Hold / Sell) - Bold text
                - **📉 프랙탈 관점:** (과거 유사 패턴과 현재 위치 비교 분석)
                - **📰 뉴스/실적 검증:** (뉴스와 실적이 주가에 미칠 구체적 영향)
                - **💰 예상 주가 밴드:** (다음주 예상 최저가 ~ 최고가 제시)
                
                Keep it sharp, professional, and under 300 characters total.
                """
                
                # Generate
                resp = requests.post(
                    f"{self.url}?key={self.api_key}", 
                    json={"contents": [{"parts": [{"text": prompt}]}]}, 
                    timeout=30
                )
                
                if resp.status_code == 200:
                    analysis = resp.json()['candidates'][0]['content']['parts'][0]['text']
                    summaries[ticker] = analysis
                else:
                    summaries[ticker] = "AI Analysis unavailable."
                    
            except Exception as e:
                logger.error(f"Error for {ticker}: {e}")
                summaries[ticker] = "Analysis failed."

        # Save result
        with open(self.output_file, 'w') as f:
            json.dump(summaries, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved AI summaries to {self.output_file}")

if __name__ == "__main__":
    AIStockAnalyzer().generate_summaries()
