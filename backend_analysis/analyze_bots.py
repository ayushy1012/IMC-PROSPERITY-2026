import json
import os
import glob
from collections import defaultdict
import pandas as pd
import numpy as np

LOGS_DIR = "/Users/dmitt/Desktop/Prosperity/logs/logs"
ANALYSIS_DIR = "backend_analysis"
os.makedirs(ANALYSIS_DIR, exist_ok=True)

def parse_logs():
    bot_trades = []
    
    log_files = glob.glob(f"{LOGS_DIR}/*.log")
    print(f"Found {len(log_files)} log files. Parsing...")
    
    for file_path in log_files:
        run_id = os.path.basename(file_path).replace('.log', '')
        
        with open(file_path, 'r') as f:
            for line in f:
                if "marketTrades" in line:
                    try:
                        data = json.loads(line)
                        if "marketTrades" in data:
                            for symbol, trades in data["marketTrades"].items():
                                for t in trades:
                                    bot_trades.append({
                                        'run_id': run_id,
                                        'timestamp': t['timestamp'],
                                        'symbol': symbol,
                                        'price': t['price'],
                                        'quantity': t['quantity'],
                                        'buyer': t.get('buyer', ''),
                                        'seller': t.get('seller', '')
                                    })
                    except Exception as e:
                        pass

    if len(bot_trades) == 0:
        print("No market trades found.")
        return
        
    df = pd.DataFrame(bot_trades)
    
    print("Columns:", df.columns)
    
    if 'buyer' in df.columns:
        df = df[(df['buyer'] != 'SUBMISSION') & (df['seller'] != 'SUBMISSION')]
    
    print(f"Extracted {len(df)} purely bot-to-bot trades.")
    
    # Analyze by symbol
    for symbol in df['symbol'].unique():
        sym_df = df[df['symbol'] == symbol].copy()
        print(f"\n--- {symbol} Bot Analysis ---")
        
        if 'buyer' in sym_df.columns:
            buyers = sym_df['buyer'].value_counts()
            sellers = sym_df['seller'].value_counts()
            
            print("Top Buyers:")
            print(buyers.head())
            print("Top Sellers:")
            print(sellers.head())
        
        sym_df.to_csv(os.path.join(ANALYSIS_DIR, f"{symbol}_bot_trades.csv"), index=False)

if __name__ == "__main__":
    parse_logs()
