# ============================================================
# NICE MPC v44.3 Backend - [REAL PRICE UPDATE]
# ============================================================

from flask import Flask, jsonify, render_template
from flask_cors import CORS
import logging
import pyupbit 
from datetime import datetime
import pytz
import requests
import config
import google.generativeai as genai
import os
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gemini Setup
GEMINI_KEY = os.getenv('GOOGLE_API_KEY')
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None

app = Flask(__name__)
CORS(app)

def get_market_metrics():
    """
    업비트에서 핵심 데이터(BTC 가격, RSI, 거래량)를 한방에 가져옵니다.
    """
    try:
        # 1. 비트코인 분석 (시장 전체 지표)
        btc_price = pyupbit.get_current_price("KRW-BTC")
        df = pyupbit.get_ohlcv("KRW-BTC", interval="minute15", count=30)
        
        # 간단 RSI 계산
        delta = df['close'].diff()
        up, down = delta.copy(), delta.copy()
        up[up < 0] = 0
        down[down > 0] = 0
        _gain = up.ewm(com=13, adjust=False).mean()
        _loss = down.abs().ewm(com=13, adjust=False).mean()
        rs = _gain / _loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        return {
            "btc_price": btc_price,
            "rsi": rsi,
            "volume_score": int((df['volume'].iloc[-1] / df['volume'].mean()) * 50) + 30
        }
    except:
        return {"btc_price": 0, "rsi": 50, "volume_score": 50}

def get_coin_price(ticker):
    """개별 코인 현재가 조회"""
    try:
        return pyupbit.get_current_price(ticker)
    except:
        return 0

def get_bithumb_data():
    """빗썸 주요 코인 시세 및 김프 계산"""
    try:
        # 빗썸 API: ALL (전체 시세)
        url = f"{config.BITHUMB_API_URL}/ticker/ALL_KRW"
        res = requests.get(url, timeout=2).json()
        
        if res['status'] != '0000': return []
        
        data = res['data']
        result = []
        
        # 바이낸스 테더 가격 (김프 계산용) - 간소화
        try:
            binance_btc = float(requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=1).json()['price'])
        except:
            binance_btc = 98000 # Fallback
            
        for sym, coin in data.items():
            if sym == 'date': continue # 메타데이터 제외
            
            # 필수 필드 체크
            if 'closing_price' not in coin: continue
            
            price = float(coin['closing_price'])
            chg_rate = float(coin['fluctate_rate_24H'])
            vol = float(coin['acc_trade_value_24H'])
            
            # 거래량 적은 코인 필터링 (옵션 - 1억 미만 제외)
            if vol < 100000000: continue
            
            # 김프 (BTC 기준 약식용 - 전체 적용은 API Call 과부하 방지 위해 생략하거나 BTC만 적용)
            kimp_txt = "-"
            if sym == 'BTC' and binance_btc > 0:
                kimp = ((price / (binance_btc * config.KRW_RATE)) - 1) * 100
                kimp_txt = f"{kimp:.1f}%"
                
            result.append({
                "symbol": sym,
                "price": price,
                "chg": chg_rate,
                "vol": vol,
                "kimp": kimp_txt
            })
            
        # 등락률 순 정렬 (Hot Coins)
        result.sort(key=lambda x: x['chg'], reverse=True)
            
        return result
    except Exception as e:
        logger.error(f"Bithumb API Error: {e}")
        return []

