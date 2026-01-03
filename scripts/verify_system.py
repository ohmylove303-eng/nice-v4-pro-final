import requests
import sys

BASE_URL = "http://127.0.0.1:5001"
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def check(name, url, validator):
    try:
        print(f"🔍 Checking {name}...", end=" ")
        res = requests.get(f"{BASE_URL}{url}", timeout=10)
        data = res.json()
        
        if validator(data):
            print(f"{GREEN}PASS{RESET}")
            return True
        else:
            print(f"{RED}FAIL{RESET}")
            return False
    except Exception as e:
        print(f"{RED}ERROR ({e}){RESET}")
        return False

print("========================================")
print("🚀 SYSTEM VERIFICATION START")
print("========================================")

# 1. Top 10 Price Check
def validate_top10(data):
    picks = data.get('top_picks', [])
    if not picks: return False
    # Check if change_pct is not all zero
    non_zero_changes = [p for p in picks if p.get('change_pct', 0) != 0]
    if len(non_zero_changes) > 0:
        print(f"\n   -> Found {len(non_zero_changes)} stocks with live price changes.", end="")
        return True
    print("\n   -> All price changes are 0.00%. (Live patch failed)", end="")
    return False

check("Top 10 Live Prices", "/api/us/smart-money", validate_top10)

# 2. AI Macro Korean Check
def validate_macro(data):
    analysis = data.get('ai_analysis', '')
    # Check for Korean characters (Hangul)
    if any('\uac00' <= char <= '\ud7a3' for char in analysis):
        print(f"\n   -> Korean text detected.", end="")
        return True
    print("\n   -> No Korean text found. AI is speaking English.", end="")
    return False

check("AI Macro Analysis (Korean)", "/api/us/macro-analysis?lang=ko", validate_macro)

# 3. News & Earnings Check
def validate_news(data):
    earnings = data.get('earnings', [])
    if len(earnings) > 0:
        print(f"\n   -> Found {len(earnings)} upcoming earnings events.", end="")
        return True
    return False

check("Corporate News & Earnings", "/api/us/corporate-events", validate_news)

print("========================================")
print("✅ VERIFICATION COMPLETE")
