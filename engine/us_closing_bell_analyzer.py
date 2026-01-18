# US Closing Bell Bet Analyzer
from datetime import datetime
import pytz
from typing import Dict

class USClosingBellAnalyzer:
    """미국 종가배팅 (Closing Bell Bet)"""
    
    def __init__(self):
        self.est = pytz.timezone('US/Eastern')
    
    def should_execute_closing_bell(self,
                                   ticker: str,
                                   today: Dict,
                                   yesterday: Dict,
                                   ma20: float,
                                   ma60: float,
                                   monthly_high: float) -> Dict:
        """
        미국 종가배팅 5조건 검증
        
        1. 거래량 >= 전일 × 150%
        2. 종가 >= 고점 × 90%
        3. 종가 > 20일선 AND 20일선 > 60일선
        4. 종가 > 월간 고점
        5. 형태 (양봉 + 윗꼬리 < 20%)
        """
        
        checks = {}
        
        # 1️⃣ 거래량
        if yesterday.get('volume', 0) > 0:
            volume_ratio = today['volume'] / yesterday['volume']
            checks['volume'] = volume_ratio >= 1.5
            checks['volume_ratio'] = round(volume_ratio, 2)
        else:
            checks['volume'] = False
            checks['volume_ratio'] = 0
        
        # 2️⃣ 종가 위치
        if today['high'] > 0:
            price_ratio = today['close'] / today['high']
            checks['price'] = price_ratio >= 0.90
            checks['price_ratio'] = round(price_ratio * 100, 1)
        else:
            checks['price'] = False
            checks['price_ratio'] = 0
        
        # 3️⃣ 이평선
        checks['ma'] = (today['close'] > ma20) and (ma20 > ma60)
        checks['ma20'] = round(ma20, 2)
        checks['ma60'] = round(ma60, 2)
        
        # 4️⃣ 월간 저항
        checks['resistance'] = today['close'] > monthly_high
        checks['monthly_high'] = round(monthly_high, 2)
        
        # 5️⃣ 형태
        is_bullish = today['close'] > today['open']
        total = today['high'] - today['low']
        
        if total > 0:
            upper_wick = today['high'] - today['close']
            wick_ratio = upper_wick / total
            checks['pattern'] = is_bullish and (wick_ratio < 0.20)
            checks['wick_ratio'] = round(wick_ratio * 100, 1)
        else:
            checks['pattern'] = False
            checks['wick_ratio'] = 0
        
        # 통과 조건 수
        condition_keys = ['volume', 'price', 'ma', 'resistance', 'pattern']
        passed = sum(1 for k in condition_keys if checks.get(k, False))
        
        # 신뢰도 계산
        if passed == 5:
            confidence = 0.88
        elif passed == 4:
            confidence = 0.75
        elif passed == 3:
            confidence = 0.60
        else:
            confidence = 0
        
        return {
            'ticker': ticker,
            'passed_conditions': passed,
            'confidence': confidence,
            'checks': checks,
            'is_qualified': passed >= 4
        }
    
    def is_trading_time(self) -> Dict:
        """트레이딩 시간 확인"""
        now = datetime.now(self.est)
        
        # 14:45 ~ 16:00 EST
        is_closing_bell_time = (
            (now.hour == 14 and now.minute >= 45) or
            now.hour == 15 or
            (now.hour == 16 and now.minute == 0)
        )
        
        # 주말 체크
        is_weekday = now.weekday() < 5
        
        return {
            'current_time': now.strftime('%H:%M EST'),
            'is_trading_time': is_closing_bell_time and is_weekday,
            'is_weekday': is_weekday,
            'message': 'Closing Bell Time' if is_closing_bell_time else 'Wait for 14:45 EST'
        }