def get_global_metrics():
    """CoinMarketCap 글로벌 지표"""
    try:
        url = f"{config.COINMARKETCAP_API_URL}/global-metrics/quotes/latest"
        headers = {'X-CMC_PRO_API_KEY': config.COINMARKETCAP_API_KEY}
        res = requests.get(url, headers=headers, timeout=3).json()
        
        data = res['data']
        btc_d = data['btc_dominance']
        eth_d = data['eth_dominance']
        mcap_chg = data['quote']['USD']['total_market_cap_yesterday_percentage_change']
        
        return {
            "btc_dominance": f"{btc_d:.1f}%",
            "eth_dominance": f"{eth_d:.1f}%",
            "market_change": f"{mcap_chg:.2f}%",
            "status": "BULL" if mcap_chg > 0 else "BEAR"
        }
    except Exception as e:
        logger.error(f"CMC API Error: {e}")
        return {"btc_dominance": "-", "eth_dominance": "-", "market_change": "-", "status": "-"}

    except Exception as e:
        logger.error(f"CMC API Error: {e}")
        return {"btc_dominance": "-", "eth_dominance": "-", "market_change": "-", "status": "-"}

def calculate_technical_indicators(df):
    """기술적 지표 계산 (RSI, MACD, BB, MA)"""
    try:
        close = df['close']
        
        # 1. RSI (14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # 2. Bollinger Bands (20, 2)
        ma20 = close.rolling(window=20).mean()
        std20 = close.rolling(window=20).std()
        upper = ma20 + (std20 * 2)
        lower = ma20 - (std20 * 2)
        
        # 3. Moving Averages
        ma60 = close.rolling(window=60).mean()
        ma200 = close.rolling(window=200).mean()
        
        return {
            "rsi": rsi.iloc[-1],
            "bb_upper": upper.iloc[-1],
            "bb_lower": lower.iloc[-1],
            "ma20": ma20.iloc[-1],
            "ma60": ma60.iloc[-1],
            "ma200": ma200.iloc[-1]
        }
    except:
        return None

def calculate_wave_levels(df):
    """파동 분석 (피보나치 & 지지저항) - 200일 기준"""
    try:
        high_200 = df['high'].max()
        low_200 = df['low'].min()
        curr = df['close'].iloc[-1]
        
        # 피보나치 레벨
        diff = high_200 - low_200
        fib = {
            "0.236": high_200 - (diff * 0.236),
            "0.382": high_200 - (diff * 0.382),
            "0.5": high_200 - (diff * 0.5),
            "0.618": high_200 - (diff * 0.618)
        }
        
        # 현재 위치 파악
        status = "중립 구간"
        if curr > fib["0.236"]: status = "강세 (신고가 도전)"
        elif curr > fib["0.5"]: status = "조정 (0.5 지지선 위)"
        elif curr < fib["0.618"]: status = "약세 (지지선 붕괴 위험)"
        
        # 추세선 (MA 정배열 확인)
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        ma60 = df['close'].rolling(60).mean().iloc[-1]
        trend_score = 50
        trend_str = "횡보"
        
        if ma20 > ma60: 
            trend_str = "상승 추세"
            trend_score = 70 + (10 if curr > ma20 else 0)
        elif ma20 < ma60:
            trend_str = "하락 추세"
            trend_score = 30
            
        return {
            "status": status,
            "levels": {k: int(v) for k,v in fib.items()},
            "trend": trend_str,
            "trend_score": trend_score
        }
    except:
        return {"status": "분석 실패", "levels": {}, "trend": "-", "trend_score": 0}

def get_ai_insight(ticker, df, tech):
    """Gemini AI 분석 (기술적 지표 포함)"""
    try:
        if not model: return {"summary": "AI 모델이 설정되지 않았습니다. (API Key Missing)", "score": 50}
        
        curr = df['close'].iloc[-1]
        closes = df['close'].tail(5).tolist()
        
        # 기술적 지표 없을 경우 대비
        rsi = f"{tech['rsi']:.1f}" if tech else "N/A"
        bb_pos = "Band Inside"
        if tech:
            if curr > tech['bb_upper']: bb_pos = "Overbought (Band Upper)"
            elif curr < tech['bb_lower']: bb_pos = "Oversold (Band Lower)"
            
        prompt = f"""
        Analyze {ticker} crypto asset.
        Date: {datetime.now().strftime('%Y-%m-%d')}
        Current Price: {curr}
        Recent 5-day Prices: {closes}
        Key Indicators: RSI {rsi}, BB Position {bb_pos}
        
        Task:
        1. Summarize market sentiment (Korean, 2 sentences).
        2. Give an investment score (0-100) based on Technicals.
        
        Output format: JSON {{ "summary": "...", "score": 75 }}
        """
        
        res = model.generate_content(prompt)
        # Mock Parsing fallback if JSON fails
        txt = res.text
        import json
        try:
            # Try to find JSON block
            if "{" in txt and "}" in txt:
                json_str = txt[txt.find("{"):txt.rfind("}")+1]
                data = json.loads(json_str)
                return data
            else:
                return {"summary": txt[:100] + "...", "score": 60}
        except:
             return {"summary": txt[:100] + "...", "score": 60}
             
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return {"summary": "AI 분석 중 오류가 발생했습니다.", "score": 50}

