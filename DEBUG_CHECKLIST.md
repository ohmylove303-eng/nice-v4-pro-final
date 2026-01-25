# 🛠️ NICE v8.5 ULTRATHINK SYSTEM DEBUGGING CHECKLIST

This checklist is provided to ensure the system is functioning according to the `COMPLETE_SYSTEM.md` specifications and recent v8.5 upgrades.

## 1. Context Engine Verification (Scalp vs Swing)
- [ ] **Action**: Open the dashboard. Click on [🔥 SWING] tab. Search `BTC`. Note the Score.
- [ ] **Action**: Click on [⚡ SCALP] tab. Search `BTC` again. Note the Score.
- [ ] **Expected Result**: The scores MUST be different. (e.g., Swing 50, Scalp 70).
- [ ] **Debug**: If scores are identical, `MarketData.fetch` in `app.py` is not respecting the `timeframe` parameter.

## 2. Deep Scan Screener Verification
- [ ] **Action**: Click [⚡ SCALP] tab in the sidebar.
- [ ] **Expected Result**: Loading spinner "Deep Scanning..." appears for 1-3 seconds. The list should populate with coins showing high **Momentum** (e.g., +2.5%).
- [ ] **Debug**: If list is empty, check `services/screener.py` logs for Bithumb API errors (429 Too Many Requests). The Semaphore limit is currently set to 5.

## 3. Portfolio & Risk Metrics (New Phase 4 Features)
- [ ] **Action**: Check the top-right header ("Win Rate") and the "Risk Landscape" card.
- [ ] **Expected Result**: Numbers should be populated (e.g., "Win Rate: 55%", "Sharpe: 1.8").
- [ ] **Debug**: If showing `--`, check `/api/portfolio/metrics` endpoint response manually in browser.

## 4. Guard Chain Logic
- [ ] **Action**: Analyze a coin.
- [ ] **Expected Result**: Guard Card should show 7 Phases.
- [ ] **Critical Check**: If you analyze a meaningless coin (low liquidity), Phase 3 (Liquidity) should fail (Red Dot).
- [ ] **Debug**: Check `services/guard_chain.py` logic for liquidity thresholds.

## 5. Agent Consensus
- [ ] **Action**: Look at the "Signal Agents" card.
- [ ] **Expected Result**: 5 distinct bars should appear (Tech, OnChain, Sentiment, Macro, Inst).
- [ ] **Verification**: "Technical" score should roughly align with the RSI/MACD state of the mock chart.

---
**Troubleshooting Command**
If you suspect the system is frozen, run:
```bash
python3 tests/system_health_check.py
```
This script runs a self-diagnostic autopsy on the engine.
