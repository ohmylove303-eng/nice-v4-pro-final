#!/usr/bin/env python3
"""Flask Web Server for US Stock Dashboard - Complete Version from PART4"""
import os
import sys
import json
import threading
import pandas as pd
import numpy as np
import yfinance as yf
import subprocess
from flask import Flask, render_template, jsonify, request
import traceback
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# API keys from .env
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Initialize Google Generative AI if available
try:
    import google.generativeai as genai
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        GEMINI_MODEL = genai.GenerativeModel('gemini-2.0-flash')
        print("✅ Gemini API configured")
    else:
        GEMINI_MODEL = None
        print("⚠️ No Google API key found")
except ImportError:
    GEMINI_MODEL = None
    print("⚠️ google-generativeai not installed")

# Initialize OpenAI as fallback
OPENAI_CLIENT = None
try:
    from openai import OpenAI
    if OPENAI_API_KEY:
        OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ OpenAI API configured as fallback")
    else:
        print("⚠️ No OpenAI API key found")
except ImportError:
    print("⚠️ openai not installed")

app = Flask(__name__)

# Register Closing Bell Blueprint
try:
    from app.routes.us_stocks import us_stocks_bp
    app.register_blueprint(us_stocks_bp)
    print("✅ Closing Bell Blueprint registered")
except ImportError as e:
    print(f"⚠️ Closing Bell Blueprint not loaded: {e}")

# Register Performance Blueprint
try:
    from app.routes.performance import performance_bp
    app.register_blueprint(performance_bp)
    print("✅ Performance Blueprint registered")
except ImportError as e:
    print(f"⚠️ Performance Blueprint not loaded: {e}")