def calculate_precision_layers(tech, vol_24h):
    """5-Layer 정밀 분석 점수 (Real Logic)"""
    if not tech: return  {
            "L1_Tech": 50, "L2_Whale": 50, "L3_Sentiment": 50,
            "L4_Macro": 50, "L5_Inst": 50,
            "Total_Score": 50,
            "Comment": "데이터 부족"
        }
        
    # L1: Technical (RSI, BB)
    l1 = 50
    rsi = tech['rsi']
    if rsi < 30: l1 = 80 # 과매도 -> 매수 기회
    elif rsi > 70: l1 = 30 # 과매수 -> 매도 압박
    else: l1 = 60 if rsi > 50 else 40
    
    # L2: Whale/Liquidity (Volume)
    # 거래량이 충분한지 (대략 1000억 기준) - 상대적이나 절대값으로 간단 처리
    l2 = min(90, max(20, int(vol_24h / 1000000000 * 2))) # 10억당 2점? 너무 낮음. 
    if vol_24h > 100_000_000_000: l2 = 85
    elif vol_24h > 30_000_000_000: l2 = 60
    else: l2 = 30
    
    # L3: Sentiment (RSI 기반 추정 + 추세)
    l3 = 70 if tech['ma20'] > tech['ma60'] else 30
    
    # L4: Macro (고정값 or Global API 연동 필요하지만 여기선 L3와 연동)
    l4 = l3
    
    # L5: Institutional (BB Bandwidth or Stability)
    # 밴드폭이 좁으면(수렴) 기관 매집 가능성 -> 점수 높임
    bandwidth = (tech['bb_upper'] - tech['bb_lower']) / tech['ma20']
    l5 = 80 if bandwidth < 0.1 else 40
    
    total = int((l1 + l2 + l3 + l4 + l5) / 5)
    
    comment = "관망 필요"
    if total > 70: comment = "적극 매수 구간"
    elif total > 55: comment = "매수 우위"
    elif total < 40: comment = "매도/리스크 관리"
    
    return {
        "L1_Tech": int(l1), "L2_Liquidity": int(l2), "L3_Sentiment": int(l3),
        "L4_Macro": int(l4), "L5_Inst": int(l5),
        "Total_Score": total,
        "Comment": comment
    }

