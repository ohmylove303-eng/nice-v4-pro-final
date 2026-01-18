#!/usr/bin/env python3
"""
Performance Tracker for Stock Recommendations
추천 종목의 성과를 추적하고 적중률을 계산하는 스크립트
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'data')

# API 키
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY', '')
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', '')

# 성과 판정 기준
SMART_MONEY_MAX_DAYS = 30  # Smart Money 최대 보유 기간
CLOSING_BELL_EVAL_DAYS = 3  # Closing Bell 평가 기간
SUCCESS_THRESHOLD = 0.10  # 10% 이상 상승시 성공
STOP_LOSS_THRESHOLD = -0.10  # 10% 이상 하락시 손절


class PerformanceTracker:
    """추천 성과 추적 클래스"""
    
    def __init__(self):
        self.data_dir = DATA_DIR
        self.smart_money_history_file = os.path.join(self.data_dir, 'smart_money_history.json')
        self.closing_bell_history_file = os.path.join(self.data_dir, 'closing_bell_history.json')
        self.performance_file = os.path.join(self.data_dir, 'recommendation_performance.json')
        
        # 데이터 로드
        self.smart_money_history = self._load_json(self.smart_money_history_file, {})
        self.closing_bell_history = self._load_json(self.closing_bell_history_file, {})
        self.performance_data = self._load_json(self.performance_file, self._get_empty_performance())
    
    def _load_json(self, filepath: str, default: any) -> any:
        """JSON 파일 로드"""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading {filepath}: {e}")
        return default
    
    def _save_json(self, filepath: str, data: any):
        """JSON 파일 저장"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved: {filepath}")
        except Exception as e:
            logger.error(f"Error saving {filepath}: {e}")
    
    def _get_empty_performance(self) -> Dict:
        """빈 성과 데이터 구조"""
        return {
            "last_updated": "",
            "smart_money": {
                "total_recommendations": 0,
                "active": 0,
                "successful": 0,
                "failed": 0,
                "hit_rate": 0.0,
                "avg_return": 0.0,
                "best_pick": {"ticker": "", "return_pct": 0.0},
                "worst_pick": {"ticker": "", "return_pct": 0.0},
                "history": []
            },
            "closing_bell": {
                "total_recommendations": 0,
                "active": 0,
                "successful": 0,
                "failed": 0,
                "hit_rate": 0.0,
                "avg_return": 0.0,
                "best_pick": {"ticker": "", "return_pct": 0.0},
                "worst_pick": {"ticker": "", "return_pct": 0.0},
                "history": []
            }
        }
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """현재 주가 조회 (Finnhub API)"""
        try:
            if not FINNHUB_API_KEY:
                logger.warning("FINNHUB_API_KEY not set")
                return None
            
            url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                current_price = data.get('c', 0)  # 'c' = current price
                if current_price and current_price > 0:
                    return float(current_price)
            
            logger.warning(f"Failed to get price for {ticker}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting price for {ticker}: {e}")
            return None
    
    def save_daily_recommendations(self):
        """오늘의 추천을 history에 저장"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Smart Money 현재 데이터 저장
        smart_money_file = os.path.join(self.data_dir, 'smart_money_current.json')
        if os.path.exists(smart_money_file):
            try:
                with open(smart_money_file, 'r', encoding='utf-8') as f:
                    smart_money_data = json.load(f)
                
                recommendations = []
                for pick in smart_money_data.get('picks', [])[:10]:  # Top 10
                    recommendations.append({
                        "ticker": pick.get('ticker', ''),
                        "name": pick.get('name', ''),
                        "recommended_price": pick.get('current_price', 0),
                        "target_price": pick.get('target_price', 0),
                        "ai_score": pick.get('ai_score', 0),
                        "recommendation": pick.get('recommendation', 'Hold'),
                        "date": today
                    })
                
                if recommendations:
                    self.smart_money_history[today] = {
                        "recommendations": recommendations,
                        "saved_at": datetime.now().isoformat()
                    }
                    logger.info(f"Saved {len(recommendations)} Smart Money recommendations for {today}")
                    
            except Exception as e:
                logger.error(f"Error saving Smart Money history: {e}")
        
        # Closing Bell 데이터 저장 (있는 경우)
        closing_bell_file = os.path.join(self.data_dir, 'closing_bell_current.json')
        if os.path.exists(closing_bell_file):
            try:
                with open(closing_bell_file, 'r', encoding='utf-8') as f:
                    closing_bell_data = json.load(f)
                
                recommendations = []
                for rec in closing_bell_data.get('recommendations', []):
                    recommendations.append({
                        "ticker": rec.get('ticker', ''),
                        "name": rec.get('name', ''),
                        "entry_price": rec.get('entry_price', 0),
                        "conditions": rec.get('conditions', []),
                        "date": today
                    })
                
                if recommendations:
                    self.closing_bell_history[today] = {
                        "recommendations": recommendations,
                        "saved_at": datetime.now().isoformat()
                    }
                    logger.info(f"Saved {len(recommendations)} Closing Bell recommendations for {today}")
                    
            except Exception as e:
                logger.error(f"Error saving Closing Bell history: {e}")
        
        # History 파일 저장
        self._save_json(self.smart_money_history_file, self.smart_money_history)
        self._save_json(self.closing_bell_history_file, self.closing_bell_history)
    
    def calculate_smart_money_performance(self):
        """Smart Money 추천 성과 계산"""
        today = datetime.now()
        performance_history = []
        
        for date_str, day_data in self.smart_money_history.items():
            try:
                rec_date = datetime.strptime(date_str, '%Y-%m-%d')
                days_held = (today - rec_date).days
                
                for rec in day_data.get('recommendations', []):
                    ticker = rec.get('ticker', '')
                    recommended_price = rec.get('recommended_price', 0)
                    target_price = rec.get('target_price', 0)
                    
                    if not ticker or not recommended_price:
                        continue
                    
                    # 현재 가격 조회
                    current_price = self.get_current_price(ticker)
                    if current_price is None:
                        continue
                    
                    # 수익률 계산
                    return_pct = ((current_price - recommended_price) / recommended_price) * 100
                    
                    # 목표가 도달 여부
                    target_hit = current_price >= target_price if target_price > 0 else False
                    
                    # 상태 판정
                    if target_hit or return_pct >= SUCCESS_THRESHOLD * 100:
                        status = "success"
                    elif return_pct <= STOP_LOSS_THRESHOLD * 100:
                        status = "failed"
                    elif days_held > SMART_MONEY_MAX_DAYS:
                        status = "failed" if return_pct < 0 else "success"
                    else:
                        status = "active"
                    
                    performance_history.append({
                        "ticker": ticker,
                        "name": rec.get('name', ''),
                        "recommended_date": date_str,
                        "recommended_price": round(recommended_price, 2),
                        "target_price": round(target_price, 2),
                        "current_price": round(current_price, 2),
                        "days_held": days_held,
                        "return_pct": round(return_pct, 2),
                        "target_hit": target_hit,
                        "status": status
                    })
                    
            except Exception as e:
                logger.error(f"Error processing {date_str}: {e}")
        
        return performance_history
    
    def calculate_closing_bell_performance(self):
        """Closing Bell 추천 성과 계산"""
        today = datetime.now()
        performance_history = []
        
        for date_str, day_data in self.closing_bell_history.items():
            try:
                rec_date = datetime.strptime(date_str, '%Y-%m-%d')
                days_held = (today - rec_date).days
                
                # 최소 1일 경과 필요 (다음날 종가 기준)
                if days_held < 1:
                    continue
                
                for rec in day_data.get('recommendations', []):
                    ticker = rec.get('ticker', '')
                    entry_price = rec.get('entry_price', 0)
                    
                    if not ticker or not entry_price:
                        continue
                    
                    # 현재 가격 조회
                    current_price = self.get_current_price(ticker)
                    if current_price is None:
                        continue
                    
                    # 수익률 계산
                    return_pct = ((current_price - entry_price) / entry_price) * 100
                    
                    # 상태 판정 (단타 기준)
                    if return_pct >= 2.0:  # 2% 이상 상승
                        status = "success"
                    elif return_pct <= -2.0:  # 2% 이상 하락
                        status = "failed"
                    elif days_held >= CLOSING_BELL_EVAL_DAYS:
                        status = "success" if return_pct > 0 else "failed"
                    else:
                        status = "active"
                    
                    performance_history.append({
                        "ticker": ticker,
                        "name": rec.get('name', ''),
                        "recommended_date": date_str,
                        "entry_price": round(entry_price, 2),
                        "current_price": round(current_price, 2),
                        "days_held": days_held,
                        "return_pct": round(return_pct, 2),
                        "conditions": rec.get('conditions', []),
                        "status": status
                    })
                    
            except Exception as e:
                logger.error(f"Error processing {date_str}: {e}")
        
        return performance_history
    
    def aggregate_statistics(self, history: List[Dict]) -> Dict:
        """통계 집계"""
        if not history:
            return {
                "total_recommendations": 0,
                "active": 0,
                "successful": 0,
                "failed": 0,
                "hit_rate": 0.0,
                "avg_return": 0.0,
                "best_pick": {"ticker": "", "return_pct": 0.0},
                "worst_pick": {"ticker": "", "return_pct": 0.0}
            }
        
        total = len(history)
        active = sum(1 for h in history if h['status'] == 'active')
        successful = sum(1 for h in history if h['status'] == 'success')
        failed = sum(1 for h in history if h['status'] == 'failed')
        
        # 완료된 것만으로 적중률 계산
        completed = successful + failed
        hit_rate = (successful / completed * 100) if completed > 0 else 0.0
        
        # 평균 수익률
        returns = [h['return_pct'] for h in history]
        avg_return = sum(returns) / len(returns) if returns else 0.0
        
        # 최고/최저 성과
        best = max(history, key=lambda x: x['return_pct']) if history else None
        worst = min(history, key=lambda x: x['return_pct']) if history else None
        
        return {
            "total_recommendations": total,
            "active": active,
            "successful": successful,
            "failed": failed,
            "hit_rate": round(hit_rate, 1),
            "avg_return": round(avg_return, 2),
            "best_pick": {
                "ticker": best['ticker'] if best else "",
                "return_pct": best['return_pct'] if best else 0.0
            },
            "worst_pick": {
                "ticker": worst['ticker'] if worst else "",
                "return_pct": worst['return_pct'] if worst else 0.0
            }
        }
    
    def run(self):
        """메인 실행"""
        logger.info("🚀 Starting Performance Tracker...")
        
        # 1. 오늘의 추천 저장
        logger.info("📝 Saving today's recommendations...")
        self.save_daily_recommendations()
        
        # 2. Smart Money 성과 계산
        logger.info("📊 Calculating Smart Money performance...")
        sm_history = self.calculate_smart_money_performance()
        sm_stats = self.aggregate_statistics(sm_history)
        sm_stats['history'] = sorted(sm_history, key=lambda x: x['recommended_date'], reverse=True)[:50]
        
        # 3. Closing Bell 성과 계산
        logger.info("📊 Calculating Closing Bell performance...")
        cb_history = self.calculate_closing_bell_performance()
        cb_stats = self.aggregate_statistics(cb_history)
        cb_stats['history'] = sorted(cb_history, key=lambda x: x['recommended_date'], reverse=True)[:50]
        
        # 4. 결과 저장
        self.performance_data = {
            "last_updated": datetime.now().isoformat(),
            "smart_money": sm_stats,
            "closing_bell": cb_stats
        }
        self._save_json(self.performance_file, self.performance_data)
        
        # 5. 요약 출력
        logger.info("=" * 50)
        logger.info("📈 Performance Summary")
        logger.info("=" * 50)
        logger.info(f"Smart Money - 적중률: {sm_stats['hit_rate']}%, 평균수익률: {sm_stats['avg_return']}%")
        logger.info(f"Closing Bell - 적중률: {cb_stats['hit_rate']}%, 평균수익률: {cb_stats['avg_return']}%")
        logger.info("=" * 50)
        
        return self.performance_data


if __name__ == "__main__":
    tracker = PerformanceTracker()
    tracker.run()
