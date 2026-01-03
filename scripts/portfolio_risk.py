#!/usr/bin/env python3
"""Portfolio Risk Analyzer"""
import os, json, logging
import pandas as pd
import numpy as np
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PortfolioRiskAnalyzer:
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.output_file = os.path.join(self.data_dir, 'portfolio_risk.json')

    def load_portfolio(self):
        """Load portfolio from CSV"""
        csv_path = os.path.join(self.data_dir, 'us_portfolio.csv')
        if not os.path.exists(csv_path):
            logger.warning(f"Portfolio file not found at {csv_path}. Using default list.")
            return None, None
        
        try:
            df = pd.read_csv(csv_path)
            # Standardize columns
            df.columns = [c.strip() for c in df.columns]
            if 'Ticker' not in df.columns:
                return None, None
            
            tickers = df['Ticker'].tolist()
            shares = df['Shares'].tolist() if 'Shares' in df.columns else [1] * len(tickers)
            return tickers, shares
        except Exception as e:
            logger.error(f"Error reading portfolio CSV: {e}")
            return None, None

    def analyze_portfolio(self, tickers=None):
        try:
            shares = None
            if tickers is None:
                tickers, shares = self.load_portfolio()
                if tickers is None:
                    tickers = ['NVDA', 'MSFT', 'AAPL', 'GOOGL', 'AMZN', 'TSLA', 'AMD', 'META']
                    shares = [1] * len(tickers)

            logger.info(f"Fetching data for risk analysis: {tickers}")
            # Fetch 1 year of data
            data = yf.download(tickers, period='1y', progress=False)['Close']
            
            if data.empty:
                return {}
            
            if isinstance(data, pd.Series):
                data = data.to_frame()

            data = data.ffill().bfill()
            returns = data.pct_change().dropna()
            
            if returns.empty:
                return {}

            # --- 1. Correlation Matrix ---
            corr_matrix = returns.corr().round(2)
            
            heatmap_series = []
            for ticker_x in corr_matrix.columns:
                row_data = []
                for ticker_y in corr_matrix.columns:
                    val = corr_matrix.loc[ticker_x, ticker_y]
                    row_data.append({'x': ticker_y, 'y': val})
                heatmap_series.append({'name': ticker_x, 'data': row_data})

            high_corr = []
            cols = corr_matrix.columns
            for i in range(len(cols)):
                for j in range(i+1, len(cols)):
                    val = corr_matrix.iloc[i, j]
                    if abs(val) > 0.7:
                        high_corr.append({
                            'pair': [cols[i], cols[j]], 
                            'value': round(val, 2),
                            'type': 'Positive' if val > 0 else 'Negative'
                        })

            # --- 2. Portfolio Metrics (Value Expected) ---
            # Calculate current weights based on latest price * shares
            if shares and len(shares) == len(tickers):
                current_prices = data.iloc[-1]
                # Align shares with columns in data (yf might change order or drop invalid tickers)
                valid_tickers = data.columns.tolist()
                
                # Create a map for shares
                share_map = {t: s for t, s in zip(tickers, shares)}
                
                try:
                    # Calculate position values
                    pos_values = [current_prices[t] * share_map.get(t, 1) for t in valid_tickers]
                    total_value = sum(pos_values)
                    weights = np.array([v / total_value for v in pos_values])
                except Exception as e:
                    logger.warning(f"Error calculating weights: {e}. Using equal weights.")
                    weights = np.array([1/len(valid_tickers)] * len(valid_tickers))
            else:
                weights = np.array([1/data.shape[1]] * data.shape[1])

            port_returns = returns.dot(weights)
            
            # Annualized Volatility
            ann_vol = port_returns.std() * np.sqrt(252)
            
            # Sharpe Ratio
            rf = 0.04
            sharpe = (port_returns.mean() * 252 - rf) / ann_vol if ann_vol != 0 else 0
            
            # Max Drawdown
            cum_returns = (1 + port_returns).cumprod()
            rolling_max = cum_returns.cummax()
            drawdown = (cum_returns - rolling_max) / rolling_max
            max_drawdown = drawdown.min()

            # Value at Risk (95%)
            var_95 = np.percentile(port_returns, 5)

            # --- 3. Individual Risk Metrics ---
            individual_metrics = []
            for ticker in tickers:
                if ticker in returns.columns:
                    r = returns[ticker]
                    vol = r.std() * np.sqrt(252)
                    cum = (1 + r).cumprod()
                    dd = ((cum - cum.cummax()) / cum.cummax()).min()
                    
                    # Beta calculation vs SPY (simplified, vs portfolio here for relative beta)
                    # For real beta, we need a benchmark. Using portfolio as benchmark for now.
                    cov_with_port = r.cov(port_returns)
                    var_port = port_returns.var()
                    beta = cov_with_port / var_port if var_port != 0 else 1.0

                    individual_metrics.append({
                        'ticker': ticker,
                        'volatility': round(vol * 100, 2),
                        'max_drawdown': round(dd * 100, 2),
                        'beta': round(beta, 2)
                    })

            result = {
                'timestamp': pd.Timestamp.now().isoformat(),
                'summary': {
                    'portfolio_volatility': round(ann_vol * 100, 2),
                    'sharpe_ratio': round(sharpe, 2),
                    'max_drawdown': round(max_drawdown * 100, 2),
                    'var_95': round(var_95 * 100, 2),
                    'risk_level': 'High' if ann_vol > 0.25 else 'Medium' if ann_vol > 0.15 else 'Low'
                },
                'correlation_matrix': {
                    'series': heatmap_series,
                    'high_correlations': high_corr
                },
                'individual_risks': individual_metrics
            }
            
            with open(self.output_file, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"Saved risk analysis to {self.output_file}")
            return result
            
        except Exception as e:
            logger.error(f"Error in risk analysis: {e}")
            import traceback
            traceback.print_exc()
            return {}

if __name__ == "__main__":
    PortfolioRiskAnalyzer().analyze_portfolio()
