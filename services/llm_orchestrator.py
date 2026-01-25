# services/llm_orchestrator.py
import os
import google.generativeai as genai

class LLMOrchestrator:
    def __init__(self):
        self.key = os.getenv('GOOGLE_API_KEY')
        if self.key:
            genai.configure(api_key=self.key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")

    def synthesize(self, symbol, scores, weighted_score):
        if not self.key: return {"signal": "TYPE C", "reasoning": "No AI Key"}
        
        # Token Efficient Prompt
        prompt = f"""
        ROLE: Crypto CIO.
        DATA: {symbol} Score {weighted_score}/100.
        Details: Tech {scores['technical']}, OnChain {scores['onchain']}, Sent {scores['sentiment']}, Macro {scores['macro']}, Inst {scores['institutional']}.
        
        TASK: JSON {{ "signal": "TYPE A/B/C", "reasoning": "Korean 1-liner decision" }}
        RULES: A(>80, Strong), B(>60, Buy), C(Wait). Focus on volatility & Volume.
        """
        
        try:
            res = self.model.generate_content(prompt)
            import json
            # Heuristic to find JSON
            txt = res.text
            s = txt.find('{')
            e = txt.rfind('}')
            if s!=-1 and e!=-1:
                return json.loads(txt[s:e+1])
        except: pass
        
        return {"signal": "TYPE C", "reasoning": "AI Parsing Error"}
