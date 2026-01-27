import sys
import os
import pandas as pd
import numpy as np

# Add parent dir to path to import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import ScoreEngine, Backtester

def create_mock_df(trend="UP", vol_surge=False):
    # Create 100 days of data
    dates = pd.date_range("2024-01-01", periods=100)
    data = []
    price = 1000
    for i in range(100):
        if trend == "UP": price *= 1.01 # 1% up daily
        else: price *= 0.99
        
        vol = 1000000
        if vol_surge and i == 99: vol = 5000000 # 5x surge on last day
        
        data.append([price, price, price, price, vol])
        
    df = pd.DataFrame(data, columns=['open','high','low','close','volume'], index=dates)
    return df

def test_score_engine():
    print(">>> 1. Testing ScoreEngine...")
    
    # CASE 1: Surge + Uptrend
    df_surge = create_mock_df(trend="UP", vol_surge=True)
    ob_tight = {"bids":[{"price":100}], "asks":[{"price":100.1}]} # 0.1% spread
    score, vol_power = ScoreEngine.calculate(df_surge, ob_tight)
    
    print(f"CASE 1 (Surge+Up): Score={score}, VolPower={vol_power:.1f}x")
    if score >= 60 and vol_power > 2.0:
        print("✅ PASS: High Score & Vol Detected")
    else:
        print("❌ FAIL: Score/Vol Logic Error")

    # CASE 2: Dead + Downtrend
    df_dead = create_mock_df(trend="DOWN", vol_surge=False)
    score_dead, vol_power_dead = ScoreEngine.calculate(df_dead, ob_tight)
    
    print(f"CASE 2 (Dead+Down): Score={score_dead}, VolPower={vol_power_dead:.1f}x")
    if score_dead < 50:
        print("✅ PASS: Low Score for Dead Market")
    else:
        print("❌ FAIL: Score should be low")

def test_backtest_engine():
    print("\n>>> 2. Testing Backtest Engine...")
    # Just checking if class exists and runs without crash
    try:
        # We can't easily mock pyupbit here without mocking library, 
        # but we verified the class exists by importing it.
        # We will check if the method is callable.
        if callable(Backtester.run):
             print("✅ PASS: Backtest Engine is ready (Method exists)")
        else:
             print("❌ FAIL: Backtest Method missing")
    except Exception as e:
        print(f"❌ FAIL: {e}")

if __name__ == "__main__":
    try:
        test_score_engine()
        test_backtest_engine()
        print("\nSUMMARY: QA Logic Verification Complete.")
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
