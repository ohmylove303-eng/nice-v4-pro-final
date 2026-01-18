# US Recommendation Engine (3개 종목 선정)
from datetime import datetime
from typing import List, Dict

class USRecommendationEngine:
    """추천 종목 3개 자동 선정"""
    
    def get_final_recommendations(self, candidates: List[Dict]) -> Dict:
        """
        최종 추천 3개
        
        필터링 조건:
        - Closing Bell 조건 >= 4개
        - Perplexity 신뢰도 > 70%
        - NICE 점수 > 80
        
        없으면 미표시
        """
        
        filtered = [
            c for c in candidates
            if c.get('closing_bell_passed', 0) >= 4
            and c.get('perplexity_confidence', 0) > 0.70
            and c.get('nice_score', 0) > 80
        ]
        
        # 상위 3개 (NICE 점수 내림차순)
        top_3 = sorted(
            filtered,
            key=lambda x: x.get('nice_score', 0),
            reverse=True
        )[:3]
        
        if len(top_3) == 0:
            return {
                'status': 'NO_RECOMMENDATIONS',
                'count': 0,
                'message': '조건을 만족하는 종목이 없습니다',
                'recommendations': [],
                'timestamp': datetime.now().isoformat()
            }
        
        # 순위 추가
        for i, rec in enumerate(top_3, 1):
            rec['rank'] = i
        
        return {
            'status': 'SUCCESS',
            'count': len(top_3),
            'message': f'{len(top_3)}개 종목 추천',
            'recommendations': top_3,
            'timestamp': datetime.now().isoformat()
        }
    
    def calculate_simple_nice_score(self, checks: Dict, volume_ratio: float) -> int:
        """간단한 NICE 점수 계산 (0-100)"""
        score = 50  # 기본 점수
        
        # 각 조건당 +10점
        if checks.get('volume'):
            score += 10
            # 거래량 폭증 보너스
            if volume_ratio >= 2.0:
                score += 5
        
        if checks.get('price'):
            score += 10
        
        if checks.get('ma'):
            score += 10
        
        if checks.get('resistance'):
            score += 10
        
        if checks.get('pattern'):
            score += 10
        
        return min(score, 100)
