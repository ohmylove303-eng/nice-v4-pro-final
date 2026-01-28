# services/llm_orchestrator.py
import os
import google.generativeai as genai

class LLMOrchestrator:
    def __init__(self):
        # Support both naming conventions
        self.server_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        self.model_name = "gemini-1.5-flash"
        
        if self.server_key:
            genai.configure(api_key=self.server_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            self.model = None

    def synthesize(self, symbol, scores, weighted_score, override_key=None):
        # Determine which key to use
        active_key = override_key or self.server_key
        
        if not active_key: 
            return {"signal": "TYPE C", "reasoning": "API 키가 없습니다."}
            
        # Re-configure for this request if needed
        try:
            genai.configure(api_key=active_key)
            if not self.model: self.model = genai.GenerativeModel("gemini-1.5-flash")
        except Exception as e:
            return {"signal": "TYPE C", "reasoning": f"키 설정 오류: {str(e)}"}
        
        # Simple Korean Prompt
        prompt = f"""
        역할: 가상화폐 최고투자책임자(CIO).
        데이터: {symbol} 종합점수 {weighted_score}/100.
        세부점수: 기술적 {scores['technical']}, 온체인 {scores['onchain']}, 정서 {scores['sentiment']}, 거시경제 {scores['macro']}, 기관 {scores['institutional']}.
        
        임무: 다음 JSON 형식으로 한국어 1줄 요약 분석을 제공하시오.
        형식: {{ "signal": "TYPE A/B/C", "reasoning": "핵심만 간결하게 1줄 코멘트 (존댓말 사용)" }}
        규칙: A(>80, 강력매수), B(>60, 매수), C(관망). 변동성과 거래량에 집중.
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
            # Fallback to older model if Flash fails (404)
            if "404" in str(e) or "not found" in str(e).lower():
                try:
                    fallback_model = genai.GenerativeModel("gemini-pro")
                    res = fallback_model.generate_content(prompt)
                    txt = res.text
                    s = txt.find('{')
                    e = txt.rfind('}')
                    if s!=-1 and e!=-1:
                        return json.loads(txt[s:e+1])
                except Exception as fallback_e:
                     return {"signal": "TYPE C", "reasoning": f"모델 오류(Fallback 실패): {str(fallback_e)}"}
            
            return {"signal": "TYPE C", "reasoning": f"AI 분석 오류: {str(e)}"}
        
        return {"signal": "TYPE C", "reasoning": "AI 응답 형식 오류"}
