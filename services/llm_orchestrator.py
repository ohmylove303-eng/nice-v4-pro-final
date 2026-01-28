# services/llm_orchestrator.py
import os
import requests
import json
import logging

class LLMOrchestrator:
    def __init__(self):
        self.server_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

    def synthesize(self, symbol, scores, weighted_score, override_key=None):
        # Determine which key to use
        active_key = override_key or self.server_key
        
        if not active_key: 
            return {"signal": "TYPE C", "reasoning": "API 키가 없습니다."}
            
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
        payload = {
            "contents": [{
                "parts": [{"text": prompt_text}]
            }]
        }
        
        try:
            # Fallback to older model if Flash fails? Actually REST is safer.
            # But just in case, we can try gemini-pro url if first fails? 
            # Let's stick to 1.5-flash first as it's standard now.
            
            response = requests.post(self.api_url, headers=headers, params=params, json=payload, timeout=10)
            
            if response.status_code != 200:
                # Fallback to Gemini Pro REST URL
                fallback_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
                response = requests.post(fallback_url, headers=headers, params=params, json=payload, timeout=10)
                
                if response.status_code != 200:
                    return {"signal": "TYPE C", "reasoning": f"API 오류 ({response.status_code}): {response.text[:50]}..."}

            data = response.json()
            
            # Parse Candidate
            try:
                raw_text = data['candidates'][0]['content']['parts'][0]['text']
                # Clean JSON
                s = raw_text.find('{')
                e = raw_text.rfind('}')
                if s!=-1 and e!=-1:
                    return json.loads(raw_text[s:e+1])
                return {"signal": "TYPE C", "reasoning": raw_text[:100]}
            except:
                 return {"signal": "TYPE C", "reasoning": "응답 파싱 실패 (JSON 형식 아님)"}

        except Exception as e:
            return {"signal": "TYPE C", "reasoning": f"연결 오류: {str(e)}"}

