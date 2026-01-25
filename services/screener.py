# services/screener.py
import requests
import asyncio
import aiohttp
import config
import logging
import pandas as pd
import random

logger = logging.getLogger(__name__)

class BithumbScreener:
    @staticmethod
    async def get_realtime_momentum(limit=20):
        try:
            # 1. Base List
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
            
            # Liquidity Cut: Top 30 to save API calls
            candidates.sort(key=lambda x: x['vol'], reverse=True)
            targets = candidates[:30]
            
            # 2. Deep Scan with Semaphore
            sem = asyncio.Semaphore(5) # Max 5 concurrent requests
            
            async def get_momentum(coin):
                async with sem:
                    try:
                        # Random sleep to avoid pattern detection
                        await asyncio.sleep(random.uniform(0.1, 0.3))
                        
                        url = f"{config.BITHUMB_API_URL}/candlestick/{coin['symbol']}_KRW/30m"
                        headers = {"User-Agent": "Mozilla/5.0"}
                        
                        async with aiohttp.ClientSession() as session:
                            async with session.get(url, headers=headers) as resp:
                                if resp.status != 200: 
                                    return None
                                res = await resp.json()
                                if res['status'] != '0000': 
                                    return None
                                
                                candles = res['data'][-3:] 
                                start_p = float(candles[0][1])
                                end_p = float(candles[-1][2])
                                
                                mom = ((end_p - start_p) / start_p) * 100
                                coin['momentum'] = mom
                                return coin
                    except Exception as e:
                        return None

            results = await asyncio.gather(*[get_momentum(c) for c in targets])
            results = [r for r in results if r is not None]
            
            # 3. Sort
            results.sort(key=lambda x: abs(x['momentum']), reverse=True)
            
            if not results:
                logger.warning("Deep Scan returned empty. Returning raw volume list.")
                return candidates[:limit] # Fallback
                
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Screener Error: {e}")
            return []

    # Wrapper for Sync Call
    @staticmethod
    def get_rankings(category="surge"):
        pass
