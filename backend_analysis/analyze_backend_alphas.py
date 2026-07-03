import json
import io
import glob
import pandas as pd
import numpy as np

LOGS_DIR = "/Users/dmitt/Desktop/Prosperity/logs/logs"
OUTPUT_DIR = "/Users/dmitt/Desktop/Prosperity/backend_analysis"

def parse_activities_log(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    if 'activitiesLog' not in data:
        return None
        
    df = pd.read_csv(io.StringIO(data['activitiesLog']), sep=';')
    num_cols = ['timestamp', 'bid_price_1', 'bid_volume_1', 'ask_price_1', 'ask_volume_1', 'mid_price']
    
    # We only care about L1 and mid_price for now, so drop other cols to avoid NaN issues
    df = df[['day', 'timestamp', 'product'] + num_cols[1:]]
    
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    df['run_id'] = file_path.split('/')[-1].replace('.log', '')
    return df

def extract_alphas():
    files = glob.glob(f"{LOGS_DIR}/*.log")
    dfs = []
    print(f"Loading {len(files)} logs...")
    for f in files:
        df = parse_activities_log(f)
        if df is not None:
            dfs.append(df)
            
    master_df = pd.concat(dfs, ignore_index=True)
    master_df = master_df.sort_values(['run_id', 'product', 'timestamp'])
    
    # Calculate Order Book Imbalance (OBI)
    master_df['obi'] = (master_df['bid_volume_1'] - master_df['ask_volume_1']) / (master_df['bid_volume_1'] + master_df['ask_volume_1'] + 1e-9)
    
    # Pre-compute target columns group-wise to ensure alignment
    g = master_df.groupby(['run_id', 'product'])
    master_df['ret_1_tick'] = g['mid_price'].shift(-1) - master_df['mid_price']
    master_df['ret_5_tick'] = g['mid_price'].shift(-5) - master_df['mid_price']
    master_df['prev_ret_1_tick'] = g['mid_price'].diff(1)
    
    results = {}
    
    for product in master_df['product'].unique():
        # Only drop NA in the specific columns we use for calculation
        prod_df = master_df[master_df['product'] == product].dropna(subset=['obi', 'ret_1_tick', 'ret_5_tick', 'prev_ret_1_tick', 'mid_price'])
        
        # 1. Autocorrelation (Lag 1)
        autocorr_1 = prod_df['prev_ret_1_tick'].corr(prod_df['ret_1_tick'])
        
        # 2. OBI predictive power
        obi_corr_1 = prod_df['obi'].corr(prod_df['ret_1_tick'])
        obi_corr_5 = prod_df['obi'].corr(prod_df['ret_5_tick'])
        
        # 3. Mean Reversion to Moving Average / True Value
        prod_df['dist_to_mean'] = prod_df['mid_price'] - prod_df['mid_price'].mean()
        mean_rev_corr_1 = prod_df['dist_to_mean'].corr(prod_df['ret_1_tick'])
        mean_rev_corr_5 = prod_df['dist_to_mean'].corr(prod_df['ret_5_tick'])
        
        results[product] = {
            "AutoCorrelation (Lag 1)": round(autocorr_1, 4),
            "OBI_Correlation_1_Tick": round(obi_corr_1, 4),
            "OBI_Correlation_5_Tick": round(obi_corr_5, 4),
            "Mean_Reversion_1_Tick": round(mean_rev_corr_1, 4),
            "Mean_Reversion_5_Tick": round(mean_rev_corr_5, 4),
        }
        
    print("\nAlpha Signatures of Backend Bots:")
    result_df = pd.DataFrame(results).T
    print(result_df)
    result_df.to_csv(f"{OUTPUT_DIR}/backend_alphas.csv")

if __name__ == "__main__":
    extract_alphas()
