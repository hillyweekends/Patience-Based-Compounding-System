# generate_report.py
import pandas as pd, numpy as np, os
from datetime import datetime

DATA_DIR = 'data'           # change to '.' if CSVs are in root
LOOKBACK_DAYS = 60
ENTRY_PERCENTILE = 5.0
FLOOR = 0.02
TARGET_WINDOW = 7
TOP_N = 5

def prepare_data(fp):
    df = pd.read_csv(fp)
    df.columns = [c.strip().lower() for c in df.columns]
    dc = 'date' if 'date' in df.columns else 'timestamp'
    df[dc] = pd.to_datetime(df[dc])
    df = df.sort_values(dc).reset_index(drop=True)
    df = df.rename(columns={dc:'Date','open':'Open','high':'High','low':'Low','close':'Close'})
    return df[['Date','Open','High','Low','Close']].dropna()

def compute_today_metrics(df, ticker):
    lows = df['Low'].values; highs = df['High'].values; closes = df['Close'].values
    n = len(lows)
    if n < LOOKBACK_DAYS + TARGET_WINDOW:
        return None

    # ATR(14) vectorised
    prev_closes = np.roll(closes, 1); prev_closes[0] = closes[0]
    tr = np.maximum(highs - lows, np.maximum(np.abs(highs - prev_closes), np.abs(lows - prev_closes)))
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values

    # daily deviations (shifted)
    daily_devs = np.zeros(n)
    for j in range(LOOKBACK_DAYS, n):
        avg = np.mean(lows[j-LOOKBACK_DAYS:j])
        daily_devs[j] = (lows[j] - avg) / avg

    # use deviations up to yesterday (index n-1) for today's floor
    devs_up_to_yesterday = daily_devs[LOOKBACK_DAYS:n]
    if len(devs_up_to_yesterday) == 0:
        return None
    gf = np.percentile(devs_up_to_yesterday, ENTRY_PERCENTILE)
    if gf > -0.05:
        gf = -0.07

    avg_low = np.mean(lows[-LOOKBACK_DAYS:])   # last 60 days including yesterday
    low_est = avg_low * (1 + gf)

    high_avg = np.mean(highs[-TARGET_WINDOW:])   # last 7 days including yesterday
    profit_potential = high_avg / low_est - 1
    current_atr = atr[-1]
    last_close = closes[-1]
    score = profit_potential * (current_atr / last_close) if last_close > 0 else 0

    target_price = max(high_avg, low_est * (1 + FLOOR))
    distance_pct = (last_close - low_est) / last_close * 100

    return {
        'ticker': ticker,
        'last_date': df['Date'].iloc[-1].strftime('%Y-%m-%d'),
        'last_close': last_close,
        'low_estimate': low_est,
        'target_price': target_price,
        'score': score,
        'distance_pct': distance_pct
    }

def main():
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv') and ' (1)' not in f and '.trashed' not in f.lower()]
    if not files:
        print("No CSV files found.")
        return

    ticker_metrics = []
    for f in files:
        fp = os.path.join(DATA_DIR, f)
        ticker = os.path.splitext(f)[0].upper()
        df = prepare_data(fp)
        metrics = compute_today_metrics(df, ticker)
        if metrics:
            ticker_metrics.append(metrics)

    ticker_metrics.sort(key=lambda x: x['score'], reverse=True)
    top = ticker_metrics[:TOP_N]
    last_date = max(m['last_date'] for m in ticker_metrics) if ticker_metrics else "unknown"

    # pool balance
    pool_file = 'pool_balance.txt'
    if os.path.exists(pool_file):
        with open(pool_file) as f:
            pool_balance = float(f.read().strip())
    else:
        pool_balance = 100.0
    slices = int(pool_balance // 10)

    # Build HTML
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Patience Compounding – Daily Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{ font-family: Arial, sans-serif; max-width: 800px; margin: auto; padding: 20px; background: #f5f5f5; }}
h1 {{ text-align: center; color: #2c3e50; }}
.card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 8px 12px; border-bottom: 1px solid #ddd; text-align: left; }}
th {{ background: #f0f0f0; }}
.rank {{ font-weight: bold; color: #3498db; }}
</style></head><body>
<h1>📉 Patience-Based Compounding System</h1>
<div class="card">
<p><strong>Report generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</p>
<p><strong>Last data date:</strong> {last_date}</p>
<p><strong>Pool Balance:</strong> ${pool_balance:.2f}</p>
<p><strong>Available $10 slices:</strong> {slices}</p>
</div>
<div class="card">
<p><strong>Top {TOP_N} tickers for today's limit orders:</strong></p>
<table>
<tr><th>Rank</th><th>Ticker</th><th>Last Close</th><th>Buy Limit</th><th>Target</th><th>Gain%</th><th>Score</th></tr>"""
    for rank, m in enumerate(top, 1):
        gain = (m['target_price'] / m['low_estimate'] - 1) * 100
        html += f"<tr><td class='rank'>{rank}</td><td>{m['ticker']}</td><td>${m['last_close']:.2f}</td><td>${m['low_estimate']:.2f}</td><td>${m['target_price']:.2f}</td><td>{gain:.1f}%</td><td>{m['score']:.4f}</td></tr>"
    html += """</table>
</div>
<p style="text-align:center; color:#888;">Automated daily update via GitHub Actions. No mark‑to‑market. No stop‑losses.</p>
</body></html>"""

    os.makedirs('docs', exist_ok=True)
    with open('docs/index.html', 'w') as f:
        f.write(html)
    print("Dashboard generated: docs/index.html")

if __name__ == "__main__":
    main()
