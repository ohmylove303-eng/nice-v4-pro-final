# tests/system_health_check.py
import requests
import time
import sys
import pandas as pd

BASE_URL = "http://localhost:5002"

def log(msg, status="INFO"):
    colors = {"INFO": "\033[94m", "PASS": "\033[92m", "FAIL": "\033[91m", "WARN": "\033[93m", "END": "\033[0m"}
    print(f"[{colors.get(status, '')}{status}{colors['END']}] {msg}")

def check_context_switch():
    log("TEST 1: Context Switching (Scalp vs Swing)...")
    try:
        # 1. Fetch Swing Data (24H)
        t0 = time.time()
        res_swing = requests.get(f"{BASE_URL}/api/analyze/BTC?timeframe=day").json()
        t_swing = time.time() - t0
        
        # 2. Fetch Scalp Data (30m)
        t0 = time.time()
        res_scalp = requests.get(f"{BASE_URL}/api/analyze/BTC?timeframe=scalp").json()
        t_scalp = time.time() - t0
        
        score_swing = res_swing['score']
        score_scalp = res_scalp['score']
        
        log(f"Swing Score: {score_swing} (Time: {t_swing:.2f}s)")
        log(f"Scalp Score: {score_scalp} (Time: {t_scalp:.2f}s)")
        
        if score_swing == score_scalp:
            log("Scores are IDENTICAL. Context Engine FAILED.", "FAIL")
            return False
        else:
            log("Scores are DIFFERENT. Context Engine WORKING.", "PASS")
            return True
    except Exception as e:
        log(f"Context Test Error: {e}", "FAIL")
        return False

def check_screener_integrity():
    log("\nTEST 2: Deep Scan Screener Integrity...")
    try:
        # 1. Surge List
        res_surge = requests.get(f"{BASE_URL}/api/screener/surge").json()
        list_surge = [x['symbol'] for x in res_surge['list'][:5]]
        
        # 2. Scalp List
        t0 = time.time()
        res_scalp = requests.get(f"{BASE_URL}/api/screener/scalp").json()
        t_scan = time.time() - t0
        list_scalp = [x['symbol'] for x in res_scalp['list'][:5]]
        
        log(f"Surge Top 5: {list_surge}")
        log(f"Scalp Top 5: {list_scalp}")
        log(f"Deep Scan Time: {t_scan:.2f}s")
        
        if set(list_surge) == set(list_scalp):
             log("Lists are IDENTICAL. Deep Scan FAILED (Just copying surge?).", "WARN")
        else:
             log("Lists are DIFFERENT. Deep Scan WORKING.", "PASS")
             
        if t_scan > 5.0:
            log("Deep Scan is TOO SLOW (>5s). Needs Async Optimization.", "WARN")
        
        return True
    except Exception as e:
        log(f"Screener Test Error: {e}", "FAIL")
        return False

def check_backtest():
    log("\nTEST 3: Backtest Engine...")
    try:
        res = requests.get(f"{BASE_URL}/api/backtest/BTC").json()
        if 'error' in res:
            log(f"Backtest Error: {res['error']}", "FAIL")
            return False
            
        trades = res.get('trades', 0)
        ret = res.get('return_pct', 0)
        log(f"Trades: {trades}, Return: {ret}%")
        
        if trades == 0:
            log("No Trades Executed. Strategy Constraint too strict?", "WARN")
        else:
            log("Backtest Returns Valid Data.", "PASS")
        return True
    except Exception as e:
        log(f"Backtest Exception: {e}", "FAIL")
        return False

def main():
    log("=== STARTING SYSTEM AUTOPSY ===")
    
    # Pre-check: Is server running?
    try:
        requests.get(BASE_URL)
    except:
        log("Server not running at localhost:5002. Starting it background...", "WARN")
        import subprocess
        subprocess.Popen(["python3", "app.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5) # Wait for startup
    
    p1 = check_context_switch()
    p2 = check_screener_integrity()
    p3 = check_backtest()
    
    if p1 and p2 and p3:
        log("\n>>> SYSTEM HEALTH: OPTIMAL (READY FOR DEPLOY) <<<", "PASS")
    else:
        log("\n>>> SYSTEM HEALTH: ATTENTION REQUIRED <<<", "FAIL")

if __name__ == "__main__":
    main()
