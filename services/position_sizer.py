# services/position_sizer.py
class PositionSizer:
    def calculate(self, symbol, signal, account_size, win_rate=0.6, rr_ratio=2.0):
        # Kelly Formula: f = (bp - q) / b
        # b = odds (RR ratio)
        # p = probability (win rate)
        # q = 1-p
        
        b = rr_ratio
        p = win_rate
        q = 1 - p
        
        kelly = (b * p - q) / b
        safe_kelly = max(0, kelly * 0.5) # Half Kelly for safety
        
        # Max 5% constraint
        position_pct = min(safe_kelly * 100, 5.0)
        
        return {
            "kelly_pct": round(position_pct, 2),
            "size": account_size * (position_pct/100),
            "leverage": 1
        }
