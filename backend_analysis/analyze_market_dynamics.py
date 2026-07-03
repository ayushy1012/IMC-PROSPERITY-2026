import json
import io
import csv
import glob
import pandas as pd
import numpy as np

LOGS_DIR = "/Users/dmitt/Desktop/Prosperity/logs/logs"

def parse_activities_log(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    if 'activitiesLog' not in data:
        return None
        
    df = pd.read_csv(io.StringIO(data['activitiesLog']), sep=';')
    # Convert numerical columns
    num_cols = ['timestamp', 'bid_price_1', 'bid_volume_1', 'bid_price_2', 'bid_volume_2', 
                'bid_price_3', 'bid_volume_3', 'ask_price_1', 'ask_volume_1', 'ask_price_2', 
                'ask_volume_2', 'ask_price_3', 'ask_volume_3', 'mid_price', 'profit_and_loss']
    
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    df['run_id'] = file_path.split('/')[-1].replace('.log', '')
    return df

def analyze_all():
    files = glob.glob(f"{LOGS_DIR}/*.log")
    
    dfs = []
    print(f"Loading {len(files)} logs...")
    for f in files:
        df = parse_activities_log(f)
        if df is not None:
            dfs.append(df)
            
    if not dfs:
        print("No valid logs found.")
        return
        
    master_df = pd.concat(dfs, ignore_index=True)
    
    # ------------------
    # Analysis by Product
    # ------------------
    summary = []
    
    for product in master_df['product'].unique():
        prod_df = master_df[master_df['product'] == product]
        print(f"\nEvaluating {product} (N={len(prod_df)} ticks across runs)")
        
        # Calculate mid_price properties
        mean_mid = prod_df['mid_price'].mean()
        std_mid = prod_df['mid_price'].std()
        min_mid = prod_df['mid_price'].min()
        max_mid = prod_df['mid_price'].max()
        
        # Calculate tick-to-tick changes per run
        prod_df = prod_df.sort_values(['run_id', 'timestamp'])
        prod_df['mid_return'] = prod_df.groupby('run_id')['mid_price'].diff()
        
        mean_return = prod_df['mid_return'].mean()
        std_return = prod_df['mid_return'].std()
        
        # Auto-correlation (lag 1)
        lag1_autocorr = prod_df['mid_return'].autocorr(lag=1)
        
        # Spread analysis
        prod_df['spread'] = prod_df['ask_price_1'] - prod_df['bid_price_1']
        mean_spread = prod_df['spread'].mean()
        
        # Total volume provided at level 1
        mean_bid_vol = prod_df['bid_volume_1'].mean()
        mean_ask_vol = prod_df['ask_volume_1'].mean()
        
        summary.append({
            'Product': product,
            'Mean_Price': mean_mid,
            'Std_Price': std_mid,
            'Min_Price': min_mid,
            'Max_Price': max_mid,
            'Volatility_per_Tick': std_return,
            'Return_Autocorr_Lag1': lag1_autocorr,
            'Mean_Spread': mean_spread,
            'Mean_Bid_Vol_L1': mean_bid_vol,
            'Mean_Ask_Vol_L1': mean_ask_vol
        })
        
        print(f"Mean Price: {mean_mid:.2f} (Std: {std_mid:.2f}, Range: [{min_mid:.2f}, {max_mid:.2f}])")
        print(f"Volatility (tick): {std_return:.2f}")
        print(f"Auto-corr (lag 1): {lag1_autocorr:.4f}")
        print(f"Mean Spread: {mean_spread:.2f}")
    
    sum_df = pd.DataFrame(summary)
    sum_df.to_csv("backend_analysis/market_dynamics_summary.csv", index=False)
    print("\nSaved market dynamics summary to backend_analysis/market_dynamics_summary.csv")

if __name__ == "__main__":
    analyze_all()
