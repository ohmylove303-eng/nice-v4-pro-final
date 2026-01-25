# services/portfolio_manager.py
import time
import random

class PortfolioManager:
    def __init__(self):
        self.initial_balance = 100000000 # 100M KRW
        self.balance = self.initial_balance
        self.positions = [] # {id, symbol, size, entry_price, current_price, pnl}
        self.history = [] # {symbol, pnl, win_loss}
        self.start_time = time.time()
        
        # Seed some data for UI visualization (Mocking Phase 3 DB)
        self._seed_mock_data()

    def _seed_mock_data(self):
        # Simulate past trades for Analytics
        for _ in range(10):
            win = random.choice([True, True, False])
            pnl = random.randint(100000, 5000000) if win else random.randint(-2000000, -100000)
            self.history.append({
                "symbol": random.choice(["BTC", "ETH", "SOL", "XRP"]),
                "pnl": pnl,
                "win": win,
                "timestamp": time.time() - random.randint(1000, 100000)
            })
            self.balance += pnl

    def get_metrics(self):
        # Calculate Win Rate
        wins = [t for t in self.history if t['win']]
        win_rate = (len(wins) / len(self.history) * 100) if self.history else 0
        
        # Calculate PnL
        total_pnl = self.balance - self.initial_balance
        pnl_pct = (total_pnl / self.initial_balance) * 100
        
        # Simulated Sharpe/Drawdown (Complex math simplified for v8.4)
        sharpe = 1.5 + (random.random() * 0.5)
        mdd = -5.0 - (random.random() * 5.0)
        
        return {
            "total_balance": int(self.balance),
            "unrealized_pnl": sum(p['pnl'] for p in self.positions),
            "realized_pnl_24h": int(total_pnl), # Simplified
            "win_rate": round(win_rate, 1),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(mdd, 2),
            "open_positions": len(self.positions),
            "recent_trades": self.history[-5:]
        }
    
    def get_positions(self):
        # Update current prices (Simulated)
        for p in self.positions:
            change = (random.random() - 0.45) * 0.01
            p['current_price'] = p['entry_price'] * (1 + change)
            p['pnl'] = (p['current_price'] - p['entry_price']) * p['size']
            p['pnl_pct'] = ((p['current_price'] - p['entry_price']) / p['entry_price']) * 100
        return self.positions

    def open_position(self, symbol, price, size):
        self.positions.append({
            "id": len(self.positions) + 1,
            "symbol": symbol,
            "entry_price": price,
            "current_price": price,
            "size": size,
            "pnl": 0,
            "pnl_pct": 0,
            "side": "BUY"
        })
        return True
