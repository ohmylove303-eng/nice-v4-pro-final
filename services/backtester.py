# services/backtester.py
import pandas as pd
import numpy as np

class Backtester:
    def __init__(self):
        self.name = "Historical Simulator"

    def run(self, ticker, df_in):
        try:
            # Copy to avoid mutating original
            df = df_in.copy()
            if len(df) < 50: return {"error": "Not enough history"}
            
            # Strategy Indicators
            df['ma20'] = df['close'].rolling(20).mean()
            df['ma60'] = df['close'].rolling(60).mean()
            
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['rsi'] = 100 - (100 / (1 + (gain/loss)))
            
            # Simulation
            balance = 100000000 # 100M KRW
            position = 0 # 0 or amount
            trades = []
            wins = 0
            
            for i in range(60, len(df)):
                row = df.iloc[i]
                price = row['close']
                date = str(df.index[i]) if isinstance(df.index, pd.DatetimeIndex) else f"T-{len(df)-i}"
                
                # Logic: Buy if MA20 > MA60 (Trend) AND RSI < 40 (Dip)
                signal_buy = (row['ma20'] > row['ma60']) and (row['rsi'] < 45)
                # Logic: Sell if RSI > 70 or Trend Break
                signal_sell = (row['rsi'] > 70) or (row['ma20'] < row['ma60'])
                
                if position == 0 and signal_buy:
                    position = balance / price
                    balance = 0
                    trades.append({"type": "BUY", "price": price, "date": date})
                    
                elif position > 0 and signal_sell:
                    sell_amt = position * price
                    profit = sell_amt - (trades[-1]['price'] * position)
                    if profit > 0: wins += 1
                    
                    balance = sell_amt
                    position = 0
                    trades.append({"type": "SELL", "price": price, "date": date, "pnl": int(profit)})
            
            # Final Value
            final_val = balance + (position * df.iloc[-1]['close'])
            ret_pct = (final_val - 100000000) / 100000000 * 100
            
            total_trades = len([t for t in trades if t['type']=='SELL'])
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            return {
                "ticker": ticker,
                "return_pct": round(ret_pct, 2),
                "win_rate": round(win_rate, 1),
                "trades": total_trades,
                "log": trades[-5:] # Last 5
            }
            
        except Exception as e:
            return {"error": str(e)}
