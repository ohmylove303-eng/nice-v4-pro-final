# services/signal_agents.py
import numpy as np
from typing import Dict
import pandas as pd

# ============================================================================
# DEEP LOGIC AGENTS (Real Math, No Mocks, DataFrame Injected)
# ============================================================================

class TechnicalAgent:
    def __init__(self):
        self.name = "Technical"
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        # 1. RSI (14)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # 2. Bollinger Bands (20, 2)
        ma20 = df['close'].rolling(20).mean()
        std = df['close'].rolling(20).std()
        upper = ma20 + (std * 2)
        lower = ma20 - (std * 2)
        middle = ma20
        curr_price = df['close'].iloc[-1]
        
        # 3. MACD (12, 26, 9)
        k = df['close'].ewm(span=12, adjust=False).mean()
        d = df['close'].ewm(span=26, adjust=False).mean()
        macd = k - d
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal
        
        # Scoring Logic (Weighted Mix)
        score = 50
        
        # RSI (+- 20)
        if current_rsi < 30: score += 20     # Oversold
        elif current_rsi > 70: score -= 20   # Overbought
        
        # MACD (+- 15)
        if hist.iloc[-1] > 0 and hist.iloc[-1] > hist.iloc[-2]: score += 15 # Growing Bullish
        elif hist.iloc[-1] < 0 and hist.iloc[-1] < hist.iloc[-2]: score -= 15 # Growing Bearish
        
        # BB (+- 15)
        if curr_price < lower.iloc[-1]: score += 15 # Bounce play
        elif curr_price > upper.iloc[-1]: score -= 15 # Resistance
        
        # Trend Alignment (EMA)
        if curr_price > middle.iloc[-1]: score += 5
        
        final_score = int(max(0, min(100, score)))
        
        return {
            "score": final_score,
            "details": f"RSI:{current_rsi:.1f} MACD:{hist.iloc[-1]:.2f} BB:{(curr_price-lower.iloc[-1])/(upper.iloc[-1]-lower.iloc[-1]):.2f}"
        }

class OnChainAgent:
    def __init__(self):
        self.name = "OnChain"
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        # Volume & Volatility Analysis
        vol = df['volume']
        avg_vol = vol.rolling(20).mean().iloc[-1]
        curr_vol = vol.iloc[-1]
        vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0
        
        # Price Action Context
        price_chg = df['close'].pct_change().iloc[-1]
        
        score = 50
        # Volume Surge Rule
        if vol_ratio > 2.0:
            if price_chg > 0: score += 30 # Strong Buy Volume
            else: score -= 30 # Panic Sell Volume
        elif vol_ratio > 1.5:
             if price_chg > 0: score += 10
             else: score -= 10
             
        return {
            "score": int(max(0, min(100, score))),
            "details": f"Vol Ratio: {vol_ratio:.1f}x"
        }

class SentimentAgent:
    def __init__(self):
        self.name = "Sentiment"
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        # Momentum Proxy (5-day return)
        ret_5d = df['close'].pct_change(5).iloc[-1] * 100
        score = 50 + (ret_5d * 2) 
        return {
            "score": int(max(0, min(100, score))), 
            "details": f"Mom(5D): {ret_5d:.1f}%"
        }

class MacroAgent:
    def analyze(self, df: pd.DataFrame) -> Dict:
        # Intraday Volatility Proxy for Fear
        high_low = (df['high'] - df['low']) / df['low']
        avg_volat = high_low.rolling(10).mean().iloc[-1] * 100
        curr_volat = high_low.iloc[-1] * 100
        
        score = 50
        if curr_volat > avg_volat * 1.5: score = 30 # High Fear/Uncertainty
        else: score = 60 # Stable
        
        return {"score": score, "details": f"Volat: {curr_volat:.2f}%"}

class InstitutionalAgent:
    def analyze(self, df: pd.DataFrame) -> Dict:
        # Golden Cross / Death Cross Check
        ma50 = df['close'].rolling(50).mean().iloc[-1]
        ma200 = df['close'].rolling(200).mean().iloc[-1] # Might be NaN if history short
        
        # If not enough data, use shorter MAs
        if pd.isna(ma200):
            ma50 = df['close'].rolling(20).mean().iloc[-1]
            ma200 = df['close'].rolling(60).mean().iloc[-1]
            
        score = 50
        if ma50 > ma200: score = 70 # Golden Cross Zone
        else: score = 30 # Death Cross Zone
        
        return {"score": score, "details": "Bullish Structure" if score > 50 else "Bearish Structure"}

class SignalAggregator:
    def __init__(self):
        self.agents = {
            "technical": TechnicalAgent(),
            "onchain": OnChainAgent(),
            "sentiment": SentimentAgent(),
            "macro": MacroAgent(),
            "institutional": InstitutionalAgent()
        }
    
    def get_all_signals(self, df: pd.DataFrame) -> Dict:
        scores = {}
        for name, agent in self.agents.items():
            res = agent.analyze(df)
            scores[name] = res["score"]
            
        avg = sum(scores.values()) / 5
        
        # Confidence based on Consensus (Variance)
        variance = np.var(list(scores.values()))
        confidence = max(0, min(100, 100 - variance))
        
        return {
            "agent_scores": scores,
            "weighted_score": int(avg),
            "confidence": int(confidence)
        }
