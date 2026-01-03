#!/usr/bin/env python3
"""Macro Market Analyzer with Gemini AI"""
import os, json, requests, logging
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MacroDataCollector:
    def __init__(self):
        self.tickers = {
            'VIX': '^VIX', 'DXY': 'DX-Y.NYB', '10Y_Yield': '^TNX',
            'GOLD': 'GC=F', 'OIL': 'CL=F', 'BTC': 'BTC-USD', 'SPY': 'SPY', 'QQQ': 'QQQ'
        }
    
    def get_data(self):
        logger.info("Fetching macro data...")
        data = {}
        try:
            tickers = list(self.tickers.values())
            df = yf.download(tickers, period='5d', progress=False)
            for name, ticker in self.tickers.items():
                try:
                    if ticker not in df['Close'].columns: continue
                    hist = df['Close'][ticker].dropna()
                    if len(hist) < 2: continue
                    val, prev = hist.iloc[-1], hist.iloc[-2]
                    data[name] = {'value': round(val, 2), 'change_1d': round(((val/prev)-1)*100, 2)}
                except: pass
        except Exception as e:
            logger.error(f"Error: {e}")
        return data

class MacroAIAnalyzer:
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    
    def analyze(self, data, lang='ko'):
        if not self.api_key: return "API Key Missing"
        
        metrics = "\n".join([f"- {k}: {v['value']} ({v['change_1d']:+.1f}%)" for k,v in data.items()])
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        system_instruction = f"""
        Role: **Scientific Market Historian & Quantitative Strategist**
        Current Date: {current_date}
        
        [Principle: The "Genius Questioning" Protocol]
        1. **Data-Driven Grounding:** You must cite the provided exact numbers (VIX, Yields, etc.) as evidence. Do NOT vague assertions.
        2. **Fractal Verification:** When comparing to history (e.g., 2008, 1970s), you must prove the similarity mathematically based on the provided changes. If data does not match, reject the fractal.
        3. **Adversarial Thinking:** Ask yourself "Why might my view be wrong?" before concluding.
        """
        
        if lang == 'ko':
            # Korean Specific System Instruction with Genius Protocol
            system_instruction_ko = f"""
            역할: **과학적 시장 역사학자 및 퀀트 전략가**
            현재 날짜: {current_date}
            
            [원칙: "천재들의 질문법" 프로토콜]
            1. **데이터 기반 근거 (Data-Driven):** 모호한 주장 대신 반드시 제공된 정확한 수치(VIX, 국채금리 등)를 근거로 인용하십시오.
            2. **프랙탈 검증 (Fractal Verification):** 과거(2008년, 1970년대 등)와 비교할 때는 제공된 데이터 변화율에 기초하여 수학적/논리적 유사성을 증명하십시오. 데이터가 일치하지 않으면 과감히 기각(Reject)하십시오.
            3. **반대 심문 (Adversarial Thinking):** 결론을 내리기 전에 반드시 "내 분석이 틀렸다면 그 이유는 무엇인가?"를 자문하고 이를 명시하십시오.
            """
            
            prompt = f"""{system_instruction_ko}
            
            [제공된 실시간 데이터]
            {metrics}
            
            [분석 과제]
            1. **🔍 데이터 검증 (Data Audit):** VIX, 10년물 국채, 달러 인덱스 등 '현재 수치'가 의미하는 바를 직설적으로 해석하십시오. (예: VIX 13 이하는 안도감인가, 폭풍전야인가?)
            2. **📜 프랙탈 검증 (Fractal Verify):** "지표 패턴"에 기반하여 과거(1970s, 2000, 2022 등)와 가장 유사한 국면을 찾으십시오. 
               - *주의:* 단순히 느낌으로 비교하지 말고, "금리가 오르는데 나스닥이 오르는 현상" 등 구체적 상관관계로 증명하십시오. 유사한 과거가 없다면 없다고 말하십시오.
            3. **⚡ 유동성 및 핵심 변수:** 지금 시장이 상승/하락하는 단 하나의 'Money Flow' 원인은 무엇입니까? 유동성이 어디로 흐르고 있습니까?
            4. **🔮 결론 (Scenario):** 위 분석을 토대로 향후 1주~1개월 시장의 구체적 방향성(Strong Buy / Watch / Sell)을 제시하십시오.
            
            형식: 마크다운 리스트, 명확한 논거 필수. 답변은 100% 한국어로 작성하십시오.
            """
        else:
            prompt = f"""{system_instruction}
            
            [Real-time Data]
            {metrics}
            
            [Analysis Task]
            1. **Data Audit:** Interpret the exact numbers provided. What does the current VIX/Yield combination scream?
            2. **Fractal Verification:** Mathematically compare current correlations to historical regimes (1970s, 2000s). Prove the match using the provided data points.
            3. **Liquidity Driver:** Where is the money flowing? Identify the single most critical variable driving today's price action.
            4. **Verdict:** Provide a concrete 1-month forecast based on this evidence.
            
            Format: Markdown, strict evidence-based reasoning.
            """
        
        try:
            resp = requests.post(f"{self.url}?key={self.api_key}", 
                json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
            if resp.status_code == 200:
                return resp.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            logger.error(f"AI Req Error: {e}")
            pass
        return "AI Analysis failed."

class MultiModelAnalyzer:
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.collector = MacroDataCollector()
        self.gemini = MacroAIAnalyzer()
    
    def run(self):
        data = self.collector.get_data()
        analysis_ko = self.gemini.analyze(data, 'ko')
        analysis_en = self.gemini.analyze(data, 'en')
        
        output = {'timestamp': datetime.now().isoformat(), 'indicators': data, 'analysis_ko': analysis_ko, 'analysis_en': analysis_en}
        with open(os.path.join(self.data_dir, 'macro_analysis.json'), 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        logger.info("Saved macro analysis")
        return output

if __name__ == "__main__":
    MultiModelAnalyzer().run()
