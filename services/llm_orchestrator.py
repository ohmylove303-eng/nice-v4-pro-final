# services/llm_orchestrator.py
import os
import google.generativeai as genai

class LLMOrchestrator:
    def __init__(self):
        api_key = os.getenv('GOOGLE_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.model = None

    def synthesize(self, symbol, agent_scores, weighted_score):
        if not self.model:
            return {"type": "Wait", "reasoning": "LLM Key Missing"}
            
        prompt = f"""
        ACT AS 'NICE PRO' CHIEF INVESTMENT OFFICER.
        
        [Analysis Target: {symbol}]
        
        [5-Agent Report]
        1. Technical: {agent_scores['technical']}/100
        2. OnChain: {agent_scores['onchain']}/100
        3. Sentiment: {agent_scores['sentiment']}/100
        4. Macro: {agent_scores['macro']}/100
        5. Institutional: {agent_scores['institutional']}/100
        
        [Aggregated Score]: {weighted_score}/100
        
        [Mission]
        Synthesize these 5 perspectives into a final decision.
        Return JSON Code Check: {{ "signal": "TYPE A/B/C", "reasoning": "Korean Summary" }}
        
        Rules:
        - TYPE A: Score > 80. Strong Buy.
        - TYPE B: Score > 60. Buy.
        - TYPE C: Wait/Watch.
        """
        
        try:
            res = self.model.generate_content(prompt)
            import json
            txt = res.text
            if "{" in txt:
                js = json.loads(txt[txt.find("{"):txt.rfind("}")+1])
                return js
        except:
            return {"signal": "TYPE C", "reasoning": "AI Analysis Failed"}
        
        return {"signal": "TYPE C", "reasoning": "Low Confidence"}
