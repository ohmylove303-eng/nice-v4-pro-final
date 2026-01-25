# services/signal_agents.py
import math

class MathLib:
    @staticmethod
    def sma(data, window):
        if len(data) < window: return 0
        return sum(data[-window:]) / window

    @staticmethod
    def std(data, window):
        if len(data) < window: return 0
        avg = sum(data[-window:]) / window
        var = sum((x - avg) ** 2 for x in data[-window:]) / window
        return math.sqrt(var)

    @staticmethod
    def ema(data, window):
        if len(data) < window: return 0
        alpha = 2 / (window + 1)
        ema = data[0]
        for p in data[1:]:
            ema = (p * alpha) + (ema * (1 - alpha))
        return ema

    @staticmethod
    def rsi(prices, window=14):
        if len(prices) < window + 1: return 50
        deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[-window:]) / window
        avg_loss = sum(losses[-window:]) / window # Simple avg for approximation

        if avg_loss == 0: return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

class TechnicalAgent:
    def __init__(self): self.name = "Technical"
    def analyze(self, candles):
        # candles: list of {close, open, high, low, volume}
        closes = [c['close'] for c in candles]
        
        # RSI
        current_rsi = MathLib.rsi(closes)
        
        # BB
        ma20 = MathLib.sma(closes, 20)
        std = MathLib.std(closes, 20)
        upper = ma20 + (std * 2)
        lower = ma20 - (std * 2)
        curr_price = closes[-1]
        
        # MACD (Approximated simple logic for now vs heavy calc)
        ema12 = MathLib.ema(closes, 12)
        ema26 = MathLib.ema(closes, 26)
        macd = ema12 - ema26
        
        score = 50
        if current_rsi < 30: score += 20
        elif current_rsi > 70: score -= 20
        
        if curr_price < lower: score += 15
        elif curr_price > upper: score -= 15
        
        return {"score": int(max(0, min(100, score))), "details": f"RSI:{current_rsi:.1f}"}

class OnChainAgent:
    def __init__(self): self.name = "OnChain"
    def analyze(self, candles):
        vols = [c['volume'] for c in candles]
        closes = [c['close'] for c in candles]
        
        avg_vol = MathLib.sma(vols, 20)
        curr_vol = vols[-1]
        vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0
        
        score = 50
        if vol_ratio > 2.0: score += 20
        return {"score": score, "details": f"Vol Ratio: {vol_ratio:.1f}x"}

class SentimentAgent:
    def __init__(self): self.name = "Sentiment"
    def analyze(self, candles):
        closes = [c['close'] for c in candles]
        if len(closes) < 5: return {"score": 50, "details": "No Data"}
        ret = ((closes[-1] - closes[-5]) / closes[-5]) * 100
        return {"score": int(50 + ret), "details": f"Mom(5D): {ret:.1f}%"}

class MacroAgent:
    def analyze(self, candles):
        return {"score": 60, "details": "Stable"}

class InstitutionalAgent:
    def analyze(self, candles):
        closes = [c['close'] for c in candles]
        ma50 = MathLib.sma(closes, 50)
        ma20 = MathLib.sma(closes, 20)
        score = 70 if ma20 > ma50 else 30
        return {"score": score, "details": "Trend"}

class SignalAggregator:
    def __init__(self):
        self.agents = [TechnicalAgent(), OnChainAgent(), SentimentAgent(), MacroAgent(), InstitutionalAgent()]
    
    def get_all_signals(self, candles):
        scores = {}
        total = 0
        for agent in self.agents:
            res = agent.analyze(candles)
            scores[agent.name] = res['score']
            total += res['score']
            
        avg = total / 5
        return {"agent_scores": scores, "weighted_score": int(avg), "confidence": 85}