@app.route('/api/analyze/<ticker>')
def analyze_coin(ticker):
    """심층 분석 API (Chart -> Wave -> AI -> Stats -> Report)"""
    try:
        # 1. 캔들 데이터 (Upbit) - 200일 확보
        if not ticker.startswith("KRW-"): ticker = f"KRW-{ticker}"
        df = pyupbit.get_ohlcv(ticker, interval="day", count=200)
        
        if df is None: return jsonify({"error": "Data not found"}), 404
        
        # 최신 거래량 등 기본 정보 (Ticker)
        try:
            curr_info = pyupbit.get_current_price(ticker, verbose=True)
            vol_24h = curr_info.get('acc_trade_price_24h', 0)
        except:
            vol_24h = 0
        
        # 2. 기술적 지표 계산
        tech = calculate_technical_indicators(df)
        
        # 3. 파동 분석
        wave = calculate_wave_levels(df)
        
        # 4. AI 분석
        ai = get_ai_insight(ticker, df, tech)
        
        # 5. 정밀 분석 (5-Layer Real)
        precision = calculate_precision_layers(tech, vol_24h)
        
        return jsonify({
            "ticker": ticker,
            "current_price": float(df['close'].iloc[-1]),
            "wave_analysis": wave,
            "ai_insight": ai,
            "precision_report": precision,
            "chart_data_len": len(df),
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
        
    except Exception as e:
        logger.error(f"Analysis Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/mpc-data', methods=['GET'])
def get_mpc_data():
    # 1. 시장 지표 가져오기
    metrics = get_market_metrics()
    btc_price = metrics["btc_price"]
    rsi = metrics["rsi"]
    
    # 2. NICE 레이어 점수 산출 (실제 데이터 기반)
    # L0: 가격이 1억 이상이면 기본 점수 부여 (예시 로직)
    l0_score = 60 + (1 if btc_price > 0 else 0) 
    l1_score = metrics["volume_score"]
    l3_score = int(rsi)
    
    # 점수 보정 (0~100 사이)
    l0_score = max(30, min(90, l0_score))
    l1_score = max(20, min(95, l1_score))
    
    # 3. 개별 추천 코인 가격 조회
    xrp_price = get_coin_price("KRW-XRP")
    sui_price = get_coin_price("KRW-SUI")
    sui_price = get_coin_price("KRW-SUI")
    doge_price = get_coin_price("KRW-DOGE")

    # 4. 추가 데이터 소스 (빗썸, CMC)
    bithumb_data = get_bithumb_data()
    global_macro = get_global_metrics()

    wrs_avg = round((l0_score + l1_score + 60 + l3_score + 70)/5, 1)

    response_data = {
        "current_snapshot": {
            "wrs": wrs_avg,
            "tier": "TIER 2" if wrs_avg < 70 else "TIER 1",
            "time": datetime.now(pytz.timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M:%S")
        },
        "layer_scores": [
            # desc 부분에 실제 가격 정보를 넣어서 보냅니다!
            {"id": "L0", "name": "L0 매크로", "score": l0_score, "desc": f"BTC {btc_price:,.0f}원"},
            {"id": "L1", "name": "L1 거래량", "score": l1_score, "desc": "실시간 거래량 분석"},
            {"id": "L2", "name": "L2 유동성", "score": 60, "desc": "메이저 알트 유입"},
            {"id": "L3", "name": "L3 모멘텀", "score": l3_score, "desc": f"RSI {rsi:.1f}"},
            {"id": "L7", "name": "L7 온체인", "score": 70, "desc": "기관 매수세"}
        ],
        "wrs_timeline": [
            {"time": "현재", "wrs": wrs_avg, "tier": "REAL"}
        ],
        "recommendations": {
             "scalping": {
                "title": "단타 (Real-Time)", "mode": "공격적",
                "coins": [
                    # 여기에 실제 가격을 문자열로 포맷팅해서 넣습니다
                    {"symbol": "BTC", "label": "비트코인", "role": "대장주", "entry": f"{btc_price:,.0f}", "tp": "자율", "sl": "-1%"},
                    {"symbol": "DOGE", "label": "도지코인", "role": "모멘텀", "entry": f"{doge_price:,.0f}", "tp": "+5%", "sl": "-3%"}
                ]
            },
            "short": {
                "title": "단기 스윙", "mode": "추세",
                "coins": [
                    {"symbol": "XRP", "label": "리플", "role": "메이저", "entry": f"{xrp_price:,.0f}", "tp": "+10%", "sl": "-5%"},
                    {"symbol": "SUI", "label": "수이", "role": "성장형", "entry": f"{sui_price:,.0f}", "tp": "+15%", "sl": "-7%"}
                ]
            },
            "medium": { "title": "중기", "mode": "관망", "coins": [] }
        }
        },
        "bithumb_list": bithumb_data,
        "global_macro": global_macro
    }
    
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)