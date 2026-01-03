#!/usr/bin/env python3
"""Unified Update Script - Runs all analysis scripts"""
import os, sys, subprocess, time, argparse

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

scripts = [
    ("create_us_daily_prices.py", "Data Collection", 600),
    ("analyze_volume.py", "Volume Analysis", 300),
    ("analyze_13f.py", "13F Holdings", 600),
    ("analyze_etf_flows.py", "ETF Flows", 300),
    ("smart_money_screener_v2.py", "Screening", 600),
    ("sector_heatmap.py", "Heatmap", 120),
    ("options_flow.py", "Options", 120),
    ("insider_tracker.py", "Insider", 180),
    ("portfolio_risk.py", "Risk", 60),
    ("historical_returns.py", "Historical Returns", 120),  # ADDED: Fixes stale historical_returns.json
    ("macro_analyzer.py", "Macro", 120),
    ("ai_summary_generator.py", "AI Summaries", 900),
    ("fetch_news_earnings.py", "News/Earnings", 180),  # ADDED: Fixes stale news_events.json
    ("final_report_generator.py", "Final Report", 60),
    ("economic_calendar.py", "Calendar", 120),
    ("market_gate_manager.py", "Market Gate", 120),
    ("lead_lag_analyzer.py", "Lead-Lag Analysis", 300),
    ("vcp_screener.py", "VCP Screener", 180)
]

def run_script(name, desc, timeout):
    path = os.path.join(SCRIPTS_DIR, name)
    if not os.path.exists(path):
        print(f"⚠️  {desc}: Script not found")
        return False
    
    print(f"▶️  Running {desc}...")
    try:
        result = subprocess.run([sys.executable, path], timeout=timeout, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {desc}: Done")
            return True
        else:
            print(f"❌ {desc}: Failed")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏱️  {desc}: Timeout")
        return False
    except Exception as e:
        print(f"❌ {desc}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='US Market Update Script')
    parser.add_argument('--quick', action='store_true', help='Skip AI-heavy scripts')
    parser.add_argument('--data-only', action='store_true', help='Only run data collection')
    args = parser.parse_args()
    
    print("="*50)
    print("🚀 US Market Dashboard Update")
    print("="*50)
    
    start = time.time()
    success, failed = 0, 0
    
    for name, desc, timeout in scripts:
        if args.data_only and name not in ['create_us_daily_prices.py', 'analyze_volume.py', 'analyze_13f.py']:
            continue
        if args.quick and "AI" in desc:
            print(f"⏭️  Skipping {desc} (--quick mode)")
            continue
            
        if run_script(name, desc, timeout):
            success += 1
        else:
            failed += 1
    
    elapsed = time.time() - start
    print("="*50)
    print(f"✅ Completed: {success} | ❌ Failed: {failed}")
    print(f"⏱️  Total time: {elapsed/60:.1f} minutes")
    print("="*50)

if __name__ == "__main__":
    main()
