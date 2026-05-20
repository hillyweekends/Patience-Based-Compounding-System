# update_data.py
import pandas as pd
import pandas_datareader.data as web
import os
from datetime import datetime, timedelta

TICKERS = ['AAPL','AMC','AMZN','BN','CAT','CNR','DIS','DOL','ENB','FTS',
           'GME','HOOD','INTC','JNJ','LLY','META','MSTR','NVDA','PLTR','TSLA','WMT','XOM']
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
start = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')

for ticker in TICKERS:
    filepath = os.path.join(DATA_DIR, f'{ticker}_1D_2021_2026.csv')
    try:
        df_new = web.DataReader(ticker, 'stooq', start=start)
        if df_new.empty:
            print(f'{ticker}: No new data')
            continue
        df_new = df_new.sort_index()
        df_new = df_new.reset_index()
        df_new.columns = ['Date','Open','High','Low','Close','Volume']
        df_new = df_new[['Date','Open','High','Low','Close']]
        df_new = df_new[df_new['Date'] <= yesterday]
        if df_new.empty:
            continue

        if os.path.exists(filepath):
            df_existing = pd.read_csv(filepath)
            # force timezone‑naive datetime
            df_existing['Date'] = pd.to_datetime(df_existing['Date']).dt.tz_localize(None)
            df_new['Date'] = pd.to_datetime(df_new['Date']).dt.tz_localize(None)
            last_date = df_existing['Date'].max()
            new_rows = df_new[df_new['Date'] > last_date]
            if not new_rows.empty:
                df_updated = pd.concat([df_existing, new_rows], ignore_index=True)
                df_updated.to_csv(filepath, index=False)
                print(f'{ticker}: Added {len(new_rows)} rows, last date now {df_updated["Date"].max()}')
            else:
                print(f'{ticker}: No new rows to add')
        else:
            df_new.to_csv(filepath, index=False)
            print(f'{ticker}: Created initial CSV with {len(df_new)} rows')
    except Exception as e:
        print(f'{ticker}: Error - {e}')