# Sector mapping for major US stocks (S&P 500 + popular stocks)
SECTOR_MAP = {
    # Technology
    'AAPL': 'Tech', 'MSFT': 'Tech', 'NVDA': 'Tech', 'AVGO': 'Tech', 'ORCL': 'Tech',
    'CRM': 'Tech', 'AMD': 'Tech', 'ADBE': 'Tech', 'CSCO': 'Tech', 'INTC': 'Tech',
    'IBM': 'Tech', 'MU': 'Tech', 'QCOM': 'Tech', 'TXN': 'Tech', 'NOW': 'Tech',
    'AMAT': 'Tech', 'LRCX': 'Tech', 'KLAC': 'Tech', 'SNPS': 'Tech', 'CDNS': 'Tech',
    'ADI': 'Tech', 'MRVL': 'Tech', 'FTNT': 'Tech', 'PANW': 'Tech', 'CRWD': 'Tech',
    'SNOW': 'Tech', 'DDOG': 'Tech', 'ZS': 'Tech', 'NET': 'Tech', 'PLTR': 'Tech',
    'DELL': 'Tech', 'HPQ': 'Tech', 'HPE': 'Tech', 'KEYS': 'Tech', 'SWKS': 'Tech',
    # Financials
    'BRK-B': 'Fin', 'JPM': 'Fin', 'V': 'Fin', 'MA': 'Fin', 'BAC': 'Fin',
    'WFC': 'Fin', 'GS': 'Fin', 'MS': 'Fin', 'SPGI': 'Fin', 'AXP': 'Fin',
    'C': 'Fin', 'BLK': 'Fin', 'SCHW': 'Fin', 'CME': 'Fin', 'CB': 'Fin',
    'PGR': 'Fin', 'MMC': 'Fin', 'AON': 'Fin', 'ICE': 'Fin', 'MCO': 'Fin',
    'USB': 'Fin', 'PNC': 'Fin', 'TFC': 'Fin', 'AIG': 'Fin', 'MET': 'Fin',
    'PRU': 'Fin', 'ALL': 'Fin', 'TRV': 'Fin', 'COIN': 'Fin', 'HOOD': 'Fin',
    # Healthcare
    'LLY': 'Health', 'UNH': 'Health', 'JNJ': 'Health', 'ABBV': 'Health', 'MRK': 'Health',
    'PFE': 'Health', 'TMO': 'Health', 'ABT': 'Health', 'DHR': 'Health', 'BMY': 'Health',
    'AMGN': 'Health', 'GILD': 'Health', 'VRTX': 'Health', 'ISRG': 'Health', 'MDT': 'Health',
    'SYK': 'Health', 'BSX': 'Health', 'REGN': 'Health', 'ZTS': 'Health', 'ELV': 'Health',
    'CI': 'Health', 'HUM': 'Health', 'CVS': 'Health', 'MCK': 'Health', 'CAH': 'Health',
    'GEHC': 'Health', 'DXCM': 'Health', 'IQV': 'Health', 'BIIB': 'Health', 'MRNA': 'Health',
    # Energy
    'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy', 'SLB': 'Energy', 'EOG': 'Energy',
    'MPC': 'Energy', 'PSX': 'Energy', 'VLO': 'Energy', 'OXY': 'Energy', 'WMB': 'Energy',
    'DVN': 'Energy', 'HES': 'Energy', 'HAL': 'Energy', 'BKR': 'Energy', 'KMI': 'Energy',
    'FANG': 'Energy', 'PXD': 'Energy', 'TRGP': 'Energy', 'OKE': 'Energy', 'ET': 'Energy',
    # Consumer Discretionary
    'AMZN': 'Cons', 'TSLA': 'Cons', 'HD': 'Cons', 'MCD': 'Cons', 'NKE': 'Cons',
    'LOW': 'Cons', 'SBUX': 'Cons', 'TJX': 'Cons', 'BKNG': 'Cons', 'CMG': 'Cons',
    'ORLY': 'Cons', 'AZO': 'Cons', 'ROST': 'Cons', 'DHI': 'Cons', 'LEN': 'Cons',
    'GM': 'Cons', 'F': 'Cons', 'MAR': 'Cons', 'HLT': 'Cons', 'YUM': 'Cons',
    'DG': 'Cons', 'DLTR': 'Cons', 'BBY': 'Cons', 'ULTA': 'Cons', 'POOL': 'Cons',
    'LULU': 'Cons',
    # Consumer Staples
    'WMT': 'Staple', 'PG': 'Staple', 'COST': 'Staple', 'KO': 'Staple', 'PEP': 'Staple',
    'PM': 'Staple', 'MDLZ': 'Staple', 'MO': 'Staple', 'CL': 'Staple', 'KMB': 'Staple',
    'GIS': 'Staple', 'K': 'Staple', 'HSY': 'Staple', 'SYY': 'Staple', 'STZ': 'Staple',
    'KHC': 'Staple', 'KR': 'Staple', 'EL': 'Staple', 'CHD': 'Staple', 'CLX': 'Staple',
    'KDP': 'Staple', 'TAP': 'Staple', 'ADM': 'Staple', 'BG': 'Staple', 'MNST': 'Staple',
    # Industrials
    'CAT': 'Indust', 'GE': 'Indust', 'RTX': 'Indust', 'HON': 'Indust', 'UNP': 'Indust',
    'BA': 'Indust', 'DE': 'Indust', 'LMT': 'Indust', 'UPS': 'Indust', 'MMM': 'Indust',
    'GD': 'Indust', 'NOC': 'Indust', 'CSX': 'Indust', 'NSC': 'Indust', 'WM': 'Indust',
    'EMR': 'Indust', 'ETN': 'Indust', 'ITW': 'Indust', 'PH': 'Indust', 'ROK': 'Indust',
    'FDX': 'Indust', 'CARR': 'Indust', 'TT': 'Indust', 'PCAR': 'Indust', 'FAST': 'Indust',
    # Materials
    'LIN': 'Mater', 'APD': 'Mater', 'SHW': 'Mater', 'FCX': 'Mater', 'ECL': 'Mater',
    'NEM': 'Mater', 'NUE': 'Mater', 'DOW': 'Mater', 'DD': 'Mater', 'VMC': 'Mater',
    'CTVA': 'Mater', 'PPG': 'Mater', 'MLM': 'Mater', 'IP': 'Mater', 'PKG': 'Mater',
    'ALB': 'Mater', 'GOLD': 'Mater', 'FMC': 'Mater', 'CF': 'Mater', 'MOS': 'Mater',
    # Utilities
    'NEE': 'Util', 'SO': 'Util', 'DUK': 'Util', 'CEG': 'Util', 'SRE': 'Util',
    'AEP': 'Util', 'D': 'Util', 'PCG': 'Util', 'EXC': 'Util', 'XEL': 'Util',
    'ED': 'Util', 'WEC': 'Util', 'ES': 'Util', 'AWK': 'Util', 'DTE': 'Util',
    # Real Estate
    'PLD': 'REIT', 'AMT': 'REIT', 'EQIX': 'REIT', 'SPG': 'REIT', 'PSA': 'REIT',
    'O': 'REIT', 'WELL': 'REIT', 'DLR': 'REIT', 'CCI': 'REIT', 'AVB': 'REIT',
    'CBRE': 'REIT', 'SBAC': 'REIT', 'WY': 'REIT', 'EQR': 'REIT', 'VTR': 'REIT',
    # Communication Services
    'META': 'Comm', 'GOOGL': 'Comm', 'GOOG': 'Comm', 'NFLX': 'Comm', 'DIS': 'Comm',
    'T': 'Comm', 'VZ': 'Comm', 'CMCSA': 'Comm', 'TMUS': 'Comm', 'CHTR': 'Comm',
    'EA': 'Comm', 'TTWO': 'Comm', 'RBLX': 'Comm', 'PARA': 'Comm', 'WBD': 'Comm',
    'MTCH': 'Comm', 'LYV': 'Comm', 'OMC': 'Comm', 'IPG': 'Comm', 'FOXA': 'Comm',
    'EPAM': 'Tech', 'ALGN': 'Health',
}

# Data directory
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# Persistent sector cache file
SECTOR_CACHE_FILE = os.path.join(DATA_DIR, 'sector_cache.json')

