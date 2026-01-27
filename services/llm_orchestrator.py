# services/llm_orchestrator.py
import os
import google.generativeai as genai

class LLMOrchestrator:
    def __init__(self):
        # Support both naming conventions
        self.server_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if self.server_key:
            genai.configure(api_key=self.server_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.model = None

    def synthesize(self, symbol, scores, weighted_score, override_key=None):
        # Determine which key to use
        active_key = override_key or self.server_key
        
        if not active_key: 
            return {"signal": "TYPE C", "reasoning": "No API Key Provided (Server or Client)"}
            
        # Re-configure for this request if needed (or just ensure it's set)
        try:
            genai.configure(api_key=active_key)
            if not self.model: self.model = genai.GenerativeModel("gemini-1.5-flash")
        except Exception as e:
            return {"signal": "TYPE C", "reasoning": f"Key Config Error: {str(e)}"}
        
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
        except Exception as e:
            return {"signal": "TYPE C", "reasoning": f"ERR: {str(e)}"}
        
        return {"signal": "TYPE C", "reasoning": "AI Parsing Error (No JSON)"}
