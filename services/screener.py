# services/screener.py
import requests
import config
import logging
import random
import time

logger = logging.getLogger(__name__)

class BithumbScreener:
    @staticmethod
    def get_realtime_momentum(limit=20):
        """
        [SYNC MODE - STABILITY FIRST]
        Fetch 30m candles for top 15 coins using standard Requests.
        Slower, but crashes are impossible.
        """
        try:
            # 1. Base List
            url_all = f"{config.BITHUMB_API_URL}/ticker/ALL_KRW"
            res = requests.get(url_all, timeout=2).json()
            
            candidates = []
            for k, v in res['data'].items():
                if k == 'date': continue
                candidates.append({
                    "symbol": k,
                    "vol": float(v['acc_trade_value_24H']),
                    "price": float(v['closing_price'])
                })
            
            # Reduce Count to 15 to prevent Timeout during Sync Fetch
            candidates.sort(key=lambda x: x['vol'], reverse=True)
            targets = candidates[:15]
            
            results = []
            headers = {"User-Agent": "Mozilla/5.0"}
            
            for coin in targets:
                try:
                    # Sync Request
                    url = f"{config.BITHUMB_API_URL}/candlestick/{coin['symbol']}_KRW/30m"
                    resp = requests.get(url, headers=headers, timeout=0.5)
                    
                    if resp.status_code == 200:
                        r_json = resp.json()
                        if r_json['status'] == '0000':
                            candles = r_json['data'][-3:] 
                            start_p = float(candles[0][1])
                            end_p = float(candles[-1][2])
                            mom = ((end_p - start_p) / start_p) * 100
                            coin['momentum'] = mom
                            results.append(coin)
                except:
                    continue
            
            results.sort(key=lambda x: abs(x['momentum']), reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Screener Error: {e}")
            return []

    # Wrapper for Sync Call
    @staticmethod
    def get_rankings(category="surge"):
        pass
