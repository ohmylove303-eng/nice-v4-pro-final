# ============================================================
# NICE MPC v9.0 - config.py
# 한국(Bithumb) + 글로벌 암호화폐 시장 실시간 데이터
# ============================================================

import os
from datetime import datetime

# 1. Flask 설정
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
DEBUG = FLASK_ENV == 'development'
SECRET_KEY = os.getenv('SECRET_KEY', 'nice-mpc-secret-key-dev')

# 2. API 엔드포인트
UPBIT_API_URL = "https://api.upbit.com/v1"
BITHUMB_API_URL = "https://api.bithumb.com/public"
COINMARKETCAP_API_URL = "https://pro-api.coinmarketcap.com/v2"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

# 3. API 키 설정
UPBIT_API_KEY = os.getenv('UPBIT_API_KEY', '')  
COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY', 'demo') 
COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY', '')

# 4. NICE MPC 레이어 설정
NICE_LAYERS = {
    'L0': {'name': '매크로 시황', 'weight': 0.15, 'type': 'macro'},
    'L1': {'name': '거래량', 'weight': 0.20, 'type': 'volume'},
    'L2': {'name': '유동성', 'weight': 0.15, 'type': 'liquidity'},
    'L3': {'name': '모멘텀', 'weight': 0.20, 'type': 'momentum'},
    'L7': {'name': '온체인', 'weight': 0.30, 'type': 'onchain'},
    'L9': {'name': '위험', 'weight': 0.00, 'type': 'risk_flag'}
}

# 5. 임계값
MPC_THRESHOLDS = {
    'tier1': 80,      
    'tier2_plus': 70, 
    'tier2': 60,      
    'tier3': 50       
}

# 6. 로깅 설정 (SAFE PATH FOR RENDER)
LOG_DIR = os.path.join(os.getcwd(), 'logs')
if not os.path.exists(LOG_DIR):
    try:
        os.makedirs(LOG_DIR)
    except:
        pass # If read-only filesystem, ignore

LOG_LEVEL = 'INFO'
TIMEZONE = 'Asia/Seoul'

print(f"[CONFIG] NICE MPC v9.0 Config Loaded | ENV: {FLASK_ENV}")
