# services/llm_orchestrator.py
import os
import requests
import json
import logging

class LLMOrchestrator:
    def __init__(self):
        self.server_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        # Base URL pattern
        self.base_url = "https://generativelanguage.googleapis.com/v1/models/{}:generateContent"

    def synthesize(self, symbol, scores, weighted_score, override_key=None):
        active_key = override_key or self.server_key
        
        if not active_key: 
            return {"signal": "TYPE C", "reasoning": "API 키가 등록되지 않았습니다."}
            
        # Simple Korean Prompt
        prompt_text = f"""
        역할: 가상화폐 최고투자책임자(CIO).
        데이터: {symbol} 종합점수 {weighted_score}/100.
        세부점수: 기술적 {scores['technical']}, 온체인 {scores['onchain']}, 정서 {scores['sentiment']}, 거시경제 {scores['macro']}, 기관 {scores['institutional']}.
        
        임무: 다음 JSON 형식으로 한국어 1줄 요약 분석을 제공하시오.
        형식: {{ "signal": "TYPE A/B/C", "reasoning": "핵심만 간결하게 1줄 코멘트 (존댓말 사용)" }}
        규칙: A(>80, 강력매수), B(>60, 매수), C(관망). 변동성과 거래량에 집중.
        """
        
        headers = {'Content-Type': 'application/json'}
        params = {'key': active_key}
        payload = { "contents": [{ "parts": [{"text": prompt_text}] }] }
        
        # Priority Chain: Flash (Fast) -> Pro (Stable) -> 1.0 Pro (Legacy)
        models_to_try = ["gemini-1.5-flash", "gemini-pro", "gemini-1.0-pro"]
        
        last_error = ""
        
        for model in models_to_try:
            try:
                # Try v1beta for Flash (it might require beta), v1 for Pro
                version = "v1beta" if "flash" in model else "v1"
                url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent"
                
                response = requests.post(url, headers=headers, params=params, json=payload, timeout=8)
                
                if response.status_code == 200:
                    data = response.json()
                    raw_text = data['candidates'][0]['content']['parts'][0]['text']
                    # Clean JSON
                    s = raw_text.find('{')
                    e = raw_text.rfind('}')
                    if s!=-1 and e!=-1:
                        return json.loads(raw_text[s:e+1])
                    return {"signal": "TYPE C", "reasoning": raw_text[:100]}
                else:
                    last_error = f"{model} ({response.status_code}): {response.text[:100]}"
                    continue # Try next model
                    
            except Exception as e:
                last_error = f"{model} Exception: {str(e)}"
                continue

        return {"signal": "TYPE C", "reasoning": f"모든 모델 연결 실패: {last_error}"}

