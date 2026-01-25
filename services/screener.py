# services/screener.py
import requests
import asyncio
import aiohttp
import config
import logging
import pandas as pd

logger = logging.getLogger(__name__)

class BithumbScreener:
    @staticmethod
    async def get_realtime_momentum(limit=20):
        """
        [TRUE SCALP LOGIC]
        1. Get Top 40 Volume Coins (Liquid enough to trade).
        2. Async Fetch '30m Candles' for ALL of them.
        3. Rank by 'Last 3 Candle Volatility' (Real-time movement).
        """
        try:
            # 1. Base List (Liquidity Filter)
            url_all = f"{config.BITHUMB_API_URL}/ticker/ALL_KRW"
            async with aiohttp.ClientSession() as session:
                async with session.get(url_all) as resp:
                    data = await resp.json()
            
            candidates = []
            for k, v in data['data'].items():
                if k == 'date': continue
                candidates.append({
                    "symbol": k,
                    "vol": float(v['acc_trade_value_24H']),
                    "price": float(v['closing_price'])
                })
            
            # Liquidity Cut: Top 40
            candidates.sort(key=lambda x: x['vol'], reverse=True)
            targets = candidates[:40]
            
            # 2. Deep Scan (Fetch 30m Candles)
            async def get_momentum(coin):
                try:
                    url = f"{config.BITHUMB_API_URL}/candlestick/{coin['symbol']}_KRW/30m"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as resp:
                            res = await resp.json()
                            if res['status'] != '0000': return None
                            
                            # Get last 3 candles
                            candles = res['data'][-3:] 
                            # Calc Momentum: (LastClose - 3rdOpen) / 3rdOpen
                            start_p = float(candles[0][1]) # Open
                            end_p = float(candles[-1][2]) # Close
                            
                            mom = ((end_p - start_p) / start_p) * 100
                            coin['momentum'] = mom
                            return coin
                except: return None

            results = await asyncio.gather(*[get_momentum(c) for c in targets])
            results = [r for r in results if r is not None]
            
            # 3. Sort by ABSOLUTE Momentum (Up or Down action)
            results.sort(key=lambda x: abs(x['momentum']), reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Screener Error: {e}")
            return []

    # Wrapper for Sync Call if needed
    @staticmethod
    def get_rankings(category="surge"):
        # This is for legacy/standard calls.
        # But 'scalping' category will trigger the Async Loop inside the route handler
        pass
