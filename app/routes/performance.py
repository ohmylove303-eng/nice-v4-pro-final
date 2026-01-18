"""
Performance API Routes
추천 성과 데이터를 제공하는 API 엔드포인트
"""

from flask import Blueprint, jsonify
import os
import json

performance_bp = Blueprint('performance', __name__)

# 데이터 디렉토리
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')


def load_json_file(filename: str, default: any = None):
    """JSON 파일 로드 헬퍼"""
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
    return default if default is not None else {}


@performance_bp.route('/api/us/performance')
def get_performance():
    """전체 추천 성과 데이터 반환"""
    try:
        performance_data = load_json_file('recommendation_performance.json')
        
        if not performance_data:
            return jsonify({
                "error": "No performance data available yet",
                "message": "성과 데이터가 아직 없습니다. 첫 번째 데이터 업데이트 후 확인해주세요."
            }), 404
        
        return jsonify(performance_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@performance_bp.route('/api/us/performance/smart-money')
def get_smart_money_performance():
    """Smart Money 추천 성과 상세"""
    try:
        performance_data = load_json_file('recommendation_performance.json')
        
        if not performance_data or 'smart_money' not in performance_data:
            return jsonify({
                "error": "No Smart Money performance data available",
                "total_recommendations": 0,
                "hit_rate": 0,
                "avg_return": 0,
                "history": []
            })
        
        sm_data = performance_data['smart_money']
        sm_data['last_updated'] = performance_data.get('last_updated', '')
        
        return jsonify(sm_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@performance_bp.route('/api/us/performance/closing-bell')
def get_closing_bell_performance():
    """Closing Bell 추천 성과 상세"""
    try:
        performance_data = load_json_file('recommendation_performance.json')
        
        if not performance_data or 'closing_bell' not in performance_data:
            return jsonify({
                "error": "No Closing Bell performance data available",
                "total_recommendations": 0,
                "hit_rate": 0,
                "avg_return": 0,
                "history": []
            })
        
        cb_data = performance_data['closing_bell']
        cb_data['last_updated'] = performance_data.get('last_updated', '')
        
        return jsonify(cb_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@performance_bp.route('/api/us/performance/summary')
def get_performance_summary():
    """성과 요약 (대시보드 카드용)"""
    try:
        performance_data = load_json_file('recommendation_performance.json')
        
        if not performance_data:
            return jsonify({
                "smart_money": {
                    "hit_rate": 0,
                    "avg_return": 0,
                    "total": 0
                },
                "closing_bell": {
                    "hit_rate": 0,
                    "avg_return": 0,
                    "total": 0
                },
                "last_updated": None
            })
        
        sm = performance_data.get('smart_money', {})
        cb = performance_data.get('closing_bell', {})
        
        return jsonify({
            "smart_money": {
                "hit_rate": sm.get('hit_rate', 0),
                "avg_return": sm.get('avg_return', 0),
                "total": sm.get('total_recommendations', 0),
                "successful": sm.get('successful', 0),
                "failed": sm.get('failed', 0),
                "active": sm.get('active', 0)
            },
            "closing_bell": {
                "hit_rate": cb.get('hit_rate', 0),
                "avg_return": cb.get('avg_return', 0),
                "total": cb.get('total_recommendations', 0),
                "successful": cb.get('successful', 0),
                "failed": cb.get('failed', 0),
                "active": cb.get('active', 0)
            },
            "last_updated": performance_data.get('last_updated')
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