def _load_sector_cache() -> dict:
    """Load sector cache from file"""
    try:
        if os.path.exists(SECTOR_CACHE_FILE):
            with open(SECTOR_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {}

def _save_sector_cache(cache: dict):
    """Save sector cache to file"""
    try:
        os.makedirs(os.path.dirname(SECTOR_CACHE_FILE), exist_ok=True)
        with open(SECTOR_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving sector cache: {e}")

# Load cache at startup
_sector_cache = _load_sector_cache()

def get_sector(ticker: str) -> str:
    """Get sector for a ticker, auto-fetch from yfinance if not in SECTOR_MAP"""
    global _sector_cache
    
    if ticker in SECTOR_MAP:
        return SECTOR_MAP[ticker]
    
    if ticker in _sector_cache:
        return _sector_cache[ticker]
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        sector = info.get('sector', '')
        
        sector_short_map = {
            'Technology': 'Tech', 'Information Technology': 'Tech',
            'Healthcare': 'Health', 'Health Care': 'Health',
            'Financials': 'Fin', 'Financial Services': 'Fin',
            'Consumer Discretionary': 'Cons', 'Consumer Cyclical': 'Cons',
            'Consumer Staples': 'Staple', 'Consumer Defensive': 'Staple',
            'Energy': 'Energy', 'Industrials': 'Indust',
            'Materials': 'Mater', 'Basic Materials': 'Mater',
            'Utilities': 'Util', 'Real Estate': 'REIT',
            'Communication Services': 'Comm',
        }
        
        short_sector = sector_short_map.get(sector, sector[:5] if sector else '-')
        _sector_cache[ticker] = short_sector
        _save_sector_cache(_sector_cache)
        print(f"✅ Cached sector for {ticker}: {short_sector}")
        return short_sector
    except Exception as e:
        print(f"Error fetching sector for {ticker}: {e}")
        _sector_cache[ticker] = '-'
        _save_sector_cache(_sector_cache)
        return '-'

# ... (existing imports)

# Global update lock/status
is_updating = False
last_update_check = datetime.min

def run_update_background():
    """Runs the update script in a background thread"""
    global is_updating
    if is_updating:
        print("⚠️ Update already in progress")
        return

    is_updating = True
    print("🔄 Starting background data update (Quick Mode)...")
    
    def target():
        global is_updating
        try:
            # Use absolute path to script
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts', 'update_all.py')
            result = subprocess.run([sys.executable, script_path, '--quick'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Background update completed successfully")
            else:
                print(f"❌ Background update failed: {result.stderr[:200]}")
        except Exception as e:
            print(f"❌ Background update error: {e}")
        finally:
            is_updating = False

    thread = threading.Thread(target=target)
    thread.daemon = True # Allow app to exit even if thread is running
    thread.start()

def check_data_freshness():
    """Checks if data is stale and triggers update if needed"""
    global last_update_check
    
    # Only check once every 5 minutes to avoid file I/O spam
    if (datetime.now() - last_update_check).total_seconds() < 300:
        return

    last_update_check = datetime.now()
    
    try:
        target_file = os.path.join(DATA_DIR, 'smart_money_current.json')
        should_update = False
        
        if not os.path.exists(target_file):
            should_update = True
        else:
            mtime = datetime.fromtimestamp(os.path.getmtime(target_file))
            age = datetime.now() - mtime
            
            # If older than 6 hours and it's a weekday
            if age.total_seconds() > 6 * 3600 and datetime.now().weekday() < 5:
                should_update = True
                print(f"📉 Data is stale ({age.total_seconds()/3600:.1f} hours old). Triggering update.")

        if should_update and not is_updating:
            run_update_background()
            
    except Exception as e:
        print(f"⚠️ Freshness check error: {e}")

@app.before_request
def trigger_check():
    # Check freshness on every request (rate limited internally)
    if request.path.startswith('/api/us/smart-money'):
        check_data_freshness()

@app.route('/api/refresh-data', methods=['POST'])
def manual_refresh_data():
    """수동 데이터 갱신 API (관리자용)"""
    try:
        if is_updating:
            return jsonify({'status': 'already_running', 'message': '이미 업데이트 중입니다.'})
        
        run_update_background()
        return jsonify({
            'status': 'started',
            'message': '백그라운드 데이터 갱신이 시작되었습니다.',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/health')
def health_check():
    """서버 상태 확인 API"""
    return jsonify({
        'status': 'ok',
        'service': 'US Market Dashboard',
        'version': '2.0.2',
        'is_updating': is_updating,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/')
def index():
    check_data_freshness() # Also check on homepage load
    return render_template('index.html')

# ==================== KR Market APIs (placeholder - redirects to US) ====================

@app.route('/api/portfolio')
def get_kr_portfolio():
    """KR Market Portfolio - Returns US market data as placeholder"""
    try:
        market_indices = []
        # Korean market indices (using Yahoo Finance tickers)
        indices_map = {
            '^KS11': 'KOSPI', '^KQ11': 'KOSDAQ', '^KS200': 'KOSPI200',
            '005930.KS': 'Samsung', '000660.KS': 'SK Hynix',
            'KRW=X': 'USD/KRW', '^DJI': 'Dow Jones', '^GSPC': 'S&P 500'
        }
        
        for ticker, name in indices_map.items():
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period='5d')
                if not hist.empty and len(hist) >= 2:
                    current_val = float(hist['Close'].iloc[-1])
                    prev_val = float(hist['Close'].iloc[-2])
                    change = current_val - prev_val
                    change_pct = (change / prev_val) * 100
                    market_indices.append({
                        'name': name, 'ticker': ticker,
                        'price': f"{current_val:,.2f}",
                        'change': f"{change:+,.2f}",
                        'change_pct': round(change_pct, 2),
                        'color': 'red' if change_pct >= 0 else 'blue'
                    })
            except Exception as e:
                print(f"Error fetching {ticker}: {e}")
        
        # Placeholder for KR stock picks
        return jsonify({
            'market_indices': market_indices,
            'top_holdings': [],
            'style_box': {
                'large_value': 15, 'large_core': 25, 'large_growth': 20,
                'mid_value': 10, 'mid_core': 10, 'mid_growth': 10,
                'small_value': 3, 'small_core': 4, 'small_growth': 3
            }
        })
    except Exception as e:
        print(f"Error getting KR portfolio: {e}")
        return jsonify({'error': str(e), 'market_indices': [], 'top_holdings': []}), 500

# ==================== US Market APIs ====================

@app.route('/api/us/portfolio')
def get_us_portfolio_data():
    """US Market Portfolio Data - Market Indices"""
    try:
        market_indices = []
        indices_map = {
            '^DJI': 'Dow Jones', '^GSPC': 'S&P 500', '^IXIC': 'NASDAQ',
            '^RUT': 'Russell 2000', '^VIX': 'VIX', 'GC=F': 'Gold',
            'CL=F': 'Crude Oil', 'BTC-USD': 'Bitcoin', '^TNX': '10Y Treasury',
            'DX-Y.NYB': 'Dollar Index', 'KRW=X': 'USD/KRW'
        }
        
        for ticker, name in indices_map.items():
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period='5d')
                if not hist.empty and len(hist) >= 2:
                    current_val = float(hist['Close'].iloc[-1])
                    prev_val = float(hist['Close'].iloc[-2])
                    change = current_val - prev_val
                    change_pct = (change / prev_val) * 100
                    market_indices.append({
                        'name': name, 'price': f"{current_val:,.2f}",
                        'change': f"{change:+,.2f}", 'change_pct': round(change_pct, 2),
                        'color': 'green' if change >= 0 else 'red'
                    })
                elif not hist.empty:
                    current_val = float(hist['Close'].iloc[-1])
                    market_indices.append({
                        'name': name, 'price': f"{current_val:,.2f}",
                        'change': "0.00", 'change_pct': 0, 'color': 'gray'
                    })
            except Exception as e:
                print(f"Error fetching {ticker} ({name}): {e}")

        return jsonify({'market_indices': market_indices, 'top_holdings': [], 'style_box': {}})
    except Exception as e:
        print(f"Error getting US portfolio data: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/us/smart-money')
def get_us_smart_money():
    """Get Smart Money Picks with performance tracking"""
    try:
        import math
        current_file = os.path.join(DATA_DIR, 'smart_money_current.json')
        
        if os.path.exists(current_file):
            with open(current_file, 'r', encoding='utf-8') as f:
                snapshot = json.load(f)
            
            tickers = [p['ticker'] for p in snapshot['picks']]
            current_prices = {}
            
            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period='5d')
                    if not hist.empty:
                        current_prices[ticker] = round(float(hist['Close'].dropna().iloc[-1]), 2)
                except Exception as e:
                    print(f"Error fetching price for {ticker}: {e}")
            
            picks_with_perf = []
            for pick in snapshot['picks']:
                ticker = pick['ticker']
                price_at_rec = pick.get('price_at_analysis', 0) or 0
                current_price = current_prices.get(ticker, price_at_rec) or price_at_rec or 0
                
                if isinstance(price_at_rec, float) and math.isnan(price_at_rec):
                    price_at_rec = 0
                if isinstance(current_price, float) and math.isnan(current_price):
                    current_price = price_at_rec
                
                change_pct = ((current_price / price_at_rec) - 1) * 100 if price_at_rec > 0 else 0
                if isinstance(change_pct, float) and math.isnan(change_pct):
                    change_pct = 0
                
                picks_with_perf.append({
                    **pick, 'sector': get_sector(ticker),
                    'current_price': round(current_price, 2),
                    'price_at_rec': round(price_at_rec, 2),
                    'change_since_rec': round(change_pct, 2)
                })
            
            # Use file modification time as fallback for missing timestamps
            analysis_date = snapshot.get('analysis_date', '')
            analysis_timestamp = snapshot.get('analysis_timestamp', '')
            
            if not analysis_date or not analysis_timestamp:
                file_mtime = datetime.fromtimestamp(os.path.getmtime(current_file))
                if not analysis_date:
                    analysis_date = file_mtime.strftime('%Y-%m-%d')
                if not analysis_timestamp:
                    analysis_timestamp = file_mtime.isoformat()
            
            return jsonify({
                'analysis_date': analysis_date,
                'analysis_timestamp': analysis_timestamp,
                'top_picks': picks_with_perf,
                'summary': {
                    'total_analyzed': len(picks_with_perf),
                    'avg_score': round(sum(p['final_score'] for p in picks_with_perf) / len(picks_with_perf), 1) if picks_with_perf else 0
                }
            })
        
        # Fallback to CSV
        csv_path = os.path.join(DATA_DIR, 'smart_money_picks_v2.csv')
        if not os.path.exists(csv_path):
            csv_path = os.path.join(DATA_DIR, 'smart_money_picks.csv')
        
        if not os.path.exists(csv_path):
            return jsonify({'error': 'Smart money picks not found. Run screener first.'}), 404
        
        df = pd.read_csv(csv_path)
        tickers = df['ticker'].head(20).tolist()
        current_prices = {}
        
        try:
            price_data = yf.download(tickers, period='1d', progress=False)
            if not price_data.empty:
                closes = price_data['Close']
                for ticker in tickers:
                    try:
                        if isinstance(closes, pd.DataFrame) and ticker in closes.columns:
                            val = closes[ticker].iloc[-1]
                        elif isinstance(closes, pd.Series):
                            val = closes.iloc[-1]
                        else:
                            val = 0
                        current_prices[ticker] = round(float(val), 2) if not (isinstance(val, float) and math.isnan(val)) else 0
                    except:
                        current_prices[ticker] = 0
        except Exception as e:
            print(f"Error fetching US real-time prices: {e}")
        
        top_picks = []
        for _, row in df.head(20).iterrows():
            ticker = row['ticker']
            rec_price = row.get('current_price', 0) or 0
            cur_price = current_prices.get(ticker, rec_price) or rec_price
            change_pct = ((cur_price / rec_price) - 1) * 100 if rec_price > 0 else 0
            
            top_picks.append({
                'ticker': ticker, 'name': row.get('name', ticker),
                'sector': get_sector(ticker),
                'final_score': row.get('smart_money_score', row.get('composite_score', 0)),
                'current_price': round(cur_price, 2), 'price_at_rec': round(rec_price, 2),
                'change_since_rec': round(change_pct, 2),
                'category': row.get('category', 'N/A'),
                'volume_stage': row.get('volume_stage', 'N/A'),
                'insider_score': row.get('insider_score', 0),
                'avg_surprise': row.get('avg_surprise', 0)
            })
        
        return jsonify({
            'top_picks': top_picks,
            'summary': {
                'total_analyzed': len(df),
                'avg_score': round(df['smart_money_score'].mean() if 'smart_money_score' in df.columns else 0, 1)
            }
        })
    except Exception as e:
        print(f"Error getting smart money picks: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/us/etf-flows')
def get_us_etf_flows():
    """Get ETF Fund Flow Analysis"""
    try:
        # Try JSON file first (has full analysis)
        json_path = os.path.join(DATA_DIR, 'etf_flow_analysis.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return jsonify({
                    'market_sentiment_score': 55,
                    'top_inflows': data.get('top_inflows', []),
                    'top_outflows': data.get('top_outflows', []),
                    'ai_analysis': data.get('ai_analysis', ''),
                    'summary': data.get('summary', {}),
                    'timestamp': data.get('timestamp', '')
                })
        
        # Fallback to CSV
        csv_path = os.path.join(DATA_DIR, 'us_etf_flows.csv')
        if not os.path.exists(csv_path):
            return jsonify({'error': 'ETF flows not found. Run analyze_etf_flows.py first.'}), 404
        
        df = pd.read_csv(csv_path)
        top_inflows = df.nlargest(5, 'flow_score').to_dict(orient='records')
        top_outflows = df.nsmallest(5, 'flow_score').to_dict(orient='records')
        return jsonify({
            'market_sentiment_score': 50,
            'top_inflows': top_inflows,
            'top_outflows': top_outflows,
            'ai_analysis': ''
        })
    except Exception as e:
        print(f"Error getting ETF flows: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/us/stock-chart/<ticker>')
def get_us_stock_chart(ticker):
    """Get US stock chart data (OHLC) for candlestick chart"""
    try:
        period = request.args.get('period', '1y')
        valid_periods = ['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max']
        if period not in valid_periods:
            period = '1y'
        
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        if hist.empty:
            return jsonify({'error': f'No data found for {ticker}'}), 404
        
        candles = [{'time': int(date.timestamp()), 'open': round(row['Open'], 2),
                    'high': round(row['High'], 2), 'low': round(row['Low'], 2),
                    'close': round(row['Close'], 2)} for date, row in hist.iterrows()]
        return jsonify({'ticker': ticker, 'period': period, 'candles': candles})
    except Exception as e:
        print(f"Error getting US stock chart for {ticker}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/us/history-dates')
def get_us_history_dates():
    """Get list of available historical analysis dates"""
    try:
        history_dir = os.path.join(DATA_DIR, 'history')
        if not os.path.exists(history_dir):
            return jsonify({'dates': []})
        dates = [f[6:-5] for f in os.listdir(history_dir) if f.startswith('picks_') and f.endswith('.json')]
        dates.sort(reverse=True)
        return jsonify({'dates': dates, 'count': len(dates)})
    except Exception as e:
        print(f"Error getting history dates: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/us/history/<date>')
def get_us_history_by_date(date):
    """Get picks from a specific historical date with current performance"""
    try:
        import math
        history_file = os.path.join(DATA_DIR, 'history', f'picks_{date}.json')
        if not os.path.exists(history_file):
            return jsonify({'error': f'No analysis found for {date}'}), 404
        
        with open(history_file, 'r', encoding='utf-8') as f:
            snapshot = json.load(f)
        
        tickers = [p['ticker'] for p in snapshot['picks']]
        current_prices = {}
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period='5d')
                if not hist.empty:
                    current_prices[ticker] = round(float(hist['Close'].dropna().iloc[-1]), 2)
            except Exception as e:
                print(f"Error fetching price for {ticker}: {e}")
        
        picks_with_perf = []
        for pick in snapshot['picks']:
            ticker = pick['ticker']
            price_at_rec = pick.get('price_at_analysis', 0) or 0
            current_price = current_prices.get(ticker, price_at_rec) or price_at_rec
            
            if isinstance(price_at_rec, float) and math.isnan(price_at_rec):
                price_at_rec = 0
            if isinstance(current_price, float) and math.isnan(current_price):
                current_price = price_at_rec
            
            change_pct = ((current_price / price_at_rec) - 1) * 100 if price_at_rec > 0 else 0
            if isinstance(change_pct, float) and math.isnan(change_pct):
                change_pct = 0
            
            picks_with_perf.append({
                **pick, 'sector': get_sector(ticker),
                'current_price': round(current_price, 2),
                'price_at_rec': round(price_at_rec, 2),
                'change_since_rec': round(change_pct, 2)
            })
        
        changes = [p['change_since_rec'] for p in picks_with_perf if p['price_at_rec'] > 0]
        avg_perf = round(sum(changes) / len(changes), 2) if changes else 0
        
        return jsonify({
            'analysis_date': snapshot.get('analysis_date', date),
            'analysis_timestamp': snapshot.get('analysis_timestamp', ''),
            'top_picks': picks_with_perf,
            'summary': {'total': len(picks_with_perf), 'avg_performance': avg_perf}
        })
    except Exception as e:
        print(f"Error getting history for {date}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/us/macro-analysis')
def get_us_macro_analysis():
    """Get macro market analysis with live indicators + cached AI predictions"""
    try:
        lang = request.args.get('lang', 'ko')
        model = request.args.get('model', 'gemini')
        macro_indicators = {}
        
        # Determine analysis file path
        if model == 'gpt':
            analysis_path = os.path.join(DATA_DIR, f'macro_analysis_gpt{"_en" if lang == "en" else ""}.json')
            if not os.path.exists(analysis_path):
                analysis_path = os.path.join(DATA_DIR, f'macro_analysis{"_en" if lang == "en" else ""}.json')
        else:
            analysis_path = os.path.join(DATA_DIR, f'macro_analysis{"_en" if lang == "en" else ""}.json')
        
        if not os.path.exists(analysis_path):
            analysis_path = os.path.join(DATA_DIR, 'macro_analysis.json')
        
        ai_analysis = "AI 분석을 로드할 수 없습니다. macro_analyzer.py를 실행하세요."
        
        if os.path.exists(analysis_path):
            with open(analysis_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
                # Try different key names based on language
                if lang == 'en':
                    ai_analysis = cached.get('analysis_en', cached.get('ai_analysis', ai_analysis))
                else:
                    ai_analysis = cached.get('analysis_ko', cached.get('ai_analysis', ai_analysis))
                
                # Handle "Analysis failed" case
                if ai_analysis == "Analysis failed":
                    ai_analysis = "매크로 분석 생성 중 오류가 발생했습니다. API 키를 확인하고 다시 실행하세요."
                
                # Read indicators (different key name in file)
                macro_indicators = cached.get('indicators', cached.get('macro_indicators', {}))
        
        # Update key indicators with live data
        live_tickers = {
            'VIX': '^VIX', 'SPY': 'SPY', 'QQQ': 'QQQ',
            'BTC': 'BTC-USD', 'GOLD': 'GC=F', 'USD/KRW': 'KRW=X'
        }
        
        try:
            import time as t
            for name, ticker in live_tickers.items():
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period='5d')
                    if not hist.empty and len(hist) >= 2:
                        current = float(hist['Close'].iloc[-1])
                        prev = float(hist['Close'].iloc[-2])
                        change_pct = ((current - prev) / prev) * 100 if prev != 0 else 0
                        macro_indicators[name] = {'current': round(current, 2), 'change_1d': round(change_pct, 2)}
                    t.sleep(0.3)
                except Exception as e:
                    print(f"Error fetching live {name}: {e}")
        except Exception as e:
            print(f"Error in live data loop: {e}")
        
        return jsonify({
            'macro_indicators': macro_indicators, 'ai_analysis': ai_analysis,
            'model': model, 'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Error getting macro analysis: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/us/sector-heatmap')
def get_us_sector_heatmap():
    """Get sector performance data for heatmap visualization"""
    try:
        heatmap_path = os.path.join(DATA_DIR, 'market_treemap.json')
        if os.path.exists(heatmap_path):
            with open(heatmap_path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        return jsonify({'series': []})
    except Exception as e:
        print(f"Error getting sector heatmap: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/us/risk')
def get_us_risk_analysis():
    """Get portfolio risk metrics and correlation matrix"""
    try:
        risk_path = os.path.join(DATA_DIR, 'portfolio_risk.json')
        if os.path.exists(risk_path):
            with open(risk_path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        return jsonify({'error': 'Risk analysis not found'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/us/corporate-events')
def get_us_corporate_events():
    """Get earnings calendar and news"""
    try:
        path = os.path.join(DATA_DIR, 'news_events.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        return jsonify({'error': 'Data not found'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/us/historical-returns')
def get_us_historical_returns():
    """Get historical monthly returns heatmap data"""
    try:
        hist_path = os.path.join(DATA_DIR, 'historical_returns.json')
        if os.path.exists(hist_path):
            with open(hist_path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        return jsonify({'error': 'Historical returns data not found'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/us/options-flow')
def get_us_options_flow():
    """Get options flow data"""
    try:
        flow_path = os.path.join(DATA_DIR, 'options_flow.json')
        if not os.path.exists(flow_path):
            return jsonify({'error': 'Options flow data not found. Run options_flow.py first.'}), 404
        with open(flow_path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        print(f"Error getting options flow: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/us/ai-summary/<ticker>')
def get_us_ai_summary(ticker):
    """Get AI-generated summary for a US stock - with real-time generation fallback"""
    try:
        lang = request.args.get('lang', 'ko')
        summary_path = os.path.join(DATA_DIR, 'ai_summaries.json')
        
        # Try cached file first
        if os.path.exists(summary_path):
            with open(summary_path, 'r', encoding='utf-8') as f:
                summaries = json.load(f)
            if ticker in summaries:
                summary_data = summaries[ticker]
                # Handle both string and dict formats
                if isinstance(summary_data, str):
                    summary = summary_data
                    return jsonify({
                        'ticker': ticker, 'summary': summary, 'lang': lang,
                        'news_count': 0, 'updated': ''
                    })
                elif isinstance(summary_data, dict):
                    if lang == 'en':
                        summary = summary_data.get('summary_en', summary_data.get('summary', ''))
                    else:
                        summary = summary_data.get('summary_ko', summary_data.get('summary', ''))
                    return jsonify({
                        'ticker': ticker, 'summary': summary, 'lang': lang,
                        'news_count': summary_data.get('news_count', 0),
                        'updated': summary_data.get('updated', '')
                    })
        # Stock data for AI analysis
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period='3mo')
        
        if not hist.empty:
            current_price = round(hist['Close'].iloc[-1], 2)
            price_1m = round(hist['Close'].iloc[-22] if len(hist) > 22 else hist['Close'].iloc[0], 2)
            change_1m = round((current_price - price_1m) / price_1m * 100, 2) if price_1m > 0 else 0
        else:
            current_price, price_1m, change_1m = 0, 0, 0
        
        prompt = f"""당신은 미국 주식 전문 애널리스트입니다. 다음 종목에 대해 간단한 투자 분석을 제공해주세요.

종목: {ticker} ({info.get('longName', ticker)})
현재가: ${current_price}
1개월 수익률: {change_1m}%
섹터: {info.get('sector', 'N/A')}
시가총액: {info.get('marketCap', 'N/A')}
PER: {info.get('trailingPE', 'N/A')}

200자 이내로 간략하게 분석해주세요. {'영어로 작성해주세요.' if lang == 'en' else '한국어로 작성해주세요.'}"""

        # Try Gemini first
        if GEMINI_MODEL:
            try:
                response = GEMINI_MODEL.generate_content(prompt)
                return jsonify({
                    'ticker': ticker, 'summary': response.text, 'lang': lang,
                    'model': 'gemini', 'generated': True, 'updated': datetime.now().isoformat()
                })
            except Exception as e:
                print(f"Gemini API error: {e}")
                # Fall through to OpenAI
        
        # Fallback to OpenAI
        if OPENAI_CLIENT:
            try:
                response = OPENAI_CLIENT.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500
                )
                return jsonify({
                    'ticker': ticker, 'summary': response.choices[0].message.content, 'lang': lang,
                    'model': 'openai', 'generated': True, 'updated': datetime.now().isoformat()
                })
            except Exception as e:
                print(f"OpenAI API error: {e}")
                return jsonify({'error': f'AI analysis unavailable: {str(e)}'}), 500
        
        return jsonify({'error': 'No AI model configured'}), 500

    except Exception as e:
        print(f"Error getting AI summary: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/us/market-gate')
def get_us_market_gate():
    """Get Market Gate Status (Risk On/Off)"""
    try:
        gate_path = os.path.join(DATA_DIR, 'market_gate.json')
        if not os.path.exists(gate_path):
            # Try running the script if file doesn't exist
            try:
                from scripts.market_gate_manager import MarketGateManager
                MarketGateManager().run_analysis()
            except ImportError:
                # If cannot import (e.g. running from root), try subprocess or just fail gracefully
                pass
        
        if os.path.exists(gate_path):
            with open(gate_path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        
        return jsonify({'gate': 'UNKNOWN', 'score': 50, 'reasons': ['Data not available']})
    except Exception as e:
        print(f"Error getting Market Gate: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/us/lead-lag')
def get_us_lead_lag():
    """Get Lead-Lag Analysis Results"""
    try:
        path = os.path.join(DATA_DIR, 'lead_lag_analysis.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        return jsonify({'analysis': [], 'summary': 'No analysis found'})
    except Exception as e:
        print(f"Error getting Lead-Lag: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/us/vcp-candidates')
def get_us_vcp_candidates():
    """Get VCP Screener Results"""
    try:
        path = os.path.join(DATA_DIR, 'vcp_candidates.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        return jsonify({'candidates': [], 'count': 0})
    except Exception as e:
        print(f"Error getting VCP candidates: {e}")
        return jsonify({'error': str(e)}), 500
        
        return jsonify({'error': 'No AI API available. Configure Gemini or OpenAI API key.'}), 404
    except Exception as e:
        print(f"Error getting AI summary for {ticker}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/us/calendar')
def get_us_calendar():
    """Get Weekly Economic Calendar"""
    try:
        calendar_path = os.path.join(DATA_DIR, 'weekly_calendar.json')
        if not os.path.exists(calendar_path):
            return jsonify({'events': [], 'message': 'Calendar data not available'}), 404
        with open(calendar_path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/us/technical-indicators/<ticker>')
def get_technical_indicators(ticker):
    """Get technical indicators (RSI, MACD, Bollinger Bands, Support/Resistance)"""
    try:
        period = request.args.get('period', '1y')
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        if hist.empty:
            return jsonify({'error': f'No data found for {ticker}'}), 404
        
        df = hist.reset_index()
        close = df['Close']
        high = df['High']
        low = df['Low']
        
        # RSI (14-period)
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD (12, 26, 9)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df['macd_line'] = ema12 - ema26
        df['signal_line'] = df['macd_line'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd_line'] - df['signal_line']
        
        # Bollinger Bands (20-period, 2 std)
        df['bb_middle'] = close.rolling(20).mean()
        std = close.rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * std
        df['bb_lower'] = df['bb_middle'] - 2 * std
        
        # Support & Resistance
        def find_support_resistance(df, window=20):
            supports, resistances = [], []
            for i in range(window, len(df) - window):
                low_window = low.iloc[i-window:i+window+1]
                high_window = high.iloc[i-window:i+window+1]
                if low.iloc[i] == low_window.min():
                    supports.append(float(low.iloc[i]))
                if high.iloc[i] == high_window.max():
                    resistances.append(float(high.iloc[i]))
            
            def cluster_levels(levels, threshold=0.02):
                if not levels:
                    return []
                levels = sorted(levels)
                clusters = []
                current_cluster = [levels[0]]
                for level in levels[1:]:
                    if (level - current_cluster[0]) / current_cluster[0] < threshold:
                        current_cluster.append(level)
                    else:
                        clusters.append(sum(current_cluster) / len(current_cluster))
                        current_cluster = [level]
                clusters.append(sum(current_cluster) / len(current_cluster))
                return [round(c, 2) for c in clusters[-5:]]
            
            return cluster_levels(supports), cluster_levels(resistances)
        
        supports, resistances = find_support_resistance(df)
        
        def make_series(dates, values):
            return [{'time': int(d.timestamp()), 'value': round(float(v), 2)} 
                    for d, v in zip(dates, values) if pd.notna(v)]
        
        return jsonify({
            'ticker': ticker,
            'rsi': make_series(df['Date'], df['rsi']),
            'macd': {
                'macd_line': make_series(df['Date'], df['macd_line']),
                'signal_line': make_series(df['Date'], df['signal_line']),
                'histogram': make_series(df['Date'], df['macd_histogram'])
            },
            'bollinger': {
                'upper': make_series(df['Date'], df['bb_upper']),
                'middle': make_series(df['Date'], df['bb_middle']),
                'lower': make_series(df['Date'], df['bb_lower'])
            },
            'support_resistance': {'support': supports, 'resistance': resistances}
        })
    except Exception as e:
        print(f"Error getting technical indicators for {ticker}: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/run-analysis', methods=['POST'])
def run_analysis():
    """Run analysis scripts in background"""
    try:
        def run_scripts():
            print("🚀 Starting Analysis...")
            try:
                subprocess.run(['python3', 'scripts/update_all.py'], check=True, cwd=os.path.dirname(__file__))
                print("✅ Analysis Complete.")
            except Exception as e:
                print(f"❌ Error running scripts: {e}")
        
        thread = threading.Thread(target=run_scripts)
        thread.start()
        return jsonify({'status': 'started', 'message': 'Analysis started in background.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print('🚀 Flask Server Starting on port 5001...')
    app.run(port=5001, debug=True, use_reloader=False)
