#!/usr/bin/env python3
"""Economic Calendar with AI Enrichment"""
import os, json, requests, logging
from datetime import datetime
import pandas as pd
from io import StringIO
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EconomicCalendar:
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.output = os.path.join(data_dir, 'weekly_calendar.json')
        
    def get_events(self):
        from datetime import timedelta
        today = datetime.now()
        
        events = [
            {'date': today.strftime('%Y-%m-%d'), 'event': 'Market Open', 'impact': 'Low', 'description': 'Regular trading session'},
        ]
        
        # Calculate next occurrence of known events
        # FOMC meetings are typically 8 times per year (roughly every 6-7 weeks)
        # CPI release is typically 2nd week of each month
        # Jobs report is typically 1st Friday of each month
        # GDP is quarterly
        
        def next_weekday(date, weekday):
            """Get next specific weekday (0=Monday, 4=Friday)"""
            days_ahead = weekday - date.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return date + timedelta(days=days_ahead)
        
        # Jobs Report - 1st Friday of next month
        next_month = today.replace(day=1) + timedelta(days=32)
        first_of_next = next_month.replace(day=1)
        jobs_date = next_weekday(first_of_next, 4)  # Friday = 4
        events.append({
            'event': 'Jobs Report (NFP)',
            'impact': 'High',
            'description': 'Non-farm payrolls data - key employment indicator',
            'date': jobs_date.strftime('%Y-%m-%d')
        })
        
        # CPI Release - around 10-13th of each month
        cpi_date = today.replace(day=12) if today.day < 12 else (today.replace(day=1) + timedelta(days=42)).replace(day=12)
        events.append({
            'event': 'CPI Release',
            'impact': 'High',
            'description': 'Consumer Price Index - inflation indicator',
            'date': cpi_date.strftime('%Y-%m-%d')
        })
        
        # FOMC - roughly every 6 weeks, let's estimate next one
        fomc_date = today + timedelta(days=21)  # Approximate next meeting
        events.append({
            'event': 'FOMC Meeting',
            'impact': 'High',
            'description': 'Fed interest rate decision',
            'date': fomc_date.strftime('%Y-%m-%d')
        })
        
        # GDP Report - end of each quarter
        quarter_end_month = ((today.month - 1) // 3 + 1) * 3 + 1
        if quarter_end_month > 12:
            quarter_end_month = 1
            gdp_year = today.year + 1
        else:
            gdp_year = today.year
        gdp_date = datetime(gdp_year, quarter_end_month, 28)
        events.append({
            'event': 'GDP Report',
            'impact': 'Medium',
            'description': 'Quarterly GDP growth',
            'date': gdp_date.strftime('%Y-%m-%d')
        })
        
        # Sort by date
        events.sort(key=lambda x: x['date'])
        
        return events
    
    def enrich_ai(self, events):
        key = os.getenv('GOOGLE_API_KEY')
        if not key: return events
        
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        
        for ev in events:
            if ev['impact'] == 'High':
                try:
                    prompt = f"Explain market impact of {ev['event']} in 1 sentence. Korean."
                    resp = requests.post(f"{url}?key={key}", json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
                    if resp.status_code == 200:
                        ev['ai_insight'] = resp.json()['candidates'][0]['content']['parts'][0]['text']
                except: pass
        return events

    def run(self):
        events = self.get_events()
        events = self.enrich_ai(events)
        
        output = {'updated': datetime.now().isoformat(), 'events': events}
        with open(self.output, 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        logger.info("Saved economic calendar")
        return output

if __name__ == "__main__":
    EconomicCalendar().run()
