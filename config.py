# ============================================
# NICE MPC v44.2 - config.py
# 한국(Upbit) + 글로벌 암호화폐 시장 실시간 데이터
# ============================================

import os
from datetime import datetime

# 1. Flask 설정
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
DEBUG = FLASK_ENV == 'development'
SECRET_KEY = os.getenv('SECRET_KEY', 'nice-mpc-secret-key-dev')

# 2. API 엔드포인트 (변경 금지)
# 2. API 엔드포인트 (변경 금지)
UPBIT_API_URL = "https://api.upbit.com/v1"
BITHUMB_API_URL = "https://api.bithumb.com/public"
COINMARKETCAP_API_URL = "https://pro-api.coinmarketcap.com/v2"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

# 3. API 키 설정
# 사용법: export UPBIT_API_KEY="your_key"
UPBIT_API_KEY = os.getenv('UPBIT_API_KEY', '')  # Upbit은 공개 API 사용
COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY', 'demo')  # 무료 플랜 or API 키
COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY', '')  # CoinGecko 공개 API 사용

# 4. NICE MPC 레이어 설정
NICE_LAYERS = {
    'L0': {'name': '매크로 시황', 'weight': 0.15, 'type': 'macro'},
    'L1': {'name': '거래량', 'weight': 0.20, 'type': 'volume'},
    'L2': {'name': '유동성', 'weight': 0.15, 'type': 'liquidity'},
    'L3': {'name': '모멘텀', 'weight': 0.20, 'type': 'momentum'},
    'L7': {'name': '온체인', 'weight': 0.30, 'type': 'onchain'},
    'L9': {'name': '위험', 'weight': 0.00, 'type': 'risk_flag'}
}

# 5. 모니터링 종목 (한국 거래소 기준)
WATCHLIST_KOREAN = [
    'APM', 'PIVERSE', 'PARTI', 'TURBO', 'BRETT',
    'PENGU', 'SUI', 'DEEP', 'PENGU', 'WIF', 'ZZ',
    'BTC', 'ETH', 'SOL'
]

# 6. MPC 추천 임계값
MPC_THRESHOLDS = {
    'tier1': 80,      # TIER 1: STRONG BUY
    'tier2_plus': 70, # TIER 2+: BUY 강화
    'tier2': 60,      # TIER 2: BUY
    'tier3': 50       # TIER 3: HOLD
}

# 7. 데이터 캐시 시간 (초)
CACHE_TTL = 60  # 1분마다 갱신

# 8. 로깅 설정
LOG_DIR = os.path.expanduser('~/super_radar/logs')
LOG_LEVEL = 'INFO'

# 9. 타임존 설정
TIMEZONE = 'Asia/Seoul'

# 10. 매매 신호 설정
SIGNAL_CONFIG = {
    'scalping': {
        'period': '15m',
        'stop_loss': 0.03,      # -3%
        'take_profit': 0.06,    # +6%
        'confidence_min': 60
    },
    'short_term': {
        'period': '4h',
        'stop_loss': 0.07,      # -7%
        'take_profit': 0.12,    # +12%
        'confidence_min': 75
    },
    'medium_term': {
        'period': '1d',
        'stop_loss': 0.15,      # -15%
        'take_profit': 0.40,    # +40%
        'confidence_min': 80
    }
}

# 11. 경고 임계값
ALERT_THRESHOLDS = {
    'btc_drop_pct': -5,        # BTC -5%
    'volume_drop_pct': -20,    # 거래량 -20%
    'l9_risk_on': True         # L9 위험 플래그
}

# 12. 한국 KRW 환율 (실시간 갱신)
KRW_RATE = 1460  # 기본값, app.py에서 갱신됨

print(f"[CONFIG] NICE MPC v44.2 초기화 완료 | ENV: {FLASK_ENV}")
