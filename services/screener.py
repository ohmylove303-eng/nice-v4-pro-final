# services/screener.py
import requests
import config

class BithumbScreener:
    @staticmethod
    def get_rankings(category="surge"):
        try:
            url = f"{config.BITHUMB_API_URL}/ticker/ALL_KRW"
            res = requests.get(url, timeout=2).json()
            
            if res['status'] != '0000': return []
            
            data = []
            for k, v in res['data'].items():
                if k == 'date': continue
                
                price = float(v['closing_price'])
                chg_amt = float(v['fluctate_24H'])
                chg_rate = float(v['fluctate_rate_24H'])
                vol_amt = float(v['acc_trade_value_24H'])
                
                data.append({
                    "symbol": k,
                    "price": price,
                    "change": chg_rate,
                    "volume": vol_amt
                })
            
            # SORTING LOGIC based on User's "Grand Principles"
            # 1. Surge (Variation): High Change + Minimum Volume (Avoid dead coins)
            if category == "surge":
                # Filter: Min Volume 1B KRW (to avoid fake 100% pumps on dead coins)
                candidates = [d for d in data if d['volume'] > 1000000000]
                candidates.sort(key=lambda x: x['change'], reverse=True)
                return candidates[:20]
            
            # 2. Major/Volume (Liquidity): High Volume
            elif category == "volume" or category == "majors":
                data.sort(key=lambda x: x['volume'], reverse=True)
                return data[:20]
                
            # 3. Scalp (High Volatility + High Volume Intersection)
            elif category == "scalping":
                # Score = Norm(Vol) * Norm(Abs(Change))
                # Simple Proxy: Top 30 Vol -> Sort by Abs Change
                top_vol = sorted(data, key=lambda x: x['volume'], reverse=True)[:50]
                top_vol.sort(key=lambda x: abs(x['change']), reverse=True)
                return top_vol[:20]
                
            return []
            
        except Exception as e:
            print(f"Screener Error: {e}")
            return []
