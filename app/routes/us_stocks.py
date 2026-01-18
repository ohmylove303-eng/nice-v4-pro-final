# US Stocks API Routes - Closing Bell
from flask import Blueprint, jsonify, request
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.us_stocks_data_collector import USStocksDataCollector
from engine.us_closing_bell_analyzer import USClosingBellAnalyzer
from engine.us_recommendation_engine import USRecommendationEngine
import pytz
from datetime import datetime
import time

us_stocks_bp = Blueprint('us_stocks', __name__, url_prefix='/api/us/stocks')

collector = USStocksDataCollector()
analyzer = USClosingBellAnalyzer()
engine = USRecommendationEngine()

@us_stocks_bp.route('/closing-bell-status', methods=['GET'])
def get_closing_bell_status():
    """트레이딩 시간 상태 확인"""
    try:
        status = analyzer.is_trading_time()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@us_stocks_bp.route('/closing-bell-recommendations', methods=['GET'])
def get_closing_bell_recommendations():
    """
    최종 추천 종목 3개
    
    curl http://localhost:5000/api/us/stocks/closing-bell-recommendations
    """
    try:
        est = pytz.timezone('US/Eastern')
        now = datetime.now(est)
        
        # 시간 체크 (테스트 모드 지원)
        test_mode = request.args.get('test', 'false').lower() == 'true'
        
        if not test_mode:
            trading_status = analyzer.is_trading_time()
            if not trading_status['is_trading_time']:
                return jsonify({
                    'status': 'not_time',
                    'message': trading_status['message'],
                    'current_time': now.isoformat(),
                    'next_window': '14:45 EST'
                }), 200  # 200 반환하여 프론트엔드에서 처리
        
        candidates = []
        errors = []
        
        # 모든 모니터링 종목 분석
        for ticker in collector.monitored_tickers:
            try:
                today = collector.get_daily_ohlcv(ticker)
                time.sleep(0.5)  # API 제한 방지
                
                yesterday = collector.get_daily_ohlcv(ticker, days_ago=1)
                time.sleep(0.5)
                
                if not today or not yesterday:
                    errors.append(f"{ticker}: No data")
                    continue
                
                # Closing Bell 5조건 검증
                ma = collector.get_moving_averages(ticker)
                time.sleep(0.5)
                
                monthly_high = collector.get_monthly_high(ticker)
                time.sleep(0.5)
                
                cb_result = analyzer.should_execute_closing_bell(
                    ticker, today, yesterday, ma['ma20'], ma['ma60'], monthly_high
                )
                
                if cb_result['passed_conditions'] < 3:
                    continue
                
                # 기업 정보
                info = collector.get_company_info(ticker)
                news = collector.get_news(ticker)
                
                # NICE 점수 계산
                nice_score = engine.calculate_simple_nice_score(
                    cb_result['checks'],
                    cb_result['checks'].get('volume_ratio', 1)
                )
                
                candidates.append({
                    'ticker': ticker,
                    'company': info['company'],
                    'sector': info['sector'],
                    'market_cap': info['market_cap'],
                    'closing_bell_passed': cb_result['passed_conditions'],
                    'confidence': cb_result['confidence'],
                    'current_price': today['close'],
                    'volume': today['volume'],
                    'checks': cb_result['checks'],
                    'key_news': [n['headline'] for n in news],
                    'nice_score': nice_score,
                    'perplexity_confidence': 0.75  # 기본값
                })
                
            except Exception as e:
                errors.append(f"{ticker}: {str(e)}")
                continue
        
        # 최종 추천 3개
        result = engine.get_final_recommendations(candidates)
        result['all_candidates'] = candidates
        result['errors'] = errors
        result['analyzed_count'] = len(collector.monitored_tickers)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@us_stocks_bp.route('/analyze/<ticker>', methods=['GET'])
def analyze_single_ticker(ticker):
    """단일 종목 분석"""
    try:
        today = collector.get_daily_ohlcv(ticker.upper())
        if not today:
            return jsonify({'error': f'No data for {ticker}'}), 404
        
        yesterday = collector.get_daily_ohlcv(ticker.upper(), days_ago=1)
        ma = collector.get_moving_averages(ticker.upper())
        monthly_high = collector.get_monthly_high(ticker.upper())
        
        cb_result = analyzer.should_execute_closing_bell(
            ticker.upper(), today, yesterday or today, 
            ma['ma20'], ma['ma60'], monthly_high
        )
        
        info = collector.get_company_info(ticker.upper())
        news = collector.get_news(ticker.upper())
        
        nice_score = engine.calculate_simple_nice_score(
            cb_result['checks'],
            cb_result['checks'].get('volume_ratio', 1)
        )
        
        return jsonify({
            'ticker': ticker.upper(),
            'company': info['company'],
            'sector': info['sector'],
            'price': today,
            'closing_bell': cb_result,
            'nice_score': nice_score,
            'news': news
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
